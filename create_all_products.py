"""
Dodanie WSZYSTKICH produktow Cabrinha 2026 + akcesoriow do WooCommerce
+ YouTube i Google Reviews na stronie glownej
+ Czyszczenie menu
"""
import subprocess, json, sys, time

COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"

def login():
    # Czysty login
    subprocess.run(['curl', '-s',
        '-c', COOKIE,
        'https://funlikehel.pl/wp-login.php'], capture_output=True)

    # Dodaj test cookie
    with open(COOKIE, 'a') as f:
        f.write("funlikehel.pl\tFALSE\t/\tTRUE\t0\twordpress_test_cookie\tWP%20Cookie%20check\n")

    r = subprocess.run(['curl', '-s',
        '-c', COOKIE, '-b', COOKIE,
        '-d', 'log=Admin&pwd=Japoniamarzen1!&wp-submit=Log+In&redirect_to=%2Fwp-admin%2F&testcookie=1',
        '-D', '-',
        'https://funlikehel.pl/wp-login.php'],
        capture_output=True, text=True, encoding='utf-8')
    if 'logged_in' in r.stdout:
        print("Login OK")
        return True
    if 'Too many' in r.stdout:
        print("ZABLOKOWANY - czekam 60s...")
        return False
    print("Login failed - unknown reason")
    return False

def get_nonce():
    r = subprocess.run(['curl', '-s', '-b', COOKIE,
        'https://funlikehel.pl/wp-admin/admin-ajax.php?action=rest-nonce'],
        capture_output=True, text=True)
    return r.stdout.strip()

def api(method, route, data=None, nonce=""):
    cmd = ['curl', '-s', '-b', COOKIE, '-H', f'X-WP-Nonce: {nonce}',
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

def upload_img(url, filename, nonce):
    img_path = f"C:/Users/\u0141ukaszMichalina/funlikehel/{filename}"
    subprocess.run(['curl', '-s', '-L', '-o', img_path, url], capture_output=True)
    ct = 'image/png' if filename.endswith('.png') else 'image/jpeg'
    r = subprocess.run(['curl', '-s', '-b', COOKIE,
        '-H', f'X-WP-Nonce: {nonce}',
        '-H', f'Content-Disposition: attachment; filename={filename}',
        '-H', f'Content-Type: {ct}',
        '-X', 'POST',
        'https://funlikehel.pl/?rest_route=/wp/v2/media',
        '--data-binary', f'@{img_path}'],
        capture_output=True, text=True, encoding='utf-8')
    try:
        d = json.loads(r.stdout)
        return d.get('id')
    except:
        return None

# =====================================================
# WAIT FOR LOGIN
# =====================================================
print("=== LOGOWANIE ===")
for attempt in range(10):
    if login():
        break
    time.sleep(60)
    print(f"  Proba {attempt+2}...")

NONCE = get_nonce()
if NONCE == '0' or not NONCE:
    print("FATAL: Nie udalo sie zalogowac")
    sys.exit(1)
print(f"Nonce: {NONCE}")

# =====================================================
# KATEGORIE
# =====================================================
print("\n=== KATEGORIE ===")
categories_needed = ["Latawce", "Deski", "Wing", "Bary", "Foil", "Akcesoria", "Pokrowce"]
cat_ids = {}
for cat_name in categories_needed:
    result = api("POST", "/wc/v3/products/categories", {"name": cat_name}, NONCE)
    if isinstance(result, dict) and 'id' in result:
        cat_ids[cat_name] = result['id']
    elif isinstance(result, dict) and result.get('code') == 'term_exists':
        cat_ids[cat_name] = result['data']['resource_id']
    print(f"  {cat_name}: {cat_ids.get(cat_name, 'ERR')}")

# =====================================================
# NOWE PRODUKTY (tylko te ktorych jeszcze nie ma)
# =====================================================
print("\n=== NOWE PRODUKTY ===")

new_products = [
    # Latawce
    {"name": "Cabrinha Nitro Apex 2026", "price": "7199", "cat": "Latawce",
     "desc": "Latawiec C-shape do freestyle i wakestyle. Bezposrednia reakcja, potezny pop. Aluula Composite, 3-strutowa konstrukcja.",
     "short": "Latawiec freestyle/wakestyle C-shape. Rozmiary: 7-12 m2.",
     "img": "https://cabrinha.pl/wp-content/uploads/2026/04/Cab_Moto-X-APEX_361118_C1_1.png", "fn": "nitro-apex-2026.png"},
    {"name": "Cabrinha Moto XL Apex 2026", "price": "9449", "cat": "Latawce",
     "desc": "Latawiec light wind do jazdy w slabym wietrze. Ogromna powierzchnia, minimalna waga dzieki Aluula. Idealny na dni bez wiatru.",
     "short": "Latawiec light wind Aluula. Rozmiary: 13-17 m2.",
     "img": "https://cabrinha.pl/wp-content/uploads/2026/04/Cab_Moto-X-APEX_361118_C2_1.png", "fn": "moto-xl-apex-2026.png"},
    # Bary
    {"name": "Cabrinha Bar UNIFY 2026", "price": "2999", "cat": "Bary",
     "desc": "System kontroli UNIFY 2026. Ergonomiczny bar z systemem szybkiego odpiecia, regulacja dlugosci linek. Kompatybilny ze wszystkimi latawcami Cabrinha.",
     "short": "Bar kontroli UNIFY 2026 z systemem bezpieczenstwa.",
     "img": "https://cabrinha.pl/wp-content/uploads/2025/11/Switchblade-C6.png", "fn": "bar-unify-2026.png"},
    # Foil
    {"name": "Cabrinha Logic 2026", "price": "5749", "cat": "Foil",
     "desc": "Kompletny zestaw foil do kite i wing foilingu. Karbon, modularny system, rozne rozmiary skrzydel. Swietna stabilnosc i predkosc.",
     "short": "Foil karbonowy komplet. Do kite i wing foil.",
     "img": "https://cabrinha.pl/wp-content/uploads/2025/11/Mantis-C1.png", "fn": "logic-2026.png"},
    {"name": "Cabrinha H-Series 1000 Carbon", "price": "4999", "cat": "Foil",
     "desc": "Karbonowy foil z serii H. Powierzchnia 1000 cm2, idealny do freeride i wave. Lekki, sztywny, szybki. PROMOCJA!",
     "short": "Foil karbonowy H-Series 1000. Promocja!",
     "img": "https://cabrinha.pl/wp-content/uploads/2025/11/Mantis-C2-.png", "fn": "h-series-1000.png"},
    # Deski dodatkowe
    {"name": "Cabrinha ACE Apex 2026", "price": "3569", "cat": "Deski",
     "desc": "Premiumowa wersja ACE z lepszymi materialami. Lzejsza, sztywniejsza, bardziej responsywna. Dla wymagajacych riderow.",
     "short": "Deska twin-tip premium. Rozmiary: 120-145 cm.",
     "img": "https://cabrinha.pl/wp-content/uploads/2026/04/Cab_Ace_361161_4-1-scaled.jpg", "fn": "ace-apex-2026.jpg"},
    {"name": "Cabrinha Vapor Apex 2026", "price": "4249", "cat": "Deski",
     "desc": "Premiumowa deska big air. Mocniejszy pop, lepszy flex, premium materialy. Dla riderow chcacych wiecej z kazdego skoku.",
     "short": "Deska twin-tip big air premium. Rozmiary: 133-141 cm.",
     "img": "https://cabrinha.pl/wp-content/uploads/2026/04/Cab_Ace_361161_6-1-scaled.jpg", "fn": "vapor-apex-2026.jpg"},
    {"name": "Cabrinha Skillit 2026", "price": "5499", "cat": "Deski",
     "desc": "Deska surfowa do kite. Idealny shape do wave ridingu i strapless freestyle. Lekka, zwrotna, z doskonalym gripu.",
     "short": "Deska surfowa do kite wave riding.",
     "img": "https://cabrinha.pl/wp-content/uploads/2026/04/Cab_Ace_361161_7-scaled.jpg", "fn": "skillit-2026.jpg"},
    # Wing dodatkowe
    {"name": "Cabrinha AER 2026", "price": "3349", "cat": "Wing",
     "desc": "Wing foil dla poczatkujacych i srednio zaawansowanych. Stabilny, latwy w obsludze, przystepna cena. Idealny pierwszy wing.",
     "short": "Wing foil entry-level. Rozmiary: 3-6 m.",
     "img": "https://cabrinha.pl/wp-content/uploads/2025/11/Mantis-C5.png", "fn": "aer-2026.png"},
    # Akcesoria kluczowe
    {"name": "Cabrinha Kask bialy", "price": "219", "cat": "Akcesoria",
     "desc": "Kask ochronny do kitesurfingu i wing foilingu. Lekki, wygodny, regulowany. Niezbedne zabezpieczenie na wodzie.",
     "short": "Kask ochronny do sportow wodnych. Promocja!",
     "img": "https://cabrinha.pl/wp-content/uploads/2025/11/Switchblade-C2.png", "fn": "kask-bialy.png"},
    {"name": "Cabrinha Pompka XL", "price": "219", "cat": "Akcesoria",
     "desc": "Duza pompka do latawcow kite i wing. Szybkie pompowanie, trwala konstrukcja. Kompatybilna ze wszystkimi latawcami.",
     "short": "Pompka XL do latawcow kite i wing.",
     "img": "https://cabrinha.pl/wp-content/uploads/2025/11/Switchblade-C1.png", "fn": "pompka-xl.png"},
    {"name": "Cabrinha Source Pady i Strapy", "price": "699", "cat": "Akcesoria",
     "desc": "Pady i strapy Source do desek twin-tip. Wygodne, regulowane, trwale. Promocja!",
     "short": "Pady i strapy do deski twin-tip. Promocja!",
     "img": "https://cabrinha.pl/wp-content/uploads/2026/04/Cab_Ace_361161_8-scaled.jpg", "fn": "source-pady.jpg"},
    # Pokrowce
    {"name": "Cabrinha Golf Bag 140cm", "price": "699", "cat": "Pokrowce",
     "desc": "Pokrowiec na latawce typu golf bag. Miesci 2-3 latawce, bar i akcesoria. Kolka do transportu, wytrzymaly material.",
     "short": "Pokrowiec golf bag na latawce 140cm. Promocja!",
     "img": "https://cabrinha.pl/wp-content/uploads/2026/04/Cab_Ace_361161_9-scaled.jpg", "fn": "golf-bag.jpg"},
    {"name": "Cabrinha Leash Pro dlugi", "price": "129", "cat": "Akcesoria",
     "desc": "Profesjonalny leash do kite. Dlugi model, elastyczny, bezpieczny. Obowiazkowy element wyposazenia. Promocja!",
     "short": "Leash dlugi do kite. Promocja!",
     "img": "https://cabrinha.pl/wp-content/uploads/2025/11/Switchblade-12-scaled.jpg", "fn": "leash-pro.jpg"},
]

for p in new_products:
    print(f"  {p['name']}...", end=" ")
    img_id = upload_img(p['img'], p['fn'], NONCE)
    cats = [{"id": cat_ids[p['cat']]}] if p['cat'] in cat_ids else []
    data = {
        "name": p['name'], "type": "simple", "regular_price": p['price'],
        "description": p['desc'], "short_description": p['short'],
        "categories": cats, "status": "publish",
    }
    if img_id:
        data["images"] = [{"id": img_id}]
    result = api("POST", "/wc/v3/products", data, NONCE)
    if isinstance(result, dict) and 'id' in result:
        print(f"OK (ID:{result['id']})")
    else:
        print(f"ERR: {str(result)[:80]}")

# =====================================================
# YOUTUBE + GOOGLE REVIEWS na stronie glownej
# =====================================================
print("\n=== YOUTUBE + GOOGLE REVIEWS ===")
page = api("GET", "/wp/v2/pages/1329&context=edit", nonce=NONCE)
if isinstance(page, dict) and 'content' in page:
    content = page['content']['raw']

    yt_reviews = """
<!-- wp:group {"align":"full","style":{"spacing":{"padding":{"top":"60px","bottom":"60px"}}}} -->
<div class="wp-block-group alignfull" style="padding-top:60px;padding-bottom:60px"><!-- wp:heading {"textAlign":"center","level":2,"style":{"typography":{"fontSize":"36px"}}} -->
<h2 class="wp-block-heading has-text-align-center" style="font-size:36px">Zobacz nas w akcji</h2>
<!-- /wp:heading -->
<!-- wp:html -->
<div style="max-width:900px;margin:20px auto;text-align:center">
<iframe width="100%" height="500" src="https://www.youtube.com/embed?listType=user_uploads&list=FunLikeHel" frameborder="0" allowfullscreen style="border-radius:12px;"></iframe>
</div>
<!-- /wp:html -->
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->
<div class="wp-block-buttons"><!-- wp:button {"className":"is-style-outline"} -->
<div class="wp-block-button is-style-outline"><a class="wp-block-button__link wp-element-button" href="https://www.youtube.com/@FunLikeHel" target="_blank">Wiecej filmow na YouTube</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:group -->

<!-- wp:group {"align":"full","style":{"spacing":{"padding":{"top":"60px","bottom":"60px"}},"color":{"background":"#f9f9f9"}}} -->
<div class="wp-block-group alignfull" style="background-color:#f9f9f9;padding-top:60px;padding-bottom:60px"><!-- wp:heading {"textAlign":"center","level":2,"style":{"typography":{"fontSize":"36px"}}} -->
<h2 class="wp-block-heading has-text-align-center" style="font-size:36px">Opinie naszych klientow</h2>
<!-- /wp:heading -->
<!-- wp:paragraph {"align":"center","style":{"typography":{"fontSize":"18px"}}} -->
<p class="has-text-align-center" style="font-size:18px">99% pozytywnych recenzji na Google</p>
<!-- /wp:paragraph -->
<!-- wp:html -->
<div style="max-width:800px;margin:20px auto;text-align:center">
<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2322!2d33.6925!3d27.3347!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x1452653a6faee49d%3A0x9c73c2e88d773aa1!2sFUNLIKEHEL%20EGYPT%20Cabrinha%20Test%20Center!5e0!3m2!1spl!2spl" width="100%" height="400" style="border:0;border-radius:12px;" allowfullscreen="" loading="lazy"></iframe>
</div>
<!-- /wp:html -->
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->
<div class="wp-block-buttons"><!-- wp:button -->
<div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="https://maps.app.goo.gl/MU8Co8dDKndSkcVGA" target="_blank">Zobacz wszystkie opinie na Google</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:group -->
"""

    # Wstaw przed ostatnim cover (kemping CTA)
    last_cover = content.rfind('<!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/10/kemping2.png"')
    if last_cover > 0:
        content = content[:last_cover] + yt_reviews + content[last_cover:]
    else:
        content += yt_reviews

    result = api("POST", "/wp/v2/pages/1329", {"content": content}, NONCE)
    if isinstance(result, dict) and 'id' in result:
        print("  OK: YouTube + Google Reviews dodane")
    else:
        print(f"  ERR: {str(result)[:200]}")
else:
    print("  ERR: Nie mozna pobrac strony glownej")

# =====================================================
# MENU - wyczysc i postaw 5 pozycji
# =====================================================
print("\n=== MENU ===")
items = api("GET", "/wp/v2/menu-items&menus=22&per_page=100", nonce=NONCE)
if isinstance(items, list):
    for item in items:
        api("DELETE", f"/wp/v2/menu-items/{item['id']}&force=true", nonce=NONCE)
    print(f"  Wyczyszczono {len(items)} pozycji")

menu_pages = [
    ("Oferta", 2033, 1),
    ("Egipt", 2044, 2),
    ("Obozy i Kolonie", 2037, 3),
    ("Sklep", 2040, 4),
    ("Kontakt", 2042, 5),
]
for title, page_id, order in menu_pages:
    result = api("POST", "/wp/v2/menu-items", {
        "title": title, "type": "post_type", "object": "page",
        "object_id": page_id,
        "url": f"https://funlikehel.pl/?page_id={page_id}",
        "menus": 22, "menu_order": order, "parent": 0, "status": "publish"
    }, NONCE)
    if isinstance(result, dict) and 'id' in result:
        print(f"  OK #{order} {title}")

print("\n=== WSZYSTKO GOTOWE ===")
