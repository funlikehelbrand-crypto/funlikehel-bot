"""
Czyszczenie skrzynki Gmail — usuwa spam, bounce'y i niechciane maile.
Uruchom: python cleanup_mail.py
"""

import logging
from googleapiclient.discovery import build
from google_auth import get_credentials

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


def get_service():
    return build("gmail", "v1", credentials=get_credentials())


def delete_messages(service, query: str, label: str):
    """Usuwa wszystkie wiadomości pasujące do zapytania."""
    deleted = 0
    page_token = None

    while True:
        params = {"userId": "me", "q": query, "maxResults": 500}
        if page_token:
            params["pageToken"] = page_token

        result = service.users().messages().list(**params).execute()
        messages = result.get("messages", [])

        if not messages:
            break

        ids = [m["id"] for m in messages]

        # Usuń hurtowo (max 1000 na raz)
        service.users().messages().batchDelete(
            userId="me",
            body={"ids": ids}
        ).execute()

        deleted += len(ids)
        logger.info("%s: usunięto %d wiadomości...", label, deleted)

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    logger.info("%s: łącznie usunięto %d wiadomości.", label, deleted)
    return deleted


def daily_cleanup():
    """Codzienny cleanup — spam, bounce, newslettery. BEZ kosza."""
    service = get_service()
    total = 0

    total += delete_messages(service, "in:spam", "SPAM")
    total += delete_messages(service, "from:mailer-daemon", "BOUNCE")
    total += delete_messages(service, "in:promotions", "PROMOCJE")
    total += delete_messages(service, "unsubscribe", "NEWSLETTERY")
    total += delete_messages(service, "from:noreply@buynotice.alibaba.com", "Alibaba")
    total += delete_messages(service, "from:player@player.pl", "Player.pl")

    logger.info("Codzienny cleanup: usunięto %d wiadomości.", total)
    return total


def trash_cleanup():
    """Co 2 miesiące — opróżnienie kosza."""
    service = get_service()
    total = delete_messages(service, "in:trash", "KOSZ")
    logger.info("Cleanup kosza: usunięto %d wiadomości.", total)
    return total


if __name__ == "__main__":
    potwierdzenie = input("Czy na pewno chcesz trwale usunąć wszystkie śmieci z Gmail? (tak/nie): ")
    if potwierdzenie.strip().lower() == "tak":
        daily_cleanup()
        trash_cleanup()
    else:
        print("Anulowano.")
