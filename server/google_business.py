"""
Obsługa Google Business Profile — odpowiadanie na recenzje, posty, statystyki.

API v1 (aktualne, zastąpiło deprecated v4 z 2022):
- mybusinessaccountmanagement.googleapis.com/v1  — konta
- mybusinessbusinessinformation.googleapis.com/v1 — lokalizacje
- mybusinessreviews.googleapis.com/v1             — recenzje
"""

import logging
import httpx
from google_auth import get_credentials
from claude_agent import get_reply

logger = logging.getLogger(__name__)

ACCOUNTS_URL  = "https://mybusinessaccountmanagement.googleapis.com/v1"
LOCATIONS_URL = "https://mybusinessbusinessinformation.googleapis.com/v1"
# Reviews via v4 (mybusinessreviews.googleapis.com/v1 daje 404 — użyj v4)
V4_URL        = "https://mybusiness.googleapis.com/v4"
POSTS_URL     = "https://mybusiness.googleapis.com/v4"


def _headers() -> dict:
    creds = get_credentials()
    return {"Authorization": f"Bearer {creds.token}"}


# ---------------------------------------------------------------------------
# Konta i lokalizacje
# ---------------------------------------------------------------------------

def get_accounts() -> list[dict]:
    """Pobiera listę kont Google Business."""
    resp = httpx.get(f"{ACCOUNTS_URL}/accounts", headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json().get("accounts", [])


def get_locations(account_name: str) -> list[dict]:
    """
    Pobiera lokalizacje dla danego konta.
    account_name = "accounts/{id}"
    """
    resp = httpx.get(
        f"{LOCATIONS_URL}/{account_name}/locations",
        params={"readMask": "name,title,phoneNumbers,websiteUri,storefrontAddress"},
        headers=_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("locations", [])


# ---------------------------------------------------------------------------
# Recenzje
# ---------------------------------------------------------------------------

def get_reviews(parent: str) -> list[dict]:
    """
    Pobiera recenzje dla lokalizacji bez odpowiedzi.
    parent = "accounts/{accountId}/locations/{locationId}"
    Uses v4 API (mybusiness.googleapis.com/v4).
    """
    resp = httpx.get(
        f"{V4_URL}/{parent}/reviews",
        headers=_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    reviews = resp.json().get("reviews", [])
    # Zwracamy tylko recenzje bez odpowiedzi
    return [r for r in reviews if "reviewReply" not in r]


def reply_to_review(review_name: str, reply_text: str) -> dict:
    """
    Odpowiada na recenzję.
    review_name = "accounts/{accountId}/locations/{locationId}/reviews/{reviewId}"
    Uses v4 API.
    """
    resp = httpx.put(
        f"{V4_URL}/{review_name}/reply",
        headers=_headers(),
        json={"comment": reply_text},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Posty (Google Posts) — v4 nadal obsługiwane
# ---------------------------------------------------------------------------

def create_post(account_name: str, location_name: str, text: str, call_to_action: str = None) -> dict:
    """
    Publikuje post na Google Business Profile.
    account_name   = "accounts/{id}"
    location_name  = "locations/{id}"
    """
    loc_id = location_name.split("/")[-1]
    url = f"{POSTS_URL}/{account_name}/locations/{loc_id}/localPosts"
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

    resp = httpx.post(url, headers=_headers(), json=body, timeout=15)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Automatyczna obsługa recenzji przez agenta
# ---------------------------------------------------------------------------

def process_reviews():
    """
    Pobiera recenzje bez odpowiedzi i automatycznie odpowiada przez agenta.
    Zwraca liczbę obsłużonych recenzji.
    """
    total = 0
    try:
        accounts = get_accounts()
        if not accounts:
            logger.info("Brak kont Google Business.")
            return 0

        for account in accounts:
            account_name = account["name"]  # np. "accounts/1234567"
            logger.info("Google Business — konto: %s", account_name)

            try:
                locations = get_locations(account_name)
            except httpx.HTTPStatusError as e:
                logger.error("Błąd pobierania lokalizacji dla %s: %s %s",
                             account_name, e.response.status_code, e.response.text[:200])
                continue

            for location in locations:
                loc_name = location["name"]           # np. "locations/9876543"
                loc_id   = loc_name.split("/")[-1]
                parent   = f"{account_name}/locations/{loc_id}"
                title    = location.get("title", loc_id)

                try:
                    reviews = get_reviews(parent)
                except httpx.HTTPStatusError as e:
                    logger.error("Błąd pobierania recenzji dla %s (%s): %s %s",
                                 title, parent, e.response.status_code, e.response.text[:200])
                    continue

                if not reviews:
                    logger.info("Brak nowych recenzji dla %s.", title)
                    continue

                logger.info("%d nowych recenzji dla %s.", len(reviews), title)

                for review in reviews:
                    reviewer    = review.get("reviewer", {}).get("displayName", "Klient")
                    comment     = review.get("comment", "")
                    rating      = review.get("starRating", "?")
                    review_name = review["name"]   # pełna ścieżka zasobu

                    logger.info("Recenzja od %s (%s★): %s", reviewer, rating, comment[:80])

                    prompt = (
                        f"Recenzja Google od {reviewer} (ocena: {rating}/5):\n{comment}\n\n"
                        f"Napisz krótką, profesjonalną odpowiedź w imieniu szkoły FUN like HEL."
                    )
                    try:
                        reply_text = get_reply(
                            prompt, sender_id=reviewer, channel="google_business"
                        )
                        reply_to_review(review_name, reply_text)
                        logger.info("Odpowiedź na recenzję wysłana dla %s.", reviewer)
                        total += 1
                        # Sync to panel Messages
                        try:
                            from google_mail import _sync_to_panel
                            _sync_to_panel(sender_email=reviewer, sender_name=f"Google {rating}★ {reviewer}", subject=f"Recenzja Google ({rating}★)", body=comment, reply=reply_text, status="ai_handled")
                        except: pass
                    except httpx.HTTPStatusError as e:
                        logger.error("Błąd odpowiedzi na recenzję %s: %s %s",
                                     review_name, e.response.status_code, e.response.text[:200])

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status == 403:
            logger.warning(
                "Google Business API — brak dostępu (403). "
                "Włącz API w Google Cloud Console:\n"
                "  • My Business Reviews API\n"
                "  • My Business Account Management API\n"
                "  • My Business Business Information API"
            )
        elif status == 401:
            logger.warning("Google Business API — token wygasł lub brak scope 'business.manage' (401).")
        else:
            logger.error("Google Business HTTP %s: %s", status, e.response.text[:300])
    except Exception as e:
        logger.error("Niespodziewany błąd Google Business: %s", e)

    return total


# ---------------------------------------------------------------------------
# Diagnostyka — wywołaj ręcznie żeby sprawdzić połączenie
# ---------------------------------------------------------------------------

def diagnose() -> dict:
    """Zwraca info diagnostyczne: konta, lokalizacje, liczba recenzji bez odpowiedzi."""
    result = {"accounts": [], "errors": []}
    try:
        accounts = get_accounts()
        for acc in accounts:
            acc_info = {"name": acc["name"], "locations": []}
            try:
                locs = get_locations(acc["name"])
                for loc in locs:
                    loc_id = loc["name"].split("/")[-1]
                    parent = f"{acc['name']}/locations/{loc_id}"
                    try:
                        reviews = get_reviews(parent)
                        acc_info["locations"].append({
                            "title": loc.get("title", loc_id),
                            "parent": parent,
                            "unanswered_reviews": len(reviews),
                        })
                    except Exception as e:
                        acc_info["locations"].append({
                            "title": loc.get("title", loc_id),
                            "error": str(e)
                        })
            except Exception as e:
                acc_info["error"] = str(e)
            result["accounts"].append(acc_info)
    except Exception as e:
        result["errors"].append(str(e))
    return result
