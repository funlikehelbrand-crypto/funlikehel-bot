"""
Przebudowa strony FUN like HEL:
1. Wyczysc menu do 5 pozycji
2. Ukryj puste strony
3. Zbuduj jakosciowa tresc na kluczowych stronach
"""
import subprocess, json, sys, os

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

# =====================================================
# KROK 1: Wyczysc CALE menu i zbuduj od nowa
# =====================================================
print("\n=== CZYSZCZE MENU ===")
items = api("GET", "/wp/v2/menu-items&menus=22&per_page=100")
if isinstance(items, list):
    for item in items:
        api("DELETE", f"/wp/v2/menu-items/{item['id']}&force=true")
        print(f"  Usunieto: {item['title']['rendered']}")

# =====================================================
# KROK 2: Ukryj puste strony (draft)
# =====================================================
print("\n=== UKRYWAM PUSTE STRONY ===")
hide_ids = [2034, 2035, 2036, 2041]  # Windsurfing, Wing/SUP, Wakeboarding, Galeria (osobne)
for pid in hide_ids:
    result = api("POST", f"/wp/v2/pages/{pid}", {"status": "draft"})
    if isinstance(result, dict) and 'id' in result:
        print(f"  Draft: {result['title']['rendered']}")

# =====================================================
# KROK 3: Buduj tresc OFERTA (page 2033 - Kitesurfing -> przerobka na Oferta)
# =====================================================
print("\n=== BUDUJE STRONE: OFERTA ===")

oferta_content = """<!-- wp:heading {"level":1,"style":{"typography":{"fontSize":"42px"}}} -->
<h1 class="wp-block-heading" style="font-size:42px">Nasza oferta \u2014 sporty wodne dla ka\u017cdego</h1>
<!-- /wp:heading -->

<!-- wp:paragraph {"style":{"typography":{"fontSize":"18px"}}} -->
<p style="font-size:18px">Szkolimy od zera do zaawansowanych. Ka\u017cdy sport, ka\u017cdy poziom, ca\u0142y rok \u2014 latem w Jastarni, zim\u0105 w Hurghadzie.</p>
<!-- /wp:paragraph -->

<!-- wp:columns {"align":"wide","style":{"spacing":{"blockGap":"30px","margin":{"top":"40px"}}}} -->
<div class="wp-block-columns alignwide"><!-- wp:column -->
<div class="wp-block-column"><!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/07/kite.png","id":1645,"dimRatio":30,"minHeight":250,"minHeightUnit":"px"} -->
<div class="wp-block-cover" style="min-height:250px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim has-background-dim-30"></span><img class="wp-block-cover__image-background wp-image-1645" alt="Kitesurfing FUN like HEL" src="https://funlikehel.pl/wp-content/uploads/2025/07/kite.png" data-object-fit="cover"/><div class="wp-block-cover__inner-container"><!-- wp:heading {"textAlign":"center","level":3,"style":{"color":{"text":"#ffffff"}}} --><h3 class="wp-block-heading has-text-align-center" style="color:#ffffff">Kitesurfing</h3><!-- /wp:heading --></div></div>
<!-- /wp:cover -->
<!-- wp:paragraph --><p>Nauka od podstaw \u2014 pierwsze starty na latawcu, body drag, jazda na desce. Dla zaawansowanych: skoki, tricki, jazda po fali. Szkolenia indywidualne i grupowe.</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/07/windsurfing.png","id":1644,"dimRatio":30,"minHeight":250,"minHeightUnit":"px"} -->
<div class="wp-block-cover" style="min-height:250px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim has-background-dim-30"></span><img class="wp-block-cover__image-background wp-image-1644" alt="Windsurfing FUN like HEL" src="https://funlikehel.pl/wp-content/uploads/2025/07/windsurfing.png" data-object-fit="cover"/><div class="wp-block-cover__inner-container"><!-- wp:heading {"textAlign":"center","level":3,"style":{"color":{"text":"#ffffff"}}} --><h3 class="wp-block-heading has-text-align-center" style="color:#ffffff">Windsurfing</h3><!-- /wp:heading --></div></div>
<!-- /wp:cover -->
<!-- wp:paragraph --><p>Klasyka sport\u00f3w wodnych. P\u0142ytka Zatoka Pucka to idealne miejsce do nauki \u2014 ciep\u0142a woda, \u0142agodny wiatr, sta\u0142y dost\u0119p do sprz\u0119tu.</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/07/wing.png","id":1643,"dimRatio":30,"minHeight":250,"minHeightUnit":"px"} -->
<div class="wp-block-cover" style="min-height:250px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim has-background-dim-30"></span><img class="wp-block-cover__image-background wp-image-1643" alt="Wing Pumpfoil SUP FUN like HEL" src="https://funlikehel.pl/wp-content/uploads/2025/07/wing.png" data-object-fit="cover"/><div class="wp-block-cover__inner-container"><!-- wp:heading {"textAlign":"center","level":3,"style":{"color":{"text":"#ffffff"}}} --><h3 class="wp-block-heading has-text-align-center" style="color:#ffffff">Wing / Pumpfoil / SUP</h3><!-- /wp:heading --></div></div>
<!-- /wp:cover -->
<!-- wp:paragraph --><p>Najnowsze trendy \u2014 wingfoil, pumpfoil i Stand Up Paddle. \u0141atwe do nauki, mnóstwo frajdy. Idealne na pocz\u0105tek przygody z wod\u0105.</p><!-- /wp:paragraph --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->

<!-- wp:columns {"align":"wide","style":{"spacing":{"blockGap":"30px","margin":{"top":"30px"}}}} -->
<div class="wp-block-columns alignwide"><!-- wp:column -->
<div class="wp-block-column"><!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/07/deskorolka.png","id":1646,"dimRatio":30,"minHeight":250,"minHeightUnit":"px"} -->
<div class="wp-block-cover" style="min-height:250px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim has-background-dim-30"></span><img class="wp-block-cover__image-background wp-image-1646" alt="Wakeboarding" src="https://funlikehel.pl/wp-content/uploads/2025/07/deskorolka.png" data-object-fit="cover"/><div class="wp-block-cover__inner-container"><!-- wp:heading {"textAlign":"center","level":3,"style":{"color":{"text":"#ffffff"}}} --><h3 class="wp-block-heading has-text-align-center" style="color:#ffffff">Wakeboarding</h3><!-- /wp:heading --></div></div>
<!-- /wp:cover -->
<!-- wp:paragraph --><p>Jazda za motorówk\u0105 \u2014 czysta adrenalina. Dla pocz\u0105tkuj\u0105cych i zaawansowanych. Godzinowe sesje z instruktorem.</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:heading {"level":3} --><h3 class="wp-block-heading">Cennik orientacyjny</h3><!-- /wp:heading -->
<!-- wp:table -->
<figure class="wp-block-table"><table><thead><tr><th>Kurs</th><th>Czas</th><th>Cena od</th></tr></thead><tbody><tr><td>Kite / Windsurf indywidualny</td><td>1h</td><td>200 z\u0142</td></tr><tr><td>Kite / Windsurf grupowy</td><td>3h</td><td>350 z\u0142</td></tr><tr><td>Wing / SUP</td><td>1h</td><td>150 z\u0142</td></tr><tr><td>Wakeboarding</td><td>15 min</td><td>100 z\u0142</td></tr><tr><td>Surfkolonie (dziecko/dzie\u0144)</td><td>6h</td><td>od 180 z\u0142</td></tr></tbody></table></figure>
<!-- /wp:table -->
<!-- wp:paragraph {"style":{"typography":{"fontSize":"14px"}}} --><p style="font-size:14px">Dok\u0142adne ceny zale\u017c\u0105 od sezonu i wielko\u015bci grupy. Zadzwo\u0144 po indywidualn\u0105 wycen\u0119: <strong>690 270 032</strong></p><!-- /wp:paragraph --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->

<!-- wp:group {"style":{"spacing":{"padding":{"top":"40px","bottom":"40px"}},"color":{"background":"#e8f4f8"}}} -->
<div class="wp-block-group" style="background-color:#e8f4f8;padding-top:40px;padding-bottom:40px"><!-- wp:paragraph {"align":"center","style":{"typography":{"fontSize":"20px"}}} -->
<p class="has-text-align-center" style="font-size:20px">\ud83d\udcde <strong>Zarezerwuj kurs:</strong> <a href="tel:690270032">690 270 032</a> &nbsp;|&nbsp; \u2709\ufe0f <a href="mailto:funlikehelbrand@gmail.com">funlikehelbrand@gmail.com</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->"""

result = api("POST", "/wp/v2/pages/2033", {
    "title": "Oferta \u2014 Kursy i Szkolenia",
    "slug": "oferta",
    "content": oferta_content,
    "status": "publish"
})
if isinstance(result, dict) and 'id' in result:
    print(f"  OK: Oferta (ID:{result['id']})")
else:
    print(f"  ERR: {str(result)[:200]}")

# =====================================================
# KROK 4: Buduj tresc EGIPT (page 2044)
# =====================================================
print("\n=== BUDUJE STRONE: EGIPT ===")

egipt_content = """<!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/10/1760544043687.jpg","id":1675,"dimRatio":50,"minHeight":500,"minHeightUnit":"px","align":"full"} -->
<div class="wp-block-cover alignfull" style="min-height:500px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim"></span><img class="wp-block-cover__image-background wp-image-1675" alt="Hurghada Egipt kitesurfing FUN like HEL" src="https://funlikehel.pl/wp-content/uploads/2025/10/1760544043687.jpg" data-object-fit="cover"/><div class="wp-block-cover__inner-container"><!-- wp:heading {"textAlign":"center","level":1,"style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"44px"}}} -->
<h1 class="wp-block-heading has-text-align-center" style="color:#ffffff;font-size:44px">Hurghada, Egipt \u2014 Cabrinha Test Center</h1>
<!-- /wp:heading -->
<!-- wp:paragraph {"align":"center","style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"20px"}}} -->
<p class="has-text-align-center" style="color:#ffffff;font-size:20px">Jedyna polska szko\u0142a kite z baz\u0105 zimow\u0105 w Egipcie. P\u0142ytka, ciep\u0142a woda, s\u0142o\u0144ce 300 dni w roku.</p>
<!-- /wp:paragraph --></div></div>
<!-- /wp:cover -->

<!-- wp:group {"style":{"spacing":{"padding":{"top":"50px","bottom":"50px"}}}} -->
<div class="wp-block-group" style="padding-top:50px;padding-bottom:50px"><!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Dlaczego Hurghada?</h2>
<!-- /wp:heading -->
<!-- wp:list -->
<ul><!-- wp:list-item --><li><strong>Wiatr 300 dni w roku</strong> \u2014 nie czekasz na pogod\u0119, jedziesz kiedy chcesz</li><!-- /wp:list-item --><!-- wp:list-item --><li><strong>P\u0142ytka zatoka</strong> \u2014 woda do kolan na setki metr\u00f3w, idealna do nauki</li><!-- /wp:list-item --><!-- wp:list-item --><li><strong>Ciep\u0142a woda ca\u0142y rok</strong> \u2014 \u017cadnego piankowca, szkolenie w szortach</li><!-- /wp:list-item --><!-- wp:list-item --><li><strong>Cabrinha Test Center</strong> \u2014 testuj najnowszy sprz\u0119t przed zakupem</li><!-- /wp:list-item --><!-- wp:list-item --><li><strong>Polscy instruktorzy</strong> \u2014 szkolenia po polsku i angielsku</li><!-- /wp:list-item --><!-- wp:list-item --><li><strong>Przeloty od 330 z\u0142</strong> \u2014 pomagamy znale\u017a\u0107 tani lot</li><!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"50px"}}}} -->
<h2 class="wp-block-heading" style="margin-top:50px">Pakiety szkoleniowe</h2>
<!-- /wp:heading -->

<!-- wp:columns {"style":{"spacing":{"blockGap":"24px"}}} -->
<div class="wp-block-columns"><!-- wp:column {"style":{"color":{"background":"#fff8e1"},"spacing":{"padding":{"top":"30px","bottom":"30px","left":"25px","right":"25px"}}}} -->
<div class="wp-block-column" style="background-color:#fff8e1;padding:30px 25px"><!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">\ud83d\udfe1 Wariant \u017b\u00f3\u0142ty</h3><!-- /wp:heading -->
<!-- wp:heading {"textAlign":"center","level":4} --><h4 class="wp-block-heading has-text-align-center">2300 z\u0142</h4><!-- /wp:heading -->
<!-- wp:list --><ul><!-- wp:list-item --><li>8 godzin szkolenia kite</li><!-- /wp:list-item --><!-- wp:list-item --><li>5 nocleg\u00f3w na spocie Play Kite</li><!-- /wp:list-item --><!-- wp:list-item --><li>\u015aniadania w cenie</li><!-- /wp:list-item --><!-- wp:list-item --><li>Transfer z lotniska</li><!-- /wp:list-item --><!-- wp:list-item --><li>Pomoc przy znalezieniu lotu</li><!-- /wp:list-item --></ul><!-- /wp:list --></div>
<!-- /wp:column -->
<!-- wp:column {"style":{"color":{"background":"#e8e8e8"},"spacing":{"padding":{"top":"30px","bottom":"30px","left":"25px","right":"25px"}}}} -->
<div class="wp-block-column" style="background-color:#e8e8e8;padding:30px 25px"><!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">\u26aa Wariant Srebrny</h3><!-- /wp:heading -->
<!-- wp:heading {"textAlign":"center","level":4} --><h4 class="wp-block-heading has-text-align-center">3300 z\u0142</h4><!-- /wp:heading -->
<!-- wp:list --><ul><!-- wp:list-item --><li>12 godzin szkolenia kite</li><!-- /wp:list-item --><!-- wp:list-item --><li>7 nocleg\u00f3w w mieszkaniu (klimatyzacja, kuchnia)</li><!-- /wp:list-item --><!-- wp:list-item --><li>4 baseny w obiekcie Tiba View</li><!-- /wp:list-item --><!-- wp:list-item --><li>Transfer z lotniska</li><!-- /wp:list-item --><!-- wp:list-item --><li>Pomoc na miejscu 24/7</li><!-- /wp:list-item --><!-- wp:list-item --><li>Mo\u017cliwo\u015b\u0107 nurkowania</li><!-- /wp:list-item --></ul><!-- /wp:list --></div>
<!-- /wp:column -->
<!-- wp:column {"style":{"color":{"background":"#e3f2fd"},"spacing":{"padding":{"top":"30px","bottom":"30px","left":"25px","right":"25px"}}}} -->
<div class="wp-block-column" style="background-color:#e3f2fd;padding:30px 25px"><!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">\ud83d\udfe6 Bez noclegu</h3><!-- /wp:heading -->
<!-- wp:heading {"textAlign":"center","level":4} --><h4 class="wp-block-heading has-text-align-center">od 1910 z\u0142</h4><!-- /wp:heading -->
<!-- wp:list --><ul><!-- wp:list-item --><li>8h szkolenia \u2014 1910 z\u0142</li><!-- /wp:list-item --><!-- wp:list-item --><li>12h szkolenia \u2014 2640 z\u0142</li><!-- /wp:list-item --><!-- wp:list-item --><li>Pe\u0142na elastyczno\u015b\u0107</li><!-- /wp:list-item --><!-- wp:list-item --><li>Sam decydujesz o noclegu i wy\u017cywieniu</li><!-- /wp:list-item --><!-- wp:list-item --><li>Wsparcie na miejscu</li><!-- /wp:list-item --></ul><!-- /wp:list --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->

<!-- wp:paragraph {"style":{"typography":{"fontSize":"14px"}}} -->
<p style="font-size:14px"><a href="https://maps.app.goo.gl/31vLLyFcq4LbAwA96" target="_blank">\ud83d\udccd Poka\u017c na mapie: FUNLIKEHEL EGYPT, Hurghada (27.3347, 33.6925)</a></p>
<!-- /wp:paragraph -->

<!-- wp:group {"style":{"spacing":{"padding":{"top":"40px","bottom":"40px"}},"color":{"background":"#e8f4f8"}}} -->
<div class="wp-block-group" style="background-color:#e8f4f8;padding-top:40px;padding-bottom:40px"><!-- wp:paragraph {"align":"center","style":{"typography":{"fontSize":"20px"}}} -->
<p class="has-text-align-center" style="font-size:20px">\ud83d\udcde <strong>Zarezerwuj wyjazd:</strong> <a href="tel:690270032">690 270 032</a> &nbsp;|&nbsp; \u2709\ufe0f <a href="mailto:funlikehelbrand@gmail.com">funlikehelbrand@gmail.com</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group --></div>
<!-- /wp:group -->"""

result = api("POST", "/wp/v2/pages/2044", {
    "title": "Egipt \u2014 Hurghada | Cabrinha Test Center",
    "slug": "egipt-hurghada",
    "content": egipt_content,
    "status": "publish"
})
if isinstance(result, dict) and 'id' in result:
    print(f"  OK: Egipt (ID:{result['id']})")

# =====================================================
# KROK 5: Buduj tresc OBOZY I KOLONIE (page 2037)
# =====================================================
print("\n=== BUDUJE STRONE: OBOZY I KOLONIE ===")

obozy_content = """<!-- wp:heading {"level":1,"style":{"typography":{"fontSize":"42px"}}} -->
<h1 class="wp-block-heading" style="font-size:42px">Obozy, Kolonie i Femi Campy</h1>
<!-- /wp:heading -->

<!-- wp:paragraph {"style":{"typography":{"fontSize":"18px"}}} -->
<p style="font-size:18px">Sport, przygoda i niezapomniane wspomnienia \u2014 dla dzieci, m\u0142odzie\u017cy i kobiet. Pod okiem do\u015bwiadczonych instruktor\u00f3w na P\u00f3\u0142wyspie Helskim i w Egipcie.</p>
<!-- /wp:paragraph -->

<!-- wp:columns {"style":{"spacing":{"margin":{"top":"40px"}}}} -->
<div class="wp-block-columns"><!-- wp:column -->
<div class="wp-block-column"><!-- wp:image {"id":1866,"sizeSlug":"large"} -->
<figure class="wp-block-image size-large"><img src="https://funlikehel.pl/wp-content/uploads/2025/10/Obozy-scaled.png" alt="Obozy FUN like HEL" class="wp-image-1866"/></figure>
<!-- /wp:image -->
<!-- wp:heading {"level":2} --><h2 class="wp-block-heading">Surfkolonie dla dzieci (5\u20139 lat)</h2><!-- /wp:heading -->
<!-- wp:paragraph --><p>6-godzinne p\u00f3\u0142kolonie ka\u017cdego dnia:</p><!-- /wp:paragraph -->
<!-- wp:list --><ul><!-- wp:list-item --><li>3 godziny zaj\u0119\u0107 sportowych (kite, windsurf, SUP, deskorolka)</li><!-- /wp:list-item --><!-- wp:list-item --><li>Posi\u0142ek wliczony w cen\u0119</li><!-- /wp:list-item --><!-- wp:list-item --><li>Profesjonalna opieka i animacje</li><!-- /wp:list-item --><!-- wp:list-item --><li>Rodzice mog\u0105 spokojnie korzysta\u0107 z wolnego czasu</li><!-- /wp:list-item --></ul><!-- /wp:list --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:image {"id":1990,"sizeSlug":"large"} -->
<figure class="wp-block-image size-large"><img src="https://funlikehel.pl/wp-content/uploads/2025/11/Femicampy-Ala-600-x-600-px-1.png" alt="Femi Campy FUN like HEL" class="wp-image-1990"/></figure>
<!-- /wp:image -->
<!-- wp:heading {"level":2} --><h2 class="wp-block-heading">Femi Campy \u2014 wyjazdy dla kobiet</h2><!-- /wp:heading -->
<!-- wp:paragraph --><p>Ca\u0142oroczne wyjazdy \u0142\u0105cz\u0105ce sport i relaks:</p><!-- /wp:paragraph -->
<!-- wp:list --><ul><!-- wp:list-item --><li>Kitesurfing, windsurfing, wing, SUP</li><!-- /wp:list-item --><!-- wp:list-item --><li>Yoga i mindfulness</li><!-- /wp:list-item --><!-- wp:list-item --><li>W Egipcie: jazda konna i nurkowanie</li><!-- /wp:list-item --><!-- wp:list-item --><li>Atmosfera wsparcia i dobrej zabawy</li><!-- /wp:list-item --></ul><!-- /wp:list --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->

<!-- wp:separator -->
<hr class="wp-block-separator"/>
<!-- /wp:separator -->

<!-- wp:columns {"style":{"spacing":{"margin":{"top":"40px"}}}} -->
<div class="wp-block-columns"><!-- wp:column -->
<div class="wp-block-column"><!-- wp:heading {"level":2} --><h2 class="wp-block-heading">Obozy dla m\u0142odzie\u017cy (13\u201318 lat)</h2><!-- /wp:heading -->
<!-- wp:paragraph --><p>Tydzie\u0144 na wodzie z r\u00f3wie\u015bnikami. Kite, windsurf, wing, deskorolka + wiecz\u00f3rki integracyjne. Bezpiecznie, profesjonalnie, z pasj\u0105.</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:heading {"level":2} --><h2 class="wp-block-heading">Zielone szko\u0142y i wyjazdy firmowe</h2><!-- /wp:heading -->
<!-- wp:paragraph --><p>Kemping Sun4Hel: 300+ miejsc noclegowych, sto\u0142\u00f3wka, szkolenia wodne. Idealne na zielon\u0105 szko\u0142\u0119, wyjazd integracyjny lub team building.</p><!-- /wp:paragraph --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->

<!-- wp:group {"style":{"spacing":{"padding":{"top":"40px","bottom":"40px"}},"color":{"background":"#e8f4f8"}}} -->
<div class="wp-block-group" style="background-color:#e8f4f8;padding-top:40px;padding-bottom:40px"><!-- wp:paragraph {"align":"center","style":{"typography":{"fontSize":"20px"}}} -->
<p class="has-text-align-center" style="font-size:20px">\ud83d\udcde <strong>Zapytaj o terminy:</strong> <a href="tel:690270032">690 270 032</a> &nbsp;|&nbsp; \u2709\ufe0f <a href="mailto:funlikehelbrand@gmail.com">funlikehelbrand@gmail.com</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->"""

result = api("POST", "/wp/v2/pages/2037", {
    "title": "Obozy, Kolonie i Femi Campy",
    "slug": "obozy-kolonie",
    "content": obozy_content,
    "status": "publish"
})
if isinstance(result, dict) and 'id' in result:
    print(f"  OK: Obozy (ID:{result['id']})")

# =====================================================
# KROK 6: Buduj tresc KONTAKT (page 2042)
# =====================================================
print("\n=== BUDUJE STRONE: KONTAKT ===")

kontakt_content = """<!-- wp:heading {"level":1,"style":{"typography":{"fontSize":"42px"}}} -->
<h1 class="wp-block-heading" style="font-size:42px">Kontakt i Rezerwacje</h1>
<!-- /wp:heading -->

<!-- wp:columns {"style":{"spacing":{"margin":{"top":"40px"}}}} -->
<div class="wp-block-columns"><!-- wp:column -->
<div class="wp-block-column"><!-- wp:heading {"level":2} --><h2 class="wp-block-heading">Zadzwo\u0144 lub napisz</h2><!-- /wp:heading -->
<!-- wp:paragraph {"style":{"typography":{"fontSize":"22px"}}} --><p style="font-size:22px">\ud83d\udcde <a href="tel:690270032"><strong>690 270 032</strong></a></p><!-- /wp:paragraph -->
<!-- wp:paragraph {"style":{"typography":{"fontSize":"22px"}}} --><p style="font-size:22px">\u2709\ufe0f <a href="mailto:funlikehelbrand@gmail.com"><strong>funlikehelbrand@gmail.com</strong></a></p><!-- /wp:paragraph -->
<!-- wp:paragraph {"style":{"typography":{"fontSize":"22px"}}} --><p style="font-size:22px">\ud83c\udf10 <a href="https://www.instagram.com/funlikehel/" target="_blank"><strong>@funlikehel</strong></a> (Instagram)</p><!-- /wp:paragraph -->

<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} --><h2 class="wp-block-heading" style="margin-top:40px">Baza Polska \u2014 Jastarnia</h2><!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>Kemping Sun4Hel</strong><br>100 m od morza, 20 m od Zatoki Puckiej<br>Jastarnia, P\u00f3\u0142wysep Helski</p><!-- /wp:paragraph -->

<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"30px"}}}} --><h2 class="wp-block-heading" style="margin-top:30px">Baza Egipt \u2014 Hurghada</h2><!-- /wp:heading -->
<!-- wp:paragraph --><p><strong>FUNLIKEHEL EGYPT \u2014 Cabrinha Test Center</strong><br>P\u00f3\u0142nocna Hurghada, przy spocie kite<br><a href="https://maps.app.goo.gl/31vLLyFcq4LbAwA96" target="_blank">Poka\u017c na mapie Google</a></p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:heading {"level":2} --><h2 class="wp-block-heading">Jak dojecha\u0107?</h2><!-- /wp:heading -->
<!-- wp:html -->
<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2322.5!2d18.6727!3d54.6961!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x46fd0c0ab18add63%3A0x978b28a7e7e4daaa!2sSun4Hel!5e0!3m2!1spl!2spl!4v1700000000000" width="100%" height="350" style="border:0;" allowfullscreen="" loading="lazy"></iframe>
<!-- /wp:html -->

<!-- wp:image {"id":1842,"sizeSlug":"large"} -->
<figure class="wp-block-image size-large"><img src="https://funlikehel.pl/wp-content/uploads/2025/10/kemping2.png" alt="Kemping Sun4Hel Jastarnia" class="wp-image-1842"/></figure>
<!-- /wp:image --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->"""

result = api("POST", "/wp/v2/pages/2042", {
    "title": "Kontakt i Rezerwacje",
    "slug": "kontakt",
    "content": kontakt_content,
    "status": "publish"
})
if isinstance(result, dict) and 'id' in result:
    print(f"  OK: Kontakt (ID:{result['id']})")

# =====================================================
# KROK 7: Stworz strone SKLEP (uzyj istniejacego WooCommerce shop page lub nowy)
# =====================================================
print("\n=== BUDUJE STRONE: SKLEP ===")

sklep_content = """<!-- wp:heading {"level":1,"style":{"typography":{"fontSize":"42px"}}} -->
<h1 class="wp-block-heading" style="font-size:42px">Aquashop FUN like HEL</h1>
<!-- /wp:heading -->

<!-- wp:paragraph {"style":{"typography":{"fontSize":"18px"}}} -->
<p style="font-size:18px">Sprz\u0119t od najlepszych marek \u2014 przetestowany przez naszych instruktor\u00f3w na wodzie. Kupuj \u015bwiadomie.</p>
<!-- /wp:paragraph -->

<!-- wp:columns {"align":"wide","style":{"spacing":{"margin":{"top":"40px"}}}} -->
<div class="wp-block-columns alignwide"><!-- wp:column {"textAlign":"center"} -->
<div class="wp-block-column has-text-align-center"><!-- wp:image {"id":2060,"sizeSlug":"medium","width":"300px"} -->
<figure class="wp-block-image size-medium" style="width:300px"><img src="https://funlikehel.pl/wp-content/uploads/2026/04/IMG_5278-scaled.jpg" alt="Cabrinha kite" class="wp-image-2060"/></figure>
<!-- /wp:image -->
<!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">Cabrinha</h3><!-- /wp:heading -->
<!-- wp:paragraph {"align":"center"} --><p class="has-text-align-center">Latawce, deski, bary. Jeste\u015bmy oficjalnym Cabrinha Test Center \u2014 ka\u017cdy sprz\u0119t mo\u017cesz przetestowa\u0107 na wodzie.</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column {"textAlign":"center"} -->
<div class="wp-block-column has-text-align-center"><!-- wp:image {"id":1664,"sizeSlug":"medium","width":"300px"} -->
<figure class="wp-block-image size-medium" style="width:300px"><img src="https://funlikehel.pl/wp-content/uploads/2025/07/sklep.jpg" alt="Aquashop FUN like HEL" class="wp-image-1664"/></figure>
<!-- /wp:image -->
<!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">Prolimit &amp; Nobile</h3><!-- /wp:heading -->
<!-- wp:paragraph {"align":"center"} --><p class="has-text-align-center">Pianki, trapeze, kaski \u2014 wszystko co potrzebujesz na wod\u0119. Deski Nobile do kite i wake.</p><!-- /wp:paragraph --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->

<!-- wp:separator -->
<hr class="wp-block-separator"/>
<!-- /wp:separator -->

<!-- wp:heading {"level":2} --><h2 class="wp-block-heading">Produkty</h2><!-- /wp:heading -->

<!-- wp:woocommerce/product-collection {"queryId":1,"query":{"perPage":12,"pages":0,"offset":0,"postType":"product","order":"asc","orderBy":"title","search":"","exclude":[],"inherit":false,"taxQuery":{},"isProductCollectionBlock":true,"featured":false,"woocommerceOnSale":false,"woocommerceStockStatus":["instock","outofstock","onbackorder"],"woocommerceAttributes":[],"woocommerceHandPickedProducts":[]},"tagName":"div","displayLayout":{"type":"flex","columns":3}} -->
<div><!-- wp:woocommerce/product-template -->
<!-- wp:woocommerce/product-image /-->
<!-- wp:post-title {"isLink":true} /-->
<!-- wp:woocommerce/product-price /-->
<!-- wp:woocommerce/product-button /-->
<!-- /wp:woocommerce/product-template --></div>
<!-- /wp:woocommerce/product-collection -->

<!-- wp:group {"style":{"spacing":{"padding":{"top":"40px","bottom":"40px"}},"color":{"background":"#e8f4f8"}}} -->
<div class="wp-block-group" style="background-color:#e8f4f8;padding-top:40px;padding-bottom:40px"><!-- wp:paragraph {"align":"center","style":{"typography":{"fontSize":"20px"}}} -->
<p class="has-text-align-center" style="font-size:20px">Chcesz przetestowa\u0107 sprz\u0119t na wodzie? Zadzwo\u0144: <a href="tel:690270032"><strong>690 270 032</strong></a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->"""

# Update existing Aquashop page
result = api("POST", "/wp/v2/pages/2040", {
    "title": "Sklep \u2014 Aquashop",
    "slug": "sklep",
    "content": sklep_content,
    "status": "publish"
})
if isinstance(result, dict) and 'id' in result:
    print(f"  OK: Sklep (ID:{result['id']})")

# =====================================================
# KROK 8: Nowe menu - 5 pozycji
# =====================================================
print("\n=== BUDUJE NOWE MENU ===")

menu_pages = [
    ("Oferta", 2033, 1),
    ("Egipt", 2044, 2),
    ("Obozy i Kolonie", 2037, 3),
    ("Sklep", 2040, 4),
    ("Kontakt", 2042, 5),
]

for title, page_id, order in menu_pages:
    result = api("POST", "/wp/v2/menu-items", {
        "title": title,
        "type": "post_type",
        "object": "page",
        "object_id": page_id,
        "url": f"https://funlikehel.pl/?page_id={page_id}",
        "menus": 22,
        "menu_order": order,
        "parent": 0,
        "status": "publish"
    })
    if isinstance(result, dict) and 'id' in result:
        print(f"  OK  #{order} {title}")
    else:
        print(f"  ERR {title}: {str(result)[:100]}")

# Ukryj niepotrzebne strony
print("\n=== UKRYWAM POZOSTALE ===")
hide_extra = [2039, 2038, 2043, 1329]  # Nocleg, Femi Campy (oddzielna), Kite PL, ...
# Nie! 1329 to Home - zostaje. Ukryjmy te ktore weszly do obozy/oferta
hide_extra = [2039, 2038, 2043, 2034, 2035, 2036, 2041]
for pid in hide_extra:
    result = api("POST", f"/wp/v2/pages/{pid}", {"status": "draft"})
    if isinstance(result, dict) and 'id' in result:
        t = result.get('title',{}).get('rendered','?')
        print(f"  Draft: {t}")

print("\nGOTOWE!")
