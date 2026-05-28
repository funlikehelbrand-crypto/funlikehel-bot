"""
push_notifications.py — wysylka push notifications przez Expo Push API (bezplatne).

Dokumentacja: https://docs.expo.dev/push-notifications/sending-notifications/

Obsluguje:
- Wysylke do pojedynczego tokena (send_push)
- Batch wysylke do wielu tokenow (send_push_batch)
- Broadcast do wybranych rol/lokalizacji (broadcast_to_staff)
- Triggery: nowa rezerwacja, nowa wiadomosc, alert pogodowy
"""

import os
import httpx
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

# Supabase connection — lazy init
_supabase_client = None


def _get_supabase():
    """Lazy-init Supabase client for push token lookup."""
    global _supabase_client
    if _supabase_client is None:
        try:
            from supabase import create_client
            url = os.environ.get("SUPABASE_URL", "")
            key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
            if url and key:
                _supabase_client = create_client(url, key)
            else:
                logger.warning("[push] Brak SUPABASE_URL lub SUPABASE_SERVICE_ROLE_KEY — broadcast niedostepny")
        except ImportError:
            logger.warning("[push] Brak pakietu supabase-py — broadcast niedostepny")
    return _supabase_client


async def send_push(
    token: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> bool:
    """
    Wysyla push notification przez Expo Push API.

    Args:
        token: Expo Push Token (format: ExponentPushToken[...])
        title: Tytul powiadomienia
        body: Tresc powiadomienia
        data: Opcjonalne dane dodatkowe (dict) — dostepne w obsludze powiadomienia

    Returns:
        True jezeli powiadomienie zostalo przyjete przez Expo, False w przypadku bledu.
    """
    if not token or not token.startswith("ExponentPushToken"):
        logger.warning("[push] Nieprawidlowy token: %s", token[:30] if token else "brak")
        return False

    payload = {
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
        "data": data or {},
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                EXPO_PUSH_URL,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate",
                    "Content-Type": "application/json",
                },
            )

        if response.status_code != 200:
            logger.error(
                "[push] Expo API HTTP %d: %s",
                response.status_code,
                response.text[:200],
            )
            return False

        result = response.json()
        # Expo zwraca {"data": {"status": "ok"}} lub {"data": {"status": "error", ...}}
        ticket = result.get("data", {})
        if isinstance(ticket, list):
            ticket = ticket[0] if ticket else {}

        if ticket.get("status") == "error":
            logger.error("[push] Expo odrzucil wiadomosc: %s", ticket)
            return False

        logger.info("[push] Wyslano '%s' -> %s", title, token[:30])
        return True

    except httpx.TimeoutException:
        logger.error("[push] Timeout przy wysylaniu do %s", token[:30])
        return False
    except Exception as exc:
        logger.exception("[push] Nieoczekiwany blad: %s", exc)
        return False


async def send_booking_confirmation(
    customer_token: str,
    service_name: str,
    booking_date: str,
) -> bool:
    """Powiadomienie po zlozeniu rezerwacji przez klienta."""
    return await send_push(
        token=customer_token,
        title="Rezerwacja potwierdzona!",
        body=f"{service_name} — {booking_date}. Do zobaczenia na wodzie!",
        data={"type": "booking_confirmed"},
    )


async def send_booking_reminder(
    customer_token: str,
    service_name: str,
    hours_left: int,
) -> bool:
    """Przypomnienie 24h przed zajęciami."""
    return await send_push(
        token=customer_token,
        title="Jutro masz zajecia!",
        body=f"{service_name} za {hours_left}h. Sprawdz wiatr na Windguru!",
        data={"type": "reminder"},
    )


async def send_booking_status_update(
    customer_token: str,
    service_name: str,
    new_status: str,
) -> bool:
    """Powiadomienie o zmianie statusu rezerwacji przez admina."""
    STATUS_MESSAGES = {
        "confirmed": ("Rezerwacja zatwierdzona!", f"{service_name} — potwierdzono!"),
        "cancelled": ("Rezerwacja anulowana", f"{service_name} zostala anulowana. Skontaktuj sie z nami."),
        "weather_hold": ("Wstrzymano z powodu pogody", f"{service_name} — zla pogoda. Skontaktujemy sie wkrotce."),
        "rescheduled": ("Termin zmieniony", f"{service_name} — sprawdz nowy termin w aplikacji."),
    }

    title, body = STATUS_MESSAGES.get(
        new_status,
        ("Aktualizacja rezerwacji", f"{service_name} — zmiana statusu: {new_status}"),
    )

    return await send_push(
        token=customer_token,
        title=title,
        body=body,
        data={"type": "status_update", "status": new_status},
    )


# ---------------------------------------------------------------------------
# Batch send — wysylka do wielu tokenow naraz (Expo API akceptuje tablice)
# ---------------------------------------------------------------------------

async def send_push_batch(
    tokens: List[str],
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> dict:
    """
    Wysyla push do wielu tokenow naraz (batch, max 100 per request).

    Returns:
        {"sent": int, "failed": int, "errors": list}
    """
    valid_tokens = [t for t in tokens if t and t.startswith("ExponentPushToken")]
    if not valid_tokens:
        return {"sent": 0, "failed": 0, "errors": ["Brak prawidlowych tokenow"]}

    results = {"sent": 0, "failed": 0, "errors": []}

    # Expo API accepts max 100 per request
    for i in range(0, len(valid_tokens), 100):
        chunk = valid_tokens[i:i + 100]
        messages = [
            {
                "to": token,
                "title": title,
                "body": body,
                "sound": "default",
                "data": data or {},
            }
            for token in chunk
        ]

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    EXPO_PUSH_URL,
                    json=messages,
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip, deflate",
                        "Content-Type": "application/json",
                    },
                )

            if response.status_code != 200:
                results["failed"] += len(chunk)
                results["errors"].append(f"HTTP {response.status_code}")
                continue

            result = response.json()
            tickets = result.get("data", [])
            if not isinstance(tickets, list):
                tickets = [tickets]

            for ticket in tickets:
                if ticket.get("status") == "ok":
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                    err_msg = ticket.get("message", "unknown error")
                    if err_msg not in results["errors"]:
                        results["errors"].append(err_msg)

        except Exception as exc:
            results["failed"] += len(chunk)
            results["errors"].append(str(exc))

    logger.info(
        "[push] Batch: %d sent, %d failed z %d tokenow",
        results["sent"], results["failed"], len(valid_tokens),
    )
    return results


# ---------------------------------------------------------------------------
# Lookup tokenow z Supabase — po roli, lokalizacji, lub user_id
# ---------------------------------------------------------------------------

async def _get_tokens_by_role(
    roles: Optional[List[str]] = None,
    location: Optional[str] = None,
) -> List[str]:
    """Pobiera aktywne push tokeny dla uzytkownikow o danych rolach/lokalizacji."""
    sb = _get_supabase()
    if not sb:
        return []

    try:
        # Pobierz user_id z user_roles
        query = sb.table("user_roles").select("user_id")
        if roles:
            query = query.in_("role", roles)
        if location and location != "both":
            query = query.in_("location", [location, "both"])

        result = query.execute()
        user_ids = [row["user_id"] for row in (result.data or [])]

        if not user_ids:
            return []

        # Pobierz aktywne tokeny
        token_result = (
            sb.table("push_tokens")
            .select("token")
            .in_("user_id", user_ids)
            .eq("is_active", True)
            .execute()
        )

        return [row["token"] for row in (token_result.data or [])]
    except Exception as exc:
        logger.error("[push] Blad pobierania tokenow: %s", exc)
        return []


async def _get_tokens_by_user_id(user_id: str) -> List[str]:
    """Pobiera aktywne push tokeny dla konkretnego usera."""
    sb = _get_supabase()
    if not sb:
        return []

    try:
        result = (
            sb.table("push_tokens")
            .select("token")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .execute()
        )
        return [row["token"] for row in (result.data or [])]
    except Exception as exc:
        logger.error("[push] Blad pobierania tokenow dla user %s: %s", user_id, exc)
        return []


# ---------------------------------------------------------------------------
# Broadcast do staff/admin
# ---------------------------------------------------------------------------

async def broadcast_to_staff(
    title: str,
    body: str,
    data: Optional[dict] = None,
    roles: Optional[List[str]] = None,
    location: Optional[str] = None,
) -> dict:
    """
    Wysyla push notification do wszystkich aktywnych urzadzen
    uzytkownikow o podanych rolach i/lub lokalizacji.

    Domyslnie: admin + staff + instructor.
    """
    if roles is None:
        roles = ["admin", "staff", "instructor"]

    tokens = await _get_tokens_by_role(roles=roles, location=location)
    if not tokens:
        logger.info("[push] Broadcast: brak tokenow dla rol=%s loc=%s", roles, location)
        return {"sent": 0, "failed": 0, "errors": ["Brak zarejestrowanych urzadzen"]}

    return await send_push_batch(tokens, title, body, data)


async def notify_user(
    user_id: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> dict:
    """Wysyla push do wszystkich urzadzen konkretnego usera."""
    tokens = await _get_tokens_by_user_id(user_id)
    if not tokens:
        return {"sent": 0, "failed": 0, "errors": ["Brak tokenow dla usera"]}

    return await send_push_batch(tokens, title, body, data)


# ---------------------------------------------------------------------------
# Triggery — gotowe funkcje do wywolania z main.py
# ---------------------------------------------------------------------------

async def trigger_new_booking(
    booking_ref: str,
    customer_name: str,
    service_name: str,
    start_date: str,
    location: str = "both",
) -> dict:
    """
    Powiadamia staff o nowej rezerwacji.
    Wywolaj po INSERT do bookings.
    """
    return await broadcast_to_staff(
        title="Nowa rezerwacja!",
        body=f"{booking_ref} — {customer_name}: {service_name} ({start_date})",
        data={
            "type": "new_booking",
            "booking_ref": booking_ref,
        },
        roles=["admin", "staff"],
        location=location,
    )


async def trigger_new_message(
    sender_name: str,
    channel: str,
    preview: str,
    message_id: Optional[str] = None,
) -> dict:
    """
    Powiadamia staff o nowej wiadomosci w inbox.
    Wywolaj po INSERT do inbox_messages.
    """
    preview_short = (preview[:80] + "...") if len(preview) > 80 else preview
    return await broadcast_to_staff(
        title=f"Wiadomosc od {sender_name}",
        body=f"[{channel}] {preview_short}",
        data={
            "type": "new_message",
            "channel": channel,
            "message_id": message_id or "",
        },
        roles=["admin", "staff"],
    )


async def trigger_morning_equipment_briefing(location: str = "hel") -> dict:
    """
    Poranny briefing sprzętowy — 7:00.
    Sprawdza dzisiejsze rezerwacje + pogodę → lista sprzętu do przygotowania.
    Push do instruktorów i adminów.
    """
    import requests as _req
    from datetime import date

    today = date.today().isoformat()
    sb = _get_supabase()
    if not sb:
        return {"error": "no supabase"}

    # Get today's bookings with customer weight
    bookings = sb.table("bookings").select(
        "customer_name, service_name_snap, start_time, instructor_snap, customer:customers!customer_id(weight, skill_level)"
    ).eq("start_date", today).eq("location", location).neq("booking_status", "cancelled").execute()

    if not bookings.data:
        return {"skipped": "no bookings today"}

    # Get wind forecast
    loc = {"lat": 27.18, "lon": 33.83} if location == "hurghada" else {"lat": 54.7, "lon": 18.67}
    try:
        wr = _req.get(f"https://api.open-meteo.com/v1/forecast?latitude={loc['lat']}&longitude={loc['lon']}&daily=wind_speed_10m_max&start_date={today}&end_date={today}&wind_speed_unit=kn", timeout=5)
        wind_kn = wr.json().get("daily", {}).get("wind_speed_10m_max", [14])[0] if wr.ok else 14
    except:
        wind_kn = 14

    # Generate equipment list
    kites_needed = {}
    harnesses_needed = {}
    total_lessons = len(bookings.data)

    for b in bookings.data:
        cust = b.get("customer") or {}
        weight = cust.get("weight")
        if not weight:
            continue
        svc = (b.get("service_name_snap") or "").lower()
        if "kite" in svc:
            kite_size = max(4, min(17, round((weight * 0.9) / (wind_kn * 0.55))))
            kites_needed[kite_size] = kites_needed.get(kite_size, 0) + 1
        harness = "XXXS" if weight < 35 else "XS" if weight < 45 else "S" if weight < 60 else "M" if weight < 75 else "L" if weight < 90 else "XL" if weight < 105 else "XXL"
        harnesses_needed[harness] = harnesses_needed.get(harness, 0) + 1

    # Build message
    lines = [f"Dzis {total_lessons} lekcji, wiatr {wind_kn:.0f}kn"]
    if kites_needed:
        kite_str = ", ".join(f"{cnt}x {size}m" for size, cnt in sorted(kites_needed.items()))
        lines.append(f"Kite: {kite_str}")
    if harnesses_needed:
        harness_str = ", ".join(f"{cnt}x {size}" for size, cnt in sorted(harnesses_needed.items()))
        lines.append(f"Trapez: {harness_str}")

    body = "\n".join(lines)

    return await broadcast_to_staff(
        title=f"Sprzet na dzis ({total_lessons} lekcji)",
        body=body,
        data={"type": "morning_equipment", "location": location, "wind_kn": str(wind_kn)},
        roles=["admin", "staff", "instructor"],
        location=location,
    )


async def trigger_weather_alert(
    location: str,
    wind_speed_kn: float,
    description: str = "",
) -> dict:
    """
    Alert pogodowy — silny wiatr >25 kn.
    Wywolaj z weather checking loop.
    """
    body = f"Wiatr {wind_speed_kn:.0f} kn w {'Jastarnia' if location == 'hel' else 'Hurghada'}"
    if description:
        body += f" — {description}"

    return await broadcast_to_staff(
        title="Alert pogodowy!",
        body=body,
        data={
            "type": "weather_alert",
            "location": location,
            "wind_speed_kn": str(wind_speed_kn),
        },
        roles=["admin", "staff", "instructor"],
        location=location,
    )
