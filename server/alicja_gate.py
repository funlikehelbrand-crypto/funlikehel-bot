"""
Alicja Gate — checks if auto-reply is enabled for a channel.
If Alicja agent is OFF or channel is disabled → message saved but NO auto-reply.
Staff replies manually from panel.
"""

import os
import logging
import requests as _req

logger = logging.getLogger(__name__)

_SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://pmkzzchckmpcmvtdhxwh.supabase.co")
_SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# Cache — refresh every 5 min
_cache = {}
_cache_ts = 0


def _fetch_config():
    """Fetch Alicja agent config from Supabase."""
    global _cache, _cache_ts
    import time
    now = time.time()
    if now - _cache_ts < 300 and _cache:  # 5 min cache
        return _cache

    if not _SUPABASE_KEY:
        return {"enabled": True, "channels": {}}  # fallback: allow all

    try:
        h = {"apikey": _SUPABASE_KEY, "Authorization": f"Bearer {_SUPABASE_KEY}", "Prefer": "return=representation"}
        r = _req.get(f"{_SUPABASE_URL}/rest/v1/agent_configs?agent_type=eq.alicja_bot&limit=1", headers=h, timeout=5)
        if r.status_code == 200 and r.json():
            agent = r.json()[0]
            import json
            channels = {}
            if agent.get("config"):
                cfg = agent["config"] if isinstance(agent["config"], dict) else json.loads(agent["config"])
                channels = cfg.get("channels", {})
            _cache = {
                "enabled": agent.get("is_enabled", False),
                "mode": agent.get("mode", "off"),
                "channels": channels,
            }
            _cache_ts = now
            return _cache
    except Exception as e:
        logger.warning("Alicja gate fetch error: %s", e)

    return {"enabled": False, "channels": {}}


def should_auto_reply(channel: str) -> bool:
    """
    Check if Alicja should auto-reply on this channel.

    channel: 'email', 'instagram_dm', 'instagram_comments', 'messenger',
             'whatsapp', 'youtube', 'google_reviews'

    Returns True if auto-reply enabled, False if staff should handle manually.
    """
    config = _fetch_config()

    # Agent globally disabled
    if not config.get("enabled"):
        return False

    # Mode check
    mode = config.get("mode", "off")
    if mode == "off":
        return False

    # Channel-specific check
    channels = config.get("channels", {})
    return channels.get(channel, False)


def clear_cache():
    """Force refresh config on next check."""
    global _cache_ts
    _cache_ts = 0
