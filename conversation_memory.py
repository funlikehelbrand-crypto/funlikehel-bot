"""
Pamięć rozmów Alicji — SQLite, per nadawca, per kanał.
Alicja pamięta historię każdego klienta przez 30 dni.
"""

import os
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")
MAX_HISTORY = 20   # ostatnie N wiadomości na klienta
MAX_AGE_DAYS = 30  # historia starsza niż 30 dni jest ignorowana


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
    """Zapisuje wiadomość do bazy."""
    with _conn() as c:
        c.execute(
            "INSERT INTO conversations (channel, sender_id, role, content) "
            "VALUES (?, ?, ?, ?)",
            (channel, sender_id, role, content),
        )


def get_history(channel: str, sender_id: str) -> list[dict]:
    """
    Zwraca historię rozmowy z danym nadawcą (maks. MAX_HISTORY wiadomości,
    nie starszych niż MAX_AGE_DAYS dni), w kolejności chronologicznej.
    """
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
    """Czyści historię konkretnego nadawcy (np. na życzenie klienta)."""
    with _conn() as c:
        c.execute(
            "DELETE FROM conversations WHERE channel = ? AND sender_id = ?",
            (channel, sender_id),
        )
