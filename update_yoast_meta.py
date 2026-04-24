import subprocess, json, sys, urllib.parse

COOKIE = "C:/Users/ŁukaszMichalina/funlikehel/wp_cookies.txt"

def login():
    subprocess.run(['curl', '-s', '-c', COOKIE, 'https://funlikehel.pl/wp-login.php'], capture_output=True)
    with open(COOKIE, 'a') as f:
        f.write("funlikehel.pl\tFALSE\t/\tTRUE\t0\twordpress_test_cookie\tWP%20Cookie%20check\n")
    subprocess.run(['curl', '-s', '-c', COOKIE, '-b', COOKIE,
        '-d', 'log=Admin&pwd=Japoniamarzen1!&wp-submit=Log+In&redirect_to=%2Fwp-admin%2F&testcookie=1',
        'https://funlikehel.pl/wp-login.php'], capture_output=True)

def get_rest_nonce():
    r = subprocess.run(['curl', '-s', '-b', COOKIE,
        'https://funlikehel.pl/wp-admin/admin-ajax.php?action=rest-nonce'],
        capture_output=True, text=True)
    return r.stdout.strip()

def get_edit_nonces(post_id):
    """Get _wpnonce and yoast_free_metabox_nonce from the edit page"""
    r = subprocess.run(['curl', '-s', '-b', COOKIE,
        f'https://funlikehel.pl/wp-admin/post.php?post={post_id}&action=edit'],
        capture_output=True, text=True, encoding='utf-8')
    html = r.stdout
    
    import re
    # WP nonce
    m = re.search(r'id="_wpnonce" name="_wpnonce" value="([^"]+)"', html)
    wp_nonce = m.group(1) if m else None
    
    # Yoast nonce
    m = re.search(r'yoast_free_metabox_nonce" value="([^"]+)"', html)
    yoast_nonce = m.group(1) if m else None
    
    return wp_nonce, yoast_nonce

def update_yoast_meta(post_id, metadesc, metatitle=None):
    """Update Yoast SEO meta description for a post/page"""
    wp_nonce, yoast_nonce = get_edit_nonces(post_id)
    if not wp_nonce or not yoast_nonce:
        print(f"  ERROR: Could not get nonces for post {post_id} (wp={wp_nonce}, yoast={yoast_nonce})")
        return False
    
    # Build form data - minimal fields needed for post.php
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
    if metatitle:
        data['yoast_wpseo_title'] = metatitle
    
    # URL-encode the data
    encoded = '&'.join(f'{k}={urllib.parse.quote(v, safe="")}' for k, v in data.items())
    
    r = subprocess.run(['curl', '-s', '-b', COOKIE, '-c', COOKIE,
        '-X', 'POST', 'https://funlikehel.pl/wp-admin/post.php',
        '-d', encoded,
        '-o', '/dev/null', '-w', '%{http_code}'],
        capture_output=True, text=True)
    
    status = r.stdout.strip()
    if status == '302':
        # Verify
        r2 = subprocess.run(['curl', '-s',
            f'https://funlikehel.pl/wp-json/yoast/v1/get_head?url=https://funlikehel.pl/?page_id={post_id}'],
            capture_output=True, text=True)
        return True
    else:
        print(f"  ERROR: HTTP {status}")
        return False

# Login
login()
nonce = get_rest_nonce()
print(f"REST nonce: {nonce}")
if nonce == '0':
    print("Login failed!")
    sys.exit(1)

# Pages to update with meta descriptions
pages = {
    1329: {  # Homepage
        'desc': 'Kursy kitesurfingu, windsurfingu i wingfoil w Jastarni i Hurghadzie. FUN like HEL - szkolimy przez caly rok! 3000+ kursantow, 99% pozytywnych opinii.',
        'slug': ''
    },
    2033: {  # Oferta
        'desc': 'Kursy kite, windsurfing, wingfoil, SUP i wiele wiecej. Sprawdz oferte FUN like HEL - szkolenia na Helu i w Egipcie. Zarezerwuj termin!',
        'slug': 'oferta'
    },
    2044: {  # Egipt-Hurghada
        'desc': 'Kitesurfing w Hurghadzie - jedyna polska baza Cabrinha Test Center w Egipcie. Pakiety od 2300 zl z noclegiem. Warunki 365 dni w roku!',
        'slug': 'egipt-hurghada'
    },
    2161: {  # Jastarnia
        'desc': 'Kursy kitesurfingu i windsurfingu w Jastarni na Polwyspie Helskim. Najlepsza szkola na Helu - plytka woda, idealne warunki dla poczatkujacych.',
        'slug': 'jastarnia'
    },
    2037: {  # Obozy/Kolonie
        'desc': 'Obozy kitesurfingowe, kolonie dla dzieci i Femi Campy. FUN like HEL organizuje wyjazdy na Hel i do Egiptu. Sport, przygoda, nowe umiejetnosci!',
        'slug': 'obozy-kolonie'
    },
    2042: {  # Kontakt
        'desc': 'Skontaktuj sie z FUN like HEL - tel. 690 270 032. Szkola sportow wodnych Jastarnia i Hurghada. Zarezerwuj kurs kitesurfingu juz dzis!',
        'slug': 'kontakt'
    },
    2189: {  # Ekipa
        'desc': 'Poznaj ekipe FUN like HEL - doswiadczeni instruktorzy kitesurfingu, windsurfingu i wingfoil. Dolacz do naszego zespolu na Helu lub w Egipcie!',
        'slug': 'ekipa'
    },
    2040: {  # Sklep
        'desc': 'Sklep Cabrinha 2026 - latawce, deski, foile i akcesoria kite. Aquashop FUN like HEL w Jastarni. Sprzet testowy i nowy w swietnych cenach!',
        'slug': 'sklep'
    },
}

for page_id, info in pages.items():
    desc = info['desc']
    slug = info['slug'] or '(homepage)'
    print(f"\n--- {slug} (ID: {page_id}) ---")
    print(f"  Meta desc ({len(desc)} chars): {desc}")
    ok = update_yoast_meta(page_id, desc)
    if ok:
        print(f"  -> HTTP 302 (saved)")
    
    # Re-login periodically to keep session fresh
    login()

print("\n=== WERYFIKACJA ===")
for page_id, info in pages.items():
    slug = info['slug']
    url = f"https://funlikehel.pl/{slug}/" if slug else "https://funlikehel.pl/"
    r = subprocess.run(['curl', '-s',
        f'https://funlikehel.pl/wp-json/yoast/v1/get_head?url={url}'],
        capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        j = d.get('json', {})
        desc = j.get('description', '(brak)')
        print(f"  {slug or '(homepage)'}: {desc[:80]}...")
    except:
        print(f"  {slug or '(homepage)'}: ERROR parsing response")
