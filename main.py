import asyncio
import hashlib
import hmac
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware

# Core - zawsze wymagane
from claude_agent import get_reply

# Opcjonalne moduły - mogą nie działać bez credentials/kluczy na serwerze
try:
    from instagram import reply_to_comment, send_dm
    from google_mail import process_unread_emails
    from youtube import process_youtube_comments
    from tiktok import get_auth_url, exchange_code_for_token
    from cleanup_mail import daily_cleanup, trash_cleanup
    from google_business import process_reviews
    from auto_upload import process_upload_folder
    from sms_campaign import run_campaign, send_reminder, send_notification
    from google_contacts import get_contacts_with_phones
    HAS_ALL_MODULES = True
except Exception as e:
    logging.warning("Niektóre moduły niedostępne (brak credentials): %s", e)
    HAS_ALL_MODULES = False

load_dotenv("api.env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="FUN like HEL — Instagram Bot + Gmail + Chatbot")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://funlikehel.pl", "https://www.funlikehel.pl", "https://faceless-security-enactment.ngrok-free.dev"],
    allow_methods=["POST"],
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
    import sqlite3
    import datetime

    db = sqlite3.connect("ekipa.db")
    db.execute("""CREATE TABLE IF NOT EXISTS ekipa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT, phone TEXT, sport TEXT, locations TEXT,
        created_at TEXT
    )""")
    db.execute(
        "INSERT INTO ekipa (name, email, phone, sport, locations, created_at) VALUES (?,?,?,?,?,?)",
        (req.name, req.email, req.phone or "", req.sport or "", ",".join(req.locations), datetime.datetime.now().isoformat())
    )
    db.commit()
    db.close()

    logger.info("Nowy zapis do ekipy: %s | %s | %s | %s", req.name, req.email, req.sport, req.locations)
    return {"status": "ok", "message": f"Cześć {req.name}! Jesteś w ekipie! 🤙"}


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
        await asyncio.sleep(300)  # 5 minut


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


@app.on_event("startup")
async def startup_event():
    if HAS_ALL_MODULES:
        asyncio.create_task(gmail_polling_loop())
        asyncio.create_task(youtube_polling_loop())
        asyncio.create_task(daily_cleanup_loop())
        asyncio.create_task(trash_cleanup_loop())
        asyncio.create_task(google_business_loop())
        asyncio.create_task(auto_upload_loop())
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


# ---------------------------------------------------------------------------
# Strony prawne (regulamin, polityka prywatności)
# ---------------------------------------------------------------------------

@app.get("/regulamin", response_class=HTMLResponse)
async def regulamin():
    with open("../regulamin.html", encoding="utf-8") as f:
        return f.read()

@app.get("/polityka-prywatnosci", response_class=HTMLResponse)
async def polityka():
    with open("../polityka-prywatnosci.html", encoding="utf-8") as f:
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
# Odbiór zdarzeń z Instagrama
# ---------------------------------------------------------------------------

@app.post("/webhook")
async def receive_event(request: Request):
    # Weryfikacja podpisu Meta (bezpieczeństwo)
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()
    _verify_signature(body, signature)

    payload = await request.json()
    logger.info("Zdarzenie: %s", payload)

    for entry in payload.get("entry", []):
        # --- Wiadomości DM ---
        for messaging in entry.get("messaging", []):
            await _handle_dm(messaging)

        # --- Komentarze pod postami ---
        for change in entry.get("changes", []):
            if change.get("field") == "comments":
                await _handle_comment(change["value"])

    return Response(status_code=200)


# ---------------------------------------------------------------------------
# Obsługa wiadomości DM
# ---------------------------------------------------------------------------

async def _handle_dm(messaging: dict):
    sender_id = messaging.get("sender", {}).get("id")
    message = messaging.get("message", {})
    text = message.get("text")

    # Pomijamy echa (wiadomości wysłane przez bota)
    if message.get("is_echo") or not text or not sender_id:
        return

    logger.info("DM od %s: %s", sender_id, text)

    try:
        reply = get_reply(text, sender_id=sender_id, channel="instagram_dm")
        await send_dm(sender_id, reply)
        logger.info("Odpowiedź DM wysłana do %s", sender_id)
    except Exception as e:
        logger.error("Błąd przy obsłudze DM: %s", e)


# ---------------------------------------------------------------------------
# Obsługa komentarzy
# ---------------------------------------------------------------------------

async def _handle_comment(value: dict):
    comment_id = value.get("id")
    text = value.get("text")
    from_user = value.get("from", {})
    sender_name = from_user.get("name", "użytkownik")

    # Pomijamy komentarze od siebie (żeby nie odpowiadać na własne odpowiedzi)
    if value.get("from", {}).get("id") == value.get("media", {}).get("owner_id"):
        return

    if not comment_id or not text:
        return

    logger.info("Komentarz od %s: %s", sender_name, text)

    try:
        sender_ig = from_user.get("id", sender_name)
        reply = get_reply(text, sender_id=sender_ig, channel="instagram_comment")
        await reply_to_comment(comment_id, reply)
        logger.info("Odpowiedź na komentarz wysłana.")
    except Exception as e:
        logger.error("Błąd przy obsłudze komentarza: %s", e)


# ---------------------------------------------------------------------------
# Weryfikacja podpisu HMAC-SHA256
# ---------------------------------------------------------------------------

def _verify_signature(body: bytes, signature: str):
    secret = os.environ.get("META_APP_SECRET", "")
    if not secret:
        return  # pomijamy w trybie dev jeśli secret nie ustawiony

    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="Nieprawidłowy podpis.")


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
