"""
Pamięć rozmów Alicji — Firestore (Cloud Run) lub SQLite (lokalny dev).
Alicja pamięta historię każdego klienta przez 30 dni.
"""

import os
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

MAX_HISTORY = 20   # ostatnie N wiadomości na klienta
MAX_AGE_DAYS = 30  # historia starsza niż 30 dni jest ignorowana

# Cloud Run ustawia automatycznie GOOGLE_CLOUD_PROJECT
USE_FIRESTORE = bool(os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("USE_FIRESTORE"))


if USE_FIRESTORE:
    from google.cloud import firestore as _fs
    _db = _fs.Client()

    def save_message(channel: str, sender_id: str, role: str, content: str):
        doc_ref = _db.collection("conversations").document(f"{channel}_{sender_id}")
        doc = doc_ref.get()
        messages = doc.to_dict().get("messages", []) if doc.exists else []
        messages.append({
            "role": role,
            "content": content,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        messages = messages[-MAX_HISTORY:]
        doc_ref.set({"messages": messages, "updated_at": _fs.SERVER_TIMESTAMP})

    def get_history(channel: str, sender_id: str) -> list[dict]:
        doc = _db.collection("conversations").document(f"{channel}_{sender_id}").get()
        if not doc.exists:
            return []
        messages = doc.to_dict().get("messages", [])
        cutoff = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)).isoformat()
        recent = [m for m in messages if m.get("ts", "") > cutoff]
        return [{"role": m["role"], "content": m["content"]} for m in recent[-MAX_HISTORY:]]

    def clear_history(channel: str, sender_id: str):
        _db.collection("conversations").document(f"{channel}_{sender_id}").delete()

else:
    import sqlite3

    DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")

    def _conn():
        c = sqlite3.connect(DB_PATH)
        c.row_factory = sqlite3.Row
        return c

    def _init():
        with _conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel   TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    role      TEXT NOT NULL,
                    content   TEXT NOT NULL,
                    ts        DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_sender "
                "ON conversations(channel, sender_id, ts)"
            )

    _init()

    def save_message(channel: str, sender_id: str, role: str, content: str):
        with _conn() as c:
            c.execute(
                "INSERT INTO conversations (channel, sender_id, role, content) "
                "VALUES (?, ?, ?, ?)",
                (channel, sender_id, role, content),
            )

    def get_history(channel: str, sender_id: str) -> list[dict]:
        cutoff = (datetime.utcnow() - timedelta(days=MAX_AGE_DAYS)).isoformat()
        with _conn() as c:
            rows = c.execute(
                """
                SELECT role, content FROM conversations
                WHERE channel = ? AND sender_id = ? AND ts > ?
                ORDER BY ts DESC LIMIT ?
                """,
                (channel, sender_id, cutoff, MAX_HISTORY),
            ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def clear_history(channel: str, sender_id: str):
        with _conn() as c:
            c.execute(
                "DELETE FROM conversations WHERE channel = ? AND sender_id = ?",
                (channel, sender_id),
            )
