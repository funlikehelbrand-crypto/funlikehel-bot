"""
Porządki: usunięcie starych stron, wyczyszczenie menu, sprawdzenie nawigacji FSE
"""
import subprocess, json, sys

NONCE = "ae86df740a"
COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"

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
# ZOSTAWIAMY (6 stron + 3 WooCommerce + 2 prawne):
# 1329  Home
# 2033  Oferta
# 2044  Egipt
# 2037  Obozy i Kolonie
# 2040  Sklep
# 2042  Kontakt
# 1214  Cart (WooCommerce)
# 1215  Checkout (WooCommerce)
# 1216  My Account (WooCommerce)
# 2101  Polityka Prywatności
# 2102  Regulamin
# =====================================================

KEEP_IDS = {1329, 2033, 2044, 2037, 2040, 2042, 1214, 1215, 1216, 2101, 2102}

# Trash stare published strony
print("=== USUWAM STARE STRONY (trash) ===")
r = api("GET", "/wp/v2/pages&per_page=100&status=publish&context=edit")
if isinstance(r, list):
    for p in r:
        pid = p['id']
        title = p['title']['raw']
        if pid not in KEEP_IDS:
            result = api("POST", f"/wp/v2/pages/{pid}", {"status": "trash"})
            if isinstance(result, dict) and 'id' in result:
                sys.stdout.buffer.write(f"  Trash: {title} (ID:{pid})\n".encode('utf-8'))
            else:
                sys.stdout.buffer.write(f"  ERR: {title}\n".encode('utf-8'))
        else:
            sys.stdout.buffer.write(f"  KEEP: {title} (ID:{pid})\n".encode('utf-8'))

# Trash drafty
print("\n=== USUWAM DRAFTY ===")
r = api("GET", "/wp/v2/pages&per_page=100&status=draft&context=edit")
if isinstance(r, list):
    for p in r:
        pid = p['id']
        title = p['title']['raw']
        if pid not in KEEP_IDS:
            result = api("POST", f"/wp/v2/pages/{pid}", {"status": "trash"})
            if isinstance(result, dict) and 'id' in result:
                sys.stdout.buffer.write(f"  Trash: {title} (ID:{pid})\n".encode('utf-8'))

# =====================================================
# MENU TRADYCYJNE - wyczysc i ustaw
# =====================================================
print("\n=== MENU TRADYCYJNE ===")
items = api("GET", "/wp/v2/menu-items&menus=22&per_page=100")
if isinstance(items, list):
    for item in items:
        api("DELETE", f"/wp/v2/menu-items/{item['id']}&force=true")
    print(f"  Wyczyszczono {len(items)} pozycji")

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
        print(f"  OK #{order} {title}")

# =====================================================
# FSE NAWIGACJA - Twenty Twenty-Five uzywa navigation block
# =====================================================
print("\n=== NAWIGACJA FSE ===")
navs = api("GET", "/wp/v2/navigation&per_page=20")
if isinstance(navs, list):
    print(f"  Znaleziono {len(navs)} blokow nawigacji")
    for nav in navs:
        nav_id = nav['id']
        title = nav.get('title', {}).get('rendered', '?')
        status = nav.get('status', '?')
        content_raw = nav.get('content', {}).get('raw', '')
        sys.stdout.buffer.write(f"  Nav ID:{nav_id} [{status}] '{title}' ({len(content_raw)} chars)\n".encode('utf-8'))

# Pobierz pelna tresc nawigacji
print("\n=== TRESC NAWIGACJI FSE (context=edit) ===")
navs_edit = api("GET", "/wp/v2/navigation&per_page=20&context=edit")
if isinstance(navs_edit, list):
    for nav in navs_edit:
        nav_id = nav['id']
        title = nav.get('title', {}).get('raw', '?')
        content = nav.get('content', {}).get('raw', '')
        sys.stdout.buffer.write(f"\n  Nav ID:{nav_id} '{title}':\n".encode('utf-8'))
        sys.stdout.buffer.write(f"  {content[:500]}\n".encode('utf-8'))

print("\nGOTOWE!")
