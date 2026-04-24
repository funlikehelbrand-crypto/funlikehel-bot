"""
Update strony Egipt/Hurghada:
1. Fix CF7 form sender
2. Wstaw formularz CF7 na strone z cenami
3. Dodaj CSS styling + Google Ads conversion tracking
"""

import httpx
import base64
import json

WP_URL = "https://funlikehel.pl"
AUTH = base64.b64encode(b"Admin:PDlm Q9wV AKvP tvlK uUEa 64zw").decode()
H = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}
TIMEOUT = 60

# --- KROK 1: Fix CF7 sender ---
print("=== KROK 1: Fix CF7 sender ===")

r = httpx.put(
    f"{WP_URL}/wp-json/contact-form-7/v1/contact-forms/4",
    headers=H,
    json={
        "mail": {
            "active": True,
            "subject": "NOWA REZERWACJA Hurghada: [your-name] - [your-package]",
            "sender": "FUN like HEL <wordpress@funlikehel.pl>",
            "recipient": "funlikehelbrand@gmail.com",
            "body": (
                "NOWA REZERWACJA KURSU KITE W HURGHADZIE!\n\n"
                "Imie: [your-name]\n"
                "Email: [your-email]\n"
                "Telefon: [your-phone]\n"
                "Pakiet: [your-package]\n"
                "Termin: [your-dates]\n"
                "Poziom: [your-level]\n"
                "Liczba osob: [your-persons]\n"
                "Wiadomosc: [your-message]\n\n"
                "---\nOdpowiedz klientowi jak najszybciej!"
            ),
            "additional_headers": "Reply-To: [your-email]",
            "attachments": "",
            "use_html": False,
            "exclude_blank": False,
        },
        "mail_2": {
            "active": True,
            "subject": "Potwierdzenie rezerwacji - FUN like HEL Hurghada",
            "sender": "FUN like HEL <wordpress@funlikehel.pl>",
            "recipient": "[your-email]",
            "body": (
                "Czesc [your-name]!\n\n"
                "Dziekujemy za rezerwacje kursu kitesurfingu w Hurghadzie!\n\n"
                "Twoj wybrany pakiet: [your-package]\n"
                "Termin: [your-dates]\n\n"
                "Odezwiemy sie w ciagu 24h z potwierdzeniem i szczegolami.\n\n"
                "W razie pytan dzwon: 690 270 032\n\n"
                "Do zobaczenia na wodzie!\n"
                "Zespol FUN like HEL"
            ),
            "additional_headers": "",
            "attachments": "",
            "use_html": False,
            "exclude_blank": False,
        },
    },
    timeout=TIMEOUT,
    follow_redirects=True,
)

data = r.json()
errors = data.get("config_errors", {})
print(f"  Status: {r.status_code}")
if errors:
    for k, v in errors.items():
        print(f"  Warning {k}: {v[0]['message'] if v else '?'}")
else:
    print("  Brak bledow!")
print(f"  Sender: {data.get('properties', {}).get('mail', {}).get('sender', '?')}")


# --- KROK 2: Update strony Egipt ---
print("\n=== KROK 2: Update strony Egipt z formularzem ===")

# Oryginalny cennik + nowy formularz
egipt_content = (
    '<!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/10/1760544043687.jpg","id":1675,"dimRatio":50,"minHeight":500,"minHeightUnit":"px","align":"full"} -->\n'
    '<div class="wp-block-cover alignfull" style="min-height:500px">'
    '<span aria-hidden="true" class="wp-block-cover__background has-background-dim"></span>'
    '<img class="wp-block-cover__image-background wp-image-1675" alt="Hurghada Egipt kitesurfing FUN like HEL" '
    'src="https://funlikehel.pl/wp-content/uploads/2025/10/1760544043687.jpg" data-object-fit="cover"/>'
    '<div class="wp-block-cover__inner-container">'
    '<!-- wp:heading {"textAlign":"center","level":1,"style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"44px"}}} -->\n'
    '<h1 class="wp-block-heading has-text-align-center" style="color:#ffffff;font-size:44px">'
    'Hurghada, Egipt \u2014 Cabrinha Test Center</h1>\n'
    '<!-- /wp:heading -->\n'
    '<!-- wp:paragraph {"align":"center","style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"20px"}}} -->\n'
    '<p class="has-text-align-center" style="color:#ffffff;font-size:20px">'
    'Jedyna polska szko\u0142a kite z baz\u0105 zimow\u0105 w Egipcie. P\u0142ytka, ciep\u0142a woda, s\u0142o\u0144ce 300 dni w roku.</p>\n'
    '<!-- /wp:paragraph -->'
    '</div></div>\n'
    '<!-- /wp:cover -->\n\n'

    # --- Dlaczego Hurghada ---
    '<!-- wp:group {"style":{"spacing":{"padding":{"top":"50px","bottom":"50px"}}}} -->\n'
    '<div class="wp-block-group" style="padding-top:50px;padding-bottom:50px">'
    '<!-- wp:heading {"level":2} -->\n'
    '<h2 class="wp-block-heading">Dlaczego Hurghada?</h2>\n'
    '<!-- /wp:heading -->\n'
    '<!-- wp:list -->\n'
    '<ul>'
    '<!-- wp:list-item --><li><strong>Wiatr 300 dni w roku</strong> \u2014 nie czekasz na pogod\u0119, jedziesz kiedy chcesz</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>P\u0142ytka zatoka</strong> \u2014 woda do kolan na setki metr\u00f3w, idealna do nauki</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>Ciep\u0142a woda ca\u0142y rok</strong> \u2014 \u017cadnego piankowca, szkolenie w szortach</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>Cabrinha Test Center</strong> \u2014 testuj najnowszy sprz\u0119t przed zakupem</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>Polscy instruktorzy</strong> \u2014 szkolenia po polsku i angielsku</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><strong>Przeloty od 330 z\u0142</strong> \u2014 pomagamy znale\u017a\u0107 tani lot</li><!-- /wp:list-item -->'
    '</ul>\n'
    '<!-- /wp:list -->\n\n'

    # --- Pakiety ---
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"50px"}}}} -->\n'
    '<h2 class="wp-block-heading" style="margin-top:50px">Pakiety szkoleniowe</h2>\n'
    '<!-- /wp:heading -->\n\n'

    '<!-- wp:columns {"style":{"spacing":{"blockGap":"24px"}}} -->\n'
    '<div class="wp-block-columns">'

    # Zolty
    '<!-- wp:column {"style":{"color":{"background":"#fff8e1"},"spacing":{"padding":{"top":"30px","bottom":"30px","left":"25px","right":"25px"}}}} -->\n'
    '<div class="wp-block-column" style="background-color:#fff8e1;padding:30px 25px">'
    '<!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">\ud83d\udfe1 Wariant \u017b\u00f3\u0142ty</h3><!-- /wp:heading -->\n'
    '<!-- wp:heading {"textAlign":"center","level":4} --><h4 class="wp-block-heading has-text-align-center">2300 z\u0142</h4><!-- /wp:heading -->\n'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li>8 godzin szkolenia kite</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>5 nocleg\u00f3w na spocie Play Kite</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>\u015aniadania w cenie</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Transfer z lotniska</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Pomoc przy znalezieniu lotu</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list -->\n'
    '<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->\n'
    '<div class="wp-block-buttons"><!-- wp:button {"style":{"color":{"background":"#f9a825","text":"#000000"}}} -->\n'
    '<div class="wp-block-button"><a class="wp-block-button__link has-text-color has-background" href="#rezerwacja" style="background-color:#f9a825;color:#000000">Rezerwuj Wariant \u017b\u00f3\u0142ty</a></div>\n'
    '<!-- /wp:button --></div>\n'
    '<!-- /wp:buttons -->'
    '</div>\n'
    '<!-- /wp:column -->\n'

    # Srebrny
    '<!-- wp:column {"style":{"color":{"background":"#e8e8e8"},"spacing":{"padding":{"top":"30px","bottom":"30px","left":"25px","right":"25px"}}}} -->\n'
    '<div class="wp-block-column" style="background-color:#e8e8e8;padding:30px 25px">'
    '<!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">\u26aa Wariant Srebrny</h3><!-- /wp:heading -->\n'
    '<!-- wp:heading {"textAlign":"center","level":4} --><h4 class="wp-block-heading has-text-align-center">3300 z\u0142</h4><!-- /wp:heading -->\n'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li>12 godzin szkolenia kite</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>7 nocleg\u00f3w w mieszkaniu (klimatyzacja, kuchnia)</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>4 baseny w obiekcie Tiba View</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Transfer z lotniska</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Pomoc na miejscu 24/7</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Mo\u017cliwo\u015b\u0107 nurkowania</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list -->\n'
    '<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->\n'
    '<div class="wp-block-buttons"><!-- wp:button {"style":{"color":{"background":"#9e9e9e","text":"#000000"}}} -->\n'
    '<div class="wp-block-button"><a class="wp-block-button__link has-text-color has-background" href="#rezerwacja" style="background-color:#9e9e9e;color:#000000">Rezerwuj Wariant Srebrny</a></div>\n'
    '<!-- /wp:button --></div>\n'
    '<!-- /wp:buttons -->'
    '</div>\n'
    '<!-- /wp:column -->\n'

    # Bez noclegu
    '<!-- wp:column {"style":{"color":{"background":"#e3f2fd"},"spacing":{"padding":{"top":"30px","bottom":"30px","left":"25px","right":"25px"}}}} -->\n'
    '<div class="wp-block-column" style="background-color:#e3f2fd;padding:30px 25px">'
    '<!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">\ud83d\udfe6 Bez noclegu</h3><!-- /wp:heading -->\n'
    '<!-- wp:heading {"textAlign":"center","level":4} --><h4 class="wp-block-heading has-text-align-center">od 1910 z\u0142</h4><!-- /wp:heading -->\n'
    '<!-- wp:list --><ul>'
    '<!-- wp:list-item --><li>8h szkolenia \u2014 1910 z\u0142</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>12h szkolenia \u2014 2640 z\u0142</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Pe\u0142na elastyczno\u015b\u0107</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Sam decydujesz o noclegu i wy\u017cywieniu</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li>Wsparcie na miejscu</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list -->\n'
    '<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->\n'
    '<div class="wp-block-buttons"><!-- wp:button {"style":{"color":{"background":"#42a5f5","text":"#ffffff"}}} -->\n'
    '<div class="wp-block-button"><a class="wp-block-button__link has-text-color has-background" href="#rezerwacja" style="background-color:#42a5f5;color:#ffffff">Rezerwuj bez noclegu</a></div>\n'
    '<!-- /wp:button --></div>\n'
    '<!-- /wp:buttons -->'
    '</div>\n'
    '<!-- /wp:column -->'

    '</div>\n'
    '<!-- /wp:columns -->\n\n'

    '<!-- wp:paragraph {"style":{"typography":{"fontSize":"14px"}}} -->\n'
    '<p style="font-size:14px"><a href="https://maps.app.goo.gl/31vLLyFcq4LbAwA96" target="_blank">'
    '\ud83d\udccd Poka\u017c na mapie: FUNLIKEHEL EGYPT, Hurghada (27.3347, 33.6925)</a></p>\n'
    '<!-- /wp:paragraph -->\n\n'

    '</div>\n'
    '<!-- /wp:group -->\n\n'

    # ================= FORMULARZ REZERWACJI =================
    '<!-- wp:group {"style":{"spacing":{"padding":{"top":"50px","bottom":"50px"}},"color":{"background":"#1a3a2a"}}} -->\n'
    '<div class="wp-block-group" style="background-color:#1a3a2a;padding-top:50px;padding-bottom:50px">\n\n'

    '<!-- wp:heading {"textAlign":"center","level":2,"style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"36px"}}} -->\n'
    '<h2 class="wp-block-heading has-text-align-center" style="color:#ffffff;font-size:36px" id="rezerwacja">'
    'Zarezerwuj kurs w Hurghadzie</h2>\n'
    '<!-- /wp:heading -->\n\n'

    '<!-- wp:paragraph {"align":"center","style":{"color":{"text":"#b0d4c1"},"typography":{"fontSize":"16px"}}} -->\n'
    '<p class="has-text-align-center" style="color:#b0d4c1;font-size:16px">'
    'Wypelnij formularz \u2014 odezwiemy sie w ciagu 24h z potwierdzeniem i szczegolami.</p>\n'
    '<!-- /wp:paragraph -->\n\n'

    '<!-- wp:html -->\n'
    '<style>\n'
    '.rezerwacja-wrap{max-width:620px;margin:30px auto 0}\n'
    '.rezerwacja-wrap .wpcf7-form label{display:block;color:#b0d4c1;font-size:14px;margin-bottom:4px;font-weight:600}\n'
    '.rezerwacja-wrap .wpcf7-form input[type=text],\n'
    '.rezerwacja-wrap .wpcf7-form input[type=email],\n'
    '.rezerwacja-wrap .wpcf7-form input[type=tel],\n'
    '.rezerwacja-wrap .wpcf7-form input[type=number],\n'
    '.rezerwacja-wrap .wpcf7-form select,\n'
    '.rezerwacja-wrap .wpcf7-form textarea{width:100%;padding:12px 14px;border:2px solid #2d5a3f;border-radius:8px;font-size:16px;background:#0d1f16;color:#fff;box-sizing:border-box;margin-bottom:16px;transition:border-color .2s}\n'
    '.rezerwacja-wrap .wpcf7-form input:focus,\n'
    '.rezerwacja-wrap .wpcf7-form select:focus,\n'
    '.rezerwacja-wrap .wpcf7-form textarea:focus{border-color:#4CAF50;outline:none}\n'
    '.rezerwacja-wrap .wpcf7-form input::placeholder,\n'
    '.rezerwacja-wrap .wpcf7-form textarea::placeholder{color:#5a8a6a}\n'
    '.rezerwacja-wrap .wpcf7-form select{cursor:pointer;appearance:auto}\n'
    '.rezerwacja-wrap .wpcf7-form select option{background:#0d1f16;color:#fff}\n'
    '.rezerwacja-wrap .flh-row{display:flex;gap:16px}\n'
    '.rezerwacja-wrap .flh-row>div{flex:1}\n'
    '.rezerwacja-wrap .wpcf7-form .flh-btn,\n'
    '.rezerwacja-wrap .wpcf7-form input[type=submit]{display:block;width:100%;padding:16px;background:#4CAF50;color:#fff;font-size:18px;font-weight:700;border:none;border-radius:8px;cursor:pointer;margin-top:8px;transition:background .2s}\n'
    '.rezerwacja-wrap .wpcf7-form input[type=submit]:hover{background:#45a049}\n'
    '.rezerwacja-wrap .wpcf7-response-output{color:#4CAF50;text-align:center;border:none!important;font-size:16px;padding:20px!important}\n'
    '.rezerwacja-wrap .wpcf7-not-valid-tip{color:#ff6b6b;font-size:13px}\n'
    '@media(max-width:600px){.rezerwacja-wrap .flh-row{flex-direction:column;gap:0}}\n'
    '</style>\n'
    '<div class="rezerwacja-wrap">\n'
    '[contact-form-7 id="4" title="Rezerwacja Hurghada"]\n'
    '</div>\n'
    '<script>\n'
    'document.addEventListener("wpcf7mailsent",function(e){\n'
    '  if(e.detail.contactFormId==4 && typeof gtag==="function"){\n'
    '    gtag("event","conversion",{"send_to":"AW-8974478964/hurghada_rezerwacja","value":2300,"currency":"PLN"});\n'
    '  }\n'
    '});\n'
    '</script>\n'
    '<!-- /wp:html -->\n\n'

    '</div>\n'
    '<!-- /wp:group -->\n\n'

    # --- CTA telefon/email ---
    '<!-- wp:group {"style":{"spacing":{"padding":{"top":"30px","bottom":"30px"}},"color":{"background":"#e8f4f8"}}} -->\n'
    '<div class="wp-block-group" style="background-color:#e8f4f8;padding-top:30px;padding-bottom:30px">'
    '<!-- wp:paragraph {"align":"center","style":{"typography":{"fontSize":"20px"}}} -->\n'
    '<p class="has-text-align-center" style="font-size:20px">'
    '\ud83d\udcde <strong>Wolisz zadzwoni\u0107?</strong> <a href="tel:690270032">690 270 032</a>'
    ' &nbsp;|&nbsp; \u2709\ufe0f <a href="mailto:funlikehelbrand@gmail.com">funlikehelbrand@gmail.com</a></p>\n'
    '<!-- /wp:paragraph --></div>\n'
    '<!-- /wp:group -->'
)

r2 = httpx.post(
    f"{WP_URL}/?rest_route=/wp/v2/pages/2044",
    headers=H,
    json={
        "title": "Egipt \u2014 Hurghada | Cabrinha Test Center",
        "slug": "egipt-hurghada",
        "content": egipt_content,
        "status": "publish",
    },
    timeout=TIMEOUT,
    follow_redirects=True,
)

print(f"  Status: {r2.status_code}")
if r2.status_code == 200:
    page = r2.json()
    print(f"  Page ID: {page['id']}")
    print(f"  Link: {page['link']}")
    print(f"  STRONA ZAKTUALIZOWANA!")
else:
    print(f"  Error: {r2.text[:500]}")


# --- KROK 3: Test CF7 submission ---
print("\n=== KROK 3: Test formularza CF7 ===")

r3 = httpx.post(
    f"{WP_URL}/wp-json/contact-form-7/v1/contact-forms/4/feedback",
    data={
        "your-name": "Test Deploy",
        "your-email": "test@test.pl",
        "your-phone": "+48000000000",
        "your-package": "Wariant Zolty - 2300 zl (8h kite + 5 noclegow)",
        "your-dates": "test deploy",
        "your-level": "Poczatkujacy",
        "your-persons": "1",
        "your-message": "test deploy - ignoruj",
    },
    timeout=TIMEOUT,
    follow_redirects=True,
)

print(f"  Status: {r3.status_code}")
if r3.status_code == 200:
    data = r3.json()
    print(f"  CF7 status: {data.get('status')}")
    print(f"  Message: {data.get('message')}")
    if data.get("status") == "mail_sent":
        print("  FORMULARZ DZIALA! Email wyslany!")
    else:
        print(f"  Response: {json.dumps(data, indent=2)[:300]}")
else:
    print(f"  Error: {r3.text[:300]}")


print("\n" + "=" * 60)
print("GOTOWE!")
print(f"Strona: {WP_URL}/egipt-hurghada/")
print(f"Formularz: {WP_URL}/egipt-hurghada/#rezerwacja")
print(f"Google Ads conversion: AW-8974478964/hurghada_rezerwacja")
print("=" * 60)
