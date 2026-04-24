import subprocess, json, sys

COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"
NONCE = "866bcb4140"

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

# XCal 2026 - cena szacunkowa na poziomie Stylus/Vapor
# XCal Apex - cena na poziomie Vapor Apex
xcal_products = [
    {
        "name": "Cabrinha XCal 2026",
        "price": "3199",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-2026-xcal-twintip-cutout-768x768.jpg",
        "img_file": "cab-xcal-2026-cutout.jpg",
        "desc": (
            "Deska freestyle/wakestyle zaprojektowana do agresywnej jazdy i trik\u00f3w. "
            "Sztywny flex i p\u0142aski rocker daj\u0105 maksymalny pop z chopperu i precyzyjne l\u0105dowania. "
            "Wzmocnione kraw\u0119dzie trzymaj\u0105 nawet przy pe\u0142nej mocy. "
            "Dla rider\u00f3w, kt\u00f3rzy chc\u0105 kr\u0119ci\u0107 handlepass, kiteloop i unhooked tricki. "
            "Dost\u0119pna wy\u0142\u0105cznie u oficjalnych dystrybutor\u00f3w Cabrinha \u2014 takich jak my."
            "\n\nDost\u0119pne rozmiary: 133, 136, 139 cm"
            "\n\nCa\u0142y sprz\u0119t dost\u0119pny do test\u00f3w w naszych bazach \u2014 Jastarnia i Hurghada."
        ),
        "short": "Twin-tip freestyle/wakestyle. Sztywny, agresywny, precyzyjny. Rozmiary: 133\u2013139 cm.",
    },
    {
        "name": "Cabrinha XCal Apex 2026",
        "price": "4399",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-2026-xcal-apex-twintip-cutout-768x768.jpg",
        "img_file": "cab-xcal-apex-2026-cutout.jpg",
        "desc": (
            "Premiumowa wersja XCal z karbonowymi wzmocnieniami i ulepszonym rdzeniem. "
            "Jeszcze sztywniejsza, jeszcze l\u017cejsza \u2014 ka\u017cdy gram mniej to ostrzejsza reakcja i wi\u0119kszy pop. "
            "Apex construction: karbon w kluczowych strefach, premium materialy, najwy\u017cszy poziom wykonania. "
            "Najlepsza deska freestyle w kolekcji Cabrinha 2026. "
            "Dost\u0119pna wy\u0142\u0105cznie u oficjalnych dystrybutor\u00f3w."
            "\n\nDost\u0119pne rozmiary: 133, 136, 139 cm"
            "\n\nCa\u0142y sprz\u0119t dost\u0119pny do test\u00f3w w naszych bazach \u2014 Jastarnia i Hurghada."
        ),
        "short": "Twin-tip freestyle premium. Karbon, maksymalna precyzja. Rozmiary: 133\u2013139 cm.",
    },
]

print("=== DODAJE XCAL ===")
for p in xcal_products:
    sys.stdout.buffer.write(f"  {p['name']}... ".encode('utf-8'))
    img_id = upload_img(p['img_url'], p['img_file'])

    data = {
        "name": p['name'],
        "type": "simple",
        "regular_price": p['price'],
        "description": p['desc'],
        "short_description": p['short'],
        "categories": [{"id": 54}],  # Deski Twin-Tip
        "status": "publish",
    }
    if img_id:
        data["images"] = [{"id": img_id}]

    result = api("POST", "/wc/v3/products", data)
    if isinstance(result, dict) and 'id' in result:
        sys.stdout.buffer.write(f"OK (ID:{result['id']}, {p['price']} zl)\n".encode('utf-8'))
    else:
        sys.stdout.buffer.write(f"ERR: {str(result)[:100]}\n".encode('utf-8'))

print("\nGOTOWE!")
