"""
FUN like HEL — Booking Database Layer
Manages: services, bookings, availability, booking events.
Uses SQLite (bookings.db). Firestore-ready via same interface.
"""

import sqlite3
import random
import string
from datetime import datetime
from typing import Optional
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "bookings.db")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
-- ── SERVICES ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS booking_services (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    slug            TEXT    UNIQUE NOT NULL,
    name_pl         TEXT    NOT NULL,
    name_en         TEXT    NOT NULL,
    subtitle_pl     TEXT    DEFAULT '',
    subtitle_en     TEXT    DEFAULT '',
    description_pl  TEXT    DEFAULT '',
    description_en  TEXT    DEFAULT '',
    category        TEXT    NOT NULL,   -- lesson | course | camp | package | experience
    location        TEXT    NOT NULL,   -- hurghada | hel | both
    duration_hours  REAL    DEFAULT 2,
    min_persons     INTEGER DEFAULT 1,
    max_persons     INTEGER DEFAULT 1,
    base_price      REAL    DEFAULT 0,
    currency        TEXT    DEFAULT 'PLN',
    booking_unit    TEXT    DEFAULT 'per_person',  -- per_person | per_group | per_session | per_day
    included_pl     TEXT    DEFAULT '',
    included_en     TEXT    DEFAULT '',
    excluded_pl     TEXT    DEFAULT '',
    excluded_en     TEXT    DEFAULT '',
    requirements_pl TEXT    DEFAULT '',
    requirements_en TEXT    DEFAULT '',
    weather_note_pl TEXT    DEFAULT '',
    weather_note_en TEXT    DEFAULT '',
    cancel_policy   TEXT    DEFAULT 'Bezplatna anulacja do 7 dni przed zajęciami. Po tym terminie — 50% oplaty. Brak zwrotu ponizej 24h.',
    is_active       INTEGER DEFAULT 1,
    sort_order      INTEGER DEFAULT 0,
    created_at      TEXT    DEFAULT (datetime('now'))
);

-- ── BOOKINGS ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bookings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_ref         TEXT    UNIQUE NOT NULL,      -- FLH-2026-0001
    service_id          INTEGER NOT NULL,
    service_name        TEXT    NOT NULL,              -- snapshot at booking time
    location            TEXT    NOT NULL,              -- hurghada | hel
    customer_name       TEXT    NOT NULL,
    customer_email      TEXT    NOT NULL,
    customer_phone      TEXT    DEFAULT '',
    customer_level      TEXT    DEFAULT '',            -- beginner | basic | intermediate | advanced
    persons             INTEGER DEFAULT 1,
    preferred_dates     TEXT    DEFAULT '',            -- free text from customer
    start_date          TEXT    DEFAULT '',            -- YYYY-MM-DD after confirmation
    start_time          TEXT    DEFAULT '',            -- HH:MM
    duration_hours      REAL    DEFAULT 2,
    total_price         REAL    DEFAULT 0,
    currency            TEXT    DEFAULT 'PLN',
    booking_status      TEXT    DEFAULT 'pending',     -- pending | confirmed | completed | cancelled | no_show
    payment_status      TEXT    DEFAULT 'unpaid',      -- unpaid | deposit_paid | paid | refunded
    payment_method      TEXT    DEFAULT '',            -- transfer | card | cash | online
    notes               TEXT    DEFAULT '',
    special_requests    TEXT    DEFAULT '',
    instructor          TEXT    DEFAULT '',
    language            TEXT    DEFAULT 'pl',
    source              TEXT    DEFAULT 'website',     -- website | instagram | whatsapp | viator | email | phone
    external_booking_id TEXT    DEFAULT '',            -- Viator / external channel ID
    external_channel    TEXT    DEFAULT '',
    created_at          TEXT    DEFAULT (datetime('now')),
    updated_at          TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY (service_id) REFERENCES booking_services(id)
);

-- ── BOOKING EVENTS (audit log) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS booking_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_ref TEXT NOT NULL,
    event_type  TEXT NOT NULL,  -- created | confirmed | cancelled | payment_received | reminder_sent | note_added
    event_data  TEXT DEFAULT '', -- JSON string
    created_by  TEXT DEFAULT 'system',   -- system | admin | customer
    created_at  TEXT DEFAULT (datetime('now'))
);

-- ── AVAILABILITY BLOCKS ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS availability_blocks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id  INTEGER DEFAULT NULL,   -- NULL = all services
    location    TEXT    DEFAULT NULL,   -- NULL = all locations
    block_date  TEXT    NOT NULL,       -- YYYY-MM-DD
    block_time  TEXT    DEFAULT NULL,   -- HH:MM or NULL = full day
    reason      TEXT    DEFAULT '',     -- weather | holiday | full | maintenance
    created_at  TEXT    DEFAULT (datetime('now'))
);

-- ── INDEXES ────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_bookings_ref    ON bookings(booking_ref);
CREATE INDEX IF NOT EXISTS idx_bookings_email  ON bookings(customer_email);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(booking_status);
CREATE INDEX IF NOT EXISTS idx_bookings_date   ON bookings(start_date);
CREATE INDEX IF NOT EXISTS idx_events_ref      ON booking_events(booking_ref);
CREATE INDEX IF NOT EXISTS idx_avail_date      ON availability_blocks(block_date);
"""

SEED_SERVICES = [
    # slug, name_pl, name_en, subtitle_pl, subtitle_en, description_pl, description_en,
    # category, location, duration_hours, min_p, max_p, price, currency, unit,
    # included_pl, included_en, excluded_pl, excluded_en, requirements_pl, requirements_en,
    # weather_note_pl, weather_note_en, sort_order
    {
        "slug": "private-lesson",
        "name_pl": "Lekcja Prywatna Kitesurfingu",
        "name_en": "Private Kitesurfing Lesson",
        "subtitle_pl": "Indywidualny trening z certyfikowanym instruktorem",
        "subtitle_en": "One-on-one training with a certified instructor",
        "description_pl": "Lekcja prywatna to najszybsza droga do postępu na desce. Twój własny instruktor skupia się wyłącznie na Tobie — analizuje styl, koryguje błędy i dobiera program dokładnie pod Twój poziom. Idealna dla osób, które chcą szybko przejść na wyższy poziom lub mają specyficzne cele (skok, body drag, poprawienie techniczne).",
        "description_en": "A private lesson is the fastest path to progression on the board. Your dedicated instructor focuses entirely on you — analyzing your style, correcting mistakes, and tailoring the program to your level. Perfect for riders who want to level up fast or have specific goals (jumps, body drag, technical improvement).",
        "category": "lesson",
        "location": "both",
        "duration_hours": 2.0,
        "min_persons": 1,
        "max_persons": 1,
        "base_price": 450,
        "currency": "PLN",
        "booking_unit": "per_session",
        "included_pl": "Sprzęt kite + deska + trapez, instruktor, ubezpieczenie na czas zajęć, materiały safety brief",
        "included_en": "Kite + board + harness, instructor, session insurance, safety brief",
        "excluded_pl": "Transport na plażę, napoje, zdjęcia/wideo",
        "excluded_en": "Beach transport, drinks, photos/video",
        "requirements_pl": "Umiejętność pływania, minimum 16 lat (lub za zgoda rodziców)",
        "requirements_en": "Swimming ability, minimum age 16 (or parental consent)",
        "weather_note_pl": "Zajęcia zależne od warunków wietrznych (min. 12 węzłów). W razie braku wiatru oferujemy zmianę terminu.",
        "weather_note_en": "Session depends on wind conditions (min. 12 knots). If wind is insufficient we reschedule at no extra cost.",
        "sort_order": 1,
    },
    {
        "slug": "group-lesson",
        "name_pl": "Lekcja Grupowa Kitesurfingu",
        "name_en": "Group Kitesurfing Lesson",
        "subtitle_pl": "Nauka z przyjaciółmi lub nowymi znajomymi z plaży",
        "subtitle_en": "Learn with friends or new beach crew",
        "description_pl": "Lekcja grupowa łączy świetną atmosferę z profesjonalnym instruktażem. Grupy są małe — maksymalnie 4 osoby — dzięki czemu każdy uczestnik otrzymuje pełną uwagę instruktora. Wspólna nauka motywuje i przyspiesza progres. Polecana osobom na podobnym poziomie zaawansowania.",
        "description_en": "Group lessons combine great atmosphere with professional coaching. Groups are small — maximum 4 people — so every participant gets full instructor attention. Learning together motivates and speeds up progression. Recommended for people at a similar skill level.",
        "category": "lesson",
        "location": "both",
        "duration_hours": 2.0,
        "min_persons": 2,
        "max_persons": 4,
        "base_price": 280,
        "currency": "PLN",
        "booking_unit": "per_person",
        "included_pl": "Sprzęt kite + deska + trapez, instruktor grupowy, ubezpieczenie, safety brief",
        "included_en": "Kite + board + harness, group instructor, insurance, safety brief",
        "excluded_pl": "Transport, napoje",
        "excluded_en": "Transport, drinks",
        "requirements_pl": "Umiejętność pływania, minimum 16 lat",
        "requirements_en": "Swimming ability, minimum age 16",
        "weather_note_pl": "Zależy od wiatru (min. 12 węzłów). W razie braku wiatru — zmiana terminu.",
        "weather_note_en": "Wind-dependent (min. 12 knots). No wind = free reschedule.",
        "sort_order": 2,
    },
    {
        "slug": "beginner-course",
        "name_pl": "Kurs dla Początkujących",
        "name_en": "Beginner Kite Course",
        "subtitle_pl": "Od zera do pierwszych jazd w 3 dni",
        "subtitle_en": "From zero to first rides in 3 days",
        "description_pl": "Nasz flagowy kurs startowy. W ciągu 3 dni (9 godzin na wodzie) poznasz podstawy latawca, body drag, water start i pierwsze jazdy na desce. Program oparty na metodyce IKO (Międzynarodowa Organizacja Kiteboardingu). Instruktor prowadzi Cię od teorii do pierwszego samodzielnego przejścia przez wodę. Po kursie — możesz jeździć na własnym sprzęcie!",
        "description_en": "Our flagship starter course. In 3 days (9 hours on the water) you'll master kite control, body drag, water start, and first board rides. Program based on IKO methodology. Your instructor guides you from theory to first independent run. After the course — you can ride on your own gear!",
        "category": "course",
        "location": "both",
        "duration_hours": 9.0,
        "min_persons": 1,
        "max_persons": 4,
        "base_price": 1100,
        "currency": "PLN",
        "booking_unit": "per_person",
        "included_pl": "9h nauki (3x3h), sprzęt szkolny, instruktor IKO, certyfikat IKO, ubezpieczenie, safety brief",
        "included_en": "9h training (3x3h), school gear, IKO instructor, IKO certificate, insurance, safety brief",
        "excluded_pl": "Nocleg, wyżywienie, transport",
        "excluded_en": "Accommodation, meals, transport",
        "requirements_pl": "Umiejętność pływania, dobra kondycja fizyczna, min. 16 lat",
        "requirements_en": "Swimming ability, good physical condition, min. 16 years old",
        "weather_note_pl": "Kurs rozłożony na 3 dni — elastyczny grafik dostosowany do prognoz wiatru.",
        "weather_note_en": "Course spread over 3 days — flexible schedule adapts to wind forecast.",
        "sort_order": 3,
    },
    {
        "slug": "progression-course",
        "name_pl": "Kurs Progression / Intermediate",
        "name_en": "Progression / Intermediate Course",
        "subtitle_pl": "Dla tych, którzy już jeżdżą — czas na kolejny poziom",
        "subtitle_en": "For riders who already ride — time for the next level",
        "description_pl": "Masz już podstawy, ale chcesz jechać ostrzej, wykonywać jumpy lub wreszcie zmienić kierunek? Ten kurs jest dla Ciebie. Pracujemy nad techniką, transitions, pierwszymi skokami i zaawansowanymi manewrami. Program dostosowany indywidualnie — na pierwsze spotkanie przynosisz swój poziom, my budujemy plan.",
        "description_en": "You already have the basics but want to ride harder, jump, or finally change direction? This course is for you. We work on technique, transitions, first jumps and advanced maneuvers. Program tailored individually — bring your level, we build the plan.",
        "category": "course",
        "location": "both",
        "duration_hours": 6.0,
        "min_persons": 1,
        "max_persons": 3,
        "base_price": 850,
        "currency": "PLN",
        "booking_unit": "per_person",
        "included_pl": "6h treningu (2x3h), sprzęt, instruktor, analiza wideo (opcja), ubezpieczenie",
        "included_en": "6h training (2x3h), gear, instructor, video analysis (optional), insurance",
        "excluded_pl": "Nocleg, wyżywienie, transport",
        "excluded_en": "Accommodation, meals, transport",
        "requirements_pl": "Samodzielna jazda w obie strony (body drag + water start zaliczone)",
        "requirements_en": "Ability to ride both directions (body drag + water start done)",
        "weather_note_pl": "Idealne warunki: 15-20 węzłów. Dostosujemy terminy do prognozy.",
        "weather_note_en": "Ideal: 15-20 knots. We'll match session times to the forecast.",
        "sort_order": 4,
    },
    {
        "slug": "gear-test",
        "name_pl": "Test Sprzętu Kite",
        "name_en": "Kite Gear Test Session",
        "subtitle_pl": "Przetestuj latawce Cabrinha zanim kupisz",
        "subtitle_en": "Try Cabrinha kites before you buy",
        "description_pl": "Zastanawiasz się nad zakupem nowego latawca lub deski? Oferujemy sesję testową, podczas której możesz przetestować różne modele ze stocku Cabrinha. Instruktor pomoże dobrać sprzęt do Twojego stylu jazdy i warunków. Idealne dla jeżdżących samodzielnie, którzy chcą świadomie wybrać własny zestaw.",
        "description_en": "Thinking about buying a new kite or board? We offer test sessions where you can try different Cabrinha models from our stock. Our instructor helps match gear to your riding style and conditions. Perfect for independent riders who want to make an informed purchase.",
        "category": "experience",
        "location": "both",
        "duration_hours": 1.5,
        "min_persons": 1,
        "max_persons": 1,
        "base_price": 250,
        "currency": "PLN",
        "booking_unit": "per_session",
        "included_pl": "Sprzęt testowy (Cabrinha), krótki briefing, czas na wodzie",
        "included_en": "Test gear (Cabrinha), short briefing, water time",
        "excluded_pl": "Instruktaż (chyba że dokupiony), transport",
        "excluded_en": "Instruction (unless added), transport",
        "requirements_pl": "Samodzielna jazda — kurs IKO level 3 lub odpowiednik",
        "requirements_en": "Independent rider — IKO level 3 or equivalent",
        "weather_note_pl": "Min. 12 węzłów. Sesja dostosowana do warunków dnia.",
        "weather_note_en": "Min. 12 knots. Session adjusted to daily conditions.",
        "sort_order": 5,
    },
    {
        "slug": "kite-camp",
        "name_pl": "Obóz Kitesurfingowy",
        "name_en": "Kite Camp",
        "subtitle_pl": "Tygodniowy intensywny trening dla grup i indywidualistów",
        "subtitle_en": "Week-long intensive training for groups and solo riders",
        "description_pl": "Tygodniowy kamp kite to idealne połączenie intensywnej nauki z doskonałą atmosferą. Rano trening na wodzie, wieczorami sesje teorii, analizy wideo i imprezowanie z ekipą. W Polsce: Jastarnia w lipcu/sierpniu. W Egipcie: Hurghada od października do marca. Grupy do 12 osób. Transport z lotniska opcjonalnie.",
        "description_en": "A kite camp is the perfect combination of intensive training and great atmosphere. Morning water sessions, evenings for theory, video analysis and hanging out with the crew. In Poland: Jastarnia July/August. In Egypt: Hurghada October to March. Groups up to 12. Airport transfer optional.",
        "category": "camp",
        "location": "both",
        "duration_hours": 20.0,
        "min_persons": 1,
        "max_persons": 12,
        "base_price": 2500,
        "currency": "PLN",
        "booking_unit": "per_person",
        "included_pl": "7 dni, ~20h na wodzie, sprzęt, instruktorzy, teoria, wieczorne sesje, certyfikat, welcome pack",
        "included_en": "7 days, ~20h on water, gear, instructors, theory, evening sessions, certificate, welcome pack",
        "excluded_pl": "Nocleg (opcja dokupienia), loty, wyżywienie",
        "excluded_en": "Accommodation (optional add-on), flights, meals",
        "requirements_pl": "Brak (program dla każdego poziomu — grupy są podzielone poziomowo)",
        "requirements_en": "None required (program for all levels — groups split by level)",
        "weather_note_pl": "W Polsce: sezon VII-VIII. W Egipcie: X-III. Obozy planowane w oknach wietrznych.",
        "weather_note_en": "Poland: season Jul-Aug. Egypt: Oct-Mar. Camps scheduled in wind windows.",
        "sort_order": 6,
    },
    {
        "slug": "stay-kite-package",
        "name_pl": "Pakiet Nocleg + Kite",
        "name_en": "Stay + Kite Package",
        "subtitle_pl": "Wszystko w jednym — zakwaterowanie, kurs i plaża",
        "subtitle_en": "All-in-one — accommodation, course, and beach life",
        "description_pl": "Nasz pakiet all-inclusive to najprostszy sposób na urlop kitesurfingowy. Dobierasz długość pobytu (minimum 5 nocy), poziom kursu i liczbę osób — my zajmujemy się resztą. Współpracujemy ze sprawdzonymi apartamentami i hotelami w okolicy szkoły. Hurghada: pakiety Żółty, Srebrny i Złoty. Polska: pakiety sezonowe na Helu.",
        "description_en": "Our all-inclusive package is the easiest way to plan a kite holiday. Choose your stay length (minimum 5 nights), course level and number of people — we handle the rest. We work with verified apartments and hotels near the school. Hurghada: Yellow, Silver and Gold packages. Poland: seasonal packages on the Hel Peninsula.",
        "category": "package",
        "location": "both",
        "duration_hours": 0,
        "min_persons": 1,
        "max_persons": 10,
        "base_price": 2300,
        "currency": "PLN",
        "booking_unit": "per_person",
        "included_pl": "Nocleg (5-14 nocy), kurs kite (wg pakietu), sprzęt, instruktor, ubezpieczenie aktywności",
        "included_en": "Accommodation (5-14 nights), kite course (per package), gear, instructor, activity insurance",
        "excluded_pl": "Loty, wyżywienie, visa (Egipt: bezwizowo dla Polaków)",
        "excluded_en": "Flights, meals, visa (Egypt: visa-free for most EU citizens)",
        "requirements_pl": "Brak — pakiet dostępny dla wszystkich poziomów",
        "requirements_en": "None — package available for all levels",
        "weather_note_pl": "Hurghada: stały wiatr 15-25 węzłów przez cały sezon. Polska: uzależnione od sezonu letniego.",
        "weather_note_en": "Hurghada: consistent 15-25 knots throughout the season. Poland: seasonal summer wind.",
        "sort_order": 7,
    },
    {
        "slug": "custom-session",
        "name_pl": "Sesja Indywidualna (Custom)",
        "name_en": "Custom / Tailor-made Session",
        "subtitle_pl": "Tworzysz program razem z instruktorem",
        "subtitle_en": "Build your own program with the instructor",
        "description_pl": "Masz specyficzne potrzeby, które nie pasują do żadnego z naszych standardowych produktów? Napisz do nas i zaprojektujemy sesję specjalnie dla Ciebie. Fotosesja na kitach, specjalistyczny trening techniczny, sesja dla dwójki z różnymi poziomami, nauka konkretnej sztuczki — możemy to zorganizować.",
        "description_en": "Have specific needs that don't fit our standard products? Write to us and we'll design a session just for you. Photoshoot on kites, specialist technical training, session for two with different levels, learning a specific trick — we can organize it.",
        "category": "experience",
        "location": "both",
        "duration_hours": 0,
        "min_persons": 1,
        "max_persons": 8,
        "base_price": 0,
        "currency": "PLN",
        "booking_unit": "per_session",
        "included_pl": "Zależy od wybranego programu — ustalamy indywidualnie",
        "included_en": "Depends on chosen program — agreed individually",
        "excluded_pl": "Transport, wyżywienie, nocleg",
        "excluded_en": "Transport, meals, accommodation",
        "requirements_pl": "Brak — dopasowujemy do Ciebie",
        "requirements_en": "None — we adapt to you",
        "weather_note_pl": "Planujemy z wyprzedzeniem, uwzględniając prognozy wiatru.",
        "weather_note_en": "Planned in advance considering wind forecasts.",
        "sort_order": 8,
    },
]


# ---------------------------------------------------------------------------
# Init & connection
# ---------------------------------------------------------------------------

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    """Create tables and seed services if empty."""
    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)
        # Seed default services if table is empty
        row = conn.execute("SELECT COUNT(*) FROM booking_services").fetchone()
        if row[0] == 0:
            for svc in SEED_SERVICES:
                conn.execute("""
                    INSERT INTO booking_services
                        (slug, name_pl, name_en, subtitle_pl, subtitle_en,
                         description_pl, description_en, category, location,
                         duration_hours, min_persons, max_persons, base_price,
                         currency, booking_unit, included_pl, included_en,
                         excluded_pl, excluded_en, requirements_pl, requirements_en,
                         weather_note_pl, weather_note_en, sort_order)
                    VALUES
                        (:slug,:name_pl,:name_en,:subtitle_pl,:subtitle_en,
                         :description_pl,:description_en,:category,:location,
                         :duration_hours,:min_persons,:max_persons,:base_price,
                         :currency,:booking_unit,:included_pl,:included_en,
                         :excluded_pl,:excluded_en,:requirements_pl,:requirements_en,
                         :weather_note_pl,:weather_note_en,:sort_order)
                """, svc)


# ---------------------------------------------------------------------------
# Booking reference generator
# ---------------------------------------------------------------------------

def _next_ref() -> str:
    year = datetime.now().year
    rand = "".join(random.choices(string.digits, k=4))
    return f"FLH-{year}-{rand}"


def _unique_ref(conn: sqlite3.Connection) -> str:
    for _ in range(20):
        ref = _next_ref()
        exists = conn.execute(
            "SELECT 1 FROM bookings WHERE booking_ref = ?", (ref,)
        ).fetchone()
        if not exists:
            return ref
    raise RuntimeError("Could not generate unique booking ref")


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

def list_services(location: Optional[str] = None) -> list[dict]:
    with get_conn() as conn:
        if location:
            rows = conn.execute(
                "SELECT * FROM booking_services WHERE is_active=1 AND (location=? OR location='both') ORDER BY sort_order",
                (location,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM booking_services WHERE is_active=1 ORDER BY sort_order"
            ).fetchall()
        return [dict(r) for r in rows]


def get_service_by_slug(slug: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM booking_services WHERE slug=? AND is_active=1", (slug,)
        ).fetchone()
        return dict(row) if row else None


def get_service_by_id(service_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM booking_services WHERE id=?", (service_id,)
        ).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Bookings — create
# ---------------------------------------------------------------------------

def create_booking(data: dict) -> dict:
    """
    data keys: service_id, location, customer_name, customer_email,
               customer_phone, customer_level, persons, preferred_dates,
               notes, special_requests, language, source
    Returns the created booking dict.
    """
    service = get_service_by_id(data["service_id"])
    if not service:
        raise ValueError(f"Service {data['service_id']} not found")

    persons = int(data.get("persons", 1))
    unit = service["booking_unit"]
    price = service["base_price"]

    if unit == "per_person":
        total = price * persons
    elif unit in ("per_session", "per_group"):
        total = price
    elif unit == "per_day":
        total = price
    else:
        total = price * persons

    with get_conn() as conn:
        ref = _unique_ref(conn)
        conn.execute("""
            INSERT INTO bookings
                (booking_ref, service_id, service_name, location,
                 customer_name, customer_email, customer_phone,
                 customer_level, persons, preferred_dates,
                 duration_hours, total_price, currency,
                 notes, special_requests, language, source,
                 booking_status, payment_status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'pending','unpaid')
        """, (
            ref, service["id"], service["name_pl"],
            data.get("location", service["location"]),
            data["customer_name"], data["customer_email"],
            data.get("customer_phone", ""),
            data.get("customer_level", ""),
            persons,
            data.get("preferred_dates", ""),
            service["duration_hours"],
            total, service["currency"],
            data.get("notes", ""),
            data.get("special_requests", ""),
            data.get("language", "pl"),
            data.get("source", "website"),
        ))
        _log_event(conn, ref, "created", f'{{"service":"{service["name_pl"]}","persons":{persons}}}')
        row = conn.execute("SELECT * FROM bookings WHERE booking_ref=?", (ref,)).fetchone()
        return dict(row)


# ---------------------------------------------------------------------------
# Bookings — read
# ---------------------------------------------------------------------------

def get_booking(booking_ref: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM bookings WHERE booking_ref=?", (booking_ref,)
        ).fetchone()
        return dict(row) if row else None


def list_bookings(
    status: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    clauses, params = [], []
    if status:
        clauses.append("booking_status=?")
        params.append(status)
    if location:
        clauses.append("location=?")
        params.append(location)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params += [limit, offset]
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM bookings {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def get_booking_events(booking_ref: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM booking_events WHERE booking_ref=? ORDER BY created_at",
            (booking_ref,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Bookings — update
# ---------------------------------------------------------------------------

def update_booking_status(
    booking_ref: str,
    booking_status: str,
    by: str = "admin",
    extra_data: str = "",
) -> bool:
    allowed = {"pending", "confirmed", "completed", "cancelled", "no_show"}
    if booking_status not in allowed:
        raise ValueError(f"Invalid status: {booking_status}")
    with get_conn() as conn:
        n = conn.execute(
            "UPDATE bookings SET booking_status=?, updated_at=datetime('now') WHERE booking_ref=?",
            (booking_status, booking_ref),
        ).rowcount
        if n:
            _log_event(conn, booking_ref, booking_status, extra_data, by)
        return bool(n)


def update_payment_status(
    booking_ref: str,
    payment_status: str,
    payment_method: str = "",
    by: str = "admin",
) -> bool:
    allowed = {"unpaid", "deposit_paid", "paid", "refunded"}
    if payment_status not in allowed:
        raise ValueError(f"Invalid payment status: {payment_status}")
    with get_conn() as conn:
        n = conn.execute(
            """UPDATE bookings
               SET payment_status=?, payment_method=?, updated_at=datetime('now')
               WHERE booking_ref=?""",
            (payment_status, payment_method, booking_ref),
        ).rowcount
        if n:
            _log_event(conn, booking_ref, "payment_received",
                       f'{{"status":"{payment_status}","method":"{payment_method}"}}', by)
        return bool(n)


def confirm_booking_dates(
    booking_ref: str,
    start_date: str,
    start_time: str,
    instructor: str = "",
    by: str = "admin",
) -> bool:
    with get_conn() as conn:
        n = conn.execute(
            """UPDATE bookings
               SET start_date=?, start_time=?, instructor=?,
                   booking_status='confirmed', updated_at=datetime('now')
               WHERE booking_ref=?""",
            (start_date, start_time, instructor, booking_ref),
        ).rowcount
        if n:
            _log_event(conn, booking_ref, "confirmed",
                       f'{{"date":"{start_date}","time":"{start_time}","instructor":"{instructor}"}}', by)
        return bool(n)


def add_note(booking_ref: str, note: str, by: str = "admin") -> bool:
    with get_conn() as conn:
        n = conn.execute(
            "UPDATE bookings SET notes=notes||char(10)||?, updated_at=datetime('now') WHERE booking_ref=?",
            (note, booking_ref),
        ).rowcount
        if n:
            _log_event(conn, booking_ref, "note_added", f'{{"note":"{note[:80]}"}}', by)
        return bool(n)


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

def is_date_blocked(
    date_str: str,
    service_id: Optional[int] = None,
    location: Optional[str] = None,
) -> bool:
    with get_conn() as conn:
        # Check full-day blocks for this service or global
        params: list = [date_str]
        row = conn.execute("""
            SELECT 1 FROM availability_blocks
            WHERE block_date=?
              AND (service_id IS NULL OR service_id=?)
              AND (location IS NULL OR location=?)
            LIMIT 1
        """, (date_str, service_id, location)).fetchone()
        return row is not None


def block_date(
    date_str: str,
    reason: str = "maintenance",
    service_id: Optional[int] = None,
    location: Optional[str] = None,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO availability_blocks (service_id, location, block_date, reason) VALUES (?,?,?,?)",
            (service_id, location, date_str, reason),
        )
        return cur.lastrowid


def list_blocked_dates(
    start: str,
    end: str,
    location: Optional[str] = None,
) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM availability_blocks
               WHERE block_date BETWEEN ? AND ?
                 AND (location IS NULL OR location=?)
               ORDER BY block_date""",
            (start, end, location),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _log_event(
    conn: sqlite3.Connection,
    booking_ref: str,
    event_type: str,
    event_data: str = "",
    created_by: str = "system",
):
    conn.execute(
        "INSERT INTO booking_events (booking_ref, event_type, event_data, created_by) VALUES (?,?,?,?)",
        (booking_ref, event_type, event_data, created_by),
    )
