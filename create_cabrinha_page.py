"""
Tworzy strone Cabrinha 2026 - kolekcja, opis baz, zaproszenie do sklepu
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
        if 'id' in d:
            return d['id'], d['source_url']
    except:
        pass
    return None, None

# =====================================================
# Pobierz zdjecia kolekcji 2026 z kingofwatersports
# =====================================================
print("\n=== POBIERAM ZDJECIA KOLEKCJI ===")

images_to_fetch = [
    ("https://www.kingofwatersports.com/wp-content/uploads/2025/11/cab26blog.png", "cabrinha-2026-banner.png"),
    ("https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-2026-vapor-twintip-cutout-768x768.jpg", "cabrinha-2026-vapor.jpg"),
    ("https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinhaaerwing2026c1-768x768.jpg", "cabrinha-2026-aer-wing.jpg"),
    ("https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-skillit-surfboard-2026-cutout-768x768.jpg", "cabrinha-2026-skillit.jpg"),
    ("https://www.kingofwatersports.com/wp-content/uploads/2026/03/cabrinha-logic-foil-board-2026-cutout-768x768.jpg", "cabrinha-2026-logic.jpg"),
]

uploaded = {}
for url, fname in images_to_fetch:
    img_id, img_url = upload_img(url, fname)
    if img_id:
        uploaded[fname] = img_url
        print(f"  OK: {fname} (ID:{img_id})")
    else:
        print(f"  ERR: {fname}")

# Fallback URLs
banner_url = uploaded.get("cabrinha-2026-banner.png", "https://funlikehel.pl/wp-content/uploads/2026/04/IMG_5278-scaled.jpg")
vapor_url = uploaded.get("cabrinha-2026-vapor.jpg", "")
aer_url = uploaded.get("cabrinha-2026-aer-wing.jpg", "")
skillit_url = uploaded.get("cabrinha-2026-skillit.jpg", "")
logic_url = uploaded.get("cabrinha-2026-logic.jpg", "")

# =====================================================
# Tworz strone Cabrinha
# =====================================================
print("\n=== TWORZE STRONE CABRINHA ===")

# Uzyj istniejacych zdjec Cabrinha z Drive
cabrinha_img_5278 = "https://funlikehel.pl/wp-content/uploads/2026/04/IMG_5278-scaled.jpg"
cabrinha_img_5051 = "https://funlikehel.pl/wp-content/uploads/2026/04/IMG_5051-scaled.jpg"
cabrinha_img_5292 = "https://funlikehel.pl/wp-content/uploads/2026/04/IMG_5292-scaled.jpg"

content = f"""<!-- wp:cover {{"url":"{cabrinha_img_5278}","dimRatio":50,"minHeight":500,"minHeightUnit":"px","align":"full"}} -->
<div class="wp-block-cover alignfull" style="min-height:500px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim"></span><img class="wp-block-cover__image-background" alt="Cabrinha Test Center FUN like HEL" src="{cabrinha_img_5278}" data-object-fit="cover"/><div class="wp-block-cover__inner-container"><!-- wp:heading {{"textAlign":"center","level":1,"style":{{"color":{{"text":"#ffffff"}},"typography":{{"fontSize":"48px"}}}}}} -->
<h1 class="wp-block-heading has-text-align-center" style="color:#ffffff;font-size:48px">Cabrinha 2026 \u2014 Oficjalne Centrum Testowe</h1>
<!-- /wp:heading -->
<!-- wp:paragraph {{"align":"center","style":{{"color":{{"text":"#ffffff"}},"typography":{{"fontSize":"20px"}}}}}} -->
<p class="has-text-align-center" style="color:#ffffff;font-size:20px">FUN like HEL to jedyne w Polsce oficjalne Cabrinha Test Center.<br>Przetestuj najnowszy sprz\u0119t 2026 na wodzie zanim kupisz.</p>
<!-- /wp:paragraph --></div></div>
<!-- /wp:cover -->

<!-- wp:group {{"align":"full","style":{{"spacing":{{"padding":{{"top":"60px","bottom":"60px"}}}}}}}} -->
<div class="wp-block-group alignfull" style="padding-top:60px;padding-bottom:60px"><!-- wp:columns {{"align":"wide"}} -->
<div class="wp-block-columns alignwide"><!-- wp:column {{"style":{{"color":{{"background":"#e3f2fd"}},"spacing":{{"padding":{{"top":"30px","bottom":"30px","left":"25px","right":"25px"}}}}}}}} -->
<div class="wp-block-column" style="background-color:#e3f2fd;padding:30px 25px"><!-- wp:heading {{"textAlign":"center","level":3}} --><h3 class="wp-block-heading has-text-align-center">\ud83c\uddf5\ud83c\uddf1 Baza Polska \u2014 Jastarnia</h3><!-- /wp:heading -->
<!-- wp:paragraph {{"align":"center"}} --><p class="has-text-align-center">Kemping Sun4Hel, P\u00f3\u0142wysep Helski<br>100 m od morza, 20 m od Zatoki Puckiej<br>Sezon: <strong>maj \u2013 wrzesie\u0144</strong><br><br>Ca\u0142y sprz\u0119t Cabrinha 2026 dost\u0119pny do test\u00f3w na p\u0142ytkiej Zatoce Puckiej \u2014 idealnej do nauki i jazdy.</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column {{"style":{{"color":{{"background":"#fff8e1"}},"spacing":{{"padding":{{"top":"30px","bottom":"30px","left":"25px","right":"25px"}}}}}}}} -->
<div class="wp-block-column" style="background-color:#fff8e1;padding:30px 25px"><!-- wp:heading {{"textAlign":"center","level":3}} --><h3 class="wp-block-heading has-text-align-center">\ud83c\uddea\ud83c\uddec Baza Egipt \u2014 Hurghada</h3><!-- /wp:heading -->
<!-- wp:paragraph {{"align":"center"}} --><p class="has-text-align-center">FUNLIKEHEL EGYPT \u2014 Cabrinha Test Center<br>P\u00f3\u0142nocna Hurghada, przy spocie kite<br>Sezon: <strong>ca\u0142y rok</strong><br><br>300 dni wiatru, ciep\u0142a p\u0142ytka woda. Przetestuj sprz\u0119t w wymarzonych warunkach \u2014 bez pianki!</p><!-- /wp:paragraph --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->

<!-- wp:group {{"align":"full","style":{{"spacing":{{"padding":{{"top":"60px","bottom":"60px"}}}},"color":{{"background":"#1a1a1a"}}}}}} -->
<div class="wp-block-group alignfull" style="background-color:#1a1a1a;padding-top:60px;padding-bottom:60px"><!-- wp:heading {{"textAlign":"center","level":2,"style":{{"color":{{"text":"#ffffff"}},"typography":{{"fontSize":"36px"}}}}}} -->
<h2 class="wp-block-heading has-text-align-center" style="color:#ffffff;font-size:36px">Kolekcja Cabrinha 2026</h2>
<!-- /wp:heading -->
<!-- wp:paragraph {{"align":"center","style":{{"color":{{"text":"#cccccc"}}}}}} -->
<p class="has-text-align-center" style="color:#cccccc">Najnowsza generacja sprz\u0119tu kite, wing i foil. Ka\u017cdy produkt mo\u017cesz przetestowa\u0107 u nas na wodzie.</p>
<!-- /wp:paragraph -->

<!-- wp:heading {{"level":3,"style":{{"color":{{"text":"#4fc3f7"}},"spacing":{{"margin":{{"top":"50px"}}}}}}}} -->
<h3 class="wp-block-heading" style="color:#4fc3f7;margin-top:50px">\ud83e\ude81 Latawce (Kites)</h3>
<!-- /wp:heading -->

<!-- wp:columns {{"style":{{"spacing":{{"blockGap":"20px"}}}}}} -->
<div class="wp-block-columns"><!-- wp:column -->
<div class="wp-block-column"><!-- wp:heading {{"level":4,"style":{{"color":{{"text":"#ffffff"}}}}}} --><h4 class="wp-block-heading" style="color:#ffffff">Switchblade Apex 2026</h4><!-- /wp:heading -->
<!-- wp:paragraph {{"style":{{"color":{{"text":"#cccccc"}},"typography":{{"fontSize":"14px"}}}}}} --><p style="color:#cccccc;font-size:14px">5-Strut | Hybrid Design | Fusion Wing Tips. Najbardziej wszechstronny latawiec Cabrinhy \u2014 freeride, big air, wave. Nowa konstrukcja draft-forward, lepsza stabilno\u015b\u0107 w porywach, pot\u0119\u017cny pop. Rozmiary: 5-14 m\u00b2.</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:heading {{"level":4,"style":{{"color":{{"text":"#ffffff"}}}}}} --><h4 class="wp-block-heading" style="color:#ffffff">Drifter Apex 2026</h4><!-- /wp:heading -->
<!-- wp:paragraph {{"style":{{"color":{{"text":"#cccccc"}},"typography":{{"fontSize":"14px"}}}}}} --><p style="color:#cccccc;font-size:14px">3-Strut | Surf/Drift Wing Tips. Ikoniczny latawiec surfowy \u2014 lepszy drift, bardziej bezpo\u015brednie sterowanie. Benchmark do jazdy wave i down-the-line. Rozmiary: 5-12 m\u00b2.</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:heading {{"level":4,"style":{{"color":{{"text":"#ffffff"}}}}}} --><h4 class="wp-block-heading" style="color:#ffffff">Nitro Apex 2026</h4><!-- /wp:heading -->
<!-- wp:paragraph {{"style":{{"color":{{"text":"#cccccc"}},"typography":{{"fontSize":"14px"}}}}}} --><p style="color:#cccccc;font-size:14px">5-Strut | High Aspect | High Sweep. Bro\u0144 na big air \u2014 maksymalny lift, stabilno\u015b\u0107 i hang time. Ulepszona wersja 2026 z jeszcze lepszym zasysaniem. Rozmiary: 7-12 m\u00b2.</p><!-- /wp:paragraph --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->

<!-- wp:heading {{"level":3,"style":{{"color":{{"text":"#4fc3f7"}},"spacing":{{"margin":{{"top":"50px"}}}}}}}} -->
<h3 class="wp-block-heading" style="color:#4fc3f7;margin-top:50px">\ud83c\udfc4 Deski (Boards)</h3>
<!-- /wp:heading -->

<!-- wp:columns {{"style":{{"spacing":{{"blockGap":"20px"}}}}}} -->
<div class="wp-block-columns"><!-- wp:column -->
<div class="wp-block-column"><!-- wp:heading {{"level":4,"style":{{"color":{{"text":"#ffffff"}}}}}} --><h4 class="wp-block-heading" style="color:#ffffff">ACE / ACE Apex 2026</h4><!-- /wp:heading -->
<!-- wp:paragraph {{"style":{{"color":{{"text":"#cccccc"}},"typography":{{"fontSize":"14px"}}}}}} --><p style="color:#cccccc;font-size:14px">Wszechstronna twin-tip freeride/freestyle. Rdze\u0144 Paulownia, double concave, \u015bwietna kontrola kraw\u0119dzi. Wersja Apex z premium materia\u0142ami.</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:heading {{"level":4,"style":{{"color":{{"text":"#ffffff"}}}}}} --><h4 class="wp-block-heading" style="color:#ffffff">Vapor / Vapor Apex 2026</h4><!-- /wp:heading -->
<!-- wp:paragraph {{"style":{{"color":{{"text":"#cccccc"}},"typography":{{"fontSize":"14px"}}}}}} --><p style="color:#cccccc;font-size:14px">Deska big air/freestyle. Agresywny flex, progresywny rocker, pot\u0119\u017cny pop. Dla riderow szukaj\u0105cych powietrza.</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:heading {{"level":4,"style":{{"color":{{"text":"#ffffff"}}}}}} --><h4 class="wp-block-heading" style="color:#ffffff">Spectrum / Skillit / Stylus</h4><!-- /wp:heading -->
<!-- wp:paragraph {{"style":{{"color":{{"text":"#cccccc"}},"typography":{{"fontSize":"14px"}}}}}} --><p style="color:#cccccc;font-size:14px">Spectrum \u2014 idealna na start. Skillit \u2014 deska surfowa do wave. Stylus \u2014 wszechstronny kompromis mi\u0119dzy freeride a freestyle.</p><!-- /wp:paragraph --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->

<!-- wp:heading {{"level":3,"style":{{"color":{{"text":"#4fc3f7"}},"spacing":{{"margin":{{"top":"50px"}}}}}}}} -->
<h3 class="wp-block-heading" style="color:#4fc3f7;margin-top:50px">\ud83e\udeb6 Wing Foil</h3>
<!-- /wp:heading -->

<!-- wp:columns {{"style":{{"spacing":{{"blockGap":"20px"}}}}}} -->
<div class="wp-block-columns"><!-- wp:column -->
<div class="wp-block-column"><!-- wp:heading {{"level":4,"style":{{"color":{{"text":"#ffffff"}}}}}} --><h4 class="wp-block-heading" style="color:#ffffff">Mantis / Mantis Apex 2026</h4><!-- /wp:heading -->
<!-- wp:paragraph {{"style":{{"color":{{"text":"#cccccc"}},"typography":{{"fontSize":"14px"}}}}}} --><p style="color:#cccccc;font-size:14px">Najbardziej stabilny i przyjazny wing Cabrinhy. 2026 to najczystsza, najsztywniejsza wersja. Apex z Aluula Composite \u2014 ultralight. Low Dihedral, High Rigidity LE.</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:heading {{"level":4,"style":{{"color":{{"text":"#ffffff"}}}}}} --><h4 class="wp-block-heading" style="color:#ffffff">AER 2 2026</h4><!-- /wp:heading -->
<!-- wp:paragraph {{"style":{{"color":{{"text":"#cccccc"}},"typography":{{"fontSize":"14px"}}}}}} --><p style="color:#cccccc;font-size:14px">Entry-level wing idealny do nauki. Stabilny, wybaczaj\u0105cy b\u0142\u0119dy, przyst\u0119pna cena. Twoj pierwszy wing do foilowania.</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:heading {{"level":4,"style":{{"color":{{"text":"#ffffff"}}}}}} --><h4 class="wp-block-heading" style="color:#ffffff">Foile: Logic / H-Series / Prestige</h4><!-- /wp:heading -->
<!-- wp:paragraph {{"style":{{"color":{{"text":"#cccccc"}},"typography":{{"fontSize":"14px"}}}}}} --><p style="color:#cccccc;font-size:14px">Karbonowe foile modularnego systemu. Logic \u2014 wszechstronny. H-Series \u2014 freeride i wave. Prestige \u2014 ultra high aspect, max glide i efektywno\u015b\u0107.</p><!-- /wp:paragraph --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->

<!-- wp:image {{"align":"full","sizeSlug":"full"}} -->
<figure class="wp-block-image alignfull size-full"><img src="{banner_url}" alt="Cabrinha 2026 kolekcja"/></figure>
<!-- /wp:image -->

<!-- wp:group {{"align":"full","style":{{"spacing":{{"padding":{{"top":"60px","bottom":"60px"}}}},"color":{{"background":"#e8f4f8"}}}}}} -->
<div class="wp-block-group alignfull" style="background-color:#e8f4f8;padding-top:60px;padding-bottom:60px"><!-- wp:heading {{"textAlign":"center","level":2}} -->
<h2 class="wp-block-heading has-text-align-center">Dlaczego Cabrinha Test Center?</h2>
<!-- /wp:heading -->
<!-- wp:columns {{"align":"wide"}} -->
<div class="wp-block-columns alignwide"><!-- wp:column {{"textAlign":"center"}} -->
<div class="wp-block-column has-text-align-center"><!-- wp:paragraph {{"style":{{"typography":{{"fontSize":"36px"}}}}}} --><p style="font-size:36px">\ud83c\udfc4</p><!-- /wp:paragraph -->
<!-- wp:heading {{"textAlign":"center","level":4}} --><h4 class="wp-block-heading has-text-align-center">Testuj na wodzie</h4><!-- /wp:heading -->
<!-- wp:paragraph {{"align":"center"}} --><p class="has-text-align-center">Ka\u017cdy latawiec, desk\u0119 i winga z kolekcji 2026 mo\u017cesz wypr\u00f3bowa\u0107 w realnych warunkach \u2014 na Zatoce Puckiej lub w Hurghadzie.</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column {{"textAlign":"center"}} -->
<div class="wp-block-column has-text-align-center"><!-- wp:paragraph {{"style":{{"typography":{{"fontSize":"36px"}}}}}} --><p style="font-size:36px">\ud83d\udcac</p><!-- /wp:paragraph -->
<!-- wp:heading {{"textAlign":"center","level":4}} --><h4 class="wp-block-heading has-text-align-center">Doradztwo eksperta</h4><!-- /wp:heading -->
<!-- wp:paragraph {{"align":"center"}} --><p class="has-text-align-center">Nasi instruktorzy znaj\u0105 ka\u017cdy model od podszewki. Doradzimy jaki sprz\u0119t pasuje do Twojego poziomu i stylu jazdy.</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column {{"textAlign":"center"}} -->
<div class="wp-block-column has-text-align-center"><!-- wp:paragraph {{"style":{{"typography":{{"fontSize":"36px"}}}}}} --><p style="font-size:36px">\ud83d\udcb0</p><!-- /wp:paragraph -->
<!-- wp:heading {{"textAlign":"center","level":4}} --><h4 class="wp-block-heading has-text-align-center">Najlepsze ceny</h4><!-- /wp:heading -->
<!-- wp:paragraph {{"align":"center"}} --><p class="has-text-align-center">Jako oficjalny Test Center oferujemy pe\u0142n\u0105 gam\u0119 w cenach producenta. Bez po\u015brednik\u00f3w.</p><!-- /wp:paragraph --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->

<!-- wp:group {{"align":"full","style":{{"spacing":{{"padding":{{"top":"60px","bottom":"60px"}}}}}}}} -->
<div class="wp-block-group alignfull" style="padding-top:60px;padding-bottom:60px"><!-- wp:heading {{"textAlign":"center","level":2}} -->
<h2 class="wp-block-heading has-text-align-center">Sprawd\u017a nasz sklep</h2>
<!-- /wp:heading -->
<!-- wp:paragraph {{"align":"center","style":{{"typography":{{"fontSize":"18px"}}}}}} -->
<p class="has-text-align-center" style="font-size:18px">Pe\u0142na oferta Cabrinha 2026 dost\u0119pna online i stacjonarnie w naszych bazach.</p>
<!-- /wp:paragraph -->
<!-- wp:buttons {{"layout":{{"type":"flex","justifyContent":"center"}},"style":{{"spacing":{{"margin":{{"top":"30px"}}}}}}}} -->
<div class="wp-block-buttons"><!-- wp:button {{"style":{{"typography":{{"fontSize":"20px"}},"spacing":{{"padding":{{"top":"16px","bottom":"16px","left":"40px","right":"40px"}}}}}}}} -->
<div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="https://funlikehel.pl/sklep/" style="font-size:20px;padding:16px 40px">Przejd\u017a do sklepu Aquashop</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons -->
<!-- wp:paragraph {{"align":"center","style":{{"typography":{{"fontSize":"16px"}}}}}} -->
<p class="has-text-align-center" style="font-size:16px">Masz pytania o sprz\u0119t? Zadzwo\u0144: <a href="tel:690270032"><strong>690 270 032</strong></a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->"""

result = api("POST", "/wp/v2/pages", {
    "title": "Cabrinha 2026 \u2014 Test Center",
    "slug": "cabrinha",
    "content": content,
    "status": "publish",
    "parent": 0,
    "meta": {
        "_yoast_wpseo_title": "Cabrinha 2026 Test Center | FUN like HEL \u2014 Jastarnia i Hurghada",
        "_yoast_wpseo_metadesc": "Oficjalne Cabrinha Test Center w Polsce i Egipcie. Przetestuj kolekcj\u0119 2026 na wodzie: latawce, deski, wing foil. Aquashop FUN like HEL."
    }
})
if isinstance(result, dict) and 'id' in result:
    page_id = result['id']
    print(f"  OK: Strona Cabrinha (ID:{page_id}, link: {result['link']})")
else:
    print(f"  ERR: {str(result)[:200]}")
    sys.exit(1)

# =====================================================
# Dodaj do menu + nawigacji FSE
# =====================================================
print("\n=== DODAJE DO MENU ===")

# Menu tradycyjne
result = api("POST", "/wp/v2/menu-items", {
    "title": "Cabrinha", "type": "post_type", "object": "page",
    "object_id": page_id,
    "url": f"https://funlikehel.pl/cabrinha/",
    "menus": 22, "menu_order": 3, "parent": 0, "status": "publish"
})
if isinstance(result, dict) and 'id' in result:
    print(f"  OK: Menu item Cabrinha")

# Przesun Sklep i Kontakt
items = api("GET", "/wp/v2/menu-items&menus=22&per_page=20")
if isinstance(items, list):
    for item in items:
        title = item['title']['rendered']
        if title == 'Obozy i Kolonie':
            api("POST", f"/wp/v2/menu-items/{item['id']}", {"menu_order": 4})
        elif title == 'Sklep':
            api("POST", f"/wp/v2/menu-items/{item['id']}", {"menu_order": 5})
        elif title == 'Kontakt':
            api("POST", f"/wp/v2/menu-items/{item['id']}", {"menu_order": 6})

# Nawigacja FSE
nav_content = (
    '<!-- wp:navigation-link {"label":"Oferta","type":"page","id":2033,"url":"https://funlikehel.pl/oferta/","kind":"post-type","isTopLevelLink":true} /-->'
    '\n<!-- wp:navigation-link {"label":"Egipt","type":"page","id":2044,"url":"https://funlikehel.pl/egipt-hurghada/","kind":"post-type","isTopLevelLink":true} /-->'
    f'\n<!-- wp:navigation-link {{"label":"Cabrinha","type":"page","id":{page_id},"url":"https://funlikehel.pl/cabrinha/","kind":"post-type","isTopLevelLink":true}} /-->'
    '\n<!-- wp:navigation-link {"label":"Obozy i Kolonie","type":"page","id":2037,"url":"https://funlikehel.pl/obozy-kolonie/","kind":"post-type","isTopLevelLink":true} /-->'
    '\n<!-- wp:navigation-link {"label":"Sklep","type":"page","id":2040,"url":"https://funlikehel.pl/sklep/","kind":"post-type","isTopLevelLink":true} /-->'
    '\n<!-- wp:navigation-link {"label":"Kontakt","type":"page","id":2042,"url":"https://funlikehel.pl/kontakt/","kind":"post-type","isTopLevelLink":true} /-->'
)
result = api("POST", "/wp/v2/navigation/6", {"content": nav_content, "status": "publish"})
if isinstance(result, dict) and 'id' in result:
    print("  OK: Nawigacja FSE zaktualizowana")

print("\n=== GOTOWE ===")
