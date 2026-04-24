# CLAUDE.md — FUN like HEL

## Projekt

Bot AI dla szkoły sportów wodnych **FUN like HEL | Szkoła Kite Wind** z siedzibą w Jastarni (Polska) i Hurghadzie (Egipt).

System automatycznie odpowiada na wiadomości klientów przez:
- Instagram (komentarze + DM)
- Gmail
- YouTube (komentarze)
- Google Business (recenzje)
- WhatsApp
- TikTok

## Struktura projektu

```
funlikehel/
├── server/              # FastAPI backend
│   ├── main.py          # Serwer + pętle pollingu (Gmail co 5 min, YT co 10 min)
│   ├── claude_agent.py  # Integracja z Claude API — główny mózg bota
│   ├── instagram.py     # Webhook Instagram (komentarze + DM)
│   ├── google_mail.py   # Obsługa skrzynki Gmail
│   ├── youtube.py       # Komentarze YouTube
│   ├── google_business.py # Recenzje Google Business
│   ├── whatsapp.py      # WhatsApp Cloud API (wysyłka + odbiór)
│   ├── tiktok.py        # Integracja TikTok
│   ├── auto_upload.py   # Auto-upload treści na Drive
│   ├── conversation_memory.py # Pamięć rozmów (SQLite: memory.db)
│   ├── cleanup_mail.py  # Cykliczne czyszczenie skrzynki
│   ├── google_drive.py  # Operacje na Google Drive
│   ├── google_auth.py   # OAuth Google
│   ├── api.env          # Zmienne środowiskowe (NIE commituj)
│   └── requirements.txt
└── google_ads_scripts/  # Skrypty Google Ads (JS)
    ├── 1_sezonowy_przelacznik.js
    ├── 2_budzet_sezonowy.js
    └── 3_raport_tygodniowy.js
```

## Agent AI — persona "Alicja"

Bot wciela się w **Alicję** — przyjazną pracownicę szkoły. Pełna definicja persony i oferty w:
`.claude/agents/funlikehel-agent.md`

### Kluczowe zasady komunikacji
- Odpowiedzi po polsku (po angielsku gdy klient pisze po angielsku)
- Zaczyna od "Cześć [imię]!" — nigdy od "Szanowni Państwo"
- Ciepły, konkretny, entuzjastyczny ton — jak znajoma z plaży
- Social media: max 3-4 zdania, 1-2 emoji
- Zawsze kończy CTA: "Zadzwoń!", "Zarezerwuj!", "Napisz do nas!"
- Kwalifikuje klienta zanim poda szczegóły (poziom, sport, lokalizacja, termin, liczba osób)

### Kontakt i rezerwacje
- Tel: **690 270 032**
- Email: **funlikehelbrand@gmail.com**
- WWW: www.funlikehel.pl

## Uruchomienie serwera

```bash
cd server
pip install -r requirements.txt
uvicorn main:app --reload
```

Serwer nasłuchuje webhooków Instagrama i uruchamia pętle pollingu dla Gmail i YouTube.

## Zmienne środowiskowe (api.env)

Wymagane klucze w `server/api.env`:
- `ANTHROPIC_API_KEY` — klucz Claude API
- `INSTAGRAM_*` — tokeny Meta/Instagram
- `GOOGLE_*` — dane OAuth Google
- `TIKTOK_*` — dane TikTok API

## Ważne zasady

- `api.env`, `credentials.json`, `token.json`, `memory.db` — nigdy nie commituj
- Pamięć rozmów przechowywana lokalnie w SQLite (`memory.db`)
- Bot używa subagenta `funlikehel-agent` dla odpowiedzi klientom
