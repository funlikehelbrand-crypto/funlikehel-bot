import httpx
import os

GRAPH_API_URL = "https://graph.facebook.com/v21.0"


async def send_dm(recipient_id: str, text: str) -> dict:
    """Wysyła wiadomość DM do użytkownika Instagrama."""
    token = os.environ["PAGE_ACCESS_TOKEN"]
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


async def reply_to_comment(comment_id: str, text: str) -> dict:
    """Odpowiada na komentarz pod postem."""
    token = os.environ["PAGE_ACCESS_TOKEN"]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GRAPH_API_URL}/{comment_id}/replies",
            params={"access_token": token},
            json={"message": text},
        )
        response.raise_for_status()
        return response.json()


async def get_user_name(user_id: str) -> str:
    """Pobiera nazwę użytkownika (opcjonalnie, do logów)."""
    token = os.environ["PAGE_ACCESS_TOKEN"]
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GRAPH_API_URL}/{user_id}",
                params={"fields": "name", "access_token": token},
            )
            data = response.json()
            return data.get("name", user_id)
    except Exception:
        return user_id
