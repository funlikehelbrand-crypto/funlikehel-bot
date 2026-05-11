import anthropic
import logging
import os
from dotenv import load_dotenv
from conversation_memory import get_history, save_message

load_dotenv("api.env")

logger = logging.getLogger(__name__)

# --- Silniki AI ---
claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

# Opcjonalne silniki — Gemini i OpenAI (fallback)
gemini_model = None
gemini_genai_client = None
openai_client = None
try:
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        from google import genai as google_genai
        gemini_genai_client = google_genai.Client(api_key=gemini_key)
        gemini_model = "gemini-2.0-flash"
        logger.info("Gemini engine loaded (google.genai)")
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

## Stopka — ZAWSZE na końcu każdej wiadomości email

Pozdrawiamy,
Alicja | Zespół FUN like HEL

📍 Baza Polska: Kemping Sun4Hel, Jastarnia (Półwysep Helski)
📍 Baza Egipt: Cabrinha Test Center, Hurghada
📞 690 270 032
📧 funlikehelbrand@gmail.com
🌐 www.funlikehel.pl
"""


def _call_claude(messages: list[dict], max_tokens: int) -> str:
    """Claude (Anthropic) — główny silnik."""
    response = claude_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text


def _call_gemini(messages: list[dict], max_tokens: int) -> str:
    """Gemini (Google) — fallback #1. Używa google.genai SDK."""
    contents = [{"role": "user", "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{messages[-1]['content']}"}]}]
    if len(messages) > 1:
        # Dodaj historię konwersacji
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            contents.insert(-1, {"role": role, "parts": [{"text": msg["content"]}]})

    response = gemini_genai_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config={"max_output_tokens": max_tokens},
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


# Kolejność silników: Claude → Gemini → GPT (pomijaj niedostępne)
_ENGINES = [
    ("Claude", _call_claude, lambda: bool(claude_client.api_key)),
    ("Gemini", _call_gemini, lambda: gemini_model is not None and gemini_genai_client is not None),
    ("GPT", _call_openai, lambda: openai_client is not None),
]


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

    messages = history + [{"role": "user", "content": user_message}]

    if max_tokens is None:
        max_tokens = 1024 if channel == "email" else 512

    # Próbuj każdy silnik po kolei (pomijaj niedostępne)
    for engine_name, engine_fn, is_available in _ENGINES:
        if not is_available():
            logger.debug("Pomijam %s — niedostępny (brak klucza API)", engine_name)
            continue
        try:
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
