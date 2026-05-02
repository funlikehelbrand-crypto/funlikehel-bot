"""
Instagram multi-account — obsługa wielu kont IG przez Graph API.

Konta:
  funlikehel — główne konto szkoły (env: PAGE_ACCESS_TOKEN)
  surf4hel   — drugie konto szkoły (env: Insta_surf4hel)
  (trzecie)  — do dodania (env: Insta_<nazwa>)

Alicja odpowiada na DM/komentarze na wszystkich kontach.
Kasia publikuje spójny content na wszystkich kontach.
"""

import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v21.0"


# ---------------------------------------------------------------------------
# Konfiguracja kont
# ---------------------------------------------------------------------------

@dataclass
class IGAccount:
    name: str
    token: str
    ig_user_id: str = ""
    username: str = ""


def _discover_ig_user_id(token: str) -> tuple[str, str]:
    """Pobiera IG User ID i username z tokena przez Graph API."""
    if not token:
        return "", ""
    try:
        r = httpx.get(
            f"{GRAPH_API_URL}/me/accounts",
            params={"access_token": token, "fields": "id,name,instagram_business_account"},
            timeout=15,
        )
        if r.status_code != 200:
            logger.warning("Nie mogę pobrać pages: %s", r.text[:200])
            return "", ""

        pages = r.json().get("data", [])
        for page in pages:
            ig = page.get("instagram_business_account")
            if ig:
                ig_id = ig["id"]
                r2 = httpx.get(
                    f"{GRAPH_API_URL}/{ig_id}",
                    params={"access_token": token, "fields": "username"},
                    timeout=10,
                )
                username = r2.json().get("username", "") if r2.status_code == 200 else ""
                return ig_id, username
    except Exception as e:
        logger.warning("Auto-discovery IG user ID failed: %s", e)
    return "", ""


def _discover_ig_user_id_instagram(token: str) -> tuple[str, str]:
    """Pobiera IG User ID z tokena IGAA (Instagram API, nie Facebook Graph)."""
    if not token:
        return "", ""
    try:
        r = httpx.get(
            "https://graph.instagram.com/v21.0/me",
            params={"access_token": token, "fields": "id,username"},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("id", ""), data.get("username", "")
    except Exception as e:
        logger.warning("Instagram API discovery failed: %s", e)
    return "", ""


def _load_accounts() -> dict[str, IGAccount]:
    """Ładuje konta IG z env vars."""
    accounts = {}

    # Konto główne: funlikehel
    main_token = os.environ.get("PAGE_ACCESS_TOKEN", "")
    if main_token:
        ig_id, username = _discover_ig_user_id(main_token)
        # Fallback: spróbuj Instagram API jeśli Facebook Graph nie zadziałał
        if not ig_id:
            ig_id, username = _discover_ig_user_id_instagram(main_token)
        accounts["funlikehel"] = IGAccount(
            name="funlikehel",
            token=main_token,
            ig_user_id=ig_id or "27441134238823713",
            username=username or "funlikehel",
        )

    # Konto surf4hel
    surf_token = os.environ.get("Insta_surf4hel", "")
    if surf_token:
        ig_id, username = _discover_ig_user_id(surf_token)
        if not ig_id:
            ig_id, username = _discover_ig_user_id_instagram(surf_token)
        accounts["surf4hel"] = IGAccount(
            name="surf4hel",
            token=surf_token,
            ig_user_id=ig_id or "35116715114638747",
            username=username or "surf4hel",
        )
        if ig_id:
            logger.info("surf4hel IG User ID: %s (@%s)", ig_id, username)
        else:
            logger.warning("surf4hel: nie udało się pobrać IG User ID")

    # Przyszłe konta: szukaj env Insta_* (poza surf4hel)
    for key, val in os.environ.items():
        if key.startswith("Insta_") and key != "Insta_surf4hel" and val:
            acct_name = key.replace("Insta_", "").lower()
            if acct_name not in accounts:
                ig_id, username = _discover_ig_user_id(val)
                if not ig_id:
                    ig_id, username = _discover_ig_user_id_instagram(val)
                accounts[acct_name] = IGAccount(
                    name=acct_name, token=val,
                    ig_user_id=ig_id, username=username or acct_name,
                )
                logger.info("Dodano konto IG: %s (@%s)", acct_name, username)

    return accounts


ACCOUNTS: dict[str, IGAccount] = {}


def init_accounts():
    """Inicjalizacja kont — wywoływana z main.py po załadowaniu env."""
    global ACCOUNTS
    ACCOUNTS = _load_accounts()
    logger.info("Załadowano %d kont IG: %s", len(ACCOUNTS), list(ACCOUNTS.keys()))


def get_account(name: str = "funlikehel") -> IGAccount | None:
    return ACCOUNTS.get(name)


def get_all_accounts() -> list[IGAccount]:
    return list(ACCOUNTS.values())


def find_account_by_ig_id(ig_user_id: str) -> IGAccount | None:
    """Znajduje konto po IG User ID (do routingu webhooków)."""
    for acct in ACCOUNTS.values():
        if acct.ig_user_id == ig_user_id:
            return acct
    return None


# ---------------------------------------------------------------------------
# Operacje — DM, komentarze
# ---------------------------------------------------------------------------

async def send_dm(recipient_id: str, text: str, account: str = "funlikehel") -> dict:
    """Wysyła wiadomość DM do użytkownika Instagrama."""
    acct = get_account(account)
    token = acct.token if acct else os.environ.get("PAGE_ACCESS_TOKEN", "")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GRAPH_API_URL}/me/messages",
            params={"access_token": token},
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": text},
            },
        )
        response.raise_for_status()
        return response.json()


async def reply_to_comment(comment_id: str, text: str, account: str = "funlikehel") -> dict:
    """Odpowiada na komentarz pod postem."""
    acct = get_account(account)
    token = acct.token if acct else os.environ.get("PAGE_ACCESS_TOKEN", "")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GRAPH_API_URL}/{comment_id}/replies",
            params={"access_token": token},
            json={"message": text},
        )
        response.raise_for_status()
        return response.json()


async def get_user_name(user_id: str, account: str = "funlikehel") -> str:
    """Pobiera nazwę użytkownika."""
    acct = get_account(account)
    token = acct.token if acct else os.environ.get("PAGE_ACCESS_TOKEN", "")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GRAPH_API_URL}/{user_id}",
                params={"fields": "name,username", "access_token": token},
            )
            data = response.json()
            return data.get("username", data.get("name", user_id))
    except Exception:
        return user_id


# ---------------------------------------------------------------------------
# Publikacja — posty, stories, reels
# ---------------------------------------------------------------------------

async def publish_post(image_url: str, caption: str, account: str = "funlikehel") -> dict:
    """Publikuje post ze zdjęciem na IG."""
    acct = get_account(account)
    if not acct or not acct.ig_user_id:
        raise ValueError(f"Konto IG '{account}' nie skonfigurowane lub brak ig_user_id")

    async with httpx.AsyncClient(timeout=60) as client:
        r1 = await client.post(
            f"{GRAPH_API_URL}/{acct.ig_user_id}/media",
            params={"access_token": acct.token},
            json={"image_url": image_url, "caption": caption},
        )
        r1.raise_for_status()
        creation_id = r1.json()["id"]

        r2 = await client.post(
            f"{GRAPH_API_URL}/{acct.ig_user_id}/media_publish",
            params={"access_token": acct.token},
            json={"creation_id": creation_id},
        )
        r2.raise_for_status()
        result = r2.json()
        logger.info("Post na @%s: %s", acct.username, result.get("id"))
        return result


async def publish_story(image_url: str, account: str = "funlikehel", link: str = "") -> dict:
    """Publikuje story ze zdjęciem."""
    acct = get_account(account)
    if not acct or not acct.ig_user_id:
        raise ValueError(f"Konto IG '{account}' nie skonfigurowane")

    payload = {"image_url": image_url, "media_type": "STORIES"}
    if link:
        payload["link"] = link

    async with httpx.AsyncClient(timeout=60) as client:
        r1 = await client.post(
            f"{GRAPH_API_URL}/{acct.ig_user_id}/media",
            params={"access_token": acct.token},
            json=payload,
        )
        r1.raise_for_status()
        creation_id = r1.json()["id"]

        r2 = await client.post(
            f"{GRAPH_API_URL}/{acct.ig_user_id}/media_publish",
            params={"access_token": acct.token},
            json={"creation_id": creation_id},
        )
        r2.raise_for_status()
        result = r2.json()
        logger.info("Story na @%s: %s", acct.username, result.get("id"))
        return result


async def publish_reel(video_url: str, caption: str, account: str = "funlikehel") -> dict:
    """Publikuje reel na IG."""
    acct = get_account(account)
    if not acct or not acct.ig_user_id:
        raise ValueError(f"Konto IG '{account}' nie skonfigurowane")

    async with httpx.AsyncClient(timeout=120) as client:
        r1 = await client.post(
            f"{GRAPH_API_URL}/{acct.ig_user_id}/media",
            params={"access_token": acct.token},
            json={"video_url": video_url, "caption": caption, "media_type": "REELS"},
        )
        r1.raise_for_status()
        creation_id = r1.json()["id"]

        r2 = await client.post(
            f"{GRAPH_API_URL}/{acct.ig_user_id}/media_publish",
            params={"access_token": acct.token},
            json={"creation_id": creation_id},
        )
        r2.raise_for_status()
        result = r2.json()
        logger.info("Reel na @%s: %s", acct.username, result.get("id"))
        return result


async def publish_to_all(image_url: str, caption: str, accounts: list[str] | None = None) -> dict[str, dict]:
    """Publikuje ten sam post na wielu kontach."""
    targets = accounts or list(ACCOUNTS.keys())
    results = {}
    for name in targets:
        try:
            result = await publish_post(image_url, caption, account=name)
            results[name] = {"ok": True, "id": result.get("id")}
        except Exception as e:
            logger.error("Błąd publikacji na @%s: %s", name, e)
            results[name] = {"ok": False, "error": str(e)}
    return results


# ---------------------------------------------------------------------------
# Statystyki
# ---------------------------------------------------------------------------

async def get_account_info(account: str = "funlikehel") -> dict:
    """Pobiera statystyki konta IG."""
    acct = get_account(account)
    if not acct or not acct.ig_user_id:
        return {}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{GRAPH_API_URL}/{acct.ig_user_id}",
                params={
                    "access_token": acct.token,
                    "fields": "username,followers_count,follows_count,media_count,biography",
                },
            )
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        logger.warning("Błąd info @%s: %s", acct.username, e)
    return {}
