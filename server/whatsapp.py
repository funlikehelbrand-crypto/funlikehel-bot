"""
Integracja WhatsApp Cloud API — wysyłanie i odbieranie wiadomości.

WhatsApp Cloud API działa przez Graph API (wysyłka) i Webhooks (odbiór).
Dokumentacja: https://developers.facebook.com/docs/whatsapp/cloud-api
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v21.0"


def _get_config():
    """Pobiera konfigurację WhatsApp z env."""
    return {
        "token": os.environ.get("WHATSAPP_TOKEN", ""),
        "phone_number_id": os.environ.get("WHATSAPP_PHONE_NUMBER_ID", ""),
    }


async def send_message(to: str, text: str) -> dict:
    """
    Wysyła wiadomość tekstową przez WhatsApp Cloud API.

    to   — numer telefonu odbiorcy (format międzynarodowy, np. 48690270032)
    text — treść wiadomości
    """
    config = _get_config()
    if not config["token"] or not config["phone_number_id"]:
        logger.error("Brak WHATSAPP_TOKEN lub WHATSAPP_PHONE_NUMBER_ID")
        return {"error": "WhatsApp not configured"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GRAPH_API_URL}/{config['phone_number_id']}/messages",
            headers={
                "Authorization": f"Bearer {config['token']}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text},
            },
            timeout=15,
        )
        data = response.json()

        if response.status_code == 200:
            logger.info("WhatsApp wysłany do %s", to)
        else:
            logger.warning("WhatsApp błąd dla %s: %s", to, data)

        return data


async def mark_as_read(message_id: str) -> dict:
    """Oznacza wiadomość jako przeczytaną (niebieskie ptaszki)."""
    config = _get_config()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GRAPH_API_URL}/{config['phone_number_id']}/messages",
            headers={
                "Authorization": f"Bearer {config['token']}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
            },
            timeout=10,
        )
        return response.json()
