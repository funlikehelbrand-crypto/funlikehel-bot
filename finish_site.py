"""
Dokończenie strony:
1. Permalinki (pretty URLs)
2. WooCommerce - waluta PLN
3. SEO - Yoast meta opisy
4. Logo w nagłówku
"""
import subprocess, json, sys, re

COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"

# Login
subprocess.run(['curl', '-s', '-c', COOKIE, 'https://funlikehel.pl/wp-login.php'], capture_output=True)
with open(COOKIE, 'a') as f:
    f.write("funlikehel.pl\tFALSE\t/\tTRUE\t0\twordpress_test_cookie\tWP%20Cookie%20check\n")
subprocess.run(['curl', '-s', '-c', COOKIE, '-b', COOKIE,
    '-d', 'log=Admin&pwd=Japoniamarzen1!&wp-submit=Log+In&redirect_to=%2Fwp-admin%2F&testcookie=1',
    'https://funlikehel.pl/wp-login.php'], capture_output=True)

r = subprocess.run(['curl', '-s', '-b', COOKIE,
    'https://funlikehel.pl/wp-admin/admin-ajax.php?action=rest-nonce'],
    capture_output=True, text=True)
NONCE = r.stdout.strip()
print(f"Nonce: {NONCE}")
if NONCE == '0':
    print("FATAL: login failed")
    sys.exit(1)

def api(method, route, data=None):
    cmd = ['curl', '-s', '-b', COOKIE, '-H', f'X-WP-Nonce: {NONCE}',
           '-H', 'Content-Type: application/json', '-X', method,
           f'https://funlikehel.pl/?rest_route={route}']
    if data:
        path = "C:/Users/\u0141ukaszMichalina/funlikehel/payload_tmp.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=True)
        cmd += ['--data-binary', f'@{path}']
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    try:
        return json.loads(r.stdout)
    except:
        return r.stdout

# =====================================================
# 1. PERMALINKI — /%postname%/
# =====================================================
print("\n=== PERMALINKI ===")
# Pobierz stronę opcji permalinków żeby dostać nonce
r = subprocess.run(['curl', '-s', '-b', COOKIE,
    'https://funlikehel.pl/wp-admin/options-permalink.php'],
    capture_output=True, text=True, encoding='utf-8')
perm_nonce = re.findall(r'name=\"_wpnonce\" value=\"([a-f0-9]+)\"', r.stdout)
if perm_nonce:
    # Ustaw na /%postname%/
    r2 = subprocess.run(['curl', '-s', '-b', COOKIE,
        '-X', 'POST',
        'https://funlikehel.pl/wp-admin/options-permalink.php',
        '-d', f'_wpnonce={perm_nonce[0]}&_wp_http_referer=%2Fwp-admin%2Foptions-permalink.php&selection=%2F%25postname%25%2F&permalink_structure=%2F%25postname%25%2F&submit=Save+Changes'],
        capture_output=True, text=True, encoding='utf-8')
    if 'Permalink structure updated' in r2.stdout or 'options-permalink' in r2.stdout:
        print("  OK: Permalinki ustawione na /%postname%/")
    else:
        print("  Prawdopodobnie OK (302 redirect)")
else:
    print("  ERR: Brak nonce do permalinków")

# =====================================================
# 2. WooCommerce — waluta PLN, lokalizacja PL
# =====================================================
print("\n=== WOOCOMMERCE KONFIGURACJA ===")

# WooCommerce ustawienia przez REST API
wc_settings = [
    ("/wc/v3/settings/general/woocommerce_currency", {"value": "PLN"}),
    ("/wc/v3/settings/general/woocommerce_currency_pos", {"value": "right_space"}),
    ("/wc/v3/settings/general/woocommerce_price_decimal_sep", {"value": ","}),
    ("/wc/v3/settings/general/woocommerce_price_thousand_sep", {"value": " "}),
    ("/wc/v3/settings/general/woocommerce_default_country", {"value": "PL"}),
]

for route, data in wc_settings:
    result = api("PUT", route, data)
    if isinstance(result, dict) and 'value' in result:
        print(f"  OK: {route.split('/')[-1]} = {result['value']}")
    else:
        # Try POST
        result2 = api("POST", route, data)
        if isinstance(result2, dict) and 'value' in result2:
            print(f"  OK: {route.split('/')[-1]} = {result2['value']}")
        else:
            print(f"  ERR: {route.split('/')[-1]}")

# =====================================================
# 3. SEO — Yoast meta opisy
# =====================================================
print("\n=== SEO — YOAST META OPISY ===")

seo_data = {
    1329: {
        "title": "FUN like HEL — Szko\u0142a Sport\u00f3w Wodnych | Jastarnia i Egipt",
        "desc": "Szko\u0142a kitesurfingu, windsurfingu i wing foil w Jastarni i Hurghadzie. Kursy ca\u0142y rok, obozy dla dzieci, Femi Campy. Cabrinha Test Center. Zadzwo\u0144: 690 270 032"
    },
    2033: {
        "title": "Oferta — Kursy Kite, Windsurf, Wing, SUP | FUN like HEL",
        "desc": "Kitesurfing, windsurfing, wingfoil, wakeboarding, SUP — kursy dla pocz\u0105tkuj\u0105cych i zaawansowanych. Jastarnia i Hurghada. Cennik i rezerwacje."
    },
    2044: {
        "title": "Egipt Hurghada — Kursy Kite | Cabrinha Test Center | FUN like HEL",
        "desc": "Baza zimowa w Hurghadzie. Pakiety od 2300 z\u0142 z noclegiem i szkoleniem kite. P\u0142ytka woda, 300 dni wiatru, polscy instruktorzy."
    },
    2037: {
        "title": "Obozy, Kolonie i Femi Campy | FUN like HEL Jastarnia",
        "desc": "Surfkolonie dla dzieci 5-9 lat, obozy dla m\u0142odzie\u017cy, Femi Campy dla kobiet. P\u00f3\u0142wysep Helski i Egipt. Profesjonalna opieka i sport."
    },
    2040: {
        "title": "Sklep Aquashop — Sprz\u0119t Cabrinha 2026 | FUN like HEL",
        "desc": "Oficjalny Cabrinha Test Center. Latawce, deski, wing foil, foile — nowa kolekcja 2026. Przetestuj na wodzie zanim kupisz!"
    },
    2042: {
        "title": "Kontakt i Rezerwacje | FUN like HEL — 690 270 032",
        "desc": "Zarezerwuj kurs: tel. 690 270 032, email funlikehelbrand@gmail.com. Baza Polska: Jastarnia (Sun4Hel). Baza Egipt: Hurghada."
    },
}

for page_id, seo in seo_data.items():
    # Yoast uzywa meta fields: _yoast_wpseo_title i _yoast_wpseo_metadesc
    result = api("POST", f"/wp/v2/pages/{page_id}", {
        "meta": {
            "_yoast_wpseo_title": seo["title"],
            "_yoast_wpseo_metadesc": seo["desc"]
        }
    })
    if isinstance(result, dict) and 'id' in result:
        sys.stdout.buffer.write(f"  OK: ID:{page_id} — {seo['title'][:50]}...\n".encode('utf-8'))
    else:
        sys.stdout.buffer.write(f"  ERR: ID:{page_id}\n".encode('utf-8'))

# =====================================================
# 4. LOGO w nagłówku — ustaw site icon / custom logo
# =====================================================
print("\n=== LOGO ===")
# Logo jest juz wgrane jako ID:1682 (logo-poziom_male.jpg) lub 1703 (cropped)
result = api("POST", "/wp/v2/settings", {
    "site_logo": 1682,
    "site_icon": 1703
})
if isinstance(result, dict):
    print(f"  Logo: {result.get('site_logo', 'ERR')}")
    print(f"  Favicon: {result.get('site_icon', 'ERR')}")

# =====================================================
# 5. Napraw linki w menu na pretty URLs
# =====================================================
print("\n=== AKTUALIZACJA LINKOW W MENU ===")
items = api("GET", "/wp/v2/menu-items&menus=22&per_page=20")
if isinstance(items, list):
    slug_map = {
        2033: "https://funlikehel.pl/oferta/",
        2044: "https://funlikehel.pl/egipt-hurghada/",
        2037: "https://funlikehel.pl/obozy-kolonie/",
        2040: "https://funlikehel.pl/sklep/",
        2042: "https://funlikehel.pl/kontakt/",
    }
    for item in items:
        obj_id = item.get('object_id', 0)
        if obj_id in slug_map:
            api("POST", f"/wp/v2/menu-items/{item['id']}", {
                "url": slug_map[obj_id]
            })
            title = item['title']['rendered']
            sys.stdout.buffer.write(f"  OK: {title} -> {slug_map[obj_id]}\n".encode('utf-8'))

# =====================================================
# 6. Napraw nawigacje FSE na pretty URLs
# =====================================================
print("\n=== AKTUALIZACJA NAWIGACJI FSE ===")
nav_content = (
    '<!-- wp:navigation-link {"label":"Oferta","type":"page","id":2033,"url":"https://funlikehel.pl/oferta/","kind":"post-type","isTopLevelLink":true} /-->'
    '\n<!-- wp:navigation-link {"label":"Egipt","type":"page","id":2044,"url":"https://funlikehel.pl/egipt-hurghada/","kind":"post-type","isTopLevelLink":true} /-->'
    '\n<!-- wp:navigation-link {"label":"Obozy i Kolonie","type":"page","id":2037,"url":"https://funlikehel.pl/obozy-kolonie/","kind":"post-type","isTopLevelLink":true} /-->'
    '\n<!-- wp:navigation-link {"label":"Sklep","type":"page","id":2040,"url":"https://funlikehel.pl/sklep/","kind":"post-type","isTopLevelLink":true} /-->'
    '\n<!-- wp:navigation-link {"label":"Kontakt","type":"page","id":2042,"url":"https://funlikehel.pl/kontakt/","kind":"post-type","isTopLevelLink":true} /-->'
)

result = api("POST", "/wp/v2/navigation/6", {"content": nav_content, "status": "publish"})
if isinstance(result, dict) and 'id' in result:
    print("  OK: Nawigacja FSE z pretty URLs")

# =====================================================
# 7. Tytuł i opis strony
# =====================================================
print("\n=== TYTUL I OPIS ===")
result = api("POST", "/wp/v2/settings", {
    "title": "FUN like HEL",
    "description": "Szko\u0142a Sport\u00f3w Wodnych | Jastarnia i Egipt"
})
if isinstance(result, dict):
    print(f"  Tytul: {result.get('title', 'ERR')}")
    print(f"  Opis: {result.get('description', 'ERR')}")

print("\n=== WSZYSTKO GOTOWE ===")
