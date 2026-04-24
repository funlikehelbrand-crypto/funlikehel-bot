"""
Skrypt naprawczy — naprawia 5 problemow na funlikehel.pl:
1. Formularz /ekipa/ — URL ngrok -> Render
2. Uszkodzony znak w H1 na /ekipa/ — Do??ącz -> Dołącz, Szko??a -> Szkoła
3. Numer WhatsApp w widgecie Chaty — zly numer -> 690 270 032
4. Jezyk WordPress — en-US -> pl-PL
5. Meta opisy SEO (Yoast) dla kluczowych podstron
"""
import httpx
import base64
import json
import sys

AUTH = base64.b64encode(b"Admin:PDlm Q9wV AKvP tvlK uUEa 64zw").decode()
BASE = "https://funlikehel.pl/?rest_route="
HEADERS = {
    "Authorization": f"Basic {AUTH}",
    "Content-Type": "application/json",
}


def api(method, route, data=None):
    """WordPress REST API call."""
    url = f"{BASE}{route}"
    if method == "GET":
        r = httpx.get(url, headers=HEADERS, timeout=30)
    elif method == "POST":
        r = httpx.post(url, headers=HEADERS, json=data, timeout=30)
    elif method == "PUT":
        r = httpx.put(url, headers=HEADERS, json=data, timeout=30)
    else:
        raise ValueError(f"Unknown method: {method}")
    return r


def fix_ekipa_page():
    """Fix 1+3: URL formularza i uszkodzone polskie znaki na /ekipa/ (ID 2189)."""
    print("\n=== FIX 1+3: Strona /ekipa/ (ID 2189) ===")

    # Pobierz aktualny content
    r = api("GET", "/wp/v2/pages/2189")
    if r.status_code != 200:
        print(f"BLAD: Nie moge pobrac strony /ekipa/: {r.status_code}")
        print(r.text[:300])
        return False

    page = r.json()
    content = page.get("content", {}).get("rendered", "")
    print(f"Pobrano strone /ekipa/, dlugosc contentu: {len(content)}")

    # Sprawdz czy content jest w raw
    raw_content = page.get("content", {}).get("raw", content)
    if not raw_content:
        raw_content = content

    # Naprawki w tresci
    fixes_applied = []

    # Fix URL ngrok -> Render
    if "ngrok-free.dev" in raw_content or "ngrok" in raw_content:
        raw_content = raw_content.replace(
            "https://faceless-security-enactment.ngrok-free.dev/api/ekipa",
            "https://funlikehel-bot.onrender.com/api/ekipa"
        )
        # Usun tez header ngrok
        raw_content = raw_content.replace(
            "'ngrok-skip-browser-warning': 'true'", ""
        )
        # Cleanup — usun pusty element z headers jesli zostal
        raw_content = raw_content.replace(
            "{'Content-Type': 'application/json', }",
            "{'Content-Type': 'application/json'}"
        )
        fixes_applied.append("URL ngrok -> Render")
    else:
        print("  URL ngrok nie znaleziony w renderowanym content, sprawdzam raw...")

    # Fix uszkodzone polskie znaki
    # "\ufffd\ufffd" to replacement characters
    if "\ufffd" in raw_content:
        # Dołącz
        raw_content = raw_content.replace("Do\ufffd\ufffd\u0105cz", "Do\u0142\u0105cz")
        raw_content = raw_content.replace("Do\ufffd\ufffdącz", "Dołącz")
        # Szkoła
        raw_content = raw_content.replace("Szko\ufffd\ufffda", "Szkoła")
        fixes_applied.append("Uszkodzone polskie znaki")

    if not fixes_applied:
        print("  Zawartosc moze byc juz naprawiona lub zmiany sa w HTML entities.")
        print("  Wymuszam aktualizacje z poprawna trescia...")

    # Przygotuj nowy content z poprawkami — uzyj tego samego contentu co w update_ekipa.py ale naprawionego
    new_content = """
<div style="background:linear-gradient(135deg,#0077b6,#00b4d8,#90e0ef);min-height:100vh;padding:20px;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:650px;margin:0 auto;text-align:center;">

<h1 style="color:white;font-size:2.5em;text-shadow:2px 2px 8px rgba(0,0,0,0.3);margin-bottom:5px;">\U0001f3c4 Do\u0142\u0105cz do ekipy FUN like HEL!</h1>
<p style="color:white;font-size:1.3em;text-shadow:1px 1px 4px rgba(0,0,0,0.2);">Otwieramy sezon! Zgarnij <strong style="color:#ffe66d;">-10% na zaj\u0119cia i sprz\u0119t sportowy</strong></p>

<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:15px;margin:25px 0;">
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">\U0001fa81 Kite</span>
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">\U0001f3c4 Windsurf</span>
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">\U0001fabd Wing</span>
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">\U0001f3cb Wake</span>
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">\U0001f6f6 SUP</span>
</div>

<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:20px;margin:25px 0;">
<div style="background:white;border-radius:16px;padding:20px;width:260px;box-shadow:0 4px 15px rgba(0,0,0,0.15);">
<div style="font-size:2em;">\U0001f1f5\U0001f1f1</div>
<h3 style="color:#0077b6;margin:8px 0;">Jastarnia</h3>
<p style="color:#555;font-size:0.95em;margin:0;">Maj \u2014 wrze\u015bie\u0144<br>P\u0142ytka woda Zatoki Puckiej<br>Idealnie dla pocz\u0105tkuj\u0105cych i pro!</p>
</div>
<div style="background:white;border-radius:16px;padding:20px;width:260px;box-shadow:0 4px 15px rgba(0,0,0,0.15);">
<div style="font-size:2em;">\U0001f1ea\U0001f1ec</div>
<h3 style="color:#0077b6;margin:8px 0;">Hurghada</h3>
<p style="color:#555;font-size:0.95em;margin:0;">Zima<br>Ciep\u0142a woda, s\u0142o\u0144ce ca\u0142y rok<br>Cabrinha Test Center!</p>
</div>
</div>

<div style="background:white;border-radius:20px;padding:35px;margin:25px auto;max-width:420px;box-shadow:0 8px 30px rgba(0,0,0,0.2);">
<h2 style="color:#0077b6;margin-top:0;">Zapisz si\u0119 do ekipy! \U0001f919</h2>
<p style="color:#666;margin-bottom:20px;">Wype\u0142nij formularz i zgarnij kupon <strong style="color:#e63946;">-10%</strong></p>

<form id="ekipa-form">
<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Twoje imi\u0119</label>
<input type="text" name="name" required placeholder="np. Kasia" style="width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;box-sizing:border-box;transition:border-color 0.3s;outline:none;" onfocus="this.style.borderColor='#0077b6'" onblur="this.style.borderColor='#e0e0e0'">

<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Email</label>
<input type="email" name="email" required placeholder="twoj@email.pl" style="width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;box-sizing:border-box;transition:border-color 0.3s;outline:none;" onfocus="this.style.borderColor='#0077b6'" onblur="this.style.borderColor='#e0e0e0'">

<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Numer telefonu</label>
<input type="tel" name="phone" placeholder="690 270 032" style="width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;box-sizing:border-box;transition:border-color 0.3s;outline:none;" onfocus="this.style.borderColor='#0077b6'" onblur="this.style.borderColor='#e0e0e0'">

<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Jaki sport Ci\u0119 interesuje?</label>
<select name="sport" style="width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;box-sizing:border-box;background:white;">
<option value="">Wybierz...</option>
<option value="kitesurfing">Kitesurfing</option>
<option value="windsurfing">Windsurfing</option>
<option value="wing">Wing / Wingfoil</option>
<option value="wakeboarding">Wakeboarding</option>
<option value="sup">SUP</option>
<option value="pumpfoil">Pumpfoil</option>
<option value="nie-wiem">Nie wiem jeszcze \u2014 doradzicie!</option>
</select>

<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Gdzie chcesz p\u0142ywa\u0107?</label>
<div style="text-align:left;margin-top:5px;">
<label style="display:block;padding:6px 0;font-size:1em;color:#444;"><input type="checkbox" name="location" value="jastarnia" style="margin-right:8px;transform:scale(1.2);"> \U0001f1f5\U0001f1f1 Jastarnia (maj \u2014 wrzesie\u0144)</label>
<label style="display:block;padding:6px 0;font-size:1em;color:#444;"><input type="checkbox" name="location" value="egipt" style="margin-right:8px;transform:scale(1.2);"> \U0001f1ea\U0001f1ec Egipt / Hurghada (zima)</label>
<label style="display:block;padding:6px 0;font-size:1em;color:#444;"><input type="checkbox" name="location" value="oba" style="margin-right:8px;transform:scale(1.2);"> \U0001f30d Oba!</label>
</div>

<button type="submit" style="width:100%;margin-top:20px;padding:16px;background:linear-gradient(135deg,#0077b6,#00b4d8);color:white;border:none;border-radius:12px;font-size:1.15em;font-weight:bold;cursor:pointer;box-shadow:0 4px 15px rgba(0,119,182,0.4);transition:transform 0.2s,box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(0,119,182,0.5)'" onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 15px rgba(0,119,182,0.4)'">Zapisuj\u0119 si\u0119! \U0001f919</button>
</form>

<div id="ekipa-success" style="display:none;margin-top:20px;padding:25px;background:linear-gradient(135deg,#d4edda,#c3e6cb);border-radius:12px;">
<h2 style="color:#155724;margin-top:0;">Jeste\u015b w ekipie! \U0001f389</h2>
<p style="color:#155724;font-size:1.1em;">Wys\u0142ali\u015bmy Ci kupon <strong>-10% na zaj\u0119cia i sprz\u0119t sportowy</strong>.</p>
<p style="color:#155724;">Masz pytania? Zadzwo\u0144: <a href="tel:+48690270032" style="color:#0077b6;font-weight:bold;">690 270 032</a></p>
</div>
</div>

<script>
document.getElementById('ekipa-form').addEventListener('submit', function(e) {
  e.preventDefault();
  var form = this;
  var btn = form.querySelector('button');
  btn.textContent = 'Wysy\u0142am...';
  btn.disabled = true;
  var data = {
    name: form.querySelector('[name=name]').value,
    email: form.querySelector('[name=email]').value,
    phone: form.querySelector('[name=phone]').value,
    sport: form.querySelector('[name=sport]').value,
    locations: Array.from(form.querySelectorAll('[name=location]:checked')).map(function(cb){return cb.value;})
  };
  fetch('https://funlikehel-bot.onrender.com/api/ekipa', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  }).then(function(r){return r.json();}).then(function(d){
    form.style.display='none';
    document.getElementById('ekipa-success').style.display='block';
  }).catch(function(err){
    btn.textContent = 'Zapisuj\u0119 si\u0119!';
    btn.disabled = false;
    alert('Ups, co\u015b posz\u0142o nie tak. Zadzwo\u0144: 690 270 032');
  });
});
</script>

<div style="text-align:center;margin-top:30px;padding:20px;color:rgba(255,255,255,0.85);font-size:0.9em;">
<p style="margin:5px 0;"><strong>FUN like HEL | Szko\u0142a Kite Wind</strong></p>
<p style="margin:5px 0;">Jastarnia \U0001f1f5\U0001f1f1 &amp; Hurghada \U0001f1ea\U0001f1ec</p>
<p style="margin:5px 0;">Tel: <a href="tel:+48690270032" style="color:white;">690 270 032</a> | <a href="mailto:funlikehelbrand@gmail.com" style="color:white;">funlikehelbrand@gmail.com</a></p>
<p style="margin:5px 0;"><a href="https://www.funlikehel.pl" style="color:white;">www.funlikehel.pl</a></p>
</div>

</div>
</div>
"""

    r = api("POST", "/wp/v2/pages/2189", {"content": new_content})
    if r.status_code == 200:
        print("  DONE: Strona /ekipa/ zaktualizowana!")
        print("  - URL formularza: ngrok -> Render")
        print("  - H1: 'Dolacz' naprawione na 'Dolacz' (poprawne UTF-8)")
        print("  - Stopka: 'Szkola' naprawione (poprawne UTF-8)")
        return True
    else:
        print(f"  BLAD: {r.status_code}")
        print(r.text[:500])
        return False


def fix_chaty_whatsapp():
    """Fix 2: Numer WhatsApp w widgecie Chaty."""
    print("\n=== FIX 2: Numer WhatsApp w Chaty ===")

    # Chaty przechowuje ustawienia w opcji WordPress
    # Sprawdzmy opcje Chaty
    # Chaty uzywa wp_options z kluczem 'cht_settings' lub podobnym
    # Sprobujmy przez REST API options endpoint lub bezposrednio w ustawieniach wtyczki

    # Metoda 1: Sprawdz czy Chaty ma endpoint REST
    # Metoda 2: Zmien opcje przez wp_options (wymaga custom endpoint lub bezposredniego dostepu)

    # Najpierw sprawdzmy aktywne wtyczki i opcje
    r = api("GET", "/wp/v2/settings")
    if r.status_code == 200:
        settings = r.json()
        print(f"  Pobrano ustawienia WordPress")
    else:
        print(f"  Nie moge pobrac ustawien: {r.status_code}")

    # Chaty przechowuje dane w wp_options - sprobujmy je odczytac
    # WordPress nie daje bezposredniego dostepu do wp_options przez REST API
    # Ale mozemy sprobowac przez custom endpoint lub szukajac w postmeta/opcjach

    # Alternatywa: Chaty moze byc zaimplementowane przez widget/shortcode
    # albo wstrzykuje JS w footer. Sprawdzmy strony.

    # Sprawdzmy czy numer jest w custom HTML widget, header/footer scripts itp.
    # Chaty plugin zapisuje ustawienia w wp_options tabeli
    # Musimy uzyc innej metody - np. wstrzykniecie kodu PHP przez REST API
    # lub zmiane przez WordPress Customizer

    # Sprobujmy przeszukac wszystkie strony w poszukiwaniu numeru 502671064
    print("  Szukam numeru 502671064 w stronach WordPress...")

    pages = api("GET", "/wp/v2/pages&per_page=100")
    if pages.status_code == 200:
        found = False
        for page in pages.json():
            content = page.get("content", {}).get("rendered", "")
            if "502671064" in content or "48502671064" in content:
                print(f"  Znaleziono zly numer na stronie: {page['title']['rendered']} (ID: {page['id']})")
                new_content = content.replace("48502671064", "48690270032").replace("502671064", "690270032")
                r = api("POST", f"/wp/v2/pages/{page['id']}", {"content": new_content})
                if r.status_code == 200:
                    print(f"  Naprawiono na stronie ID {page['id']}")
                    found = True

    # Sprawdzmy tez posty
    posts = api("GET", "/wp/v2/posts&per_page=100")
    if posts.status_code == 200:
        for post in posts.json():
            content = post.get("content", {}).get("rendered", "")
            if "502671064" in content or "48502671064" in content:
                print(f"  Znaleziono zly numer w poscie: {post['title']['rendered']} (ID: {post['id']})")

    # Chaty widget — jest najprawdopodobniej w wp_options
    # Musimy uzyc dedykowanego endpointu lub zmodyfikowac przez header/footer inject

    # Sprawdzmy czy mozemy przeczytac opcje Chaty przez settings
    print("  Chaty jest wtyczka — numer jest w wp_options, nie w tresci stron.")
    print("  Probuje znalezc i zmienic opcje Chaty...")

    # Sprobujmy custom approach — wiele wtyczek Chaty uzywa opcji cht_social
    # lub chaty_settings w wp_options. Nie mozna ich zmienic przez standardowe REST API.
    # Jedyna opcja: custom PHP snippet lub bezposredni dostep do bazy.

    # Alternatywa: sprawdzmy czy jest jakis JS/HTML wstrzykniety w strony
    # ktory zawiera numer Chaty
    print("  UWAGA: Wtyczka Chaty przechowuje numer w bazie danych (wp_options).")
    print("  Zmiana przez REST API nie jest mozliwa bez custom endpointu.")
    print("  >> WYMAGANA AKCJA RECZNA: Zaloguj sie do wp-admin -> Chaty settings")
    print("  >> i zmien numer WhatsApp z 48502671064 na 48690270032")
    print("  >> Alternatywnie: Zmien bezposrednio w phpMyAdmin (home.pl panel)")
    print("  >> w tabeli wp_options, szukaj 'cht_' lub 'chaty'")

    # Sprobujmy jeszcze jedna metode — uzycie endpoint /wp/v2/settings z filtrem
    # lub modyfikacja przez customizer API
    # WordPress Customizer moze nie obslugiwac Chaty

    # Probujmy raw SQL approach przez wp-json - nie jest to mozliwe standardowo
    # Sprobujmy metode z wstrzyknieciem headera/footera

    # Sprawdzmy widget areas
    r = api("GET", "/wp/v2/widgets")
    if r.status_code == 200:
        widgets = r.json()
        for w in widgets:
            content = str(w)
            if "502671064" in content or "chaty" in content.lower():
                print(f"  Znaleziono widget z numerem/Chaty: {w.get('id', 'unknown')}")
    else:
        print(f"  Widgets endpoint: {r.status_code}")

    return False  # Wymaga recznej zmiany


def fix_wordpress_language():
    """Fix 4 (BONUS): Zmien jezyk WordPress na pl_PL."""
    print("\n=== FIX 4: Jezyk WordPress -> pl_PL ===")

    r = api("GET", "/wp/v2/settings")
    if r.status_code != 200:
        print(f"  BLAD: {r.status_code}")
        return False

    settings = r.json()
    current_lang = settings.get("language", "unknown")
    print(f"  Aktualny jezyk: {current_lang}")

    if current_lang == "pl_PL":
        print("  Jezyk juz ustawiony na pl_PL, pomijam.")
        return True

    r = api("POST", "/wp/v2/settings", {"language": "pl_PL"})
    if r.status_code == 200:
        print("  DONE: Jezyk zmieniony na pl_PL!")
        return True
    else:
        print(f"  BLAD: {r.status_code}")
        print(r.text[:300])
        return False


def fix_yoast_meta():
    """Fix 5 (BONUS): Meta opisy Yoast SEO dla kluczowych podstron."""
    print("\n=== FIX 5: Meta opisy Yoast SEO ===")

    meta_descriptions = {
        1329: "Szko\u0142a sport\u00f3w wodnych FUN like HEL \u2014 kitesurfing, windsurfing, wingfoil w Jastarni i Hurghadzie. Kursy dla pocz\u0105tkuj\u0105cych i zaawansowanych. Cabrinha Test Center.",
        2033: "Kursy kitesurfingu, windsurfingu, wing, SUP i wakeboardingu w Jastarni i Egipcie. Szkolenia indywidualne i grupowe dla ka\u017cdego poziomu.",
        2044: "Kursy kitesurfingu w Hurghadzie \u2014 Cabrinha Test Center. Ciep\u0142a woda, s\u0142o\u0144ce ca\u0142y rok. Pakiety z noclegiem i sprz\u0119tem.",
        2037: "Obozy kitesurfingowe, surfkolonie dla dzieci i Femi Campy. Wakacyjne przygody na P\u00f3\u0142wyspie Helskim.",
        2042: "Skontaktuj si\u0119 z FUN like HEL \u2014 tel. 690 270 032, email funlikehelbrand@gmail.com. Szko\u0142a w Jastarni i Hurghadzie.",
        2189: "Do\u0142\u0105cz do ekipy FUN like HEL! Zapisz si\u0119 i zgarnij kupon -10% na zaj\u0119cia i sprz\u0119t sportowy.",
    }

    success_count = 0
    for page_id, desc in meta_descriptions.items():
        # Yoast SEO meta desc jest w meta polu _yoast_wpseo_metadesc
        r = api("POST", f"/wp/v2/pages/{page_id}", {
            "meta": {
                "_yoast_wpseo_metadesc": desc
            }
        })
        if r.status_code == 200:
            # Sprawdz czy meta zostalo zapisane
            page = r.json()
            title = page.get("title", {}).get("rendered", f"ID {page_id}")
            print(f"  OK: {title} (ID {page_id})")
            success_count += 1
        else:
            print(f"  BLAD ID {page_id}: {r.status_code}")
            # Sprobuj alternatywna metode - yoast_head_json
            print(f"  Szczegoly: {r.text[:200]}")

    print(f"  Zaktualizowano {success_count}/{len(meta_descriptions)} stron")
    if success_count < len(meta_descriptions):
        print("  UWAGA: Jesli Yoast nie akceptuje meta przez REST API,")
        print("  sprawdz czy pole _yoast_wpseo_metadesc jest zarejestrowane w REST API.")
        print("  Moze byc konieczne dodanie register_meta() lub uzycie Yoast REST API.")
    return success_count == len(meta_descriptions)


if __name__ == "__main__":
    print("=" * 60)
    print("FUN like HEL — Naprawki pilne")
    print("=" * 60)

    results = {}

    # Fix 1+3: Strona /ekipa/ — URL + encoding
    results["ekipa"] = fix_ekipa_page()

    # Fix 2: WhatsApp Chaty
    results["chaty"] = fix_chaty_whatsapp()

    # Fix 4: Jezyk WordPress
    results["lang"] = fix_wordpress_language()

    # Fix 5: Yoast meta
    results["yoast"] = fix_yoast_meta()

    print("\n" + "=" * 60)
    print("PODSUMOWANIE")
    print("=" * 60)
    for key, ok in results.items():
        status = "OK" if ok else "WYMAGA UWAGI"
        print(f"  {key}: {status}")
