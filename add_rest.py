"""
Dodanie: Wings, Bar, Foil, Akcesoria
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

# Kategorie
print("=== KATEGORIE ===")
cat_ids = {}
for name in ["Wing Foil", "Bary i Trapeze", "Foile", "Akcesoria"]:
    result = api("POST", "/wc/v3/products/categories", {"name": name})
    if isinstance(result, dict) and 'id' in result:
        cat_ids[name] = result['id']
    elif isinstance(result, dict) and result.get('code') == 'term_exists':
        cat_ids[name] = result['data']['resource_id']
    print(f"  {name}: {cat_ids.get(name, 'ERR')}")

products = [
    # === WINGS ===
    {
        "name": "Cabrinha Mantis 2026",
        "price": "4249",
        "cat": "Wing Foil",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2025/06/cabrinha-mantis-wing-2025-cutout-zoom-768x768.jpg",
        "img_file": "cab-mantis-2026-cutout.jpg",
        "desc": (
            "Najbardziej stabilny i przyjazny wing w ofercie Cabrinhy. Generacja 2026 to "
            "najczystsza, najsztywniejsza i najlepiej wywa\u017cona wersja w historii tego modelu. "
            "High Rigidity LE i Low Dihedral daj\u0105 natychmiastow\u0105 reakcj\u0119 na wiatr i pewn\u0105 "
            "kontrol\u0119 mocy. Drop Strut Design zapewnia czysty profil i mniejszy opor.\n\n"
            "Idealny do: freeride, wave, nauka foilowania.\n"
            "W zestawie: composite boom handle, zestaw naprawczy, torba.\n\n"
            "Dost\u0119pne rozmiary: 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6 m\n"
            "Ceny od 4 249 z\u0142 do 5 449 z\u0142 w zale\u017cno\u015bci od rozmiaru.\n\n"
            "Przetestuj na wodzie \u2014 Jastarnia i Hurghada."
        ),
        "short": "Wing foil allround. Stabilny, sztywny, kontrolowany. Rozmiary: 2\u20136 m. Od 4 249 z\u0142.",
    },
    {
        "name": "Cabrinha Mantis Apex Aluula 2026",
        "price": "6199",
        "cat": "Wing Foil",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-mantis-apex-wing-2026-cutout-768x768.jpg",
        "img_file": "cab-mantis-apex-2026-cutout.jpg",
        "desc": (
            "Premiumowa wersja Mantisa z Aluula Composite \u2014 najl\u017cejszy wing w ofercie Cabrinhy. "
            "Wyj\u0105tkowa sztywno\u015b\u0107 przy minimalnej wadze daje fenomenalne czucie wiatru "
            "i natychmiastow\u0105 reakcj\u0119. Ka\u017cdy gram mniej to wi\u0119kszy komfort i d\u0142u\u017csze sesje.\n\n"
            "Idealny do: zaawansowany freeride, wave, downwind, racing.\n"
            "Materia\u0142y: Aluula Composite, premium canopy.\n\n"
            "Dost\u0119pne rozmiary: 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6 m\n"
            "Ceny od 6 199 z\u0142 do 7 199 z\u0142 w zale\u017cno\u015bci od rozmiaru.\n\n"
            "Przetestuj na wodzie \u2014 Jastarnia i Hurghada."
        ),
        "short": "Wing foil premium Aluula. Najl\u017cejszy, najsztywniejszy. Rozmiary: 2\u20136 m. Od 6 199 z\u0142.",
    },
    {
        "name": "Cabrinha AER 2 2026",
        "price": "3349",
        "cat": "Wing Foil",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinhaaerwing2026c1-768x768.jpg",
        "img_file": "cab-aer2-2026-cutout.jpg",
        "desc": (
            "Wing foil dla pocz\u0105tkuj\u0105cych i \u015brednio zaawansowanych. Stabilny, \u0142atwy "
            "w obs\u0142udze i wybaczaj\u0105cy b\u0142\u0119dy \u2014 idealny pierwszy wing. Nowa wersja AER 2 "
            "z ulepszonym profilem i lepszym zakresem wiatru. Przyst\u0119pna cena przy "
            "solidnej jako\u015bci wykonania.\n\n"
            "Idealny do: nauka wing foil, light wind, freeride.\n"
            "W zestawie: boom handle, torba, zestaw naprawczy.\n\n"
            "Dost\u0119pne rozmiary: 3, 3.5, 4, 4.5, 5, 5.5, 6 m\n"
            "Ceny od 3 349 z\u0142 do 4 119 z\u0142 w zale\u017cno\u015bci od rozmiaru.\n\n"
            "Przetestuj na wodzie \u2014 Jastarnia i Hurghada."
        ),
        "short": "Wing foil entry-level. Stabilny i wybaczaj\u0105cy. Rozmiary: 3\u20136 m. Od 3 349 z\u0142.",
    },
    {
        "name": "Cabrinha Vision 2026",
        "price": "4749",
        "cat": "Wing Foil",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinhavisionwing2026c1-768x768.jpg",
        "img_file": "cab-vision-2026-cutout.jpg",
        "desc": (
            "Wing do wave ridingu i zaawansowanego freeride. Kompaktowy profil, szybki zwrot "
            "i doskona\u0142y drift na fali. Vision to wing dla rider\u00f3w, kt\u00f3rzy chc\u0105 surfa\u0107 "
            "na foilu \u2014 precyzyjne sterowanie i natychmiastowa reakcja na ruchy nadgarstka.\n\n"
            "Idealny do: wave riding, strapless, surf foil.\n\n"
            "Dost\u0119pne rozmiary: 2.5, 3, 3.5, 4, 4.5, 5 m\n"
            "Ceny od 4 749 z\u0142 w zale\u017cno\u015bci od rozmiaru.\n\n"
            "Przetestuj na wodzie \u2014 Jastarnia i Hurghada."
        ),
        "short": "Wing foil wave/surf. Kompaktowy, szybki, precyzyjny. Rozmiary: 2.5\u20135 m. Od 4 749 z\u0142.",
    },
    # === BAR ===
    {
        "name": "Cabrinha Unify Control System 2026",
        "price": "2999",
        "cat": "Bary i Trapeze",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2025/09/shop-cabrinha-bars.jpg",
        "img_file": "cab-unify-bar-2026.jpg",
        "desc": (
            "Kompletnie przeprojektowany system kontroli na 2026 rok. Ergonomiczny bar "
            "z intuicyjnym systemem szybkiego odpi\u0119cia i regulacj\u0105 d\u0142ugo\u015bci linek. "
            "Kompatybilny ze wszystkimi latawcami Cabrinha.\n\n"
            "Nowo\u015bci 2026: uproszczona obs\u0142uga, lepszy komfort chwytu, "
            "szybsze i pewniejsze odpi\u0119cie bezpiecze\u0144stwa.\n\n"
            "Dost\u0119pne d\u0142ugo\u015bci linek: 20 m, 22 m, 24 m.\n\n"
            "Niezb\u0119dny element zestawu do ka\u017cdego latawca."
        ),
        "short": "Bar kontroli Unify 2026. Nowy design, lepszy komfort i bezpiecze\u0144stwo. Od 2 999 z\u0142.",
    },
    # === FOILE ===
    {
        "name": "Cabrinha H-Series 1000 Carbon Foil",
        "price": "4999",
        "cat": "Foile",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2025/09/shop-cabrinha-foils.jpg",
        "img_file": "cab-h-series-foil.jpg",
        "desc": (
            "Karbonowy foil z serii H \u2014 uniwersalny zestaw do kite i wing foilingu. "
            "Powierzchnia skrzyd\u0142a g\u0142\u00f3wnego 1000 cm\u00b2 \u2014 idealny balans mi\u0119dzy "
            "stabilno\u015bci\u0105 a pr\u0119dko\u015bci\u0105. Lekki, sztywny, responsywny.\n\n"
            "Modularny system \u2014 mo\u017cna wymienia\u0107 skrzyd\u0142a w zale\u017cno\u015bci od warunk\u00f3w.\n"
            "Idealny do: freeride, wave, nauka foilowania.\n\n"
            "W cenie: front wing, stabilizer, fuselage, mast. PROMOCJA!"
        ),
        "short": "Foil karbonowy 1000 cm\u00b2. Kompletny zestaw do kite i wing. Promocja: 4 999 z\u0142.",
    },
    {
        "name": "Cabrinha Prestige Foil Kit 2026",
        "price": "8999",
        "cat": "Foile",
        "img_url": "https://www.kingofwatersports.com/wp-content/uploads/2025/06/cabrinha-foil-alloy-top-plate-cutout-zoom-768x768.jpg",
        "img_file": "cab-prestige-foil.jpg",
        "desc": (
            "Topowy foil w ofercie Cabrinhy \u2014 Ultra High Aspect dla maksymalnej efektywno\u015bci "
            "i najd\u0142u\u017cszego glide. P\u0142ynne, intuicyjne skr\u0119ty, minimalne tarcie. "
            "Dla zaawansowanych rider\u00f3w szukaj\u0105cych perfekcji.\n\n"
            "Idealny do: downwind, racing, zaawansowany freeride, pump foil.\n"
            "Materia\u0142y: pe\u0142en karbon, premium wykonanie.\n\n"
            "W cenie: front wing Prestige, Union stabilizer, fuselage, mast."
        ),
        "short": "Foil Ultra High Aspect \u2014 top Cabrinhy. Max glide i efektywno\u015b\u0107. 8 999 z\u0142.",
    },
    # === AKCESORIA ===
    {
        "name": "Cabrinha Pompka XL",
        "price": "219",
        "cat": "Akcesoria",
        "img_url": "https://cabrinha.pl/wp-content/uploads/2025/11/Switchblade-C1.png",
        "img_file": "cab-pompka-xl.png",
        "desc": "Du\u017ca pompka do latawc\u00f3w kite i wing. Szybkie pompowanie dzi\u0119ki du\u017cej pojemno\u015bci cylindra. Trwa\u0142a konstrukcja, kompatybilna ze wszystkimi latawcami i wingami Cabrinha. Lekka i podr\u0119czna.",
        "short": "Pompka XL do latawc\u00f3w i wing\u00f3w. 219 z\u0142.",
    },
    {
        "name": "Cabrinha Kask ochronny",
        "price": "219",
        "cat": "Akcesoria",
        "img_url": "https://cabrinha.pl/wp-content/uploads/2025/11/Switchblade-C2.png",
        "img_file": "cab-kask.png",
        "desc": "Kask ochronny do kitesurfingu, wing foilingu i wakeboard. Lekki, wygodny, regulowany \u2014 dopasowuje si\u0119 do ka\u017cdej g\u0142owy. Niezb\u0119dne zabezpieczenie na wodzie, szczeg\u00f3lnie przy nauce foilowania.",
        "short": "Kask ochronny do sport\u00f3w wodnych. 219 z\u0142.",
    },
    {
        "name": "Cabrinha Source Pady i Strapy",
        "price": "699",
        "cat": "Akcesoria",
        "img_url": "https://cabrinha.pl/wp-content/uploads/2026/04/Cab_Ace_361161_8-scaled.jpg",
        "img_file": "cab-source-pady.jpg",
        "desc": "Pady i strapy Source do desek twin-tip. Wygodne, regulowane, trwa\u0142e. Pasuj\u0105 do wszystkich desek Cabrinha z monta\u017cem M6. \u0141atwy monta\u017c i demonta\u017c.",
        "short": "Pady i strapy do deski twin-tip. 699 z\u0142.",
    },
    {
        "name": "Cabrinha Leash Pro",
        "price": "129",
        "cat": "Akcesoria",
        "img_url": "https://cabrinha.pl/wp-content/uploads/2025/11/Switchblade-12-scaled.jpg",
        "img_file": "cab-leash-pro.jpg",
        "desc": "Profesjonalny leash do kite \u2014 d\u0142ugi model z elastycznym rdzeniem. Bezpieczny, pewny, obowi\u0105zkowy element wyposazzenia ka\u017cdego kitera. Dzi\u0119ki elastyczno\u015bci nie ogranicza ruch\u00f3w podczas jazdy.",
        "short": "Leash do kite, d\u0142ugi, elastyczny. 129 z\u0142.",
    },
    {
        "name": "Cabrinha Golf Bag 140 cm",
        "price": "699",
        "cat": "Akcesoria",
        "img_url": "https://cabrinha.pl/wp-content/uploads/2026/04/Cab_Ace_361161_9-scaled.jpg",
        "img_file": "cab-golf-bag.jpg",
        "desc": "Pokrowiec na latawce typu golf bag \u2014 mie\u015bci 2-3 latawce, bar i akcesoria. K\u00f3\u0142ka do transportu, wytrzyma\u0142y materia\u0142, wygodne r\u0105czki. Idealny na podr\u00f3\u017c do Egiptu!",
        "short": "Pokrowiec golf bag na latawce 140 cm. 699 z\u0142.",
    },
]

print("\n=== DODAJE PRODUKTY ===")
for p in products:
    sys.stdout.buffer.write(f"  {p['name']}... ".encode('utf-8'))
    img_id = upload_img(p['img_url'], p['img_file'])

    cats = [{"id": cat_ids[p['cat']]}] if p['cat'] in cat_ids else []
    data = {
        "name": p['name'],
        "type": "simple",
        "regular_price": p['price'],
        "description": p['desc'],
        "short_description": p['short'],
        "categories": cats,
        "status": "publish",
    }
    if img_id:
        data["images"] = [{"id": img_id}]

    result = api("POST", "/wc/v3/products", data)
    if isinstance(result, dict) and 'id' in result:
        sys.stdout.buffer.write(f"OK (ID:{result['id']}, {p['price']} zl)\n".encode('utf-8'))
    else:
        sys.stdout.buffer.write(f"ERR: {str(result)[:80]}\n".encode('utf-8'))

print("\nGOTOWE!")
