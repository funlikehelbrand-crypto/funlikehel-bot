"""
Synchronizacja danych z ekipa z serwera Render do lokalnej bazy ekipa.db.

Uzycie:
    python sync_ekipa.py

Wymaga zmiennej EKIPA_SECRET (domyslnie: flh2024ekipa).
Po redeployu na Render endpoint /api/ekipa/list bedzie dostepny.
"""

import httpx
import sqlite3
import os
import sys

RENDER_URL = "https://funlikehel-bot.onrender.com"
SECRET = os.environ.get("EKIPA_SECRET", "flh2024ekipa")
LOCAL_DB = os.path.join(os.path.dirname(__file__), "ekipa.db")


def init_db(db):
    db.execute("""CREATE TABLE IF NOT EXISTS ekipa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT, phone TEXT, sport TEXT, locations TEXT,
        created_at TEXT
    )""")
    db.commit()


def fetch_remote():
    print(f"Pobieranie danych z {RENDER_URL}/api/ekipa/list ...")
    r = httpx.get(f"{RENDER_URL}/api/ekipa/list", params={"token": SECRET}, timeout=30)
    r.raise_for_status()
    data = r.json()
    print(f"Znaleziono {data['count']} rekordow na Render.")
    return data["items"]


def sync_to_local(items):
    db = sqlite3.connect(LOCAL_DB)
    init_db(db)

    existing_emails = set(
        row[0] for row in db.execute("SELECT email FROM ekipa").fetchall()
    )

    new_count = 0
    for item in items:
        if item["email"] not in existing_emails:
            db.execute(
                "INSERT INTO ekipa (name, email, phone, sport, locations, created_at) VALUES (?,?,?,?,?,?)",
                (item["name"], item["email"], item.get("phone", ""),
                 item.get("sport", ""), item.get("locations", ""), item.get("created_at", "")),
            )
            new_count += 1
            print(f"  [NOWY] {item['name']} | {item['email']} | {item.get('created_at', '')}")
        else:
            print(f"  [juz jest] {item['email']}")

    db.commit()
    db.close()
    print(f"\nDodano {new_count} nowych rekordow do lokalnej bazy.")
    return new_count


def show_all():
    db = sqlite3.connect(LOCAL_DB)
    rows = db.execute("SELECT id, name, email, phone, sport, locations, created_at FROM ekipa ORDER BY created_at DESC").fetchall()
    db.close()
    print(f"\n=== LOKALNA BAZA EKIPA ({len(rows)} rekordow) ===")
    for r in rows:
        print(f"  #{r[0]} [{r[6]}] {r[1]} | {r[2]} | tel:{r[3]} | {r[4]} | {r[5]}")


if __name__ == "__main__":
    try:
        items = fetch_remote()
        sync_to_local(items)
        show_all()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print("\nBLAD: Endpoint /api/ekipa/list nie istnieje na Render.")
            print("-> Wgraj zaktualizowany main.py na Render i sprobuj ponownie.")
        elif e.response.status_code == 403:
            print("\nBLAD: Niepoprawny token. Sprawdz EKIPA_SECRET.")
        else:
            print(f"\nBLAD HTTP {e.response.status_code}: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\nBLAD: {e}")
        sys.exit(1)
