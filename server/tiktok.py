"""
Obsługa TikTok — autoryzacja, upload filmów, wiadomości od klientów.
"""

import base64
import hashlib
import json
import logging
import math
import os
import secrets
import time
import httpx
from dotenv import load_dotenv

load_dotenv("api.env")

logger = logging.getLogger(__name__)

CLIENT_KEY = os.environ.get("TT_CLIENT_KEY", "")
CLIENT_SECRET = os.environ.get("TT_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("TT_REDIRECT_URI", "https://funlikehel-bot.onrender.com/tiktok/callback")

# Persistent token storage (przeżywa restart serwera)
_TOKEN_FILE = os.path.join(os.path.dirname(__file__), "tiktok_token.json")


def get_stored_token() -> dict | None:
    """Czyta token z pliku lub ze zmiennej środowiskowej TT_ACCESS_TOKEN."""
    # Najpierw env (Render secrets)
    env_token = os.environ.get("TT_ACCESS_TOKEN", "")
    env_refresh = os.environ.get("TT_REFRESH_TOKEN", "")
    if env_token:
        return {
            "access_token": env_token,
            "refresh_token": env_refresh,
            "expires_at": time.time() + 86400,  # zakładamy ważny
        }
    # Potem plik lokalny
    try:
        with open(_TOKEN_FILE) as f:
            return json.load(f)
    except Exception:
        return None


def save_token(token_data: dict):
    """Zapisuje token do pliku."""
    if "expires_in" in token_data and "expires_at" not in token_data:
        token_data["expires_at"] = time.time() + token_data["expires_in"]
    try:
        with open(_TOKEN_FILE, "w") as f:
            json.dump(token_data, f)
        logger.info("TikTok token zapisany do %s", _TOKEN_FILE)
    except Exception as e:
        logger.error("Błąd zapisu tokenu TikTok: %s", e)

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
    """Wymienia kod autoryzacyjny na access token (z PKCE) i zapisuje go."""
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
        data = response.json()
        save_token(data)
        return data


async def refresh_access_token(refresh_tok: str) -> dict:
    """Odświeża wygasły access token i zapisuje nowy."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": CLIENT_KEY,
                "client_secret": CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_tok,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        data = response.json()
        save_token(data)
        return data


async def get_valid_access_token() -> str:
    """Zwraca ważny access token (odświeża automatycznie jeśli wygasł)."""
    token_data = get_stored_token()
    if not token_data:
        raise RuntimeError("Brak tokenu TikTok. Otwórz /tiktok/login w przeglądarce.")

    # Odśwież jeśli zostało < 5 min
    if token_data.get("expires_at", 0) < time.time() + 300:
        if not token_data.get("refresh_token"):
            raise RuntimeError("Token wygasł i brak refresh_token. Zaloguj ponownie: /tiktok/login")
        token_data = await refresh_access_token(token_data["refresh_token"])

    return token_data["access_token"]


# ---------------------------------------------------------------------------
# Upload filmów
# ---------------------------------------------------------------------------

async def upload_video_file(access_token: str, video_path: str, caption: str,
                           privacy_level: str = "PUBLIC_TO_EVERYONE") -> str:
    """
    Wgrywa plik wideo bezpośrednio na TikTok (chunked FILE_UPLOAD).
    Zwraca publish_id.
    """
    file_size = os.path.getsize(video_path)
    chunk_size = 10 * 1024 * 1024  # 10 MB chunks (max allowed)
    total_chunks = math.ceil(file_size / chunk_size)

    async with httpx.AsyncClient(timeout=120) as client:
        # Krok 1: inicjalizacja uploadu
        init_resp = await client.post(
            "https://open.tiktokapis.com/v2/post/publish/video/init/",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={
                "post_info": {
                    "title": caption[:2200],
                    "privacy_level": privacy_level,
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": file_size,
                    "chunk_size": chunk_size,
                    "total_chunk_count": total_chunks,
                },
            },
        )
        init_resp.raise_for_status()
        init_data = init_resp.json()
        publish_id = init_data["data"]["publish_id"]
        upload_url = init_data["data"]["upload_url"]
        logger.info("TikTok upload zainicjowany. publish_id=%s, chunks=%d", publish_id, total_chunks)

        # Krok 2: upload chunków
        with open(video_path, "rb") as fh:
            for idx in range(total_chunks):
                chunk = fh.read(chunk_size)
                start = idx * chunk_size
                end = start + len(chunk) - 1
                put_resp = await client.put(
                    upload_url,
                    content=chunk,
                    headers={
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                        "Content-Length": str(len(chunk)),
                        "Content-Type": "video/mp4",
                    },
                )
                put_resp.raise_for_status()
                logger.info("TikTok chunk %d/%d OK", idx + 1, total_chunks)

    return publish_id


def upload_video_file_sync(video_path: str, caption: str,
                           privacy_level: str = "PUBLIC_TO_EVERYONE") -> str:
    """Synchroniczny wrapper — do użycia z pipeline (subprocess/script)."""
    import asyncio

    async def _run():
        token = await get_valid_access_token()
        return await upload_video_file(token, video_path, caption, privacy_level)

    return asyncio.run(_run())


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
