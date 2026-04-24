"""
Tworzenie produktow Cabrinha w WooCommerce na funlikehel.pl
"""
import subprocess, json, sys, time

COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"

# Relogin
subprocess.run(['curl', '-s', '-c', COOKIE,
    '-b', 'wordpress_test_cookie=WP+Cookie+check',
    '-d', 'log=Admin&pwd=Japoniamarzen1!&wp-submit=Log+In&redirect_to=%2Fwp-admin%2F&testcookie=1',
    'https://funlikehel.pl/wp-login.php'], capture_output=True)

r = subprocess.run(['curl', '-s', '-b', COOKIE,
    'https://funlikehel.pl/wp-admin/admin-ajax.php?action=rest-nonce'],
    capture_output=True, text=True)
NONCE = r.stdout.strip()
print(f"Nonce: {NONCE}")

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

def upload_image(url, filename):
    """Pobierz zdjecie z cabrinha.pl i wgraj do WP"""
    img_path = f"C:/Users/\u0141ukaszMichalina/funlikehel/{filename}"
    subprocess.run(['curl', '-s', '-L', '-o', img_path, url], capture_output=True)

    # Upload do WP
    content_type = 'image/png' if filename.endswith('.png') else 'image/jpeg'
    r = subprocess.run(['curl', '-s', '-b', COOKIE,
        '-H', f'X-WP-Nonce: {NONCE}',
        '-H', f'Content-Disposition: attachment; filename={filename}',
        '-H', f'Content-Type: {content_type}',
        '-X', 'POST',
        'https://funlikehel.pl/?rest_route=/wp/v2/media',
        '--data-binary', f'@{img_path}'],
        capture_output=True, text=True, encoding='utf-8')
    try:
        d = json.loads(r.stdout)
        if 'id' in d:
            return d['id']
    except:
        pass
    return None

# =====================================================
# Produkty do stworzenia
# =====================================================
products = [
    {
        "name": "Cabrinha Moto X Apex 2026",
        "price": "7599",
        "description": "Nowoczesny latawiec freeride z ultralekkiego Aluula Composite. Konstrukcja 3-strutowa zapewnia balans mocy i stabilnosci. Reactive Wing Tip dla precyzyjnego sterowania, system bridle 7-punktowy. Poszycie Teijin D2 Ripstop \u2014 lekkie i wytrzymale. Przeznaczony do freeride, big air, surfingu i foila.",
        "short_desc": "Latawiec freeride Aluula \u2014 lekki, mocny, wszechstronny. Rozmiary: 7-12 m\u00b2.",
        "image_url": "https://cabrinha.pl/wp-content/uploads/2026/04/mtok.jpg",
        "image_name": "cabrinha-moto-x-apex-2026.jpg",
        "categories": ["Latawce"],
    },
    {
        "name": "Cabrinha Switchblade Apex 2026",
        "price": "6799",
        "description": "Wszechstronny latawiec freeride 5-strutowy z hybrydowym profilem. Fusion Wing Tip zapewnia stabilnosc i kontrole mocy. System Airframe Inflation, Teijin D2 Ripstop, Ultra HT. Dla poczatkujacych i zaawansowanych kitesurferow. Rozmiary 5-14 m\u00b2.",
        "short_desc": "Legendarny allround \u2014 od nauki do zaawansowanych trikow. Rozmiary: 5-14 m\u00b2.",
        "image_url": "https://cabrinha.pl/wp-content/uploads/2025/11/Switchblade-C5.png",
        "image_name": "cabrinha-switchblade-apex-2026.png",
        "categories": ["Latawce"],
    },
    {
        "name": "Cabrinha Drifter Apex 2026",
        "price": "6699",
        "description": "Latawiec wave/strapless freestyle. Szybki zwrot, doskonala kontrola mocy, drift na fali bez ciagniecia. Idealny do surfowania na kicie i strapless freestyle. Aluula Composite.",
        "short_desc": "Latawiec wave \u2014 drift, surf, strapless. Rozmiary: 5-12 m\u00b2.",
        "image_url": "https://cabrinha.pl/wp-content/uploads/2026/04/Cab_Moto-X-APEX_361118_C2_1.png",
        "image_name": "cabrinha-drifter-apex-2026.png",
        "categories": ["Latawce"],
    },
    {
        "name": "Cabrinha ACE 2026",
        "price": "2899",
        "description": "Wszechstronna deska twin-tip laczaca freeride ze stabilnoscia freestyle. Umiarkowany rocker, double concave, rdzen z drewna Paulownia klasy A. Centralne grab raile. W zestawie: 4cm finki, uchwyt, sruby.",
        "short_desc": "Deska twin-tip freeride/freestyle. Rozmiary: 120-145 cm.",
        "image_url": "https://cabrinha.pl/wp-content/uploads/2026/04/ACEok.png",
        "image_name": "cabrinha-ace-2026.png",
        "categories": ["Deski"],
    },
    {
        "name": "Cabrinha Vapor 2026",
        "price": "2999",
        "description": "Deska twin-tip zaprojektowana do big airu i freestyle. Progresywny rocker, agresywny flex, mocne krawedzie. Dla zaawansowanych riderow szukajacych popu i kontroli w powietrzu.",
        "short_desc": "Deska twin-tip big air/freestyle. Rozmiary: 133-141 cm.",
        "image_url": "https://cabrinha.pl/wp-content/uploads/2026/04/Cab_Ace_361161_1-scaled.png",
        "image_name": "cabrinha-vapor-2026.png",
        "categories": ["Deski"],
    },
    {
        "name": "Cabrinha Mantis 2026",
        "price": "4249",
        "description": "Wszechstronne skrzydlo wing foil zapewniajace stabilnosc, moc i kontrole. High-stiffness LE, Drop Strut Design. Composite boom handle w zestawie. Do wave ridingu i freeride. Rozmiary 2-6 m.",
        "short_desc": "Wing foil allround \u2014 stabilny, mocny, kontrolowany. Rozmiary: 2-6 m.",
        "image_url": "https://cabrinha.pl/wp-content/uploads/2025/11/Mantis-C5.png",
        "image_name": "cabrinha-mantis-2026.png",
        "categories": ["Wing"],
    },
    {
        "name": "Cabrinha Mantis Apex Aluula 2026",
        "price": "6199",
        "description": "Premiumowa wersja Mantisa z Aluula Composite. Najlzejszy wing w ofercie \u2014 wyjatkowa sztywnosc przy minimalnej wadze. Fenomenalne czucie wiatru i natychmiastowa reakcja. Dla wymagajacych riderow.",
        "short_desc": "Wing foil premium Aluula \u2014 najlzejszy, najsztywniejszy. Rozmiary: 2-6 m.",
        "image_url": "https://cabrinha.pl/wp-content/uploads/2025/11/Mantis-C4.png",
        "image_name": "cabrinha-mantis-apex-2026.png",
        "categories": ["Wing"],
    },
    {
        "name": "Cabrinha Spectrum 2026",
        "price": "2359",
        "description": "Deska twin-tip dla poczatkujacych i srednio zaawansowanych. Szeroki outline, plaski rocker \u2014 latwa do plywania i wybaczajaca bledy. Idealna na pierwsze kroki w kitesurfingu.",
        "short_desc": "Deska twin-tip dla poczatkujacych. Rozmiary: 133-145 cm.",
        "image_url": "https://cabrinha.pl/wp-content/uploads/2026/04/Cab_Ace_361161_2-scaled.png",
        "image_name": "cabrinha-spectrum-2026.png",
        "categories": ["Deski"],
    },
]

# =====================================================
# Tworzenie kategorii WooCommerce
# =====================================================
print("=== TWORZENIE KATEGORII ===")
cat_ids = {}
for cat_name in ["Latawce", "Deski", "Wing"]:
    result = api("POST", "/wc/v3/products/categories", {"name": cat_name})
    if isinstance(result, dict) and 'id' in result:
        cat_ids[cat_name] = result['id']
        print(f"  OK: {cat_name} (ID:{result['id']})")
    elif isinstance(result, dict) and result.get('code') == 'term_exists':
        cat_ids[cat_name] = result['data']['resource_id']
        print(f"  Istnieje: {cat_name} (ID:{result['data']['resource_id']})")
    else:
        print(f"  ERR: {cat_name} \u2014 {str(result)[:100]}")

# =====================================================
# Tworzenie produktow
# =====================================================
print("\n=== TWORZENIE PRODUKTOW ===")
for p in products:
    print(f"\n  Pobieram zdjecie: {p['image_name']}...")
    img_id = upload_image(p['image_url'], p['image_name'])

    if not img_id:
        print(f"  WARN: Nie udalo sie wgrac zdjecia, tworze bez")

    cats = [{"id": cat_ids[c]} for c in p['categories'] if c in cat_ids]

    product_data = {
        "name": p['name'],
        "type": "simple",
        "regular_price": p['price'],
        "description": p['description'],
        "short_description": p['short_desc'],
        "categories": cats,
        "status": "publish",
    }

    if img_id:
        product_data["images"] = [{"id": img_id}]

    result = api("POST", "/wc/v3/products", product_data)
    if isinstance(result, dict) and 'id' in result:
        print(f"  OK: {p['name']} (ID:{result['id']}, {p['price']} zl)")
    else:
        print(f"  ERR: {p['name']} \u2014 {str(result)[:150]}")

print("\nGOTOWE!")
