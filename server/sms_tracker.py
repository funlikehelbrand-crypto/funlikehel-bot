"""
SMS Campaign Tracker — śledzenie kampanii SMS i konwersji.

Śledzi:
- Kto dostał SMS (per kampania)
- Kto się zapisał po SMS (konwersja)
- Statystyki: wysłano / odebrano / zapisano się

Tabele SQLite:
- sms_campaigns  — kampanie (temat, treść, data, liczba wysłanych)
- sms_sends      — kto dostał SMS w ramach kampanii
- sms_conversions — kto się zapisał po kampanii (powiązane z numerem telefonu)
"""

import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

import os
DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_tracker_db():
    """Tworzy tabele jeśli nie istnieją."""
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS sms_campaigns (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_key TEXT UNIQUE NOT NULL,
                topic        TEXT NOT NULL,
                message      TEXT NOT NULL,
                sent_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_sent   INTEGER DEFAULT 0,
                total_ok     INTEGER DEFAULT 0,
                total_failed INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS sms_sends (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_key TEXT NOT NULL,
                phone        TEXT NOT NULL,
                name         TEXT,
                status       TEXT DEFAULT 'sent',
                sent_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(campaign_key, phone)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS sms_conversions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                phone           TEXT NOT NULL,
                name            TEXT,
                campaign_key    TEXT,
                conversion_type TEXT NOT NULL,
                note            TEXT,
                converted_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_sends_campaign ON sms_sends(campaign_key)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sends_phone ON sms_sends(phone)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_conv_phone ON sms_conversions(phone)")


init_tracker_db()


def create_campaign(key: str, topic: str, message: str) -> int:
    """Tworzy nowy rekord kampanii. Zwraca ID."""
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO sms_campaigns (campaign_key, topic, message) VALUES (?,?,?)",
            (key, topic, message)
        )
        row = c.execute(
            "SELECT id FROM sms_campaigns WHERE campaign_key = ?", (key,)
        ).fetchone()
        return row["id"] if row else 0


def record_sends(campaign_key: str, results: list[dict], message: str, topic: str):
    """
    Zapisuje wyniki bulk wysyłki do sms_sends + aktualizuje sms_campaigns.

    results — lista dict z kluczami: phone, name, result (dict z SerwerSMS)
    """
    create_campaign(campaign_key, topic, message)
    total = len(results)
    ok = 0
    failed = 0

    with _conn() as c:
        for r in results:
            phone  = r.get("phone", "")
            name   = r.get("name", "")
            err    = r.get("result", {}).get("error")
            status = "failed" if err else "sent"
            if status == "sent":
                ok += 1
            else:
                failed += 1
            try:
                c.execute(
                    "INSERT OR REPLACE INTO sms_sends (campaign_key, phone, name, status) "
                    "VALUES (?,?,?,?)",
                    (campaign_key, phone, name, status)
                )
            except Exception as e:
                logger.warning("sms_sends insert error: %s", e)

        c.execute(
            "UPDATE sms_campaigns SET total_sent=?, total_ok=?, total_failed=?, sent_at=? "
            "WHERE campaign_key=?",
            (total, ok, failed, datetime.now().isoformat(timespec="seconds"), campaign_key)
        )
    logger.info("Kampania %s: łącznie=%d ok=%d failed=%d", campaign_key, total, ok, failed)


def record_conversion(phone: str, name: str, conversion_type: str,
                      note: str = None, campaign_key: str = None):
    """
    Rejestruje konwersję (klient zapisał się na kurs/demo/sklep po SMS).

    phone           — numer telefonu (48XXXXXXXXX)
    name            — imię klienta
    conversion_type — "kurs" | "demo_day" | "sklep" | "kontakt"
    note            — opcjonalna notatka (co zarezerwował, kiedy)
    campaign_key    — jeśli wiadomo z której kampanii pochodzi lead
    """
    # Jeśli nie podano campaign_key — znajdź ostatnią kampanię do której był wysłany SMS
    if not campaign_key:
        with _conn() as c:
            row = c.execute(
                "SELECT campaign_key FROM sms_sends WHERE phone=? "
                "ORDER BY sent_at DESC LIMIT 1", (phone,)
            ).fetchone()
            campaign_key = row["campaign_key"] if row else "unknown"

    with _conn() as c:
        c.execute(
            "INSERT INTO sms_conversions (phone, name, campaign_key, conversion_type, note) "
            "VALUES (?,?,?,?,?)",
            (phone, name, campaign_key, conversion_type, note or "")
        )
    logger.info("Konwersja: %s | %s | %s | %s", phone, name, conversion_type, campaign_key)


def get_campaign_stats(campaign_key: str = None) -> list[dict]:
    """
    Zwraca statystyki kampanii z liczbą konwersji.

    Jeśli campaign_key podany — tylko ta kampania.
    Jeśli None — wszystkie kampanie, najnowsze pierwsze.
    """
    with _conn() as c:
        if campaign_key:
            where = "WHERE sc.campaign_key = ?"
            params = (campaign_key,)
        else:
            where = ""
            params = ()

        rows = c.execute(f"""
            SELECT
                sc.campaign_key,
                sc.topic,
                sc.message,
                sc.sent_at,
                sc.total_sent,
                sc.total_ok,
                sc.total_failed,
                COUNT(DISTINCT sv.phone) AS conversions,
                GROUP_CONCAT(DISTINCT sv.conversion_type) AS conversion_types
            FROM sms_campaigns sc
            LEFT JOIN sms_conversions sv ON sv.campaign_key = sc.campaign_key
            {where}
            GROUP BY sc.campaign_key
            ORDER BY sc.sent_at DESC
        """, params).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        sent  = d.get("total_ok", 0) or 0
        conv  = d.get("conversions", 0) or 0
        d["conversion_rate"] = f"{conv/sent*100:.1f}%" if sent > 0 else "—"
        d["conversion_types"] = (d.get("conversion_types") or "").split(",")
        result.append(d)
    return result


def get_converted_contacts(campaign_key: str = None) -> list[dict]:
    """Zwraca listę klientów którzy się zapisali (konwersje)."""
    with _conn() as c:
        if campaign_key:
            where = "WHERE campaign_key = ?"
            params = (campaign_key,)
        else:
            where = ""
            params = ()
        rows = c.execute(f"""
            SELECT phone, name, campaign_key, conversion_type, note, converted_at
            FROM sms_conversions
            {where}
            ORDER BY converted_at DESC
        """, params).fetchall()
    return [dict(r) for r in rows]


def get_pending_followup(campaign_key: str, min_days: int = 3) -> list[dict]:
    """
    Zwraca kontakty z kampanii które jeszcze się NIE zapisały
    (wysłano SMS ale brak konwersji) — do follow-up.

    min_days — ile dni minęło od wysyłki (filtr, żeby nie dzwonić od razu)
    """
    with _conn() as c:
        rows = c.execute("""
            SELECT ss.phone, ss.name, ss.sent_at
            FROM sms_sends ss
            WHERE ss.campaign_key = ?
              AND ss.status = 'sent'
              AND julianday('now') - julianday(ss.sent_at) >= ?
              AND NOT EXISTS (
                  SELECT 1 FROM sms_conversions sc
                  WHERE sc.phone = ss.phone
              )
            ORDER BY ss.name
        """, (campaign_key, min_days)).fetchall()
    return [dict(r) for r in rows]
