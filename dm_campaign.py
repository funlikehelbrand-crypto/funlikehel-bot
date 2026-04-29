"""
Kampania DM Instagram — automatyczne zaproszenia do ekipy FUN like HEL.

Raz dziennie skanuje konwersacje DM, wysyła wiadomość do osób które jeszcze
nie dostały zaproszenia. Tracking w SQLite (dm_campaign.db) — bez spamu.

Konfiguracja (api.env):
  PAGE_ACCESS_TOKEN — token IG
  DM_CAMPAIGN_MESSAGE — opcjonalna treść (domyślnie zaproszenie do /ekipa)
  DM_CAMPAIGN_ENABLED — "1" aby włączyć auto-wysyłkę (domyślnie wyłączona)
  DM_CAMPAIGN_DELAY — sekundy między wiadomościami (domyślnie 120)
"""

import asyncio
import logging
import os
import sqlite3
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.instagram.com/v21.0"
DB_PATH = os.path.join(os.path.dirname(__file__), "dm_campaign.db")

DEFAULT_MESSAGE = """Hej! 👋

Dołącz do ekipy FUN like HEL i zgarnij -10% na pierwszy kurs kitesurfingu, windsurfingu lub wing! 🪁🏄

Zapisz się tutaj: funlikehel.pl/ekipa

Do zobaczenia na wodzie! 🤙"""


# ---------------------------------------------------------------------------
# Database — tracking wysłanych DM
# ---------------------------------------------------------------------------

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dm_sent (
            recipient_id  TEXT PRIMARY KEY,
            username      TEXT,
            status        TEXT DEFAULT 'sent',
            sent_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dm_campaign_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_contacts INTEGER,
            sent          INTEGER,
            skipped       INTEGER,
            failed        INTEGER
        )
    """)
    conn.commit()
    conn.close()


_init_db()


def _is_already_sent(recipient_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT 1 FROM dm_sent WHERE recipient_id = ?", (recipient_id,)
    ).fetchone()
    conn.close()
    return row is not None


def _mark_sent(recipient_id: str, username: str, status: str = "sent"):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO dm_sent (recipient_id, username, status, sent_at) VALUES (?, ?, ?, ?)",
        (recipient_id, username, status, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def _log_run(total: int, sent: int, skipped: int, failed: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO dm_campaign_log (total_contacts, sent, skipped, failed) VALUES (?, ?, ?, ?)",
        (total, sent, skipped, failed),
    )
    conn.commit()
    conn.close()


def get_campaign_stats() -> dict:
    """Statystyki kampanii — do endpointu /api/dm-campaign/stats."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total_sent = conn.execute("SELECT COUNT(*) as c FROM dm_sent WHERE status = 'sent'").fetchone()["c"]
    total_failed = conn.execute("SELECT COUNT(*) as c FROM dm_sent WHERE status = 'failed'").fetchone()["c"]

    last_run = conn.execute(
        "SELECT * FROM dm_campaign_log ORDER BY run_at DESC LIMIT 1"
    ).fetchone()

    recent = conn.execute(
        "SELECT username, status, sent_at FROM dm_sent ORDER BY sent_at DESC LIMIT 10"
    ).fetchall()

    conn.close()
    return {
        "total_sent": total_sent,
        "total_failed": total_failed,
        "last_run": dict(last_run) if last_run else None,
        "recent": [dict(r) for r in recent],
    }


# ---------------------------------------------------------------------------
# Instagram Graph API — pobieranie kontaktów i wysyłanie DM
# ---------------------------------------------------------------------------

def _get_token() -> str:
    return os.environ.get("PAGE_ACCESS_TOKEN", "")


def _get_page_id() -> str:
    """ID konta IG bota — pomijamy w listach kontaktów."""
    token = _get_token()
    if not token:
        return ""
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{GRAPH_API_URL}/me",
                params={"fields": "id", "access_token": token},
            )
            resp.raise_for_status()
            return resp.json().get("id", "")
    except Exception as e:
        logger.warning("Nie udało się pobrać page_id: %s", e)
        return ""


def get_dm_contacts() -> list[dict]:
    """Pobiera wszystkich uczestników konwersacji DM z paginacją."""
    token = _get_token()
    if not token:
        logger.warning("Brak PAGE_ACCESS_TOKEN — nie mogę pobrać kontaktów DM.")
        return []

    page_id = _get_page_id()
    contacts = []
    seen_ids = set()
    url = f"{GRAPH_API_URL}/me/conversations?fields=participants,updated_time&platform=instagram&limit=50&access_token={token}"

    with httpx.Client(timeout=30) as client:
        while url:
            try:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error("Błąd pobierania konwersacji DM: %s", e)
                break

            for conv in data.get("data", []):
                for p in conv.get("participants", {}).get("data", []):
                    pid = p.get("id", "")
                    if pid and pid != page_id and pid not in seen_ids:
                        seen_ids.add(pid)
                        contacts.append({
                            "id": pid,
                            "username": p.get("username", "?"),
                        })

            url = data.get("paging", {}).get("next", "")
            if not url:
                break

    logger.info("Pobrano %d kontaktów DM.", len(contacts))
    return contacts


async def send_campaign_dm(recipient_id: str, text: str) -> bool:
    """Wysyła DM kampanijny. Zwraca True jeśli sukces."""
    token = _get_token()
    if not token:
        return False

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{GRAPH_API_URL}/me/messages",
            params={"access_token": token},
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": text},
            },
        )
        resp.raise_for_status()
        return True


# ---------------------------------------------------------------------------
# Główna logika kampanii
# ---------------------------------------------------------------------------

async def run_dm_campaign(dry_run: bool = False) -> dict:
    """
    Wysyła zaproszenie /ekipa do osób z DM, które jeszcze go nie dostały.

    Args:
        dry_run: True = tylko policz, nie wysyłaj (do testów)

    Returns:
        dict ze statystykami: total, sent, skipped, failed
    """
    message = os.environ.get("DM_CAMPAIGN_MESSAGE", DEFAULT_MESSAGE)
    delay = int(os.environ.get("DM_CAMPAIGN_DELAY", "120"))

    contacts = get_dm_contacts()
    total = len(contacts)
    sent = 0
    skipped = 0
    failed = 0

    for i, contact in enumerate(contacts):
        uid = contact["id"]
        username = contact["username"]

        if _is_already_sent(uid):
            skipped += 1
            continue

        if dry_run:
            logger.info("[DRY RUN] %d/%d @%s — pominięto (dry run)", i + 1, total, username)
            skipped += 1
            continue

        try:
            await send_campaign_dm(uid, message)
            _mark_sent(uid, username, "sent")
            sent += 1
            logger.info("[DM Campaign] %d/%d OK @%s", i + 1, total, username)
        except Exception as e:
            _mark_sent(uid, username, "failed")
            failed += 1
            logger.error("[DM Campaign] %d/%d FAIL @%s: %s", i + 1, total, username, str(e)[:100])

        # Rate limit — czekamy między wiadomościami
        if not dry_run and i < total - 1:
            await asyncio.sleep(delay)

    result = {"total": total, "sent": sent, "skipped": skipped, "failed": failed}
    _log_run(total, sent, skipped, failed)
    logger.info("DM Campaign zakończona: %s", result)
    return result
