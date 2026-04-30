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
import json
import logging
import os
import sqlite3
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.instagram.com/v21.0"
DB_PATH = os.path.join(os.path.dirname(__file__), "dm_campaign.db")

# ---------------------------------------------------------------------------
# Google Drive persistent tracking — historia wysyłek przetrwa restart serwera
# ---------------------------------------------------------------------------
DRIVE_SENT_FILE = "dm_campaign_sent.json"
DRIVE_FOLDER_ID = None  # root Drive
_drive_sent_cache: dict = {}  # {recipient_id: {username, sent_at, account, status}}


def _load_sent_from_drive():
    """Pobiera historię wysyłek z Google Drive (trwała pamięć)."""
    global _drive_sent_cache
    try:
        from google_auth import get_credentials
        from googleapiclient.discovery import build
        creds = get_credentials()
        drive = build("drive", "v3", credentials=creds)

        # Find the file
        results = drive.files().list(
            q=f"name='{DRIVE_SENT_FILE}' and trashed=false",
            spaces="drive", fields="files(id)"
        ).execute()
        files = results.get("files", [])

        if files:
            file_id = files[0]["id"]
            content = drive.files().get_media(fileId=file_id).execute()
            _drive_sent_cache = json.loads(content)
            logger.info("Drive: załadowano %d rekordów wysyłek DM", len(_drive_sent_cache))
        else:
            _drive_sent_cache = {}
            logger.info("Drive: brak pliku historii — nowy start")
    except Exception as e:
        logger.warning("Drive load failed (kontynuuję z SQLite): %s", e)
        _drive_sent_cache = {}


def _save_sent_to_drive():
    """Zapisuje historię wysyłek na Google Drive."""
    try:
        from google_auth import get_credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaInMemoryUpload
        creds = get_credentials()
        drive = build("drive", "v3", credentials=creds)

        content = json.dumps(_drive_sent_cache, ensure_ascii=False, indent=2)
        media = MediaInMemoryUpload(content.encode("utf-8"), mimetype="application/json")

        # Find existing file
        results = drive.files().list(
            q=f"name='{DRIVE_SENT_FILE}' and trashed=false",
            spaces="drive", fields="files(id)"
        ).execute()
        files = results.get("files", [])

        if files:
            drive.files().update(fileId=files[0]["id"], media_body=media).execute()
        else:
            drive.files().create(
                body={"name": DRIVE_SENT_FILE, "mimeType": "application/json"},
                media_body=media
            ).execute()

        logger.info("Drive: zapisano %d rekordów wysyłek DM", len(_drive_sent_cache))
    except Exception as e:
        logger.warning("Drive save failed: %s", e)


# Załaduj na starcie
try:
    _load_sent_from_drive()
except Exception:
    pass

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
    """Sprawdza czy już wysłano — Drive (trwały) + SQLite (szybki)."""
    # Check 1: Drive cache (trwały, przetrwa restart)
    if recipient_id in _drive_sent_cache:
        return True
    # Check 2: SQLite (szybki, ale ginie po restarcie)
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT 1 FROM dm_sent WHERE recipient_id = ?", (recipient_id,)
    ).fetchone()
    conn.close()
    return row is not None


def _mark_sent(recipient_id: str, username: str, status: str = "sent", account: str = ""):
    """Zapisuje wysyłkę — w SQLite + Drive (podwójna trwałość)."""
    now = datetime.utcnow().isoformat()

    # SQLite (szybki lokalny cache)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO dm_sent (recipient_id, username, status, sent_at) VALUES (?, ?, ?, ?)",
        (recipient_id, username, status, now),
    )
    conn.commit()
    conn.close()

    # Drive (trwały — przetrwa restart)
    _drive_sent_cache[recipient_id] = {
        "username": username,
        "status": status,
        "sent_at": now,
        "account": account,
    }
    _save_sent_to_drive()


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
        "SELECT recipient_id, username, status, sent_at FROM dm_sent ORDER BY sent_at ASC"
    ).fetchall()

    conn.close()
    return {
        "total_sent": total_sent,
        "total_failed": total_failed,
        "last_run": dict(last_run) if last_run else None,
        "recent": [dict(r) for r in recent],
    }


# ---------------------------------------------------------------------------
# Instagram Graph API — pobieranie kontaktów i wysyłanie DM (multi-account)
# ---------------------------------------------------------------------------

def _get_account_tokens() -> list[dict]:
    """Zwraca listę kont IG z tokenami do kampanii DM."""
    accounts = []

    # Konto główne: funlikehel
    main_token = os.environ.get("PAGE_ACCESS_TOKEN", "")
    if main_token:
        accounts.append({"name": "funlikehel", "token": main_token})

    # Konto surf4hel
    surf_token = os.environ.get("Insta_surf4hel", "")
    if surf_token:
        accounts.append({"name": "surf4hel", "token": surf_token})

    return accounts


def _get_page_id(token: str) -> str:
    """ID konta IG — pomijamy w listach kontaktów."""
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


def get_dm_contacts_for_account(account_name: str, token: str) -> list[dict]:
    """Pobiera uczestników konwersacji DM dla jednego konta z paginacją."""
    if not token:
        return []

    page_id = _get_page_id(token)
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
                logger.error("[%s] Błąd pobierania konwersacji DM: %s", account_name, e)
                break

            for conv in data.get("data", []):
                for p in conv.get("participants", {}).get("data", []):
                    pid = p.get("id", "")
                    if pid and pid != page_id and pid not in seen_ids:
                        seen_ids.add(pid)
                        contacts.append({
                            "id": pid,
                            "username": p.get("username", "?"),
                            "account": account_name,
                        })

            url = data.get("paging", {}).get("next", "")
            if not url:
                break

    logger.info("[%s] Pobrano %d kontaktów DM.", account_name, len(contacts))
    return contacts


def get_all_dm_contacts() -> list[dict]:
    """Pobiera kontakty DM ze wszystkich kont IG."""
    all_contacts = []
    seen_ids = set()

    for acct in _get_account_tokens():
        contacts = get_dm_contacts_for_account(acct["name"], acct["token"])
        for c in contacts:
            if c["id"] not in seen_ids:
                seen_ids.add(c["id"])
                all_contacts.append(c)

    logger.info("Łącznie %d unikalnych kontaktów DM z %d kont.", len(all_contacts), len(_get_account_tokens()))
    return all_contacts


async def send_campaign_dm(recipient_id: str, text: str, account_name: str = "funlikehel") -> bool:
    """Wysyła DM kampanijny z odpowiedniego konta. Zwraca True jeśli sukces."""
    accounts = {a["name"]: a["token"] for a in _get_account_tokens()}
    token = accounts.get(account_name, "")
    if not token:
        token = os.environ.get("PAGE_ACCESS_TOKEN", "")
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

async def run_dm_campaign(dry_run: bool = False, account: str = "") -> dict:
    """
    Wysyła zaproszenie /ekipa do osób z DM.

    Args:
        dry_run: True = tylko policz, nie wysyłaj (do testów)
        account: filtr konta ("surf4hel", "funlikehel") — pusty = wszystkie

    Returns:
        dict ze statystykami: total, sent, skipped, failed, per_account
    """
    message = os.environ.get("DM_CAMPAIGN_MESSAGE", DEFAULT_MESSAGE)
    delay = int(os.environ.get("DM_CAMPAIGN_DELAY", "120"))

    contacts = get_all_dm_contacts()
    if account:
        contacts = [c for c in contacts if c.get("account") == account]
    total = len(contacts)
    sent = 0
    skipped = 0
    failed = 0
    per_account = {}

    for i, contact in enumerate(contacts):
        uid = contact["id"]
        username = contact["username"]
        acct_name = contact.get("account", "funlikehel")

        if acct_name not in per_account:
            per_account[acct_name] = {"sent": 0, "skipped": 0, "failed": 0}

        if _is_already_sent(uid):
            skipped += 1
            per_account[acct_name]["skipped"] += 1
            continue

        if dry_run:
            logger.info("[DRY RUN] %d/%d @%s via @%s", i + 1, total, username, acct_name)
            skipped += 1
            per_account[acct_name]["skipped"] += 1
            continue

        try:
            await send_campaign_dm(uid, message, account_name=acct_name)
            _mark_sent(uid, username, "sent", account=acct_name)
            sent += 1
            per_account[acct_name]["sent"] += 1
            logger.info("[DM Campaign] %d/%d OK @%s via @%s", i + 1, total, username, acct_name)
        except Exception as e:
            _mark_sent(uid, username, "failed", account=acct_name)
            failed += 1
            per_account[acct_name]["failed"] += 1
            logger.error("[DM Campaign] %d/%d FAIL @%s via @%s: %s", i + 1, total, username, acct_name, str(e)[:100])

        # Rate limit — czekamy między wiadomościami
        if not dry_run and i < total - 1:
            await asyncio.sleep(delay)

    result = {"total": total, "sent": sent, "skipped": skipped, "failed": failed, "per_account": per_account}
    _log_run(total, sent, skipped, failed)
    logger.info("DM Campaign zakończona: %s", result)
    return result
