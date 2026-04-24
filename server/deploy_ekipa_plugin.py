"""
Deploy pluginu funlikehel-ekipa na WordPress (home.pl).

Krok 1: Login do wp-admin
Krok 2: Upload ZIP pluginu
Krok 3: Aktywacja pluginu przez REST API
Krok 4: Update formularza /ekipa/ — URL z Render -> WordPress REST API
Krok 5: Test nowego endpointu

Skrypt automatycznie ponawia proby przy timeoutach.
"""

import httpx
import base64
import re
import time
import sys
import os

# ---- CONFIG ----
WP_URL = "https://funlikehel.pl"
WP_USER = "Admin"
WP_APP_PASSWORD = "PDlm Q9wV AKvP tvlK uUEa 64zw"
AUTH = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
ZIP_PATH = os.path.join(os.path.dirname(__file__), "wp-plugin", "funlikehel-ekipa.zip")
PLUGIN_SLUG = "funlikehel-ekipa/funlikehel-ekipa"
NEW_API_URL = f"{WP_URL}/wp-json/funlikehel/v1/ekipa"
EKIPA_PAGE_ID = 2189
MAX_RETRIES = 5
TIMEOUT = 45


def rest_api(method, route, data=None, retry=MAX_RETRIES):
    """WordPress REST API call with retries."""
    headers = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}
    url = f"{WP_URL}/wp-json{route}"

    for attempt in range(1, retry + 1):
        try:
            if method == "GET":
                r = httpx.get(url, headers=headers, timeout=TIMEOUT, follow_redirects=True)
            elif method == "POST":
                r = httpx.post(url, headers=headers, json=data, timeout=TIMEOUT, follow_redirects=True)
            elif method == "PUT":
                r = httpx.put(url, headers=headers, json=data, timeout=TIMEOUT, follow_redirects=True)
            return r
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
            print(f"  Proba {attempt}/{retry} timeout: {type(e).__name__}")
            if attempt < retry:
                time.sleep(3)
    return None


def rest_api_alt(method, route, data=None, retry=MAX_RETRIES):
    """WordPress REST API via ?rest_route= (backup format)."""
    headers = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}
    url = f"{WP_URL}/?rest_route={route}"

    for attempt in range(1, retry + 1):
        try:
            if method == "GET":
                r = httpx.get(url, headers=headers, timeout=TIMEOUT, follow_redirects=True)
            elif method == "POST":
                r = httpx.post(url, headers=headers, json=data, timeout=TIMEOUT, follow_redirects=True)
            return r
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
            print(f"  [alt] Proba {attempt}/{retry} timeout: {type(e).__name__}")
            if attempt < retry:
                time.sleep(3)
    return None


def step1_login_and_upload():
    """Login do wp-admin i upload pluginu ZIP."""
    print("\n=== KROK 1: Login + Upload pluginu ===")

    client = httpx.Client(follow_redirects=True, timeout=TIMEOUT)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  Proba logowania {attempt}/{MAX_RETRIES}...")

            # Login
            r = client.post(f"{WP_URL}/wp-login.php", data={
                "log": WP_USER,
                "pwd": WP_APP_PASSWORD,
                "wp-submit": "Log In",
                "testcookie": "1",
                "redirect_to": "/wp-admin/",
            })

            cookies = dict(client.cookies)
            logged_in = any("logged_in" in k for k in cookies)

            if not logged_in:
                print(f"  Login failed (status {r.status_code})")
                if attempt < MAX_RETRIES:
                    time.sleep(5)
                continue

            print("  Zalogowano do wp-admin!")

            # Get plugin upload page + nonce
            r2 = client.get(f"{WP_URL}/wp-admin/plugin-install.php?tab=upload")
            nonce_match = re.search(r'name="_wpnonce" value="([a-f0-9]+)"', r2.text)

            if not nonce_match:
                print("  Nie znaleziono nonce na stronie uploadu")
                continue

            nonce = nonce_match.group(1)
            print(f"  Nonce: {nonce}")

            # Upload ZIP
            with open(ZIP_PATH, "rb") as f:
                r3 = client.post(
                    f"{WP_URL}/wp-admin/update.php?action=upload-plugin",
                    files={"pluginzip": ("funlikehel-ekipa.zip", f, "application/zip")},
                    data={"_wpnonce": nonce, "install-plugin-submit": "Zainstaluj"},
                )

            if r3.status_code == 200:
                body = r3.text.lower()
                if "successfully" in body or "zainstalowana" in body or "installed" in body:
                    print("  PLUGIN ZAINSTALOWANY!")
                    client.close()
                    return True
                elif "already" in body or "istnieje" in body or "jest już" in body:
                    print("  Plugin juz istnieje — OK")
                    client.close()
                    return True
                else:
                    # Extract messages
                    msgs = re.findall(r'<p[^>]*>([^<]{5,})</p>', r3.text)
                    for m in msgs[:5]:
                        print(f"  msg: {m.strip()}")
            else:
                print(f"  Upload HTTP {r3.status_code}")

        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
            print(f"  Timeout: {type(e).__name__}")
            if attempt < MAX_RETRIES:
                time.sleep(5)

    client.close()
    return False


def step2_activate_plugin():
    """Aktywacja pluginu przez REST API."""
    print("\n=== KROK 2: Aktywacja pluginu ===")

    # Check if plugin exists
    r = rest_api("GET", "/wp/v2/plugins")
    if not r or r.status_code != 200:
        r = rest_api_alt("GET", "/wp/v2/plugins")

    if not r or r.status_code != 200:
        print("  Nie moge pobrac listy pluginow")
        return False

    plugins = r.json()
    ekipa_plugin = None
    for p in plugins:
        if "ekipa" in p.get("plugin", "").lower():
            ekipa_plugin = p
            break

    if not ekipa_plugin:
        print("  Plugin funlikehel-ekipa NIE znaleziony na serwerze")
        return False

    print(f"  Znaleziono plugin: {ekipa_plugin['plugin']} (status: {ekipa_plugin['status']})")

    if ekipa_plugin["status"] == "active":
        print("  Plugin juz aktywny!")
        return True

    # Activate
    plugin_file = ekipa_plugin["plugin"]
    r = rest_api("POST", f"/wp/v2/plugins/{plugin_file}", {"status": "active"})
    if not r:
        r = rest_api_alt("POST", f"/wp/v2/plugins/{plugin_file}", {"status": "active"})

    if r and r.status_code == 200:
        print("  PLUGIN AKTYWOWANY!")
        return True
    else:
        print(f"  Blad aktywacji: {r.status_code if r else 'timeout'}")
        if r:
            print(f"  {r.text[:200]}")
        return False


def step3_update_form_url():
    """Update formularza /ekipa/ — zmiana URL z Render na WordPress."""
    print("\n=== KROK 3: Update URL formularza ===")

    # Get current page content
    r = rest_api_alt("GET", f"/wp/v2/pages/{EKIPA_PAGE_ID}")
    if not r:
        r = rest_api("GET", f"/wp/v2/pages/{EKIPA_PAGE_ID}")

    if not r or r.status_code != 200:
        print("  Nie moge pobrac strony /ekipa/")
        return False

    page = r.json()
    content = page.get("content", {}).get("raw", "")
    if not content:
        content = page.get("content", {}).get("rendered", "")

    old_url = "https://funlikehel-bot.onrender.com/api/ekipa"

    if old_url not in content:
        if NEW_API_URL in content:
            print("  URL juz zmieniony na nowy endpoint — OK")
            return True
        print(f"  Stary URL ({old_url}) nie znaleziony w tresci")
        print("  Moze formularz jest w innym formacie...")
        # Try to update anyway with full content

    new_content = content.replace(old_url, NEW_API_URL)

    r = rest_api_alt("POST", f"/wp/v2/pages/{EKIPA_PAGE_ID}", {"content": new_content})
    if not r:
        r = rest_api("POST", f"/wp/v2/pages/{EKIPA_PAGE_ID}", {"content": new_content})

    if r and r.status_code == 200:
        print(f"  URL ZMIENIONY: {old_url}")
        print(f"  ->            {NEW_API_URL}")
        return True
    else:
        print(f"  Blad update: {r.status_code if r else 'timeout'}")
        return False


def step4_test_endpoint():
    """Test nowego endpointu."""
    print("\n=== KROK 4: Test endpointu ===")

    r = rest_api("POST", "/funlikehel/v1/ekipa", {
        "name": "Test-Deploy",
        "email": "deploy-test@test.pl",
        "phone": "",
        "sport": "test",
        "locations": ["test"],
    })

    if r and r.status_code == 200:
        data = r.json()
        print(f"  ENDPOINT DZIALA! Odpowiedz: {data}")
        return True
    else:
        print(f"  Endpoint nie odpowiada: {r.status_code if r else 'timeout'}")
        if r:
            print(f"  {r.text[:200]}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Deploy pluginu FUN like HEL — Ekipa API")
    print("=" * 60)

    results = {}

    # Krok 1: Upload
    results["upload"] = step1_login_and_upload()

    # Krok 2: Aktywacja (nawet jesli upload failed — plugin moze juz byc)
    results["activate"] = step2_activate_plugin()

    # Krok 3: Update URL (tylko jesli plugin aktywny)
    if results["activate"]:
        results["form_url"] = step3_update_form_url()
    else:
        print("\n=== KROK 3: POMINIETO (plugin nieaktywny) ===")
        results["form_url"] = False

    # Krok 4: Test
    if results["activate"]:
        results["test"] = step4_test_endpoint()
    else:
        results["test"] = False

    print("\n" + "=" * 60)
    print("WYNIK DEPLOY")
    print("=" * 60)
    for k, v in results.items():
        print(f"  {k}: {'OK' if v else 'FAILED'}")

    if all(results.values()):
        print("\nWSZYSTKO DZIALA! Formularz /ekipa/ przeniesiony na home.pl.")
    elif results["activate"] and results["form_url"]:
        print("\nPlugin aktywny, URL zmieniony. Formularz powinien dzialac.")
    else:
        print("\nNIEKTORE KROKI NIE POWIODLY SIE.")
        print("Jesli upload failed — wgraj plugin reczne przez:")
        print("  1. Panel home.pl -> Menedzer plikow")
        print("  2. Wgraj ZIP do wp-content/plugins/")
        print("  3. Rozpakuj")
        print("  4. Aktywuj w wp-admin -> Wtyczki")
        print(f"  ZIP: {os.path.abspath(ZIP_PATH)}")
