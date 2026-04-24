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

# 1. Stworz strone Jastarnia
print("\n=== TWORZE STRONE JASTARNIA ===")
jastarnia_content = (
    '<!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/10/kemping2.png","dimRatio":50,"minHeight":500,"minHeightUnit":"px","align":"full"} -->'
    '<div class="wp-block-cover alignfull" style="min-height:500px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim"></span>'
    '<img class="wp-block-cover__image-background" alt="Jastarnia FUN like HEL" src="https://funlikehel.pl/wp-content/uploads/2025/10/kemping2.png" data-object-fit="cover"/>'
    '<div class="wp-block-cover__inner-container">'
    '<!-- wp:heading {"textAlign":"center","level":1,"style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"48px"}}} -->'
    '<h1 class="wp-block-heading has-text-align-center" style="color:#ffffff;font-size:48px">Jastarnia \u2014 P\u00f3\u0142wysep Helski</h1>'
    '<!-- /wp:heading -->'
    '<!-- wp:paragraph {"align":"center","style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"20px"}}} -->'
    '<p class="has-text-align-center" style="color:#ffffff;font-size:20px">Kemping Sun4Hel \u2014 100 m od morza, 20 m od Zatoki Puckiej. Sezon: maj\u2013wrzesie\u0144.</p>'
    '<!-- /wp:paragraph --></div></div><!-- /wp:cover -->'

    '<!-- wp:group {"style":{"spacing":{"padding":{"top":"50px","bottom":"50px"}}}} -->'
    '<div class="wp-block-group" style="padding-top:50px;padding-bottom:50px">'

    '<!-- wp:heading {"level":2} --><h2 class="wp-block-heading">Dlaczego Jastarnia?</h2><!-- /wp:heading -->'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li><strong>Zatoka Pucka</strong> \u2014 p\u0142ytka woda na setki metr\u00f3w, idealna do nauki kite i windsurf</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>100 m do morza</strong> \u2014 fale, wave riding, surfing po drugiej stronie</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>Sta\u0142y wiatr</strong> \u2014 termiczny wiatr od maja do wrze\u015bnia, 15\u201325 w\u0119z\u0142\u00f3w</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>Cabrinha Test Center</strong> \u2014 testuj najnowszy sprz\u0119t 2026 na wodzie</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>300+ miejsc noclegowych</strong> \u2014 pawilony, sto\u0142\u00f3wka, pe\u0142na infrastruktura</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>Aquashop</strong> \u2014 sklep Cabrinha, Prolimit, Nobile na miejscu</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list -->'

    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Sporty dost\u0119pne w Jastarni</h2><!-- /wp:heading -->'
    '<!-- wp:columns --><div class="wp-block-columns">'
    '<!-- wp:column --><div class="wp-block-column"><!-- wp:list --><ul>'
    '<!-- wp:list-item --><li>Kitesurfing</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Windsurfing</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Wing foil</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Pumpfoil</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list --></div><!-- /wp:column -->'
    '<!-- wp:column --><div class="wp-block-column"><!-- wp:list --><ul>'
    '<!-- wp:list-item --><li>SUP</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Wakeboarding</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Deskorolka</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Yoga</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list --></div><!-- /wp:column -->'
    '</div><!-- /wp:columns -->'

    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Nocleg \u2014 Kemping Sun4Hel</h2><!-- /wp:heading -->'
    '<!-- wp:paragraph --><p>Ponad <strong>300 miejsc noclegowych</strong> na terenie kempingu. '
    'Pawilony mieszkalne (15 m\u00b2): 2 pi\u0119trowe \u0142\u00f3\u017cka z po\u015bciel\u0105, '
    'lod\u00f3wka, stolik z krzes\u0142ami, szafa, grzejnik. Sto\u0142\u00f3wka i jadalnia na miejscu.</p><!-- /wp:paragraph -->'

    '<!-- wp:gallery {"columns":3,"align":"wide"} -->'
    '<figure class="wp-block-gallery alignwide has-nested-images columns-3">'
    '<!-- wp:image {"id":1842} --><figure class="wp-block-image"><img src="https://funlikehel.pl/wp-content/uploads/2025/10/kemping2.png" alt="Kemping Sun4Hel" class="wp-image-1842"/></figure><!-- /wp:image -->'
    '<!-- wp:image {"id":1841} --><figure class="wp-block-image"><img src="https://funlikehel.pl/wp-content/uploads/2025/10/kemping3.png" alt="Kemping Sun4Hel" class="wp-image-1841"/></figure><!-- /wp:image -->'
    '<!-- wp:image {"id":1840} --><figure class="wp-block-image"><img src="https://funlikehel.pl/wp-content/uploads/2025/10/kemping4.png" alt="Kemping Sun4Hel" class="wp-image-1840"/></figure><!-- /wp:image -->'
    '</figure><!-- /wp:gallery -->'

    '<!-- wp:group {"style":{"spacing":{"padding":{"top":"40px","bottom":"40px"}},"color":{"background":"#e8f4f8"}}} -->'
    '<div class="wp-block-group" style="background-color:#e8f4f8;padding-top:40px;padding-bottom:40px">'
    '<!-- wp:paragraph {"align":"center","style":{"typography":{"fontSize":"20px"}}} -->'
    '<p class="has-text-align-center" style="font-size:20px">\ud83d\udcde <strong>Zarezerwuj:</strong> '
    '<a href="tel:690270032">690 270 032</a> &nbsp;|&nbsp; \u2709\ufe0f '
    '<a href="mailto:funlikehelbrand@gmail.com">funlikehelbrand@gmail.com</a></p>'
    '<!-- /wp:paragraph --></div><!-- /wp:group -->'
    '</div><!-- /wp:group -->'
)

result = api("POST", "/wp/v2/pages", {
    "title": "Jastarnia \u2014 P\u00f3\u0142wysep Helski",
    "slug": "jastarnia",
    "content": jastarnia_content,
    "status": "publish",
    "parent": 0
})
jastarnia_id = None
if isinstance(result, dict) and 'id' in result:
    jastarnia_id = result['id']
    print(f"  OK: Jastarnia (ID:{jastarnia_id})")
else:
    print(f"  ERR: {str(result)[:200]}")
    sys.exit(1)

# 2. Aktualizuj menu
print("\n=== AKTUALIZUJE MENU ===")
items = api("GET", "/wp/v2/menu-items&menus=22&per_page=20")
if isinstance(items, list):
    for item in items:
        title = item['title']['rendered']
        mid = item['id']
        obj_id = item.get('object_id', 0)
        if obj_id == 2044 or 'Egipt' in title:
            api("POST", f"/wp/v2/menu-items/{mid}", {"title": "Egipt-Hurghada"})
            print(f"  Zmieniono: {title} -> Egipt-Hurghada")

# Dodaj Jastarnia
result = api("POST", "/wp/v2/menu-items", {
    "title": "Jastarnia", "type": "post_type", "object": "page",
    "object_id": jastarnia_id,
    "url": f"https://funlikehel.pl/jastarnia/",
    "menus": 22, "menu_order": 2, "parent": 0, "status": "publish"
})
if isinstance(result, dict) and 'id' in result:
    print("  Dodano: Jastarnia")

# Ustaw kolejnosc
items2 = api("GET", "/wp/v2/menu-items&menus=22&per_page=20")
if isinstance(items2, list):
    for item in items2:
        t = item['title']['rendered']
        mid = item['id']
        order = None
        if t == 'Oferta': order = 1
        elif t == 'Jastarnia': order = 2
        elif 'Egipt' in t: order = 3
        elif t == 'Cabrinha': order = 4
        elif t == 'Obozy i Kolonie': order = 5
        elif t == 'Sklep': order = 6
        elif t == 'Kontakt': order = 7
        if order:
            api("POST", f"/wp/v2/menu-items/{mid}", {"menu_order": order})

# 3. Nawigacja FSE
print("\n=== NAWIGACJA FSE ===")
nav_content = '\n'.join([
    '<!-- wp:navigation-link {"label":"Oferta","type":"page","id":2033,"url":"https://funlikehel.pl/oferta/","kind":"post-type","isTopLevelLink":true} /-->',
    f'<!-- wp:navigation-link {{"label":"Jastarnia","type":"page","id":{jastarnia_id},"url":"https://funlikehel.pl/jastarnia/","kind":"post-type","isTopLevelLink":true}} /-->',
    '<!-- wp:navigation-link {"label":"Egipt-Hurghada","type":"page","id":2044,"url":"https://funlikehel.pl/egipt-hurghada/","kind":"post-type","isTopLevelLink":true} /-->',
    '<!-- wp:navigation-link {"label":"Cabrinha","type":"page","id":2158,"url":"https://funlikehel.pl/cabrinha/","kind":"post-type","isTopLevelLink":true} /-->',
    '<!-- wp:navigation-link {"label":"Obozy i Kolonie","type":"page","id":2037,"url":"https://funlikehel.pl/obozy-kolonie/","kind":"post-type","isTopLevelLink":true} /-->',
    '<!-- wp:navigation-link {"label":"Sklep","type":"page","id":2040,"url":"https://funlikehel.pl/sklep/","kind":"post-type","isTopLevelLink":true} /-->',
    '<!-- wp:navigation-link {"label":"Kontakt","type":"page","id":2042,"url":"https://funlikehel.pl/kontakt/","kind":"post-type","isTopLevelLink":true} /-->',
])
result = api("POST", "/wp/v2/navigation/6", {"content": nav_content, "status": "publish"})
if isinstance(result, dict) and 'id' in result:
    print("  OK")

print("\nGOTOWE!")
