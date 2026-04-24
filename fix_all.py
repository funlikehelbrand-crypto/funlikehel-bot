"""
1. Dodaj YouTube + Google Reviews do strony glownej
2. Wyczysc menu
3. Pobierz reszte produktow Cabrinha
"""
import subprocess, json, sys, re

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

def upload_image(url, filename):
    img_path = f"C:/Users/\u0141ukaszMichalina/funlikehel/{filename}"
    subprocess.run(['curl', '-s', '-L', '-o', img_path, url], capture_output=True)
    content_type = 'image/png' if filename.endswith('.png') else 'image/jpeg'
    r = subprocess.run(['curl', '-s', '-b', COOKIE,
        '-H', f'X-WP-Nonce: {NONCE}',
        '-H', f'Content-Disposition: attachment; filename={filename}',
        '-H', f'Content-Type: {content_type}',
        '-X', 'POST',
        'https://funlikehel.pl/?rest_route=/wp/v2/media',
        '--data-binary', f'@{img_path}'],
        capture_output=True, text=True, encoding='utf-8')
    try:
        d = json.loads(r.stdout)
        if 'id' in d:
            return d['id']
    except:
        pass
    return None

# =====================================================
# 1. Dodaj YouTube i Google Reviews do strony glownej
# =====================================================
print("=== AKTUALIZACJA STRONY GLOWNEJ ===")
page = api("GET", "/wp/v2/pages/1329&context=edit")
content = page['content']['raw']

# Dodaj sekcje YouTube i Google Reviews PRZED ostatnim cover (CTA)
youtube_section = """
<!-- wp:group {"align":"full","style":{"spacing":{"padding":{"top":"60px","bottom":"60px"}}}} -->
<div class="wp-block-group alignfull" style="padding-top:60px;padding-bottom:60px"><!-- wp:heading {"textAlign":"center","level":2,"style":{"typography":{"fontSize":"38px"}}} -->
<h2 class="wp-block-heading has-text-align-center" style="font-size:38px">Zobacz nas w akcji</h2>
<!-- /wp:heading -->
<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center">Filmy z kursow, obozow i wypraw do Egiptu</p>
<!-- /wp:paragraph -->
<!-- wp:embed {"url":"https://www.youtube.com/@FunLikeHel","type":"rich","providerNameSlug":"youtube","className":"wp-embed-aspect-16-9"} -->
<figure class="wp-block-embed is-type-rich is-provider-youtube wp-block-embed-youtube wp-embed-aspect-16-9"><div class="wp-block-embed__wrapper">
https://www.youtube.com/@FunLikeHel
</div></figure>
<!-- /wp:embed -->
<!-- wp:columns {"align":"wide"} -->
<div class="wp-block-columns alignwide"><!-- wp:column -->
<div class="wp-block-column"><!-- wp:embed {"url":"https://www.youtube.com/watch?v=LATEST1","type":"video","providerNameSlug":"youtube"} -->
<figure class="wp-block-embed is-type-video is-provider-youtube wp-block-embed-youtube"><div class="wp-block-embed__wrapper">
https://www.youtube.com/@FunLikeHel/videos
</div></figure>
<!-- /wp:embed --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->
<div class="wp-block-buttons"><!-- wp:button {"className":"is-style-outline"} -->
<div class="wp-block-button is-style-outline"><a class="wp-block-button__link wp-element-button" href="https://www.youtube.com/@FunLikeHel" target="_blank">Zobacz wiecej na YouTube</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:group -->

<!-- wp:group {"align":"full","style":{"spacing":{"padding":{"top":"60px","bottom":"60px"}},"color":{"background":"#f9f9f9"}}} -->
<div class="wp-block-group alignfull" style="background-color:#f9f9f9;padding-top:60px;padding-bottom:60px"><!-- wp:heading {"textAlign":"center","level":2,"style":{"typography":{"fontSize":"38px"}}} -->
<h2 class="wp-block-heading has-text-align-center" style="font-size:38px">Opinie naszych klientow</h2>
<!-- /wp:heading -->
<!-- wp:paragraph {"align":"center"} -->
<p class="has-text-align-center">99% pozytywnych recenzji na Google</p>
<!-- /wp:paragraph -->
<!-- wp:html -->
<div style="text-align:center;margin:20px auto;max-width:800px;">
<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2322!2d33.6925!3d27.3347!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x1452653a6faee49d%3A0x9c73c2e88d773aa1!2sFUNLIKEHEL%20EGYPT%20Cabrinha%20Test%20Center!5e0!3m2!1spl!2spl" width="100%" height="400" style="border:0;border-radius:12px;" allowfullscreen="" loading="lazy"></iframe>
</div>
<!-- /wp:html -->
<!-- wp:buttons {"layout":{"type":"flex","justifyContent":"center"}} -->
<div class="wp-block-buttons"><!-- wp:button -->
<div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="https://maps.app.goo.gl/MU8Co8dDKndSkcVGA" target="_blank">Zobacz wszystkie opinie na Google</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons --></div>
<!-- /wp:group -->
"""

# Wstaw przed ostatnim cover (CTA z kempingiem)
last_cover_pos = content.rfind('<!-- wp:cover {"url":"https://funlikehel.pl/wp-content/uploads/2025/10/kemping2.png"')
if last_cover_pos > 0:
    content = content[:last_cover_pos] + youtube_section + content[last_cover_pos:]
    print("  Dodano YouTube + Google Reviews do strony glownej")
else:
    content = content + youtube_section
    print("  Dodano na koniec strony")

result = api("POST", "/wp/v2/pages/1329", {"content": content})
if isinstance(result, dict) and 'id' in result:
    print(f"  OK: Strona glowna zaktualizowana")
else:
    print(f"  ERR: {str(result)[:200]}")

# =====================================================
# 2. Wyczysc menu - usun WSZYSTKO i dodaj tylko 5 pozycji
# =====================================================
print("\n=== CZYSZCZE I BUDUJE MENU ===")

# Sprawdz wszystkie menu (nie tylko 22)
for menu_id in [22]:
    items = api("GET", f"/wp/v2/menu-items&menus={menu_id}&per_page=100")
    if isinstance(items, list):
        for item in items:
            api("DELETE", f"/wp/v2/menu-items/{item['id']}&force=true")
        print(f"  Wyczyszczono menu {menu_id} ({len(items)} pozycji)")

# Dodaj 5 pozycji
menu_pages = [
    ("Oferta", 2033, 1),
    ("Egipt", 2044, 2),
    ("Obozy i Kolonie", 2037, 3),
    ("Sklep", 2040, 4),
    ("Kontakt", 2042, 5),
]
for title, page_id, order in menu_pages:
    result = api("POST", "/wp/v2/menu-items", {
        "title": title, "type": "post_type", "object": "page",
        "object_id": page_id,
        "url": f"https://funlikehel.pl/?page_id={page_id}",
        "menus": 22, "menu_order": order, "parent": 0, "status": "publish"
    })
    if isinstance(result, dict) and 'id' in result:
        print(f"  OK  #{order} {title}")
    else:
        print(f"  ERR {title}")

# Sprawdz czy Twenty Twenty-Five uzywa innego menu niz 22
# FSE themes uzywaja navigation block - sprawdzmy
print("\n  Sprawdzam nawigacje FSE...")
nav_items = api("GET", "/wp/v2/navigation&per_page=10")
if isinstance(nav_items, list):
    for nav in nav_items:
        print(f"  Nav block: ID:{nav['id']} | {nav.get('title',{}).get('rendered','?')}")

print("\nGOTOWE!")
