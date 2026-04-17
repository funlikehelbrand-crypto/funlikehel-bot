"""
Integracja z SerwerSMS.pl — wysyłanie SMS do klientów.

Dokumentacja API: https://serwersms.pl/api-sms
"""

import hashlib
import logging
import os
from dotenv import load_dotenv
import httpx

load_dotenv("api.env")

logger = logging.getLogger(__name__)

SERWERSMS_API = "https://api2.serwersms.pl"
LOGIN = os.environ.get("SERWERSMS_LOGIN", "")
PASSWORD = os.environ.get("SERWERSMS_PASSWORD", "")
TOKEN = os.environ.get("SERWERSMS_TOKEN", "")
SENDER = os.environ.get("SERWERSMS_SENDER", "FUNlikeHEL")  # pre-zatwierdzony nadawca


def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _headers() -> dict:
    """Zwraca nagłówki HTTP z autoryzacją Bearer token."""
    return {"Authorization": f"Bearer {TOKEN}"}


def send_sms(phone: str, message: str, sender: str = None) -> dict:
    """
    Wysyła pojedynczego SMS-a przez SerwerSMS.pl.

    phone    — numer telefonu (format: 48600000000 lub +48600000000)
    message  — treść SMS (max 160 znaków dla jednej wiadomości)
    sender   — nadawca (domyślnie SERWERSMS_SENDER z env)
    """
    phone = _normalize_phone(phone)
    if not phone:
        return {"error": "Nieprawidłowy numer telefonu"}

    payload = {
        "phone": phone,
        "text": message,
        "sender": sender or SENDER,
    }

    try:
        response = httpx.post(
            f"{SERWERSMS_API}/messages/send_sms",
            headers=_headers(),
            json=payload,
            timeout=10,
        )
        data = response.json()
        if data.get("queued"):
            logger.info("SMS wysłany do %s", phone)
        else:
            logger.warning("SerwerSMS błąd dla %s: %s", phone, data)
        return data
    except Exception as e:
        logger.error("Błąd wysyłki SMS do %s: %s", phone, e)
        return {"error": str(e)}


def send_bulk_sms(contacts: list[dict], message: str, sender: str = None) -> list[dict]:
    """
    Wysyła SMS-y do listy kontaktów.

    contacts — lista słowników z kluczem 'phone' i opcjonalnie 'name'
    Zwraca listę wyników dla każdego kontaktu.
    """
    sender = sender or SENDER
    results = []

    for contact in contacts:
        phone = contact.get("phone", "")
        name = contact.get("name", "")
        result = send_sms(phone, message, sender)
        results.append({"phone": phone, "name": name, "result": result})

    success = sum(1 for r in results if not r["result"].get("error"))
    logger.info("Kampania SMS: wysłano %d/%d wiadomości", success, len(contacts))
    return results


def _normalize_phone(phone: str) -> str:
    """Normalizuje numer do formatu 48XXXXXXXXX."""
    phone = phone.strip().replace(" ", "").replace("-", "").replace("+", "")
    if not phone:
        return ""
    # Dodaj prefix Polski jeśli 9-cyfrowy
    if len(phone) == 9 and phone.isdigit():
        phone = "48" + phone
    return phone
