"""
Obsługa Gmaila — odczyt wiadomości i automatyczne odpowiedzi przez agenta FunLikeHel.
"""

import base64
import email as email_lib
import logging
import re
from email.mime.text import MIMEText

from googleapiclient.discovery import build

from claude_agent import get_reply
from google_auth import get_credentials

logger = logging.getLogger(__name__)

LABEL_PROCESSED = "FUNLIKEHEL_BOT"  # etykieta oznaczająca przetworzone maile


def get_gmail_service():
    return build("gmail", "v1", credentials=get_credentials(), cache_discovery=False)


def get_unread_messages(max_results: int = 10) -> list[dict]:
    """Pobiera nieprzeczytane maile ze skrzynki."""
    service = get_gmail_service()
    result = service.users().messages().list(
        userId="me",
        labelIds=["UNREAD", "INBOX"],
        maxResults=max_results,
    ).execute()
    return result.get("messages", [])


def get_message_details(message_id: str) -> dict:
    """Pobiera szczegóły wiadomości — nadawcę, temat i treść."""
    service = get_gmail_service()
    msg = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()

    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    sender = headers.get("From", "")
    subject = headers.get("Subject", "(brak tematu)")
    body = _extract_body(msg["payload"])

    return {
        "id": message_id,
        "sender": sender,
        "subject": subject,
        "body": body,
        "thread_id": msg["threadId"],
        "message_id": headers.get("Message-ID", ""),
        "references": headers.get("References", ""),
    }


def _extract_body(payload: dict) -> str:
    """Wyciąga treść tekstową z wiadomości."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"].get("data", "")
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    data = payload.get("body", {}).get("data", "")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return ""


def _extract_email(sender: str) -> str:
    """Wyciąga sam adres email z formatu 'Imię Nazwisko <email@domain.com>'."""
    match = re.search(r'<([^>]+)>', sender)
    return match.group(1) if match else sender.strip()


def send_reply(thread_id: str, to: str, subject: str, body: str,
               in_reply_to: str = "", references: str = ""):
    """Wysyła odpowiedź w tym samym wątku z poprawnymi nagłówkami RFC 2822."""
    service = get_gmail_service()
    clean_to = _extract_email(to)
    message = MIMEText(body, "plain", "utf-8")
    message["to"] = clean_to
    message["subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        # References: poprzednie + bieżący Message-ID
        ref_chain = f"{references} {in_reply_to}".strip()
        message["References"] = ref_chain
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    service.users().messages().send(
        userId="me",
        body={"raw": raw, "threadId": thread_id},
    ).execute()


def mark_as_read(message_id: str):
    """Oznacza wiadomość jako przeczytaną."""
    service = get_gmail_service()
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()


IGNORED_SENDERS = [
    "mailer-daemon",
    "noreply",
    "no-reply",
    "notifications",
    "newsletter",
    "donotreply",
    "bounce",
    "postmaster",
    "alibaba",
    "player.pl",
    "buynotice",
    "design.com",
    "logo-save",
    "googleplay",
    "accounts.google.com",
    "businessprofile",
    "facebookmail",
    "security@",
    "alert@",
    "support@google",
    # Platformy techniczne / hosting / SaaS — nie klienci szkoły
    "render.com",
    "serwersms.pl",
    "ngrok.com",
    "hubspot",
    "mailchimp",
    "sendgrid",
    "github.com",
    "gitlab.com",
    "heroku.com",
    "vercel.com",
    "netlify.com",
    "digitalocean.com",
    "aws.amazon.com",
    "cloud.google.com",
    "calendar-notification",
]


def _is_real_customer(sender: str) -> bool:
    """Zwraca True tylko jeśli nadawca nie jest na liście ignorowanych."""
    sender_lower = sender.lower()
    for ignored in IGNORED_SENDERS:
        if ignored in sender_lower:
            return False
    return True


SPORT_KEYWORDS = [
    "kite", "surf", "wind", "wing", "sup", "wakeboard", "foil",
    "kurs", "szkolenie", "obóz", "oboz", "rezerwacja", "cena", "oferta",
    "jastarnia", "egipt", "hurghada", "hel", "zatoka",
    "lesson", "course", "booking", "price",
]


def _is_customer_inquiry(subject: str, body: str) -> bool:
    """
    Sprawdza czy mail dotyczy oferty szkoły.
    Najpierw szybki pre-filtr po słowach kluczowych (bez Claude),
    potem Claude dla niejednoznacznych przypadków.
    """
    text = (subject + " " + body).lower()

    # Szybki pre-filtr — jeśli jest słowo kluczowe, od razu TAK
    if any(kw in text for kw in SPORT_KEYWORDS):
        return True

    # Dla niejednoznacznych — zapytaj Claude
    prompt = f"""Oceń czy poniższy email dotyczy sportów wodnych, kursu, rezerwacji lub oferty szkoły FunLikeHel.

Temat: {subject}
Treść: {body[:500]}

Odpowiedz TYLKO jednym słowem:
- TAK — jeśli treść dotyczy: kursu, ceny, terminu, rezerwacji, kitesurfingu, windsurfingu, wing, SUP, wakeboardingu, obozu, noclegu, Jastarni, Egiptu lub oferty szkoły
- NIE — jeśli to: newsletter, powiadomienie systemowe, faktura, oferta sprzedaży czegoś, spam lub treść niezwiązana ze sportami wodnymi

Odpowiedź:"""

    try:
        reply = get_reply(prompt)
        return "TAK" in reply.upper()
    except Exception:
        return False


def process_unread_emails():
    """
    Główna funkcja — pobiera nieprzeczytane maile,
    generuje odpowiedzi przez Claude i odsyła je.
    Ignoruje bounce'y, newslettery i spam.
    """
    messages = get_unread_messages()
    if not messages:
        logger.info("Brak nowych wiadomości.")
        return

    for msg_ref in messages:
        try:
            details = get_message_details(msg_ref["id"])

            if not _is_real_customer(details["sender"]):
                logger.info("Pomijam (filtr nadawcy): %s", details["sender"])
                mark_as_read(details["id"])
                continue

            is_thread_reply = details["subject"].strip().lower().startswith("re:")
            if not is_thread_reply and not _is_customer_inquiry(details["subject"], details["body"]):
                logger.info("Pomijam jako nieprzeczytany (nie zapytanie klienta): %s | %s", details["sender"], details["subject"])
                continue  # zostawiamy jako nieprzeczytany

            logger.info("Przetwarzam mail od: %s | Temat: %s", details["sender"], details["subject"])

            prompt = f"Wiadomość email od klienta:\nTemat: {details['subject']}\n\n{details['body']}"
            sender_email = _extract_email(details["sender"])
            reply_text = get_reply(prompt, sender_id=sender_email, channel="email")

            send_reply(
                thread_id=details["thread_id"],
                to=details["sender"],
                subject=details["subject"],
                body=reply_text,
                in_reply_to=details["message_id"],
                references=details["references"],
            )
            mark_as_read(details["id"])
            logger.info("Odpowiedź wysłana do: %s", details["sender"])

        except Exception as e:
            logger.error("Błąd przy przetwarzaniu maila %s: %s", msg_ref["id"], e)
