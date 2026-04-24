import subprocess, json, sys

NONCE = "49d48a67ba"
COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"

homepage_content = """<!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/10/DSC08514-scaled.jpg","id":1758,"dimRatio":50,"minHeight":600,"minHeightUnit":"px","align":"full","style":{"spacing":{"padding":{"top":"80px","bottom":"80px"}}}} -->
<div class="wp-block-cover alignfull" style="min-height:600px;padding-top:80px;padding-bottom:80px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim"></span><img class="wp-block-cover__image-background wp-image-1758" alt="FUN like HEL kitesurfing" src="https://funlikehel.pl/wp-content/uploads/2025/10/DSC08514-scaled.jpg" data-object-fit="cover"/><div class="wp-block-cover__inner-container"><!-- wp:heading {"textAlign":"center","level":1,"style":{"typography":{"fontSize":"52px"},"color":{"text":"#ffffff"}}} -->
<h1 class="wp-block-heading has-text-align-center" style="color:#ffffff;font-size:52px">Szko\u0142a Sport\u00f3w Wodnych FUN like HEL</h1>
<!-- /wp:heading -->
<!-- wp:paragraph {"align":"center","style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"22px"}}} -->
<p class="has-text-align-center" style="color:#ffffff;font-size:22px">Szkolimy przez ca\u0142y rok \u2014 latem w Jastarni, zim\u0105 w Egipcie \ud83c\udf0a</p>
<!-- /wp:paragraph -->
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"},"style":{"spacing":{"margin":{"top":"30px"}}}} -->
<div class="wp-block-buttons"><!-- wp:button {"backgroundColor":"vivid-cyan-blue","style":{"typography":{"fontSize":"18px"},"spacing":{"padding":{"top":"14px","bottom":"14px","left":"32px","right":"32px"}}}} -->
<div class="wp-block-button"><a class="wp-block-button__link has-vivid-cyan-blue-background-color has-background wp-element-button" href="tel:690270032" style="font-size:18px;padding:14px 32px">\ud83d\udcde Zadzwo\u0144: 690 270 032</a></div>
<!-- /wp:button -->
<!-- wp:button {"className":"is-style-outline","style":{"typography":{"fontSize":"18px"},"spacing":{"padding":{"top":"14px","bottom":"14px","left":"32px","right":"32px"}}}} -->
<div class="wp-block-button is-style-outline"><a class="wp-block-button__link wp-element-button" href="https://funlikehel.pl/?page_id=2042" style="font-size:18px;padding:14px 32px">Zarezerwuj kurs</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div></div>
<!-- /wp:cover -->

<!-- wp:group {"align":"full","style":{"spacing":{"padding":{"top":"60px","bottom":"60px"}},"color":{"background":"#f0f8ff"}}} -->
<div class="wp-block-group alignfull" style="background-color:#f0f8ff;padding-top:60px;padding-bottom:60px"><!-- wp:columns {"align":"wide"} -->
<div class="wp-block-columns alignwide"><!-- wp:column {"textAlign":"center"} -->
<div class="wp-block-column has-text-align-center"><!-- wp:paragraph {"style":{"typography":{"fontSize":"48px"}}} --><p style="font-size:48px">\ud83c\udfc4</p><!-- /wp:paragraph -->
<!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">3000 przeszkolonych klient\u00f3w</h3><!-- /wp:heading -->
<!-- wp:paragraph {"align":"center"} --><p class="has-text-align-center">Do\u0142\u0105cz do tysi\u0119cy, kt\u00f3rzy z nami pokochali wod\u0119</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column {"textAlign":"center"} -->
<div class="wp-block-column has-text-align-center"><!-- wp:paragraph {"style":{"typography":{"fontSize":"48px"}}} --><p style="font-size:48px">\ud83c\udf0d</p><!-- /wp:paragraph -->
<!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">Polska i Egipt</h3><!-- /wp:heading -->
<!-- wp:paragraph {"align":"center"} --><p class="has-text-align-center">Jedyna polska szko\u0142a z baz\u0105 zimow\u0105 w Hurghadzie</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column {"textAlign":"center"} -->
<div class="wp-block-column has-text-align-center"><!-- wp:paragraph {"style":{"typography":{"fontSize":"48px"}}} --><p style="font-size:48px">\u2b50</p><!-- /wp:paragraph -->
<!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">99% pozytywnych recenzji</h3><!-- /wp:heading -->
<!-- wp:paragraph {"align":"center"} --><p class="has-text-align-center">Najlepiej oceniana szko\u0142a na P\u00f3\u0142wyspie Helskim</p><!-- /wp:paragraph --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->

<!-- wp:group {"align":"full","style":{"spacing":{"padding":{"top":"60px","bottom":"60px"}}}} -->
<div class="wp-block-group alignfull" style="padding-top:60px;padding-bottom:60px"><!-- wp:heading {"textAlign":"center","level":2,"style":{"typography":{"fontSize":"38px"}}} -->
<h2 class="wp-block-heading has-text-align-center" style="font-size:38px">Co oferujemy?</h2>
<!-- /wp:heading -->
<!-- wp:columns {"align":"wide","style":{"spacing":{"blockGap":"24px","margin":{"top":"40px"}}}} -->
<div class="wp-block-columns alignwide"><!-- wp:column -->
<div class="wp-block-column"><!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/07/kite.png","id":1645,"dimRatio":40,"minHeight":300,"minHeightUnit":"px"} -->
<div class="wp-block-cover" style="min-height:300px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim has-background-dim-40"></span><img class="wp-block-cover__image-background wp-image-1645" alt="Kitesurfing" src="https://funlikehel.pl/wp-content/uploads/2025/07/kite.png" data-object-fit="cover"/><div class="wp-block-cover__inner-container"><!-- wp:heading {"textAlign":"center","level":3,"style":{"color":{"text":"#ffffff"}}} --><h3 class="wp-block-heading has-text-align-center" style="color:#ffffff">Kitesurfing</h3><!-- /wp:heading -->
<!-- wp:paragraph {"align":"center","style":{"color":{"text":"#ffffff"}}} --><p class="has-text-align-center" style="color:#ffffff">Polska i Egipt</p><!-- /wp:paragraph -->
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} --><div class="wp-block-buttons"><!-- wp:button {"className":"is-style-outline"} --><div class="wp-block-button is-style-outline"><a class="wp-block-button__link wp-element-button" href="https://funlikehel.pl/?page_id=2033">Dowiedz si\u0119 wi\u0119cej</a></div><!-- /wp:button --></div><!-- /wp:buttons --></div></div>
<!-- /wp:cover --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/07/windsurfing.png","id":1644,"dimRatio":40,"minHeight":300,"minHeightUnit":"px"} -->
<div class="wp-block-cover" style="min-height:300px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim has-background-dim-40"></span><img class="wp-block-cover__image-background wp-image-1644" alt="Windsurfing" src="https://funlikehel.pl/wp-content/uploads/2025/07/windsurfing.png" data-object-fit="cover"/><div class="wp-block-cover__inner-container"><!-- wp:heading {"textAlign":"center","level":3,"style":{"color":{"text":"#ffffff"}}} --><h3 class="wp-block-heading has-text-align-center" style="color:#ffffff">Windsurfing</h3><!-- /wp:heading -->
<!-- wp:paragraph {"align":"center","style":{"color":{"text":"#ffffff"}}} --><p class="has-text-align-center" style="color:#ffffff">Jastarnia i Hurghada</p><!-- /wp:paragraph -->
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} --><div class="wp-block-buttons"><!-- wp:button {"className":"is-style-outline"} --><div class="wp-block-button is-style-outline"><a class="wp-block-button__link wp-element-button" href="https://funlikehel.pl/?page_id=2034">Dowiedz si\u0119 wi\u0119cej</a></div><!-- /wp:button --></div><!-- /wp:buttons --></div></div>
<!-- /wp:cover --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/07/wing.png","id":1643,"dimRatio":40,"minHeight":300,"minHeightUnit":"px"} -->
<div class="wp-block-cover" style="min-height:300px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim has-background-dim-40"></span><img class="wp-block-cover__image-background wp-image-1643" alt="Wing SUP Pumpfoil" src="https://funlikehel.pl/wp-content/uploads/2025/07/wing.png" data-object-fit="cover"/><div class="wp-block-cover__inner-container"><!-- wp:heading {"textAlign":"center","level":3,"style":{"color":{"text":"#ffffff"}}} --><h3 class="wp-block-heading has-text-align-center" style="color:#ffffff">Wing / Pumpfoil / SUP</h3><!-- /wp:heading -->
<!-- wp:paragraph {"align":"center","style":{"color":{"text":"#ffffff"}}} --><p class="has-text-align-center" style="color:#ffffff">Nowoczesne sporty wodne</p><!-- /wp:paragraph -->
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} --><div class="wp-block-buttons"><!-- wp:button {"className":"is-style-outline"} --><div class="wp-block-button is-style-outline"><a class="wp-block-button__link wp-element-button" href="https://funlikehel.pl/?page_id=2035">Dowiedz si\u0119 wi\u0119cej</a></div><!-- /wp:button --></div><!-- /wp:buttons --></div></div>
<!-- /wp:cover --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->

<!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/10/1760544043687.jpg","id":1675,"dimRatio":60,"align":"full","minHeight":500,"minHeightUnit":"px"} -->
<div class="wp-block-cover alignfull" style="min-height:500px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim has-background-dim-60"></span><img class="wp-block-cover__image-background wp-image-1675" alt="Hurghada Egipt kitesurfing" src="https://funlikehel.pl/wp-content/uploads/2025/10/1760544043687.jpg" data-object-fit="cover"/><div class="wp-block-cover__inner-container"><!-- wp:heading {"textAlign":"center","level":2,"style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"40px"}}} -->
<h2 class="wp-block-heading has-text-align-center" style="color:#ffffff;font-size:40px">Baza zimowa \u2014 Hurghada, Egipt \ud83c\udf05</h2>
<!-- /wp:heading -->
<!-- wp:paragraph {"align":"center","style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"20px"}}} -->
<p class="has-text-align-center" style="color:#ffffff;font-size:20px">Cabrinha Test Center. P\u0142ytka, ciep\u0142a woda, s\u0142o\u0144ce przez ca\u0142y rok.</p>
<!-- /wp:paragraph -->
<!-- wp:columns {"align":"wide","style":{"spacing":{"margin":{"top":"40px"}}}} -->
<div class="wp-block-columns alignwide"><!-- wp:column {"textAlign":"center"} --><div class="wp-block-column has-text-align-center"><!-- wp:heading {"textAlign":"center","level":4,"style":{"color":{"text":"#ffffff"}}} --><h4 class="wp-block-heading has-text-align-center" style="color:#ffffff">Wariant \u017b\u00f3\u0142ty</h4><!-- /wp:heading --><!-- wp:paragraph {"align":"center","style":{"color":{"text":"#ffffff"}}} --><p class="has-text-align-center" style="color:#ffffff">8h kite + 5 nocleg\u00f3w<br><strong>2300 z\u0142</strong></p><!-- /wp:paragraph --></div><!-- /wp:column -->
<!-- wp:column {"textAlign":"center"} --><div class="wp-block-column has-text-align-center"><!-- wp:heading {"textAlign":"center","level":4,"style":{"color":{"text":"#ffffff"}}} --><h4 class="wp-block-heading has-text-align-center" style="color:#ffffff">Wariant Srebrny</h4><!-- /wp:heading --><!-- wp:paragraph {"align":"center","style":{"color":{"text":"#ffffff"}}} --><p class="has-text-align-center" style="color:#ffffff">12h kite + 7 nocleg\u00f3w<br><strong>3300 z\u0142</strong></p><!-- /wp:paragraph --></div><!-- /wp:column -->
<!-- wp:column {"textAlign":"center"} --><div class="wp-block-column has-text-align-center"><!-- wp:heading {"textAlign":"center","level":4,"style":{"color":{"text":"#ffffff"}}} --><h4 class="wp-block-heading has-text-align-center" style="color:#ffffff">Bez noclegu</h4><!-- /wp:heading --><!-- wp:paragraph {"align":"center","style":{"color":{"text":"#ffffff"}}} --><p class="has-text-align-center" style="color:#ffffff">8h \u2014 1910 z\u0142<br>12h \u2014 <strong>2640 z\u0142</strong></p><!-- /wp:paragraph --></div><!-- /wp:column --></div><!-- /wp:columns -->
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"},"style":{"spacing":{"margin":{"top":"30px"}}}} -->
<div class="wp-block-buttons"><!-- wp:button {"style":{"typography":{"fontSize":"18px"}}} --><div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="https://funlikehel.pl/?page_id=2044" style="font-size:18px">Zobacz ofert\u0119 Egipt</a></div><!-- /wp:button --></div><!-- /wp:buttons --></div></div>
<!-- /wp:cover -->

<!-- wp:group {"align":"full","style":{"spacing":{"padding":{"top":"60px","bottom":"60px"}}}} -->
<div class="wp-block-group alignfull" style="padding-top:60px;padding-bottom:60px"><!-- wp:heading {"textAlign":"center","level":2} -->
<h2 class="wp-block-heading has-text-align-center">Obozy, Kolonie i Femi Campy</h2>
<!-- /wp:heading -->
<!-- wp:columns {"align":"wide","style":{"spacing":{"margin":{"top":"40px"}}}} -->
<div class="wp-block-columns alignwide"><!-- wp:column -->
<div class="wp-block-column"><!-- wp:image {"id":1866,"sizeSlug":"large","linkDestination":"custom"} -->
<figure class="wp-block-image size-large"><a href="https://funlikehel.pl/?page_id=2037"><img src="https://funlikehel.pl/wp-content/uploads/2025/10/Obozy-scaled.png" alt="Obozy i kolonie FUN like HEL" class="wp-image-1866"/></a></figure>
<!-- /wp:image -->
<!-- wp:heading {"level":3} --><h3 class="wp-block-heading">Obozy i Kolonie</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p>Surfkolonie dla dzieci, obozy dla m\u0142odzie\u017cy, zielone szko\u0142y. Profesjonalna opieka, sport i masa zabawy na P\u00f3\u0142wyspie Helskim.</p><!-- /wp:paragraph -->
<!-- wp:buttons --><div class="wp-block-buttons"><!-- wp:button --><div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="https://funlikehel.pl/?page_id=2037">Sprawd\u017a obozy</a></div><!-- /wp:button --></div><!-- /wp:buttons --></div>
<!-- /wp:column -->
<!-- wp:column -->
<div class="wp-block-column"><!-- wp:image {"id":1990,"sizeSlug":"large","linkDestination":"custom"} -->
<figure class="wp-block-image size-large"><a href="https://funlikehel.pl/?page_id=2038"><img src="https://funlikehel.pl/wp-content/uploads/2025/11/Femicampy-Ala-600-x-600-px-1.png" alt="Femi Campy FUN like HEL" class="wp-image-1990"/></a></figure>
<!-- /wp:image -->
<!-- wp:heading {"level":3} --><h3 class="wp-block-heading">Femi Campy</h3><!-- /wp:heading -->
<!-- wp:paragraph --><p>Ca\u0142oroczne wyjazdy dla kobiet \u2014 kite, windsurfing, wing, yoga, a w Egipcie te\u017c jazda konna i nurkowanie. Zr\u00f3b co\u015b tylko dla siebie!</p><!-- /wp:paragraph -->
<!-- wp:buttons --><div class="wp-block-buttons"><!-- wp:button --><div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="https://funlikehel.pl/?page_id=2038">Femi Campy</a></div><!-- /wp:button --></div><!-- /wp:buttons --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->

<!-- wp:gallery {"ids":[1758,1757,1756,1799,1876,1875],"columns":3,"align":"wide"} -->
<figure class="wp-block-gallery alignwide has-nested-images columns-3"><!-- wp:image {"id":1758} --><figure class="wp-block-image"><img src="https://funlikehel.pl/wp-content/uploads/2025/10/DSC08514-scaled.jpg" alt="FUN like HEL" class="wp-image-1758"/></figure><!-- /wp:image --><!-- wp:image {"id":1757} --><figure class="wp-block-image"><img src="https://funlikehel.pl/wp-content/uploads/2025/10/DSC08510-scaled.jpg" alt="FUN like HEL" class="wp-image-1757"/></figure><!-- /wp:image --><!-- wp:image {"id":1756} --><figure class="wp-block-image"><img src="https://funlikehel.pl/wp-content/uploads/2025/10/DSC08509-scaled.jpg" alt="FUN like HEL" class="wp-image-1756"/></figure><!-- /wp:image --><!-- wp:image {"id":1799} --><figure class="wp-block-image"><img src="https://funlikehel.pl/wp-content/uploads/2025/10/IMG_3865-scaled.jpg" alt="kitesurfing Jastarnia" class="wp-image-1799"/></figure><!-- /wp:image --><!-- wp:image {"id":1876} --><figure class="wp-block-image"><img src="https://funlikehel.pl/wp-content/uploads/2025/10/IMG_0226.jpg" alt="FUN like HEL kursy" class="wp-image-1876"/></figure><!-- /wp:image --><!-- wp:image {"id":1875} --><figure class="wp-block-image"><img src="https://funlikehel.pl/wp-content/uploads/2025/10/IMG_0110.jpg" alt="FUN like HEL sport" class="wp-image-1875"/></figure><!-- /wp:image --></figure>
<!-- /wp:gallery -->

<!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/10/kemping2.png","id":1842,"dimRatio":60,"align":"full","minHeight":400,"minHeightUnit":"px"} -->
<div class="wp-block-cover alignfull" style="min-height:400px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim has-background-dim-60"></span><img class="wp-block-cover__image-background wp-image-1842" alt="Kemping Sun4Hel Jastarnia" src="https://funlikehel.pl/wp-content/uploads/2025/10/kemping2.png" data-object-fit="cover"/><div class="wp-block-cover__inner-container"><!-- wp:heading {"textAlign":"center","level":2,"style":{"color":{"text":"#ffffff"}}} -->
<h2 class="wp-block-heading has-text-align-center" style="color:#ffffff">Masz pytanie? Zadzwo\u0144 lub napisz!</h2>
<!-- /wp:heading -->
<!-- wp:paragraph {"align":"center","style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"22px"}}} -->
<p class="has-text-align-center" style="color:#ffffff;font-size:22px">\ud83d\udcde 690 270 032 &nbsp;|&nbsp; \u2709\ufe0f funlikehelbrand@gmail.com</p>
<!-- /wp:paragraph -->
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"},"style":{"spacing":{"margin":{"top":"24px"}}}} -->
<div class="wp-block-buttons"><!-- wp:button {"style":{"typography":{"fontSize":"20px"},"spacing":{"padding":{"top":"16px","bottom":"16px","left":"40px","right":"40px"}}}} -->
<div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="https://funlikehel.pl/?page_id=2042" style="font-size:20px;padding:16px 40px">Zarezerwuj kurs teraz!</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div></div>
<!-- /wp:cover -->"""

payload = json.dumps({
    "title": "Szko\u0142a Sport\u00f3w Wodnych FUN like HEL | Jastarnia i Egipt",
    "content": homepage_content,
    "status": "publish"
})

cmd = ["curl", "-s", "-b", COOKIE,
       "-H", f"X-WP-Nonce: {NONCE}",
       "-H", "Content-Type: application/json",
       "-X", "POST",
       "https://funlikehel.pl/?rest_route=/wp/v2/pages/1329",
       "-d", payload]

r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
try:
    d = json.loads(r.stdout)
    if "id" in d:
        print(f"OK! Strona glowna zaktualizowana. ID:{d['id']}")
        print(f"Link: {d['link']}")
    else:
        print(f"ERR: {r.stdout[:300]}")
except Exception as e:
    print(f"ERR: {e}")
    print(r.stdout[:300])
