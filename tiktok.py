"""
Obsługa TikTok — autoryzacja, upload filmów, wiadomości od klientów.
"""

import base64
import hashlib
import logging
import os
import secrets
import httpx
from dotenv import load_dotenv

load_dotenv("api.env")

logger = logging.getLogger(__name__)

CLIENT_KEY = os.environ["TT_CLIENT_KEY"]
CLIENT_SECRET = os.environ["TT_CLIENT_SECRET"]
REDIRECT_URI = os.getenv("TT_REDIRECT_URI", "https://faceless-security-enactment.ngrok-free.dev/tiktok/callback")

SCOPES = [
    "user.info.basic",
    "video.upload",
    "video.publish",
]


# ---------------------------------------------------------------------------
# OAuth 2.0 z PKCE — autoryzacja
# ---------------------------------------------------------------------------

# Przechowuje code_verifier między krokami autoryzacji
_pkce_store: dict = {}


def _generate_pkce() -> tuple[str, str]:
    """Generuje code_verifier i code_challenge (PKCE S256)."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def get_auth_url() -> str:
    """Zwraca URL do autoryzacji TikTok z PKCE."""
    import urllib.parse
    code_verifier, code_challenge = _generate_pkce()
    _pkce_store["code_verifier"] = code_verifier

    params = {
        "client_key": CLIENT_KEY,
        "scope": ",".join(SCOPES),
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(params)


async def exchange_code_for_token(code: str) -> dict:
    """Wymienia kod autoryzacyjny na access token (z PKCE)."""
    code_verifier = _pkce_store.get("code_verifier", "")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": CLIENT_KEY,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()


async def refresh_token(refresh_token: str) -> dict:
    """Odświeża wygasły access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": CLIENT_KEY,
                "client_secret": CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# Upload filmów
# ---------------------------------------------------------------------------

async def upload_video_from_url(access_token: str, video_url: str, title: str) -> dict:
    """
    Publikuje film na TikTok przez URL (film musi być publicznie dostępny).
    """
    async with httpx.AsyncClient() as client:
        # Krok 1: inicjalizacja uploadu
        init_response = await client.post(
            "https://open.tiktokapis.com/v2/post/publish/video/init/",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "post_info": {
                    "title": title,
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "video_url": video_url,
                },
            },
        )
        init_response.raise_for_status()
        data = init_response.json()
        publish_id = data["data"]["publish_id"]
        logger.info("TikTok upload zainicjowany. Publish ID: %s", publish_id)
        return data


async def check_upload_status(access_token: str, publish_id: str) -> dict:
    """Sprawdza status uploadu filmu."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"publish_id": publish_id},
        )
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# Informacje o użytkowniku
# ---------------------------------------------------------------------------

async def get_user_info(access_token: str) -> dict:
    """Pobiera podstawowe informacje o koncie TikTok."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://open.tiktokapis.com/v2/user/info/",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": "open_id,union_id,avatar_url,display_name,follower_count,following_count,video_count"},
        )
        response.raise_for_status()
        return response.json()
