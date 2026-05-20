"""
SurfIQ Telegram Bot — two-way communication with school clients.

Uses Telegram Bot API for receiving and sending messages.
AI replies powered by Claude Haiku with SurfIQ product knowledge.

Setup:
    1. Create bot via @BotFather on Telegram → get TELEGRAM_BOT_TOKEN
    2. Set webhook: POST https://api.telegram.org/bot{TOKEN}/setWebhook
       body: {"url": "https://funlikehel-bot.onrender.com/api/telegram/webhook"}
    3. Add TELEGRAM_BOT_TOKEN to api.env

Usage:
    - Webhook receives messages at /api/telegram/webhook
    - Bot replies using SurfIQ chat AI (surfiq_chat.py)
    - Supports text messages in any language
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}"


def _get_token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


async def send_message(chat_id: int | str, text: str,
                       parse_mode: str = "HTML") -> dict:
    """Send a text message to a Telegram chat."""
    token = _get_token()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set")
        return {"ok": False, "error": "no token"}

    url = f"{TELEGRAM_API.format(token=token)}/sendMessage"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        })
        data = r.json()
        if not data.get("ok"):
            logger.error("Telegram send error: %s", data)
        return data


async def send_typing(chat_id: int | str):
    """Send typing indicator."""
    token = _get_token()
    if not token:
        return
    url = f"{TELEGRAM_API.format(token=token)}/sendChatAction"
    async with httpx.AsyncClient(timeout=5) as client:
        await client.post(url, json={"chat_id": chat_id, "action": "typing"})


async def set_webhook(webhook_url: str) -> dict:
    """Set the webhook URL for the bot."""
    token = _get_token()
    if not token:
        return {"ok": False, "error": "no token"}
    url = f"{TELEGRAM_API.format(token=token)}/setWebhook"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json={"url": webhook_url})
        return r.json()


async def get_webhook_info() -> dict:
    """Get current webhook info."""
    token = _get_token()
    if not token:
        return {"ok": False, "error": "no token"}
    url = f"{TELEGRAM_API.format(token=token)}/getWebhookInfo"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        return r.json()


# ── Conversation memory (simple in-memory for now) ──────────────────────────
_conversations: dict[int, list[dict]] = {}
MAX_HISTORY = 10


def _get_history(chat_id: int) -> list[dict]:
    return _conversations.get(chat_id, [])


def _add_to_history(chat_id: int, role: str, content: str):
    if chat_id not in _conversations:
        _conversations[chat_id] = []
    _conversations[chat_id].append({"role": role, "content": content})
    # Keep last MAX_HISTORY messages
    if len(_conversations[chat_id]) > MAX_HISTORY:
        _conversations[chat_id] = _conversations[chat_id][-MAX_HISTORY:]


async def handle_message(update: dict) -> str | None:
    """
    Process incoming Telegram update and return reply text.
    Called from webhook endpoint in main.py.
    """
    message = update.get("message")
    if not message:
        return None

    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    user = message.get("from", {})
    username = user.get("first_name", "User")

    if not text:
        return None

    # Handle /start command
    if text.strip() == "/start":
        welcome = (
            f"Hi {username}! 👋\n\n"
            "I'm the <b>SurfIQ Bot</b> — your assistant for water sport school management.\n\n"
            "Ask me about:\n"
            "• Features & modules\n"
            "• Pricing & plans\n"
            "• Live demo\n"
            "• Weather intelligence\n"
            "• AI agents\n"
            "• KiteSafari module\n\n"
            "Or just type your question in any language!\n\n"
            "🌐 <a href='https://surfiq.eu'>surfiq.eu</a> | "
            "🎮 <a href='https://demo.surfiq.eu'>demo.surfiq.eu</a>"
        )
        await send_message(chat_id, welcome)
        return welcome

    # Show typing
    await send_typing(chat_id)

    # Get AI reply
    try:
        from surfiq_chat import get_surfiq_reply

        history = _get_history(chat_id)
        _add_to_history(chat_id, "user", text)

        reply = get_surfiq_reply(text, history)
        _add_to_history(chat_id, "assistant", reply)

        # Send reply (strip HTML tags for Telegram, keep bold)
        reply_tg = reply.replace("<strong>", "<b>").replace("</strong>", "</b>")
        await send_message(chat_id, reply_tg)

        logger.info("Telegram: %s (%d) asked: %s → replied",
                     username, chat_id, text[:50])
        return reply

    except Exception as e:
        logger.error("Telegram AI error: %s", e)
        fallback = "Sorry, I'm having a moment! Please try again or email office@surfiq.eu 😊"
        await send_message(chat_id, fallback)
        return fallback
