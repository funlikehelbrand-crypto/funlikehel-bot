#!/usr/bin/env python3
"""
Wstawia sekcje TripAdvisor na homepage WordPress (ID 1329)
PRZED ostatnim blokiem CTA (kemping2 cover).
"""
import json
import requests
import sys

WP_API = "https://www.funlikehel.pl/wp-json/wp/v2/pages/1329"
WP_AUTH = ("Admin", "PDlm Q9wV AKvP tvlK uUEa 64zw")

# --- 1. Wczytaj aktualny content ---
print("Pobieranie aktualnej treści strony...")
r = requests.get(WP_API, params={"_fields": "id,content"}, auth=WP_AUTH, timeout=30)
r.raise_for_status()
data = r.json()
current_html = data["content"]["rendered"]
print(f"Pobrano {len(current_html)} znaków HTML")

# --- 2. Sprawdź czy sekcja już istnieje ---
if "fhl-ta-section" in current_html:
    print("UWAGA: Sekcja TripAdvisor (fhl-ta-section) juz istnieje na stronie!")
    print("Przerywam — uzyj flagi --force zeby nadpisac.")
    sys.exit(0)

# --- 3. Wczytaj nowy blok ---
with open("C:/Users/ŁukaszMichalina/funlikehel/tripadvisor_block.html", "r", encoding="utf-8") as f:
    ta_block = f.read().strip()

# --- 4. Znajdz miejsce wstawienia (przed ostatnim CTA) ---
CTA_MARKER = '<div class="wp-block-cover alignfull" style="min-height:400px'
idx = current_html.find(CTA_MARKER)
if idx == -1:
    print("BLAD: Nie znaleziono markera CTA! Sprawdz HTML strony.")
    sys.exit(1)
print(f"Znaleziono marker CTA na pozycji {idx}")

# --- 5. Wstaw blok przed CTA ---
new_html = current_html[:idx] + "\n\n" + ta_block + "\n\n" + current_html[idx:]
print(f"Nowa dlugosc HTML: {len(new_html)} znaków")

# --- 6. Wyslij przez REST API ---
print("Wysylanie do WordPress...")
resp = requests.post(
    WP_API,
    auth=WP_AUTH,
    headers={"Content-Type": "application/json"},
    data=json.dumps({"content": new_html}),
    timeout=60
)
print(f"HTTP {resp.status_code}")
if resp.status_code in (200, 201):
    rd = resp.json()
    print("OK! Strona zaktualizowana.")
    print("Link:", rd.get("link", ""))
    print("Modified:", rd.get("modified", ""))
else:
    print("BLAD odpowiedzi:")
    print(resp.text[:1000])
    sys.exit(1)
