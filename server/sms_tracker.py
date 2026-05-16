"""
SMS Campaign Tracker — śledzenie kampanii SMS i konwersji.

Śledzi:
- Kto dostał SMS (per kampania)
- Kto się zapisał po SMS (konwersja)
- Statystyki: wysłano / odebrano / zapisano się

Tabele SQLite (v1 — legacy, nie zmieniaj):
- sms_campaigns  — kampanie (temat, treść, data, liczba wysłanych)
- sms_sends      — kto dostał SMS w ramach kampanii
- sms_conversions — kto się zapisał po kampanii (powiązane z numerem telefonu)

Tabele SQLite (v2 — nowe, tworzone przez sms_migrations.py):
- sms_contacts      — kontakty z consent i opt-out
- sms_campaigns_v2  — kampanie v2 ze szczegółowymi statystykami
- sms_recipients    — odbiorcy z tracking tokenami (NIGDY nie wygasają)
- sms_clicks        — kliknięcia linków trackingowych
- sms_opt_outs      — opt-outy (STOP / WYPISZ)
"""

import hashlib
import logging
import os
import secrets
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

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


# =============================================================================
# TRACKING v2 — tokeny, kliknięcia, opt-outy (tabele z sms_migrations.py)
# =============================================================================

BASE_TRACKING_URL = "https://funlikehel.pl/s/"
FALLBACK_URL = "https://funlikehel.pl"


def generate_tracking_token() -> str:
    """
    Generuje losowy 12-znakowy URL-safe token.
    Token jest PERMANENTNY — nie wygasa nigdy.
    """
    return secrets.token_urlsafe(9)  # 9 bajtów → ~12 znaków base64url


def build_tracking_link(token: str, target_url: str = None) -> str:
    """
    Zwraca link trackingowy.

    Jeśli target_url podany — dodaje ?ref={token} do URL kampanii
    (np. https://funlikehel.pl/sezon2026?ref=aB3xK9mQ).
    Link wygląda naturalnie, a token umożliwia śledzenie per osoba.

    Jeśli target_url nie podany — fallback na stary format /s/{token}.
    """
    if target_url:
        separator = "&" if "?" in target_url else "?"
        return f"{target_url}{separator}ref={token}"
    return f"{BASE_TRACKING_URL}{token}"


# -----------------------------------------------------------------------------
# sms_contacts
# -----------------------------------------------------------------------------

def upsert_contact(
    phone_e164: str,
    first_name: str = None,
    last_name: str = None,
    source: str = "import",
    consent_marketing: bool = False,
    consent_transactional: bool = False,
    consent_source: str = None,
) -> int:
    """
    Tworzy lub aktualizuje kontakt. Zwraca contact_id.
    Nigdy nie nadpisuje unsubscribed_at jeśli jest ustawione.
    """
    with _conn() as c:
        existing = c.execute(
            "SELECT id FROM sms_contacts WHERE phone_e164 = ?", (phone_e164,)
        ).fetchone()

        now = datetime.now().isoformat(timespec="seconds")

        if existing:
            c.execute("""
                UPDATE sms_contacts
                SET first_name = COALESCE(?, first_name),
                    last_name  = COALESCE(?, last_name),
                    consent_sms_marketing      = MAX(consent_sms_marketing, ?),
                    consent_sms_transactional  = MAX(consent_sms_transactional, ?),
                    updated_at = ?
                WHERE phone_e164 = ?
            """, (first_name, last_name,
                  int(consent_marketing), int(consent_transactional),
                  now, phone_e164))
            return existing["id"]
        else:
            c.execute("""
                INSERT INTO sms_contacts
                    (phone_e164, first_name, last_name, source,
                     consent_sms_marketing, consent_sms_transactional,
                     consent_source, consent_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (phone_e164, first_name, last_name, source,
                  int(consent_marketing), int(consent_transactional),
                  consent_source,
                  now if (consent_marketing or consent_transactional) else None))
            return c.execute(
                "SELECT id FROM sms_contacts WHERE phone_e164 = ?", (phone_e164,)
            ).fetchone()["id"]


def get_contact_by_phone(phone_e164: str) -> dict | None:
    """Zwraca kontakt po numerze telefonu (lub None)."""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM sms_contacts WHERE phone_e164 = ?", (phone_e164,)
        ).fetchone()
    return dict(row) if row else None


def is_unsubscribed(phone_e164: str) -> bool:
    """Sprawdza czy kontakt wypisał się z marketingu."""
    with _conn() as c:
        row = c.execute(
            "SELECT unsubscribed_at FROM sms_contacts WHERE phone_e164 = ?",
            (phone_e164,)
        ).fetchone()
    if not row:
        return False
    return bool(row["unsubscribed_at"])


# -----------------------------------------------------------------------------
# sms_campaigns_v2
# -----------------------------------------------------------------------------

def create_campaign_v2(
    name: str,
    campaign_type: str,  # 'marketing' | 'transactional'
    message_template: str,
    target_description: str = None,
    scheduled_at: str = None,
) -> int:
    """Tworzy nową kampanię v2. Zwraca campaign_id."""
    with _conn() as c:
        c.execute("""
            INSERT INTO sms_campaigns_v2
                (name, type, message_template, target_description, status, scheduled_at)
            VALUES (?, ?, ?, ?, 'draft', ?)
        """, (name, campaign_type, message_template, target_description, scheduled_at))
        return c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]


def get_campaign_v2(campaign_id: int) -> dict | None:
    """Zwraca kampanię v2 po ID."""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM sms_campaigns_v2 WHERE id = ?", (campaign_id,)
        ).fetchone()
    return dict(row) if row else None


def update_campaign_status(campaign_id: int, status: str):
    """Zmienia status kampanii."""
    with _conn() as c:
        c.execute(
            "UPDATE sms_campaigns_v2 SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(timespec="seconds"), campaign_id)
        )


def update_campaign_counters(campaign_id: int):
    """Przelicza i aktualizuje liczniki kampanii na podstawie sms_recipients."""
    with _conn() as c:
        row = c.execute("""
            SELECT
                COUNT(*) AS total_recipients,
                SUM(CASE WHEN status IN ('sent','delivered') THEN 1 ELSE 0 END) AS total_sent,
                SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS total_delivered,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS total_failed,
                SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) AS total_clicked,
                SUM(CASE WHEN converted_at IS NOT NULL THEN 1 ELSE 0 END) AS total_converted
            FROM sms_recipients
            WHERE campaign_id = ?
        """, (campaign_id,)).fetchone()
        if row:
            c.execute("""
                UPDATE sms_campaigns_v2
                SET total_recipients = ?,
                    total_sent       = ?,
                    total_delivered  = ?,
                    total_failed     = ?,
                    total_clicked    = ?,
                    total_converted  = ?,
                    updated_at       = ?
                WHERE id = ?
            """, (
                row["total_recipients"] or 0,
                row["total_sent"] or 0,
                row["total_delivered"] or 0,
                row["total_failed"] or 0,
                row["total_clicked"] or 0,
                row["total_converted"] or 0,
                datetime.now().isoformat(timespec="seconds"),
                campaign_id,
            ))


# -----------------------------------------------------------------------------
# sms_recipients
# -----------------------------------------------------------------------------

def add_recipient(
    campaign_id: int,
    contact_id: int,
    phone_e164: str,
    target_url: str = "https://funlikehel.pl",
    personalized_message: str = None,
) -> dict:
    """
    Dodaje odbiorcę do kampanii z unikalnym tracking tokenem.
    Zwraca dict z id i tracking_token.
    Jeśli odbiorca już istnieje — zwraca istniejący rekord (idempotency).
    """
    with _conn() as c:
        existing = c.execute(
            "SELECT id, tracking_token FROM sms_recipients WHERE campaign_id = ? AND contact_id = ?",
            (campaign_id, contact_id)
        ).fetchone()
        if existing:
            return {"id": existing["id"], "tracking_token": existing["tracking_token"],
                    "already_exists": True}

        # Generuj unikalny token (retry w razie kolizji — praktycznie niemożliwe)
        for _ in range(5):
            token = generate_tracking_token()
            collision = c.execute(
                "SELECT 1 FROM sms_recipients WHERE tracking_token = ?", (token,)
            ).fetchone()
            if not collision:
                break

        c.execute("""
            INSERT INTO sms_recipients
                (campaign_id, contact_id, phone_e164, tracking_token, target_url,
                 personalized_message, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (campaign_id, contact_id, phone_e164, token, target_url, personalized_message))

        row = c.execute(
            "SELECT id, tracking_token FROM sms_recipients WHERE campaign_id = ? AND contact_id = ?",
            (campaign_id, contact_id)
        ).fetchone()
        return {"id": row["id"], "tracking_token": row["tracking_token"], "already_exists": False}


def get_recipient_by_token(token: str) -> dict | None:
    """Zwraca odbiorcę po tracking tokenie."""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM sms_recipients WHERE tracking_token = ?", (token,)
        ).fetchone()
    return dict(row) if row else None


def get_pending_recipients(campaign_id: int, limit: int = 100) -> list[dict]:
    """Zwraca listę pending/failed odbiorców do wysyłki (ORDER BY id — wznawialne)."""
    with _conn() as c:
        rows = c.execute("""
            SELECT r.*, c.first_name, c.last_name, c.unsubscribed_at
            FROM sms_recipients r
            LEFT JOIN sms_contacts c ON c.id = r.contact_id
            WHERE r.campaign_id = ?
              AND r.status IN ('pending', 'failed')
              AND r.send_attempts < 3
            ORDER BY r.id
            LIMIT ?
        """, (campaign_id, limit)).fetchall()
    return [dict(r) for r in rows]


def mark_recipient_sent(
    recipient_id: int,
    provider_message_id: str = None,
    status: str = "sent",
    error: str = None,
):
    """Aktualizuje status wysyłki dla odbiorcy."""
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        c.execute("""
            UPDATE sms_recipients
            SET status              = ?,
                provider_message_id = COALESCE(?, provider_message_id),
                provider_error      = ?,
                send_attempts       = send_attempts + 1,
                last_attempt_at     = ?,
                sent_at             = CASE WHEN ? = 'sent' THEN ? ELSE sent_at END
            WHERE id = ?
        """, (status, provider_message_id, error, now, status, now, recipient_id))


def mark_recipient_clicked(recipient_id: int):
    """Oznacza kliknięcie linku (jeśli jeszcze nie kliknięto)."""
    with _conn() as c:
        c.execute("""
            UPDATE sms_recipients
            SET clicked_at = COALESCE(clicked_at, ?)
            WHERE id = ?
        """, (datetime.now().isoformat(timespec="seconds"), recipient_id))


def mark_recipient_converted(recipient_id: int):
    """Oznacza konwersję (zapis na kurs itp.)."""
    with _conn() as c:
        c.execute("""
            UPDATE sms_recipients
            SET converted_at = COALESCE(converted_at, ?)
            WHERE id = ?
        """, (datetime.now().isoformat(timespec="seconds"), recipient_id))


def mark_recipient_unsubscribed(recipient_id: int):
    """Oznacza odbiorcę jako wypisanego."""
    with _conn() as c:
        c.execute(
            "UPDATE sms_recipients SET status = 'unsubscribed' WHERE id = ?",
            (recipient_id,)
        )


# -----------------------------------------------------------------------------
# sms_clicks — rejestrowanie kliknięć
# -----------------------------------------------------------------------------

def record_click(
    tracking_token: str,
    user_agent: str = None,
    ip: str = None,
) -> dict:
    """
    Rejestruje kliknięcie linku trackingowego.
    IP jest hashowane (SHA256) — nie przechowujemy surowego IP.
    Zwraca dict z recipient i redirect URL.
    """
    recipient = get_recipient_by_token(tracking_token)
    if not recipient:
        return {"found": False, "redirect_url": FALLBACK_URL}

    # Hash IP dla prywatności
    ip_hash = None
    if ip:
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]

    with _conn() as c:
        c.execute("""
            INSERT INTO sms_clicks
                (campaign_id, recipient_id, contact_id, tracking_token, user_agent, ip_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            recipient.get("campaign_id"),
            recipient.get("id"),
            recipient.get("contact_id"),
            tracking_token,
            user_agent,
            ip_hash,
        ))

    # Oznacz kliknięcie w recipients
    mark_recipient_clicked(recipient["id"])

    # Przelicz liczniki kampanii (async-friendly — szybka operacja)
    if recipient.get("campaign_id"):
        try:
            update_campaign_counters(recipient["campaign_id"])
        except Exception:
            pass

    # Zbuduj URL z UTM params
    target_url = recipient.get("target_url") or FALLBACK_URL
    utm = "utm_source=sms&utm_medium=sms&utm_campaign=flh_sms"
    separator = "&" if "?" in target_url else "?"
    redirect_url = f"{target_url}{separator}{utm}"

    return {
        "found": True,
        "recipient_id": recipient["id"],
        "campaign_id": recipient.get("campaign_id"),
        "redirect_url": redirect_url,
    }


# -----------------------------------------------------------------------------
# sms_opt_outs — STOP / WYPISZ
# -----------------------------------------------------------------------------

STOP_KEYWORDS = {
    "stop", "wypisz", "wypisuje", "wypisuję", "cancel",
    "rezygnacja", "rezygnuje", "rezygnuję", "unsubscribe",
    "koniec", "nie", "out",
}


def is_stop_message(text: str) -> tuple[bool, str | None]:
    """
    Sprawdza czy wiadomość to opt-out (STOP/WYPISZ itp.).
    Zwraca (True, słowo_kluczowe) lub (False, None).
    """
    normalized = text.strip().lower()
    # Sprawdź czy któryś keyword jest w tekście
    for kw in STOP_KEYWORDS:
        if kw in normalized:
            return True, kw
    return False, None


def process_opt_out(
    phone_e164: str,
    raw_message: str,
    keyword: str = None,
    source: str = "inbound_sms",
) -> dict:
    """
    Przetwarza opt-out:
    1. Ustawia unsubscribed_at w sms_contacts
    2. Zapisuje do sms_opt_outs
    3. Oznacza wszystkie pending recipients jako 'unsubscribed'
    Zwraca dict z informacją co zrobiono.
    """
    now = datetime.now().isoformat(timespec="seconds")

    with _conn() as c:
        # Znajdź kontakt
        contact = c.execute(
            "SELECT id, unsubscribed_at FROM sms_contacts WHERE phone_e164 = ?",
            (phone_e164,)
        ).fetchone()

        contact_id = None
        already_unsubscribed = False

        if contact:
            contact_id = contact["id"]
            already_unsubscribed = bool(contact["unsubscribed_at"])

            if not already_unsubscribed:
                c.execute("""
                    UPDATE sms_contacts
                    SET unsubscribed_at = ?,
                        consent_sms_marketing = 0,
                        updated_at = ?
                    WHERE id = ?
                """, (now, now, contact_id))

                # Anuluj wszystkie pending wysyłki do tego kontaktu
                c.execute("""
                    UPDATE sms_recipients
                    SET status = 'unsubscribed'
                    WHERE contact_id = ? AND status = 'pending'
                """, (contact_id,))
        else:
            # Kontakt nie istnieje w sms_contacts — zapisz opt-out bez contact_id
            logger.warning("Opt-out od nieznanego numeru: %s", phone_e164)

        # Zawsze zapisz do sms_opt_outs (log każdej wiadomości STOP)
        c.execute("""
            INSERT INTO sms_opt_outs (contact_id, phone_e164, source, keyword, raw_message)
            VALUES (?, ?, ?, ?, ?)
        """, (contact_id, phone_e164, source, keyword, raw_message))

    logger.info(
        "Opt-out zarejestrowany: %s | keyword=%s | already=%s",
        phone_e164, keyword, already_unsubscribed
    )

    return {
        "phone": phone_e164,
        "contact_id": contact_id,
        "keyword": keyword,
        "already_unsubscribed": already_unsubscribed,
        "action": "already_unsubscribed" if already_unsubscribed else "unsubscribed",
    }


def get_opt_out_list() -> list[dict]:
    """Zwraca wszystkich wypisanych kontaktów."""
    with _conn() as c:
        rows = c.execute("""
            SELECT phone_e164, first_name, last_name, unsubscribed_at
            FROM sms_contacts
            WHERE unsubscribed_at IS NOT NULL
            ORDER BY unsubscribed_at DESC
        """).fetchall()
    return [dict(r) for r in rows]
