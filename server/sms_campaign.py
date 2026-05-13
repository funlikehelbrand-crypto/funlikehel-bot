"""
Kampanie SMS i powiadomienia dla klientów FUN like HEL.

Alicja generuje treść wiadomości (lub używamy gotowego tekstu),
system pobiera kontakty z Google i wysyła SMS-y przez SerwerSMS.pl.
"""

import logging
import re
from claude_agent import get_reply
from google_contacts import get_contacts_with_phones
from sms import send_bulk_sms, send_sms

logger = logging.getLogger(__name__)

# Max długość SMS bez dzielenia na części (GSM-7)
SMS_MAX_LEN = 160


def _strip_sms(text: str, max_len: int = SMS_MAX_LEN) -> str:
    """
    Czyści tekst do formatu SMS:
    - usuwa markdown (**, __, #, *)
    - usuwa emoji (blok Unicode Emoticons i inne)
    - usuwa nadmiarowe białe znaki / nowe linie
    - obcina do max_len znaków
    """
    # Usuń markdown bold/italic
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', text)
    # Usuń nagłówki Markdown
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Usuń emoji (szeroki zakres Unicode)
    text = re.sub(
        r'[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001FA00-\U0001FAFF]',
        '', text
    )
    # Usuń metadane typu "Wersja SMS (N znaków):" jeśli Alicja je dodała
    text = re.sub(r'^.*?znaków\).*?\n\n', '', text, flags=re.DOTALL)
    # Normalizuj białe znaki
    text = re.sub(r'\s+', ' ', text).strip()
    # Obetnij
    if len(text) > max_len:
        text = text[:max_len - 3] + "..."
    return text


def run_campaign(topic: str, label: str = None, dry_run: bool = False,
                 message: str = None) -> dict:
    """
    Uruchamia kampanię SMS.

    topic    — temat/instrukcja dla Alicji (generowanie treści)
    label    — opcjonalna etykieta Google Contacts do filtrowania (np. "Klienci")
    dry_run  — jeśli True, tylko generuje treść i listę kontaktów bez wysyłki
    message  — jeśli podany, używa tej treści zamiast generowania przez Alicję

    Zwraca słownik z wynikami kampanii.
    """
    # Krok 1: treść SMS — własna lub od Alicji
    if message:
        message = _strip_sms(message)
        logger.info("Używam podanej treści SMS (%d znaków): %s", len(message), message)
    else:
        prompt = (
            f"Napisz treść SMS dla klientów szkoły FUN like HEL na temat: {topic}. "
            f"SMS max {SMS_MAX_LEN} znaków. Bez pozdrowień, bez formatowania markdown, "
            f"bez emoji — tylko czysty tekst SMS + CTA. Pisz po polsku, ciepło i konkretnie. "
            f"Odpowiedz TYLKO treścią SMS, żadnych nagłówków ani komentarzy."
        )
        message = _strip_sms(get_reply(prompt))
        logger.info("Wygenerowana treść SMS (%d znaków): %s", len(message), message)

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
