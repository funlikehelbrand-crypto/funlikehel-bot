"""
Deploy funlikehel-booking-v2 plugin na WordPress + shortcode na stronie Egipt.

Kroki:
1. Upload ZIP pluginu
2. Aktywacja pluginu
3. Zapis ustawień (API URL + admin token) przez wp-options endpoint
4. Dodanie shortcode [flh_booking_form location="hurghada"] na stronę /egipt (page 2044)
"""

import httpx
import base64
import os
import json
import time

WP_URL = "https://funlikehel.pl"
WP_USER = "Admin"
WP_APP_PASSWORD = "PDlm Q9wV AKvP tvlK uUEa 64zw"
AUTH = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {AUTH}"}

PLUGIN_ZIP = os.path.join(os.path.dirname(__file__), "server", "wp-plugin", "funlikehel-booking-v2.zip")
PLUGIN_SLUG = "funlikehel-booking-v2/funlikehel-booking-v2"

API_BASE_URL = "https://funlikehel-bot.onrender.com"
BOOKING_ADMIN_TOKEN = "dM9UneILeMs-KBipJbhdlmjH9ACcRcSY5Du4sUTPqng"

EGIPT_PAGE_ID = 2044

SHORTCODE_BLOCK = '\n\n<!-- wp:shortcode -->\n[flh_booking_form location="hurghada"]\n<!-- /wp:shortcode -->'


def step(msg):
    print(f"\n{'='*60}\n{msg}\n{'='*60}")


def upload_plugin():
    step("Krok 1: Upload pluginu")
    with open(PLUGIN_ZIP, "rb") as f:
        zip_data = f.read()
    encoded = base64.b64encode(zip_data).decode()
    resp = httpx.post(
        f"{WP_URL}/wp-json/wp/v2/plugins",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"slug": "funlikehel-booking-v2", "zip": encoded},
        timeout=60,
    )
    if resp.status_code in (201, 200):
        print("✅ Plugin wgrany")
        return True
    elif resp.status_code == 409:
        print("ℹ️  Plugin już istnieje (409) — pomijam upload, aktywuję")
        return True
    else:
        print(f"❌ Upload failed: {resp.status_code} {resp.text[:300]}")
        return False


def activate_plugin():
    step("Krok 2: Aktywacja pluginu")
    resp = httpx.put(
        f"{WP_URL}/wp-json/wp/v2/plugins/{PLUGIN_SLUG}",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"status": "active"},
        timeout=30,
    )
    if resp.status_code in (200, 201):
        print("✅ Plugin aktywowany")
        return True
    else:
        print(f"❌ Aktywacja failed: {resp.status_code} {resp.text[:300]}")
        return False


def save_plugin_settings():
    step("Krok 3: Zapis ustawień pluginu (API URL + token)")
    # WordPress stores plugin options via wp-json/wp/v2/settings
    resp = httpx.post(
        f"{WP_URL}/wp-json/wp/v2/settings",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={
            "flh_api_base_url": API_BASE_URL,
            "flh_booking_admin_token": BOOKING_ADMIN_TOKEN,
        },
        timeout=30,
    )
    if resp.status_code == 200:
        print("✅ Ustawienia zapisane")
        return True
    else:
        # Fallback: use custom endpoint if registered by plugin
        print(f"⚠️  /settings endpoint: {resp.status_code} — próbuję alternatywnie")
        # Try via options API directly
        for key, val in [("flh_api_base_url", API_BASE_URL), ("flh_booking_admin_token", BOOKING_ADMIN_TOKEN)]:
            r = httpx.post(
                f"{WP_URL}/wp-json/flh/v1/option",
                headers={**HEADERS, "Content-Type": "application/json"},
                json={"key": key, "value": val},
                timeout=15,
            )
            print(f"  {key}: {r.status_code}")
        print("ℹ️  Ustaw ręcznie w WP Admin → Rezerwacje jeśli nie zadziałało")
        return True


def add_shortcode_to_page():
    step(f"Krok 4: Shortcode na stronie /egipt (ID: {EGIPT_PAGE_ID})")

    # Get current page content
    resp = httpx.get(
        f"{WP_URL}/wp-json/wp/v2/pages/{EGIPT_PAGE_ID}",
        headers=HEADERS,
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"❌ Nie mogę pobrać strony: {resp.status_code}")
        return False

    page = resp.json()
    current_content = page.get("content", {}).get("raw", "") or page.get("content", {}).get("rendered", "")
    title = page.get("title", {}).get("rendered", "")
    print(f"Strona: '{title}' — {len(current_content)} znaków")

    # Check if shortcode already exists
    if "flh_booking_form" in current_content:
        print("ℹ️  Shortcode już jest na stronie — pomijam")
        return True

    # Append shortcode at end of content
    new_content = current_content + SHORTCODE_BLOCK

    update_resp = httpx.post(
        f"{WP_URL}/wp-json/wp/v2/pages/{EGIPT_PAGE_ID}",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"content": new_content},
        timeout=30,
    )
    if update_resp.status_code == 200:
        print("✅ Shortcode dodany na stronie /egipt")
        return True
    else:
        print(f"❌ Update strony failed: {update_resp.status_code} {update_resp.text[:300]}")
        return False


def verify():
    step("Krok 5: Weryfikacja")
    resp = httpx.get(f"{WP_URL}/wp-json/wp/v2/pages/{EGIPT_PAGE_ID}", headers=HEADERS, timeout=15)
    if resp.status_code == 200:
        content = resp.json().get("content", {}).get("rendered", "")
        if "flh_booking" in content or "flh-booking" in content:
            print("✅ Formularz widoczny na stronie")
        else:
            print("⚠️  Shortcode nie renderuje się — sprawdź czy plugin aktywny")
    print(f"\nStrona: {WP_URL}/egipt")
    print(f"Admin panmel: {WP_URL}/wp-admin/admin.php?page=flh-bookings")


if __name__ == "__main__":
    ok1 = upload_plugin()
    if ok1:
        time.sleep(2)
        ok2 = activate_plugin()
        if ok2:
            time.sleep(1)
            save_plugin_settings()
            time.sleep(1)
            add_shortcode_to_page()
            time.sleep(1)
            verify()
    print("\nDone.")
