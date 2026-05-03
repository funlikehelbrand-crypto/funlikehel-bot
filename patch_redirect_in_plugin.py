"""
Dodaje redirect 301 /rezerwacje -> /oferta-i-rezerwacje
bezposrednio do pluginu funlikehel-booking-v2.php
przez endpoint /flh/v1/optimize z plugin_code.

Czyta aktualny kod pluginu, dodaje hook, wgrywa nowy kod.
"""
import httpx
import base64
import os

WP_URL = "https://funlikehel.pl"
WP_USER = "Admin"
WP_APP_PASSWORD = "PDlm Q9wV AKvP tvlK uUEa 64zw"
AUTH = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}
TIMEOUT = 60

REDIRECT_HOOK = """

// ── Auto-redirect: /rezerwacje -> /oferta-i-rezerwacje (301) ──────────────
add_action( 'template_redirect', 'flhv2_page_redirects' );
function flhv2_page_redirects() {
    global $post;
    if ( ! $post ) return;
    if ( $post->post_name === 'rezerwacje' ) {
        wp_redirect( home_url( '/oferta-i-rezerwacje/' ), 301 );
        exit;
    }
}
"""

# Aktualny plik pluginu
local_plugin_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server", "wp-plugin", "funlikehel-booking-v2.php")


def get_current_plugin_code():
    with open(local_plugin_path, "r", encoding="utf-8") as f:
        return f.read()


def patch_and_upload():
    code = get_current_plugin_code()

    # Sprawdz czy redirect juz jest
    if "flhv2_page_redirects" in code:
        print("Redirect hook juz istnieje w pliku pluginu!")
        return True

    # Wstaw redirect na koniec pliku (przed ostatnia linijka jezeli jest ?>)
    if code.rstrip().endswith("?>"):
        new_code = code.rstrip()[:-2] + REDIRECT_HOOK + "\n?>"
    else:
        new_code = code + REDIRECT_HOOK

    print(f"Nowy kod: {len(new_code)} znakow (bylo {len(code)})")

    # Wyslij przez endpoint /flh/v1/optimize
    print("Wgrywanie nowego kodu pluginu przez /flh/v1/optimize ...")
    r = httpx.post(
        f"{WP_URL}/wp-json/flh/v1/optimize",
        headers=HEADERS,
        json={
            "patch_plugin": True,
            "plugin_code": new_code,
        },
        timeout=60,
        follow_redirects=True,
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        resp = r.json()
        print(f"Odpowiedz: {resp}")
        if "patched" in str(resp.get("patch_plugin", "")):
            print("OK - plugin zaktualizowany z redirectem 301!")
            # Zapisz tez lokalnie
            with open(local_plugin_path, "w", encoding="utf-8") as f:
                f.write(new_code)
            print("Zapisano lokalnie.")
            return True
        else:
            print(f"Blad patchowania: {resp.get('patch_plugin')}")
    else:
        print(f"Blad HTTP: {r.text[:300]}")
    return False


def verify_redirect():
    print("\nWeryfikacja redirect ...")
    r = httpx.get(
        f"{WP_URL}/rezerwacje/",
        follow_redirects=False,
        timeout=30,
    )
    print(f"  GET /rezerwacje/ -> {r.status_code}")
    if r.status_code == 301:
        loc = r.headers.get("location", "?")
        print(f"  Location: {loc}")
        if "oferta-i-rezerwacje" in loc:
            print("  SUKCES - redirect 301 dziala poprawnie!")
        else:
            print(f"  Redirect do nieoczekiwanego URL: {loc}")
    elif r.status_code == 200:
        body = r.text[:200].lower()
        if "oferta-i-rezerwacje" in body or "meta http-equiv" in body:
            print("  Meta-refresh aktywny (serwer zwraca 200 + JS redirect)")
        else:
            print("  Strona zwraca 200 bez redirectu - sprawdz recznie")


if __name__ == "__main__":
    ok = patch_and_upload()
    verify_redirect()

    if not ok:
        print("\nAlternatywnie: dodaj recznie nastepujacy kod do functions.php motywu:")
        print(REDIRECT_HOOK)
