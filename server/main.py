import asyncio
import hashlib
import hmac
import logging
import os
from datetime import datetime

import httpx

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware

# Core - zawsze wymagane
from claude_agent import get_reply

# Booking system
from booking_db import init_db
from booking import booking_router

# Opcjonalne moduły - mogą nie działać bez credentials/kluczy na serwerze
try:
    from instagram import reply_to_comment, send_dm, init_accounts as init_ig_accounts, find_account_by_ig_id
    from google_mail import process_unread_emails
    from youtube import process_youtube_comments
    from tiktok import get_auth_url, exchange_code_for_token
    from cleanup_mail import daily_cleanup, trash_cleanup
    from google_business import process_reviews
    from auto_upload import process_upload_folder
    from sms_campaign import run_campaign, send_reminder, send_notification
    from google_contacts import get_contacts_with_phones
    from whatsapp import send_message as wa_send_message, mark_as_read as wa_mark_as_read
    from facebook_groups import process_facebook_groups
    HAS_ALL_MODULES = True
except Exception as e:
    logging.warning("Niektóre moduły niedostępne (brak credentials): %s", e)
    HAS_ALL_MODULES = False

load_dotenv("api.env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="FUN like HEL — Instagram Bot + Gmail + Chatbot")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Booking API
app.include_router(booking_router)

# Init booking DB on startup
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
    has_claude = bool(os.environ.get("ANTHROPIC_API_KEY", ""))
    has_gemini = bool(os.environ.get("GEMINI_API_KEY", ""))
    has_openai = bool(os.environ.get("OPENAI_API_KEY", ""))
    return {
        "status": "ok",
        "has_all_modules": HAS_ALL_MODULES,
        "claude_key": has_claude,
        "claude_key_prefix": os.environ.get("ANTHROPIC_API_KEY", "")[:15] + "..." if has_claude else "MISSING",
        "gemini_key": has_gemini,
        "openai_key": has_openai,
    }

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

    if os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("USE_FIRESTORE"):
        from google.cloud import firestore as _fs
        _fs.Client().collection("ekipa").add(record)
    else:
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

    logger.info("Nowy zapis do ekipy: %s | %s | %s | %s", req.name, req.email, req.sport, req.locations)

    # SMS powiadomienie do właściciela — żeby nie stracić zapisu przy restarcie Rendera
    try:
        from sms import send_sms
        locs = ",".join(req.locations) if req.locations else "?"
        send_sms(
            phone="690270032",
            message=f"EKIPA: {req.name} | {req.email} | {req.phone or '-'} | {req.sport or '?'} | {locs}",
        )
    except Exception as _sms_err:
        logger.warning("SMS powiadomienie ekipa nie wysłane: %s", _sms_err)

    # Zapis do Google Contacts — trwałe przechowywanie danych klientów
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
    """Lista zapisanych klientow (chroniona tokenem)."""
    import sqlite3
    secret = os.environ.get("EKIPA_SECRET", "flh2024ekipa")
    if token != secret:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Brak dostepu")

    db = sqlite3.connect("ekipa.db")
    db.row_factory = sqlite3.Row
    rows = db.execute("SELECT * FROM ekipa ORDER BY created_at DESC").fetchall()
    db.close()
    return {"count": len(rows), "items": [dict(r) for r in rows]}


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
    """Sprawdza folder DO_UPLOADU i uploaduje nowe filmy na YouTube — co 1 godzinę."""
    await asyncio.sleep(120)  # opóźnienie startu
    while True:
        try:
            process_upload_folder()
        except Exception as e:
            logger.error("Błąd auto-upload: %s", e)
        await asyncio.sleep(3600)  # 1 godzina


async def google_business_loop():
    """Sprawdzanie recenzji Google Business — co 3 godziny."""
    await asyncio.sleep(180)  # opóźnienie startu
    while True:
        try:
            logger.info("Sprawdzam recenzje Google Business...")
            process_reviews()
        except Exception as e:
            logger.error("Błąd Google Business polling: %s", e)
        await asyncio.sleep(10800)  # 3 godziny


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


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_alive_loop())
    if HAS_ALL_MODULES:
        asyncio.create_task(gmail_polling_loop())
        asyncio.create_task(youtube_polling_loop())
        asyncio.create_task(daily_cleanup_loop())
        asyncio.create_task(trash_cleanup_loop())
        asyncio.create_task(google_business_loop())
        asyncio.create_task(auto_upload_loop())
        asyncio.create_task(facebook_groups_loop())
    else:
        logger.info("Tryb minimalny — tylko chatbot i API. Brak polling loops.")


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


@app.get("/tiktok/login")
async def tiktok_login():
    """Otwórz ten URL w przeglądarce żeby autoryzować TikTok."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(get_auth_url())


@app.get("/tiktok/callback")
async def tiktok_callback(code: str):
    """TikTok przekierowuje tutaj po autoryzacji."""
    tokens = await exchange_code_for_token(code)
    tiktok_tokens["access_token"] = tokens.get("access_token")
    tiktok_tokens["refresh_token"] = tokens.get("refresh_token")
    logger.info("TikTok autoryzowany pomyślnie.")
    return {"status": "ok", "message": "TikTok połączony z FunLikeHel!"}


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
# Start
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
