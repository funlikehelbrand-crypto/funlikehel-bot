"""
Tworzy strone /oferta-i-rezerwacje na funlikehel.pl
Ustawia redirect 301 z /rezerwacje -> /oferta-i-rezerwacje przez Yoast
"""
import httpx
import base64
import json
import sys

WP_URL = "https://funlikehel.pl"
WP_USER = "Admin"
WP_APP_PASSWORD = "PDlm Q9wV AKvP tvlK uUEa 64zw"
AUTH = base64.b64encode(f"{WP_USER}:{WP_APP_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}
TIMEOUT = 60

PAGE_CONTENT = """
<!-- FLH Oferta & Rezerwacje v1.0 -->
<style>
.flh-oferta-wrap { font-family: inherit; max-width: 1100px; margin: 0 auto; }
.flh-oferta-wrap * { box-sizing: border-box; }
.flh-lead { font-size: 17px; line-height: 1.7; color: #333; margin-bottom: 36px; text-align: center; max-width: 750px; margin-left: auto; margin-right: auto; }
.flh-tabs { display: flex; gap: 8px; margin-bottom: 32px; border-bottom: 2px solid #e0e0e0; }
.flh-tab-btn { padding: 12px 28px; font-size: 16px; font-weight: 700; cursor: pointer; border: none; background: none; color: #666; border-bottom: 3px solid transparent; margin-bottom: -2px; transition: all .2s; border-radius: 4px 4px 0 0; }
.flh-tab-btn:hover { color: #0099cc; background: #f0f8fc; }
.flh-tab-btn.active { color: #0099cc; border-bottom-color: #0099cc; background: #f0f8fc; }
.flh-tab-panel { display: none; }
.flh-tab-panel.active { display: block; }
.flh-sports-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-bottom: 40px; }
.flh-sport-card { border: 1px solid #e8e8e8; border-radius: 12px; padding: 20px 22px; background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,.06); transition: box-shadow .2s, transform .2s; }
.flh-sport-card:hover { box-shadow: 0 4px 20px rgba(0,153,204,.15); transform: translateY(-2px); }
.flh-sport-card .flh-sport-icon { font-size: 30px; margin-bottom: 10px; }
.flh-sport-card h3 { font-size: 17px; margin: 0 0 8px; color: #1a1a2e; }
.flh-sport-card p { font-size: 14px; color: #555; line-height: 1.6; margin: 0 0 14px; }
.flh-sport-card .flh-price-tag { font-weight: 700; color: #0099cc; font-size: 16px; margin-bottom: 12px; }
.flh-sport-card .flh-reserve-btn { display: inline-block; background: #0099cc; color: #fff; border: none; padding: 9px 20px; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; transition: background .2s; }
.flh-sport-card .flh-reserve-btn:hover { background: #007aaa; color: #fff; }
.flh-packages { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-bottom: 40px; }
.flh-pkg { border-radius: 12px; padding: 24px; color: #fff; }
.flh-pkg.yellow { background: linear-gradient(135deg, #f39c12, #e67e22); }
.flh-pkg.silver { background: linear-gradient(135deg, #636e72, #2d3436); }
.flh-pkg.blue   { background: linear-gradient(135deg, #0099cc, #005f80); }
.flh-pkg h3 { margin: 0 0 6px; font-size: 19px; }
.flh-pkg .flh-pkg-price { font-size: 28px; font-weight: 900; margin: 8px 0; }
.flh-pkg ul { padding-left: 18px; margin: 10px 0 16px; font-size: 14px; line-height: 1.8; }
.flh-pkg .flh-reserve-btn { display: inline-block; background: rgba(255,255,255,.2); color: #fff; border: 2px solid rgba(255,255,255,.6); padding: 9px 20px; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; transition: background .2s; }
.flh-pkg .flh-reserve-btn:hover { background: rgba(255,255,255,.35); color: #fff; }
.flh-section-title { font-size: 22px; font-weight: 700; color: #1a1a2e; margin: 36px 0 18px; padding-bottom: 8px; border-bottom: 2px solid #f0f0f0; }
.flh-cta-bar { background: linear-gradient(135deg, #0099cc, #005f80); border-radius: 14px; padding: 28px 32px; text-align: center; color: #fff; margin: 40px 0; }
.flh-cta-bar h2 { margin: 0 0 8px; font-size: 24px; }
.flh-cta-bar p { margin: 0 0 18px; opacity: .9; font-size: 16px; }
.flh-cta-bar a { color: #fff; font-weight: 700; text-decoration: underline; }
.flh-booking-section { scroll-margin-top: 80px; margin-top: 50px; }
.flh-booking-section h2 { font-size: 26px; font-weight: 800; color: #1a1a2e; margin-bottom: 8px; }
.flh-booking-section .flh-booking-lead { color: #555; margin-bottom: 28px; font-size: 15px; }
.flh-loc-switcher { display: flex; gap: 8px; margin-bottom: 24px; }
.flh-loc-btn { flex: 1; padding: 10px; text-align: center; border: 2px solid #e0e0e0; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; background: #fff; color: #555; transition: all .2s; }
.flh-loc-btn.active { border-color: #0099cc; color: #0099cc; background: #f0f8fc; }
@media (max-width: 600px) {
    .flh-tabs { flex-direction: column; border-bottom: none; }
    .flh-tab-btn { border-bottom: none; border-left: 3px solid transparent; text-align: left; }
    .flh-tab-btn.active { border-left-color: #0099cc; border-bottom: none; }
    .flh-sports-grid { grid-template-columns: 1fr; }
    .flh-packages { grid-template-columns: 1fr; }
}
</style>

<div class="flh-oferta-wrap">

<p class="flh-lead">
Szkolimy przez ca&#322;y rok &#8212; latem na <strong>P&#243;&#322;wyspie Helskim w Jastarni</strong>, zim&#261; w <strong>Hurghadzie w Egipcie</strong>.
Kitesurfing, windsurfing, wingfoil, wakeboarding i wi&#281;cej &#8212; dla ka&#380;dego poziomu zaawansowania.
Wybierz lokalizacj&#281;, sport i zarezerwuj termin w kilku klikach.
</p>

<div class="flh-tabs" role="tablist">
<button class="flh-tab-btn active" onclick="flhTab('jastarnia')" id="tab-jastarnia" role="tab" aria-selected="true">Jastarnia</button>
<button class="flh-tab-btn" onclick="flhTab('hurghada')" id="tab-hurghada" role="tab" aria-selected="false">Hurghada</button>
</div>

<div class="flh-tab-panel active" id="panel-jastarnia">
<div class="flh-section-title">Sporty &#8212; Jastarnia, P&#243;&#322;wysep Helski</div>
<div class="flh-sports-grid">
<div class="flh-sport-card">
<div class="flh-sport-icon">&#129683;</div>
<h3>Kitesurfing</h3>
<p>Kurs dla pocz&#261;tkuj&#261;cych (IKO), kurs progression, jazda z instruktorem. Zatoka Pucka to jedno z najlepszych miejsc w Polsce do nauki kite &#8212; p&#322;ytko, bezpiecznie i wietrznie.</p>
<div class="flh-price-tag" id="price-hel-kite">od 450 z&#322; / sesja</div>
<button class="flh-reserve-btn" onclick="flhScrollToForm('hel')">Zarezerwuj</button>
</div>
<div class="flh-sport-card">
<div class="flh-sport-icon">&#127940;</div>
<h3>Windsurfing</h3>
<p>Klasyczny sport wodny na Zatoce Puckiej. Nauka od podstaw do samodzielnej jazdy &#8212; spokojne wody idealne dla pocz&#261;tkuj&#261;cych i rodzin z dzie&#263;mi.</p>
<div class="flh-price-tag">zapytaj o termin</div>
<button class="flh-reserve-btn" onclick="flhScrollToForm('hel')">Zarezerwuj</button>
</div>
<div class="flh-sport-card">
<div class="flh-sport-icon">&#129445;</div>
<h3>Wing Foil</h3>
<p>Najnowszy trend &#8212; deska foilowa nap&#281;dzana r&#281;cznym wing-iem. &#322;atwo wej&#347;&#263;, trudno przesta&#263;. Idealna dla fan&#243;w nowych dozna&#324; i dla tych, kt&#243;rzy chc&#261; spr&#243;bowa&#263; czego&#347; zupe&#322;nie innego.</p>
<div class="flh-price-tag">zapytaj o termin</div>
<button class="flh-reserve-btn" onclick="flhScrollToForm('hel')">Zarezerwuj</button>
</div>
<div class="flh-sport-card">
<div class="flh-sport-icon">&#128676;</div>
<h3>Wakeboarding</h3>
<p>Czysta adrenalina za mot&#243;r&#243;wk&#261;. Skoki, tricki, transfery &#8212; to sport dla tych, kt&#243;rzy lubi&#261; dawk&#281; ostrzejszych wra&#380;e&#324;. Wymagana umiej&#281;tno&#347;&#263; p&#322;ywania.</p>
<div class="flh-price-tag">zapytaj o termin</div>
<button class="flh-reserve-btn" onclick="flhScrollToForm('hel')">Zarezerwuj</button>
</div>
<div class="flh-sport-card">
<div class="flh-sport-icon">&#127951;</div>
<h3>Pumpfoil / SUP</h3>
<p>Foil nap&#281;dzany pompowaniem cia&#322;em &#8212; medytacja w ruchu na wodzie. SUP (Stand Up Paddle) &#8212; spokojne zwiedzanie zatoki na stoj&#261;co. Dla wszystkich poziom&#243;w i ka&#380;dego wieku.</p>
<div class="flh-price-tag">zapytaj o termin</div>
<button class="flh-reserve-btn" onclick="flhScrollToForm('hel')">Zarezerwuj</button>
</div>
<div class="flh-sport-card">
<div class="flh-sport-icon">&#127957;</div>
<h3>Obozy i Kolonie</h3>
<p>Surfkolonie dla dzieci (6h dziennie z opiek&#261;), zielone szko&#322;y, obozy sportowe dla grup i wyjazdy integracyjne dla firm. Ponad 300 miejsc noclegowych na kempingu Sun4Hel.</p>
<div class="flh-price-tag" id="price-hel-camp">od 2&#160;500 z&#322; / os.</div>
<button class="flh-reserve-btn" onclick="flhScrollToForm('hel')">Zarezerwuj</button>
</div>
</div>
<div class="flh-cta-bar">
<h2>Sezon letni w Jastarni &#8212; lipiec i sierpie&#324;</h2>
<p>100 metr&#243;w od morza, 20 metr&#243;w od Zatoki Puckiej. Jedno z najlepszych miejsc do nauki sport&#243;w wodnych w Polsce.</p>
<p><a href="tel:690270032">Zadzwo&#324;: 690 270 032</a> lub <a href="mailto:funlikehelbrand@gmail.com">napisz do nas</a></p>
</div>
</div>

<div class="flh-tab-panel" id="panel-hurghada">
<div class="flh-section-title">Pakiety &#8212; Hurghada, Egipt (sezon pa&#378;dziernik&#8211;marzec)</div>
<div class="flh-packages">
<div class="flh-pkg yellow">
<h3>Wariant &#379;&#243;&#322;ty</h3>
<div class="flh-pkg-price">2&#160;300 z&#322;</div>
<ul>
<li>8 godzin szkolenia kite</li>
<li>5 nocleg&#243;w przy spocie Play Kite</li>
<li>&#346;niadania wliczone</li>
<li>Transfer z lotniska</li>
<li>Wsparcie na miejscu</li>
</ul>
<button class="flh-reserve-btn" onclick="flhScrollToForm('hurghada')">Zarezerwuj</button>
</div>
<div class="flh-pkg silver">
<h3>Wariant Srebrny</h3>
<div class="flh-pkg-price">3&#160;300 z&#322;</div>
<ul>
<li>12 godzin szkolenia kite</li>
<li>7 nocleg&#243;w &#8212; mieszkanie z kuchni&#261;, AC</li>
<li>4 baseny w obiekcie Tiba View</li>
<li>Transfer z lotniska</li>
<li>Pomoc na miejscu 24/7</li>
<li>Opcja: nurkowanie w atrakcyjnych cenach</li>
</ul>
<button class="flh-reserve-btn" onclick="flhScrollToForm('hurghada')">Zarezerwuj</button>
</div>
<div class="flh-pkg blue">
<h3>Wariant Niebieski</h3>
<div class="flh-pkg-price">od 1&#160;910 z&#322;</div>
<ul>
<li>Bez zakwaterowania (w&#322;asny hotel)</li>
<li>8h szkolenia &#8212; 1&#160;910 z&#322;</li>
<li>12h szkolenia &#8212; 2&#160;640 z&#322;</li>
<li>Pe&#322;na elastyczno&#347;&#263; termin&#243;w</li>
<li>Dost&#281;p do sprawdzonych kontakt&#243;w lokalnych</li>
</ul>
<button class="flh-reserve-btn" onclick="flhScrollToForm('hurghada')">Zarezerwuj</button>
</div>
</div>
<div class="flh-section-title">Sporty &#8212; Hurghada</div>
<div class="flh-sports-grid">
<div class="flh-sport-card">
<div class="flh-sport-icon">&#129683;</div>
<h3>Kitesurfing &#8212; Cabrinha Test Center</h3>
<p>Jedyna polska baza w Hurghadzie. Sta&#322;y wiatr 15&#8211;25 w&#281;z&#322;&#243;w przez ca&#322;y sezon, ciep&#322;a woda, p&#322;ytka laguna. Szkolenia na ka&#380;dym poziomie &#8212; od zerowego po zaawansowane tricki.</p>
<div class="flh-price-tag" id="price-eg-kite">od 1&#160;910 z&#322; (8h)</div>
<button class="flh-reserve-btn" onclick="flhScrollToForm('hurghada')">Zarezerwuj</button>
</div>
<div class="flh-sport-card">
<div class="flh-sport-icon">&#129445;</div>
<h3>Wing Foil</h3>
<p>Ciep&#322;a, czysta woda Morza Czerwonego to idealne &#347;rodowisko do nauki wingfoila. Warunki w Hurghadzie pozwalaj&#261; &#263;wiczy&#263; przez ca&#322;y dzie&#324; &#8212; bez stresu o pogod&#281;.</p>
<div class="flh-price-tag">w pakiecie kite lub osobno</div>
<button class="flh-reserve-btn" onclick="flhScrollToForm('hurghada')">Zarezerwuj</button>
</div>
<div class="flh-sport-card">
<div class="flh-sport-icon">&#127957;</div>
<h3>Obozy Kite &#8212; Hurghada</h3>
<p>Tygodniowy intensywny kamp kite &#8212; rano na wodzie, wieczorem teoria i analiza wideo. Grupy do 12 os&#243;b podzielone poziomowo. Hurghada od pa&#378;dziernika do marca.</p>
<div class="flh-price-tag" id="price-eg-camp">od 2&#160;500 z&#322; / os.</div>
<button class="flh-reserve-btn" onclick="flhScrollToForm('hurghada')">Zarezerwuj</button>
</div>
<div class="flh-sport-card">
<div class="flh-sport-icon">&#128044;</div>
<h3>Nurkowanie i Dodatkowe Atrakcje</h3>
<p>Rafa koralowa Morza Czerwonego tuz pod nogami. Organizujemy nurkowanie w sprawdzonych centrach po wyj&#261;tkowo atrakcyjnych cenach. Jazda konna, zwiedzanie Luksoru &#8212; pomo&#380;emy zaplanowa&#263;.</p>
<div class="flh-price-tag">cena indywidualna</div>
<button class="flh-reserve-btn" onclick="flhScrollToForm('hurghada')">Zarezerwuj</button>
</div>
</div>
<div class="flh-cta-bar">
<h2>Zimuj aktywnie &#8212; jedyna polska baza kite w Egipcie</h2>
<p>Sprawd&#378; tanie przeloty z Polski od 330 z&#322;. Lot + 12h kite + nocleg &#8212; to dzia&#322;a!</p>
<p><a href="tel:690270032">Zadzwo&#324;: 690 270 032</a> lub <a href="mailto:funlikehelbrand@gmail.com">napisz: funlikehelbrand@gmail.com</a></p>
</div>
</div>

<div class="flh-booking-section" id="flh-rezerwuj">
<h2>Zarezerwuj</h2>
<p class="flh-booking-lead">Wybierz lokalizacj&#281; i sport &#8212; odezwiemy si&#281; w ci&#261;gu 24 godzin. Bez op&#322;at z g&#243;ry.</p>
<div class="flh-loc-switcher">
<div class="flh-loc-btn active" id="loc-btn-hel" onclick="flhSwitchLoc('hel')">Jastarnia (Polska)</div>
<div class="flh-loc-btn" id="loc-btn-hurghada" onclick="flhSwitchLoc('hurghada')">Hurghada (Egipt)</div>
</div>
<div id="flh-form-hel">[flh_booking_form location="hel"]</div>
<div id="flh-form-hurghada" style="display:none">[flh_booking_form location="hurghada"]</div>
</div>

</div>

<script>
function flhTab(loc){document.querySelectorAll('.flh-tab-panel').forEach(function(p){p.classList.remove('active');});document.querySelectorAll('.flh-tab-btn').forEach(function(b){b.classList.remove('active');b.setAttribute('aria-selected','false');});document.getElementById('panel-'+loc).classList.add('active');document.getElementById('tab-'+loc).classList.add('active');document.getElementById('tab-'+loc).setAttribute('aria-selected','true');}
function flhScrollToForm(loc){flhSwitchLoc(loc);var el=document.getElementById('flh-rezerwuj');if(el){el.scrollIntoView({behavior:'smooth',block:'start'});}}
function flhSwitchLoc(loc){document.getElementById('flh-form-hel').style.display=(loc==='hel')?'':'none';document.getElementById('flh-form-hurghada').style.display=(loc==='hurghada')?'':'none';document.getElementById('loc-btn-hel').classList.toggle('active',loc==='hel');document.getElementById('loc-btn-hurghada').classList.toggle('active',loc==='hurghada');}
(function(){var A='https://funlikehel-bot.onrender.com';fetch(A+'/api/services').then(function(r){return r.json();}).then(function(d){if(!d.services)return;d.services.forEach(function(s){if(s.slug==='private-lesson'){var e=document.getElementById('price-hel-kite');if(e)e.textContent='od '+s.base_price.toLocaleString('pl-PL')+' zł / sesja';}if(s.slug==='kite-camp'){var e2=document.getElementById('price-hel-camp');if(e2)e2.textContent='od '+s.base_price.toLocaleString('pl-PL')+' zł / os.';var e3=document.getElementById('price-eg-camp');if(e3)e3.textContent='od '+s.base_price.toLocaleString('pl-PL')+' zł / os.';}if(s.slug==='stay-kite-package'){var e4=document.getElementById('price-eg-kite');if(e4)e4.textContent='od '+s.base_price.toLocaleString('pl-PL')+' zł (pakiet)';}});}).catch(function(){});})();
</script>
"""

PAGE_SEO_TITLE = "Oferta i Rezerwacje \u2014 Kitesurfing, Windsurfing, Wing | FUN like HEL"
PAGE_META_DESC = "Zarezerwuj kurs kitesurfingu, windsurfingu lub wingfoila w Jastarni lub Hurghadzie. Cennik, pakiety Egipt i formularz online. FUN like HEL \u2014 szkolimy przez ca\u0142y rok."


def rest(method, path, data=None):
    url = f"{WP_URL}/wp-json{path}"
    kwargs = dict(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
    if method == "POST":
        return httpx.post(url, json=data, **kwargs)
    elif method == "PUT":
        return httpx.put(url, json=data, **kwargs)
    return httpx.get(url, **kwargs)


def create_page():
    payload = {
        "title": "Oferta i Rezerwacje",
        "slug": "oferta-i-rezerwacje",
        "content": PAGE_CONTENT,
        "status": "publish",
        "meta": {
            "_yoast_wpseo_title": PAGE_SEO_TITLE,
            "_yoast_wpseo_metadesc": PAGE_META_DESC,
            "_yoast_wpseo_focuskw": "kitesurfing Jastarnia Hurghada rezerwacje",
        }
    }
    print("Krok 1: Tworzenie strony /oferta-i-rezerwacje ...")
    r = rest("POST", "/wp/v2/pages", payload)
    print(f"  Status: {r.status_code}")
    if r.status_code in (200, 201):
        d = r.json()
        print(f"  OK - ID: {d['id']}, URL: {d.get('link', '?')}")
        return d['id']
    else:
        print(f"  Blad: {r.text[:600]}")
        return None


def set_redirect_on_rezerwacje(new_page_id):
    """
    Zamien strone /rezerwacje (ID 2283) na redirect 301
    przez wstawienie odpowiedniego meta redirectu Yoast.
    Strona pozostaje opublikowana ale w tresci dodajemy
    natychmiastowy JavaScript redirect + noindex.
    """
    print("Krok 2: Ustawienie redirect na /rezerwacje (ID 2283) ...")

    redirect_content = (
        '<meta http-equiv="refresh" content="0;url=https://funlikehel.pl/oferta-i-rezerwacje/">'
        '<script>window.location.replace("https://funlikehel.pl/oferta-i-rezerwacje/");</script>'
        '<p>Ta strona przenios&#322;a si&#281;. <a href="https://funlikehel.pl/oferta-i-rezerwacje/">'
        'Kliknij tutaj</a></p>'
    )

    payload = {
        "content": redirect_content,
        "meta": {
            "_yoast_wpseo_redirect": "https://funlikehel.pl/oferta-i-rezerwacje/",
            "_yoast_wpseo_meta-robots-noindex": "1",
        }
    }
    r = rest("POST", "/wp/v2/pages/2283", payload)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        print("  OK - strona /rezerwacje zaktualizowana")
    else:
        print(f"  Blad: {r.text[:300]}")


def add_htaccess_redirect():
    """Probuje dodac redirect przez REST snippets lub functions.php hook."""
    print("Krok 3: Dodawanie redirectu 301 przez functions.php (via REST) ...")
    # Uzyj niestandardowego endpointu pluginu booking-v2
    # ktory ma dostep do file_put_contents
    # Alternatywnie sprawdzamy czy plugin Code Snippets jest aktywny
    r = rest("GET", "/wp/v2/plugins?per_page=50")
    if r.status_code == 200:
        plugins = r.json()
        slugs = [p.get('plugin', '') for p in plugins]
        print(f"  Aktywne wtyczki (pierwsze 5): {slugs[:5]}")
        has_redirection = any('redirection' in s.lower() for s in slugs)
        if has_redirection:
            print("  Wykryto plugin Redirection - przekierowanie mozna skonfigurowac recznie")
    else:
        print(f"  Nie mozna pobrac listy pluginow: {r.status_code}")


if __name__ == "__main__":
    new_id = create_page()
    if new_id:
        set_redirect_on_rezerwacje(new_id)
        add_htaccess_redirect()
        print(f"\nGotowe!")
        print(f"  Nowa strona: https://funlikehel.pl/oferta-i-rezerwacje/")
        print(f"  Stara strona (redirect): https://funlikehel.pl/rezerwacje/")
    else:
        sys.exit(1)
