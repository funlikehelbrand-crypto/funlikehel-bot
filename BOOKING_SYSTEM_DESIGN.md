# FUN like HEL — Booking System Design
## Architecture, Data Model, API Integration Strategy

---

## PHASE 1 — AUDIT SUMMARY

### What already exists

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI backend | ✅ Production | Render, Python 3.12 |
| AI agent (Alicja) | ✅ Active | Claude sonnet-4-6, multi-channel |
| Instagram / WhatsApp | ✅ Active | Webhooks live |
| Gmail / YouTube / GBP | ✅ Active | Polling loops |
| SMS (SerwerSMS) | ✅ Active | Campaigns + reminders |
| WordPress site | ✅ Live | funlikehel.pl |
| Egypt booking form | ⚠️ Partial | Single form, no payment, no admin UI |
| Team signup form | ✅ Working | saves to ekipa.db |
| Conversation memory | ✅ SQLite | Per-user 30-day history |
| Payment | ❌ Missing | All payments handled offline |
| Admin dashboard | ❌ Missing | No booking management UI |
| Availability management | ❌ Missing | No calendar, no capacity limits |
| Confirmation emails | ❌ Missing | Manual follow-up only |
| Multi-service structure | ❌ Missing | Only one hardcoded Egypt form |

### Gaps

1. No booking reference system
2. No booking status lifecycle
3. No admin view of bookings
4. No service catalog with clean data model
5. No availability/calendar
6. No payment integration
7. No automated confirmation workflow
8. No external channel (Viator) integration layer

---

## PHASE 2 — COMMERCIAL PRODUCT STRUCTURE

### Service catalog (8 products)

| Slug | Name | Category | Location | Duration | Price from | Unit |
|------|------|----------|----------|----------|-----------|------|
| `private-lesson` | Lekcja Prywatna | lesson | both | 2h | 450 PLN | per_session |
| `group-lesson` | Lekcja Grupowa | lesson | both | 2h | 280 PLN | per_person |
| `beginner-course` | Kurs dla Początkujących | course | both | 9h | 1 100 PLN | per_person |
| `progression-course` | Kurs Progression | course | both | 6h | 850 PLN | per_person |
| `gear-test` | Test Sprzętu Kite | experience | both | 1.5h | 250 PLN | per_session |
| `kite-camp` | Obóz Kitesurfingowy | camp | both | 20h | 2 500 PLN | per_person |
| `stay-kite-package` | Pakiet Nocleg + Kite | package | both | variable | 2 300 PLN | per_person |
| `custom-session` | Sesja Indywidualna | experience | both | variable | quote | per_session |

**Pricing logic:**
- `per_person`: `total = base_price × persons`
- `per_session` / `per_group`: `total = base_price` (flat)
- `per_day`: `total = base_price × days`

---

## PHASE 3 — BOOKING DATA MODEL

### Database: `bookings.db` (SQLite)

#### Table: `booking_services`
Stores the product catalog. Seeded automatically on startup.
Can be extended without code changes by inserting rows.

```
id, slug, name_pl, name_en, subtitle_pl, subtitle_en,
description_pl, description_en, category, location,
duration_hours, min_persons, max_persons,
base_price, currency, booking_unit,
included_pl, included_en, excluded_pl, excluded_en,
requirements_pl, requirements_en,
weather_note_pl, weather_note_en,
cancel_policy, is_active, sort_order, created_at
```

#### Table: `bookings`
Core booking record.

```
id, booking_ref (FLH-YYYY-NNNN), service_id, service_name (snapshot),
location, customer_name, customer_email, customer_phone,
customer_level, persons, preferred_dates,
start_date, start_time, duration_hours,
total_price, currency,
booking_status, payment_status, payment_method,
notes, special_requests, instructor, language,
source, external_booking_id, external_channel,
created_at, updated_at
```

#### Table: `booking_events`
Immutable audit log of every status change.

```
id, booking_ref, event_type, event_data (JSON), created_by, created_at
```

Event types: `created | confirmed | completed | cancelled | no_show | payment_received | reminder_sent | note_added`

#### Table: `availability_blocks`
Dates/times that are unavailable (weather, full, holiday).

```
id, service_id (NULL=all), location (NULL=all),
block_date, block_time (NULL=full day),
reason, created_at
```

### Booking status lifecycle

```
[new customer] → pending
    ↓ admin confirms + sets date
confirmed
    ↓ session completed
completed
    ↓ (or)
cancelled / no_show
```

### Payment status lifecycle

```
unpaid → deposit_paid → paid
         ↓
       refunded
```

### Validation rules

- `persons` must be within `[min_persons, max_persons]` of service
- `location` must match service location (`hurghada | hel | both`)
- `customer_email` must be valid email
- `customer_name` minimum 2 characters
- `booking_status` transitions must be valid (no jumping to completed from pending)
- Duplicate `external_booking_id + external_channel` → return existing booking, do not create duplicate

### Assumptions

- No real-time availability check for MVP — admin manages manually
- Prices are PLN by default; EUR supported for Viator integration
- No partial-day blocking in MVP (full-day blocks only)
- Service prices are approximate — final price confirmed by admin

---

## PHASE 4 — MVP BOOKING SYSTEM

### Files created

| File | Purpose |
|------|---------|
| `server/booking_db.py` | Database layer: init, CRUD, availability |
| `server/booking.py` | FastAPI router: public + admin + channel endpoints |
| `server/wp-plugin/funlikehel-booking-v2.php` | WordPress plugin: admin panel + `[flh_booking_form]` shortcode |
| `server/main.py` | Updated: includes booking router, calls `init_db()` |

### API endpoints

**Public:**
```
GET  /api/services                     List active services (filter: ?location=hurghada)
GET  /api/services/{slug}              Single service detail
POST /api/bookings                     Create booking request → returns booking_ref
GET  /api/bookings/{ref}               Customer status check
```

**Admin** (requires `X-Admin-Token` header):
```
GET  /api/admin/bookings               List bookings (filter: ?status=pending&location=hurghada)
GET  /api/admin/bookings/{ref}         Full booking + event history
POST /api/admin/bookings/{ref}/confirm Set date + time + instructor → status=confirmed
POST /api/admin/bookings/{ref}/status  Change status manually
POST /api/admin/bookings/{ref}/payment Update payment status + method
POST /api/admin/bookings/{ref}/note    Add internal note
GET  /api/admin/availability           List blocked dates (params: start, end, location)
POST /api/admin/availability/block     Block a date
```

**Channel integration:**
```
POST /api/channel/booking              External channel (Viator) creates booking
                                       Requires X-Channel-Secret header
```

### WordPress integration

Install `funlikehel-booking-v2.php` as a plugin, then:

1. Go to **WordPress Admin → Rezerwacje → Ustawienia API**
2. Set API base URL: `https://funlikehel-bot.onrender.com`
3. Set Admin Token (same as `BOOKING_ADMIN_TOKEN` in `api.env`)
4. Embed form on any page: `[flh_booking_form location="hurghada"]`
5. View all bookings at **Admin → Rezerwacje**

### Booking flow (MVP)

```
Customer visits page with [flh_booking_form]
    ↓
Selects service from grid (loaded via GET /api/services)
    ↓
Fills form (name, email, phone, level, persons, dates, notes)
    ↓
POST /api/bookings → gets booking_ref (FLH-2026-XXXX)
    ↓
Confirmation message shown + booking_ref
    ↓
Email notification to funlikehelbrand@gmail.com (TODO: implement)
    ↓
Admin reviews in WordPress Rezerwacje panel
    ↓
Admin calls POST /api/admin/bookings/{ref}/confirm with date + instructor
    ↓
Customer receives confirmation (TODO: automated email)
    ↓
Manual payment (transfer, cash on arrival)
    ↓
Admin marks POST /api/admin/bookings/{ref}/payment → paid
    ↓
Session happens
    ↓
Admin marks status → completed
```

### New environment variables required

Add to `server/api.env`:

```bash
# Booking System
BOOKING_ADMIN_TOKEN=generate-a-strong-random-token-here
CHANNEL_BOOKING_SECRET=generate-another-secret-for-viator
```

---

## PHASE 5 — EXTERNAL CHANNEL INTEGRATION STRATEGY

### Design principles

1. **Internal IDs are authoritative.** External channel IDs are stored alongside, never replace internal `booking_ref`.
2. **Idempotency.** `POST /api/channel/booking` with duplicate `external_booking_id + channel` returns existing booking silently.
3. **No fake integrations.** The `external_channel` field and `/api/channel/booking` endpoint are the integration points — actual channel webhooks map onto them.
4. **Price reconciliation.** External price is stored (`external_price`, `external_currency`) separately from internal price for accounting.

### Channel mapping strategy

```python
# When Viator sends a booking:
{
    "channel": "viator",
    "external_booking_id": "BR-VT-12345678",
    "service_slug": "beginner-course",   # pre-agreed mapping
    "location": "hurghada",
    "customer_name": "...",
    ...
}

# We create internal booking:
{
    "booking_ref": "FLH-2026-8821",
    "external_booking_id": "BR-VT-12345678",
    "external_channel": "viator",
    ...
}
```

**Product slug mapping** (to be agreed with each channel):

| Channel | Channel product ID | Our slug |
|---------|-------------------|----------|
| Viator | `P123456` | `beginner-course` |
| Viator | `P123457` | `private-lesson` |
| Klook | `ACT-FLH-1` | `beginner-course` |

Store this mapping in a `channel_product_map` table (future phase).

### Availability sync strategy (future)

For channels that require real-time availability:

1. Expose `GET /api/availability/{service_slug}?month=2026-12` endpoint
2. Returns array of available/blocked dates
3. Channel polls or receives webhooks
4. When booking confirmed by admin → push update to channel

For MVP: manual sync (admin blocks dates in our system when sold out).

### Viator-specific notes

Viator requires:
- Product listing in Viator Supplier Center
- Unique product IDs mapped to our slugs
- Availability calendar feed (or real-time API)
- Booking confirmation webhook to our endpoint
- Cancellation handling (7-day policy standard)

**Viator cancellation policy recommendation:** Free cancellation 48h before start. After 48h: 50% fee. After 24h: no refund.

### Webhook / event strategy

For external notifications (future):

```
POST external_channel/webhook
    ↓ verify signature
    ↓ parse event type (booking.created | booking.cancelled | booking.modified)
    ↓ map to internal booking action
    ↓ log in booking_events
    ↓ notify admin (email / SMS / WhatsApp via Alicja)
```

Outbound webhooks (push to channel when status changes):
- Booking confirmed → push to channel
- Booking cancelled → push to channel with reason + refund policy

---

## PHASE 7 — PROFILE / LISTING STRUCTURE RECOMMENDATIONS

### Page structure for /egipt (booking landing page)

```
1. HERO
   - Full-width video or photo (kite in Hurghada, clear water)
   - Headline: "Naucz się kitesurfować w Hurghadzie"
   - Subheadline: "Certyfikowani instruktorzy | Mały grupy | Sprzęt Cabrinha"
   - CTA: "Zarezerwuj kurs →"

2. TRUST SIGNALS (horizontal strip)
   - IKO Certified
   - 1000+ kursantów
   - Aktywni od 2019
   - Sprzęt Cabrinha

3. SERVICE CARDS
   - Grid of 4 core offers
   - Each with: name, duration, price from, CTA "Wybierz →"

4. HOW IT WORKS (3 steps)
   - Zgłoś się online
   - Potwierdzamy w 24h
   - Pakujesz walizkę

5. BEGINNER SECTION
   - Headline: "Nigdy nie stałeś na desce? Idealne."
   - Description of beginner course
   - Before/after story or testimonial

6. ADVANCED SECTION
   - "Chcesz skakać? Mamy progression dla Ciebie."

7. PACKAGES (Hurghada)
   - Package comparison table (Yellow / Silver / Gold)

8. FAQ (accordion)

9. CONTACT / BOOKING FORM
   [flh_booking_form location="hurghada"]

10. FOOTER CTA
    "Zadzwoń teraz: 690 270 032"
```

### Listing title recommendations (Viator/GYG format)

**Primary (EN):**
> Beginner Kitesurfing Course in Hurghada — 3 Days, IKO Certified, Small Groups

**Alternative options:**
- Learn to Kitesurf in Hurghada — From Zero to First Rides (3-Day Course)
- Private Kitesurfing Lesson Hurghada — Certified Instructor, All Levels
- Kitesurf Beginner Course Hurghada — 9 Hours, IKO Certificate Included

### CTA wording that converts

| Context | CTA |
|---------|-----|
| Hero button | Zarezerwuj miejsce → |
| Service card | Sprawdź termin → |
| After description | Zadzwoń: 690 270 032 |
| Email footer | Odpiszemy w 24h |
| WhatsApp/IG | Napisz do nas! Odpowiadamy błyskawicznie 🤙 |
| Viator | Book Now — Free Cancellation 48h Before |

---

## PHASE 8 — TODO / OPEN QUESTIONS

### Must implement (MVP gap)

- [ ] **Automated confirmation email** — when admin confirms booking, send email to customer with date + instructor details
- [ ] **Admin SMS notification** — when new booking arrives, SMS to owner (infrastructure exists: `sms.py`)
- [ ] **Alicja booking awareness** — train Alicja to check booking status and mention it in chat
- [ ] **CORS for admin API** — `/api/admin/*` should be accessible from admin browser (not just WordPress server-side)
- [ ] **Pack `funlikehel-booking-v2.php` into `.zip`** — for easy WordPress upload

### Next phase

- [ ] Payment integration — Przelewy24 (Poland) + card (Hurghada)
- [ ] Calendar availability widget on booking form
- [ ] Automated reminder SMS 24h before session
- [ ] Viator product listing + webhook handler
- [ ] Customer self-service: cancel/modify booking link via email
- [ ] Dashboard stats: bookings per month, revenue, conversion rate

### Open questions (need owner's decision)

1. ~~**Cancellation policy**~~ ✅ Bezpłatna anulacja do 7 dni przed. 50% po 7 dniach. Brak zwrotu poniżej 24h.
2. **Prices** — are current prices (450/280/1100 PLN) correct for 2026 season?
3. ~~**Hurghada address**~~ ✅ FUNLIKEHEL EGYPT — Cabrinha Test Center, północna część Hurghady. GPS: 27.3347258, 33.6925064 | maps.app.goo.gl/31vLLyFcq4LbAwA96
4. **Accommodation partners** — which specific hotels/apartments for stay+kite packages?
5. **Instructor names** — for `instructor` field in confirmed bookings, what names/IDs to use?
6. **Egypt payments** — cash, card, or transfer? Mix?
7. **Viator contract** — have you started registration? What's the timeline?

---

## DEVELOPER README

### Setup

```bash
cd server
pip install -r requirements.txt

# Add to api.env:
# BOOKING_ADMIN_TOKEN=your-strong-secret-here
# CHANNEL_BOOKING_SECRET=another-secret-for-viator

uvicorn main:app --reload
```

The booking DB (`bookings.db`) is created automatically on first run.
Services are seeded automatically if the table is empty.

### Test the API

```bash
# List services
curl http://localhost:8000/api/services

# Create booking request
curl -X POST http://localhost:8000/api/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "service_slug": "beginner-course",
    "location": "hurghada",
    "customer_name": "Anna Nowak",
    "customer_email": "anna@example.com",
    "customer_phone": "+48 600 000 000",
    "customer_level": "beginner",
    "persons": 1,
    "preferred_dates": "10-15 February 2027",
    "language": "pl"
  }'

# Admin: list pending bookings
curl -H "X-Admin-Token: your-secret" \
  "http://localhost:8000/api/admin/bookings?status=pending"

# Admin: confirm booking
curl -X POST -H "X-Admin-Token: your-secret" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/admin/bookings/FLH-2026-XXXX/confirm \
  -d '{"start_date": "2027-02-11", "start_time": "09:00", "instructor": "Tomek"}'
```

### WordPress plugin install

1. Zip `server/wp-plugin/funlikehel-booking-v2.php`
2. Upload to WordPress → Plugins → Add New → Upload Plugin
3. Activate
4. Set API URL + admin token in WordPress Admin → Rezerwacje → settings
5. Use shortcode: `[flh_booking_form location="hurghada"]`

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOOKING_ADMIN_TOKEN` | Yes | Admin API token for protected endpoints |
| `CHANNEL_BOOKING_SECRET` | Optional | Secret for external channel webhook |
| `ANTHROPIC_API_KEY` | Yes | Claude AI (existing) |
| All existing vars | Yes | See `.env.example` |

---

*Document version: 1.0 — 2026-04-23*
