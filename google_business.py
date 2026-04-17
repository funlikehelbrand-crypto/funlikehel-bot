"""
Obsługa Google Business Profile — odpowiadanie na recenzje, posty, statystyki.
"""

import logging
import httpx
from google_auth import get_credentials
from claude_agent import get_reply

logger = logging.getLogger(__name__)

BASE_URL = "https://mybusinessaccountmanagement.googleapis.com/v1"
REVIEWS_URL = "https://mybusiness.googleapis.com/v4"


def _headers() -> dict:
    creds = get_credentials()
    return {"Authorization": f"Bearer {creds.token}"}


# ---------------------------------------------------------------------------
# Konta i lokalizacje
# ---------------------------------------------------------------------------

def get_accounts() -> list[dict]:
    """Pobiera listę kont Google Business."""
    resp = httpx.get(f"{BASE_URL}/accounts", headers=_headers())
    resp.raise_for_status()
    return resp.json().get("accounts", [])


def get_locations(account_name: str) -> list[dict]:
    """Pobiera lokalizacje dla danego konta."""
    resp = httpx.get(
        f"https://mybusinessbusinessinformation.googleapis.com/v1/{account_name}/locations",
        params={"readMask": "name,title,phoneNumbers,websiteUri,storefrontAddress"},
        headers=_headers(),
    )
    resp.raise_for_status()
    return resp.json().get("locations", [])


# ---------------------------------------------------------------------------
# Recenzje
# ---------------------------------------------------------------------------

def get_reviews(account_name: str, location_name: str) -> list[dict]:
    """Pobiera recenzje dla lokalizacji."""
    resp = httpx.get(
        f"{REVIEWS_URL}/{account_name}/{location_name}/reviews",
        headers=_headers(),
    )
    resp.raise_for_status()
    reviews = resp.json().get("reviews", [])

    # Zwracamy tylko recenzje bez odpowiedzi
    return [r for r in reviews if "reviewReply" not in r]


def reply_to_review(account_name: str, location_name: str, review_name: str, reply_text: str) -> dict:
    """Odpowiada na recenzję."""
    resp = httpx.put(
        f"{REVIEWS_URL}/{account_name}/{location_name}/{review_name}/reply",
        headers=_headers(),
        json={"comment": reply_text},
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Posty (Google Posts)
# ---------------------------------------------------------------------------

def create_post(account_name: str, location_name: str, text: str, call_to_action: str = None) -> dict:
    """Publikuje post na Google Business Profile."""
    body = {
        "languageCode": "pl",
        "summary": text,
        "topicType": "STANDARD",
    }
    if call_to_action:
        body["callToAction"] = {
            "actionType": "LEARN_MORE",
            "url": call_to_action,
        }

    resp = httpx.post(
        f"{REVIEWS_URL}/{account_name}/{location_name}/localPosts",
        headers=_headers(),
        json=body,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Automatyczna obsługa recenzji przez agenta
# ---------------------------------------------------------------------------

def process_reviews():
    """
    Pobiera recenzje bez odpowiedzi i automatycznie odpowiada przez agenta.
    """
    try:
        accounts = get_accounts()
        if not accounts:
            logger.info("Brak kont Google Business.")
            return

        for account in accounts:
            account_name = account["name"]
            locations = get_locations(account_name)

            for location in locations:
                location_name = location["name"].split("/")[-1]
                full_location = f"{account_name}/locations/{location_name}"
                reviews = get_reviews(account_name, full_location)

                if not reviews:
                    logger.info("Brak nowych recenzji dla %s.", location.get("title", location_name))
                    continue

                for review in reviews:
                    reviewer = review.get("reviewer", {}).get("displayName", "Klient")
                    comment = review.get("comment", "")
                    rating = review.get("starRating", "")
                    review_name = review["name"]

                    logger.info("Recenzja od %s (%s gwiazdek): %s", reviewer, rating, comment[:80])

                    prompt = (
                        f"Recenzja Google od {reviewer} (ocena: {rating}/5):\n{comment}\n\n"
                        f"Napisz krótką, profesjonalną odpowiedź w imieniu szkoły FUN like HEL."
                    )
                    reply_text = get_reply(prompt, sender_id=reviewer, channel="google_business")
                    reply_to_review(account_name, full_location, review_name, reply_text)
                    logger.info("Odpowiedź na recenzję wysłana.")

    except Exception as e:
        if "403" in str(e):
            logger.warning("Google Business API — włącz API w Google Cloud Console: "
                           "console.developers.google.com/apis/api/mybusinessaccountmanagement.googleapis.com")
        else:
            logger.error("Błąd Google Business: %s", e)
