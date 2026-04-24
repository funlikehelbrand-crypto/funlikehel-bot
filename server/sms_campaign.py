"""
Kampanie SMS i powiadomienia dla klientów FUN like HEL.

Alicja generuje treść wiadomości, system pobiera kontakty z Google
i wysyła SMS-y przez SerwerSMS.pl.
"""

import logging
from claude_agent import get_reply
from google_contacts import get_contacts_with_phones
from sms import send_bulk_sms, send_sms

logger = logging.getLogger(__name__)

# Max długość SMS bez dzielenia na części
SMS_MAX_LEN = 160


def run_campaign(topic: str, label: str = None, dry_run: bool = False) -> dict:
    """
    Uruchamia kampanię SMS.

    topic    — temat/instrukcja dla Alicji (np. "promocja na wakacyjne kursy kitesurfingu")
    label    — opcjonalna etykieta Google Contacts do filtrowania (np. "Klienci VIP")
    dry_run  — jeśli True, tylko generuje treść i listę kontaktów bez wysyłki

    Zwraca słownik z wynikami kampanii.
    """
    # Krok 1: Alicja generuje treść SMS
    prompt = (
        f"Napisz krótką wiadomość SMS dla klientów szkoły FUN like HEL na temat: {topic}. "
        f"SMS max {SMS_MAX_LEN} znaków. Bez pozdrowień — tylko konkretna treść + CTA. "
        f"Pisz po polsku, ciepło i entuzjastycznie."
    )
    message = get_reply(prompt)

    # Upewnij się że zmieści się w SMS
    if len(message) > SMS_MAX_LEN:
        message = message[:SMS_MAX_LEN - 3] + "..."

    logger.info("Wygenerowana treść SMS (%d znaków): %s", len(message), message)

    # Krok 2: Pobierz kontakty z Google
    contacts = get_contacts_with_phones(label=label)

    if not contacts:
        logger.warning("Brak kontaktów do wysyłki")
        return {
            "status": "no_contacts",
            "message": message,
            "contacts_count": 0,
            "results": [],
        }

    # Krok 3: Wyślij (lub tylko podejrzyj przy dry_run)
    if dry_run:
        logger.info("Dry run — pomijam wysyłkę. Kontaktów: %d", len(contacts))
        return {
            "status": "dry_run",
            "message": message,
            "contacts_count": len(contacts),
            "contacts_preview": contacts[:5],  # pierwsze 5 dla podglądu
        }

    results = send_bulk_sms(contacts, message)
    success = sum(1 for r in results if not r["result"].get("error"))

    return {
        "status": "sent",
        "message": message,
        "contacts_count": len(contacts),
        "success_count": success,
        "failed_count": len(contacts) - success,
        "results": results,
    }


def send_reminder(phone: str, name: str, course_name: str, date: str, hour: str) -> dict:
    """
    Wysyła przypomnienie o kursie do konkretnego klienta.

    phone       — numer telefonu klienta
    name        — imię klienta
    course_name — nazwa kursu (np. "Kitesurfing dla początkujących")
    date        — data kursu (np. "15 lipca")
    hour        — godzina kursu (np. "10:00")
    """
    prompt = (
        f"Napisz SMS-przypomnienie dla klienta imieniem {name} o kursie '{course_name}' "
        f"zaplanowanym na {date} o {hour}. Max {SMS_MAX_LEN} znaków. "
        f"Podpisz jako FUN like HEL. Pisz ciepło i konkretnie."
    )
    message = get_reply(prompt)

    if len(message) > SMS_MAX_LEN:
        message = message[:SMS_MAX_LEN - 3] + "..."

    logger.info("Przypomnienie SMS dla %s (%s): %s", name, phone, message)
    return send_sms(phone, message)


def send_notification(phone: str, name: str, content: str) -> dict:
    """
    Wysyła dowolne powiadomienie SMS do klienta.

    phone   — numer telefonu
    name    — imię (do personalizacji przez Alicję)
    content — treść powiadomienia (Alicja ją sformatuje do SMS)
    """
    prompt = (
        f"Napisz powiadomienie SMS dla klienta imieniem {name}. "
        f"Treść: {content}. Max {SMS_MAX_LEN} znaków. Pisz ciepło i konkretnie."
    )
    message = get_reply(prompt)

    if len(message) > SMS_MAX_LEN:
        message = message[:SMS_MAX_LEN - 3] + "..."

    logger.info("Powiadomienie SMS dla %s (%s)", name, phone)
    return send_sms(phone, message)
