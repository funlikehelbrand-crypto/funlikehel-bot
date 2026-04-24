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

# Kategoria Latawce
print("=== KATEGORIA ===")
result = api("POST", "/wc/v3/products/categories", {"name": "Latawce (Kites)"})
if isinstance(result, dict) and 'id' in result:
    kite_cat = result['id']
elif isinstance(result, dict) and result.get('code') == 'term_exists':
    kite_cat = result['data']['resource_id']
else:
    kite_cat = None
print(f"  Latawce: {kite_cat}")

kites = [
    {
        "name": "Cabrinha Switchblade Apex 2026",
        "price": "6799",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2025/11/cabrinhaswitchblade20261-768x768.jpg",
        "img_file": "cab-switchblade-2026-cutout.jpg",
        "desc": (
            "Legendarny allround Cabrinhy \u2014 najbardziej wszechstronny latawiec na rynku. "
            "Konstrukcja 5-strutowa z hybrydowym profilem i Fusion Wing Tips zapewnia "
            "stabilno\u015b\u0107 i kontrol\u0119 mocy w ka\u017cdych warunkach. Draft-forward profil 2026 "
            "daje lepsze ci\u0105gni\u0119cie przy mniejszym wysi\u0142ku i pot\u0119\u017cniejszy pop do skok\u00f3w.\n\n"
            "Idealny do: freeride, big air, wave, nauka.\n"
            "Materia\u0142y: Ultra HT Airframe, Teijin D2 Canopy, Pure Form Panels.\n\n"
            "Dost\u0119pne rozmiary: 5, 6, 7, 8, 9, 10, 11, 12, 14 m\u00b2\n"
            "Ceny od 6 799 z\u0142 do 9 799 z\u0142 w zale\u017cno\u015bci od rozmiaru.\n\n"
            "Przetestuj na wodzie w naszych bazach \u2014 Jastarnia i Hurghada."
        ),
        "short": "Latawiec allround 5-strut. Freeride, big air, wave. Rozmiary: 5\u201314 m\u00b2. Od 6 799 z\u0142.",
    },
    {
        "name": "Cabrinha Drifter Apex 2026",
        "price": "6699",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2025/11/cabrinha2026drifterkite1-1-768x768.jpg",
        "img_file": "cab-drifter-2026-cutout.jpg",
        "desc": (
            "Ikoniczny latawiec surfowy \u2014 benchmark do wave ridingu i strapless freestyle. "
            "Konstrukcja 3-strutowa z Surf/Drift Wing Tips zapewnia fenomenalny drift na fali "
            "bez ci\u0105gni\u0119cia. Bezpo\u015brednie sterowanie, szybki zwrot, doskona\u0142a kontrola mocy.\n\n"
            "Idealny do: wave riding, strapless freestyle, down-the-line.\n"
            "Materia\u0142y: Aluula Composite, Teijin D2 Canopy.\n\n"
            "Dost\u0119pne rozmiary: 5, 6, 7, 8, 9, 10, 12 m\u00b2\n"
            "Ceny od 6 699 z\u0142 do 8 999 z\u0142 w zale\u017cno\u015bci od rozmiaru.\n\n"
            "Przetestuj na wodzie w naszych bazach \u2014 Jastarnia i Hurghada."
        ),
        "short": "Latawiec wave/strapless 3-strut. Drift, surf, kontrola. Rozmiary: 5\u201312 m\u00b2. Od 6 699 z\u0142.",
    },
    {
        "name": "Cabrinha Nitro Apex 2026",
        "price": "7199",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2025/11/cabrinha2026nitrokite1-768x768.jpg",
        "img_file": "cab-nitro-2026-cutout.jpg",
        "desc": (
            "Bro\u0144 na big air \u2014 maksymalny lift, stabilno\u015b\u0107 i hang time. "
            "Konstrukcja 5-strutowa High Aspect z High Sweep daje ogromne zasysanie "
            "i d\u0142ugie loty. Wersja 2026 z ulepszonym profilem canopy dla jeszcze "
            "lepszej stabilno\u015bci w porywach i pewniejszych l\u0105dowa\u0144.\n\n"
            "Idealny do: big air, megaloopy, kiteloop.\n"
            "Materia\u0142y: Ultra HT Airframe, Teijin D2 Canopy, Pure Form Panels.\n\n"
            "Dost\u0119pne rozmiary: 7, 8, 9, 10, 12 m\u00b2\n"
            "Ceny od 7 199 z\u0142 do 9 399 z\u0142 w zale\u017cno\u015bci od rozmiaru.\n\n"
            "Przetestuj na wodzie w naszych bazach \u2014 Jastarnia i Hurghada."
        ),
        "short": "Latawiec big air 5-strut. Maksymalny lift i hang time. Rozmiary: 7\u201312 m\u00b2. Od 7 199 z\u0142.",
    },
    {
        "name": "Cabrinha Moto X Apex 2026",
        "price": "7599",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-2026-moto-kite-c1-cutout-768x768.jpg",
        "img_file": "cab-moto-x-2026-cutout.jpg",
        "desc": (
            "Nowoczesny latawiec freeride z ultralekkiego Aluula Composite. "
            "Konstrukcja 3-strutowa zapewnia idealny balans mocy i stabilno\u015bci. "
            "Reactive Wing Tip dla precyzyjnego sterowania, 7-punktowy system bridle. "
            "Poszycie Teijin D2 Ripstop \u2014 lekkie i wytrzyma\u0142e.\n\n"
            "Idealny do: freeride, foil, big air, surf.\n"
            "Materia\u0142y: Aluula Composite, Teijin D2 Canopy.\n\n"
            "Dost\u0119pne rozmiary: 7, 8, 9, 10, 12 m\u00b2\n"
            "Ceny od 7 599 z\u0142 do 8 999 z\u0142 w zale\u017cno\u015bci od rozmiaru.\n\n"
            "Przetestuj na wodzie w naszych bazach \u2014 Jastarnia i Hurghada."
        ),
        "short": "Latawiec freeride Aluula 3-strut. Lekki, mocny, wszechstronny. Rozmiary: 7\u201312 m\u00b2. Od 7 599 z\u0142.",
    },
    {
        "name": "Cabrinha Moto XL Apex 2026",
        "price": "9449",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-2026-moto-xl-apex-kite-c1-cutout-768x768.jpg",
        "img_file": "cab-moto-xl-2026-cutout.jpg",
        "desc": (
            "Latawiec light wind do jazdy w s\u0142abym wietrze. Ogromna powierzchnia "
            "przy minimalnej wadze dzi\u0119ki Aluula Composite. Kiedy inni siedz\u0105 na pla\u017cy, "
            "Ty ju\u017c jedziesz. Stabilny, \u0142atwy w obs\u0142udze mimo du\u017cego rozmiaru.\n\n"
            "Idealny do: light wind, foil, freeride w s\u0142abych warunkach.\n"
            "Materia\u0142y: Aluula Composite, Featherlite Bladders.\n\n"
            "Dost\u0119pne rozmiary: 13, 15, 17 m\u00b2\n"
            "Ceny od 9 449 z\u0142 do 10 499 z\u0142 w zale\u017cno\u015bci od rozmiaru.\n\n"
            "Przetestuj na wodzie w naszych bazach \u2014 Jastarnia i Hurghada."
        ),
        "short": "Latawiec light wind Aluula. Ogromna powierzchnia, minimalna waga. Rozmiary: 13\u201317 m\u00b2. Od 9 449 z\u0142.",
    },
]

print("\n=== DODAJE KAJTY ===")
for k in kites:
    sys.stdout.buffer.write(f"  {k['name']}... ".encode('utf-8'))
    img_id = upload_img(k['img_url'], k['img_file'])

    data = {
        "name": k['name'],
        "type": "simple",
        "regular_price": k['price'],
        "description": k['desc'],
        "short_description": k['short'],
        "categories": [{"id": kite_cat}] if kite_cat else [],
        "status": "publish",
    }
    if img_id:
        data["images"] = [{"id": img_id}]

    result = api("POST", "/wc/v3/products", data)
    if isinstance(result, dict) and 'id' in result:
        sys.stdout.buffer.write(f"OK (ID:{result['id']}, od {k['price']} zl)\n".encode('utf-8'))
    else:
        sys.stdout.buffer.write(f"ERR: {str(result)[:100]}\n".encode('utf-8'))

print("\nGOTOWE!")
