"""
Obsługa Gmaila — odczyt wiadomości i automatyczne odpowiedzi przez agenta FunLikeHel.
"""

import base64
import logging
import re
from email.mime.text import MIMEText

from googleapiclient.discovery import build

from claude_agent import get_reply
from google_auth import get_credentials
from team_tasks import is_team_member, process_team_email

# Supabase sync for Messages panel
import os
import requests as _req

_SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://pmkzzchckmpcmvtdhxwh.supabase.co")
_SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

def _sync_to_panel(sender_email: str, sender_name: str, subject: str, body: str, reply: str = None, status: str = "new"):
    """Save email conversation to Supabase for Messages panel."""
    if not _SUPABASE_KEY:
        return
    try:
        headers = {"apikey": _SUPABASE_KEY, "Authorization": f"Bearer {_SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "return=minimal"}
        # Upsert conversation
        conv_data = {
            "channel": "email",
            "contact_name": sender_name or sender_email.split("@")[0],
            "contact_email": sender_email,
            "status": status,
            "unread_count": 1 if status == "new" else 0,
            "last_message_text": (body or "")[:200],
            "last_message_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "tags": ["email", "auto"],
        }
        # Check if conversation exists
        r = _req.get(f"{_SUPABASE_URL}/rest/v1/conversations?contact_email=eq.{sender_email}&channel=eq.email&limit=1",
                     headers={**headers, "Prefer": "return=representation"})
        if r.status_code == 200 and r.json():
            conv_id = r.json()[0]["id"]
            _req.patch(f"{_SUPABASE_URL}/rest/v1/conversations?id=eq.{conv_id}", headers=headers, json={
                "last_message_text": conv_data["last_message_text"],
                "last_message_at": conv_data["last_message_at"],
                "status": status,
                "unread_count": r.json()[0].get("unread_count", 0) + 1,
            })
        else:
            r2 = _req.post(f"{_SUPABASE_URL}/rest/v1/conversations", headers={**headers, "Prefer": "return=representation"}, json=conv_data)
            conv_id = r2.json()[0]["id"] if r2.status_code in (200, 201) and r2.json() else None

        if conv_id:
            # Save customer message
            _req.post(f"{_SUPABASE_URL}/rest/v1/messages", headers=headers, json={
                "conversation_id": conv_id,
                "sender_type": "customer",
                "sender_name": sender_name or sender_email,
                "body": f"[{subject}]\n{body[:500]}",
                "delivery_status": "read",
            })
            # Save AI reply if exists
            if reply:
                _req.post(f"{_SUPABASE_URL}/rest/v1/messages", headers=headers, json={
                    "conversation_id": conv_id,
                    "sender_type": "ai",
                    "sender_name": "Alicja AI",
                    "body": reply[:500],
                    "delivery_status": "sent",
                })
    except Exception as e:
        logger.warning("Supabase sync failed: %s", e)

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


def send_email(to: str, subject: str, body: str):
    """Wysyła nową wiadomość email (nie odpowiedź)."""
    service = get_gmail_service()
    clean_to = _extract_email(to)
    message = MIMEText(body, "plain", "utf-8")
    message["to"] = clean_to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(
        userId="me",
        body={"raw": raw},
    ).execute()


def mark_as_read(message_id: str):
    """Oznacza wiadomość jako przeczytaną."""
    service = get_gmail_service()
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()


BOT_OWN_EMAIL = "funlikehelbrand@gmail.com"

IGNORED_SENDERS = [
    BOT_OWN_EMAIL,  # własny adres bota — nigdy nie odpowiadaj na własne maile
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
    # Własny adres szkoły — bot nie odpowiada sam sobie
    "funlikehelbrand@gmail.com",
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


def _thread_started_by_us(thread_id: str) -> bool:
    """Sprawdza czy PIERWSZY mail w wątku został wysłany przez FLH.
    Jeśli tak — to nasz wątek wychodzący (np. zapytanie ofertowe do dostawcy)
    i bot NIE powinien odpowiadać na odpowiedzi w tym wątku."""
    try:
        service = get_gmail_service()
        thread = service.users().threads().get(
            userId="me", id=thread_id, format="metadata",
            metadataHeaders=["From"],
        ).execute()
        messages = thread.get("messages", [])
        if not messages:
            return False
        first_msg = messages[0]
        headers = {h["name"]: h["value"] for h in first_msg["payload"]["headers"]}
        sender = headers.get("From", "").lower()
        labels = first_msg.get("labelIds", [])
        if "SENT" in labels or BOT_OWN_EMAIL in sender:
            return True
    except Exception as e:
        logger.warning("Nie udało się sprawdzić pierwszego maila wątku %s: %s", thread_id, e)
    return False


def _bot_already_replied_in_thread(thread_id: str) -> bool:
    """Sprawdza czy bot (Alicja) już odpowiedział w tym wątku.
    Jeśli tak — nie odpowiadamy ponownie (człowiek przejmuje)."""
    try:
        service = get_gmail_service()
        thread = service.users().threads().get(
            userId="me", id=thread_id, format="metadata",
            metadataHeaders=["From"],
        ).execute()
        for msg in thread.get("messages", []):
            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            sender = headers.get("From", "").lower()
            labels = msg.get("labelIds", [])
            # Wiadomość wysłana przez bota (SENT label lub z naszego adresu)
            if "SENT" in labels or BOT_OWN_EMAIL in sender:
                return True
    except Exception as e:
        logger.warning("Nie udało się sprawdzić wątku %s: %s", thread_id, e)
    return False


def process_unread_emails():
    """
    Główna funkcja — pobiera nieprzeczytane maile,
    generuje odpowiedzi przez Claude i odsyła je.
    Ignoruje bounce'y, newslettery i spam.

    ZASADA: Alicja wysyła tylko JEDNĄ odpowiedź na wątek.
    Jeśli bot już odpowiedział — dalej obsługuje człowiek.
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

            # === TEAM ROUTING ===
            # Jeśli mail od członka ekipy → przetwórz jako polecenie wewnętrzne
            sender_email = _extract_email(details["sender"])
            if is_team_member(sender_email):
                logger.info("TEAM TASK od %s: %s", sender_email, details["subject"])
                try:
                    reply_text = process_team_email(
                        sender=sender_email,
                        subject=details["subject"],
                        body=details["body"],
                    )
                    send_reply(
                        thread_id=details["thread_id"],
                        to=details["sender"],
                        subject=details["subject"],
                        body=reply_text,
                        in_reply_to=details["message_id"],
                        references=details["references"],
                    )
                    mark_as_read(details["id"])
                    logger.info("TEAM TASK odpowiedź wysłana do %s", sender_email)
                except Exception as e:
                    logger.error("Błąd TEAM TASK od %s: %s", sender_email, e)
                continue

            # Sprawdź czy wątek został ROZPOCZĘTY przez nas (FLH wysłał pierwszy mail)
            # Jeśli tak — to nasz mail wychodzący (zapytanie do dostawcy, itp.)
            # Bot NIE odpowiada na odpowiedzi w naszych własnych wątkach
            if _thread_started_by_us(details["thread_id"]):
                logger.info("Wątek rozpoczęty przez FLH — pomijam (mail wychodzący): %s | %s",
                            details["sender"], details["subject"])
                continue  # zostawiamy jako NIEPRZECZYTANY — człowiek obsługuje

            # Sprawdź czy bot już odpowiedział w tym wątku — jeśli tak, nie odpowiadaj ponownie
            if _bot_already_replied_in_thread(details["thread_id"]):
                logger.info("Bot już odpowiedział w wątku — zostawiam dla człowieka: %s | %s",
                            details["sender"], details["subject"])
                continue  # zostawiamy jako NIEPRZECZYTANY — żeby człowiek widział

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

            # Sync to panel Messages
            _sync_to_panel(
                sender_email=sender_email,
                sender_name=details["sender"],
                subject=details["subject"],
                body=details["body"],
                reply=reply_text,
                status="ai_handled",
            )

        except Exception as e:
            logger.error("Błąd przy przetwarzaniu maila %s: %s", msg_ref["id"], e)
