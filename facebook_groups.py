"""
Integracja z grupami Facebook — przeglądanie postów i odpowiadanie jako Alicja.

Wymaga:
- FB_USER_ACCESS_TOKEN — token użytkownika z uprawnieniami publish_to_groups
- FB_GROUP_IDS — lista ID grup (oddzielone przecinkami)
- FB_PAGE_ID — ID strony/profilu bota (żeby pomijać własne posty)
"""

import logging
import os
import sqlite3
from datetime import datetime, timedelta

import httpx

from claude_agent import get_reply

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v21.0"
DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")

# Słowa kluczowe — bot odpowiada tylko na posty/komentarze związane z ofertą
KEYWORDS = [
    "kite", "kitesurfing", "kitesurf", "wind", "windsurfing", "windsurf",
    "wing", "wingfoil", "sup", "pumpfoil", "wakeboard", "wakeboarding",
    "hel", "jastarnia", "chałupy", "puck", "jurata",
    "hurghada", "egipt", "egypt",
    "kurs", "szkoła", "szkola", "lekcja", "nauka",
    "fun like hel", "funlikehel",
    "wypożyczenie", "wypozyczenie", "sprzęt", "sprzet",
    "obóz", "oboz", "kolonie", "camp",
    "cena", "ile kosztuje", "cennik",
]


def _init_db():
    """Tworzy tabelę do śledzenia przetworzonych postów/komentarzy."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fb_processed (
            id         TEXT PRIMARY KEY,
            group_id   TEXT NOT NULL,
            type       TEXT NOT NULL,
            ts         DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


_init_db()


def _is_processed(object_id: str) -> bool:
    """Sprawdza czy post/komentarz był już przetworzony."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT 1 FROM fb_processed WHERE id = ?", (object_id,)
    ).fetchone()
    conn.close()
    return row is not None


def _mark_processed(object_id: str, group_id: str, obj_type: str):
    """Oznacza post/komentarz jako przetworzony."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO fb_processed (id, group_id, type) VALUES (?, ?, ?)",
        (object_id, group_id, obj_type),
    )
    conn.commit()
    conn.close()


def _matches_keywords(text: str) -> bool:
    """Sprawdza czy tekst zawiera słowa kluczowe związane z ofertą."""
    lower = text.lower()
    return any(kw in lower for kw in KEYWORDS)


def _get_config():
    """Pobiera konfigurację z env."""
    token = os.environ.get("FB_USER_ACCESS_TOKEN", "")
    group_ids_raw = os.environ.get("FB_GROUP_IDS", "")
    page_id = os.environ.get("FB_PAGE_ID", "")

    group_ids = [g.strip() for g in group_ids_raw.split(",") if g.strip()]
    return token, group_ids, page_id


# ---------------------------------------------------------------------------
# API Facebook Graph
# ---------------------------------------------------------------------------

def get_group_feed(group_id: str, limit: int = 25) -> list[dict]:
    """
    Pobiera ostatnie posty z grupy.
    Zwraca listę: [{"id", "message", "from_id", "from_name", "created_time"}]
    """
    token, _, _ = _get_config()
    if not token:
        logger.warning("Brak FB_USER_ACCESS_TOKEN — pomijam Facebook Groups.")
        return []

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{GRAPH_API_URL}/{group_id}/feed",
            params={
                "access_token": token,
                "fields": "id,message,from,created_time",
                "limit": limit,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    posts = []
    for item in data.get("data", []):
        message = item.get("message", "")
        if not message:
            continue
        from_info = item.get("from", {})
        posts.append({
            "id": item["id"],
            "message": message,
            "from_id": from_info.get("id", ""),
            "from_name": from_info.get("name", ""),
            "created_time": item.get("created_time", ""),
        })

    return posts


def get_post_comments(post_id: str, limit: int = 50) -> list[dict]:
    """
    Pobiera komentarze pod postem.
    Zwraca listę: [{"id", "message", "from_id", "from_name"}]
    """
    token, _, _ = _get_config()
    if not token:
        return []

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{GRAPH_API_URL}/{post_id}/comments",
            params={
                "access_token": token,
                "fields": "id,message,from",
                "limit": limit,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return [
        {
            "id": c["id"],
            "message": c.get("message", ""),
            "from_id": c.get("from", {}).get("id", ""),
            "from_name": c.get("from", {}).get("name", ""),
        }
        for c in data.get("data", [])
        if c.get("message")
    ]


def post_comment(object_id: str, text: str) -> dict:
    """
    Dodaje komentarz pod postem lub odpowiedź na komentarz w grupie.
    """
    token, _, _ = _get_config()
    if not token:
        raise RuntimeError("Brak FB_USER_ACCESS_TOKEN")

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{GRAPH_API_URL}/{object_id}/comments",
            params={"access_token": token},
            json={"message": text},
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Główna logika — przetwarzanie postów z grup
# ---------------------------------------------------------------------------

def process_facebook_groups():
    """
    Pobiera nowe posty z monitorowanych grup Facebook i odpowiada przez Alicję.
    Wywołanie z polling loop w main.py.
    """
    token, group_ids, page_id = _get_config()

    if not token or not group_ids:
        logger.info("Facebook Groups: brak konfiguracji (FB_USER_ACCESS_TOKEN / FB_GROUP_IDS).")
        return

    total_replied = 0

    for group_id in group_ids:
        try:
            posts = get_group_feed(group_id)
            logger.info("Facebook grupa %s: %d postów do sprawdzenia.", group_id, len(posts))
        except Exception as e:
            logger.error("Błąd pobierania postów z grupy %s: %s", group_id, e)
            continue

        for post in posts:
            # Pomijamy własne posty
            if page_id and post["from_id"] == page_id:
                continue

            # Pomijamy już przetworzone
            if _is_processed(post["id"]):
                continue

            # Oznacz jako przetworzony (nawet jeśli nie pasuje do keywords)
            _mark_processed(post["id"], group_id, "post")

            # Sprawdzamy czy post jest związany z naszą ofertą
            if not _matches_keywords(post["message"]):
                continue

            try:
                prompt = (
                    f"Post w grupie Facebook od {post['from_name']}:\n"
                    f"{post['message']}\n\n"
                    f"Odpowiedz pomocnie jako Alicja z FUN like HEL. "
                    f"Bądź naturalna — to komentarz w grupie, nie reklama."
                )
                reply = get_reply(
                    prompt,
                    sender_id=post["from_id"],
                    channel="facebook_group",
                )
                post_comment(post["id"], reply)
                total_replied += 1
                logger.info(
                    "Facebook: odpowiedź na post %s od %s",
                    post["id"], post["from_name"],
                )
            except Exception as e:
                logger.error("Błąd odpowiedzi na post FB %s: %s", post["id"], e)

        # Sprawdzamy też komentarze pod ostatnimi postami
        for post in posts[:10]:  # tylko 10 najnowszych
            try:
                comments = get_post_comments(post["id"])
            except Exception as e:
                logger.error("Błąd pobierania komentarzy FB %s: %s", post["id"], e)
                continue

            for comment in comments:
                if page_id and comment["from_id"] == page_id:
                    continue
                if _is_processed(comment["id"]):
                    continue

                _mark_processed(comment["id"], group_id, "comment")

                if not _matches_keywords(comment["message"]):
                    continue

                try:
                    prompt = (
                        f"Komentarz w grupie Facebook od {comment['from_name']}:\n"
                        f"{comment['message']}\n\n"
                        f"Odpowiedz pomocnie jako Alicja z FUN like HEL. "
                        f"Bądź naturalna — to komentarz w grupie, nie reklama."
                    )
                    reply = get_reply(
                        prompt,
                        sender_id=comment["from_id"],
                        channel="facebook_group",
                    )
                    post_comment(comment["id"], reply)
                    total_replied += 1
                    logger.info(
                        "Facebook: odpowiedź na komentarz %s od %s",
                        comment["id"], comment["from_name"],
                    )
                except Exception as e:
                    logger.error("Błąd odpowiedzi na komentarz FB %s: %s", comment["id"], e)

    logger.info("Facebook Groups: przetworzono, wysłano %d odpowiedzi.", total_replied)
