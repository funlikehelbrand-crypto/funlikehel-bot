"""
Przebudowa sklepu:
1. Usun wszystkie stare produkty
2. Dodaj deski Cabrinha 2026 ze zdjeciami cutout i polskimi opisami
"""
import subprocess, json, sys

COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"
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
    print("Login failed"); sys.exit(1)

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

def upload_img(url, filename):
    img_path = f"C:/Users/\u0141ukaszMichalina/funlikehel/{filename}"
    subprocess.run(['curl', '-s', '-L',
        '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        '-o', img_path, url], capture_output=True)
    ct = 'image/png' if filename.endswith('.png') else 'image/jpeg'
    r = subprocess.run(['curl', '-s', '-b', COOKIE,
        '-H', f'X-WP-Nonce: {NONCE}',
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
# 1. USUN WSZYSTKIE STARE PRODUKTY
# =====================================================
print("\n=== USUWAM STARE PRODUKTY ===")
products = api("GET", "/wc/v3/products&per_page=100")
if isinstance(products, list):
    for p in products:
        api("DELETE", f"/wc/v3/products/{p['id']}&force=true")
        sys.stdout.buffer.write(f"  Trash: {p['name']}\n".encode('utf-8'))
    print(f"  Usunieto {len(products)} produktow")

# =====================================================
# 2. KATEGORIE
# =====================================================
print("\n=== KATEGORIE ===")
cat_ids = {}
for cat_name in ["Deski Twin-Tip", "Deski Surf", "Foil Boards"]:
    result = api("POST", "/wc/v3/products/categories", {"name": cat_name})
    if isinstance(result, dict) and 'id' in result:
        cat_ids[cat_name] = result['id']
    elif isinstance(result, dict) and result.get('code') == 'term_exists':
        cat_ids[cat_name] = result['data']['resource_id']
    print(f"  {cat_name}: {cat_ids.get(cat_name, 'ERR')}")

# =====================================================
# 3. NOWE PRODUKTY - DESKI
# =====================================================
print("\n=== NOWE PRODUKTY ===")

boards = [
    {
        "name": "Cabrinha ACE 2026",
        "price": "2899",
        "cat": "Deski Twin-Tip",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-2026-ace-twintip-cutout-768x768.jpg",
        "img_file": "cab-ace-2026-cutout.jpg",
        "desc": "Wszechstronna deska twin-tip \u0142\u0105cz\u0105ca freeride ze stabilno\u015bci\u0105 freestyle. Rdze\u0144 z drewna Paulownia klasy A zapewnia lekkos\u0107 i wytrzyma\u0142o\u015b\u0107. Umiarkowany rocker i double concave daj\u0105 wczesne \u015blizganie i pewny grip na kraw\u0119dziach. Centralne grab raile u\u0142atwiaj\u0105 tricki. W zestawie: finki 4 cm, uchwyt, \u015bruby monta\u017cowe.",
        "short": "Twin-tip freeride/freestyle. Paulownia core, double concave. Rozmiary: 120\u2013145 cm.",
        "sizes": "120, 125, 133, 135, 138, 141, 145 cm",
    },
    {
        "name": "Cabrinha ACE Apex 2026",
        "price": "3569",
        "cat": "Deski Twin-Tip",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-2026-ace-apex-twintip-cutout-768x768.jpg",
        "img_file": "cab-ace-apex-2026-cutout.jpg",
        "desc": "Premiumowa wersja ACE z ulepszonymi materia\u0142ami. L\u017cejsza, sztywniejsza i bardziej responsywna ni\u017c standardowa wersja. Ten sam sprawdzony shape z wy\u017csz\u0105 jako\u015bci\u0105 wykonania \u2014 karbon w kluczowych miejscach, lepszy flex pattern. Dla wymagaj\u0105cych rider\u00f3w, kt\u00f3rzy chc\u0105 wi\u0119cej od swojej deski.",
        "short": "Twin-tip premium z karbonowymi wzmocnieniami. Rozmiary: 120\u2013145 cm.",
        "sizes": "120, 125, 133, 135, 138, 141, 145 cm",
    },
    {
        "name": "Cabrinha Vapor 2026",
        "price": "2999",
        "cat": "Deski Twin-Tip",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-2026-vapor-twintip-cutout-768x768.jpg",
        "img_file": "cab-vapor-2026-cutout.jpg",
        "desc": "Deska stworzona do big airu i freestyle. Progresywny rocker daje pot\u0119\u017cny pop ze skoku, a agresywny flex zapewnia kontrol\u0119 w powietrzu. Mocne kraw\u0119dzie trzymaj\u0105 na kursie nawet przy du\u017cych pr\u0119dko\u015bciach. Dla rider\u00f3w, kt\u00f3rzy chc\u0105 lata\u0107 wy\u017cej i kr\u0119ci\u0107 wi\u0119cej.",
        "short": "Twin-tip big air/freestyle. Agresywny pop i kontrola. Rozmiary: 133\u2013141 cm.",
        "sizes": "133, 136, 139, 141 cm",
    },
    {
        "name": "Cabrinha Vapor Apex 2026",
        "price": "4249",
        "cat": "Deski Twin-Tip",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-2026-vapor-apex-twintip-cutout-768x768.jpg",
        "img_file": "cab-vapor-apex-2026-cutout.jpg",
        "desc": "Premiumowa wersja Vapora z karbonowymi wzmocnieniami i ulepszonym rdzeniem. Jeszcze wi\u0119kszy pop, lepszy flex i mniejsza waga. Ka\u017cdy gram zdj\u0119ty z deski to dodatkowe centymetry w powietrzu. Dla zaawansowanych big air rider\u00f3w.",
        "short": "Twin-tip big air premium. Karbon, maksymalny pop. Rozmiary: 133\u2013141 cm.",
        "sizes": "133, 136, 139, 141 cm",
    },
    {
        "name": "Cabrinha Spectrum 2026",
        "price": "2359",
        "cat": "Deski Twin-Tip",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-2026-spectrum-twintip-cutout-768x768.jpg",
        "img_file": "cab-spectrum-2026-cutout.jpg",
        "desc": "Idealna deska na start z kitesurfingiem. Szeroki outline i p\u0142aski rocker sprawiaj\u0105, \u017ce \u0142atwo si\u0119 na niej p\u0142ywa i wybacza b\u0142\u0119dy pocz\u0105tkuj\u0105cych. Stabilna na wodzie, \u0142atwa do prowadzenia, wygodna do nauki. Twoja pierwsza deska, kt\u00f3ra zabierze Ci\u0119 daleko.",
        "short": "Twin-tip dla pocz\u0105tkuj\u0105cych. Stabilna i wybaczaj\u0105ca. Rozmiary: 133\u2013145 cm.",
        "sizes": "133, 135, 138, 141, 145 cm",
    },
    {
        "name": "Cabrinha Stylus 2026",
        "price": "3179",
        "cat": "Deski Twin-Tip",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-2026-stylus-twintip-cutout-768x768.jpg",
        "img_file": "cab-stylus-2026-cutout.jpg",
        "desc": "Wszechstronny kompromis mi\u0119dzy freeride a freestyle. \u015aredni rocker, zbalansowany flex \u2014 dobrze robi wszystko: od spokojnej jazdy po pierwsze skoki i tricki. \u015awietna deska na drog\u0119 od pocz\u0105tkuj\u0105cego do \u015brednio zaawansowanego.",
        "short": "Twin-tip allround \u2014 freeride i freestyle w jednym. Rozmiary: 131\u2013141 cm.",
        "sizes": "131, 134, 137, 141 cm",
    },
    {
        "name": "Cabrinha Skillit 2026",
        "price": "5499",
        "cat": "Deski Surf",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-skillit-surfboard-2026-cutout-768x768.jpg",
        "img_file": "cab-skillit-2026-cutout.jpg",
        "desc": "Deska surfowa do kite wave ridingu i strapless freestyle. Lekka, zwrotna, z doskona\u0142ym gripem na fali. Shape zaprojektowany do jazdy po falach \u2014 kr\u00f3tkie, ostre zwroty, pewno\u015b\u0107 na kraw\u0119dzi. Dla rider\u00f3w, kt\u00f3rzy chc\u0105 surfowa\u0107 z latawcem.",
        "short": "Deska surfowa do wave ridingu i strapless. Lekka i zwrotna.",
        "sizes": "5'0, 5'4, 5'8",
    },
    {
        "name": "Cabrinha Logic 2026",
        "price": "5749",
        "cat": "Foil Boards",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-logic-foil-board-2026-cutout-768x768.jpg",
        "img_file": "cab-logic-2026-cutout.jpg",
        "desc": "Deska foilowa do kite i wing foilingu. Kompaktowy shape z p\u0142askim deckiem zapewnia stabilno\u015b\u0107 przy starcie i komfort podczas jazdy. Kompatybilna z foilami Cabrinha. Idealna na nauk\u0119 foilowania i progresj\u0119.",
        "short": "Deska foilowa do kite i wing foil. Stabilna i komfortowa.",
        "sizes": "4'4, 4'8, 5'0",
    },
]

for b in boards:
    sys.stdout.buffer.write(f"  {b['name']}... ".encode('utf-8'))
    img_id = upload_img(b['img_url'], b['img_file'])

    cats = [{"id": cat_ids[b['cat']]}] if b['cat'] in cat_ids else []
    data = {
        "name": b['name'],
        "type": "simple",
        "regular_price": b['price'],
        "description": f"{b['desc']}\n\nDost\u0119pne rozmiary: {b['sizes']}\n\nCa\u0142y sprz\u0119t dost\u0119pny do test\u00f3w w naszych bazach \u2014 Jastarnia i Hurghada.",
        "short_description": b['short'],
        "categories": cats,
        "status": "publish",
    }
    if img_id:
        data["images"] = [{"id": img_id}]

    result = api("POST", "/wc/v3/products", data)
    if isinstance(result, dict) and 'id' in result:
        sys.stdout.buffer.write(f"OK (ID:{result['id']}, {b['price']} z\u0142)\n".encode('utf-8'))
    else:
        sys.stdout.buffer.write(f"ERR\n".encode('utf-8'))

print("\nGOTOWE!")
