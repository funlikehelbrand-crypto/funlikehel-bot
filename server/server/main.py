import asyncio
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime

import httpx

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware

# Core - zawsze wymagane
from claude_agent import get_reply

# Booking system
from booking_db import init_db
from booking import booking_router

# Instagram + WhatsApp — krytyczne dla odpowiadania na wiadomości
try:
    from instagram import reply_to_comment, send_dm, init_accounts as init_ig_accounts, find_account_by_ig_id
    from whatsapp import send_message as wa_send_message, mark_as_read as wa_mark_as_read
    HAS_ALL_MODULES = True
except Exception as e:
    logging.warning("Instagram/WhatsApp niedostępny: %s", e)
    HAS_ALL_MODULES = False

# Google + inne moduły — opcjonalne (background polling)
try:
    from google_mail import process_unread_emails
    from youtube import process_youtube_comments
    from tiktok import get_auth_url, exchange_code_for_token, save_token, get_stored_token, get_valid_access_token, upload_video_from_url, check_upload_status, list_videos, refresh_access_token
    from cleanup_mail import daily_cleanup, trash_cleanup
    from google_business import process_reviews
    from auto_upload import process_upload_folder, process_tiktok_upload_folder
    from sms_campaign import run_campaign, send_reminder, send_notification
    from google_contacts import get_contacts_with_phones
    from facebook_groups import process_facebook_groups
    HAS_GOOGLE_MODULES = True
except Exception as e:
    logging.warning("Moduły Google/inne niedostępne (brak credentials): %s", e)
    HAS_GOOGLE_MODULES = False

# LinkedIn — opcjonalny
try:
    from linkedin_agent import (
        get_auth_url as li_get_auth_url,
        exchange_code_for_token as li_exchange_code,
        get_access_token as li_get_access_token,
        LinkedInAgent,
        publish_next_post as li_publish_next,
        list_post_status as li_list_posts,
    )
    HAS_LINKEDIN = True
except Exception as e:
    logging.warning("LinkedIn moduł niedostępny: %s", e)
    HAS_LINKEDIN = False

load_dotenv("api.env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="FUN like HEL — Instagram Bot + Gmail + Chatbot")

@app.get("/api/probe")
async def deploy_probe():
    return {
        "deployed": "cb3f888-tiktok-upload",
        "igaa": bool(os.getenv("INSTAGRAM_IGAA_TOKEN")),
        "tiktok_endpoints": ["/tiktok/upload", "/tiktok/upload-from-yt", "/tiktok/upload-from-ig", "/tiktok/upload-from-drive", "/tiktok/upload/status/{publish_id}", "/tiktok/videos", "/tiktok/refresh-token"],
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

# Booking API
app.include_router(booking_router)

# Init booking DB on startup
init_db()

# Init SMS v2 — migracje (idempotentne, bezpieczne)
try:
    from sms_migrations import run_migrations as _run_sms_migrations
    _run_sms_migrations()
except Exception as _sms_mig_err:
    logging.warning("SMS migracje nieudane (kontynuuję): %s", _sms_mig_err)

# Init Instagram multi-account
if HAS_ALL_MODULES:
    init_ig_accounts()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://funlikehel.pl", "https://www.funlikehel.pl", "https://panel.funlikehel.pl", "https://surfiq.eu", "https://www.surfiq.eu", "https://demo.surfiq.eu", "https://faceless-security-enactment.ngrok-free.dev"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Booking confirmation email
# ---------------------------------------------------------------------------

class BookingEmailRequest(BaseModel):
    customerName: str
    customerEmail: str
    serviceName: str
    startDate: str
    startTime: str | None = None
    endTime: str | None = None
    instructorName: str | None = None
    location: str = "hel"
    totalPrice: float = 0
    currency: str = "PLN"
    bookingRef: str = ""


@app.post("/api/send-booking-email")
async def send_booking_email(req: BookingEmailRequest):
    """Send booking confirmation email via Gmail API."""
    if not req.customerEmail or "@" not in req.customerEmail:
        raise HTTPException(400, "Invalid email")

    loc_name = "Jastarnia, Polska" if req.location == "hel" else "Hurghada, Egipt"
    time_str = ""
    if req.startTime:
        time_str = f" o {req.startTime[:5]}"
        if req.endTime:
            time_str += f"-{req.endTime[:5]}"

    subject = f"Potwierdzenie rezerwacji {req.bookingRef} — FUN like HEL"
    body = f"""Czesc {req.customerName}!

Twoja rezerwacja zostala potwierdzona:

  Usluga: {req.serviceName}
  Data: {req.startDate}{time_str}
  Lokalizacja: {loc_name}
  Instruktor: {req.instructorName or 'Do przypisania'}
  Cena: {req.totalPrice} {req.currency}
  Ref: {req.bookingRef}

Pamietaj:
- Przyjdz 15 minut wczesniej
- Zabierz stroj kapielowy i recznik
- W razie zlej pogody skontaktujemy sie z Toba

Do zobaczenia na wodzie!

FUN like HEL | Szkola Kite Wind
Tel: 690 270 032
www.funlikehel.pl
"""

    try:
        if HAS_GOOGLE_MODULES:
            from google_mail import send_email
            await asyncio.get_event_loop().run_in_executor(
                None, send_email, req.customerEmail, subject, body
            )
            logger.info("Booking email sent to %s for %s", req.customerEmail, req.bookingRef)
            return {"sent": True, "to": req.customerEmail}
        else:
            logger.warning("Google modules not available, email not sent")
            return {"sent": False, "reason": "email_module_unavailable"}
    except Exception as e:
        logger.error("Failed to send booking email: %s", e)
        raise HTTPException(500, f"Email error: {e}")


# ---------------------------------------------------------------------------
# Chatbot na stronie — Alicja odpowiada klientom w czasie rzeczywistym
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    """Diagnostyka — sprawdza czy klucze API są ustawione."""
    has_claude = bool(os.environ.get("ANTHROPIC_API_KEY", ""))
    has_gemini = bool(os.environ.get("GEMINI_API_KEY", ""))
    has_openai = bool(os.environ.get("OPENAI_API_KEY", ""))

    # Google env var diagnostics
    token_raw = os.environ.get("GOOGLE_TOKEN_JSON", "")
    creds_raw = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    token_valid = False
    token_error = None
    creds_valid = False
    creds_error = None
    try:
        import json as _json
        _json.loads(token_raw)
        token_valid = True
    except Exception as e:
        token_error = str(e)
    try:
        import json as _json
        _json.loads(creds_raw)
        creds_valid = True
    except Exception as e:
        creds_error = str(e)

    return {
        "status": "ok",
        "has_all_modules": HAS_ALL_MODULES,
        "has_instagram": HAS_ALL_MODULES,
        "has_google": HAS_GOOGLE_MODULES,
        "claude_key": has_claude,
        "claude_key_prefix": os.environ.get("ANTHROPIC_API_KEY", "")[:15] + "..." if has_claude else "MISSING",
        "gemini_key": has_gemini,
        "openai_key": has_openai,
        "google_token_env_set": bool(token_raw),
        "google_token_env_valid_json": token_valid,
        "google_token_env_len": len(token_raw),
        "google_token_env_first10": repr(token_raw[:10]),
        "google_token_env_last10": repr(token_raw[-10:]) if token_raw else "",
        "google_token_env_error": token_error,
        "google_creds_env_set": bool(creds_raw),
        "google_creds_env_valid_json": creds_valid,
        "google_creds_env_error": creds_error,
        "tt_upload_folder_id": bool(os.environ.get("TIKTOK_UPLOAD_FOLDER_ID", "")),
    }

@app.get("/api/google-business/diagnose")
async def google_business_diagnose():
    """Diagnostyka Google Business — sprawdza konta, lokalizacje i recenzje bez odpowiedzi."""
    if not HAS_GOOGLE_MODULES:
        raise HTTPException(status_code=503, detail="Moduły Google niedostępne")
    try:
        from google_business import diagnose
        return diagnose()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/google-business/process")
async def google_business_process():
    """Ręczne wywołanie przetwarzania recenzji Google Business."""
    if not HAS_GOOGLE_MODULES:
        raise HTTPException(status_code=503, detail="Moduły Google niedostępne")
    try:
        from google_business import process_reviews
        count = process_reviews()
        return {"status": "ok", "answered": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/google-business/review-links")
async def review_links():
    """Zwraca linki do wystawiania opinii na Google Maps dla wszystkich profili FLH."""
    from google_business import REVIEW_LINKS
    return {
        "links": REVIEW_LINKS,
        "primary": REVIEW_LINKS["funlikehel_jastarnia"],
        "note": "Główny profil FLH Jastarnia — tu zbieramy nowe opinie",
    }


class ReviewRequestBody(BaseModel):
    phone: str
    name: str = "Kliencie"
    location: str = "funlikehel_jastarnia"   # funlikehel_jastarnia | surf4hel_jastarnia | flh_hurghada


@app.post("/api/google-business/request-review")
async def request_review(body: ReviewRequestBody):
    """
    Wysyła SMS z prośbą o opinię na Google Maps.
    Domyślnie kieruje na główny profil FUN like HEL Jastarnia.
    """
    if not HAS_GOOGLE_MODULES:
        raise HTTPException(status_code=503, detail="Moduły Google niedostępne")
    try:
        from google_business import get_review_link
        from sms import send_sms

        link = get_review_link(body.location)
        msg = (
            f"Hej {body.name}! Dziękujemy za kurs w FUN like HEL 🤙 "
            f"Jeśli masz chwilę — zostaw nam opinię na Google, bardzo nam to pomaga! "
            f"{link}"
        )
        result = send_sms(body.phone, msg)
        return {"status": "sent", "phone": body.phone, "link": link, "sms": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Endpoint czatu na stronie — Alicja odpowiada klientom."""
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Pusta wiadomość")

    session_id = req.session_id or "web_anonymous"

    try:
        reply = get_reply(
            user_message=req.message.strip(),
            sender_id=session_id,
            channel="website",
            max_tokens=512,
        )
        return {"reply": reply, "session_id": session_id}
    except Exception as e:
        logger.error("Błąd chatbota: %s", e)
        raise HTTPException(status_code=500, detail="Przepraszam, coś poszło nie tak. Zadzwoń: 690 270 032")


# ---------------------------------------------------------------------------
# Formularz "Dołącz do ekipy" — zbieranie emaili klientów
# ---------------------------------------------------------------------------

class EkipaRequest(BaseModel):
    name: str
    email: str
    phone: str | None = None
    sport: str | None = None
    locations: list[str] = []

EKIPA_SHEET_NAME = "Ekipa FLH"
EKIPA_SHEET_HEADERS = ["Data zapisu", "Imię", "Email", "Telefon", "Sport", "Lokalizacja"]
_ekipa_sheet_id: str = ""  # cache ID arkusza w pamięci procesu


def _get_ekipa_sheet_id() -> str:
    """Zwraca ID arkusza Google Sheets 'Ekipa FLH' — tworzy jeśli nie istnieje."""
    global _ekipa_sheet_id
    if _ekipa_sheet_id:
        return _ekipa_sheet_id

    sheet_id = os.environ.get("EKIPA_SHEET_ID", "")
    if sheet_id:
        _ekipa_sheet_id = sheet_id
        return sheet_id

    from google_auth import get_credentials
    from googleapiclient.discovery import build
    creds = get_credentials()
    drive = build("drive", "v3", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)

    # Szukaj istniejącego arkusza
    res = drive.files().list(
        q=f"name='{EKIPA_SHEET_NAME}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
        spaces="drive", fields="files(id)"
    ).execute()
    files = res.get("files", [])

    if files:
        sheet_id = files[0]["id"]
    else:
        # Stwórz nowy arkusz z nagłówkami
        spreadsheet = sheets.spreadsheets().create(body={
            "properties": {"title": EKIPA_SHEET_NAME},
            "sheets": [{"properties": {"title": "Zapisy"}}]
        }).execute()
        sheet_id = spreadsheet["spreadsheetId"]
        sheets.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="Zapisy!A1",
            valueInputOption="RAW",
            body={"values": [EKIPA_SHEET_HEADERS]}
        ).execute()
        logger.info("Stworzono nowy arkusz Ekipa FLH: %s", sheet_id)

    _ekipa_sheet_id = sheet_id
    return sheet_id


def _sheets_append_ekipa(record: dict):
    """Dopisuje wiersz do Google Sheets — trwałe przechowanie danych (przeżywa restart Rendera)."""
    from google_auth import get_credentials
    from googleapiclient.discovery import build
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds)
    sheet_id = _get_ekipa_sheet_id()
    row = [
        record["created_at"][:19].replace("T", " "),
        record["name"],
        record["email"],
        record["phone"],
        record["sport"],
        record["locations"],
    ]
    sheets.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range="Zapisy!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]}
    ).execute()
    logger.info("Ekipa zapisana do Google Sheets: %s | %s", record["name"], record["email"])


def _sheets_read_ekipa() -> list[dict]:
    """Czyta wszystkie zapisy z Google Sheets."""
    from google_auth import get_credentials
    from googleapiclient.discovery import build
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds)
    sheet_id = _get_ekipa_sheet_id()
    res = sheets.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range="Zapisy!A1:F"
    ).execute()
    rows = res.get("values", [])
    if not rows or len(rows) < 2:
        return []
    headers = rows[0]
    return [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in rows[1:]]


@app.post("/api/ekipa")
async def ekipa_signup(req: EkipaRequest):
    """Zapis klienta z landing page /ekipa — email, telefon, sport, lokalizacja."""
    import datetime

    record = {
        "name": req.name,
        "email": req.email,
        "phone": req.phone or "",
        "sport": req.sport or "",
        "locations": ",".join(req.locations),
        "created_at": datetime.datetime.now().isoformat(),
    }

    # SQLite — lokalny cache (ephemeral na Render, ale szybki)
    try:
        import sqlite3
        db = sqlite3.connect("ekipa.db")
        db.execute("""CREATE TABLE IF NOT EXISTS ekipa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, email TEXT, phone TEXT, sport TEXT, locations TEXT,
            created_at TEXT
        )""")
        db.execute(
            "INSERT INTO ekipa (name, email, phone, sport, locations, created_at) VALUES (?,?,?,?,?,?)",
            tuple(record.values()),
        )
        db.commit()
        db.close()
    except Exception as _db_err:
        logger.warning("SQLite ekipa zapis nieudany: %s", _db_err)

    logger.info("Nowy zapis do ekipy: %s | %s | %s | %s", req.name, req.email, req.sport, req.locations)

    # Google Sheets — TRWAŁY backup (przeżywa restart Rendera)
    try:
        _sheets_append_ekipa(record)
    except Exception as _sh_err:
        logger.warning("Google Sheets zapis ekipa nieudany: %s", _sh_err)

    # SMS powiadomienie do właściciela
    try:
        from sms import send_sms
        locs = ",".join(req.locations) if req.locations else "?"
        send_sms(
            phone="690270032",
            message=f"EKIPA: {req.name} | {req.email} | {req.phone or '-'} | {req.sport or '?'} | {locs}",
        )
    except Exception as _sms_err:
        logger.warning("SMS powiadomienie ekipa nie wysłane: %s", _sms_err)

    # Google Contacts — dodatkowy backup
    try:
        from google_contacts import create_contact
        locs = ",".join(req.locations) if req.locations else ""
        note = f"Ekipa FUN like HEL | sport: {req.sport or '?'} | lokalizacja: {locs} | zapisany: {record['created_at'][:10]}"
        create_contact(
            name=req.name,
            email=req.email,
            phone=req.phone or "",
            note=note,
        )
    except Exception as _gc_err:
        logger.warning("Google Contacts zapis ekipa nie powiodł się: %s", _gc_err)

    return {"status": "ok", "message": f"Cześć {req.name}! Jesteś w ekipie! 🤙"}


@app.get("/api/ekipa/list")
async def ekipa_list(token: str = ""):
    """Lista zapisanych klientów — czyta z Google Sheets (trwałe) + SQLite (lokalny cache)."""
    secret = os.environ.get("EKIPA_SECRET", "flh2024ekipa")
    if token != secret:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Brak dostepu")

    # Główne źródło: Google Sheets (trwałe, przeżywa restart)
    try:
        items = _sheets_read_ekipa()
        # Filtruj nagłówki jeśli przypadkowo weszły jako dane
        items = [r for r in items if r.get("Email", "") not in ("", "Email")]
        return {"count": len(items), "source": "sheets", "items": items}
    except Exception as _sh_err:
        logger.warning("Google Sheets read ekipa nieudany, fallback SQLite: %s", _sh_err)

    # Fallback: SQLite (może być pusty po restarcie)
    try:
        import sqlite3
        db = sqlite3.connect("ekipa.db")
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM ekipa ORDER BY created_at DESC").fetchall()
        db.close()
        return {"count": len(rows), "source": "sqlite", "items": [dict(r) for r in rows]}
    except Exception as _db_err:
        return {"count": 0, "source": "error", "items": [], "error": str(_db_err)}


# DM Campaign — USUNIĘTE po incydencie spamu 2026-04-30
# Wszystkie endpointy /api/dm-campaign/* zostały usunięte z kodu.


@app.get("/api/dm-report")
async def dm_report(token: str = ""):
    """Raport: pełna historia wysłanych DM + info o kontach IG (followersi)."""
    import sqlite3, httpx as _httpx
    secret = os.environ.get("EKIPA_SECRET", "flh2024ekipa")
    if token != secret:
        raise HTTPException(status_code=403, detail="Brak dostępu")

    # 1. Historia wysłanych (SQLite)
    sent = []
    try:
        DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dm_campaign.db")
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT recipient_id, username, status, sent_at FROM dm_sent ORDER BY sent_at ASC").fetchall()
        sent = [dict(r) for r in rows]
        conn.close()
    except Exception as e:
        sent = [{"error": str(e)}]

    # 2. Info o kontach IG
    GRAPH = "https://graph.instagram.com/v21.0"
    accounts_info = {}
    tokens = {
        "funlikehel": os.environ.get("PAGE_ACCESS_TOKEN", ""),
        "surf4hel": os.environ.get("Insta_surf4hel", ""),
    }
    for name, tok in tokens.items():
        if not tok:
            accounts_info[name] = {"error": "brak tokena"}
            continue
        try:
            async with _httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"{GRAPH}/me", params={
                    "access_token": tok,
                    "fields": "id,username,followers_count,follows_count,media_count,biography"
                })
                accounts_info[name] = r.json() if r.status_code == 200 else {"error": r.text[:200]}
        except Exception as e:
            accounts_info[name] = {"error": str(e)}

    # 3. Kontakty (wszystkich którym można wysłać)
    contacts_count = 0
    not_sent_contacts = []
    try:
        from dm_campaign import get_all_dm_contacts
        sent_ids = {s["recipient_id"] for s in sent if "recipient_id" in s}
        all_contacts = get_all_dm_contacts()
        contacts_count = len(all_contacts)
        not_sent_contacts = [c for c in all_contacts if c["id"] not in sent_ids]
    except Exception as e:
        not_sent_contacts = [{"error": str(e)}]

    return {
        "sent_total": len(sent),
        "sent": sent,
        "accounts": accounts_info,
        "contacts_total": contacts_count,
        "not_sent_count": len(not_sent_contacts),
        "not_sent": not_sent_contacts,
    }


@app.get("/api/dm-history")
async def dm_history(token: str = "", limit: int = 50):
    """Pobiera historię wiadomości DM z obu kont IG (ostatnie rozmowy)."""
    admin_token = os.environ.get("BOOKING_ADMIN_TOKEN", "")
    if token != admin_token:
        raise HTTPException(status_code=403, detail="Brak dostępu")

    if not HAS_ALL_MODULES:
        raise HTTPException(status_code=503, detail="Moduły niedostępne")

    from instagram import get_all_accounts
    import httpx

    GRAPH = "https://graph.instagram.com/v21.0"
    all_conversations = []

    for acct in get_all_accounts():
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # Pobierz konwersacje (Instagram Graph API)
                r = await client.get(
                    f"{GRAPH}/me/conversations",
                    params={
                        "access_token": acct.token,
                        "platform": "instagram",
                        "fields": "participants,updated_time",
                        "limit": limit,
                    },
                )
                if r.status_code != 200:
                    all_conversations.append({
                        "account": acct.name,
                        "error": f"conversations: {r.status_code} {r.text[:200]}",
                    })
                    continue

                convs = r.json().get("data", [])

                for conv in convs[:limit]:
                    conv_id = conv["id"]
                    participants = [p.get("username", p.get("name", p.get("id")))
                                    for p in conv.get("participants", {}).get("data", [])]

                    # Pobierz wiadomości z konwersacji
                    r2 = await client.get(
                        f"{GRAPH}/{conv_id}/messages",
                        params={
                            "access_token": acct.token,
                            "fields": "message,from,created_time",
                            "limit": 20,
                        },
                    )
                    messages = []
                    if r2.status_code == 200:
                        for msg in r2.json().get("data", []):
                            messages.append({
                                "from": msg.get("from", {}).get("username", msg.get("from", {}).get("name", "?")),
                                "text": msg.get("message", ""),
                                "time": msg.get("created_time", ""),
                            })

                    all_conversations.append({
                        "account": acct.name,
                        "participants": participants,
                        "updated": conv.get("updated_time", ""),
                        "messages": messages,
                    })

        except Exception as e:
            all_conversations.append({"account": acct.name, "error": str(e)})

    return {"total_conversations": len(all_conversations), "conversations": all_conversations}


@app.get("/api/dm-export")
async def dm_export(token: str = ""):
    """
    Pełny eksport kontaktów DM — paginuje przez WSZYSTKIE rozmowy.
    Zwraca listę uczestników (username, id, konto, data) bez treści wiadomości.
    Chroni: EKIPA_SECRET.
    """
    secret = os.environ.get("EKIPA_SECRET", "flh2024ekipa")
    if token != secret:
        raise HTTPException(status_code=403, detail="Brak dostępu")

    if not HAS_ALL_MODULES:
        raise HTTPException(status_code=503, detail="Instagram niedostępny")

    from instagram import get_all_accounts
    GRAPH = "https://graph.instagram.com/v21.0"
    contacts = []
    seen_ids = set()

    async with httpx.AsyncClient(timeout=30) as client:
        for acct in get_all_accounts():
            if not acct.token:
                continue

            # Pobierz własne ID konta (żeby pominąć siebie)
            try:
                me_r = await client.get(f"{GRAPH}/me", params={"fields": "id", "access_token": acct.token})
                own_id = me_r.json().get("id", "") if me_r.status_code == 200 else ""
            except Exception:
                own_id = ""

            page_url = (
                f"{GRAPH}/me/conversations"
                f"?fields=participants,updated_time"
                f"&platform=instagram&limit=50"
                f"&access_token={acct.token}"
            )
            page_num = 0

            while page_url:
                try:
                    r = await client.get(page_url, timeout=20)
                    if r.status_code != 200:
                        break
                    data = r.json()
                    page_num += 1

                    for conv in data.get("data", []):
                        updated = conv.get("updated_time", "")
                        for p in conv.get("participants", {}).get("data", []):
                            pid = p.get("id", "")
                            if pid and pid != own_id and pid not in seen_ids:
                                seen_ids.add(pid)
                                contacts.append({
                                    "id": pid,
                                    "username": p.get("username", "?"),
                                    "konto": acct.name,
                                    "ostatnia_wiadomosc": updated,
                                    "strona": page_num,
                                })

                    page_url = data.get("paging", {}).get("next", "")
                    await asyncio.sleep(0.5)  # 0.5s między stronami — bezpieczny rate limit

                except Exception as e:
                    logger.error("dm-export paginacja błąd: %s", e)
                    break

    contacts.sort(key=lambda x: x["ostatnia_wiadomosc"], reverse=True)
    return {
        "total": len(contacts),
        "contacts": contacts,
    }


# ---------------------------------------------------------------------------
# Push Notifications — wysylka przez Expo Push API
# ---------------------------------------------------------------------------

class PushSendRequest(BaseModel):
    token: str
    title: str
    body: str
    data: dict | None = None
    api_key: str

@app.post("/push/send")
async def push_send(req: PushSendRequest):
    """
    Wysyla push notification do urzadzenia klienta przez Expo Push API.
    Wymaga api_key (FLH_API_KEY z api.env).
    """
    expected_key = os.environ.get("FLH_API_KEY", "")
    if not expected_key or req.api_key != expected_key:
        raise HTTPException(status_code=403, detail="Nieprawidlowy api_key")

    from push_notifications import send_push
    success = await send_push(
        token=req.token,
        title=req.title,
        body=req.body,
        data=req.data,
    )

    if not success:
        raise HTTPException(status_code=502, detail="Nie udalo sie wyslac powiadomienia")

    return {"status": "sent"}


# ---------------------------------------------------------------------------
# Cykliczne sprawdzanie Gmaila (co 5 minut)
# ---------------------------------------------------------------------------

async def gmail_polling_loop():
    while True:
        try:
            logger.info("Sprawdzam skrzynkę Gmail...")
            process_unread_emails()
        except Exception as e:
            logger.error("Błąd Gmail polling: %s", e)
        await asyncio.sleep(1800)  # 30 minut


async def youtube_polling_loop():
    await asyncio.sleep(60)  # opóźnienie startu — nie uderzamy wszystkich API naraz
    while True:
        try:
            logger.info("Sprawdzam komentarze YouTube...")
            process_youtube_comments()
        except Exception as e:
            logger.error("Błąd YouTube polling: %s", e)
        await asyncio.sleep(14400)  # 4 godziny — oszczędność limitu API


async def daily_cleanup_loop():
    """Codzienny cleanup spamu i bounce'ów — co 24h."""
    while True:
        try:
            logger.info("Codzienny cleanup Gmail...")
            daily_cleanup()
        except Exception as e:
            logger.error("Błąd cleanup: %s", e)
        await asyncio.sleep(86400)  # 24 godziny


async def trash_cleanup_loop():
    """Opróżnienie kosza — co 2 miesiące."""
    while True:
        try:
            logger.info("Opróżniam kosz Gmail...")
            trash_cleanup()
        except Exception as e:
            logger.error("Błąd cleanup kosza: %s", e)
        await asyncio.sleep(5184000)  # 60 dni


async def auto_upload_loop():
    """Sprawdza folder YT do wrzucenia i uploaduje nowe filmy na YouTube — co 1 godzinę."""
    await asyncio.sleep(120)  # opóźnienie startu
    while True:
        try:
            process_upload_folder()
        except Exception as e:
            logger.error("Błąd auto-upload YT: %s", e)
        await asyncio.sleep(3600)  # 1 godzina


async def tiktok_auto_upload_loop():
    """Sprawdza folder TT do wrzucenia i uploaduje nowe filmy na TikTok — co 2 godziny."""
    await asyncio.sleep(180)  # opóźnienie startu (po YT loop)
    while True:
        try:
            await process_tiktok_upload_folder()
        except Exception as e:
            logger.error("Błąd auto-upload TikTok: %s", e)
        await asyncio.sleep(7200)  # 2 godziny


# Odświeżone Shorty 2026-05-05 — promuj co godzinę jako Stories
_SHORTS_CAMPAIGN_2026_05_05 = [
    ("t2__Csj2WzU", "Freeride na Cabrinha — Low Wind Session | FUN like HEL Egipt"),
    ("4pXuxouzdpY", "Piekny spot, zapraszamy do polskiej bazy | FUN like HEL Egipt"),
    ("x4LhWYDcyaY", "What is kite for you? | FUN like HEL Egipt"),
    ("QLd53kg00H4", "Kinga od zera do bohatera | FUN like HEL Egipt"),
    ("cUVHT1Lhztc", "Pierwszenstwo na wodzie — zasady bezpieczenstwa kite | FUN like HEL"),
    ("7KV9y0VQ6_4", "Sesja kitesurfingowa | FUN like HEL Egipt"),
    ("L13PDZV01eU", "Darkslide — zmiana halsu | techniki kitesurfingu | FUN like HEL"),
]


async def shorts_stories_campaign_loop():
    """Publikuje odświeżone Shorty jako Stories IG — co 1h, jeden po drugim."""
    try:
        from instagram import publish_yt_short_story_sync
    except ImportError:
        logger.warning("Brak instagram.py — shorts_stories_campaign_loop wyłączony.")
        return

    logger.info("Shorts Stories Campaign START — %d filmów co 1h.", len(_SHORTS_CAMPAIGN_2026_05_05))
    for video_id, title in _SHORTS_CAMPAIGN_2026_05_05:
        try:
            publish_yt_short_story_sync(video_id, title)
            logger.info("✅ Story Short opublikowane: %s", title[:50])
        except Exception as e:
            logger.error("❌ Błąd Story Short '%s': %s", video_id, e)
        await asyncio.sleep(3600)  # 1 godzina między Story

    logger.info("Shorts Stories Campaign KONIEC — wszystkie 7 Story opublikowane.")


async def google_business_loop():
    """Sprawdzanie recenzji Google Business — co 3h.
    GBP API approved 2026-05-20. Alicja odpowiada na recenzje.
    """
    await asyncio.sleep(300)  # opóźnienie startu
    while True:
        try:
            logger.info("Sprawdzam recenzje Google Business...")
            process_reviews()
        except Exception as e:
            logger.error("Błąd Google Business polling: %s", e)
        await asyncio.sleep(10800)  # 3h


async def facebook_groups_loop():
    """Przeglądanie grup Facebook — co 2 godziny."""
    await asyncio.sleep(240)  # opóźnienie startu
    while True:
        try:
            logger.info("Sprawdzam grupy Facebook...")
            process_facebook_groups()
        except Exception as e:
            logger.error("Błąd Facebook Groups polling: %s", e)
        await asyncio.sleep(7200)  # 2 godziny


async def keep_alive_loop():
    """Self-ping co 10 min żeby Render free tier nie usypiał serwera."""
    while True:
        await asyncio.sleep(600)  # 10 min
        try:
            async with httpx.AsyncClient() as client:
                await client.get("https://funlikehel-bot.onrender.com/api/health", timeout=10)
            logger.debug("Keep-alive ping OK")
        except Exception:
            pass


async def fb_lead_scout_loop():
    """Skanowanie grup Facebook w poszukiwaniu leadów — co 6 godzin."""
    await asyncio.sleep(300)  # opóźnienie startu 5 min (po reszcie modułów)
    while True:
        try:
            logger.info("FB Lead Scout: startuję skanowanie grup...")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _fb_lead_scan)
            logger.info("FB Lead Scout: zakończono — %s", result)
        except Exception as e:
            logger.error("Błąd FB Lead Scout: %s", e)
        await asyncio.sleep(21600)  # 6 godzin


async def surfiq_scout_loop():
    """SurfIQ B2B prospect scanning — every 12 hours."""
    await asyncio.sleep(600)  # 10 min delay after startup
    while True:
        try:
            logger.info("SurfIQ Prospect Scout: starting scan...")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _surfiq_scan)
            logger.info("SurfIQ Prospect Scout: done — %s", result)
            # Run enrichment pass after scan
            if _HAS_SURFIQ_SCOUT:
                await loop.run_in_executor(None, _surfiq_enrich, 20)
                logger.info("SurfIQ Prospect Scout: enrichment pass done.")
        except Exception as e:
            logger.error("SurfIQ Prospect Scout error: %s", e)
        await asyncio.sleep(43200)  # 12 hours


# ---------------------------------------------------------------------------
# IG Scheduled Posts — publikuje posty z ig_posts_queue.json o właściwej godzinie
# ---------------------------------------------------------------------------

RENDER_BASE_URL = "https://funlikehel-bot.onrender.com"
IG_QUEUE_FILE   = os.path.join(os.path.dirname(__file__), "ig_posts_queue.json")


async def ig_scheduled_posts_loop():
    """Co 5 minut sprawdza kolejkę IG i publikuje posty których czas minął."""
    await asyncio.sleep(120)  # daj serwerowi chwilę na start
    while True:
        try:
            if not os.path.exists(IG_QUEUE_FILE):
                await asyncio.sleep(300)
                continue

            with open(IG_QUEUE_FILE, encoding="utf-8") as f:
                queue = json.load(f)

            now = int(__import__("time").time())
            changed = False

            for post in queue:
                if post.get("status") != "pending":
                    continue
                if post["scheduled_ts"] > now:
                    continue

                # Czas publikacji nadszedł
                label = post.get("label", "?")
                logger.info("IG scheduler: publikuję post '%s'", label)

                # Ustal URL zdjęcia
                image_url = post.get("image_url")
                if not image_url:
                    local = post.get("image_local", "")
                    # Wyciągnij ścieżkę względną po "server/static/"
                    static_marker = "server/static/"
                    if static_marker in local:
                        rel = local[local.index(static_marker) + len(static_marker):]
                    else:
                        rel = os.path.basename(local)
                    image_url = f"{RENDER_BASE_URL}/static/{rel}"

                ig_token = os.getenv("INSTAGRAM_IGAA_TOKEN") or os.getenv("IGAA_TOKEN", "")
                ig_user_id = "27441134238823713"
                caption = post.get("caption", "")

                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        # 1. Utwórz media container
                        media_resp = await client.post(
                            f"https://graph.instagram.com/v21.0/{ig_user_id}/media",
                            data={
                                "image_url": image_url,
                                "caption": caption,
                                "access_token": ig_token,
                            },
                        )
                        media_data = media_resp.json()
                        creation_id = media_data.get("id")

                        if not creation_id:
                            raise ValueError(f"Brak creation_id: {media_data}")

                        await asyncio.sleep(6)  # IG wymaga chwili na przetworzenie

                        # 2. Opublikuj
                        pub_resp = await client.post(
                            f"https://graph.instagram.com/v21.0/{ig_user_id}/media_publish",
                            data={
                                "creation_id": creation_id,
                                "access_token": ig_token,
                            },
                        )
                        pub_data = pub_resp.json()
                        post_id = pub_data.get("id")

                        post["status"] = "published"
                        post["ig_post_id"] = post_id
                        post["published_at"] = now
                        changed = True
                        logger.info("IG scheduler: opublikowano '%s' — post_id: %s", label, post_id)

                except Exception as e:
                    logger.error("IG scheduler błąd dla '%s': %s", label, e)
                    post["status"] = "error"
                    post["error"] = str(e)
                    changed = True

                await asyncio.sleep(10)  # pauza między postami

            if changed:
                with open(IG_QUEUE_FILE, "w", encoding="utf-8") as f:
                    json.dump(queue, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error("IG scheduler loop błąd: %s", e)

        await asyncio.sleep(300)  # sprawdzaj co 5 minut


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_alive_loop())
    if HAS_GOOGLE_MODULES:
        asyncio.create_task(gmail_polling_loop())
        asyncio.create_task(youtube_polling_loop())
        asyncio.create_task(daily_cleanup_loop())
        asyncio.create_task(trash_cleanup_loop())
        asyncio.create_task(google_business_loop())
        asyncio.create_task(auto_upload_loop())
        asyncio.create_task(tiktok_auto_upload_loop())
        asyncio.create_task(facebook_groups_loop())
        asyncio.create_task(shorts_stories_campaign_loop())
    if _HAS_FB_LEAD_SCOUT:
        asyncio.create_task(fb_lead_scout_loop())
        logger.info("FB Lead Scout loop uruchomiony — skanowanie co 6h.")
    if _HAS_SURFIQ_SCOUT:
        asyncio.create_task(surfiq_scout_loop())
        logger.info("SurfIQ Prospect Scout loop uruchomiony — skanowanie co 12h.")
    if not _HAS_FB_LEAD_SCOUT and not _HAS_SURFIQ_SCOUT:
        logger.info("Tryb minimalny — tylko chatbot i API. Brak polling loops.")
    asyncio.create_task(ig_scheduled_posts_loop())
    logger.info("IG Scheduled Posts loop uruchomiony — sprawdzanie co 5 min.")


# ---------------------------------------------------------------------------
# Instagram Stories — endpoint do ręcznego triggera
# ---------------------------------------------------------------------------

@app.post("/api/post-short-story")
async def post_short_story_endpoint(video_id: str, title: str = ""):
    """
    Publikuje Story na IG z miniaturą YT Shorta + link.
    Użycie: POST /api/post-short-story?video_id=ABC123&title=Tytuł
    """
    try:
        from instagram import publish_yt_short_story_sync
        result = publish_yt_short_story_sync(video_id, title)
        return {"ok": True, "story_id": result.get("id"), "video_id": video_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run-shorts-campaign")
async def run_shorts_campaign_endpoint():
    """Publikuje wszystkie 7 odświeżonych Shortów jako Stories od razu (bez czekania 1h)."""
    try:
        from instagram import publish_yt_short_story_sync
        results = []
        for video_id, title in _SHORTS_CAMPAIGN_2026_05_05:
            try:
                r = publish_yt_short_story_sync(video_id, title)
                results.append({"video_id": video_id, "ok": True, "story_id": r.get("id")})
            except Exception as e:
                results.append({"video_id": video_id, "ok": False, "error": str(e)})
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# FB Lead Scout — endpointy
# ---------------------------------------------------------------------------

try:
    from fb_lead_scout import scan_groups as _fb_lead_scan, get_leads_report as _fb_leads_report
    _HAS_FB_LEAD_SCOUT = True
except Exception as _fb_err:
    logging.warning("fb_lead_scout niedostępny: %s", _fb_err)
    _HAS_FB_LEAD_SCOUT = False


@app.post("/api/fb-leads/scan")
async def fb_leads_scan():
    """Uruchamia skanowanie grup Facebook — szuka leadów dla kitesurfingu."""
    if not _HAS_FB_LEAD_SCOUT:
        raise HTTPException(status_code=503, detail="Moduł fb_lead_scout niedostępny (zainstaluj playwright).")
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _fb_lead_scan)
    return result


@app.post("/api/instagram-to-fb")
async def instagram_to_fb(mode: str = "latest"):
    """
    Pobiera post z Instagrama i publikuje go na stronie Facebook Fun Like Hel.
    mode: 'latest' = ostatni post, 'top' = post z największą liczbą polubień
    """
    import requests as req_lib

    page_token = os.getenv("PAGE_ACCESS_TOKEN", "")
    page_id = os.getenv("FB_PAGE_ID", "763267196880291")
    graph = "https://graph.facebook.com/v25.0"

    if not page_token:
        raise HTTPException(status_code=500, detail="Brak PAGE_ACCESS_TOKEN")

    # Krok 1 — token IGAA do odczytu postów IG (Instagram Business Login)
    igaa_token = os.getenv("INSTAGRAM_IGAA_TOKEN", "") or os.getenv("IG_READ_TOKEN", "")

    # Krok 2 — pobierz posty IG przez Instagram Graph API (graph.instagram.com)
    media = []
    ig_err = "brak tokenu INSTAGRAM_IGAA_TOKEN"

    if igaa_token:
        r_ig = req_lib.get("https://graph.instagram.com/v21.0/me/media", params={
            "fields": "id,caption,media_type,media_url,thumbnail_url,like_count,timestamp,permalink",
            "limit": 10,
            "access_token": igaa_token
        })
        media = r_ig.json().get("data", [])
        ig_err = r_ig.json().get("error", {}).get("message", "")

    if not media:
        # Fallback: PAGE_ACCESS_TOKEN może być starym tokenem IGAA
        r_ig2 = req_lib.get("https://graph.instagram.com/v21.0/me/media", params={
            "fields": "id,caption,media_type,media_url,thumbnail_url,like_count,timestamp,permalink",
            "limit": 10,
            "access_token": page_token
        })
        media = r_ig2.json().get("data", [])

    if not media:
        raise HTTPException(status_code=404, detail=f"Brak postów IG. Ustaw INSTAGRAM_IGAA_TOKEN na Render. Błąd: {ig_err}")

    # Krok 3 — wybierz post
    if mode == "top":
        post = max(media, key=lambda x: x.get("like_count", 0))
    else:
        post = media[0]  # najnowszy

    caption = post.get("caption", "")
    media_url = post.get("media_url") or post.get("thumbnail_url", "")
    permalink = post.get("permalink", "")
    media_type = post.get("media_type", "IMAGE")

    # Krok 4 — opublikuj na FB
    from fb_publisher import publish_post, publish_post_with_image

    # Dodaj link do IG posta i skróć caption do 500 znaków
    text = caption[:500] if caption else ""
    if permalink:
        text += f"\n\n📸 Zobacz na Instagram: {permalink}"

    if media_url and media_type in ("IMAGE", "CAROUSEL_ALBUM"):
        result = publish_post_with_image(text=text, image_url=media_url)
    else:
        result = publish_post(text=text, link=permalink)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"Błąd publikacji FB: {result['error']}")

    return {
        "success": True,
        "ig_post_id": post["id"],
        "ig_media_type": media_type,
        "fb_post_id": result["post_id"],
        "fb_url": result.get("url"),
        "caption_preview": text[:100]
    }


@app.get("/api/version")
async def get_version():
    return {"version": "igaa-2e3294a", "ig_id": "17841402381473231", "igaa": bool(os.getenv("INSTAGRAM_IGAA_TOKEN"))}


@app.get("/api/fb-leads/report")
async def fb_leads_report_endpoint(min_score: int = 30, limit: int = 50):
    """Zwraca listę leadów z bazy SQLite (score >= min_score)."""
    if not _HAS_FB_LEAD_SCOUT:
        raise HTTPException(status_code=503, detail="Moduł fb_lead_scout niedostępny (zainstaluj playwright).")
    leads = _fb_leads_report(min_score=min_score, limit=limit)
    return {"count": len(leads), "leads": leads}


# ---------------------------------------------------------------------------
# SurfIQ Chat Bot — website chatbot for surfiq.eu
# ---------------------------------------------------------------------------

try:
    from surfiq_chat import get_surfiq_reply
    _HAS_SURFIQ_CHAT = True
except Exception as _sc_err:
    logging.warning("surfiq_chat unavailable: %s", _sc_err)
    _HAS_SURFIQ_CHAT = False


# ---------------------------------------------------------------------------
# SurfIQ Telegram Bot
# ---------------------------------------------------------------------------

try:
    from telegram_bot import handle_message as _tg_handle, set_webhook as _tg_set_webhook, get_webhook_info as _tg_webhook_info
    _HAS_TELEGRAM = True
except Exception as _tg_err:
    logging.warning("telegram_bot unavailable: %s", _tg_err)
    _HAS_TELEGRAM = False


@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request):
    """Telegram Bot webhook — receives messages and replies with SurfIQ AI."""
    if not _HAS_TELEGRAM:
        return {"ok": False}
    try:
        update = await request.json()
        await _tg_handle(update)
        return {"ok": True}
    except Exception as e:
        logging.error("Telegram webhook error: %s", e)
        return {"ok": False}


@app.post("/api/telegram/setup")
async def telegram_setup():
    """Set up Telegram webhook."""
    if not _HAS_TELEGRAM:
        return {"error": "telegram_bot unavailable"}
    result = await _tg_set_webhook("https://funlikehel-bot.onrender.com/api/telegram/webhook")
    return result


@app.get("/api/telegram/status")
async def telegram_status():
    """Check Telegram webhook status."""
    if not _HAS_TELEGRAM:
        return {"error": "telegram_bot unavailable"}
    return await _tg_webhook_info()


@app.post("/api/surfiq-chat")
async def surfiq_chat_endpoint(request: Request):
    """SurfIQ chatbot endpoint — called from surfiq.eu chat widget."""
    if not _HAS_SURFIQ_CHAT:
        return {"reply": "Chat is temporarily unavailable. Email us at office@surfiq.eu!"}
    try:
        body = await request.json()
        message = body.get("message", "")
        history = body.get("history", [])
        if not message:
            return {"reply": "How can I help you? Ask me about SurfIQ features, pricing, or demo!"}
        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(None, get_surfiq_reply, message, history)
        return {"reply": reply}
    except Exception as e:
        logging.error("SurfIQ chat error: %s", e)
        return {"reply": "Something went wrong. Please email office@surfiq.eu!"}


# ---------------------------------------------------------------------------
# SurfIQ Prospect Scout — B2B sales prospecting for SurfIQ SaaS
# ---------------------------------------------------------------------------

try:
    from surfiq_prospect_scout import (
        scan_prospects as _surfiq_scan,
        get_prospects_report as _surfiq_report,
        enrich_pending_prospects as _surfiq_enrich,
        export_prospects_csv as _surfiq_csv,
        update_prospect_status as _surfiq_update_status,
        get_prospects_markdown_report as _surfiq_md_report,
    )
    _HAS_SURFIQ_SCOUT = True
except Exception as _surfiq_err:
    logging.warning("surfiq_prospect_scout niedostępny: %s", _surfiq_err)
    _HAS_SURFIQ_SCOUT = False


@app.post("/api/surfiq/scan")
async def surfiq_scan():
    """Triggers SurfIQ B2B prospect scan across Facebook groups."""
    if not _HAS_SURFIQ_SCOUT:
        raise HTTPException(status_code=503, detail="surfiq_prospect_scout unavailable.")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _surfiq_scan)
    return result


@app.get("/api/surfiq/report")
async def surfiq_report(min_score: int = 30, limit: int = 50, status: str = None):
    """Returns SurfIQ B2B prospects from database."""
    if not _HAS_SURFIQ_SCOUT:
        raise HTTPException(status_code=503, detail="surfiq_prospect_scout unavailable.")
    prospects = _surfiq_report(min_score=min_score, limit=limit, status=status)
    return {"count": len(prospects), "prospects": prospects}


@app.post("/api/surfiq/enrich")
async def surfiq_enrich(limit: int = 20):
    """Runs web enrichment pass for pending prospects."""
    if not _HAS_SURFIQ_SCOUT:
        raise HTTPException(status_code=503, detail="surfiq_prospect_scout unavailable.")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _surfiq_enrich, limit)
    return result


@app.get("/api/surfiq/export")
async def surfiq_export(min_score: int = 25):
    """Returns CSV export of prospects."""
    if not _HAS_SURFIQ_SCOUT:
        raise HTTPException(status_code=503, detail="surfiq_prospect_scout unavailable.")
    csv_data = _surfiq_csv(min_score=min_score)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=surfiq_prospects_{datetime.now().strftime('%Y%m%d')}.csv"
        },
    )


@app.patch("/api/surfiq/status")
async def surfiq_update_status(prospect_id: int, status: str, notes: str = None):
    """Updates prospect outreach status (new/contacted/demo_scheduled/converted/rejected)."""
    if not _HAS_SURFIQ_SCOUT:
        raise HTTPException(status_code=503, detail="surfiq_prospect_scout unavailable.")
    ok = _surfiq_update_status(prospect_id, status, notes)
    if not ok:
        raise HTTPException(status_code=400,
                            detail=f"Invalid status '{status}' or prospect_id {prospect_id} not found.")
    return {"ok": True, "prospect_id": prospect_id, "status": status}


# ---------------------------------------------------------------------------
# SMS — kampanie i powiadomienia
# ---------------------------------------------------------------------------

class SMSCampaignRequest(BaseModel):
    topic: str
    label: str | None = None
    dry_run: bool = False
    message: str | None = None  # Gotowy tekst SMS (pomija generowanie przez Alicję)

class SMSReminderRequest(BaseModel):
    phone: str
    name: str
    course_name: str
    date: str
    hour: str

class SMSNotificationRequest(BaseModel):
    phone: str
    name: str
    content: str

@app.post("/sms/campaign")
async def sms_campaign(req: SMSCampaignRequest):
    """Uruchamia kampanię SMS — Alicja generuje treść (lub używa podanej), wysyłka do kontaktów Google."""
    result = run_campaign(topic=req.topic, label=req.label, dry_run=req.dry_run,
                          message=req.message)
    return result

@app.post("/sms/reminder")
async def sms_reminder(req: SMSReminderRequest):
    """Wysyła przypomnienie SMS o kursie do konkretnego klienta."""
    result = send_reminder(req.phone, req.name, req.course_name, req.date, req.hour)
    return result

@app.post("/sms/notify")
async def sms_notify(req: SMSNotificationRequest):
    """Wysyła dowolne powiadomienie SMS do klienta."""
    result = send_notification(req.phone, req.name, req.content)
    return result

@app.get("/sms/contacts")
async def sms_contacts(label: str | None = None):
    """Podgląd kontaktów z Google Contacts które mają numery telefonów."""
    contacts = get_contacts_with_phones(label=label)
    return {"count": len(contacts), "contacts": contacts}


@app.get("/sms/log")
async def sms_log(limit: int = 50):
    """Historia wysłanych SMS-ów — logi z bazy."""
    if os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("USE_FIRESTORE"):
        from google.cloud import firestore as _fs
        docs = _fs.Client().collection("sms_log").order_by(
            "ts", direction=_fs.Query.DESCENDING
        ).limit(limit).stream()
        rows = [{"id": d.id, **d.to_dict()} for d in docs]
    else:
        import sqlite3 as _sqlite3
        db = _sqlite3.connect("memory.db")
        db.row_factory = _sqlite3.Row
        rows = db.execute(
            "SELECT id, phone, message, sender, status, error, ts FROM sms_log ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
        db.close()
        rows = [dict(r) for r in rows]
    return {"count": len(rows), "log": rows}


# ---------------------------------------------------------------------------
# SMS Tracker — śledzenie kampanii i konwersji
# ---------------------------------------------------------------------------

try:
    from sms_tracker import (
        get_campaign_stats, get_converted_contacts,
        get_pending_followup, record_conversion
    )
    _SMS_TRACKER_OK = True
except ImportError:
    _SMS_TRACKER_OK = False


class SMSConversionRequest(BaseModel):
    phone: str
    name: str
    conversion_type: str  # "kurs" | "demo_day" | "sklep" | "kontakt"
    note: str | None = None
    campaign_key: str | None = None


@app.get("/sms/campaigns")
async def sms_campaigns():
    """Statystyki kampanii SMS: wysłano, dostarczono, konwersje."""
    if not _SMS_TRACKER_OK:
        raise HTTPException(status_code=503, detail="sms_tracker niedostępny")
    return {"campaigns": get_campaign_stats()}


@app.post("/sms/conversion")
async def sms_conversion(req: SMSConversionRequest):
    """Rejestruje konwersję — klient zapisał się po kampanii SMS."""
    if not _SMS_TRACKER_OK:
        raise HTTPException(status_code=503, detail="sms_tracker niedostępny")
    record_conversion(
        phone=req.phone, name=req.name,
        conversion_type=req.conversion_type,
        note=req.note, campaign_key=req.campaign_key
    )
    return {"status": "ok", "message": f"Konwersja zapisana: {req.name} ({req.conversion_type})"}


@app.get("/sms/conversions")
async def sms_conversions(campaign_key: str = None):
    """Lista klientów którzy się zapisali po kampanii SMS."""
    if not _SMS_TRACKER_OK:
        raise HTTPException(status_code=503, detail="sms_tracker niedostępny")
    return {"conversions": get_converted_contacts(campaign_key)}


@app.get("/sms/followup")
async def sms_followup(campaign_key: str, min_days: int = 3):
    """
    Kontakty z kampanii bez konwersji (do follow-up).
    min_days — ile dni minęło od wysyłki (domyślnie 3).
    """
    if not _SMS_TRACKER_OK:
        raise HTTPException(status_code=503, detail="sms_tracker niedostępny")
    contacts = get_pending_followup(campaign_key, min_days)
    return {
        "campaign_key": campaign_key,
        "pending_count": len(contacts),
        "contacts": contacts,
    }


# ---------------------------------------------------------------------------
# SMS v2 — tracking redirect (NIGDY nie wygasa → nie 404, zawsze redirect)
# ---------------------------------------------------------------------------

@app.get("/s/{token}")
async def sms_tracking_redirect(token: str, request: Request):
    """
    Endpoint trackingowy SMS — obsługuje linki z wiadomości SMS.

    Rejestruje kliknięcie (IP hash + user-agent) i przekierowuje na target_url z UTM.
    Jeśli token nieznany — przekierowuje na funlikehel.pl (NIGDY 404!).
    Token jest permanentny — nie wygasa nigdy.
    """
    try:
        from sms_tracker import record_click

        # Pobierz IP klienta (może być za proxy)
        forwarded_for = request.headers.get("x-forwarded-for", "")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (
            request.client.host if request.client else ""
        )
        user_agent = request.headers.get("user-agent", "")

        result = record_click(
            tracking_token=token,
            user_agent=user_agent[:500] if user_agent else None,
            ip=client_ip or None,
        )

        redirect_url = result.get("redirect_url", "https://funlikehel.pl")
        if result.get("found"):
            logger.info(
                "SMS click: token=%s recipient=%s campaign=%s → %s",
                token, result.get("recipient_id"), result.get("campaign_id"), redirect_url,
            )
        else:
            logger.info("SMS click: nieznany token=%s → fallback redirect", token)

        return RedirectResponse(url=redirect_url, status_code=302)

    except Exception as e:
        logger.error("Błąd tracking redirect dla token=%s: %s", token, e)
        # Zawsze redirect, nigdy 404
        return RedirectResponse(url="https://funlikehel.pl", status_code=302)


# ---------------------------------------------------------------------------
# SMS v2 — tracking pixel (wywoływany z JS na landing page, ?ref={token})
# ---------------------------------------------------------------------------

@app.get("/api/sms/pixel/{token}")
async def sms_tracking_pixel(token: str, request: Request):
    """
    Lekki tracking pixel — JS na landing page wywołuje ten endpoint
    gdy wykryje ?ref={token} w URL. Rejestruje kliknięcie bez redirect.

    Zwraca 1x1 przezroczysty GIF + CORS headers.
    """
    from starlette.responses import Response
    try:
        from sms_tracker import record_click

        forwarded_for = request.headers.get("x-forwarded-for", "")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (
            request.client.host if request.client else ""
        )
        user_agent = request.headers.get("user-agent", "")

        result = record_click(
            tracking_token=token,
            user_agent=user_agent[:500] if user_agent else None,
            ip=client_ip or None,
        )

        if result.get("found"):
            logger.info(
                "SMS pixel: token=%s recipient=%s campaign=%s",
                token, result.get("recipient_id"), result.get("campaign_id"),
            )
        else:
            logger.info("SMS pixel: nieznany token=%s", token)

    except Exception as e:
        logger.error("Błąd SMS pixel dla token=%s: %s", token, e)

    # 1x1 przezroczysty GIF
    gif = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
    return Response(
        content=gif,
        media_type="image/gif",
        headers={
            "Access-Control-Allow-Origin": "https://funlikehel.pl",
            "Cache-Control": "no-store, no-cache",
        },
    )


# ---------------------------------------------------------------------------
# SMS v2 — webhook przychodzący (opt-out STOP/WYPISZ)
# ---------------------------------------------------------------------------

@app.post("/api/sms/inbound")
async def sms_inbound(request: Request):
    """
    Webhook przychodzących SMS z SerwerSMS.pl.

    Obsługuje opt-outy: STOP / WYPISZ / CANCEL / REZYGNACJA / UNSUBSCRIBE.
    Po wykryciu opt-out:
      - ustawia contact.unsubscribed_at
      - zapisuje do sms_opt_outs
      - anuluje wszystkie pending wysyłki do tego kontaktu

    WAŻNE: ten numer NIGDY więcej nie dostanie marketingowego SMS.
    """
    try:
        from sms_tracker import is_stop_message, process_opt_out
        from sms import _normalize_phone

        # SerwerSMS może wysyłać JSON lub form-data
        content_type = request.headers.get("content-type", "")
        if "json" in content_type:
            body = await request.json()
        else:
            form = await request.form()
            body = dict(form)

        # Pola SerwerSMS.pl inbound webhook
        phone_raw = (
            body.get("phone") or body.get("sender") or body.get("from") or ""
        )
        message_text = (
            body.get("message") or body.get("text") or body.get("content") or ""
        )

        logger.info("SMS inbound: phone=%s text=%s", phone_raw, message_text[:50])

        if not phone_raw or not message_text:
            logger.warning("SMS inbound: brak phone lub message w payloadzie: %s", body)
            return {"status": "ignored", "reason": "missing_fields"}

        # Normalizuj numer do E.164
        phone_normalized = phone_raw.strip().replace(" ", "")
        if not phone_normalized.startswith("+"):
            phone_normalized = "+" + _normalize_phone(phone_normalized)

        # Sprawdź czy to opt-out
        is_stop, keyword = is_stop_message(message_text)

        if is_stop:
            result = process_opt_out(
                phone_e164=phone_normalized,
                raw_message=message_text,
                keyword=keyword,
                source="inbound_sms",
            )
            logger.info(
                "Opt-out zarejestrowany: %s | keyword=%s | action=%s",
                phone_normalized, keyword, result.get("action"),
            )
            return {
                "status": "opt_out_processed",
                "phone": phone_normalized,
                "keyword": keyword,
                "action": result.get("action"),
            }

        # Nie jest opt-out — logujemy i ignorujemy (ewentualnie przekaż do chatbota)
        logger.info(
            "SMS inbound (nie opt-out): %s → '%s'", phone_normalized, message_text[:80]
        )
        return {"status": "received", "is_opt_out": False}

    except Exception as e:
        logger.error("Błąd obsługi SMS inbound: %s", e)
        # SerwerSMS oczekuje 200 — nie rzucaj wyjątku
        return {"status": "error", "detail": str(e)}


# ---------------------------------------------------------------------------
# SMS v2 — kampanie (kolejkowanie, batch, status)
# ---------------------------------------------------------------------------

class SmsCampaignV2Request(BaseModel):
    name: str
    type: str  # 'marketing' | 'transactional'
    message_template: str
    contacts: list[dict]  # [{phone, first_name, last_name, ...}]
    target_url: str = "https://funlikehel.pl"


class SmsCampaignSendRequest(BaseModel):
    batch_size: int = 20
    dry_run: bool = False


@app.post("/api/sms/campaigns")
async def api_create_campaign_v2(req: SmsCampaignV2Request):
    """
    Tworzy kampanię SMS v2 z kolejkowaniem i tracking tokenami.
    Kontakty: [{phone: "+48600000000", first_name: "Jan", ...}]
    """
    try:
        from sms_campaign import prepare_campaign
        result = prepare_campaign(
            name=req.name,
            campaign_type=req.type,
            message_template=req.message_template,
            contacts=req.contacts,
            target_url=req.target_url,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sms/campaigns/{campaign_id}/send")
async def api_send_campaign_batch(campaign_id: int, req: SmsCampaignSendRequest):
    """
    Wysyła batch kampanii SMS v2.
    Wznawialny — uruchom wielokrotnie jeśli ma_more=true.
    """
    try:
        from sms_campaign import send_campaign_batch
        result = send_campaign_batch(
            campaign_id=campaign_id,
            batch_size=req.batch_size,
            dry_run=req.dry_run,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sms/campaigns/{campaign_id}/status")
async def api_campaign_status(campaign_id: int):
    """Status kampanii SMS v2 ze statystykami."""
    try:
        from sms_campaign import get_campaign_status
        return get_campaign_status(campaign_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sms/opt-outs")
async def api_sms_opt_outs():
    """Lista wypisanych kontaktów (opt-out)."""
    try:
        from sms_tracker import get_opt_out_list
        opt_outs = get_opt_out_list()
        return {"count": len(opt_outs), "opt_outs": opt_outs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sms/migrations")
async def api_run_sms_migrations():
    """Uruchamia migracje DB SMS v2 (bezpieczne — idempotentne)."""
    try:
        from sms_migrations import run_migrations, get_migration_status
        result = run_migrations()
        status = get_migration_status()
        return {"migrations": result, "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# WhatsApp — webhook + obsługa wiadomości
# ---------------------------------------------------------------------------

@app.get("/whatsapp")
async def whatsapp_verify(request: Request):
    """Weryfikacja webhooka WhatsApp (Meta wymaga odpowiedzi na GET)."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == os.environ.get("VERIFY_TOKEN", ""):
        logger.info("WhatsApp webhook zweryfikowany.")
        return PlainTextResponse(challenge)

    raise HTTPException(status_code=403, detail="Weryfikacja nieudana.")


@app.post("/whatsapp")
async def whatsapp_receive(request: Request):
    """Odbiera wiadomości WhatsApp i odpowiada przez Alicję."""
    payload = await request.json()
    logger.info("WhatsApp event: %s", payload)

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # Statusy dostarczenia — logujemy, nie odpowiadamy
            if value.get("statuses"):
                for status in value["statuses"]:
                    logger.info(
                        "WhatsApp status: %s -> %s",
                        status.get("recipient_id"),
                        status.get("status"),
                    )
                continue

            # Wiadomości od klientów
            for message in value.get("messages", []):
                await _handle_whatsapp_message(message, value)

    return Response(status_code=200)


async def _handle_whatsapp_message(message: dict, value: dict):
    """Obsługuje pojedynczą wiadomość WhatsApp."""
    msg_type = message.get("type")
    sender_phone = message.get("from", "")
    message_id = message.get("id", "")

    # Na razie obsługujemy tylko tekst
    if msg_type != "text":
        logger.info("WhatsApp: pomijam wiadomość typu '%s' od %s", msg_type, sender_phone)
        return

    text = message.get("text", {}).get("body", "")
    if not text:
        return

    # Imię nadawcy z profilu WhatsApp
    contacts = value.get("contacts", [])
    sender_name = contacts[0].get("profile", {}).get("name", "") if contacts else ""

    logger.info("WhatsApp od %s (%s): %s", sender_name, sender_phone, text)

    # Oznacz jako przeczytane
    try:
        await wa_mark_as_read(message_id)
    except Exception as e:
        logger.warning("Nie udało się oznaczyć jako przeczytane: %s", e)

    # Alicja odpowiada
    try:
        reply = get_reply(
            user_message=text,
            sender_id=sender_phone,
            channel="whatsapp",
            max_tokens=512,
        )
        await wa_send_message(sender_phone, reply)
        logger.info("WhatsApp odpowiedź wysłana do %s", sender_phone)
    except Exception as e:
        logger.error("Błąd WhatsApp odpowiedzi do %s: %s", sender_phone, e)


# ---------------------------------------------------------------------------
# Strony prawne (regulamin, polityka prywatności)
# ---------------------------------------------------------------------------

def _find_html(name: str) -> str:
    """Szuka pliku HTML w katalogu serwera lub nadrzędnym (dev)."""
    base = os.path.dirname(os.path.abspath(__file__))
    for path in [os.path.join(base, name), os.path.join(base, "..", name)]:
        if os.path.exists(path):
            return path
    return name  # fallback — pozwoli na czytelny błąd FileNotFoundError


@app.get("/regulamin", response_class=HTMLResponse)
async def regulamin():
    with open(_find_html("regulamin.html"), encoding="utf-8") as f:
        return f.read()

@app.get("/polityka-prywatnosci", response_class=HTMLResponse)
async def polityka():
    with open(_find_html("polityka-prywatnosci.html"), encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# TikTok — autoryzacja OAuth
# ---------------------------------------------------------------------------

# Przechowuje tymczasowo access token TikTok (w produkcji użyj bazy danych)
tiktok_tokens: dict = {}


@app.get("/tiktok/export-token")
async def tiktok_export_token(secret: str = ""):
    """Tymczasowy endpoint — zwraca token do kopiowania na lokalny dysk."""
    import os, json
    if secret != os.environ.get("ANTHROPIC_API_KEY", "")[:16]:
        raise HTTPException(status_code=403, detail="forbidden")
    token_file = os.path.join(os.path.dirname(__file__), "tiktok_token.json")
    if not os.path.exists(token_file):
        raise HTTPException(status_code=404, detail="token not found on server")
    with open(token_file) as f:
        return json.load(f)


@app.get("/tiktok/debug")
async def tiktok_debug():
    """Pokazuje aktualną konfigurację TikTok (do debugowania)."""
    import os
    key = os.environ.get("TT_CLIENT_KEY", "")
    redirect = os.environ.get("TT_REDIRECT_URI", "https://funlikehel-bot.onrender.com/tiktok/callback")
    auth_url = get_auth_url() if HAS_GOOGLE_MODULES else "unavailable"
    return {
        "client_key": key[:8] + "..." if key else "BRAK — env var nie ustawiona!",
        "client_key_full": key,  # tymczasowo pełny klucz do debugowania
        "redirect_uri": redirect,
        "auth_url": auth_url,
    }


@app.get("/tiktok/login")
async def tiktok_login():
    """Otwórz ten URL w przeglądarce żeby autoryzować TikTok."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(get_auth_url())


@app.get("/tiktok/callback")
async def tiktok_callback(code: str):
    """TikTok przekierowuje tutaj po autoryzacji."""
    tokens = await exchange_code_for_token(code)
    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")
    tiktok_tokens["access_token"] = access_token
    tiktok_tokens["refresh_token"] = refresh_token
    logger.info("TikTok autoryzowany. access_token=%s...", access_token[:12])
    # Zwracamy token — użytkownik musi go zapisać jako env var TT_ACCESS_TOKEN na Render
    return HTMLResponse(f"""
    <html><body style="font-family:monospace;padding:20px;background:#1a1a1a;color:#0f0">
    <h2>✅ TikTok połączony!</h2>
    <p>Skopiuj poniższe wartości do Render Dashboard → Environment:</p>
    <hr/>
    <p><b>TT_ACCESS_TOKEN</b><br>
    <textarea rows="3" cols="80" onclick="this.select()">{access_token}</textarea></p>
    <p><b>TT_REFRESH_TOKEN</b><br>
    <textarea rows="3" cols="80" onclick="this.select()">{refresh_token}</textarea></p>
    <hr/>
    <p>1. Idź na <a href="https://dashboard.render.com" style="color:#0ff">dashboard.render.com</a></p>
    <p>2. funlikehel-bot → Environment → Add env vars</p>
    <p>3. Wklej TT_ACCESS_TOKEN i TT_REFRESH_TOKEN</p>
    <p>4. Save Changes (Render auto-restartuje serwis)</p>
    <p>5. Pipeline będzie działał na zawsze (refresh automatyczny)</p>
    </body></html>
    """)


class TikTokUploadRequest(BaseModel):
    video_url: str
    caption: str
    privacy_level: str = "PUBLIC_TO_EVERYONE"


@app.post("/tiktok/upload")
async def tiktok_upload(req: TikTokUploadRequest):
    """Publikuje wideo na TikTok z podanego URL.
    Body: { video_url, caption, privacy_level? }
    """
    if not HAS_GOOGLE_MODULES:
        raise HTTPException(status_code=503, detail="Moduł TikTok niedostępny")
    try:
        token = await get_valid_access_token()
        result = await upload_video_from_url(token, req.video_url, req.caption)
        publish_id = result.get("data", {}).get("publish_id", "unknown")
        return {"status": "ok", "publish_id": publish_id, "caption": req.caption}
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class YouTubeUploadFromIGRequest(BaseModel):
    ig_url: str = ""       # URL reela/posta z IG (np. "https://www.instagram.com/reel/ABC123/")
    ig_media_id: str = ""  # Albo bezpośrednio media ID z Graph API
    title: str = ""        # Tytuł na YT; jeśli pusty — z opisu IG
    description: str = ""  # Opis na YT; jeśli pusty — generowany
    tags: list[str] = []
    privacy: str = "public"  # public | unlisted | private
    account: str = "funlikehel"  # Konto IG do użycia


IG_API = "https://graph.instagram.com/v21.0"
IG_ACCOUNTS = {"funlikehel": "27441134238823713", "surf4hel": "35116715114638747"}


def _ig_token(account: str) -> str:
    """Zwraca IGAA token dla danego konta IG."""
    if account == "funlikehel":
        return os.getenv("INSTAGRAM_IGAA_TOKEN", "")
    return os.getenv(f"Insta_{account}", "")


async def _fetch_ig_media_via_api(ig_url: str, ig_media_id: str, account: str) -> tuple[str, str, str]:
    """Pobiera video_url, caption, shortcode z Instagram Graph API. Zwraca (video_url, caption, shortcode)."""
    import re
    token = _ig_token(account)
    if not token:
        raise RuntimeError(f"Brak IGAA tokenu dla konta {account}")

    shortcode = ""
    if ig_url and not ig_media_id:
        m = re.search(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", ig_url)
        if m:
            shortcode = m.group(1)

    async with httpx.AsyncClient(timeout=30) as client:
        if ig_media_id:
            r = await client.get(
                f"{IG_API}/{ig_media_id}",
                params={"access_token": token, "fields": "media_url,caption,media_type,shortcode"},
            )
            if r.status_code != 200:
                raise RuntimeError(f"IG API error: {r.text[:300]}")
            data = r.json()
            return data.get("media_url", ""), data.get("caption", ""), data.get("shortcode", shortcode)

        if not shortcode:
            raise RuntimeError("Nie mogę wyciągnąć shortcode z URL. Podaj ig_media_id lub poprawny URL.")

        ig_user_id = IG_ACCOUNTS.get(account, "")
        if not ig_user_id:
            r = await client.get(f"{IG_API}/me", params={"access_token": token, "fields": "id"})
            if r.status_code == 200:
                ig_user_id = r.json().get("id", "")
        if not ig_user_id:
            raise RuntimeError(f"Nie znaleziono IG user ID dla konta {account}")

        r = await client.get(
            f"{IG_API}/{ig_user_id}/media",
            params={"access_token": token, "fields": "id,media_url,caption,media_type,shortcode", "limit": 50},
        )
        if r.status_code != 200:
            raise RuntimeError(f"IG API media list error: {r.text[:300]}")
        for item in r.json().get("data", []):
            if item.get("shortcode") == shortcode:
                return item.get("media_url", ""), item.get("caption", ""), shortcode

        raise RuntimeError(f"Nie znaleziono posta o shortcode '{shortcode}' w ostatnich 50 postach. Podaj ig_media_id.")


@app.post("/youtube/upload-from-ig")
async def youtube_upload_from_ig(req: YouTubeUploadFromIGRequest):
    """Pobiera wideo z Instagrama (Graph API) i publikuje na YouTube."""
    if not HAS_GOOGLE_MODULES:
        raise HTTPException(status_code=503, detail="Moduł YouTube niedostępny")
    if not req.ig_url and not req.ig_media_id:
        raise HTTPException(status_code=400, detail="Podaj ig_url lub ig_media_id")

    import tempfile, os as _os
    from youtube import upload_video

    tmp_dir = tempfile.mkdtemp()
    tmp_path = _os.path.join(tmp_dir, "ig_video.mp4")
    try:
        video_url, caption, shortcode = await _fetch_ig_media_via_api(req.ig_url, req.ig_media_id, req.account)
        if not video_url:
            raise RuntimeError("Post nie zawiera wideo (media_url pusty). Upewnij się, że to reel/wideo, nie zdjęcie.")

        # Pobierz plik wideo
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            r = await client.get(video_url)
            if r.status_code != 200:
                raise RuntimeError(f"Nie mogę pobrać wideo: HTTP {r.status_code}")
            with open(tmp_path, "wb") as f:
                f.write(r.content)

        title = req.title or (caption[:80] if caption else "FUN like HEL")
        description = req.description or caption or "Szkoła sportów wodnych FUN like HEL — Jastarnia & Hurghada\nwww.funlikehel.pl"
        tags = req.tags or ["kitesurfing", "windsurfing", "funlikehel", "hel", "jastarnia", "sporty wodne"]

        response = upload_video(
            file_path=tmp_path,
            title=title[:100],
            description=description,
            tags=tags,
            privacy=req.privacy,
        )
        video_id = response.get("id", "unknown")
        return {
            "status": "ok",
            "youtube_video_id": video_id,
            "youtube_url": f"https://youtube.com/watch?v={video_id}",
            "title": title[:100],
            "ig_url": req.ig_url or f"https://instagram.com/reel/{shortcode}/",
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("IG→YT upload failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.get("/youtube/ig-media-list")
async def youtube_ig_media_list(account: str = "funlikehel", limit: int = 20):
    """Lista ostatnich wideo/reelsów z IG do wyboru."""
    token = _ig_token(account)
    if not token:
        raise HTTPException(status_code=400, detail=f"Brak IGAA tokenu dla konta {account}")

    ig_user_id = IG_ACCOUNTS.get(account, "")
    async with httpx.AsyncClient(timeout=30) as client:
        if not ig_user_id:
            r = await client.get(f"{IG_API}/me", params={"access_token": token, "fields": "id"})
            if r.status_code == 200:
                ig_user_id = r.json().get("id", "")
        if not ig_user_id:
            raise HTTPException(status_code=400, detail="Nie znaleziono IG user ID")

        r = await client.get(
            f"{IG_API}/{ig_user_id}/media",
            params={"access_token": token, "fields": "id,caption,media_type,shortcode,timestamp", "limit": limit},
        )
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=r.text[:300])
        items = r.json().get("data", [])
        videos = [
            {
                "id": i["id"],
                "shortcode": i.get("shortcode", ""),
                "caption": (i.get("caption", "") or "")[:120],
                "media_type": i.get("media_type"),
                "timestamp": i.get("timestamp"),
                "url": f"https://instagram.com/reel/{i['shortcode']}/" if i.get("shortcode") else "",
            }
            for i in items if i.get("media_type") == "VIDEO"
        ]
        return {"videos": videos, "count": len(videos)}


class TikTokUploadFromYTRequest(BaseModel):
    video_id: str          # YouTube video ID (np. "En4TFI2OrEg")
    caption: str = ""      # Opis TikTok; jeśli pusty — generowany z tytułu YT
    privacy_level: str = "PUBLIC_TO_EVERYONE"


@app.post("/tiktok/upload-from-yt")
async def tiktok_upload_from_yt(req: TikTokUploadFromYTRequest):
    """Pobiera film z YouTube przez yt-dlp i publikuje na TikTok.
    Body: { video_id, caption?, privacy_level? }
    """
    if not HAS_GOOGLE_MODULES:
        raise HTTPException(status_code=503, detail="Moduł TikTok niedostępny")
    import subprocess, tempfile, os as _os, sys as _sys
    yt_url = f"https://www.youtube.com/watch?v={req.video_id}"
    tmp_dir = tempfile.mkdtemp()
    tmp_path = _os.path.join(tmp_dir, f"{req.video_id}.mp4")
    try:
        # Pobierz film przez yt-dlp (max 720p, mp4)
        result = subprocess.run(
            [
                _sys.executable, "-m", "yt_dlp",
                "--extractor-args", "youtube:player_client=mediaconnect",
                "-f", "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best",
                "--merge-output-format", "mp4",
                "-o", tmp_path,
                yt_url,
            ],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp error: {result.stderr[-500:]}")
        if not _os.path.exists(tmp_path):
            # yt-dlp może zapisać z inną nazwą — szukaj w katalogu
            files = [f for f in _os.listdir(tmp_dir) if f.endswith(".mp4")]
            if not files:
                raise RuntimeError("yt-dlp nie zapisał pliku mp4")
            tmp_path = _os.path.join(tmp_dir, files[0])

        caption = req.caption or f"Kite i surf na maxa! 🏄 Jastarnia & Hurghada\n\n#kitesurfing #funlikehel #fyp #jastarnia #hurghada"
        token = await get_valid_access_token()
        from tiktok import upload_video_file
        publish_id = await upload_video_file(token, tmp_path, caption, req.privacy_level)
        return {"status": "ok", "publish_id": publish_id, "yt_video_id": req.video_id}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.get("/tiktok/upload/status/{publish_id}")
async def tiktok_upload_status(publish_id: str):
    """Sprawdza status publikacji wideo na TikTok."""
    if not HAS_GOOGLE_MODULES:
        raise HTTPException(status_code=503, detail="Moduł TikTok niedostępny")
    try:
        token = await get_valid_access_token()
        result = await check_upload_status(token, publish_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tiktok/user-info")
async def tiktok_user_info():
    """Pobiera informacje o koncie TikTok (scope: user.info.basic)."""
    if not HAS_GOOGLE_MODULES:
        raise HTTPException(status_code=503, detail="Moduł TikTok niedostępny")
    try:
        from tiktok import get_user_info
        token = await get_valid_access_token()
        return await get_user_info(token)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tiktok/dashboard")
async def tiktok_dashboard():
    """Prosty dashboard TikTok — do demo i codziennego użytku."""
    if not HAS_GOOGLE_MODULES:
        return HTMLResponse("<h1>TikTok module unavailable</h1>", status_code=503)
    token_data = get_stored_token()
    connected = bool(token_data and token_data.get("access_token"))
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FLH Social Manager — TikTok</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f7fa;color:#1a1a2e}}
.top{{background:#1a1a2e;color:#fff;padding:16px 32px;display:flex;align-items:center;justify-content:space-between}}
.top h1{{font-size:20px;font-weight:700}}.top h1 span{{color:#00c9c9}}
.top .badge{{background:#00c9c9;color:#1a1a2e;padding:4px 12px;border-radius:12px;font-size:12px;font-weight:700}}
.container{{max-width:900px;margin:32px auto;padding:0 20px}}
.card{{background:#fff;border-radius:14px;padding:28px;margin-bottom:20px;box-shadow:0 2px 12px rgba(0,0,0,.05);border:1px solid #e8e8e8}}
.card h2{{font-size:20px;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #e8e8e8}}
.status{{display:flex;align-items:center;gap:10px;margin-bottom:16px}}
.dot{{width:12px;height:12px;border-radius:50%;background:{"#22c55e" if connected else "#ef4444"}}}
.status span{{font-size:15px;font-weight:600}}
.btn{{display:inline-block;padding:10px 24px;border-radius:8px;font-size:14px;font-weight:600;text-decoration:none;cursor:pointer;border:none}}
.btn-primary{{background:#00c9c9;color:#1a1a2e}}.btn-primary:hover{{background:#00b3b3}}
.btn-outline{{border:2px solid #00c9c9;color:#00c9c9;background:transparent}}.btn-outline:hover{{background:#e8fafa}}
#user-info{{margin-top:12px;font-size:14px;color:#555}}
.form-group{{margin-bottom:16px}}
.form-group label{{display:block;font-size:14px;font-weight:600;margin-bottom:6px}}
.form-group input,.form-group textarea,.form-group select{{width:100%;padding:10px 14px;border:1px solid #ddd;border-radius:8px;font-size:14px}}
.form-group textarea{{height:80px;resize:vertical}}
#upload-result{{margin-top:16px;padding:16px;border-radius:8px;display:none}}
.success{{background:#dcfce7;border:1px solid #22c55e;color:#166534}}
.error{{background:#fee2e2;border:1px solid #ef4444;color:#991b1b}}
</style></head>
<body>
<div class="top">
  <h1>FLH <span>Social Manager</span></h1>
  <span class="badge">TikTok Integration</span>
</div>
<div class="container">

  <div class="card">
    <h2>Account Connection</h2>
    <div class="status">
      <div class="dot"></div>
      <span>{"Connected" if connected else "Not connected"}</span>
    </div>
    {"" if connected else '<a href="/tiktok/login" class="btn btn-primary">Connect TikTok Account</a>'}
    {"<button class='btn btn-outline' onclick='loadUserInfo()'>Load Account Info</button>" if connected else ""}
    <div id="user-info"></div>
  </div>

  {"" if not connected else '''
  <div class="card">
    <h2>Upload Video to TikTok</h2>
    <form id="upload-form" onsubmit="uploadVideo(event)">
      <div class="form-group">
        <label>Video URL (publicly accessible MP4)</label>
        <input type="url" id="video-url" placeholder="https://example.com/video.mp4" required>
      </div>
      <div class="form-group">
        <label>Caption</label>
        <textarea id="caption" placeholder="Your video description and #hashtags" required></textarea>
      </div>
      <div class="form-group">
        <label>Privacy</label>
        <select id="privacy">
          <option value="PUBLIC_TO_EVERYONE">Public</option>
          <option value="MUTUAL_FOLLOW_FRIENDS">Friends</option>
          <option value="SELF_ONLY">Private</option>
        </select>
      </div>
      <button type="submit" class="btn btn-primary" id="upload-btn">Upload to TikTok</button>
    </form>
    <div id="upload-result"></div>
  </div>

  <div class="card">
    <h2>Check Upload Status</h2>
    <div class="form-group">
      <label>Publish ID</label>
      <input type="text" id="publish-id" placeholder="Enter publish_id from upload response">
    </div>
    <button class="btn btn-outline" onclick="checkStatus()">Check Status</button>
    <div id="status-result" style="margin-top:12px;font-size:14px;color:#555"></div>
  </div>
  '''}
</div>

<script>
async function loadUserInfo() {{
  const el = document.getElementById('user-info');
  el.innerHTML = 'Loading...';
  try {{
    const r = await fetch('/tiktok/user-info');
    const d = await r.json();
    const u = d.data && d.data.user ? d.data.user : d;
    el.innerHTML = '<strong>Display Name:</strong> ' + (u.display_name||'N/A')
      + '<br><strong>Followers:</strong> ' + (u.follower_count||'N/A')
      + '<br><strong>Videos:</strong> ' + (u.video_count||'N/A')
      + '<br><strong>Open ID:</strong> ' + (u.open_id||'N/A');
  }} catch(e) {{ el.innerHTML = 'Error: ' + e.message; }}
}}
async function uploadVideo(evt) {{
  evt.preventDefault();
  const btn = document.getElementById('upload-btn');
  const res = document.getElementById('upload-result');
  btn.disabled = true; btn.textContent = 'Uploading...';
  res.style.display = 'none';
  try {{
    const r = await fetch('/tiktok/upload', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        video_url: document.getElementById('video-url').value,
        caption: document.getElementById('caption').value,
        privacy_level: document.getElementById('privacy').value
      }})
    }});
    const d = await r.json();
    if (r.ok) {{
      res.className = 'success'; res.style.display = 'block';
      res.innerHTML = 'Upload initiated! Publish ID: <strong>' + d.publish_id + '</strong>';
      document.getElementById('publish-id').value = d.publish_id;
    }} else {{
      res.className = 'error'; res.style.display = 'block';
      res.textContent = 'Error: ' + (d.detail || JSON.stringify(d));
    }}
  }} catch(e) {{
    res.className = 'error'; res.style.display = 'block';
    res.textContent = 'Error: ' + e.message;
  }}
  btn.disabled = false; btn.textContent = 'Upload to TikTok';
}}
async function checkStatus() {{
  const pid = document.getElementById('publish-id').value;
  const el = document.getElementById('status-result');
  if (!pid) {{ el.textContent = 'Enter a Publish ID first.'; return; }}
  el.textContent = 'Checking...';
  try {{
    const r = await fetch('/tiktok/upload/status/' + pid);
    const d = await r.json();
    el.innerHTML = '<pre>' + JSON.stringify(d, null, 2) + '</pre>';
  }} catch(e) {{ el.textContent = 'Error: ' + e.message; }}
}}
</script>
</body></html>""")


@app.get("/tiktok/status")
async def tiktok_status():
    """Sprawdza stan autoryzacji TikTok."""
    if not HAS_GOOGLE_MODULES:
        return {"status": "error", "message": "Moduł tiktok niedostępny"}
    data = get_stored_token()
    if not data:
        return {"status": "unauthorized", "message": "Otwórz /tiktok/login żeby autoryzować"}
    import time
    expires_at = data.get("expires_at", 0)
    return {
        "status": "ok",
        "has_token": True,
        "expires_in_hours": round((expires_at - time.time()) / 3600, 1),
        "has_refresh": bool(data.get("refresh_token")),
    }


@app.get("/tiktok/videos")
async def tiktok_videos(max_count: int = 20, cursor: int | None = None):
    """Lista opublikowanych filmów na TikTok (scope: video.list)."""
    if not HAS_GOOGLE_MODULES:
        raise HTTPException(status_code=503, detail="Modul TikTok niedostepny")
    try:
        token = await get_valid_access_token()
        return await list_videos(token, max_count, cursor)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tiktok/refresh-token")
async def tiktok_refresh_token():
    """Wymusza odswiezenie tokenu TikTok (uzywa refresh_token)."""
    if not HAS_GOOGLE_MODULES:
        raise HTTPException(status_code=503, detail="Modul TikTok niedostepny")
    data = get_stored_token()
    if not data or not data.get("refresh_token"):
        raise HTTPException(status_code=401, detail="Brak refresh_token. Zaloguj ponownie: /tiktok/login")
    try:
        new_data = await refresh_access_token(data["refresh_token"])
        import time as _time
        return {
            "status": "ok",
            "expires_in_hours": round((new_data.get("expires_at", 0) - _time.time()) / 3600, 1),
            "scopes": new_data.get("scope", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TikTokUploadFromIGRequest(BaseModel):
    ig_url: str = ""
    ig_media_id: str = ""
    caption: str = ""
    account: str = "funlikehel"
    privacy_level: str = "PUBLIC_TO_EVERYONE"


@app.post("/tiktok/upload-from-ig")
async def tiktok_upload_from_ig(req: TikTokUploadFromIGRequest):
    """Pobiera wideo z Instagrama (Graph API) i publikuje na TikTok.
    Body: { ig_url?, ig_media_id?, caption?, account?, privacy_level? }
    """
    if not HAS_GOOGLE_MODULES:
        raise HTTPException(status_code=503, detail="Modul TikTok niedostepny")
    if not req.ig_url and not req.ig_media_id:
        raise HTTPException(status_code=400, detail="Podaj ig_url lub ig_media_id")

    import tempfile, shutil
    from tiktok import upload_video_file

    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, "ig_video.mp4")
    try:
        video_url, caption_ig, shortcode = await _fetch_ig_media_via_api(
            req.ig_url, req.ig_media_id, req.account
        )
        if not video_url:
            raise RuntimeError("Post nie zawiera wideo (media_url pusty). Upewnij sie, ze to reel/wideo.")

        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            r = await client.get(video_url)
            if r.status_code != 200:
                raise RuntimeError(f"Nie moge pobrac wideo: HTTP {r.status_code}")
            with open(tmp_path, "wb") as f:
                f.write(r.content)

        caption = req.caption or caption_ig or "FUN like HEL\n#kitesurfing #funlikehel #fyp"
        token = await get_valid_access_token()
        publish_id = await upload_video_file(token, tmp_path, caption, req.privacy_level)
        return {
            "status": "ok",
            "publish_id": publish_id,
            "caption": caption[:200],
            "ig_source": req.ig_url or req.ig_media_id,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("IG->TikTok upload failed")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/tiktok/upload-from-drive")
async def tiktok_upload_from_drive():
    """Wymusza natychmiastowy upload filmow z folderu 'TT do wrzucenia' na Google Drive."""
    if not HAS_GOOGLE_MODULES:
        raise HTTPException(status_code=503, detail="Modul TikTok niedostepny")
    try:
        results = await process_tiktok_upload_folder()
        return {"status": "ok", "message": "Upload z Drive zakonczony", "details": results}
    except Exception as e:
        logger.exception("TikTok upload from Drive failed")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Weryfikacja webhooka (Meta wymaga odpowiedzi na GET przy konfiguracji)
# ---------------------------------------------------------------------------

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == os.environ.get("VERIFY_TOKEN", ""):
        logger.info("Webhook zweryfikowany przez Meta.")
        return PlainTextResponse(challenge)

    raise HTTPException(status_code=403, detail="Weryfikacja nieudana.")


# ---------------------------------------------------------------------------
# Odbiór zdarzeń z Instagrama i Facebook Messenger
# ---------------------------------------------------------------------------

@app.post("/webhook")
async def receive_event(request: Request):
    # Weryfikacja podpisu Meta (bezpieczeństwo)
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()
    _verify_signature(body, signature)

    payload = await request.json()
    obj = payload.get("object", "")
    logger.info("Zdarzenie [%s]: %s", obj, payload)

    for entry in payload.get("entry", []):
        if obj == "page":
            # --- Facebook Messenger ---
            for messaging in entry.get("messaging", []):
                await _handle_messenger(messaging)
        else:
            # --- Instagram DM + komentarze ---
            entry_ig_id = entry.get("id", "")
            acct = find_account_by_ig_id(entry_ig_id) if HAS_ALL_MODULES else None
            acct_name = acct.name if acct else "funlikehel"

            for messaging in entry.get("messaging", []):
                await _handle_dm(messaging, account=acct_name)

            for change in entry.get("changes", []):
                if change.get("field") == "comments":
                    await _handle_comment(change["value"], account=acct_name)

    return Response(status_code=200)


# ---------------------------------------------------------------------------
# Facebook Messenger — obsługa wiadomości
# ---------------------------------------------------------------------------

async def _handle_messenger(messaging: dict):
    """Obsługa wiadomości z Facebook Messenger."""
    sender_id = messaging.get("sender", {}).get("id")
    message = messaging.get("message", {})
    text = message.get("text")
    mid = message.get("mid", "")

    if message.get("is_echo") or not text or not sender_id:
        return

    # Deduplikacja (SQLite)
    if _is_seen(mid):
        return
    _mark_seen(mid, "messenger")

    # Pomijamy wiadomości od naszych stron FB (anti-loop)
    page_id = os.environ.get("FB_PAGE_ID", "")
    if sender_id == page_id:
        return

    logger.info("Messenger od %s: %s", sender_id, text)

    try:
        reply_text = get_reply(text, sender_id=sender_id, channel="messenger")

        # Wyślij odpowiedź przez Messenger API
        token = os.environ.get("Fb_token", "") or os.environ.get("PAGE_ACCESS_TOKEN", "")
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://graph.facebook.com/v21.0/me/messages",
                params={"access_token": token},
                json={
                    "recipient": {"id": sender_id},
                    "message": {"text": reply_text},
                },
            )
            r.raise_for_status()

        logger.info("Messenger odpowiedź wysłana do %s", sender_id)
        try:
            from google_mail import _sync_to_panel
            _sync_to_panel(sender_email=sender_id, sender_name=f"Messenger {sender_id}", subject="Messenger DM", body=text, reply=reply_text, status="ai_handled")
        except: pass
    except Exception as e:
        logger.error("Błąd Messenger: %s", e)


# ---------------------------------------------------------------------------
# Deduplikacja — SQLite (przetrwa restarty serwera)
# ---------------------------------------------------------------------------

import sqlite3

_DEDUP_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.db")


def _init_dedup_table():
    conn = sqlite3.connect(_DEDUP_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_messages (
            mid TEXT PRIMARY KEY,
            channel TEXT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Czyść wpisy starsze niż 7 dni
    conn.execute("DELETE FROM seen_messages WHERE ts < datetime('now', '-7 days')")
    conn.commit()
    conn.close()


def _is_seen(mid: str) -> bool:
    """Sprawdza czy wiadomość już była przetworzona."""
    if not mid:
        return False
    conn = sqlite3.connect(_DEDUP_DB)
    row = conn.execute("SELECT 1 FROM seen_messages WHERE mid = ?", (mid,)).fetchone()
    conn.close()
    return row is not None


def _mark_seen(mid: str, channel: str = ""):
    """Oznacza wiadomość jako przetworzoną."""
    if not mid:
        return
    conn = sqlite3.connect(_DEDUP_DB)
    conn.execute(
        "INSERT OR IGNORE INTO seen_messages (mid, channel) VALUES (?, ?)",
        (mid, channel),
    )
    conn.commit()
    conn.close()


_init_dedup_table()


# ---------------------------------------------------------------------------
# Obsługa wiadomości DM
# ---------------------------------------------------------------------------

async def _handle_dm(messaging: dict, account: str = "funlikehel"):
    sender_id = messaging.get("sender", {}).get("id")
    message = messaging.get("message", {})
    text = message.get("text")
    mid = message.get("mid", "")

    # Pomijamy echa (wiadomości wysłane przez bota)
    if message.get("is_echo") or not text or not sender_id:
        return

    # Auto-odpowiedzi DM tylko z konta funlikehel — surf4hel jest tylko do publikacji
    dm_accounts = set(os.environ.get("DM_RESPONSE_ACCOUNTS", "funlikehel").split(","))
    if account not in dm_accounts:
        logger.info("Pomijam DM na @%s — konto nie ma włączonych auto-odpowiedzi DM", account)
        return

    # Pomijamy wiadomości od naszych własnych kont IG (anti-loop)
    from instagram import get_all_accounts
    own_ids = {a.ig_user_id for a in get_all_accounts() if a.ig_user_id}
    if sender_id in own_ids:
        logger.info("Pomijam DM od własnego konta IG (sender=%s) na @%s", sender_id, account)
        return

    # Deduplikacja (SQLite — przetrwa restart)
    if _is_seen(mid):
        logger.info("Pomijam duplikat DM: %s", mid[:30])
        return
    _mark_seen(mid, f"ig_dm_{account}")

    logger.info("DM od %s na @%s: %s", sender_id, account, text)

    try:
        reply = get_reply(text, sender_id=sender_id, channel=f"instagram_dm_{account}")
        await send_dm(sender_id, reply, account=account)
        logger.info("Odpowiedź DM wysłana do %s na @%s", sender_id, account)
        try:
            from google_mail import _sync_to_panel
            _sync_to_panel(sender_email=sender_id, sender_name=f"IG @{sender_id}", subject="Instagram DM", body=text, reply=reply, status="ai_handled")
        except: pass
    except Exception as e:
        logger.error("Błąd przy obsłudze DM na @%s: %s", account, e)


# ---------------------------------------------------------------------------
# Obsługa komentarzy
# ---------------------------------------------------------------------------


async def _handle_comment(value: dict, account: str = "funlikehel"):
    comment_id = value.get("id")
    text = value.get("text", "").strip()
    from_user = value.get("from", {})
    sender_id = from_user.get("id", "")
    sender_name = from_user.get("username", from_user.get("name", "użytkownik"))

    # Pomijamy komentarze od naszych własnych kont IG (anti-loop)
    from instagram import get_all_accounts
    own_ids = {a.ig_user_id for a in get_all_accounts() if a.ig_user_id}
    if sender_id in own_ids:
        logger.info("Pomijam komentarz od własnego konta IG (sender=%s) na @%s", sender_id, account)
        return

    if not comment_id or not text:
        return

    # Deduplikacja
    if _is_seen(comment_id):
        return
    _mark_seen(comment_id, f"ig_comment_{account}")

    # --- FILTR: kiedy odpowiadać ---
    should_reply = False
    reply_style = "standard"

    # 1. Pytanie od klienta → odpowiedz merytorycznie
    if "?" in text:
        should_reply = True
        reply_style = "answer"

    # 2. @wzmianka o funlikehel → odpowiedz
    elif "funlikehel" in text.lower():
        should_reply = True
        reply_style = "mention"

    # 3. Komplement / pochwała → krótkie podziękowanie
    elif any(w in text.lower() for w in ["super", "polecam", "rewelacja", "brawo", "wow",
                                          "great", "amazing", "awesome", "love", "best"]):
        should_reply = True
        reply_style = "thanks"

    # 4. Emotki → odpowiedz tą samą emotką + pozdrawiamy
    elif _is_emoji_only(text):
        should_reply = True
        reply_style = "emoji"

    # 5. Krótkie komentarze bez pytania → NIE odpowiadaj

    if not should_reply:
        logger.info("Komentarz od @%s: '%s' — pomijam (krótki/nieistotny)", sender_name, text[:50])
        return

    logger.info("Komentarz od @%s [%s]: %s", sender_name, reply_style, text[:80])

    try:
        if reply_style == "emoji":
            reply = f"{text} Pozdrawiamy, zapraszamy! 🤙"
        elif reply_style == "thanks":
            reply = "Dziękujemy! 🤙"
        else:
            reply = get_reply(text, sender_id=sender_id, channel=f"instagram_comment_{account}")
        await reply_to_comment(comment_id, reply, account=account)
        logger.info("Odpowiedź na komentarz @%s wysłana do @%s", account, sender_name)
    except Exception as e:
        logger.error("Błąd przy obsłudze komentarza na @%s: %s", account, e)


def _is_emoji_only(text: str) -> bool:
    """Sprawdza czy tekst zawiera tylko emotki, spacje i znaki interpunkcyjne."""
    for ch in text:
        if ch in " \t\n.,!":
            continue
        # Zwykłe znaki ASCII = nie emotka
        if ord(ch) < 127:
            return False
    return len(text.strip()) > 0


# ---------------------------------------------------------------------------
# Weryfikacja podpisu HMAC-SHA256
# ---------------------------------------------------------------------------

def _verify_signature(body: bytes, signature: str):
    secret = os.environ.get("META_APP_SECRET", "")
    if not secret:
        logger.info("META_APP_SECRET nie ustawiony — pomijam weryfikację podpisu.")
        return  # pomijamy w trybie dev jeśli secret nie ustawiony

    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"

    if not hmac.compare_digest(expected, signature):
        logger.warning("Podpis nie pasuje! Otrzymany: %s, Oczekiwany: %s — przepuszczam tymczasowo", signature[:30], expected[:30])
        return  # TODO: przywrócić raise po ustaleniu secretu


# ---------------------------------------------------------------------------
# Tymczasowy endpoint — instalacja pluginu WP z IP serwera (omija LLA lockout)
# USUŃ po zakończeniu operacji
# ---------------------------------------------------------------------------

_wp_install_log: list = []  # simple in-memory log for background task result


async def _do_wp_install(wp_url: str, wp_user: str, wp_pass: str, zip_url: str, wp_app_password: str) -> None:
    """Background task: install + activate WP plugin from ZIP via admin form."""
    import httpx, re, base64, traceback
    global _wp_install_log
    log: list = []
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            # Step 1: login
            r = await client.post(f"{wp_url}/wp-login.php", data={
                "log": wp_user, "pwd": wp_pass,
                "wp-submit": "Log In", "testcookie": "1", "redirect_to": "/wp-admin/",
            }, headers={"Cookie": "wordpress_test_cookie=WP+Cookie+check"})
            cookies = dict(client.cookies)
            logged_in = any("logged_in" in k for k in cookies)
            log.append(f"Login: {logged_in}, status={r.status_code}")
            if not logged_in:
                m = re.search(r'<div id="login_error"[^>]*>(.*?)</div>', r.text, re.DOTALL)
                log.append("Login error: " + (re.sub('<[^>]+>', '', m.group(1)).strip() if m else 'unknown'))
                _wp_install_log = log
                return

        # Step 2: nonce (new client to reuse cookies)
        async with httpx.AsyncClient(follow_redirects=True, timeout=30, cookies=cookies) as client2:
            r2 = await client2.get(f"{wp_url}/wp-admin/plugin-install.php?tab=upload")
            nm = re.search(r'name="_wpnonce" value="([a-f0-9]+)"', r2.text)
            if not nm:
                log.append(f"Nonce not found, status={r2.status_code}, body={r2.text[:300]}")
                _wp_install_log = log
                return
            nonce = nm.group(1)
            log.append(f"Nonce: {nonce}")

            # Step 3: download ZIP
            zip_resp = await client2.get(zip_url)
            if zip_resp.status_code != 200:
                log.append(f"ZIP download failed: {zip_resp.status_code}")
                _wp_install_log = log
                return
            log.append(f"ZIP: {len(zip_resp.content)} bytes")

            # Step 4: upload
            fname = zip_url.split("/")[-1]
            r3 = await client2.post(
                f"{wp_url}/wp-admin/update.php?action=upload-plugin",
                files={"pluginzip": (fname, zip_resp.content, "application/zip")},
                data={"_wpnonce": nonce, "install-plugin-submit": "Zainstaluj"},
            )
            t = r3.text.lower()
            log.append(f"Upload status={r3.status_code}")
            if any(x in t for x in ["successfully", "zainstalowana", "installed", "pomyslnie", "already", "istnieje", "replace"]):
                log.append("Install OK (or already exists)")
            else:
                log.append(f"Upload response fragment: {r3.text[500:1500]}")
                _wp_install_log = log
                return

            # Step 5: activate via REST
            if wp_app_password:
                auth = base64.b64encode(f"{wp_user}:{wp_app_password}".encode()).decode()
                r4 = await client2.put(
                    f"{wp_url}/?rest_route=/wp/v2/plugins/funlikehel-booking-v2%2Ffunlikehel-booking-v2",
                    headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
                    content=b'{"status":"active"}',
                )
                log.append(f"Activate: {r4.status_code} {r4.text[:200]}")
            else:
                log.append("Skipping activation: no wp_app_password")

        log.append("DONE")
    except Exception as exc:
        log.append(f"EXCEPTION: {exc}")
        log.append(traceback.format_exc())
    _wp_install_log = log


@app.post("/admin/wp-install-plugin")
async def wp_install_plugin(request: Request):
    """Instaluje plugin WP z ZIP URL — uruchamiany z IP Render (omija LLA lockout)."""
    import asyncio

    try:
        req_body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    token = req_body.get("token", "")
    admin_token = os.environ.get("BOOKING_ADMIN_TOKEN", "")
    if token != admin_token:
        raise HTTPException(status_code=403, detail="Brak dostępu")

    wp_url = req_body.get("wp_url", "https://funlikehel.pl")
    wp_user = req_body.get("wp_user", "Admin")
    wp_pass = req_body.get("wp_pass", "")
    zip_url = req_body.get("zip_url", "")
    wp_app_password = req_body.get("wp_app_password", "") or os.environ.get("WP_APP_PASSWORD", "")

    if not wp_pass or not zip_url:
        raise HTTPException(status_code=400, detail="Wymagane: wp_pass, zip_url")

    # Run as background task — returns immediately, check /admin/wp-install-log
    asyncio.create_task(_do_wp_install(wp_url, wp_user, wp_pass, zip_url, wp_app_password))
    return {"ok": True, "message": "Install started in background. Check /admin/wp-install-log in 30-60s."}


@app.get("/admin/wp-install-log")
async def wp_install_log(token: str = ""):
    """Wynik ostatniej instalacji pluginu WP."""
    admin_token = os.environ.get("BOOKING_ADMIN_TOKEN", "")
    if token != admin_token:
        raise HTTPException(status_code=403, detail="Brak dostępu")
    return {"log": _wp_install_log}


# ---------------------------------------------------------------------------
# Sklep — produkty z listings.db
# ---------------------------------------------------------------------------

@app.get("/shop/products")
async def get_shop_products():
    """Produkty z listings.db do wyswietlenia w FLH Panel (zakładka Sklep)."""
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "listings.db")
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Baza listings.db nie istnieje")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, product_id, full_name, category, product_type, size,
               quantity, retail_price, sale_price, purchase_price,
               image_file, status
        FROM listings
        ORDER BY id
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"products": rows}


# ---------------------------------------------------------------------------
# LinkedIn — SurfIQ Company Page
# ---------------------------------------------------------------------------

@app.get("/linkedin/login")
async def linkedin_login():
    """Otwórz ten URL w przeglądarce żeby autoryzować LinkedIn."""
    if not HAS_LINKEDIN:
        raise HTTPException(status_code=503, detail="Moduł LinkedIn niedostępny")
    return RedirectResponse(li_get_auth_url())


@app.get("/linkedin/callback")
async def linkedin_callback(code: str):
    """LinkedIn przekierowuje tutaj po autoryzacji OAuth2."""
    if not HAS_LINKEDIN:
        raise HTTPException(status_code=503, detail="Moduł LinkedIn niedostępny")
    token_data = li_exchange_code(code)
    if "access_token" in token_data:
        return HTMLResponse(f"""
        <html><body style="font-family:sans-serif;max-width:600px;margin:40px auto;text-align:center">
        <h1>LinkedIn Connected!</h1>
        <p>Token uzyskany pomyślnie. Wygasa za <b>{token_data.get('expires_in', 0) // 86400} dni</b>.</p>
        <p>Możesz teraz publikować posty: <code>python linkedin_agent.py post</code></p>
        <a href="/linkedin/dashboard">Dashboard</a>
        </body></html>""")
    return HTMLResponse(f"""
    <html><body style="font-family:sans-serif;max-width:600px;margin:40px auto;text-align:center">
    <h1>LinkedIn Error</h1>
    <pre>{json.dumps(token_data, indent=2)}</pre>
    <a href="/linkedin/login">Spróbuj ponownie</a>
    </body></html>""", status_code=400)


@app.get("/linkedin/status")
async def linkedin_status():
    """Status połączenia LinkedIn."""
    if not HAS_LINKEDIN:
        return {"status": "unavailable", "message": "Moduł LinkedIn niedostępny"}
    token = li_get_access_token()
    if not token:
        return {"status": "unauthorized", "message": "Otwórz /linkedin/login"}
    return {"status": "connected", "posts": li_list_posts()}


@app.post("/linkedin/post")
async def linkedin_post_next():
    """Publikuj następny post z kolejki."""
    if not HAS_LINKEDIN:
        raise HTTPException(status_code=503, detail="Moduł LinkedIn niedostępny")
    token = li_get_access_token()
    if not token:
        raise HTTPException(status_code=401, detail="Brak tokena LinkedIn. Otwórz /linkedin/login")
    agent = LinkedInAgent(token)
    result = li_publish_next(agent)
    if result is None:
        return {"message": "Wszystkie posty już opublikowane"}
    return result


@app.get("/linkedin/dashboard")
async def linkedin_dashboard():
    """Prosty dashboard LinkedIn — status postów i akcje."""
    if not HAS_LINKEDIN:
        raise HTTPException(status_code=503, detail="Moduł LinkedIn niedostępny")
    token = li_get_access_token()
    connected = bool(token)
    posts = li_list_posts() if connected else []

    posts_html = ""
    for p in posts:
        status_badge = (
            '<span style="color:#22c55e;font-weight:bold">PUBLISHED</span>'
            if p["status"] == "published"
            else '<span style="color:#f59e0b;font-weight:bold">PENDING</span>'
        )
        pub_info = f'<br><small>{p.get("published_at", "")}</small>' if p["status"] == "published" else ""
        posts_html += f"""
        <div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin:8px 0">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <strong>{p["title"]}</strong> {status_badge}
          </div>
          <p style="color:#6b7280;font-size:14px">{p["text_preview"]}</p>
          {pub_info}
        </div>"""

    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>LinkedIn — SurfIQ</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; }}
  .btn {{ display:inline-block; padding:10px 20px; border-radius:6px; text-decoration:none; font-weight:600; margin:4px; cursor:pointer; border:none; font-size:14px; }}
  .btn-primary {{ background:#0a66c2; color:white; }}
  .btn-outline {{ background:white; color:#0a66c2; border:2px solid #0a66c2; }}
  h1 {{ color:#0a66c2; }}
</style></head>
<body>
  <h1>LinkedIn — SurfIQ</h1>
  <div style="display:flex;align-items:center;gap:8px;margin:16px 0">
    <div style="width:12px;height:12px;border-radius:50%;background:{'#22c55e' if connected else '#ef4444'}"></div>
    <span>{'Connected' if connected else 'Not connected'}</span>
  </div>
  {"" if connected else '<a href="/linkedin/login" class="btn btn-primary">Connect LinkedIn</a>'}
  {"<button class='btn btn-primary' onclick='publishNext()'>Publish Next Post</button>" if connected else ""}
  <div id="result" style="margin:16px 0;display:none;padding:12px;border-radius:8px;background:#f0f9ff"></div>
  <h2>Posts ({len([p for p in posts if p['status'] == 'published'])}/{len(posts)} published)</h2>
  {posts_html}
  <script>
  async function publishNext() {{
    const el = document.getElementById('result');
    el.style.display = 'block';
    el.textContent = 'Publishing...';
    try {{
      const r = await fetch('/linkedin/post', {{ method: 'POST' }});
      const d = await r.json();
      el.innerHTML = '<pre>' + JSON.stringify(d, null, 2) + '</pre>';
      setTimeout(() => location.reload(), 2000);
    }} catch(e) {{ el.textContent = 'Error: ' + e.message; }}
  }}
  </script>
</body></html>""")


# ---------------------------------------------------------------------------
# SurfIQ Email Notification — SMTP via home.pl (office@surfiq.eu)
# ---------------------------------------------------------------------------

class SendNotificationRequest(BaseModel):
    to: str
    cc: str | None = None
    subject: str
    html: str


@app.post("/api/send-notification")
async def send_notification_email(req: SendNotificationRequest):
    """
    Send an email via SMTP (office@surfiq.eu → home.pl).
    Accepts JSON: { to, cc?, subject, html }
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    # Validate
    if not req.to or "@" not in req.to:
        raise HTTPException(400, "Invalid 'to' email address")
    if not req.subject:
        raise HTTPException(400, "Missing 'subject'")
    if not req.html:
        raise HTTPException(400, "Missing 'html' body")

    # SMTP config — office@surfiq.eu via home.pl
    smtp_host = os.getenv("SURFIQ_SMTP_HOST", "serwer2620595.home.pl")
    smtp_port = int(os.getenv("SURFIQ_SMTP_PORT", "587"))
    smtp_user = os.getenv("SURFIQ_SMTP_USER", "office@surfiq.eu")
    smtp_pass = os.getenv("SURFIQ_SMTP_PASS", "surfiq2026@")
    from_name = os.getenv("SURFIQ_FROM_NAME", "SurfIQ")
    from_addr = os.getenv("SURFIQ_FROM_ADDR", smtp_user)

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{from_name} <{from_addr}>"
    msg["To"] = req.to
    if req.cc:
        msg["Cc"] = req.cc
    msg["Subject"] = req.subject
    msg["Reply-To"] = from_addr

    # Attach HTML body (+ plain-text fallback)
    plain_text = req.subject  # minimal fallback
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(req.html, "html", "utf-8"))

    # Build recipient list
    recipients = [req.to]
    if req.cc:
        recipients.extend([addr.strip() for addr in req.cc.split(",") if addr.strip()])

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _smtp_send, smtp_host, smtp_port, smtp_user, smtp_pass, msg, recipients)
        logger.info("Notification email sent: to=%s cc=%s subject=%s", req.to, req.cc, req.subject)
        return {"ok": True, "to": req.to, "cc": req.cc, "subject": req.subject}
    except Exception as e:
        logger.error("Notification email FAILED: to=%s error=%s", req.to, e)
        raise HTTPException(500, f"SMTP error: {e}")


def _smtp_send(host: str, port: int, user: str, password: str, msg, recipients: list[str]):
    """Blocking SMTP send — runs in executor."""
    import smtplib
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg, to_addrs=recipients)


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
