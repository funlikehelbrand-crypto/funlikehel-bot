"""
FB Lead Scout — automatyczne skanowanie grup Facebook przez Playwright.

Loguje się na Facebook, scrapeuje posty z monitorowanych grup (ostatnie 30 dni),
analizuje je przez Claude (lead_score 0-100) i wysyła alerty email dla leadów >= 55.

Konfiguracja (api.env):
    FB_EMAIL      — email do konta Facebook
    FB_PASSWORD   — hasło do Facebooka
    FB_GROUP_URLS — grupy do skanowania, oddzielone przecinkami
                    (domyślnie: https://www.facebook.com/groups/kiteforumpl)

Uruchomienie ręczne:
    POST /api/fb-leads/scan         — uruchamia skanowanie natychmiast
    GET  /api/fb-leads/report       — lista leadów z bazy (score >= 30)

Uruchomienie automatyczne:
    Polling loop w main.py — co 6 godzin
"""

import asyncio
import base64
import concurrent.futures
import hashlib
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from email.mime.text import MIMEText

import anthropic

try:
    from google import genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

# ── Konfiguracja ─────────────────────────────────────────────────────────────

DB_PATH      = os.path.join(os.path.dirname(__file__), "memory.db")
SESSION_PATH = os.path.join(os.path.dirname(__file__), "fb_session.json")
ALERT_EMAIL  = "funlikehelbrand@gmail.com"
DAYS_BACK    = 30
MIN_SCORE    = 60   # minimalny wynik do alertu email
MAX_SCROLLS  = 20   # ile razy scrollujemy grupę (każdy scroll ≈ 3-5 postów; 20 = ~60-80 postów ≈ miesiąc)

_DEFAULT_GROUP_URLS = (
    "https://www.facebook.com/groups/kiteforumpl,"
    "https://www.facebook.com/groups/kitesurfingpolska,"
    "https://www.facebook.com/groups/wyjazdy.kitesurfingowe,"
    "https://www.facebook.com/groups/wingfoilteampolska,"
    "https://www.facebook.com/groups/ilovepolwysephelski,"
    "https://www.facebook.com/groups/polacywakacjehurghada2026,"
    "https://www.facebook.com/groups/egiptwakacje2026"
)


def _get_group_urls() -> list[str]:
    raw = os.environ.get("FB_GROUP_URLS", _DEFAULT_GROUP_URLS)
    return [u.strip() for u in raw.split(",") if u.strip()]


# ── SQLite ────────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS fb_leads (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                post_hash          TEXT UNIQUE NOT NULL,
                group_name         TEXT NOT NULL,
                post_url           TEXT NOT NULL,
                author_name        TEXT,
                post_text          TEXT,
                post_date          TEXT,
                lead_score         INTEGER DEFAULT 0,
                priority           TEXT DEFAULT 'Ignore',
                detected_intent    TEXT,
                detected_location  TEXT,
                suggested_reply_pl TEXT,
                suggested_reply_en TEXT,
                why_relevant       TEXT,
                email_sent         INTEGER DEFAULT 0,
                commented          INTEGER DEFAULT 0,
                commented_ts       TEXT,
                ts                 DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_fb_leads_score "
            "ON fb_leads(lead_score, ts)"
        )
        # Migracja dla starszych baz bez kolumn commented/commented_ts
        for col, definition in [("commented", "INTEGER DEFAULT 0"),
                                 ("commented_ts", "TEXT")]:
            try:
                c.execute(f"ALTER TABLE fb_leads ADD COLUMN {col} {definition}")
            except Exception:
                pass  # kolumna już istnieje


_init_db()


def _post_hash(text: str, author: str) -> str:
    return hashlib.md5(f"{author}::{text[:200]}".encode()).hexdigest()


def _is_processed(post_hash: str) -> bool:
    with _conn() as c:
        return c.execute(
            "SELECT 1 FROM fb_leads WHERE post_hash = ?", (post_hash,)
        ).fetchone() is not None


def _save_lead(lead: dict):
    with _conn() as c:
        c.execute("""
            INSERT OR IGNORE INTO fb_leads
                (post_hash, group_name, post_url, author_name, post_text,
                 post_date, lead_score, priority, detected_intent,
                 detected_location, suggested_reply_pl, suggested_reply_en,
                 why_relevant, email_sent)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0)
        """, (
            lead["post_hash"],
            lead.get("group_name", ""),
            lead.get("post_url", "brak"),
            lead.get("author_name", ""),
            lead.get("post_text", ""),
            lead.get("post_date", ""),
            lead.get("lead_score", 0),
            lead.get("priority", "Ignore"),
            lead.get("detected_intent", ""),
            lead.get("detected_location", ""),
            lead.get("suggested_reply_pl", ""),
            lead.get("suggested_reply_en", ""),
            lead.get("why_relevant", ""),
        ))


def _mark_email_sent(post_hash: str):
    with _conn() as c:
        c.execute(
            "UPDATE fb_leads SET email_sent = 1 WHERE post_hash = ?",
            (post_hash,),
        )


def mark_commented(lead_id: int):
    """Oznacza lead jako skomentowany — wywołaj po publikacji komentarza."""
    with _conn() as c:
        c.execute(
            "UPDATE fb_leads SET commented = 1, commented_ts = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), lead_id),
        )


def get_pending_leads(min_score: int = 55, limit: int = 20) -> list[dict]:
    """
    Zwraca leady gotowe do skomentowania:
    - score >= min_score
    - mają suggested_reply_pl
    - jeszcze nie skomentowane (commented = 0)
    """
    with _conn() as c:
        rows = c.execute("""
            SELECT id, group_name, post_url, author_name, post_text,
                   post_date, lead_score, priority, detected_intent,
                   detected_location, suggested_reply_pl, suggested_reply_en,
                   why_relevant, email_sent, ts
            FROM fb_leads
            WHERE lead_score >= ?
              AND (suggested_reply_pl IS NOT NULL AND suggested_reply_pl != '')
              AND commented = 0
            ORDER BY lead_score DESC, ts DESC
            LIMIT ?
        """, (min_score, limit)).fetchall()
    return [dict(r) for r in rows]


def get_leads_report(min_score: int = 30, limit: int = 50) -> list[dict]:
    """Pobiera leady z bazy — do endpointu /api/fb-leads/report."""
    with _conn() as c:
        rows = c.execute("""
            SELECT id, group_name, post_url, author_name, post_text,
                   post_date, lead_score, priority, detected_intent,
                   detected_location, suggested_reply_pl, why_relevant,
                   email_sent, ts
            FROM fb_leads
            WHERE lead_score >= ?
            ORDER BY lead_score DESC, ts DESC
            LIMIT ?
        """, (min_score, limit)).fetchall()
    return [dict(r) for r in rows]


# ── Pre-filter (przed Claude) ─────────────────────────────────────────────────

def _pre_filter(post_text: str, author_name: str) -> bool:
    """
    Zwraca True jeśli post należy POMINĄĆ (score = 0) bez wysyłania do Claude.

    Warunki wykluczenia:
    1. Post zawiera markery własnych postów FLH (Fun Like Hel / funlikehel).
    2. Post pochodzi od biura turystycznego: kombinacja "wycieczk" + safari/piramidy/delfin/rejs
       bez pytajnika (ogłoszenie biura, nie pytanie turysty).
    3. Post bez pytajnika o długości < 50 znaków (fragment / relacja, nie pytanie).
    """
    txt  = post_text or ""
    low  = txt.lower()

    # Własne posty FLH — nigdy nie analizuj, żeby nie komentować własnych treści
    flh_markers = ("fun like hel", "funlikehel", "funlikehelbrand", "szkoła kite wind")
    if any(m in low for m in flh_markers):
        return True

    # Biuro turystyczne: pattern "wycieczk" + atrakcja bez pytajnika
    tour_agency_attractions = ("safari", "piramid", "delfin", "rejs", "wielbłąd")
    if "wycieczk" in low and any(a in low for a in tour_agency_attractions) and "?" not in txt:
        return True

    # Ogłoszenie SPRZEDAŻY sprzętu (autor wystawia sprzęt, nie pyta o zakup)
    # Wyklucz tylko jeśli nie ma pytajnika i ma słowa sprzedażowe
    gear_sale_markers = ("sprzedam", "sprzedaj", "do sprzedania", "na sprzedaż",
                         "cena:", "zł obo", "zł do negocjacji")
    if any(m in low for m in gear_sale_markers) and "?" not in txt:
        return True

    # Za krótki post bez pytajnika — nie niesie intencji zakupowej
    if "?" not in txt and len(txt.strip()) < 50:
        return True

    return False


# ── Claude — analiza leadów ───────────────────────────────────────────────────

def _get_claude():
    """Lazy init — gwarantuje że API key jest załadowany z env przed inicjalizacją."""
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

_SYSTEM_PROMPT = """\
Jesteś agentem analizującym posty w polskich grupach Facebook dla szkoły kitesurfingu Fun Like Hel.

## O szkole FUN LIKE HEL
- Szkoła kite działająca cały rok
- Lato: Jastarnia, Półwysep Helski (płytka Zatoka Pucka — idealna do nauki)
- Zima: El Gouna i Hurghada w Egipcie (Morze Czerwone, Sahl Hasheesh)
- Instruktorzy po polsku i angielsku, sprzęt Cabrinha
- Kursy od zera, pro-campy, wyjazdy grupowe

## KLUCZOWY KROK PIERWSZY — wykryj typ tekstu

Zanim ocenisz leada, rozstrzygnij:

**post_type = "standalone"** — autor zadaje pytanie LUB dzieli się czymś do społeczności.
Przykłady: "Gdzie polecacie kurs kite?", "Lecę do Hurghady, co robić?", "Szukam szkoły w Jastarni"

**post_type = "thread_reply"** — fragment rozmowy: ktoś odpowiada INNEJ osobie, cytuje czyjś nick,
kontynuuje wątek, chwali/krytykuje kogoś konkretnego, lub daje krótką odpowiedź bez kontekstu.
Przykłady: "Zdecydowanie polecam Mateusz Kuczaj", "Artu Ditu Trzeba mieć własny sprzęt?",
"El Gouna ! Inna jakość niż Hurgada", "@Ola tak jak pisałam", "Pisz do niego"

**Jeśli post_type = "thread_reply" → lead_score = 0, priority = "Ignore", suggested_reply_pl = null**
Nie komentujemy odpowiedzi innych użytkowników — to wygląda jak spam.

## Grupy kite (Kite Forum Polska, kiteforum.pl)
Szukamy postów gdzie ktoś:
- Pyta o szkołę kite, instruktora, gdzie zrobić kurs
- Planuje wyjazd kite do Egiptu (El Gouna, Hurghada, Dahab, Soma Bay)
- Pyta o spoty w Polsce (Hel, Jastarnia, Chałupy, Kuźnica)
- Pyta "gdzie jechać zimą na kite", "ile kosztuje kurs"

## Grupy turystyczne Egipt/Hurghada
Szukamy postów gdzie turysta:
- Pyta "co robić w Hurghadzie / Egipcie?"
- Szuka aktywności sportowych, atrakcji dla rodziny
- Pyta o polskie biuro/organizatora w Hurghadzie
- Szuka "czegoś ekscytującego" lub aktywnego spędzenia wakacji

## Sprzęt kite — nowa kategoria "gear_inquiry"

Szukamy postów gdzie ktoś:
- Pyta "jaki sprzęt kupić na start / dla początkującego"
- Prosi o polecenie latawca, deski, baru — bez konretnego modelu do sprzedania
- Pyta "ile kosztuje własny zestaw", "czy warto kupić sprzęt przed kursem"
- Porównuje zestawy lub marki z punktu widzenia kupującego (nie serwisanta)

Dla tych postów:
- Alicja wchodzi w rozmowę jako osoba ze społeczności, NIE jako sprzedawca
- Daje praktyczną radę ("na start 9-12m, flat-friendly laguna"), POTEM wspomina że mają sprzęt Cabrinha i pomagają dobrać
- Jeśli pyta o kurs + sprzęt razem → wyższy score (synergia)

## IGNORUJ zawsze
- Ogłoszenia sprzedaży sprzętu (autor wystawia coś na sprzedaż — bez pytajnika o kupno)
- Pytania czysto serwisowe (naprawa, naprawa baru, wymiana linek)
- Prognozy pogody bez intencji kursu
- Relacje z sesji bez pytania ("byłem na wodzie", zdjęcia)
- Ogłoszenia pracy dla instruktorów, recepcjonistów, ratowników, personelu — pytania o "wymagania godzinowe", "warunki zatrudnienia", "nocleg dla pracownika"
- Pytania o hotele/restauracje bez sportu
- Wycieczki do piramid, safari, wielbłądy
- **Lotniarstwo, paralotnie, szybowce, samoloty** — słowa: lotnisko, paralotnia, lotnia, szybowiec, pilot, licencja lotnicza — to NIE jest kitesurfing
- Windsurfing bez pytania o kite (chyba że szkoła oferuje windsurfing)

## Styl odpowiedzi Alicji — WAŻNE
Alicja to pracownica szkoły, kiterka, rozmawia jak ktoś ze społeczności, NIE jak marketing.

ZASADY:
1. Zacznij od nicku/imienia autora jeśli znasz: "Hej Marek," — jeśli nieznany: "Hej!"
2. Najpierw wejdź w temat rozmowy (potwierdź, dopytaj) — POTEM wspomnij o FLH
3. Max 2-3 zdania, 1 emoji, kończy pytaniem
4. NIE zaczynaj od "Fun Like Hel prowadzi..." — to brzmi jak reklama
5. TYLKO polskie znaki: ą ę ó ś ź ż ć ń ł — ZERO arabskich, rosyjskich, czeskich liter
6. Naturalny slang kitera: "spot", "kuje", "sesja", "flat", "laguny"

PRZYKŁADY DOBREGO STYLU:

Ktoś pyta o szkołę na Helu:
"Hej! Jastarnia to dobry wybór — płytka zatoka, nie ma fali, idealne do nauki. My jesteśmy na miejscu, małe grupy i nowy sprzęt Cabrinha. Kiedy planujesz przyjazd? 🤙"

Ktoś jedzie do El Gouny:
"Hej! El Gouna to klasyk, laguna w Sahl Hasheesh jest płaska jak stół. My tam prowadzimy zajęcia przez cały sezon — jeśli chcesz wziąć lekcję albo dołączyć do grupy, pisz! Kiedy lecisz?"

Turysta pyta co robić w Hurghadzie:
"Hej! Kitesurfing to numer jeden na aktywne wakacje tutaj 🤙 Laguna w Sahl Hasheesh, 2h na spokojnej wodzie, zero doświadczenia potrzebne. Jesteśmy polską szkołą, transport z hotelu wliczony. Kiedy przyjeżdżacie?"

PRZYKŁADY ZŁEGO STYLU (NIE RÓB TAK):
- "Cześć! Fun Like Hel prowadzi szkolenia w El Gounie i Hurghadzie..." (zaczyna od reklamy)
- "Dzięki za rekomendację Mateusza — to świetny feedback dla FLH!" (odpowiedź na pochwałę konkurencji)
- "El Gouně" lub "Huردها" (obce znaki — błąd enkodowania)

Zwróć WYŁĄCZNIE poprawny JSON bez markdown."""

_USER_PROMPT = """\
Oceń post z grupy Facebook pod kątem potencjalnego klienta szkoły kite FUN like HEL (Jastarnia PL + Hurghada Egipt).

Grupa: {group_name}
Autor: {author}
Tekst:
{text}

SKALA SCORINGU (bazowy score przed modyfikatorami):
85-100: Bezposrednie pytanie o kurs kite / szkole kite w lokalizacji FLH
75-84: Pytanie o kite ogolnie (Polska/Egipt), spot, nauka od zera
65-74: Pytanie o sprzet dla poczatkujacego / "co kupic na start" / kurs + sprzet razem
55-64: Aktywny turysta w Hurghadzie/El Gounie szuka aktywnosci sportowej
40-54: Turysta szuka "dodatkowej atrakcji" w Hurghadzie, pyta o organizatora z cennikiem
25-39: Slaby sygnal — turysta wspomina aktywnosci wodne lub sporty
0-24: Ogloszenie firmy, safari, hotel, restauracja, pytanie niesportowe

MODYFIKATORY (dodaj do bazowego score, cap na 100):
+15 jesli post z grupy "Kite Forum Polska"
+10 jesli "El Gouna" lub "Sahl Hasheesh" w tekscie
+10 jesli "polski instruktor" lub "po polsku" lub "polska szkola" w tekscie
+10 jesli autor podal konkretny termin wyjazdu
+10 jesli post zawiera pytanie o sprzet ORAZ kurs/nauke razem (synergia)
+5 jesli post zawiera pytajnik (faktyczne pytanie)
-50 (cap score na 10) jesli post od strony firmowej / ogloszenie
-30 jesli post to OGLOSZENIE SPRZEDAZY sprzetu (autor wystawia sprzet, nie pyta o zakup)
FORCE 0 jesli post zawiera "Fun Like Hel" lub "funlikehel" (wlasny post szkoly)

WYMOG: jesli score >= 55 ale post NIE zawiera pytajnika → obniz score o 20

Zwróć JSON w DOKŁADNIE tym formacie (bez żadnego markdown ani komentarzy):
{{
  "post_type": "<standalone|thread_reply>",
  "is_lead": true/false,
  "lead_score": <liczba calkowita 0-100, uwzgledniajaca modyfikatory>,
  "priority": "<Hot|Warm|Low|Ignore>",
  "detected_language": "<PL|EN|Other>",
  "detected_location": "<Egypt|El Gouna|Hurghada|Dahab|Soma Bay|Poland|Hel|Jastarnia|Chalupy|Other|unknown>",
  "detected_intent": "<direct_kite|active_tourist|family|spam|own_post|school_recommendation|beginner_course|advanced_course|kite_trip|spot_question|travel_activity|gear_inquiry|gear_sale|technical|job_offer|thread_reply|other>",
  "why_relevant": "<1 zdanie dlaczego warto / nie warto odpowiedziec jako FLH>",
  "score_reason": "<krotkie uzasadnienie wyniku: bazowy score + ktore modyfikatory zastosowano>",
  "suggested_reply_pl": "<gotowa odpowiedz po polsku TYLKO polskie znaki — null jesli Ignore/Low/thread_reply>",
  "suggested_reply_en": "<gotowa odpowiedz po angielsku — null jesli post po polsku lub Ignore/Low>"
}}

Progi priorytetow (po wszystkich modyfikatorach):
- 80-100: Hot
- 60-79: Warm
- 30-59: Low
- 0-29: Ignore
"""


def _apply_python_modifiers(analysis: dict, post_text: str, group_name: str) -> dict:
    """
    Post-processing po odpowiedzi Claude: stosuje modyfikatory score zdefiniowane
    w prompt (Python-side, żeby score był deterministyczny niezależnie od modelu).

    Modyfikatory:
    +15 jeśli Kite Forum Polska i score >= 40
    -20 jeśli score >= 55 ale brak pytajnika w tekście (cap na 35)
    """
    score = int(analysis.get("lead_score", 0))

    # Modyfikator: Kite Forum Polska
    if "kite forum" in group_name.lower() and score >= 40:
        score = min(score + 15, 100)
        logger.debug("Modyfikator +15 (Kite Forum) → score=%d", score)

    # Modyfikator: brak pytajnika przy wyniku >= 55
    if "?" not in (post_text or "") and score >= 55:
        score = max(score - 20, 35)
        logger.debug("Modyfikator -20 (brak pytajnika) → score=%d", score)

    analysis["lead_score"] = score

    # Przelicz priority na podstawie ostatecznego score
    if score >= 80:
        analysis["priority"] = "Hot"
    elif score >= 60:
        analysis["priority"] = "Warm"
    elif score >= 30:
        analysis["priority"] = "Low"
    else:
        analysis["priority"] = "Ignore"

    analysis["is_lead"] = score >= 60

    return analysis


def _analyze_with_claude(prompt: str) -> str:
    """Scoring przez Claude Haiku."""
    response = _get_claude().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=[{
            "type": "text",
            "text": _SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def _analyze_with_gemini(prompt: str) -> str:
    """Scoring przez Gemini Flash (fallback gdy Claude nie ma kredytów)."""
    if genai is None:
        raise ImportError("google-genai nie zainstalowane")
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("Brak GEMINI_API_KEY w api.env")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"{_SYSTEM_PROMPT}\n\n---\n\n{prompt}",
    )
    return response.text.strip()


# Śledzi który provider aktualnie działa — unika retry Claude przy każdym poście
_active_provider = "claude"  # "claude" | "gemini"


def _analyze_post(post: dict) -> dict:
    """Wysyła post do AI (Claude → Gemini fallback), stosuje modyfikatory i zwraca analizę."""
    global _active_provider

    prompt = _USER_PROMPT.format(
        group_name=post.get("group_name", "nieznana"),
        author=post.get("author_name", "nieznany"),
        text=post.get("post_text", "")[:1500],
    )

    raw = None
    providers = (["claude", "gemini"] if _active_provider == "claude"
                 else ["gemini", "claude"])

    for provider in providers:
        try:
            if provider == "claude":
                raw = _analyze_with_claude(prompt)
            else:
                raw = _analyze_with_gemini(prompt)
            if _active_provider != provider:
                logger.info("Przełączono lead scoring na: %s", provider)
                _active_provider = provider
            break
        except Exception as e:
            err_msg = str(e).lower()
            is_credit_error = ("credit" in err_msg or "balance" in err_msg
                               or "billing" in err_msg or "quota" in err_msg)
            logger.warning("Błąd %s: %s%s", provider, e,
                           " → próbuję fallback" if provider == providers[0] else "")
            if is_credit_error and provider == "claude":
                _active_provider = "gemini"
            continue

    if raw is None:
        logger.error("Oba providery (Claude + Gemini) zawiodły dla posta od '%s'",
                     post.get("author_name"))
        return {
            "is_lead": False, "lead_score": 0, "priority": "Ignore",
            "detected_intent": "other", "detected_location": "unknown",
            "why_relevant": "Błąd analizy (Claude + Gemini) — sprawdź ręcznie.",
            "suggested_reply_pl": None, "suggested_reply_en": None,
        }

    try:
        # Usuń markdown code fences jeśli model je dodał
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
        analysis = json.loads(raw.strip())
        analysis = _apply_python_modifiers(
            analysis, post.get("post_text", ""), post.get("group_name", ""),
        )
        return analysis
    except (json.JSONDecodeError, IndexError) as e:
        logger.warning("Błąd parsowania JSON od %s: %s | raw: %s",
                       _active_provider, e, raw[:200])
        return {
            "is_lead": False, "lead_score": 0, "priority": "Ignore",
            "detected_intent": "other", "detected_location": "unknown",
            "why_relevant": "Błąd parsowania odpowiedzi AI.",
            "suggested_reply_pl": None, "suggested_reply_en": None,
        }


# ── Gmail alert ───────────────────────────────────────────────────────────────

OWNER_WHATSAPP = os.environ.get("OWNER_WHATSAPP", "48690270032")


def _send_gear_whatsapp_alert(lead: dict):
    """
    Wysyła WhatsApp alert do właściciela dla leadów gear_inquiry (zapytania o sprzęt).
    Szybszy kanał niż email — Łukasz reaguje od razu.
    """
    try:
        import asyncio
        from whatsapp import send_message as wa_send

        score   = lead.get("lead_score", 0)
        author  = lead.get("author_name", "nieznany")
        group   = lead.get("group_name", "FB")
        post_url = lead.get("post_url", "brak linku")
        reply   = lead.get("suggested_reply_pl") or "—"

        text = (
            f"🛒 *Lead sprzęt Cabrinha* (score {score}/100)\n"
            f"Autor: {author} | Grupa: {group}\n"
            f"Link: {post_url}\n\n"
            f"Proponowana odpowiedź:\n_{reply}_\n\n"
            f"Sklep: funlikehel.pl/sklep\n"
            f"Kod absolwenta: ABSOLWENT10 (-10%)"
        )

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(wa_send(OWNER_WHATSAPP, text))
        finally:
            loop.close()

        logger.info("WhatsApp gear alert wysłany do właściciela (autor: %s)", author)
    except Exception as e:
        logger.warning("Błąd WhatsApp gear alert: %s", e)


def _send_email_alert(lead: dict):
    """Wysyła alert email przez Gmail API (Google OAuth)."""
    try:
        from google_mail import get_gmail_service
    except ImportError:
        logger.warning("google_mail niedostępny — pomijam wysyłkę emaila.")
        return

    priority   = lead.get("priority", "Warm")
    score      = lead.get("lead_score", 0)
    author     = lead.get("author_name", "nieznany")
    post_url   = lead.get("post_url", "brak")
    post_date  = lead.get("post_date", "")
    text       = (lead.get("post_text") or "")[:600]
    why        = lead.get("why_relevant", "")
    reply_pl   = lead.get("suggested_reply_pl") or "—"
    reply_en   = lead.get("suggested_reply_en") or "—"
    group      = lead.get("group_name", "Kite Forum Polska")
    intent     = lead.get("detected_intent", "zapytanie")

    link_warning = ""
    if not post_url or post_url == "brak":
        link_warning = "\n⚠️  BRAK BEZPOŚREDNIEGO LINKU — znajdź post ręcznie w grupie."
        post_url = "https://www.facebook.com/groups/kiteforumpl"

    subject = f"[FLH Lead] [{priority}] {group} – {intent}"

    if priority == "Hot":
        header = "HOT LEAD – WARTO ODPOWIEDZIEĆ SZYBKO"
    else:
        header = "WARM LEAD – WARTO SPRAWDZIĆ"

    body = f"""{header}

Lead score: {score}/100
Priorytet:  {priority}
Grupa:      {group}
Data posta: {post_date}

Link do posta:
{post_url}{link_warning}

Autor: {author}

Treść posta:
\"{text}\"

Dlaczego warto odpowiedzieć:
{why}

Rekomendowana akcja:
Kliknij link → przeczytaj post → odpowiedz publicznym komentarzem.
Nie wysyłaj DM jako pierwszy kontakt.

Proponowana odpowiedź PL:
\"{reply_pl}\"

Proponowana odpowiedź EN:
\"{reply_en}\"

---
Alert wygenerowany przez FLH Lead Scout | {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
    try:
        service = get_gmail_service()
        msg = MIMEText(body, "plain", "utf-8")
        msg["to"]      = ALERT_EMAIL
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        logger.info("Alert email wysłany: %s (score=%d)", subject, score)
    except Exception as e:
        logger.error("Błąd wysyłki alert emaila: %s", e)


# ── Playwright — sesja Facebook ───────────────────────────────────────────────

async def _save_session(context):
    cookies = await context.cookies()
    with open(SESSION_PATH, "w") as f:
        json.dump(cookies, f)
    logger.info("Zapisano sesję Facebook (%d cookie).", len(cookies))


async def _load_session(context) -> bool:
    if not os.path.exists(SESSION_PATH):
        return False
    try:
        with open(SESSION_PATH) as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        logger.info("Wczytano sesję Facebook (%d cookie).", len(cookies))
        return True
    except Exception as e:
        logger.warning("Nie udało się wczytać sesji FB: %s", e)
        return False


async def _login(page, context):
    """Loguje się na Facebook przy użyciu FB_EMAIL i FB_PASSWORD z api.env."""
    email    = os.environ.get("FB_EMAIL", "")
    password = os.environ.get("FB_PASSWORD", "")
    if not email or not password:
        raise RuntimeError(
            "Brak FB_EMAIL / FB_PASSWORD w api.env — nie można zalogować się na Facebook."
        )

    logger.info("Loguję się na Facebook jako %s...", email)

    # Otwórz stronę główną FB (nie /login — unikamy przekierowań cookie wall)
    await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=40000)
    await page.wait_for_timeout(3000)

    # Selektory cookie banera — próbuj każdy przez 2 sekundy
    for selector in [
        '[data-cookiebanner="accept_button"]',
        'button[title="Allow all cookies"]',
        'button[title="Zezwól na wszystkie pliki cookie"]',
        '[aria-label="Allow all cookies"]',
        'div[aria-label="Zezwól na wszystkie pliki cookie"]',
        'button:has-text("Zezwól na wszystkie")',
        'button:has-text("Accept all")',
        'button:has-text("Allow all")',
    ]:
        try:
            await page.click(selector, timeout=2000)
            await page.wait_for_timeout(1000)
            logger.info("Kliknięto baner cookies: %s", selector)
            break
        except Exception:
            pass

    # Selektory pola email — FB używa różnych w zależności od wersji
    email_selectors = ["#email", 'input[name="email"]', 'input[type="email"]',
                       'input[placeholder*="mail"]', 'input[placeholder*="Email"]']
    pass_selectors  = ["#pass",  'input[name="pass"]',  'input[type="password"]']

    # Poczekaj aż pojawi się pole email (max 20s)
    email_found = False
    for sel in email_selectors:
        try:
            await page.wait_for_selector(sel, timeout=20000)
            await page.fill(sel, email)
            email_found = True
            logger.info("Wpisano email w selector: %s", sel)
            break
        except Exception:
            pass

    if not email_found:
        # Zrzut ekranu do debugowania
        try:
            await page.screenshot(path=os.path.join(os.path.dirname(__file__), "fb_login_debug.png"))
            logger.error("Nie znaleziono pola email. Zrzut ekranu: fb_login_debug.png")
        except Exception:
            pass
        raise RuntimeError("Nie znaleziono formularza logowania FB — sprawdź fb_login_debug.png")

    for sel in pass_selectors:
        try:
            await page.fill(sel, password)
            break
        except Exception:
            pass

    # Kliknij przycisk logowania
    for sel in ['[name="login"]', 'button[type="submit"]', 'input[type="submit"]']:
        try:
            await page.click(sel, timeout=5000)
            break
        except Exception:
            pass

    await page.wait_for_timeout(7000)

    if "login" in page.url or "checkpoint" in page.url:
        try:
            await page.screenshot(path=os.path.join(os.path.dirname(__file__), "fb_login_debug.png"))
        except Exception:
            pass
        raise RuntimeError(
            f"Login Facebook nie powiódł się (URL: {page.url}). "
            "Sprawdź czy konto ma 2FA lub czy email/hasło są poprawne."
        )

    logger.info("Zalogowano na Facebook. URL: %s", page.url)
    await _save_session(context)


async def _ensure_logged_in(page, context):
    """Ładuje sesję lub loguje się jeśli brak/wygasła."""
    loaded = await _load_session(context)
    if loaded:
        await page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)
        if "login" not in page.url:
            logger.info("Sesja Facebook aktywna.")
            return
        logger.info("Sesja wygasła — loguję się ponownie.")
    await _login(page, context)


# ── Playwright — scraping grupy ───────────────────────────────────────────────

async def _try_expand_post(article):
    """Klika 'Zobacz więcej' / 'See more' żeby rozwinąć tekst posta."""
    for text in ["Zobacz więcej", "Wyświetl więcej", "See more"]:
        try:
            btn = article.get_by_text(text, exact=True).first
            if await btn.count():
                await btn.click(timeout=2000)
                await article.page().wait_for_timeout(400)
                return
        except Exception:
            pass


async def _extract_post_url(article) -> str:
    """Wyciąga bezpośredni link do posta FB z artykułu."""
    for selector in ['a[href*="/posts/"]', 'a[href*="story_fbid"]']:
        try:
            links = await article.query_selector_all(selector)
            for link in links:
                href = await link.get_attribute("href") or ""
                if "/posts/" in href:
                    # Normalizuj do pełnego URL bez query string
                    clean = href.split("?")[0]
                    if clean.startswith("/"):
                        clean = "https://www.facebook.com" + clean
                    return clean
                if "story_fbid" in href:
                    return href
        except Exception:
            pass
    return "brak"


async def _extract_post_date(article) -> tuple[str, bool]:
    """
    Zwraca (data_str, is_too_old).
    Próbuje odczytać Unix timestamp z abbr[data-utime].
    """
    cutoff = datetime.utcnow() - timedelta(days=DAYS_BACK)
    today  = datetime.utcnow().strftime("%Y-%m-%d")

    try:
        abbrs = await article.query_selector_all("abbr[data-utime]")
        for abbr in abbrs:
            utime = await abbr.get_attribute("data-utime")
            if utime:
                post_dt = datetime.utcfromtimestamp(int(utime))
                return post_dt.strftime("%Y-%m-%d"), post_dt < cutoff
    except Exception:
        pass

    # Fallback: szukaj tekstu wskazującego na stary post ("X mies.", "X month")
    try:
        inner = (await article.inner_text()).lower()
        for marker in [" mies.", " months", " miesiąc"]:
            if marker in inner:
                return today, True
    except Exception:
        pass

    return today, False


def _group_name_from_url(url: str) -> str:
    """Wyciąga czytelną nazwę grupy z URL FB."""
    slug = url.rstrip("/").split("/groups/")[-1].split("/")[0]
    if slug.isdigit():
        return f"Grupa FB ({slug})"
    return slug.replace("-", " ").replace("_", " ").title()


async def _scrape_group(page, group_url: str) -> tuple[list[dict], str]:
    """
    Nawiguje do grupy i scrapeuje posty z ostatnich DAYS_BACK dni.
    Zwraca (lista postów, nazwa grupy).
    """
    logger.info("Scrapuję grupę: %s", group_url)
    await page.goto(group_url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(4000)

    if "login" in page.url:
        raise RuntimeError("Sesja wygasła w trakcie scrapowania — wymagane ponowne logowanie.")

    # Wyciągnij nazwę grupy z tytułu strony lub URL
    group_name = _group_name_from_url(group_url)
    try:
        title = await page.title()
        if title and "|" in title:
            group_name = title.split("|")[0].strip()
        elif title and title.strip():
            group_name = title.strip()
    except Exception:
        pass

    posts      : list[dict]  = []
    seen_hashes: set[str]    = set()
    stop_flag                = False

    for scroll_i in range(MAX_SCROLLS):
        if stop_flag:
            break

        articles = await page.query_selector_all('div[role="article"]')
        logger.debug("Scroll %d: %d artykułów w DOM", scroll_i, len(articles))

        for article in articles:
            try:
                # ── Rozwiń tekst ──
                await _try_expand_post(article)

                # ── Pobierz tekst posta ──
                text = ""
                for div in await article.query_selector_all('div[dir="auto"]'):
                    t = (await div.inner_text()).strip()
                    if len(t) > len(text):
                        text = t

                # Fallback: cały inner_text artykułu
                if len(text) < 30:
                    text = " ".join((await article.inner_text()).split())[:2000]

                if len(text) < 30:
                    continue

                # ── Deduplication ──
                h = _post_hash(text, "")
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)

                # ── Autor ──
                # FB renderuje imię autora jako link do profilu w h2/h3/h4/strong.
                # Kluczowe: filtrujemy po href — tylko linki do profili użytkowników,
                # nie do grup/stron/postów/eventów (które też mają linki w artykule).
                author = "nieznany"
                _SKIP_WORDS = {
                    "lubię", "komentarz", "udostępnij", "odpowiedz", "obserwuj",
                    "like", "comment", "share", "follow", "więcej", "see more",
                    "zobacz", "zareaguj", "react", "·", "napisz", "write",
                    "wyślij", "send", "polubionych", "liked", "members", "członk",
                }
                _NON_PROFILE = (
                    "/groups/", "/pages/", "/events/", "/posts/", "/video/",
                    "/photos/", "/marketplace/", "/watch/", "/reel/", "/hashtag/",
                    "?comment", "story_fbid", "#",
                )

                def _is_profile_url(href: str) -> bool:
                    """True jeśli href prowadzi do profilu użytkownika."""
                    if not href:
                        return False
                    # Absolutne linki do FB (profil numeryczny lub username)
                    if "facebook.com" in href:
                        return not any(x in href for x in _NON_PROFILE)
                    # Relatywne linki (np. /user/123456/ lub /jan.kowalski/)
                    if href.startswith("/") and not any(x in href for x in _NON_PROFILE):
                        return True
                    return False

                def _clean_candidate(txt: str) -> str:
                    return txt.strip().split("\n")[0].strip()

                # Próbuj nagłówki artykułu — najnowszy layout FB: h2, h3, h4
                for sel in ["h2 a", "h3 a", "h4 a", "strong a"]:
                    if author != "nieznany":
                        break
                    try:
                        els = await article.query_selector_all(sel)
                        for el in els:
                            href = await el.get_attribute("href") or ""
                            if not _is_profile_url(href):
                                continue
                            candidate = _clean_candidate(await el.inner_text())
                            # Fallback: aria-label linka (FB czasem chowa tekst w aria)
                            if not candidate or len(candidate) > 60:
                                candidate = _clean_candidate(
                                    await el.get_attribute("aria-label") or ""
                                )
                            if (2 < len(candidate) <= 60 and
                                    not any(w in candidate.lower() for w in _SKIP_WORDS)):
                                author = candidate
                                break
                    except Exception:
                        pass

                # Ostatni fallback: dowolny link z aria-label wyglądający jak profil
                if author == "nieznany":
                    try:
                        els = await article.query_selector_all("a[aria-label]")
                        for el in els:
                            href = await el.get_attribute("href") or ""
                            if not _is_profile_url(href):
                                continue
                            candidate = _clean_candidate(
                                await el.get_attribute("aria-label") or ""
                            )
                            if (2 < len(candidate) <= 60 and
                                    not any(w in candidate.lower() for w in _SKIP_WORDS)):
                                author = candidate
                                break
                    except Exception:
                        pass

                # ── URL posta ──
                post_url = await _extract_post_url(article)

                # ── Data posta ──
                post_date, is_too_old = await _extract_post_date(article)
                if is_too_old:
                    logger.info("Dotarłem do postów starszych niż %d dni — kończę.", DAYS_BACK)
                    stop_flag = True
                    break

                posts.append({
                    "author_name": author,
                    "post_text":   text[:2000],
                    "post_url":    post_url,
                    "post_date":   post_date,
                })

            except Exception as e:
                logger.debug("Błąd parsowania artykułu: %s", e)
                continue

        if not stop_flag:
            await page.keyboard.press("End")
            await page.wait_for_timeout(2500)

    logger.info("Scraped %d postów z %s (%s)", len(posts), group_url, group_name)
    return posts, group_name


# ── Główna logika skanowania ──────────────────────────────────────────────────

async def _scan_async() -> dict:
    """Asynchroniczna implementacja skanowania wszystkich grup."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        msg = ("Playwright nie zainstalowany. "
               "Uruchom: pip install playwright && playwright install chromium")
        logger.error(msg)
        return {"error": msg, "scanned": 0}

    group_urls = _get_group_urls()
    stats = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "scanned": 0,
        "new": 0,
        "hot": 0,
        "warm": 0,
        "low": 0,
        "ignored": 0,
        "emails_sent": 0,
    }

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="pl-PL",
        )
        page = await context.new_page()

        try:
            await _ensure_logged_in(page, context)

            for group_url in group_urls:
                try:
                    raw_posts, group_name = await _scrape_group(page, group_url)
                except Exception as e:
                    logger.error("Błąd scrapowania %s: %s", group_url, e)
                    continue

                for post in raw_posts:
                    stats["scanned"] += 1
                    post_hash = _post_hash(post["post_text"], post["author_name"])

                    if _is_processed(post_hash):
                        continue

                    # Pre-filter: pomijaj posty bez żadnego kluczowego słowa — oszczędność tokenów
                    txt_lower = (post.get("post_text") or "").lower()
                    _KITE_KEYWORDS = {
                        "kite", "lataw", "kurs", "szkoł", "instrukto", "nauk", "wyjazd",
                        "hurghad", "egipt", "egypt", "gouna", "hel", "jastarni", "chałupy",
                        "wakacj", "sporty", "aktywn", "windsur", "wing", "foil", "surf",
                        "lec", "rezerwac", "obóz", "kitesur", "kiter",
                        # Sprzęt kite — pytania o zakup/polecenie dla początkujących
                        "sprzęt", "deska", "latawiec", "trapez", "bar ", " bar",
                        "cabrinha", "north kite", "duotone", "f-one", "flysurfer",
                        "zestaw kite", "setup kite", "co kupić", "polecacie sprzęt",
                        "jaki sprzęt", "dla początkuj", "na start", "pierwszy sprzęt",
                    }
                    if not any(kw in txt_lower for kw in _KITE_KEYWORDS):
                        _save_lead({
                            "post_hash": post_hash, "group_name": group_name,
                            "post_url": post["post_url"], "author_name": post["author_name"],
                            "post_text": post["post_text"], "post_date": post["post_date"],
                            "lead_score": 0, "priority": "Ignore",
                            "detected_intent": "no_keywords", "detected_location": "",
                            "suggested_reply_pl": "", "suggested_reply_en": "",
                            "why_relevant": "Brak słów kluczowych — pominięto analizę Claude",
                        })
                        stats["ignored"] = stats.get("ignored", 0) + 1
                        continue

                    # Pre-filter: wyklucz własne posty FLH, ogłoszenia biur i fragmenty bez intencji
                    if _pre_filter(post.get("post_text", ""), post.get("author_name", "")):
                        _save_lead({
                            "post_hash": post_hash, "group_name": group_name,
                            "post_url": post["post_url"], "author_name": post["author_name"],
                            "post_text": post["post_text"], "post_date": post["post_date"],
                            "lead_score": 0, "priority": "Ignore",
                            "detected_intent": "pre_filter", "detected_location": "",
                            "suggested_reply_pl": "", "suggested_reply_en": "",
                            "why_relevant": "Odfiltrowany pre-filterem (własny post FLH / biuro turystyczne / brak pytajnika i za krótki)",
                        })
                        stats["ignored"] = stats.get("ignored", 0) + 1
                        logger.debug("Pre-filter: odrzucono post od '%s'", post.get("author_name"))
                        continue

                    stats["new"] += 1
                    post["group_name"] = group_name   # przekaż do _analyze_post / modyfikatorów
                    analysis   = _analyze_post(post)
                    lead_score = int(analysis.get("lead_score", 0))
                    priority   = analysis.get("priority", "Ignore")

                    lead = {
                        "post_hash":          post_hash,
                        "group_name":         group_name,
                        "post_url":           post["post_url"],
                        "author_name":        post["author_name"],
                        "post_text":          post["post_text"],
                        "post_date":          post["post_date"],
                        "lead_score":         lead_score,
                        "priority":           priority,
                        "detected_intent":    analysis.get("detected_intent", ""),
                        "detected_location":  analysis.get("detected_location", ""),
                        "suggested_reply_pl": analysis.get("suggested_reply_pl") or "",
                        "suggested_reply_en": analysis.get("suggested_reply_en") or "",
                        "why_relevant":       analysis.get("why_relevant", ""),
                    }

                    _save_lead(lead)
                    logger.info(
                        "Post od '%s': score=%d (%s) | %s",
                        post["author_name"], lead_score, priority,
                        analysis.get("detected_intent", ""),
                    )

                    # Aktualizuj statystyki
                    key = priority.lower() if priority in ("Hot", "Warm", "Low") else "ignored"
                    stats[key] = stats.get(key, 0) + 1

                    # Wyślij alert email
                    if lead_score >= MIN_SCORE:
                        _send_email_alert(lead)
                        _mark_email_sent(post_hash)
                        stats["emails_sent"] += 1

                    # Dla gear_inquiry — dodatkowy WhatsApp alert do właściciela
                    if (analysis.get("detected_intent") == "gear_inquiry"
                            and lead_score >= MIN_SCORE):
                        _send_gear_whatsapp_alert(lead)

        finally:
            await browser.close()

    stats["finished_at"] = datetime.now().isoformat(timespec="seconds")
    logger.info(
        "FB Lead Scout zakończony: przeskanowano=%d nowych=%d hot=%d warm=%d emaile=%d",
        stats["scanned"], stats["new"], stats["hot"],
        stats["warm"], stats["emails_sent"],
    )
    return stats


def scan_groups() -> dict:
    """
    Synchroniczny wrapper — uruchamiaj z polling loop lub endpointu FastAPI.
    Tworzy nowy event loop w osobnym wątku (bezpieczne w kontekście FastAPI).
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, _scan_async())
        try:
            return future.result(timeout=1800)  # max 30 minut (11 grup)
        except concurrent.futures.TimeoutError:
            logger.error("FB Lead Scout: timeout po 30 minutach.")
            return {"error": "timeout", "scanned": 0}
        except Exception as e:
            logger.error("FB Lead Scout: nieoczekiwany błąd: %s", e)
            return {"error": str(e), "scanned": 0}


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Załaduj api.env
    env_path = os.path.join(os.path.dirname(__file__), "api.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    result = scan_groups()
    print(f"\n=== Wynik skanu ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
