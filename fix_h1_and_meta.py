"""
Skrypt naprawczy:
1. Aktualizuje meta descriptions (Yoast SEO) z polskimi znakami
2. Naprawia podwojny H1 na stronie glownej (zmienia H1 w tresci na H2)
"""
import subprocess, json, sys, urllib.parse, re, time

COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"

def login():
    subprocess.run(['curl', '-s', '--max-time', '15', '-c', COOKIE,
        'https://funlikehel.pl/wp-login.php'], capture_output=True)
    with open(COOKIE, 'a') as f:
        f.write("funlikehel.pl\tFALSE\t/\tTRUE\t0\twordpress_test_cookie\tWP%20Cookie%20check\n")
    subprocess.run(['curl', '-s', '--max-time', '15', '-c', COOKIE, '-b', COOKIE,
        '-d', 'log=Admin&pwd=Japoniamarzen1!&wp-submit=Log+In&redirect_to=%2Fwp-admin%2F&testcookie=1',
        'https://funlikehel.pl/wp-login.php'], capture_output=True)

def get_rest_nonce():
    r = subprocess.run(['curl', '-s', '--max-time', '15', '-b', COOKIE,
        'https://funlikehel.pl/wp-admin/admin-ajax.php?action=rest-nonce'],
        capture_output=True, text=True)
    return r.stdout.strip()

def get_edit_nonces(post_id):
    r = subprocess.run(['curl', '-s', '--max-time', '30', '-b', COOKIE,
        f'https://funlikehel.pl/wp-admin/post.php?post={post_id}&action=edit'],
        capture_output=True, text=True, encoding='utf-8')
    html = r.stdout
    m = re.search(r'id="_wpnonce" name="_wpnonce" value="([^"]+)"', html)
    wp_nonce = m.group(1) if m else None
    m = re.search(r'yoast_free_metabox_nonce" value="([^"]+)"', html)
    yoast_nonce = m.group(1) if m else None
    return wp_nonce, yoast_nonce

def update_yoast_meta(post_id, metadesc):
    wp_nonce, yoast_nonce = get_edit_nonces(post_id)
    if not wp_nonce or not yoast_nonce:
        print(f"  BLAD: Nie udalo sie pobrac nonce (wp={wp_nonce}, yoast={yoast_nonce})")
        return False
    data = {
        'post_ID': str(post_id),
        '_wpnonce': wp_nonce,
        'action': 'editpost',
        'post_type': 'page',
        'post_status': 'publish',
        'original_post_status': 'publish',
        'yoast_free_metabox_nonce': yoast_nonce,
        'yoast_wpseo_metadesc': metadesc,
    }
    encoded = '&'.join(f'{k}={urllib.parse.quote(v, safe="")}' for k, v in data.items())
    r = subprocess.run(['curl', '-s', '--max-time', '30', '-b', COOKIE, '-c', COOKIE,
        '-X', 'POST', 'https://funlikehel.pl/wp-admin/post.php',
        '-d', encoded, '-o', '/dev/null', '-w', '%{http_code}'],
        capture_output=True, text=True)
    status = r.stdout.strip()
    return status == '302'

def fix_h1_on_homepage():
    """Zmienia H1 w tresci strony glownej na H2"""
    nonce = get_rest_nonce()
    if not nonce or nonce == '0':
        print("  BLAD: Brak nonce REST API")
        return False

    # Pobierz tresc strony glownej
    r = subprocess.run(['curl', '-s', '--max-time', '30', '-b', COOKIE,
        '-H', f'X-WP-Nonce: {nonce}',
        'https://funlikehel.pl/wp-json/wp/v2/pages/1329?context=edit&_fields=content'],
        capture_output=True, text=True, encoding='utf-8')

    try:
        d = json.loads(r.stdout)
        content = d.get('content', {}).get('raw', '')
    except:
        print("  BLAD: Nie udalo sie pobrac tresci strony")
        return False

    if not content:
        print("  BLAD: Pusta tresc strony")
        return False

    # Znajdz H1 w bloku heading i zmien na H2
    # Pattern: <!-- wp:heading {"level":1, ...} --> ... <h1 ...>...</h1> ... <!-- /wp:heading -->
    old_content = content

    # Zmien level w komentarzu bloku
    content = re.sub(
        r'(<!-- wp:heading \{[^}]*)"level"\s*:\s*1([^}]*\})',
        lambda m: m.group(0).replace('"level":1', '"level":2').replace('"level": 1', '"level":2'),
        content
    )

    # Zmien tagi h1 na h2 w blokach heading
    content = re.sub(r'<h1(\s[^>]*)>', r'<h2\1>', content)
    content = re.sub(r'</h1>', '</h2>', content)

    if content == old_content:
        print("  INFO: Brak H1 do zmiany w tresci")
        return True

    # Zapisz zmieniona tresc
    payload = json.dumps({'content': content}, ensure_ascii=False)
    payload_path = "C:/Users/\u0141ukaszMichalina/funlikehel/payload_h1_fix.json"
    with open(payload_path, 'w', encoding='utf-8') as f:
        f.write(payload)

    r = subprocess.run(['curl', '-s', '--max-time', '30', '-b', COOKIE,
        '-H', f'X-WP-Nonce: {nonce}',
        '-H', 'Content-Type: application/json',
        '-X', 'POST', 'https://funlikehel.pl/wp-json/wp/v2/pages/1329',
        '--data-binary', f'@{payload_path}',
        '-o', '/dev/null', '-w', '%{http_code}'],
        capture_output=True, text=True)

    status = r.stdout.strip()
    if status == '200':
        print("  OK: H1 zmieniony na H2 w tresci strony glownej")
        return True
    else:
        print(f"  BLAD: HTTP {status}")
        return False

# ============================================================
# MAIN
# ============================================================
print("=== Logowanie ===")
login()
nonce = get_rest_nonce()
print(f"REST nonce: {nonce}")
if not nonce or nonce == '0':
    print("BLAD: Logowanie nie powiodlo sie. Strona moze byc niedostepna.")
    sys.exit(1)

# --- ZADANIE 1: Meta descriptions z polskimi znakami ---
print("\n=== ZADANIE 1: Aktualizacja meta descriptions (Yoast SEO) ===")

pages = {
    1329: {
        'name': 'Strona glowna',
        'slug': '',
        'desc': 'Kursy kitesurfingu, windsurfingu i wingfoil w Jastarni i Hurghadzie. FUN like HEL \u2014 szkolimy przez ca\u0142y rok! 3000+ kursant\u00f3w, 99% pozytywnych opinii.'
    },
    2033: {
        'name': 'Oferta',
        'slug': 'oferta',
        'desc': 'Kursy kite, windsurfing, wingfoil, SUP i wiele wi\u0119cej. Sprawd\u017a ofert\u0119 FUN like HEL \u2014 szkolenia na Helu i w Egipcie. Zarezerwuj termin!'
    },
    2044: {
        'name': 'Egipt-Hurghada',
        'slug': 'egipt-hurghada',
        'desc': 'Kitesurfing w Hurghadzie \u2014 jedyna polska baza Cabrinha Test Center w Egipcie. Pakiety od 2300 z\u0142 z noclegiem. Warunki 365 dni w roku!'
    },
    2161: {
        'name': 'Jastarnia',
        'slug': 'jastarnia',
        'desc': 'Kursy kitesurfingu i windsurfingu w Jastarni na P\u00f3\u0142wyspie Helskim. Najlepsza szko\u0142a na Helu \u2014 p\u0142ytka woda, idealne warunki dla pocz\u0105tkuj\u0105cych.'
    },
    2037: {
        'name': 'Obozy/Kolonie',
        'slug': 'obozy-kolonie',
        'desc': 'Obozy kitesurfingowe, kolonie dla dzieci i Femi Campy. FUN like HEL organizuje wyjazdy na Hel i do Egiptu. Sport, przygoda, nowe umiej\u0119tno\u015bci!'
    },
    2042: {
        'name': 'Kontakt',
        'slug': 'kontakt',
        'desc': 'Skontaktuj si\u0119 z FUN like HEL \u2014 tel. 690 270 032. Szko\u0142a sport\u00f3w wodnych Jastarnia i Hurghada. Zarezerwuj kurs kitesurfingu ju\u017c dzi\u015b!'
    },
    2189: {
        'name': 'Ekipa',
        'slug': 'ekipa',
        'desc': 'Poznaj ekip\u0119 FUN like HEL \u2014 do\u015bwiadczeni instruktorzy kitesurfingu, windsurfingu i wingfoil. Do\u0142\u0105cz do naszego zespo\u0142u na Helu lub w Egipcie!'
    },
    2040: {
        'name': 'Sklep',
        'slug': 'sklep',
        'desc': 'Sklep Cabrinha 2026 \u2014 latawce, deski, foile i akcesoria kite. Aquashop FUN like HEL w Jastarni. Sprz\u0119t testowy i nowy w \u015bwietnych cenach!'
    },
}

for page_id, info in pages.items():
    desc = info['desc']
    name = info['name']
    print(f"\n  [{name}] (ID: {page_id})")
    print(f"    Meta desc ({len(desc)} zn.): {desc}")
    ok = update_yoast_meta(page_id, desc)
    if ok:
        print(f"    -> Zapisano!")
    else:
        print(f"    -> BLAD przy zapisie")
    login()  # odswiez sesje
    time.sleep(1)  # nie przeciazaj serwera

# --- ZADANIE 2: Naprawa podwojnego H1 ---
print("\n=== ZADANIE 2: Naprawa podwojnego H1 na stronie glownej ===")
login()
fix_h1_on_homepage()

# --- WERYFIKACJA ---
print("\n=== WERYFIKACJA META DESCRIPTIONS ===")
for page_id, info in pages.items():
    slug = info['slug']
    name = info['name']
    url = f"https://funlikehel.pl/{slug}/" if slug else "https://funlikehel.pl/"
    r = subprocess.run(['curl', '-s', '--max-time', '15',
        f'https://funlikehel.pl/wp-json/yoast/v1/get_head?url={url}'],
        capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        j = d.get('json', {})
        desc = j.get('description', '(brak)')
        print(f"  [{name}]: {desc[:80]}...")
    except:
        print(f"  [{name}]: BLAD parsowania odpowiedzi")

print("\n=== WERYFIKACJA H1 ===")
r = subprocess.run(['curl', '-s', '--max-time', '15', 'https://funlikehel.pl/'],
    capture_output=True, text=True, encoding='utf-8')
h1s = re.findall(r'<h1[^>]*>.*?</h1>', r.stdout, re.DOTALL | re.IGNORECASE)
print(f"  Liczba H1 na stronie glownej: {len(h1s)}")
for i, h in enumerate(h1s):
    print(f"    H1 #{i+1}: {h[:150]}")

print("\nGotowe!")
