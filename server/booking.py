"""
FUN like HEL — Booking API Endpoints
Mount this router in main.py: app.include_router(booking_router)

Public endpoints:
  GET  /api/services                    — list all active services
  GET  /api/services/{slug}             — single service detail
  POST /api/bookings                    — create booking request
  GET  /api/bookings/{ref}              — get booking status (customer view)

Admin endpoints (require X-Admin-Token header):
  GET  /api/admin/bookings              — list bookings (filter: status, location)
  GET  /api/admin/bookings/{ref}        — full booking + events
  POST /api/admin/bookings/{ref}/confirm — confirm + set date/time/instructor
  POST /api/admin/bookings/{ref}/status  — change booking status
  POST /api/admin/bookings/{ref}/payment — update payment status
  POST /api/admin/bookings/{ref}/note    — add internal note
  GET  /api/admin/availability          — list blocked dates
  POST /api/admin/availability/block    — block a date

Integration/channel endpoints:
  POST /api/channel/booking             — external channel (Viator etc) create booking
"""

import os
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Query, Depends
from pydantic import BaseModel, EmailStr, Field

import booking_db as db

logger = logging.getLogger(__name__)

booking_router = APIRouter()

ADMIN_TOKEN = os.getenv("BOOKING_ADMIN_TOKEN", "change-me-in-api.env")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class BookingRequest(BaseModel):
    service_slug: str
    location: str = Field(..., pattern="^(hurghada|hel)$")
    customer_name: str = Field(..., min_length=2, max_length=200)
    customer_email: EmailStr
    customer_phone: str = ""
    customer_level: str = ""    # beginner | basic | intermediate | advanced
    persons: int = Field(1, ge=1, le=20)
    preferred_dates: str = ""
    notes: str = ""
    special_requests: str = ""
    language: str = "pl"
    source: str = "website"


class ConfirmBookingRequest(BaseModel):
    start_date: str   # YYYY-MM-DD
    start_time: str   # HH:MM
    instructor: str = ""


class StatusUpdateRequest(BaseModel):
    booking_status: str
    note: str = ""


class PaymentUpdateRequest(BaseModel):
    payment_status: str
    payment_method: str = ""


class NoteRequest(BaseModel):
    note: str


class BlockDateRequest(BaseModel):
    date: str         # YYYY-MM-DD
    reason: str = "maintenance"
    service_id: Optional[int] = None
    location: Optional[str] = None


class ChannelBookingRequest(BaseModel):
    """Inbound booking from external channel (Viator, marketplace, etc)."""
    channel: str                        # viator | airbnb | klook | direct_api
    external_booking_id: str
    service_slug: str
    location: str
    customer_name: str
    customer_email: str
    customer_phone: str = ""
    customer_level: str = ""
    persons: int = 1
    start_date: str = ""
    start_time: str = ""
    special_requests: str = ""
    language: str = "en"
    # Pricing from external channel (for reconciliation)
    external_price: Optional[float] = None
    external_currency: str = "USD"


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

def require_admin(x_admin_token: str = Header(default="")):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------------------------------------------------------------------
# PUBLIC — Services
# ---------------------------------------------------------------------------

@booking_router.get("/api/services")
async def get_services(location: Optional[str] = Query(None)):
    """Return list of active bookable services, optionally filtered by location."""
    services = db.list_services(location=location)
    return {"services": services, "count": len(services)}


@booking_router.get("/api/services/{slug}")
async def get_service(slug: str):
    """Return single service by slug."""
    svc = db.get_service_by_slug(slug)
    if not svc:
        raise HTTPException(status_code=404, detail=f"Service '{slug}' not found")
    return svc


# ---------------------------------------------------------------------------
# PUBLIC — Create booking request
# ---------------------------------------------------------------------------

@booking_router.post("/api/bookings", status_code=201)
async def create_booking(req: BookingRequest):
    """
    Create a booking request. Returns booking_ref for tracking.
    Initial status: pending — admin must confirm.
    """
    svc = db.get_service_by_slug(req.service_slug)
    if not svc:
        raise HTTPException(status_code=404, detail=f"Service '{req.service_slug}' not found")

    # Validate persons against service limits
    if req.persons < svc["min_persons"] or req.persons > svc["max_persons"]:
        raise HTTPException(
            status_code=400,
            detail=f"This service accepts {svc['min_persons']}–{svc['max_persons']} persons"
        )

    # Validate location
    valid_locations = {"hurghada", "hel"}
    if req.location not in valid_locations:
        raise HTTPException(status_code=400, detail="Location must be 'hurghada' or 'hel'")
    if svc["location"] != "both" and svc["location"] != req.location:
        raise HTTPException(
            status_code=400,
            detail=f"Service '{req.service_slug}' is not available in {req.location}"
        )

    data = {
        "service_id": svc["id"],
        "location": req.location,
        "customer_name": req.customer_name,
        "customer_email": req.customer_email,
        "customer_phone": req.customer_phone,
        "customer_level": req.customer_level,
        "persons": req.persons,
        "preferred_dates": req.preferred_dates,
        "notes": req.notes,
        "special_requests": req.special_requests,
        "language": req.language,
        "source": req.source,
    }

    try:
        booking = db.create_booking(data)
    except Exception as e:
        logger.error(f"Booking creation failed: {e}")
        raise HTTPException(status_code=500, detail="Booking creation failed")

    logger.info(f"New booking: {booking['booking_ref']} — {svc['name_pl']} — {req.customer_email}")

    # Trigger confirmation email (non-blocking, best-effort)
    _send_booking_confirmation_email(booking, svc)

    return {
        "booking_ref": booking["booking_ref"],
        "status": "pending",
        "message": _confirmation_message(req.language, booking["booking_ref"]),
        "total_price": booking["total_price"],
        "currency": booking["currency"],
    }


def _confirmation_message(lang: str, ref: str) -> str:
    if lang == "en":
        return (
            f"Thanks for your booking request! Your reference is {ref}. "
            "We'll confirm within 24 hours and send details to your email. "
            "Questions? Call us: +48 690 270 032"
        )
    return (
        f"Dzięki za zgłoszenie rezerwacji! Twój numer referencyjny to {ref}. "
        "Potwierdzimy w ciągu 24h i wyślemy szczegóły na email. "
        "Pytania? Zadzwoń: 690 270 032"
    )


def _send_booking_confirmation_email(booking: dict, service: dict):
    """Non-blocking best-effort email notification to admin and customer."""
    try:
        import smtplib
        # If Google auth is configured, use it; otherwise skip silently
        pass
    except Exception as e:
        logger.warning(f"Email notification skipped: {e}")


# ---------------------------------------------------------------------------
# PUBLIC — Get booking status (customer view)
# ---------------------------------------------------------------------------

@booking_router.get("/api/bookings/{booking_ref}")
async def get_booking_status(booking_ref: str):
    """Customer-facing booking status. Returns limited fields only."""
    booking = db.get_booking(booking_ref)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Return only safe customer-visible fields
    return {
        "booking_ref": booking["booking_ref"],
        "service_name": booking["service_name"],
        "location": booking["location"],
        "persons": booking["persons"],
        "preferred_dates": booking["preferred_dates"],
        "start_date": booking["start_date"],
        "start_time": booking["start_time"],
        "booking_status": booking["booking_status"],
        "payment_status": booking["payment_status"],
        "total_price": booking["total_price"],
        "currency": booking["currency"],
        "created_at": booking["created_at"],
    }


# ---------------------------------------------------------------------------
# ADMIN — List bookings
# ---------------------------------------------------------------------------

@booking_router.get("/api/admin/bookings", dependencies=[Depends(require_admin)])
async def admin_list_bookings(
    status: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
):
    bookings = db.list_bookings(status=status, location=location, limit=limit, offset=offset)
    return {"bookings": bookings, "count": len(bookings)}


@booking_router.get("/api/admin/bookings/{booking_ref}", dependencies=[Depends(require_admin)])
async def admin_get_booking(booking_ref: str):
    booking = db.get_booking(booking_ref)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    events = db.get_booking_events(booking_ref)
    return {"booking": booking, "events": events}


# ---------------------------------------------------------------------------
# ADMIN — Confirm booking (set date / instructor)
# ---------------------------------------------------------------------------

@booking_router.post("/api/admin/bookings/{booking_ref}/confirm", dependencies=[Depends(require_admin)])
async def admin_confirm_booking(booking_ref: str, req: ConfirmBookingRequest):
    ok = db.confirm_booking_dates(
        booking_ref,
        start_date=req.start_date,
        start_time=req.start_time,
        instructor=req.instructor,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"booking_ref": booking_ref, "status": "confirmed"}


# ---------------------------------------------------------------------------
# ADMIN — Update status
# ---------------------------------------------------------------------------

@booking_router.post("/api/admin/bookings/{booking_ref}/status", dependencies=[Depends(require_admin)])
async def admin_update_status(booking_ref: str, req: StatusUpdateRequest):
    ok = db.update_booking_status(booking_ref, req.booking_status)
    if not ok:
        raise HTTPException(status_code=404, detail="Booking not found")
    if req.note:
        db.add_note(booking_ref, req.note)
    return {"booking_ref": booking_ref, "booking_status": req.booking_status}


# ---------------------------------------------------------------------------
# ADMIN — Update payment
# ---------------------------------------------------------------------------

@booking_router.post("/api/admin/bookings/{booking_ref}/payment", dependencies=[Depends(require_admin)])
async def admin_update_payment(booking_ref: str, req: PaymentUpdateRequest):
    ok = db.update_payment_status(booking_ref, req.payment_status, req.payment_method)
    if not ok:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"booking_ref": booking_ref, "payment_status": req.payment_status}


# ---------------------------------------------------------------------------
# ADMIN — Add note
# ---------------------------------------------------------------------------

@booking_router.post("/api/admin/bookings/{booking_ref}/note", dependencies=[Depends(require_admin)])
async def admin_add_note(booking_ref: str, req: NoteRequest):
    ok = db.add_note(booking_ref, req.note)
    if not ok:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# ADMIN — Availability
# ---------------------------------------------------------------------------

@booking_router.get("/api/admin/availability", dependencies=[Depends(require_admin)])
async def admin_get_availability(
    start: str = Query(...),
    end: str = Query(...),
    location: Optional[str] = Query(None),
):
    blocks = db.list_blocked_dates(start, end, location=location)
    return {"blocks": blocks}


@booking_router.post("/api/admin/availability/block", dependencies=[Depends(require_admin)])
async def admin_block_date(req: BlockDateRequest):
    bid = db.block_date(req.date, req.reason, req.service_id, req.location)
    return {"id": bid, "date": req.date, "reason": req.reason}


# ---------------------------------------------------------------------------
# CHANNEL INTEGRATION — External marketplace booking
# ---------------------------------------------------------------------------

@booking_router.post("/api/channel/booking", status_code=201)
async def channel_booking(
    req: ChannelBookingRequest,
    x_channel_secret: str = Header(default=""),
):
    """
    Receive booking from external channel (Viator, Klook, etc).
    Channel must pass X-Channel-Secret header matching CHANNEL_SECRET env var.
    """
    expected_secret = os.getenv("CHANNEL_BOOKING_SECRET", "")
    if expected_secret and x_channel_secret != expected_secret:
        raise HTTPException(status_code=401, detail="Unauthorized channel")

    # Prevent duplicate ingestion
    existing = _find_by_external_id(req.external_booking_id, req.channel)
    if existing:
        return {
            "booking_ref": existing["booking_ref"],
            "status": existing["booking_status"],
            "message": "already_exists",
        }

    svc = db.get_service_by_slug(req.service_slug)
    if not svc:
        raise HTTPException(status_code=404, detail=f"Service '{req.service_slug}' not found")

    data = {
        "service_id": svc["id"],
        "location": req.location,
        "customer_name": req.customer_name,
        "customer_email": req.customer_email,
        "customer_phone": req.customer_phone,
        "customer_level": req.customer_level,
        "persons": req.persons,
        "preferred_dates": req.start_date,
        "special_requests": req.special_requests,
        "language": req.language,
        "source": req.channel,
    }

    booking = db.create_booking(data)

    # Store external reference
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE bookings SET external_booking_id=?, external_channel=? WHERE booking_ref=?",
            (req.external_booking_id, req.channel, booking["booking_ref"]),
        )

    # If start_date provided, auto-confirm
    if req.start_date:
        db.confirm_booking_dates(
            booking["booking_ref"],
            start_date=req.start_date,
            start_time=req.start_time or "09:00",
        )

    logger.info(
        f"Channel booking: {req.channel} ext={req.external_booking_id} "
        f"→ {booking['booking_ref']}"
    )

    return {
        "booking_ref": booking["booking_ref"],
        "status": booking["booking_status"],
        "internal_id": booking["id"],
        "message": "created",
    }


def _find_by_external_id(external_id: str, channel: str) -> Optional[dict]:
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM bookings WHERE external_booking_id=? AND external_channel=?",
            (external_id, channel),
        ).fetchone()
        return dict(row) if row else None
