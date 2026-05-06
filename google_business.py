"""
Obsługa Google Business Profile — odpowiadanie na recenzje, posty, statystyki.

Odczyt recenzji: Google Places API (klucz GOOGLE_PLACES_API_KEY)
  — zwraca top 5 najnowszych/trafnych recenzji, nie wymaga approval

Odpowiadanie: My Business Reviews API v1 (OAuth, scope business.manage)
  — wymaga zatwierdzenia wniosku na developers.google.com/my-business
  — do czasu zatwierdzenia: odpowiedzi ręcznie przez Google Maps

Place IDs (Google Maps):
  - Surf4Hel Jastarnia:  ChIJReGbmLWr_UYRSuqTxBLTWCo  (3.8★, 10 opinii)
  - FLH Cabrinha Hurghada: ChIJneSubzplUhQRoTp3jejCc5w (5★, 15 opinii)
"""

import logging
import os
import httpx
from dotenv import load_dotenv

load_dotenv("api.env")

logger = logging.getLogger(__name__)

PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
PLACES_URL     = "https://places.googleapis.com/v1"
REVIEWS_URL    = "https://mybusinessreviews.googleapis.com/v1"
ACCOUNTS_URL   = "https://mybusinessaccountmanagement.googleapis.com/v1"
LOCATIONS_URL  = "https://mybusinessbusinessinformation.googleapis.com/v1"

# Znane profile Google Maps FUN like HEL
PLACE_IDS = {
    "funlikehel_jastarnia": "ChIJZyeuqzWr_UYRHCeYzksTZi8",   # główny profil FLH, 0 opinii — tu zbieramy
    "surf4hel_jastarnia":   "ChIJReGbmLWr_UYRSuqTxBLTWCo",   # Surf4Hel, 3.8★ — tu odpowiadamy na złe
    "flh_hurghada":         "ChIJneSubzplUhQRoTp3jejCc5w",    # Hurghada, 5★
}

# Linki do wystawiania opinii (direct review link)
REVIEW_LINKS = {
    "funlikehel_jastarnia": "https://search.google.com/local/writereview?placeid=ChIJZyeuqzWr_UYRHCeYzksTZi8",
    "surf4hel_jastarnia":   "https://search.google.com/local/writereview?placeid=ChIJReGbmLWr_UYRSuqTxBLTWCo",
    "flh_hurghada":         "https://search.google.com/local/writereview?placeid=ChIJneSubzplUhQRoTp3jejCc5w",
}

def get_review_link(profile: str = "funlikehel_jastarnia") -> str:
    """Zwraca bezpośredni link do wystawienia opinii na Google Maps."""
    return REVIEW_LINKS.get(profile, REVIEW_LINKS["funlikehel_jastarnia"])


# ---------------------------------------------------------------------------
# Odczyt recenzji przez Places API (bez approval, top 5)
# ---------------------------------------------------------------------------

def get_reviews_by_place_id(place_id: str, language: str = "pl") -> dict:
    """
    Pobiera dane miejsca + top 5 recenzji przez Places API (New).
    Nie wymaga zatwierdzonego dostępu do Business Profile API.
    """
    if not PLACES_API_KEY:
        raise RuntimeError("Brak GOOGLE_PLACES_API_KEY w api.env")

    resp = httpx.get(
        f"{PLACES_URL}/places/{place_id}",
        headers={
            "X-Goog-Api-Key": PLACES_API_KEY,
            "X-Goog-FieldMask": "displayName,rating,userRatingCount,reviews,formattedAddress",
        },
        params={"languageCode": language},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_all_reviews(language: str = "pl") -> list[dict]:
    """
    Pobiera recenzje ze wszystkich znanych profili Google Maps FLH.
    Zwraca listę słowników: {profile, place_id, author, rating, text, published}.
    """
    all_reviews = []

    for profile_key, place_id in PLACE_IDS.items():
        try:
            data = get_reviews_by_place_id(place_id, language)
            profile_name = data.get("displayName", {}).get("text", profile_key)
            reviews = data.get("reviews", [])
            rating  = data.get("rating")
            count   = data.get("userRatingCount")

            logger.info("%s: %s★ (%s opinii), pobrano %d recenzji", profile_name, rating, count, len(reviews))

            for r in reviews:
                all_reviews.append({
                    "profile":     profile_key,
                    "profile_name": profile_name,
                    "place_id":    place_id,
                    "review_name": r.get("name", ""),
                    "author":      r.get("authorAttribution", {}).get("displayName", "Klient"),
                    "rating":      r.get("rating", 0),
                    "text":        r.get("text", {}).get("text", ""),
                    "published":   r.get("relativePublishTimeDescription", ""),
                    "has_reply":   "reviewReply" in r,
                })
        except Exception as e:
            logger.error("Błąd pobierania recenzji dla %s (%s): %s", profile_key, place_id, e)

    return all_reviews


# ---------------------------------------------------------------------------
# Odpowiadanie przez Business Profile API v1 (wymaga approval od Google)
# ---------------------------------------------------------------------------

def _auth_headers() -> dict:
    from google_auth import get_credentials
    creds = get_credentials()
    return {"Authorization": f"Bearer {creds.token}"}


def get_accounts() -> list[dict]:
    resp = httpx.get(f"{ACCOUNTS_URL}/accounts", headers=_auth_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json().get("accounts", [])


def get_locations(account_name: str) -> list[dict]:
    resp = httpx.get(
        f"{LOCATIONS_URL}/{account_name}/locations",
        params={"readMask": "name,title,phoneNumbers,websiteUri,storefrontAddress"},
        headers=_auth_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("locations", [])


def get_reviews_via_api(parent: str) -> list[dict]:
    """
    parent = "accounts/{accountId}/locations/{locationId}"
    Wymaga zatwierdzonego dostępu Business Profile API (quota > 0).
    """
    resp = httpx.get(
        f"{REVIEWS_URL}/{parent}/reviews",
        headers=_auth_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    reviews = resp.json().get("reviews", [])
    return [r for r in reviews if "reviewReply" not in r]


def reply_to_review(review_name: str, reply_text: str) -> dict:
    """
    review_name = "accounts/{accountId}/locations/{locationId}/reviews/{reviewId}"
    Wymaga zatwierdzonego dostępu Business Profile API.
    """
    resp = httpx.put(
        f"{REVIEWS_URL}/{review_name}/reply",
        headers=_auth_headers(),
        json={"comment": reply_text},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Automatyczna obsługa recenzji (pętla serwera)
# ---------------------------------------------------------------------------

GBP_API_APPROVED = os.environ.get("GBP_API_APPROVED", "false").lower() == "true"
# Ustaw GBP_API_APPROVED=true w api.env gdy Google zatwierdzi wniosek (wniosek: 2026-05-03)


def process_reviews() -> int:
    """
    Główna funkcja pętli: sprawdza recenzje przez Places API i loguje bez odpowiedzi.
    Odpowiadanie przez Business Profile API: aktywne tylko gdy GBP_API_APPROVED=true.
    Zwraca liczbę recenzji bez odpowiedzi.
    """
    reviews = get_all_reviews()
    unanswered = [r for r in reviews if not r["has_reply"]]

    if not unanswered:
        logger.info("Google Reviews: brak recenzji bez odpowiedzi.")
        return 0

    logger.info("Google Reviews: %d recenzji bez odpowiedzi.", len(unanswered))
    for r in unanswered:
        logger.info("[%s★] %s @ %s (%s): %s",
                    r["rating"], r["author"], r["profile_name"], r["published"], r["text"][:80])

    if not GBP_API_APPROVED:
        logger.info(
            "Google Reviews: Business Profile API nie zatwierdzone — "
            "odpowiedz ręcznie: https://business.google.com/reviews  "
            "Gdy API zostanie zatwierdzone: ustaw GBP_API_APPROVED=true w api.env"
        )
        return len(unanswered)

    # --- Poniżej aktywne tylko po zatwierdzeniu API ---
    from claude_agent import get_reply

    for r in unanswered:
        prompt = (
            f"Recenzja Google Maps od {r['author']} na profilu \"{r['profile_name']}\" "
            f"(ocena: {r['rating']}/5, {r['published']}):\n{r['text']}\n\n"
            f"Napisz krótką, ciepłą odpowiedź w imieniu szkoły FUN like HEL."
        )
        try:
            reply_text = get_reply(prompt, sender_id=r["author"], channel="google_business")
            if r["review_name"]:
                reply_to_review(r["review_name"], reply_text)
                logger.info("Odpowiedź wysłana dla %s.", r["author"])
        except httpx.HTTPStatusError as e:
            logger.error("Błąd API reply dla %s: %s %s", r["author"],
                         e.response.status_code, e.response.text[:200])
        except Exception as e:
            logger.error("Błąd agenta dla %s: %s", r["author"], e)

    return len(unanswered)


# ---------------------------------------------------------------------------
# Diagnostyka — szybki test połączenia
# ---------------------------------------------------------------------------

def diagnose() -> dict:
    """Zwraca status obu profili i liczbę recenzji bez odpowiedzi."""
    result = {"profiles": [], "total_unanswered": 0, "api_key_ok": bool(PLACES_API_KEY)}

    for key, place_id in PLACE_IDS.items():
        try:
            data = get_reviews_by_place_id(place_id)
            reviews = data.get("reviews", [])
            unanswered = sum(1 for r in reviews if "reviewReply" not in r)
            result["profiles"].append({
                "key":        key,
                "name":       data.get("displayName", {}).get("text", key),
                "place_id":   place_id,
                "rating":     data.get("rating"),
                "total":      data.get("userRatingCount"),
                "fetched":    len(reviews),
                "unanswered": unanswered,
            })
            result["total_unanswered"] += unanswered
        except Exception as e:
            result["profiles"].append({"key": key, "place_id": place_id, "error": str(e)})

    return result
