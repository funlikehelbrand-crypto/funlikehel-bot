"""
Dopracowanie wszystkich 5 punktow:
1. Jastarnia - rozbudowa
2. Egipt-Hurghada - dopracowanie
3. Strona glowna - poprawki
4. TikTok feed
5. Chatbot URL
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

# IMG URLs
IMG = {
    "kemping2": "https://funlikehel.pl/wp-content/uploads/2025/10/kemping2.png",
    "kemping3": "https://funlikehel.pl/wp-content/uploads/2025/10/kemping3.png",
    "kemping4": "https://funlikehel.pl/wp-content/uploads/2025/10/kemping4.png",
    "team": "https://funlikehel.pl/wp-content/uploads/2025/10/teaam-scaled.jpg",
    "egipt1": "https://funlikehel.pl/wp-content/uploads/2025/10/1760544043687.jpg",
    "egipt2": "https://funlikehel.pl/wp-content/uploads/2025/10/1760629523491-scaled.jpg",
    "egipt3": "https://funlikehel.pl/wp-content/uploads/2025/10/1760629523465-scaled.jpg",
    "egipt4": "https://funlikehel.pl/wp-content/uploads/2025/10/1760629523440-scaled.jpg",
    "cab1": "https://funlikehel.pl/wp-content/uploads/2026/04/IMG_5278-scaled.jpg",
    "cab2": "https://funlikehel.pl/wp-content/uploads/2026/04/IMG_5051-scaled.jpg",
    "cab3": "https://funlikehel.pl/wp-content/uploads/2026/04/IMG_5292-scaled.jpg",
    "dsc1": "https://funlikehel.pl/wp-content/uploads/2025/10/DSC08510-scaled.jpg",
    "dsc2": "https://funlikehel.pl/wp-content/uploads/2025/10/DSC08509-scaled.jpg",
    "obozy": "https://funlikehel.pl/wp-content/uploads/2025/10/Obozy-scaled.png",
    "femi": "https://funlikehel.pl/wp-content/uploads/2025/11/Femicampy-Ala-600-x-600-px-1.png",
    "img3865": "https://funlikehel.pl/wp-content/uploads/2025/10/IMG_3865-scaled.jpg",
    "img0900": "https://funlikehel.pl/wp-content/uploads/2025/10/IMG_0900.jpg",
    "img0591": "https://funlikehel.pl/wp-content/uploads/2025/10/IMG_0591.jpg",
    "img0607": "https://funlikehel.pl/wp-content/uploads/2025/10/IMG_0607.jpg",
    "img0340": "https://funlikehel.pl/wp-content/uploads/2025/10/IMG_0340.jpg",
    "img0110": "https://funlikehel.pl/wp-content/uploads/2025/10/IMG_0110.jpg",
    "whatsapp1": "https://funlikehel.pl/wp-content/uploads/2025/10/Zdjecie-WhatsApp-2025-10-21-o-20.40.03_cef67cbd.jpg",
    "whatsapp2": "https://funlikehel.pl/wp-content/uploads/2025/10/Zdjecie-WhatsApp-2025-10-21-o-20.26.46_46df365c.jpg",
}

# =====================================================
# 1. JASTARNIA — rozbudowa
# =====================================================
print("=== 1. JASTARNIA ===")

jastarnia = (
    # HERO
    f'<!-- wp:cover {{"url":"{IMG["dsc1"]}","dimRatio":45,"minHeight":500,"minHeightUnit":"px","align":"full"}} -->'
    f'<div class="wp-block-cover alignfull" style="min-height:500px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim has-background-dim-45"></span>'
    f'<img class="wp-block-cover__image-background" alt="Jastarnia kitesurfing" src="{IMG["dsc1"]}" data-object-fit="cover"/>'
    '<div class="wp-block-cover__inner-container">'
    '<!-- wp:heading {"textAlign":"center","level":1,"style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"48px"}}} -->'
    '<h1 class="wp-block-heading has-text-align-center" style="color:#ffffff;font-size:48px">Jastarnia \u2014 P\u00f3\u0142wysep Helski</h1>'
    '<!-- /wp:heading -->'
    '<!-- wp:paragraph {"align":"center","style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"20px"}}} -->'
    '<p class="has-text-align-center" style="color:#ffffff;font-size:20px">Kemping Sun4Hel \u2014 100 m od morza, 20 m od Zatoki Puckiej<br>Sezon: maj \u2013 wrzesie\u0144</p>'
    '<!-- /wp:paragraph -->'
    '<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->'
    '<div class="wp-block-buttons"><!-- wp:button {"backgroundColor":"vivid-cyan-blue"} -->'
    '<div class="wp-block-button"><a class="wp-block-button__link has-vivid-cyan-blue-background-color has-background wp-element-button" href="tel:690270032">\ud83d\udcde 690 270 032</a></div>'
    '<!-- /wp:button --></div><!-- /wp:buttons -->'
    '</div></div><!-- /wp:cover -->'

    # DLACZEGO JASTARNIA
    '<!-- wp:group {"style":{"spacing":{"padding":{"top":"50px","bottom":"50px"}}}} -->'
    '<div class="wp-block-group" style="padding-top:50px;padding-bottom:50px">'
    '<!-- wp:heading {"level":2} --><h2 class="wp-block-heading">Dlaczego Jastarnia?</h2><!-- /wp:heading -->'
    '<!-- wp:columns --><div class="wp-block-columns">'
    '<!-- wp:column --><div class="wp-block-column">'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li><strong>Zatoka Pucka</strong> \u2014 p\u0142ytka woda (do kolan na 300 m!) idealna do nauki kite i windsurf</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>Morze po drugiej stronie</strong> \u2014 100 m i masz fale do wave ridingu</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>Termiczny wiatr</strong> \u2014 od maja do wrze\u015bnia, 15\u201325 w\u0119z\u0142\u00f3w, stabilny i przewidywalny</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list --></div><!-- /wp:column -->'
    '<!-- wp:column --><div class="wp-block-column">'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li><strong>Cabrinha Test Center</strong> \u2014 testuj najnowszy sprz\u0119t 2026 na wodzie</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>300+ miejsc noclegowych</strong> \u2014 pawilony z po\u015bciel\u0105, sto\u0142\u00f3wka, pe\u0142na infrastruktura</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>Aquashop na miejscu</strong> \u2014 Cabrinha, Prolimit, Nobile \u2014 kup lub wypo\u017cycz</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list --></div><!-- /wp:column -->'
    '</div><!-- /wp:columns -->'

    # CENNIK KURSOW
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Cennik kurs\u00f3w \u2014 sezon 2026</h2><!-- /wp:heading -->'
    '<!-- wp:table -->'
    '<figure class="wp-block-table"><table>'
    '<thead><tr><th>Kurs</th><th>Czas</th><th>Cena</th><th>Uwagi</th></tr></thead>'
    '<tbody>'
    '<tr><td>Kitesurfing indywidualny</td><td>1h</td><td><strong>250 z\u0142</strong></td><td>1 instruktor : 1 kursant</td></tr>'
    '<tr><td>Kitesurfing grupowy (2\u20134 os.)</td><td>3h</td><td><strong>350 z\u0142/os.</strong></td><td>Sprz\u0119t w cenie</td></tr>'
    '<tr><td>Windsurfing indywidualny</td><td>1h</td><td><strong>200 z\u0142</strong></td><td>1 instruktor : 1 kursant</td></tr>'
    '<tr><td>Windsurfing grupowy</td><td>2h</td><td><strong>250 z\u0142/os.</strong></td><td>Max 4 osoby</td></tr>'
    '<tr><td>Wing foil</td><td>1h</td><td><strong>250 z\u0142</strong></td><td>Foil + wing w cenie</td></tr>'
    '<tr><td>SUP</td><td>1h</td><td><strong>80 z\u0142</strong></td><td>Wypo\u017cyczenie + kr\u00f3tki instrukta\u017c</td></tr>'
    '<tr><td>Wakeboarding</td><td>15 min</td><td><strong>120 z\u0142</strong></td><td>Za motor\u00f3wk\u0105</td></tr>'
    '<tr><td>Surfkolonie (dziecko/dzie\u0144)</td><td>6h</td><td><strong>od 180 z\u0142</strong></td><td>Sport + wy\u017cywienie + opieka</td></tr>'
    '</tbody></table></figure>'
    '<!-- /wp:table -->'
    '<!-- wp:paragraph {"style":{"typography":{"fontSize":"14px"}}} -->'
    '<p style="font-size:14px">Ceny orientacyjne \u2014 zale\u017c\u0105 od sezonu i wielko\u015bci grupy. Zadzwo\u0144 po indywidualn\u0105 wycen\u0119: <strong>690 270 032</strong></p>'
    '<!-- /wp:paragraph -->'

    # SPORTY
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Sporty</h2><!-- /wp:heading -->'
    '<!-- wp:columns --><div class="wp-block-columns">'
    '<!-- wp:column --><div class="wp-block-column">'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li>\ud83e\ude81 Kitesurfing</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>\ud83c\udfc4 Windsurfing</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>\ud83e\udeb6 Wing foil</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>\ud83c\udfbf Pumpfoil</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list --></div><!-- /wp:column -->'
    '<!-- wp:column --><div class="wp-block-column">'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li>\ud83d\udea3 SUP</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>\ud83d\udea4 Wakeboarding</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>\ud83d\udef9 Deskorolka</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>\ud83e\uddd8 Yoga</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list --></div><!-- /wp:column -->'
    '</div><!-- /wp:columns -->'

    # GALERIA
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Galeria</h2><!-- /wp:heading -->'
    '<!-- wp:gallery {"columns":3,"align":"wide"} -->'
    '<figure class="wp-block-gallery alignwide has-nested-images columns-3">'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["img0900"]}" alt="Kitesurfing Jastarnia"/></figure><!-- /wp:image -->'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["img0591"]}" alt="Windsurfing Jastarnia"/></figure><!-- /wp:image -->'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["img0607"]}" alt="Sport wodny Jastarnia"/></figure><!-- /wp:image -->'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["dsc2"]}" alt="FUN like HEL Jastarnia"/></figure><!-- /wp:image -->'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["img0340"]}" alt="Kursy Jastarnia"/></figure><!-- /wp:image -->'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["img0110"]}" alt="Zatoka Pucka"/></figure><!-- /wp:image -->'
    '</figure><!-- /wp:gallery -->'

    # NOCLEG
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Nocleg \u2014 Kemping Sun4Hel</h2><!-- /wp:heading -->'
    '<!-- wp:paragraph --><p>Ponad <strong>300 miejsc noclegowych</strong> na terenie kempingu. '
    'Pawilony mieszkalne (15 m\u00b2): 2 pi\u0119trowe \u0142\u00f3\u017cka z po\u015bciel\u0105, '
    'lod\u00f3wka, stolik, szafa, grzejnik, rolety. Sto\u0142\u00f3wka i jadalnia na miejscu.</p><!-- /wp:paragraph -->'
    '<!-- wp:gallery {"columns":3,"align":"wide"} -->'
    '<figure class="wp-block-gallery alignwide has-nested-images columns-3">'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["kemping2"]}" alt="Kemping Sun4Hel"/></figure><!-- /wp:image -->'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["kemping3"]}" alt="Kemping Sun4Hel"/></figure><!-- /wp:image -->'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["kemping4"]}" alt="Kemping Sun4Hel"/></figure><!-- /wp:image -->'
    '</figure><!-- /wp:gallery -->'

    # JAK DOJECHAC
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Jak dojecha\u0107?</h2><!-- /wp:heading -->'
    '<!-- wp:paragraph --><p><strong>Samochodem:</strong> Trasa Gda\u0144sk \u2192 W\u0142adys\u0142awowo \u2192 Jastarnia (~1,5h z Gda\u0144ska). Parking na terenie kempingu.<br>'
    '<strong>Poci\u0105giem:</strong> SKM do Helu, przystanek Jastarnia \u2014 10 min pieszo do kempingu.<br>'
    '<strong>Autobusem:</strong> Linie 666 i inne z Tr\u00f3jmiasta na Hel.</p><!-- /wp:paragraph -->'
    '<!-- wp:html -->'
    '<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2322!2d18.6727!3d54.6961!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x46fd0c0ab18add63%3A0x978b28a7e7e4daaa!2sSun4Hel!5e0!3m2!1spl!2spl" width="100%" height="350" style="border:0;border-radius:12px;" allowfullscreen="" loading="lazy"></iframe>'
    '<!-- /wp:html -->'

    # CTA
    '<!-- wp:group {"style":{"spacing":{"padding":{"top":"40px","bottom":"40px"}},"color":{"background":"#e8f4f8"}}} -->'
    '<div class="wp-block-group" style="background-color:#e8f4f8;padding-top:40px;padding-bottom:40px">'
    '<!-- wp:paragraph {"align":"center","style":{"typography":{"fontSize":"20px"}}} -->'
    '<p class="has-text-align-center" style="font-size:20px">\ud83d\udcde <strong>Zarezerwuj:</strong> <a href="tel:690270032">690 270 032</a> &nbsp;|&nbsp; \u2709\ufe0f <a href="mailto:funlikehelbrand@gmail.com">funlikehelbrand@gmail.com</a></p>'
    '<!-- /wp:paragraph --></div><!-- /wp:group -->'
    '</div><!-- /wp:group -->'
)

result = api("POST", "/wp/v2/pages/2161", {"content": jastarnia})
print(f"  Jastarnia: {'OK' if isinstance(result, dict) and 'id' in result else 'ERR'}")

# =====================================================
# 2. EGIPT-HURGHADA — dopracowanie
# =====================================================
print("\n=== 2. EGIPT-HURGHADA ===")

egipt = (
    # HERO
    f'<!-- wp:cover {{"url":"{IMG["egipt1"]}","dimRatio":45,"minHeight":500,"minHeightUnit":"px","align":"full"}} -->'
    f'<div class="wp-block-cover alignfull" style="min-height:500px"><span aria-hidden="true" class="wp-block-cover__background has-background-dim has-background-dim-45"></span>'
    f'<img class="wp-block-cover__image-background" alt="Hurghada Egipt kitesurfing" src="{IMG["egipt1"]}" data-object-fit="cover"/>'
    '<div class="wp-block-cover__inner-container">'
    '<!-- wp:heading {"textAlign":"center","level":1,"style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"48px"}}} -->'
    '<h1 class="wp-block-heading has-text-align-center" style="color:#ffffff;font-size:48px">Egipt \u2014 Hurghada</h1>'
    '<!-- /wp:heading -->'
    '<!-- wp:paragraph {"align":"center","style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"20px"}}} -->'
    '<p class="has-text-align-center" style="color:#ffffff;font-size:20px">FUNLIKEHEL EGYPT \u2014 Cabrinha Test Center<br>Jedyna polska szko\u0142a kite z baz\u0105 zimow\u0105 w Egipcie</p>'
    '<!-- /wp:paragraph -->'
    '<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->'
    '<div class="wp-block-buttons"><!-- wp:button {"backgroundColor":"vivid-cyan-blue"} -->'
    '<div class="wp-block-button"><a class="wp-block-button__link has-vivid-cyan-blue-background-color has-background wp-element-button" href="tel:690270032">\ud83d\udcde 690 270 032</a></div>'
    '<!-- /wp:button --></div><!-- /wp:buttons -->'
    '</div></div><!-- /wp:cover -->'

    # DLACZEGO HURGHADA
    '<!-- wp:group {"style":{"spacing":{"padding":{"top":"50px","bottom":"50px"}}}} -->'
    '<div class="wp-block-group" style="padding-top:50px;padding-bottom:50px">'
    '<!-- wp:heading {"level":2} --><h2 class="wp-block-heading">Dlaczego Hurghada?</h2><!-- /wp:heading -->'
    '<!-- wp:columns --><div class="wp-block-columns">'
    '<!-- wp:column --><div class="wp-block-column">'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li><strong>Wiatr 300 dni w roku</strong> \u2014 nie czekasz na pogod\u0119, jedziesz kiedy chcesz</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>P\u0142ytka zatoka</strong> \u2014 woda do kolan na setki metr\u00f3w, idealna do nauki</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>Ciep\u0142a woda ca\u0142y rok</strong> \u2014 szkolenie w szortach, \u017cadnego piankowca</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list --></div><!-- /wp:column -->'
    '<!-- wp:column --><div class="wp-block-column">'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li><strong>Cabrinha Test Center</strong> \u2014 testuj najnowszy sprz\u0119t na wodzie</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>Polscy instruktorzy</strong> \u2014 szkolenia po polsku i angielsku</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>Przeloty od 330 z\u0142</strong> \u2014 pomagamy znale\u017a\u0107 tani lot</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list --></div><!-- /wp:column -->'
    '</div><!-- /wp:columns -->'

    # PAKIETY
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"50px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:50px">Pakiety szkoleniowe</h2><!-- /wp:heading -->'
    '<!-- wp:columns {"style":{"spacing":{"blockGap":"20px"}}} --><div class="wp-block-columns">'

    # ZOLTY
    '<!-- wp:column {"style":{"color":{"background":"#fff8e1"},"spacing":{"padding":{"top":"30px","bottom":"30px","left":"25px","right":"25px"}},"border":{"radius":"12px"}}} -->'
    '<div class="wp-block-column" style="background-color:#fff8e1;padding:30px 25px;border-radius:12px">'
    '<!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">\ud83d\udfe1 Wariant \u017b\u00f3\u0142ty</h3><!-- /wp:heading -->'
    '<!-- wp:heading {"textAlign":"center","level":4} --><h4 class="wp-block-heading has-text-align-center">2 300 z\u0142</h4><!-- /wp:heading -->'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li>8h szkolenia kite</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>5 nocleg\u00f3w na spocie Play Kite</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>\u015aniadania w cenie</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Transfer z lotniska</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Pomoc przy znalezieniu lotu (od 330 z\u0142)</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list --></div><!-- /wp:column -->'

    # SREBRNY
    '<!-- wp:column {"style":{"color":{"background":"#e8e8e8"},"spacing":{"padding":{"top":"30px","bottom":"30px","left":"25px","right":"25px"}},"border":{"radius":"12px"}}} -->'
    '<div class="wp-block-column" style="background-color:#e8e8e8;padding:30px 25px;border-radius:12px">'
    '<!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">\u26aa Wariant Srebrny</h3><!-- /wp:heading -->'
    '<!-- wp:heading {"textAlign":"center","level":4} --><h4 class="wp-block-heading has-text-align-center">3 300 z\u0142</h4><!-- /wp:heading -->'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li>12h szkolenia kite</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>7 nocleg\u00f3w w mieszkaniu (kuchnia, klimatyzacja)</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>4 baseny w obiekcie Tiba View</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Transfer z lotniska</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Pomoc na miejscu 24/7</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Mo\u017cliwo\u015b\u0107 nurkowania</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list --></div><!-- /wp:column -->'

    # BEZ NOCLEGU
    '<!-- wp:column {"style":{"color":{"background":"#e3f2fd"},"spacing":{"padding":{"top":"30px","bottom":"30px","left":"25px","right":"25px"}},"border":{"radius":"12px"}}} -->'
    '<div class="wp-block-column" style="background-color:#e3f2fd;padding:30px 25px;border-radius:12px">'
    '<!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">\ud83d\udfe6 Bez noclegu</h3><!-- /wp:heading -->'
    '<!-- wp:heading {"textAlign":"center","level":4} --><h4 class="wp-block-heading has-text-align-center">od 1 910 z\u0142</h4><!-- /wp:heading -->'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li>8h szkolenia \u2014 1 910 z\u0142</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>12h szkolenia \u2014 2 640 z\u0142</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Pe\u0142na elastyczno\u015b\u0107 \u2014 sam decydujesz o noclegu</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Wsparcie na miejscu</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list --></div><!-- /wp:column -->'
    '</div><!-- /wp:columns -->'

    # CO ZABRAC
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"50px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:50px">Co zabra\u0107?</h2><!-- /wp:heading -->'
    '<!-- wp:columns --><div class="wp-block-columns">'
    '<!-- wp:column --><div class="wp-block-column">'
    '<!-- wp:paragraph --><p><strong>Niezb\u0119dne:</strong></p><!-- /wp:paragraph -->'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li>Paszport (wa\u017cny min. 6 msc)</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Krem z filtrem SPF 50+</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Okulary przeciws\u0142oneczne</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Szorty, koszulki, klapki</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list --></div><!-- /wp:column -->'
    '<!-- wp:column --><div class="wp-block-column">'
    '<!-- wp:paragraph --><p><strong>Opcjonalnie:</strong></p><!-- /wp:paragraph -->'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li>W\u0142asny sprz\u0119t kite (ale mamy na miejscu!)</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Lycra / rashguard</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>GoPro</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Dobry humor \ud83d\ude04</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list --></div><!-- /wp:column -->'
    '</div><!-- /wp:columns -->'

    # GALERIA
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Galeria</h2><!-- /wp:heading -->'
    '<!-- wp:gallery {"columns":3,"align":"wide"} -->'
    '<figure class="wp-block-gallery alignwide has-nested-images columns-3">'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["egipt2"]}" alt="Hurghada kite"/></figure><!-- /wp:image -->'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["egipt3"]}" alt="Hurghada spot"/></figure><!-- /wp:image -->'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["egipt4"]}" alt="Hurghada szkolenie"/></figure><!-- /wp:image -->'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["cab1"]}" alt="Cabrinha Hurghada"/></figure><!-- /wp:image -->'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["cab2"]}" alt="Kite Hurghada"/></figure><!-- /wp:image -->'
    f'<!-- wp:image --><figure class="wp-block-image"><img src="{IMG["cab3"]}" alt="FUN like HEL Egipt"/></figure><!-- /wp:image -->'
    '</figure><!-- /wp:gallery -->'

    # MAPA
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Lokalizacja</h2><!-- /wp:heading -->'
    '<!-- wp:paragraph --><p><a href="https://maps.app.goo.gl/31vLLyFcq4LbAwA96" target="_blank">\ud83d\udccd FUNLIKEHEL EGYPT, p\u00f3\u0142nocna Hurghada (27.3347, 33.6925)</a></p><!-- /wp:paragraph -->'
    '<!-- wp:html -->'
    '<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3500!2d33.6925!3d27.3347!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x1452653a6faee49d%3A0x9c73c2e88d773aa1!2sFUNLIKEHEL%20EGYPT%20Cabrinha%20Test%20Center!5e0!3m2!1spl!2spl" width="100%" height="350" style="border:0;border-radius:12px;" allowfullscreen="" loading="lazy"></iframe>'
    '<!-- /wp:html -->'

    # CTA
    '<!-- wp:group {"style":{"spacing":{"padding":{"top":"40px","bottom":"40px"}},"color":{"background":"#e8f4f8"}}} -->'
    '<div class="wp-block-group" style="background-color:#e8f4f8;padding-top:40px;padding-bottom:40px">'
    '<!-- wp:paragraph {"align":"center","style":{"typography":{"fontSize":"20px"}}} -->'
    '<p class="has-text-align-center" style="font-size:20px">\ud83d\udcde <strong>Zarezerwuj wyjazd:</strong> <a href="tel:690270032">690 270 032</a> &nbsp;|&nbsp; \u2709\ufe0f <a href="mailto:funlikehelbrand@gmail.com">funlikehelbrand@gmail.com</a></p>'
    '<!-- /wp:paragraph --></div><!-- /wp:group -->'
    '</div><!-- /wp:group -->'
)

result = api("POST", "/wp/v2/pages/2044", {"content": egipt})
print(f"  Egipt: {'OK' if isinstance(result, dict) and 'id' in result else 'ERR'}")

# =====================================================
# 3. STRONA GLOWNA — poprawki (linki do Jastarnia i Egipt, TikTok)
# =====================================================
print("\n=== 3. STRONA GLOWNA ===")

# Pobierz aktualny content
page = api("GET", "/wp/v2/pages/1329&context=edit")
if isinstance(page, dict) and 'content' in page:
    content = page['content']['raw']

    # Dodaj TikTok embed przed YouTube section (jesli nie ma)
    if 'tiktok' not in content.lower():
        tiktok_section = (
            '<!-- wp:group {"align":"full","style":{"spacing":{"padding":{"top":"60px","bottom":"60px"}},"color":{"background":"#000000"}}} -->'
            '<div class="wp-block-group alignfull" style="background-color:#000000;padding-top:60px;padding-bottom:60px">'
            '<!-- wp:heading {"textAlign":"center","level":2,"style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"36px"}}} -->'
            '<h2 class="wp-block-heading has-text-align-center" style="color:#ffffff;font-size:36px">TikTok @funlikehel</h2>'
            '<!-- /wp:heading -->'
            '<!-- wp:html -->'
            '<div style="max-width:600px;margin:20px auto;text-align:center">'
            '<blockquote class="tiktok-embed" cite="https://www.tiktok.com/@funlikehel" data-unique-id="funlikehel" data-embed-type="creator" style="max-width:780px;min-width:288px;">'
            '<section><a target="_blank" href="https://www.tiktok.com/@funlikehel">@funlikehel</a></section>'
            '</blockquote>'
            '<script async src="https://www.tiktok.com/embed.js"></script>'
            '</div>'
            '<!-- /wp:html -->'
            '<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->'
            '<div class="wp-block-buttons"><!-- wp:button {"className":"is-style-outline","style":{"color":{"text":"#ffffff"}}} -->'
            '<div class="wp-block-button is-style-outline"><a class="wp-block-button__link has-text-color wp-element-button" href="https://www.tiktok.com/@funlikehel" target="_blank" style="color:#ffffff">Zobacz na TikTok</a></div>'
            '<!-- /wp:button --></div><!-- /wp:buttons -->'
            '</div><!-- /wp:group -->'
        )

        # Wstaw przed sekcja YouTube (szukaj "Zobacz nas w akcji")
        yt_pos = content.find('Zobacz nas w akcji')
        if yt_pos > 0:
            # Znajdz poczatek grupy przed YouTube
            group_start = content.rfind('<!-- wp:group', 0, yt_pos)
            if group_start > 0:
                content = content[:group_start] + tiktok_section + '\n' + content[group_start:]
                print("  Dodano TikTok przed YouTube")
        else:
            # Wstaw przed CTA
            cta_pos = content.rfind('Masz pytanie')
            if cta_pos > 0:
                group_start = content.rfind('<!-- wp:cover', 0, cta_pos)
                if group_start > 0:
                    content = content[:group_start] + tiktok_section + '\n' + content[group_start:]
                    print("  Dodano TikTok przed CTA")

    result = api("POST", "/wp/v2/pages/1329", {"content": content})
    print(f"  Strona glowna: {'OK' if isinstance(result, dict) and 'id' in result else 'ERR'}")

# =====================================================
# 5. CHATBOT URL
# =====================================================
print("\n=== 5. CHATBOT ===")
print("  Widget JS uzywa URL: https://funlikehel-bot.onrender.com/api/chat")
print("  Aby zmienic, edytuj: server/static/chat-widget.js linia API_URL")
print("  Chatbot bedzie dzialal gdy serwer FastAPI jest uruchomiony pod tym adresem")

print("\n=== WSZYSTKO GOTOWE ===")
