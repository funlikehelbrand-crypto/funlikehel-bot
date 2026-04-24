import subprocess, json, sys

NONCE = "c0655d99ca"
COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"

def api(method, route, data=None):
    cmd = ['curl', '-s', '-b', COOKIE, '-H', f'X-WP-Nonce: {NONCE}',
           '-H', 'Content-Type: application/json', '-X', method,
           f'https://funlikehel.pl/?rest_route={route}']
    if data:
        payload_path = "C:/Users/\u0141ukaszMichalina/funlikehel/payload_tmp.json"
        with open(payload_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        cmd += ['--data-binary', f'@{payload_path}']
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    try:
        return json.loads(r.stdout)
    except:
        return r.stdout

# Stare pozycje do usunięcia
old_ids = [27, 28, 1203, 1205, 1994, 31, 32, 2054]  # 2054 to duplikat
print("=== Usuwam stare pozycje menu ===")
for mid in old_ids:
    result = api("DELETE", f"/wp/v2/menu-items/{mid}&force=true")
    if isinstance(result, dict) and 'deleted' in result:
        print(f"  Usunieto ID:{mid}")
    else:
        print(f"  Skip ID:{mid}: {str(result)[:80]}")

# Nowe pozycje - ustaw prawidlowy porzadek
print("\n=== Ustawiam kolejnosc ===")
new_order = [
    (2052, 1, 0),     # Kitesurfing
    (2055, 1, 2052),   # └─ Polska – Jastarnia
    (2056, 2, 2052),   # └─ Egipt – Hurghada
    (2045, 2, 0),      # Windsurfing
    (2046, 3, 0),      # Wing / SUP
    (2047, 4, 0),      # Wakeboarding
    (2053, 5, 0),      # Obozy i Kolonie
    (2048, 6, 0),      # Femi Campy
    (2049, 7, 0),      # Nocleg
    (2050, 8, 0),      # Aquashop
    (2051, 9, 0),      # Kontakt
]

for mid, order, parent in new_order:
    result = api("POST", f"/wp/v2/menu-items/{mid}", {
        "menu_order": order,
        "parent": parent
    })
    if isinstance(result, dict) and 'id' in result:
        title = result.get('title', {}).get('rendered', '?')
        print(f"  OK  #{order} {title}")
    else:
        print(f"  ERR ID:{mid}: {str(result)[:80]}")

# Weryfikacja
print("\n=== Menu finalne ===")
items = api("GET", "/wp/v2/menu-items&menus=22&per_page=50")
if isinstance(items, list):
    items.sort(key=lambda x: (x['parent'], x['menu_order']))
    for item in items:
        title = item['title']['rendered']
        prefix = "  \u2514\u2500 " if item['parent'] > 0 else ""
        print(f"  {prefix}{title}")
