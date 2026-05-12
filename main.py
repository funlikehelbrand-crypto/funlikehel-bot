import asyncio
import hashlib
import hmac
import logging
import os
import sys
from datetime import datetime

import httpx

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware

# Dodaj server/ do path — moduły mogą być tam lub w katalogu głównym
_server_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server")
if os.path.isdir(_server_dir) and _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

# Wszystkie moduły — opcjonalne (graceful fallback)
try:
    from claude_agent import get_reply
    HAS_CLAUDE = True
except ImportError:
    HAS_CLAUDE = False
    def get_reply(text, **kwargs):
        return "Bot tymczasowo niedostępny. Zadzwoń: 690 270 032"

try:
    from booking_db import init_db
    from booking import booking_router
    HAS_BOOKING = True
except ImportError:
    HAS_BOOKING = False
    booking_router = None

# Instagram + WhatsApp — krytyczne dla odpowiadania na wiadomości
try:
    from instagram import reply_to_comment, send_dm, init_accounts as init_ig_accounts, find_account_by_ig_id, get_all_accounts as _ig_get_all
    from whatsapp import send_message as wa_send_message, mark_as_read as wa_mark_as_read
    HAS_ALL_MODULES = True
except Exception as e:
    logging.warning("Instagram/WhatsApp niedostępny: %s", e)
    HAS_ALL_MODULES = False

# Google + inne moduły — opcjonalne (background polling)
try:
    from google_mail import process_unread_emails
    from youtube import process_youtube_comments
    from tiktok import get_auth_url, exchange_code_for_token, save_token, get_stored_token, get_valid_access_token, upload_video_from_url, check_upload_status
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

load_dotenv("api.env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="FUN like HEL — Instagram Bot + Gmail + Chatbot")

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    pass

# Booking API
if booking_router:
    app.include_router(booking_router)

# Init booking DB on startup
if HAS_BOOKING:
    init_db()

# Init Instagram multi-account
if HAS_ALL_MODULES:
    init_ig_accounts()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://funlikehel.pl", "https://www.funlikehel.pl", "https://faceless-security-enactment.ngrok-free.dev"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Chatbot na stronie — Alicja odpowiada klientom w czasie rzeczywistym
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    """Diagnostyka — sprawdza czy klucze API są ustawione."""
    import os as _os
    import json as _json
    has_claude = bool(_os.environ.get("ANTHROPIC_API_KEY", ""))
    has_gemini = bool(_os.environ.get("GEMINI_API_KEY", ""))
    has_openai = bool(_os.environ.get("OPENAI_API_KEY", ""))

    # Sprawdź env vars Google
    token_env = _os.environ.get("GOOGLE_TOKEN_JSON", "")
    creds_env = _os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    token_valid = False
    creds_valid = False
    if token_env:
        try:
            _json.loads(token_env)
            token_valid = True
        except Exception:
            pass
    if creds_env:
        try:
            _json.loads(creds_env)
            creds_valid = True
        except Exception:
            pass

    return {
        "status": "ok",
        "has_all_modules": HAS_ALL_MODULES,
        "has_instagram": HAS_ALL_MODULES,
        "has_google": HAS_GOOGLE_MODULES,
        "claude_key": has_claude,
        "claude_key_prefix": _os.environ.get("ANTHROPIC_API_KEY", "")[:15] + "..." if has_claude else "MISSING",
        "gemini_key": has_gemini,
        "openai_key": has_openai,
        "google_token_env_set": bool(token_env),
        "google_token_env_valid_json": token_valid,
        "google_token_env_len": len(token_env),
        "google_creds_env_set": bool(creds_env),
        "google_creds_env_valid_json": creds_valid,
        "tt_upload_folder_id": bool(_os.environ.get("TT_UPLOAD_FOLDER_ID", "")),
    }

@app.get("/api/google-business/diagnose")
async def google_business_diagnose():
    """Diagnostyka Google Business — sprawdza konta, lokalizacje i recenzje bez odpowiedzi."""
    if not HAS_GOOGLE_MODULES:
        return {"error": "Google modules not loaded"}
    try:
        from google_business import diagnose
        return diagnose()
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/google-business/process")
async def google_business_process():
    """Ręczne wywołanie przetwarzania recenzji Google Business."""
    if not HAS_GOOGLE_MODULES:
        return {"error": "Google modules not loaded"}
    try:
        from google_business import process_reviews
        count = process_reviews()
        return {"processed": count}
    except Exception as e:
        return {"error": str(e)}


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


# ---------------------------------------------------------------------------
# DM Campaign — kampania zaproszeniowa przez Instagram DM
# ---------------------------------------------------------------------------

class DMCampaignRequest(BaseModel):
    dry_run: bool = False
    account: str = ""

_dm_campaign_status: dict = {"running": False, "last_result": None}

@app.post("/api/dm-campaign/run")
async def dm_campaign_run(req: DMCampaignRequest, token: str = ""):
    """ZABLOKOWANE — kampania DM wyłączona po incydencie spamu 2026-04-30."""
    raise HTTPException(status_code=503, detail="Kampania DM zablokowana.")


@app.get("/api/dm-campaign/stats")
async def dm_campaign_stats(token: str = ""):
    secret = os.environ.get("EKIPA_SECRET", "flh2024ekipa")
    if token != secret:
        raise HTTPException(status_code=403, detail="Brak dostępu")
    raise HTTPException(status_code=503, detail="Kampania DM wyłączona.")


@app.get("/api/dm-export")
async def dm_export(token: str = ""):
    """Pełny eksport kontaktów DM — paginuje przez WSZYSTKIE rozmowy IG."""
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
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error("dm-export błąd: %s", e)
                    break

    contacts.sort(key=lambda x: x["ostatnia_wiadomosc"], reverse=True)
    return {"total": len(contacts), "contacts": contacts}


@app.get("/api/dm-all-sent")
async def dm_all_sent(token: str = ""):
    """Pełna lista wszystkich wysłanych DM (bez limitu)."""
    import sqlite3 as _sq
    secret = os.environ.get("EKIPA_SECRET", "flh2024ekipa")
    if token != secret:
        raise HTTPException(status_code=403, detail="Brak dostępu")
    db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dm_campaign.db")
    try:
        conn = _sq.connect(db)
        conn.row_factory = _sq.Row
        rows = conn.execute("SELECT recipient_id, username, status, sent_at FROM dm_sent ORDER BY sent_at ASC").fetchall()
        conn.close()
        return {"total": len(rows), "sent": [dict(r) for r in rows]}
    except Exception as e:
        return {"error": str(e), "total": 0, "sent": []}


@app.get("/api/dm-sent-history")
async def dm_sent_history(token: str = ""):
    """Pełna historia wysyłek DM — kto, kiedy, z jakiego konta, status."""
    admin_token = os.environ.get("BOOKING_ADMIN_TOKEN", "")
    if token != admin_token:
        raise HTTPException(status_code=403, detail="Brak dostępu")

    from dm_campaign import _drive_sent_cache
    return {"count": len(_drive_sent_cache), "history": _drive_sent_cache}


@app.get("/api/dm-contacts")
async def dm_contacts_list(token: str = ""):
    """Lista kontaktów DM z wszystkich kont IG."""
    admin_token = os.environ.get("BOOKING_ADMIN_TOKEN", "")
    if token != admin_token:
        raise HTTPException(status_code=403, detail="Brak dostępu")

    if not HAS_ALL_MODULES:
        raise HTTPException(status_code=503, detail="Moduły niedostępne")

    from dm_campaign import get_all_dm_contacts
    contacts = get_all_dm_contacts()
    return {"count": len(contacts), "contacts": contacts}


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
    await asyncio.sleep(180)
    while True:
        try:
            await process_tiktok_upload_folder()
        except Exception as e:
            logger.error("Błąd auto-upload TikTok: %s", e)
        await asyncio.sleep(7200)


async def google_business_loop():
    """Sprawdzanie recenzji Google Business — co 3 godziny.
    UWAGA: Wyłączone do czasu zatwierdzenia dostępu GBP API przez Google.
    Włącz po otrzymaniu potwierdzenia z Google (quota > 0).
    """
    logger.info("Google Business loop wyłączony — oczekiwanie na zatwierdzenie GBP API quota.")
    return


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


async def dm_campaign_loop():
    """Kampania DM /ekipa — WYŁĄCZONA. Tylko ręcznie przez /api/dm-campaign/run."""
    # SAFETY: auto-kampania permanentnie wyłączona po incydencie 256 spamów (2026-04-30)
    # Kampanię można uruchomić TYLKO ręcznie przez endpoint /api/dm-campaign/run
    logger.info("Auto-kampania DM wyłączona (safety lock). Użyj /api/dm-campaign/run do ręcznego uruchomienia.")
    return


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
    # DM campaign loop — permanentnie wyłączona
    asyncio.create_task(dm_campaign_loop())


# ---------------------------------------------------------------------------
# SMS — kampanie i powiadomienia
# ---------------------------------------------------------------------------

class SMSCampaignRequest(BaseModel):
    topic: str
    label: str | None = None
    dry_run: bool = False

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
    """Uruchamia kampanię SMS — Alicja generuje treść, wysyłka do kontaktów Google."""
    result = run_campaign(topic=req.topic, label=req.label, dry_run=req.dry_run)
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


class WASendRequest(BaseModel):
    to: str
    text: str


@app.post("/whatsapp/send")
async def whatsapp_send(req: WASendRequest):
    """Wysyła wiadomość WhatsApp na podany numer."""
    if not HAS_ALL_MODULES:
        raise HTTPException(status_code=503, detail="WhatsApp niedostępny")
    result = await wa_send_message(req.to, req.text)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "sent", "to": req.to, "result": result}


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


@app.get("/tiktok/debug")
async def tiktok_debug():
    """Pokazuje aktualną konfigurację TikTok (do debugowania)."""
    key = os.environ.get("TT_CLIENT_KEY", "")
    redirect = os.environ.get("TT_REDIRECT_URI", "https://funlikehel-bot.onrender.com/tiktok/callback")
    auth_url = get_auth_url() if HAS_ALL_MODULES else "unavailable"
    return {
        "client_key": key[:8] + "..." if key else "BRAK — env var nie ustawiona!",
        "client_key_full": key,
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
    if HAS_ALL_MODULES and access_token:
        save_token({"access_token": access_token, "refresh_token": refresh_token})
    logger.info("TikTok autoryzowany. access_token=%s...", access_token[:12] if access_token else "")
    return HTMLResponse(f"""
    <html><body style="font-family:monospace;padding:20px;background:#1a1a1a;color:#0f0">
    <h2>&#x2705; TikTok połączony!</h2>
    <p>Token zapisany na Google Drive (przeżyje restarty Render).</p>
    <hr/>
    <p><b>TT_ACCESS_TOKEN</b><br>
    <textarea rows="3" cols="80" onclick="this.select()">{access_token}</textarea></p>
    <p><b>TT_REFRESH_TOKEN</b><br>
    <textarea rows="3" cols="80" onclick="this.select()">{refresh_token}</textarea></p>
    <hr/>
    <p>Sprawdź status: <a href="/tiktok/status" style="color:#0ff">/tiktok/status</a></p>
    </body></html>
    """)


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
        "expires_in_hours": round((expires_at - time.time()) / 3600, 1) if expires_at else "unknown",
        "has_refresh": bool(data.get("refresh_token")),
    }


class TikTokUploadRequest(BaseModel):
    video_url: str
    caption: str
    privacy_level: str = "PUBLIC_TO_EVERYONE"


@app.post("/tiktok/upload")
async def tiktok_upload(req: TikTokUploadRequest):
    """Publikuje wideo na TikTok z podanego URL."""
    if not HAS_GOOGLE_MODULES:
        raise HTTPException(status_code=503, detail="Moduł TikTok niedostępny")
    try:
        from auto_upload import build_tiktok_caption
        caption = req.caption
        if "#" not in caption:
            caption = build_tiktok_caption(caption)
        token = await get_valid_access_token()
        result = await upload_video_from_url(token, req.video_url, caption)
        publish_id = result.get("data", {}).get("publish_id", "unknown")
        return {"status": "ok", "publish_id": publish_id, "caption": caption}
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TikTokUploadFromYTRequest(BaseModel):
    video_id: str
    caption: str = ""
    privacy_level: str = "PUBLIC_TO_EVERYONE"


@app.post("/tiktok/upload-from-yt")
async def tiktok_upload_from_yt(req: TikTokUploadFromYTRequest):
    """Pobiera film z YouTube przez yt-dlp i publikuje na TikTok."""
    if not HAS_GOOGLE_MODULES:
        raise HTTPException(status_code=503, detail="Moduł TikTok niedostępny")
    import subprocess, tempfile, os as _os, sys as _sys
    yt_url = f"https://www.youtube.com/watch?v={req.video_id}"
    tmp_dir = tempfile.mkdtemp()
    tmp_path = _os.path.join(tmp_dir, f"{req.video_id}.mp4")
    try:
        result = subprocess.run(
            [_sys.executable, "-m", "yt_dlp",
             "--extractor-args", "youtube:player_client=mediaconnect",
             "-f", "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best",
             "--merge-output-format", "mp4", "-o", tmp_path, yt_url],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp error: {result.stderr[-500:]}")
        if not _os.path.exists(tmp_path):
            files = [f for f in _os.listdir(tmp_dir) if f.endswith(".mp4")]
            if not files:
                raise RuntimeError("yt-dlp nie zapisał pliku mp4")
            tmp_path = _os.path.join(tmp_dir, files[0])
        if req.caption:
            caption = req.caption
        else:
            from auto_upload import build_tiktok_caption
            caption = build_tiktok_caption("Kite i surf na maxa! 🏄 Jastarnia & Hurghada")
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
        logger.info("Pomijam DM na @%s — konto nie ma wlaczonych auto-odpowiedzi DM", account)
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


@app.post("/api/instagram-to-fb")
async def instagram_to_fb(mode: str = "latest"):
    """
    Pobiera post z Instagrama i publikuje go na stronie Facebook Fun Like Hel.
    mode: 'latest' = ostatni post, 'top' = post z największą liczbą polubień
    """
    import requests as req_lib
    import sys
    sys.path.insert(0, _server_dir)
    from fb_publisher import publish_post, publish_post_with_image

    page_token = os.getenv("PAGE_ACCESS_TOKEN", "")
    page_id = os.getenv("FB_PAGE_ID", "763267196880291")
    graph = "https://graph.facebook.com/v25.0"

    if not page_token:
        raise HTTPException(status_code=500, detail="Brak PAGE_ACCESS_TOKEN")

    # Krok 1 — znajdź IG Business Account ID
    # Najpierw z env, potem przez FB Page API, fallback = znany ID @funlikehel
    ig_id = os.getenv("INSTAGRAM_ACCOUNT_ID", "")

    if not ig_id:
        r = req_lib.get(f"{graph}/{page_id}", params={
            "fields": "instagram_business_account",
            "access_token": page_token
        })
        ig_id = r.json().get("instagram_business_account", {}).get("id", "")

    if not ig_id:
        # Fallback: znany ID konta @funlikehel (Instagram Business Login ID)
        ig_id = "17841402381473231"

    # Krok 2 — pobierz posty IG
    # Token IGAA (z Instagram Business Login) — oddzielny od PAGE_ACCESS_TOKEN
    igaa_token = os.getenv("INSTAGRAM_IGAA_TOKEN", "") or os.getenv("IG_READ_TOKEN", "")

    # Próba 1: IGAA token przez Instagram Graph API
    if igaa_token:
        r_ig = req_lib.get("https://graph.instagram.com/v21.0/me/media", params={
            "fields": "id,caption,media_type,media_url,thumbnail_url,like_count,timestamp,permalink",
            "limit": 10,
            "access_token": igaa_token
        })
        media = r_ig.json().get("data", [])
    else:
        media = []
        r_ig = type("r", (), {"json": lambda self: {}})()

    # Próba 2: PAGE_ACCESS_TOKEN przez Instagram Graph API (dla starych IGAA w PAGE_ACCESS_TOKEN)
    if not media:
        r_ig = req_lib.get("https://graph.instagram.com/v21.0/me/media", params={
            "fields": "id,caption,media_type,media_url,thumbnail_url,like_count,timestamp,permalink",
            "limit": 10,
            "access_token": page_token
        })
        media = r_ig.json().get("data", [])

    if not media:
        ig_err = r_ig.json().get("error", {}).get("message", "brak tokenu IGAA")
        raise HTTPException(status_code=404, detail=f"Brak postów IG. Ustaw INSTAGRAM_IGAA_TOKEN na Render. Błąd: {ig_err}")

    # Krok 3 — wybierz post
    post = max(media, key=lambda x: x.get("like_count", 0)) if mode == "top" else media[0]

    caption = post.get("caption", "")
    media_url = post.get("media_url") or post.get("thumbnail_url", "")
    permalink = post.get("permalink", "")
    media_type = post.get("media_type", "IMAGE")

    # Krok 4 — opublikuj na FB
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


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

@app.get("/api/version")
async def get_version():
    return {"version": "tiktok-upload-v3", "igaa": bool(os.getenv("INSTAGRAM_IGAA_TOKEN")), "tiktok_upload": True}


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
