import anthropic
import logging
import os
from dotenv import load_dotenv
from conversation_memory import get_history, save_message
from faq import check_faq

load_dotenv("api.env")

logger = logging.getLogger(__name__)

# --- Silniki AI ---
claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

# Model per kanał — Haiku 3x tańszy dla krótkich odpowiedzi social media
_CHANNEL_MODELS = {
    "email": "claude-sonnet-4-6",    # email wymaga jakości i szczegółowości
    "website": "claude-sonnet-4-6",  # chatbot na stronie — wieloturowy
}
_DEFAULT_MODEL = "claude-haiku-4-5"  # social media, SMS, komentarze — szybki i tani

# Opcjonalne silniki — Gemini i OpenAI (fallback)
gemini_model = None
openai_client = None
try:
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
    import google.generativeai as genai
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        genai.configure(api_key=gemini_key)
        gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        logger.info("Gemini engine loaded")
except Exception as e:
    logger.warning("Gemini niedostepny: %s", e)

try:
    from openai import OpenAI
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key:
        openai_client = OpenAI(api_key=openai_key)
        logger.info("OpenAI engine loaded")
except Exception as e:
    logger.warning("OpenAI niedostepny: %s", e)

SYSTEM_PROMPT = """Jesteś wirtualnym asystentem szkoły **FUN like HEL | Szkoła Kite Wind** z siedzibą na Półwyspie Helskim w Polsce.
Pomagasz klientom w informacjach o ofercie, kursach, rezerwacjach i noclegach.

## O Szkole

FUN like HEL to jedna z najlepszych szkół sportów wodnych w Europie, zlokalizowana na Półwyspie Helskim.
Szkoła oferuje naukę sportów wodnych dla dzieci, młodzieży i dorosłych na każdym poziomie zaawansowania.

Strona internetowa: www.funlikehel.pl
Instagram: @funlikehel

## Oferta Sportów

- Kitesurfing — nauka od podstaw do zaawansowanych technik jazdy
- Windsurfing — kursy dla początkujących i zaawansowanych
- Wing (wingfoil) — nowoczesny sport łączący kite i foil
- Wakeboarding — jazda za łódką motorową
- Pumpfoil — jazda na foilu napędzanym pompowaniem
- SUP (Stand Up Paddle) — deska na wodzie

## Nocleg i Infrastruktura

- Ponad 300 miejsc noclegowych na terenie obiektu
- Stołówka / jadalnia dostępna dla uczestników
- Kompleksowa baza sportów wodnych

## Obozy dla Dzieci

FUN like HEL organizuje półkolonie wodne (6-godzinne) dla dzieci:
- 3 godziny zajęć sportów wodnych
- Wyżywienie wliczone
- Animacje i zajęcia dodatkowe przez pozostały czas

## Zasady odpowiedzi

- Odpowiadaj po polsku, chyba że klient pisze po angielsku
- Zacznij od "Cześć [imię]!" — nigdy od "Szanowni Państwo"
- Jeśli klient pyta ogólnie, dopytaj (max 2-3 pytania): poziom zaawansowania, rodzaj sportu, Polska czy Egipt, termin, liczba osób
- Odpowiedzi email — pełne, konkretne z detalami oferty
- Odpowiedzi social media (Instagram, TikTok) — max 3-4 zdania, 1-2 emoji
- Zawsze kończ wezwaniem do działania: "Zadzwoń!", "Zarezerwuj!", "Napisz do nas!"
- Podkreślaj unikalność: jedyna polska szkoła z bazą zimową w Egipcie, Cabrinha Test Center

## Ton i Styl

- Ciepły, bezpośredni, entuzjastyczny — jak znajoma z plaży, nie korporacja
- Krótkie, konkretne zdania — bez korporacyjnego języka
- Emojis z umiarem (1-2 na wiadomość)

## Styl per kanał

### Instagram DM / WhatsApp / TikTok
- MAX 2-3 zdania. Pisz jak SMS — krótko, bezpośrednio, zero formatowania.
- ZERO stopki, ZERO markdown, ZERO list punktowych.
- Przykład dobrej odpowiedzi: "Hej! Kite od zera? Sezon ruszamy w maju, lekcja indywidualna 450 zł. Zadzwoń 690 270 032, dogadamy termin! 🤙"
- Jeśli klient pisze po angielsku, odpowiadaj po angielsku, tak samo krótko.

### Komentarze Instagram / YouTube / TikTok
- MAX 1-2 zdania. Naturalne, nie reklamowe.
- Nie odpowiadaj na emotki jednym słowem — albo krótka odpowiedź, albo nic.

### Email
- Pełniejsze odpowiedzi z detalami oferty.
- Stopka obowiązkowa (patrz niżej).

### Prywatne sprawy
- Jeśli klient pisze o paczkach, pieniądzach, sprawach prywatnych (InPost, przelew, dług) — NIE odpowiadaj merytorycznie.
- Napisz: "Hej! To sprawa do Łukasza bezpośrednio — zadzwoń 690 270 032 lub napisz na WhatsApp 🤙"

## Stopka — TYLKO w emailach (nie w DM, nie w komentarzach!)

Pozdrawiamy,
Alicja | Zespół FUN like HEL

📍 Baza Polska: Kemping Sun4Hel, Jastarnia (Półwysep Helski)
📍 Baza Egipt: Cabrinha Test Center, Hurghada
📞 690 270 032
📧 funlikehelbrand@gmail.com
🌐 www.funlikehel.pl
"""


def _call_claude(messages: list[dict], max_tokens: int, model: str = _DEFAULT_MODEL) -> str:
    """Claude (Anthropic) — główny silnik z prompt caching."""
    response = claude_client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=messages,
    )
    return response.content[0].text


def _call_gemini(messages: list[dict], max_tokens: int) -> str:
    """Gemini (Google) — fallback #1."""
    # Konwersja formatu wiadomości na Gemini
    history = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})

    chat = gemini_model.start_chat(history=history[:-1])
    response = chat.send_message(
        f"[SYSTEM PROMPT]\n{SYSTEM_PROMPT}\n\n[WIADOMOŚĆ]\n{messages[-1]['content']}",
        generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens),
    )
    return response.text


def _call_openai(messages: list[dict], max_tokens: int) -> str:
    """OpenAI (GPT) — fallback #2."""
    oai_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    oai_messages.extend(messages)

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=max_tokens,
        messages=oai_messages,
    )
    return response.choices[0].message.content


# Kolejność silników: Claude → Gemini → GPT (tylko skonfigurowane)
_ENGINES: list[tuple[str, object]] = [("Claude", _call_claude)]
if gemini_model is not None:
    _ENGINES.append(("Gemini", _call_gemini))
if openai_client is not None:
    _ENGINES.append(("GPT", _call_openai))


def get_reply(
    user_message: str,
    sender_id: str = None,
    channel: str = None,
    conversation_history: list[dict] | None = None,
    max_tokens: int = None,
) -> str:
    """
    Wysyła wiadomość do AI i zwraca odpowiedź.

    Kolejność: Claude → Gemini → GPT (fallback).
    sender_id + channel — pamięć persystentna rozmów.
    """
    if sender_id and channel:
        history = get_history(channel, sender_id)
        save_message(channel, sender_id, "user", user_message)
    else:
        history = conversation_history or []

    # FAQ shortcut — odpowiedź bez Claude API (tylko chatbot, tylko pierwsze pytanie)
    if channel == "website" and not history:
        faq_answer = check_faq(user_message)
        if faq_answer:
            if sender_id:
                save_message(channel, sender_id, "assistant", faq_answer)
            return faq_answer

    messages = history + [{"role": "user", "content": user_message}]

    if max_tokens is None:
        if channel == "email":
            max_tokens = 1024
        elif channel in ("instagram_dm", "whatsapp", "tiktok_dm"):
            max_tokens = 200  # DM = max 2-3 zdania jak SMS
        elif channel in ("instagram_comment", "tiktok", "youtube", "google_business"):
            max_tokens = 200  # krótkie odpowiedzi social media
        else:
            max_tokens = 512

    model = _CHANNEL_MODELS.get(channel or "", _DEFAULT_MODEL)

    # Próbuj każdy silnik po kolei
    for engine_name, engine_fn in _ENGINES:
        try:
            if engine_name == "Claude":
                reply = engine_fn(messages, max_tokens, model)
            else:
                reply = engine_fn(messages, max_tokens)
            logger.info("Odpowiedź od %s (%d znaków)", engine_name, len(reply))
            if sender_id and channel:
                save_message(channel, sender_id, "assistant", reply)
            return reply
        except Exception as e:
            logger.warning("Błąd %s: %s — próbuję następny silnik", engine_name, e)

    # Żaden silnik nie zadziałał
    fallback = "Przepraszam, mam chwilowy problem. Zadzwoń do nas: 690 270 032 🤙"
    if sender_id and channel:
        save_message(channel, sender_id, "assistant", fallback)
    return fallback
