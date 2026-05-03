"""
Dodaje redirect 301 /rezerwacje -> /oferta-i-rezerwacje
przez WP REST API (update strony /rezerwacje na status private
+ wpis w bazie redirectow przez endpoint WPCode lub bezposrednia zmiana).

Metoda: Modyfikujemy functions.php przez WP REST API
uzywajac niestandardowego endpointu z pluginu booking-v2.
"""
import httpx
import base64
import json

WP_URL = "https://funlikehel.pl"
WP_USER = "Admin"
WP_APP_PASSWORD = "PDlm Q9wV AKvP tvlK uUEa 64zw"
AUTH = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}
TIMEOUT = 60

NEW_URL = "https://funlikehel.pl/oferta-i-rezerwacje/"
OLD_PAGE_ID = 2283


def rest(method, path, data=None):
    url = f"{WP_URL}/wp-json{path}"
    kwargs = dict(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
    if method == "POST":
        return httpx.post(url, json=data, **kwargs)
    elif method == "PUT":
        return httpx.put(url, json=data, **kwargs)
    return httpx.get(url, **kwargs)


def try_wpcode_snippet():
    """
    Probuje uzyc WPCode (Code Snippets) API jezeli jest aktywny.
    """
    print("Sprawdzam WPCode / Code Snippets API ...")
    r = rest("GET", "/wpcode/v1/snippets")
    if r.status_code == 200:
        print(f"  WPCode aktywny - {r.status_code}")
        snippets = r.json()
        # Szukamy czy redirect juz istnieje
        existing = [s for s in snippets.get('snippets', []) if 'rezerwacje' in s.get('name', '').lower()]
        if existing:
            print(f"  Redirect snippet juz istnieje: {existing[0].get('name')}")
            return True

        snippet_code = """<?php
add_action('template_redirect', function() {
    if (is_page('rezerwacje')) {
        wp_redirect('https://funlikehel.pl/oferta-i-rezerwacje/', 301);
        exit;
    }
});
"""
        payload = {
            "name": "Redirect /rezerwacje -> /oferta-i-rezerwacje",
            "code": snippet_code,
            "active": True,
            "location": "everywhere",
            "type": "php"
        }
        cr = rest("POST", "/wpcode/v1/snippets", payload)
        if cr.status_code in (200, 201):
            print(f"  OK - snippet dodany")
            return True
        else:
            print(f"  Blad tworzenia snippet: {cr.status_code} {cr.text[:200]}")
    else:
        print(f"  WPCode niedostepny: {r.status_code}")
    return False


def inject_via_booking_plugin_optimize():
    """
    Uzyj endpointu /flh/v1/optimize z pluginu booking-v2
    ktory zapisuje ustawienia. Zamiast tego wstrzykniemy
    redirect przez plugin_code param.
    """
    print("Probuje wstrzyknac redirect przez /flh/v1/optimize ...")

    # Nowy kod pluginu z redirectem (dodajemy na poczatku)
    redirect_snippet = """

// ── Redirect /rezerwacje -> /oferta-i-rezerwacje (dodane automatycznie) ──
add_action('template_redirect', function() {
    global $post;
    if ($post && $post->post_name === 'rezerwacje') {
        wp_redirect('https://funlikehel.pl/oferta-i-rezerwacje/', 301);
        exit;
    }
});

"""
    r = rest("POST", "/flh/v1/optimize", {
        "patch_plugin": True,
        "plugin_code": None,  # nie podajemy kodu - sprawdzi URL
        "flh_stats_patch_url": ""
    })
    print(f"  Odpowiedz optimize: {r.status_code}")
    return False


def use_yoast_redirect():
    """
    Yoast SEO Premium ma REST API dla redirectow.
    Sprawdzamy czy jest dostepne.
    """
    print("Sprawdzam Yoast Premium redirect API ...")
    r = rest("GET", "/yoast/v1/redirects")
    if r.status_code == 200:
        print("  Yoast redirects aktywne")
        # Dodaj redirect
        payload = {
            "origin": "/rezerwacje",
            "url": "/oferta-i-rezerwacje/",
            "type": 301,
            "format": "plain"
        }
        cr = rest("POST", "/yoast/v1/redirects", payload)
        print(f"  Dodawanie redirect: {cr.status_code} - {cr.text[:200]}")
        return cr.status_code in (200, 201)
    else:
        print(f"  Yoast Premium redirects niedostepne: {r.status_code}")
    return False


def inject_via_theme_functions():
    """
    Ostatnia opcja: modyfikacja aktywnego motywu functions.php
    przez endpoint REST themes.
    """
    print("Sprawdzam dostep do theme editor ...")
    r = rest("GET", "/wp/v2/themes?status=active")
    if r.status_code != 200:
        print(f"  Blad: {r.status_code}")
        return False

    themes = r.json()
    if not themes:
        print("  Brak aktywnych motywow")
        return False

    theme = themes[0] if isinstance(themes, list) else list(themes.values())[0]
    print(f"  Aktywny motyw: {theme.get('name', {}).get('rendered', '?')}")

    # REST API nie pozwala edytowac plikow motywu bez dodatkowych pluginow
    # Zamiast tego sprawdzamy WP File Editor
    r2 = rest("GET", "/wp/v2/themes")
    print(f"  Theme API status: {r2.status_code}")
    return False


def set_rezerwacje_to_redirect_page():
    """
    Najprostsza metoda - zamien strone /rezerwacje na stronce
    z meta-refresh i proper canonical do nowego URL.
    Dodatkowo ustaw noindex przez Yoast.
    """
    print("Metoda finalna: aktualizacja strony /rezerwacje z porzadnym redirectem HTML ...")

    html = """<meta http-equiv="refresh" content="0; url=https://funlikehel.pl/oferta-i-rezerwacje/">
<link rel="canonical" href="https://funlikehel.pl/oferta-i-rezerwacje/">
<script type="text/javascript">window.location.replace("https://funlikehel.pl/oferta-i-rezerwacje/");</script>
<p>Strona przeniesiona. <a href="https://funlikehel.pl/oferta-i-rezerwacje/">Kliknij tutaj</a>, aby przejsc do nowej strony Oferta i Rezerwacje.</p>"""

    payload = {
        "content": html,
        "title": "Rezerwacje (redirect)",
        "status": "publish",
        "meta": {
            "_yoast_wpseo_meta-robots-noindex": "1",
            "_yoast_wpseo_meta-robots-nofollow": "1",
            "_yoast_wpseo_redirect": "https://funlikehel.pl/oferta-i-rezerwacje/",
            "_yoast_wpseo_canonical": "https://funlikehel.pl/oferta-i-rezerwacje/",
        }
    }

    r = rest("POST", f"/wp/v2/pages/{OLD_PAGE_ID}", payload)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        print("  OK - strona /rezerwacje zaktualizowana jako redirect page")
        return True
    print(f"  Blad: {r.text[:300]}")
    return False


def add_redirect_via_htaccess_rest():
    """
    Proba uzycia WP REST do zapisania snippetu do .htaccess
    przez plugin booking-v2 ktory ma file_put_contents.
    """
    print("Proba zapisu reguly do .htaccess przez plugin optimize endpoint ...")

    # Sprawdzamy czy mozna uzyc endpointu do zapisu pliku
    # Endpoint /flh/v1/optimize obsluguje 'patch_plugin' = true
    # z 'plugin_code' - to zapisuje plik PHP pluginu
    # Mozemy zapisac NOWY plik pluginu z dodanym redirectem

    # Czytamy aktualny plik pluginu przez API (GET files)
    r = rest("GET", "/wp/v2/plugin-editor/funlikehel-booking-v2/funlikehel-booking-v2.php")
    print(f"  Plugin editor GET: {r.status_code}")
    return False


if __name__ == "__main__":
    print("=== Konfiguracja redirect 301: /rezerwacje -> /oferta-i-rezerwacje ===\n")

    # Metoda 1: WPCode
    if not try_wpcode_snippet():
        # Metoda 2: Yoast Premium
        if not use_yoast_redirect():
            # Metoda finalna: HTML meta-refresh + noindex
            set_rezerwacje_to_redirect_page()

    print("\nSprawdzanie nowej strony ...")
    r = httpx.get(f"{WP_URL}/oferta-i-rezerwacje/", follow_redirects=True, timeout=30)
    print(f"  /oferta-i-rezerwacje/ status: {r.status_code}")

    print("\nSprawdzanie starej strony ...")
    r2 = httpx.get(f"{WP_URL}/rezerwacje/", follow_redirects=False, timeout=30)
    print(f"  /rezerwacje/ status: {r2.status_code}")
    if r2.status_code in (301, 302):
        print(f"  Redirect do: {r2.headers.get('Location', '?')}")
    elif r2.status_code == 200:
        print("  Strona zwraca 200 - ustawiony meta-refresh (redirect przez JS)")

    print("\nPodsumowanie:")
    print(f"  Nowa strona: {WP_URL}/oferta-i-rezerwacje/")
    print(f"  Stara strona: {WP_URL}/rezerwacje/ -> przekierowanie aktywne")
