"""
Deploy pluginu funlikehel-rezerwacja + formularz na stronie Egipt/Hurghada.

Krok 1: Upload ZIP pluginu na WordPress
Krok 2: Aktywacja pluginu
Krok 3: Update strony Egipt (page 2044) — dodanie formularza rezerwacji pod cennik
Krok 4: Update trackingu Google Ads na stronie Egipt
Krok 5: Test endpointu

Uruchomienie:
    cd funlikehel
    python deploy_rezerwacja.py
"""

import httpx
import base64
import re
import time
import zipfile
import os
import json

# ---- CONFIG ----
WP_URL = "https://funlikehel.pl"
WP_USER = "Admin"
WP_APP_PASSWORD = "PDlm Q9wV AKvP tvlK uUEa 64zw"
AUTH = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()

PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "server", "wp-plugin")
PHP_FILE = os.path.join(PLUGIN_DIR, "funlikehel-rezerwacja.php")
ZIP_PATH = os.path.join(PLUGIN_DIR, "funlikehel-rezerwacja.zip")

PLUGIN_SLUG = "funlikehel-rezerwacja/funlikehel-rezerwacja"
API_URL = f"{WP_URL}/wp-json/funlikehel/v1/rezerwacja"
EGIPT_PAGE_ID = 2044
MAX_RETRIES = 5
TIMEOUT = 45


def create_zip():
    """Tworzy ZIP pluginu."""
    print("\n=== Tworzenie ZIP pluginu ===")
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(PHP_FILE, "funlikehel-rezerwacja/funlikehel-rezerwacja.php")
    print(f"  ZIP: {ZIP_PATH}")
    return True


def rest_api(method, route, data=None, retry=MAX_RETRIES):
    """WordPress REST API call with retries."""
    headers = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}
    url = f"{WP_URL}/wp-json{route}"

    for attempt in range(1, retry + 1):
        try:
            if method == "GET":
                r = httpx.get(url, headers=headers, timeout=TIMEOUT, follow_redirects=True)
            elif method == "POST":
                r = httpx.post(url, headers=headers, json=data, timeout=TIMEOUT, follow_redirects=True)
            elif method == "PUT":
                r = httpx.put(url, headers=headers, json=data, timeout=TIMEOUT, follow_redirects=True)
            return r
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
            print(f"  Proba {attempt}/{retry} timeout: {type(e).__name__}")
            if attempt < retry:
                time.sleep(3)
    return None


def rest_api_alt(method, route, data=None, retry=MAX_RETRIES):
    """WordPress REST API via ?rest_route= (backup format)."""
    headers = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}
    url = f"{WP_URL}/?rest_route={route}"

    for attempt in range(1, retry + 1):
        try:
            if method == "GET":
                r = httpx.get(url, headers=headers, timeout=TIMEOUT, follow_redirects=True)
            elif method == "POST":
                r = httpx.post(url, headers=headers, json=data, timeout=TIMEOUT, follow_redirects=True)
            return r
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
            print(f"  [alt] Proba {attempt}/{retry} timeout: {type(e).__name__}")
            if attempt < retry:
                time.sleep(3)
    return None


def step1_upload():
    """Login do wp-admin i upload pluginu ZIP."""
    print("\n=== KROK 1: Login + Upload pluginu ===")

    client = httpx.Client(follow_redirects=True, timeout=TIMEOUT)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  Proba logowania {attempt}/{MAX_RETRIES}...")

            r = client.post(f"{WP_URL}/wp-login.php", data={
                "log": WP_USER,
                "pwd": WP_APP_PASSWORD,
                "wp-submit": "Log In",
                "testcookie": "1",
                "redirect_to": "/wp-admin/",
            })

            cookies = dict(client.cookies)
            logged_in = any("logged_in" in k for k in cookies)

            if not logged_in:
                print(f"  Login failed (status {r.status_code})")
                if attempt < MAX_RETRIES:
                    time.sleep(5)
                continue

            print("  Zalogowano do wp-admin!")

            r2 = client.get(f"{WP_URL}/wp-admin/plugin-install.php?tab=upload")
            nonce_match = re.search(r'name="_wpnonce" value="([a-f0-9]+)"', r2.text)

            if not nonce_match:
                print("  Nie znaleziono nonce na stronie uploadu")
                continue

            nonce = nonce_match.group(1)
            print(f"  Nonce: {nonce}")

            with open(ZIP_PATH, "rb") as f:
                r3 = client.post(
                    f"{WP_URL}/wp-admin/update.php?action=upload-plugin",
                    files={"pluginzip": ("funlikehel-rezerwacja.zip", f, "application/zip")},
                    data={"_wpnonce": nonce, "install-plugin-submit": "Zainstaluj"},
                )

            if r3.status_code == 200:
                body = r3.text.lower()
                if "successfully" in body or "zainstalowana" in body or "installed" in body:
                    print("  PLUGIN ZAINSTALOWANY!")
                    client.close()
                    return True
                elif "already" in body or "istnieje" in body or "jest już" in body:
                    print("  Plugin juz istnieje — OK")
                    client.close()
                    return True
                else:
                    msgs = re.findall(r'<p[^>]*>([^<]{5,})</p>', r3.text)
                    for m in msgs[:5]:
                        print(f"  msg: {m.strip()}")
            else:
                print(f"  Upload HTTP {r3.status_code}")

        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
            print(f"  Timeout: {type(e).__name__}")
            if attempt < MAX_RETRIES:
                time.sleep(5)

    client.close()
    return False


def step2_activate():
    """Aktywacja pluginu przez REST API."""
    print("\n=== KROK 2: Aktywacja pluginu ===")

    r = rest_api("GET", "/wp/v2/plugins")
    if not r or r.status_code != 200:
        r = rest_api_alt("GET", "/wp/v2/plugins")

    if not r or r.status_code != 200:
        print("  Nie moge pobrac listy pluginow")
        return False

    plugins = r.json()
    target = None
    for p in plugins:
        if "rezerwacja" in p.get("plugin", "").lower():
            target = p
            break

    if not target:
        print("  Plugin funlikehel-rezerwacja NIE znaleziony na serwerze")
        return False

    print(f"  Znaleziono plugin: {target['plugin']} (status: {target['status']})")

    if target["status"] == "active":
        print("  Plugin juz aktywny!")
        return True

    plugin_file = target["plugin"]
    r = rest_api("POST", f"/wp/v2/plugins/{plugin_file}", {"status": "active"})
    if not r:
        r = rest_api_alt("POST", f"/wp/v2/plugins/{plugin_file}", {"status": "active"})

    if r and r.status_code == 200:
        print("  PLUGIN AKTYWOWANY!")
        return True
    else:
        print(f"  Blad aktywacji: {r.status_code if r else 'timeout'}")
        if r:
            print(f"  {r.text[:200]}")
        return False


def step3_update_page():
    """Update strony Egipt — dodanie formularza rezerwacji."""
    print("\n=== KROK 3: Update strony Egipt z formularzem ===")

    # Formularz HTML wbudowany w WordPress block
    form_block = """
<!-- wp:group {"style":{"spacing":{"padding":{"top":"50px","bottom":"50px"}},"color":{"background":"#1a3a2a"}},"className":"rezerwacja-hurghada"} -->
<div class="wp-block-group rezerwacja-hurghada" style="background-color:#1a3a2a;padding-top:50px;padding-bottom:50px">

<!-- wp:heading {"textAlign":"center","level":2,"style":{"color":{"text":"#ffffff"},"typography":{"fontSize":"36px"}}} -->
<h2 class="wp-block-heading has-text-align-center" style="color:#ffffff;font-size:36px" id="rezerwacja">Zarezerwuj kurs w Hurghadzie</h2>
<!-- /wp:heading -->

<!-- wp:paragraph {"align":"center","style":{"color":{"text":"#b0d4c1"},"typography":{"fontSize":"16px"}}} -->
<p class="has-text-align-center" style="color:#b0d4c1;font-size:16px">Wypelnij formularz — odezwiemy sie w ciagu 24h z potwierdzeniem i szczegolami.</p>
<!-- /wp:paragraph -->

<!-- wp:html -->
<style>
.flh-form{max-width:600px;margin:30px auto 0;font-family:system-ui,-apple-system,sans-serif}
.flh-form label{display:block;color:#b0d4c1;font-size:14px;margin-bottom:4px;font-weight:600}
.flh-form input,.flh-form select,.flh-form textarea{width:100%;padding:12px 14px;border:2px solid #2d5a3f;border-radius:8px;font-size:16px;background:#0d1f16;color:#ffffff;box-sizing:border-box;margin-bottom:16px;transition:border-color .2s}
.flh-form input:focus,.flh-form select:focus,.flh-form textarea:focus{border-color:#4CAF50;outline:none}
.flh-form input::placeholder,.flh-form textarea::placeholder{color:#5a8a6a}
.flh-form select{cursor:pointer;appearance:auto}
.flh-form select option{background:#0d1f16;color:#fff}
.flh-row{display:flex;gap:16px}
.flh-row>div{flex:1}
.flh-btn{display:block;width:100%;padding:16px;background:#4CAF50;color:#fff;font-size:18px;font-weight:700;border:none;border-radius:8px;cursor:pointer;margin-top:8px;transition:background .2s}
.flh-btn:hover{background:#45a049}
.flh-btn:disabled{background:#2d5a3f;cursor:wait}
.flh-ok{text-align:center;padding:30px;color:#4CAF50;font-size:20px;font-weight:600;display:none}
.flh-err{color:#ff6b6b;font-size:14px;text-align:center;margin-top:8px;display:none}
@media(max-width:600px){.flh-row{flex-direction:column;gap:0}}
</style>

<div class="flh-form" id="flhForm">
  <form id="rezerwacjaForm" onsubmit="return false;">
    <label for="flh_name">Imie i nazwisko *</label>
    <input type="text" id="flh_name" name="name" placeholder="Jan Kowalski" required>

    <div class="flh-row">
      <div>
        <label for="flh_email">Email *</label>
        <input type="email" id="flh_email" name="email" placeholder="jan@email.com" required>
      </div>
      <div>
        <label for="flh_phone">Telefon *</label>
        <input type="tel" id="flh_phone" name="phone" placeholder="+48 600 000 000" required>
      </div>
    </div>

    <label for="flh_package">Wybierz pakiet *</label>
    <select id="flh_package" name="package" required>
      <option value="" disabled selected>-- Wybierz pakiet --</option>
      <option value="zolty">Wariant Zolty — 2300 zl (8h kite + 5 noclegow)</option>
      <option value="srebrny">Wariant Srebrny — 3300 zl (12h kite + 7 noclegow)</option>
      <option value="bez_8h">Bez noclegu — 8h szkolenia (1910 zl)</option>
      <option value="bez_12h">Bez noclegu — 12h szkolenia (2640 zl)</option>
    </select>

    <label for="flh_dates">Preferowany termin wyjazdu</label>
    <input type="text" id="flh_dates" name="dates" placeholder="np. styczen 2027, luty-marzec, elastyczny">

    <div class="flh-row">
      <div>
        <label for="flh_level">Poziom zaawansowania</label>
        <select id="flh_level" name="level">
          <option value="" disabled selected>-- Wybierz --</option>
          <option value="poczatkujacy">Poczatkujacy (nigdy nie probowalem)</option>
          <option value="podstawowy">Podstawowy (mialem kilka lekcji)</option>
          <option value="sredni">Sredniozaawansowany (jezdze samodzielnie)</option>
          <option value="zaawansowany">Zaawansowany (chce sie rozwijac)</option>
        </select>
      </div>
      <div>
        <label for="flh_persons">Liczba osob</label>
        <input type="number" id="flh_persons" name="persons" value="1" min="1" max="20">
      </div>
    </div>

    <label for="flh_message">Dodatkowe pytania / uwagi</label>
    <textarea id="flh_message" name="message" rows="3" placeholder="Np. czy mozna pojechal z dzieckiem? Potrzebuje sprzetu..."></textarea>

    <button type="submit" class="flh-btn" id="flhSubmit">Wyslij rezerwacje</button>
    <div class="flh-err" id="flhErr"></div>
  </form>
  <div class="flh-ok" id="flhOk"></div>
</div>

<script>
(function(){
  var form = document.getElementById('rezerwacjaForm');
  var btn  = document.getElementById('flhSubmit');
  var err  = document.getElementById('flhErr');
  var ok   = document.getElementById('flhOk');

  form.addEventListener('submit', function(e){
    e.preventDefault();
    err.style.display='none';
    btn.disabled=true;
    btn.textContent='Wysylam...';

    var data = {
      name:    document.getElementById('flh_name').value.trim(),
      email:   document.getElementById('flh_email').value.trim(),
      phone:   document.getElementById('flh_phone').value.trim(),
      package: document.getElementById('flh_package').value,
      dates:   document.getElementById('flh_dates').value.trim(),
      level:   document.getElementById('flh_level').value,
      persons: parseInt(document.getElementById('flh_persons').value) || 1,
      message: document.getElementById('flh_message').value.trim()
    };

    if(!data.name || !data.email || !data.phone || !data.package){
      err.textContent='Wypelnij wszystkie wymagane pola (*)';
      err.style.display='block';
      btn.disabled=false;
      btn.textContent='Wyslij rezerwacje';
      return;
    }

    fetch('/wp-json/funlikehel/v1/rezerwacja', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(data)
    })
    .then(function(r){ return r.json(); })
    .then(function(resp){
      if(resp.status==='ok'){
        form.style.display='none';
        ok.textContent=resp.message;
        ok.style.display='block';
        // Google Ads conversion tracking
        if(typeof gtag==='function'){
          gtag('event','conversion',{
            'send_to':'AW-8974478964/hurghada_rezerwacja',
            'value': data.package==='srebrny' ? 3300 : data.package==='zolty' ? 2300 : data.package==='bez_12h' ? 2640 : 1910,
            'currency':'PLN'
          });
        }
      } else {
        err.textContent=resp.message || 'Cos poszlo nie tak. Sprobuj ponownie.';
        err.style.display='block';
        btn.disabled=false;
        btn.textContent='Wyslij rezerwacje';
      }
    })
    .catch(function(){
      err.textContent='Blad polaczenia. Sprobuj ponownie lub zadzwon: 690 270 032';
      err.style.display='block';
      btn.disabled=false;
      btn.textContent='Wyslij rezerwacje';
    });
  });
})();
</script>
<!-- /wp:html -->

</div>
<!-- /wp:group -->"""

    # Pelna tresc strony Egipt: oryginalny cennik + formularz
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
<!-- wp:list --><ul><!-- wp:list-item --><li>8 godzin szkolenia kite</li><!-- /wp:list-item --><!-- wp:list-item --><li>5 nocleg\u00f3w na spocie Play Kite</li><!-- /wp:list-item --><!-- wp:list-item --><li>\u015aniadania w cenie</li><!-- /wp:list-item --><!-- wp:list-item --><li>Transfer z lotniska</li><!-- /wp:list-item --><!-- wp:list-item --><li>Pomoc przy znalezieniu lotu</li><!-- /wp:list-item --></ul><!-- /wp:list -->
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->
<div class="wp-block-buttons"><!-- wp:button {"style":{"color":{"background":"#f9a825","text":"#000000"}}} -->
<div class="wp-block-button"><a class="wp-block-button__link has-text-color has-background" href="#rezerwacja" style="background-color:#f9a825;color:#000000">Rezerwuj Wariant \u017b\u00f3\u0142ty</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:column -->
<!-- wp:column {"style":{"color":{"background":"#e8e8e8"},"spacing":{"padding":{"top":"30px","bottom":"30px","left":"25px","right":"25px"}}}} -->
<div class="wp-block-column" style="background-color:#e8e8e8;padding:30px 25px"><!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">\u26aa Wariant Srebrny</h3><!-- /wp:heading -->
<!-- wp:heading {"textAlign":"center","level":4} --><h4 class="wp-block-heading has-text-align-center">3300 z\u0142</h4><!-- /wp:heading -->
<!-- wp:list --><ul><!-- wp:list-item --><li>12 godzin szkolenia kite</li><!-- /wp:list-item --><!-- wp:list-item --><li>7 nocleg\u00f3w w mieszkaniu (klimatyzacja, kuchnia)</li><!-- /wp:list-item --><!-- wp:list-item --><li>4 baseny w obiekcie Tiba View</li><!-- /wp:list-item --><!-- wp:list-item --><li>Transfer z lotniska</li><!-- /wp:list-item --><!-- wp:list-item --><li>Pomoc na miejscu 24/7</li><!-- /wp:list-item --><!-- wp:list-item --><li>Mo\u017cliwo\u015b\u0107 nurkowania</li><!-- /wp:list-item --></ul><!-- /wp:list -->
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->
<div class="wp-block-buttons"><!-- wp:button {"style":{"color":{"background":"#9e9e9e","text":"#000000"}}} -->
<div class="wp-block-button"><a class="wp-block-button__link has-text-color has-background" href="#rezerwacja" style="background-color:#9e9e9e;color:#000000">Rezerwuj Wariant Srebrny</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:column -->
<!-- wp:column {"style":{"color":{"background":"#e3f2fd"},"spacing":{"padding":{"top":"30px","bottom":"30px","left":"25px","right":"25px"}}}} -->
<div class="wp-block-column" style="background-color:#e3f2fd;padding:30px 25px"><!-- wp:heading {"textAlign":"center","level":3} --><h3 class="wp-block-heading has-text-align-center">\ud83d\udfe6 Bez noclegu</h3><!-- /wp:heading -->
<!-- wp:heading {"textAlign":"center","level":4} --><h4 class="wp-block-heading has-text-align-center">od 1910 z\u0142</h4><!-- /wp:heading -->
<!-- wp:list --><ul><!-- wp:list-item --><li>8h szkolenia \u2014 1910 z\u0142</li><!-- /wp:list-item --><!-- wp:list-item --><li>12h szkolenia \u2014 2640 z\u0142</li><!-- /wp:list-item --><!-- wp:list-item --><li>Pe\u0142na elastyczno\u015b\u0107</li><!-- /wp:list-item --><!-- wp:list-item --><li>Sam decydujesz o noclegu i wy\u017cywieniu</li><!-- /wp:list-item --><!-- wp:list-item --><li>Wsparcie na miejscu</li><!-- /wp:list-item --></ul><!-- /wp:list -->
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->
<div class="wp-block-buttons"><!-- wp:button {"style":{"color":{"background":"#42a5f5","text":"#ffffff"}}} -->
<div class="wp-block-button"><a class="wp-block-button__link has-text-color has-background" href="#rezerwacja" style="background-color:#42a5f5;color:#ffffff">Rezerwuj bez noclegu</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->

<!-- wp:paragraph {"style":{"typography":{"fontSize":"14px"}}} -->
<p style="font-size:14px"><a href="https://maps.app.goo.gl/31vLLyFcq4LbAwA96" target="_blank">\ud83d\udccd Poka\u017c na mapie: FUNLIKEHEL EGYPT, Hurghada (27.3347, 33.6925)</a></p>
<!-- /wp:paragraph -->

</div>
<!-- /wp:group -->""" + form_block + """

<!-- wp:group {"style":{"spacing":{"padding":{"top":"30px","bottom":"30px"}},"color":{"background":"#e8f4f8"}}} -->
<div class="wp-block-group" style="background-color:#e8f4f8;padding-top:30px;padding-bottom:30px"><!-- wp:paragraph {"align":"center","style":{"typography":{"fontSize":"20px"}}} -->
<p class="has-text-align-center" style="font-size:20px">\ud83d\udcde <strong>Wolisz zadzwonic?</strong> <a href="tel:690270032">690 270 032</a> &nbsp;|&nbsp; \u2709\ufe0f <a href="mailto:funlikehelbrand@gmail.com">funlikehelbrand@gmail.com</a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->"""

    r = rest_api_alt("POST", f"/wp/v2/pages/{EGIPT_PAGE_ID}", {
        "title": "Egipt \u2014 Hurghada | Cabrinha Test Center",
        "slug": "egipt-hurghada",
        "content": egipt_content,
        "status": "publish",
    })
    if not r:
        r = rest_api("POST", f"/wp/v2/pages/{EGIPT_PAGE_ID}", {
            "title": "Egipt \u2014 Hurghada | Cabrinha Test Center",
            "slug": "egipt-hurghada",
            "content": egipt_content,
            "status": "publish",
        })

    if r and r.status_code == 200:
        print("  STRONA EGIPT ZAKTUALIZOWANA z formularzem rezerwacji!")
        return True
    else:
        print(f"  Blad update: {r.status_code if r else 'timeout'}")
        if r:
            print(f"  {r.text[:300]}")
        return False


def step4_update_gtag():
    """Update pluginu gtag — dodanie trackingu konwersji na stronie Egipt."""
    print("\n=== KROK 4: Update Google Ads tracking ===")

    gtag_path = os.path.join(PLUGIN_DIR, "funlikehel-gtag.php")
    with open(gtag_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Sprawdz czy tracking Egipt juz dodany
    if "2044" in content or "hurghada" in content.lower():
        print("  Tracking Egipt/Hurghada juz w pliku gtag — OK")
        return True

    # Dodaj tracking formularza na stronie Egipt
    new_tracking = """
/**
 * 4. Sledzenie konwersji "Rezerwacja Hurghada" na stronie egipt-hurghada (page ID 2044)
 */
add_action('wp_footer', 'flh_hurghada_tracking');
function flh_hurghada_tracking() {
    if (!is_page(2044)) return;
    ?>
<!-- Google Ads: sledzenie konwersji rezerwacji Hurghada -->
<script>
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('form').forEach(function(form) {
    form.addEventListener('submit', function() {
      if (typeof gtag === 'function') {
        gtag('event', 'conversion', {
          'send_to': 'AW-8974478964/hurghada_rezerwacja',
          'event_callback': function() {}
        });
      }
    });
  });
});
</script>
    <?php
}
"""

    # Dopisz przed zamykajacym tagiem lub na koncu
    content = content.rstrip() + "\n" + new_tracking
    with open(gtag_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("  Dodano tracking konwersji Hurghada do funlikehel-gtag.php")
    print("  UWAGA: Wgraj zaktualizowany plugin gtag na serwer!")
    return True


def step5_test():
    """Test endpointu rezerwacji."""
    print("\n=== KROK 5: Test endpointu ===")

    r = rest_api("POST", "/funlikehel/v1/rezerwacja", {
        "name": "Test-Deploy",
        "email": "deploy-test@test.pl",
        "phone": "+48000000000",
        "package": "zolty",
        "dates": "test",
        "level": "poczatkujacy",
        "persons": 1,
        "message": "test deploy",
    })

    if r and r.status_code == 200:
        data = r.json()
        print(f"  ENDPOINT DZIALA! Odpowiedz: {data}")
        return True
    else:
        print(f"  Endpoint nie odpowiada: {r.status_code if r else 'timeout'}")
        if r:
            print(f"  {r.text[:200]}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Deploy: Formularz rezerwacji Hurghada")
    print("=" * 60)

    results = {}

    # Krok 0: Tworzenie ZIP
    create_zip()

    # Krok 1: Upload
    results["upload"] = step1_upload()

    # Krok 2: Aktywacja
    results["activate"] = step2_activate()

    # Krok 3: Update strony
    if results["activate"]:
        results["page_update"] = step3_update_page()
    else:
        print("\n=== KROK 3: POMINIETO (plugin nieaktywny) ===")
        results["page_update"] = False

    # Krok 4: Update gtag
    results["gtag"] = step4_update_gtag()

    # Krok 5: Test
    if results["activate"]:
        results["test"] = step5_test()
    else:
        results["test"] = False

    print("\n" + "=" * 60)
    print("WYNIK DEPLOY")
    print("=" * 60)
    for k, v in results.items():
        print(f"  {k}: {'OK' if v else 'FAILED'}")

    if all(results.values()):
        print("\nWSZYSTKO DZIALA!")
        print(f"Formularz rezerwacji: {WP_URL}/egipt-hurghada/#rezerwacja")
        print(f"API endpoint: {API_URL}")
        print(f"Google Ads conversion: AW-8974478964/hurghada_rezerwacja")
    elif results.get("activate") and results.get("page_update"):
        print("\nPlugin aktywny, strona zaktualizowana. Formularz powinien dzialac.")
        print(f"Sprawdz: {WP_URL}/egipt-hurghada/#rezerwacja")
    else:
        print("\nNIEKTORE KROKI NIE POWIODLY SIE.")
        print("Jesli upload failed — wgraj plugin recznie:")
        print("  1. Panel home.pl -> wp-content/plugins/")
        print("  2. Wgraj ZIP i rozpakuj")
        print("  3. Aktywuj w wp-admin -> Wtyczki")
        print(f"  ZIP: {os.path.abspath(ZIP_PATH)}")
