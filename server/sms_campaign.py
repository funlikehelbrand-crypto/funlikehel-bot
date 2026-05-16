"""
Kampanie SMS i powiadomienia dla klientów FUN like HEL.

v1 (legacy) — run_campaign, send_reminder, send_notification (zachowane dla kompatybilności)
v2 — prepare_campaign, send_campaign_batch (kolejkowanie, retry, rate limit, personalizacja)

Alicja generuje treść wiadomości (lub używamy gotowego tekstu),
system pobiera kontakty z Google i wysyła SMS-y przez SerwerSMS.pl.
"""

import argparse
import logging
import re
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# Max długość SMS bez dzielenia na części (GSM-7)
SMS_MAX_LEN = 160

# Rate limit: max 20 SMS/minutę
BATCH_SIZE_DEFAULT = 20
BATCH_SLEEP_SEC = 2  # sekund między batchami

# Retry: max 3 próby z exponential backoff
MAX_ATTEMPTS = 3
RETRY_DELAYS = [5, 15, 45]  # sekundy po kolejnych nieudanych próbach

# Placeholdery w szablonach
SCHOOL_NAME = "Fun Like Hel"
STOP_SUFFIX = "\nSTOP = rezygnacja"


# =============================================================================
# Helpers — tekst SMS
# =============================================================================

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
    # Normalizuj białe znaki (ale zachowaj \n z STOP suffix)
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.split('\n')]
    text = '\n'.join(l for l in lines if l)
    # Obetnij
    if len(text) > max_len:
        text = text[:max_len - 3] + "..."
    return text


def _personalize(template: str, first_name: str = None, tracking_token: str = None,
                  target_url: str = None) -> str:
    """
    Wypełnia placeholdery w szablonie wiadomości:
      {{first_name}}         — imię (fallback: "")
      {{registration_link}}  — link z tracking tokenem (dodaje ?ref={token} do target_url)
      {{school_name}}        — "Fun Like Hel"
    """
    from sms_tracker import build_tracking_link

    msg = template
    msg = msg.replace("{{first_name}}", first_name or "")
    msg = msg.replace("{{school_name}}", SCHOOL_NAME)

    if tracking_token:
        link = build_tracking_link(tracking_token, target_url=target_url)
    else:
        link = target_url or "https://funlikehel.pl"
    msg = msg.replace("{{registration_link}}", link)

    return msg


def _add_stop_suffix(message: str, max_len: int = SMS_MAX_LEN) -> str:
    """
    Dodaje 'STOP = rezygnacja' na końcu wiadomości marketingowej.
    Jeśli wiadomość jest za długa — skraca jej treść żeby zmieścił się suffix.
    """
    suffix = STOP_SUFFIX
    if len(message) + len(suffix) <= max_len:
        return message + suffix
    # Skróć właściwą treść żeby suffix się zmieścił
    max_body = max_len - len(suffix) - 3
    return message[:max_body] + "..." + suffix


# =============================================================================
# v2 — prepare_campaign + send_campaign_batch
# =============================================================================

def prepare_campaign(
    name: str,
    campaign_type: str,  # 'marketing' | 'transactional'
    message_template: str,
    contacts: list[dict],
    target_url: str = "https://funlikehel.pl",
) -> dict:
    """
    Tworzy kampanię v2 + rekordy recipients ze statusem 'pending'.
    Kontakty powinny mieć klucze: phone (E.164), first_name, last_name (opcjonalne).

    Zwraca dict z campaign_id i liczbą dodanych odbiorców.
    Idempotentne — nie duplikuje odbiorców jeśli kampania już istnieje.

    Dla kampanii marketingowych automatycznie pomija wypisanych kontaktów.
    """
    from sms_tracker import (
        create_campaign_v2, add_recipient, upsert_contact,
        is_unsubscribed, update_campaign_counters,
    )
    from sms_migrations import run_migrations

    # Upewnij się że tabele istnieją
    run_migrations()

    campaign_id = create_campaign_v2(
        name=name,
        campaign_type=campaign_type,
        message_template=message_template,
        target_description=f"{len(contacts)} kontaktów",
    )

    added = 0
    skipped_unsubscribed = 0
    skipped_duplicate = 0

    for contact in contacts:
        phone = contact.get("phone", "").strip()
        if not phone:
            continue

        first_name = contact.get("first_name") or (contact.get("name", "").split()[0] if contact.get("name") else None)
        last_name = contact.get("last_name")

        # Pomiń wypisanych przy kampaniach marketingowych
        if campaign_type == "marketing" and is_unsubscribed(phone):
            skipped_unsubscribed += 1
            logger.debug("Pomijam wypisanego: %s", phone)
            continue

        # Utwórz/zaktualizuj kontakt
        contact_id = upsert_contact(
            phone_e164=phone,
            first_name=first_name,
            last_name=last_name,
            source=contact.get("source", "campaign"),
            consent_marketing=(campaign_type == "marketing"),
        )

        # Personalizuj wiadomość (token zostanie przypisany w add_recipient)
        result = add_recipient(
            campaign_id=campaign_id,
            contact_id=contact_id,
            phone_e164=phone,
            target_url=target_url,
        )

        if result.get("already_exists"):
            skipped_duplicate += 1
        else:
            # Teraz personalizuj z tokenem (target_url → ?ref={token})
            personalized = _personalize(
                message_template,
                first_name=first_name,
                tracking_token=result["tracking_token"],
                target_url=target_url,
            )
            if campaign_type == "marketing":
                personalized = _add_stop_suffix(personalized)
            personalized = _strip_sms(personalized, max_len=SMS_MAX_LEN)

            # Zapisz spersonalizowaną wiadomość
            import sqlite3, os as _os
            db_path = _os.path.join(_os.path.dirname(__file__), "memory.db")
            with sqlite3.connect(db_path) as c:
                c.execute(
                    "UPDATE sms_recipients SET personalized_message = ? WHERE id = ?",
                    (personalized, result["id"])
                )
            added += 1

    update_campaign_counters(campaign_id)
    logger.info(
        "Kampania %d '%s' przygotowana: dodano=%d, pominięto(unsub)=%d, pominięto(dup)=%d",
        campaign_id, name, added, skipped_unsubscribed, skipped_duplicate,
    )

    return {
        "campaign_id": campaign_id,
        "name": name,
        "type": campaign_type,
        "added": added,
        "skipped_unsubscribed": skipped_unsubscribed,
        "skipped_duplicate": skipped_duplicate,
        "total": len(contacts),
    }


def send_campaign_batch(
    campaign_id: int,
    batch_size: int = BATCH_SIZE_DEFAULT,
    dry_run: bool = False,
) -> dict:
    """
    Wysyła batch_size SMSów dla kampanii.
    - Pobiera recipients WHERE status='pending' ORDER BY id (wznawialność)
    - Pomija wypisanych kontaktów
    - Rate limit: batch_size na wywołanie, 2s przerwa między batchami
    - Retry: max 3 próby, exponential backoff 5→15→45s
    - Idempotency: nie wysyła ponownie jeśli status != 'pending' i != 'failed'

    Zwraca dict ze statystykami batcha.
    """
    from sms import send_sms
    from sms_tracker import (
        get_pending_recipients, mark_recipient_sent,
        update_campaign_counters, update_campaign_status,
    )
    from sms_migrations import run_migrations

    run_migrations()

    update_campaign_status(campaign_id, "sending")

    sent_ok = 0
    sent_failed = 0
    sent_skipped = 0
    processed = 0

    recipients = get_pending_recipients(campaign_id, limit=batch_size)

    if not recipients:
        logger.info("Kampania %d: brak pending odbiorców", campaign_id)
        update_campaign_status(campaign_id, "completed")
        return {
            "campaign_id": campaign_id,
            "sent_ok": 0,
            "sent_failed": 0,
            "sent_skipped": 0,
            "total_processed": 0,
            "status": "completed_no_pending",
        }

    for i, recipient in enumerate(recipients):
        recipient_id = recipient["id"]
        phone = recipient["phone_e164"]
        message = recipient.get("personalized_message") or recipient.get("personalized_message", "")
        attempts = recipient.get("send_attempts", 0)

        # Pomiń wypisanych (double-check)
        if recipient.get("unsubscribed_at"):
            if not dry_run:
                mark_recipient_sent(recipient_id, status="unsubscribed")
            sent_skipped += 1
            processed += 1
            logger.debug("Pominam wypisanego odbiorcę: %s", phone)
            continue

        if not message:
            logger.warning("Brak treści SMS dla recipient_id=%d, phone=%s", recipient_id, phone)
            if not dry_run:
                mark_recipient_sent(recipient_id, status="failed", error="brak_tresci")
            sent_failed += 1
            processed += 1
            continue

        if dry_run:
            logger.info(
                "[DRY RUN] Wysyłam do %s (odbiorca=%d): %s",
                phone, recipient_id, message[:80]
            )
            sent_ok += 1
            processed += 1
            continue

        # Exponential backoff przy kolejnych próbach
        if attempts > 0:
            delay = RETRY_DELAYS[min(attempts - 1, len(RETRY_DELAYS) - 1)]
            logger.info(
                "Retry #%d dla odbiorca=%d, czekam %ds",
                attempts + 1, recipient_id, delay
            )
            time.sleep(delay)

        # Wyślij SMS
        result = send_sms(phone, message)

        if result.get("error"):
            logger.warning(
                "Błąd wysyłki do %s (odbiorca=%d, próba=%d): %s",
                phone, recipient_id, attempts + 1, result["error"]
            )
            new_status = "failed" if attempts + 1 >= MAX_ATTEMPTS else "failed"
            mark_recipient_sent(
                recipient_id,
                status=new_status,
                error=str(result.get("error", ""))[:500],
            )
            sent_failed += 1
        else:
            provider_msg_id = str(result.get("id", "") or result.get("message_id", "") or "")
            mark_recipient_sent(
                recipient_id,
                provider_message_id=provider_msg_id or None,
                status="sent",
            )
            logger.info("SMS wysłany do %s (odbiorca=%d)", phone, recipient_id)
            sent_ok += 1

        processed += 1

        # Pauza między batchami co BATCH_SIZE_DEFAULT wysyłek
        # (rate limit: max 20/min → 1 batch = 20 SMS → sleep 2s)
        if (i + 1) % batch_size == 0 and i < len(recipients) - 1:
            logger.info("Batch %d wysłany, czekam %ds...", (i + 1) // batch_size, BATCH_SLEEP_SEC)
            time.sleep(BATCH_SLEEP_SEC)

    update_campaign_counters(campaign_id)

    # Sprawdź czy są jeszcze pending
    remaining = get_pending_recipients(campaign_id, limit=1)
    final_status = "sending" if remaining else "completed"
    update_campaign_status(campaign_id, final_status)

    logger.info(
        "Batch kampanii %d: ok=%d, failed=%d, skipped=%d | status=%s",
        campaign_id, sent_ok, sent_failed, sent_skipped, final_status,
    )

    return {
        "campaign_id": campaign_id,
        "sent_ok": sent_ok,
        "sent_failed": sent_failed,
        "sent_skipped": sent_skipped,
        "total_processed": processed,
        "status": final_status,
        "has_more": bool(remaining),
    }


def get_campaign_status(campaign_id: int) -> dict:
    """Zwraca aktualny status kampanii v2 ze statystykami."""
    from sms_tracker import get_campaign_v2, update_campaign_counters

    update_campaign_counters(campaign_id)
    campaign = get_campaign_v2(campaign_id)
    if not campaign:
        return {"error": f"Kampania {campaign_id} nie istnieje"}

    total = campaign.get("total_recipients") or 0
    sent = campaign.get("total_sent") or 0
    failed = campaign.get("total_failed") or 0
    clicked = campaign.get("total_clicked") or 0

    return {
        "campaign_id": campaign_id,
        "name": campaign.get("name"),
        "type": campaign.get("type"),
        "status": campaign.get("status"),
        "total_recipients": total,
        "total_sent": sent,
        "total_failed": failed,
        "total_delivered": campaign.get("total_delivered") or 0,
        "total_clicked": clicked,
        "total_converted": campaign.get("total_converted") or 0,
        "click_rate": f"{clicked/sent*100:.1f}%" if sent > 0 else "—",
        "created_at": campaign.get("created_at"),
        "updated_at": campaign.get("updated_at"),
    }


# =============================================================================
# v1 LEGACY — zachowane dla kompatybilności z istniejącym main.py
# =============================================================================

def run_campaign(topic: str, label: str = None, dry_run: bool = False,
                 message: str = None) -> dict:
    """
    [LEGACY v1] Uruchamia kampanię SMS.

    topic    — temat/instrukcja dla Alicji (generowanie treści)
    label    — opcjonalna etykieta Google Contacts do filtrowania (np. "Klienci")
    dry_run  — jeśli True, tylko generuje treść i listę kontaktów bez wysyłki
    message  — jeśli podany, używa tej treści zamiast generowania przez Alicję

    Zwraca słownik z wynikami kampanii.
    """
    from claude_agent import get_reply
    from google_contacts import get_contacts_with_phones
    from sms import send_bulk_sms
    from sms_tracker import record_sends

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
    campaign_key = f"{topic[:40]}_{datetime.now().strftime('%Y%m%d')}"

    if dry_run:
        logger.info("Dry run — pomijam wysyłkę. Kontaktów: %d", len(contacts))
        return {
            "status": "dry_run",
            "message": message,
            "contacts_count": len(contacts),
            "contacts_preview": contacts[:5],
            "campaign_key": campaign_key,
        }

    results = send_bulk_sms(contacts, message)
    success = sum(1 for r in results if not r["result"].get("error"))

    try:
        record_sends(campaign_key, results, message, topic)
    except Exception as e:
        logger.warning("Błąd zapisu do sms_tracker: %s", e)

    return {
        "status": "sent",
        "message": message,
        "contacts_count": len(contacts),
        "success_count": success,
        "failed_count": len(contacts) - success,
        "campaign_key": campaign_key,
        "results": results,
    }


def send_reminder(phone: str, name: str, course_name: str, date: str, hour: str) -> dict:
    """
    [LEGACY v1] Wysyła przypomnienie o kursie do konkretnego klienta.
    """
    from claude_agent import get_reply
    from sms import send_sms

    prompt = (
        f"Napisz SMS-przypomnienie dla klienta imieniem {name} o kursie '{course_name}' "
        f"zaplanowanym na {date} o {hour}. Max {SMS_MAX_LEN} znaków. "
        f"Podpisz jako FUN like HEL. Pisz ciepło i konkretnie."
    )
    msg = get_reply(prompt)

    if len(msg) > SMS_MAX_LEN:
        msg = msg[:SMS_MAX_LEN - 3] + "..."

    logger.info("Przypomnienie SMS dla %s (%s): %s", name, phone, msg)
    return send_sms(phone, msg)


def send_notification(phone: str, name: str, content: str) -> dict:
    """
    [LEGACY v1] Wysyła dowolne powiadomienie SMS do klienta.
    """
    from claude_agent import get_reply
    from sms import send_sms

    prompt = (
        f"Napisz powiadomienie SMS dla klienta imieniem {name}. "
        f"Treść: {content}. Max {SMS_MAX_LEN} znaków. Pisz ciepło i konkretnie."
    )
    msg = get_reply(prompt)

    if len(msg) > SMS_MAX_LEN:
        msg = msg[:SMS_MAX_LEN - 3] + "..."

    logger.info("Powiadomienie SMS dla %s (%s)", name, phone)
    return send_sms(phone, msg)


# =============================================================================
# CLI — testowanie bez serwera
# =============================================================================

if __name__ == "__main__":
    import json
    import os

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # Upewnij się, że jesteśmy w katalogu server/
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser(
        description="FUN like HEL — SMS Campaign CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady:
  # Test pojedynczego SMS (dry-run)
  python sms_campaign.py --dry-run --test-phone +48690270032 --message "Test SMS FLH"

  # Przygotuj kampanię z pliku JSON
  python sms_campaign.py --prepare --name "Lato 2025" --type marketing \\
      --template "Hej {{first_name}}! Zapisz się na kurs: {{registration_link}}" \\
      --contacts contacts.json

  # Wyślij batch kampanii
  python sms_campaign.py --campaign-id 1 --send --batch-size 20

  # Podgląd statusu kampanii
  python sms_campaign.py --campaign-id 1 --status

  # Kontynuuj wysyłkę (wznowienie po błędzie)
  python sms_campaign.py --campaign-id 1 --send --batch-size 50
        """,
    )

    # Tryb 1: Test SMS
    parser.add_argument("--dry-run", action="store_true", help="Nie wysyłaj prawdziwych SMS")
    parser.add_argument("--test-phone", help="Numer testowy (np. +48690270032)")
    parser.add_argument("--message", help="Treść SMS do wysłania")

    # Tryb 2: Przygotowanie kampanii
    parser.add_argument("--prepare", action="store_true", help="Przygotuj kampanię v2")
    parser.add_argument("--name", help="Nazwa kampanii")
    parser.add_argument("--type", choices=["marketing", "transactional"], help="Typ kampanii")
    parser.add_argument("--template", help="Szablon wiadomości z {{placeholders}}")
    parser.add_argument("--contacts", help="Plik JSON z listą kontaktów [{phone, first_name, ...}]")
    parser.add_argument("--target-url", default="https://funlikehel.pl", help="URL trackingowy")

    # Tryb 3: Wysyłka / status
    parser.add_argument("--campaign-id", type=int, help="ID kampanii v2")
    parser.add_argument("--send", action="store_true", help="Wyślij batch kampanii")
    parser.add_argument("--status", action="store_true", help="Pokaż status kampanii")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE_DEFAULT, help="Rozmiar batcha")

    args = parser.parse_args()

    # --- Tryb 1: Test SMS ---
    if args.test_phone and args.message:
        from sms import send_sms
        from sms_tracker import generate_tracking_token, build_tracking_link

        token = generate_tracking_token()
        link = build_tracking_link(token)
        msg = args.message.replace("{{registration_link}}", link)
        msg = _strip_sms(msg, max_len=SMS_MAX_LEN)

        print(f"\n--- Test SMS ---")
        print(f"Do: {args.test_phone}")
        print(f"Treść ({len(msg)} znaków):\n{msg}")
        print(f"Token: {token}")
        print(f"Link: {link}")

        if args.dry_run:
            print("\n[DRY RUN] SMS nie wysłany.")
        else:
            result = send_sms(args.test_phone, msg)
            print(f"\nWynik: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # --- Tryb 2: Przygotowanie kampanii ---
    elif args.prepare:
        if not all([args.name, args.type, args.template, args.contacts]):
            parser.error("--prepare wymaga: --name, --type, --template, --contacts")

        with open(args.contacts, encoding="utf-8") as f:
            contacts = json.load(f)

        print(f"\n--- Przygotowanie kampanii '{args.name}' ---")
        print(f"Typ: {args.type}")
        print(f"Szablon: {args.template}")
        print(f"Kontaktów: {len(contacts)}")

        result = prepare_campaign(
            name=args.name,
            campaign_type=args.type,
            message_template=args.template,
            contacts=contacts,
            target_url=args.target_url,
        )
        print(f"\nWynik: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # --- Tryb 3: Wysyłka batcha ---
    elif args.campaign_id and args.send:
        print(f"\n--- Wysyłka batcha kampanii {args.campaign_id} ---")
        print(f"Batch size: {args.batch_size}")
        if args.dry_run:
            print("[DRY RUN] Wysyłka symulowana.")

        result = send_campaign_batch(
            campaign_id=args.campaign_id,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )
        print(f"\nWynik: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # --- Tryb 4: Status kampanii ---
    elif args.campaign_id and args.status:
        result = get_campaign_status(args.campaign_id)
        print(f"\n--- Status kampanii {args.campaign_id} ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        parser.print_help()
