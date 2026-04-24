import subprocess, json, sys

NONCE = "c0655d99ca"
COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"

def api_get(route):
    r = subprocess.run(['curl', '-s', '-b', COOKIE, '-H', f'X-WP-Nonce: {NONCE}',
        f'https://funlikehel.pl/?rest_route={route}'],
        capture_output=True, text=True, encoding='utf-8')
    return json.loads(r.stdout)

def api_post(route, data):
    payload_path = "C:/Users/\u0141ukaszMichalina/funlikehel/payload_tmp.json"
    with open(payload_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    r = subprocess.run(['curl', '-s', '-b', COOKIE,
        '-H', f'X-WP-Nonce: {NONCE}',
        '-H', 'Content-Type: application/json',
        '-X', 'POST',
        f'https://funlikehel.pl/?rest_route={route}',
        '--data-binary', f'@{payload_path}'],
        capture_output=True, text=True, encoding='utf-8')
    return json.loads(r.stdout)

# 1. Podmien hero na IMG_5278 (z latawcem) i napraw URL na -scaled
print("=== Podmieniam hero ===")
page = api_get("/wp/v2/pages/1329&context=edit")
content = page['content']['raw']

# Fix: IMG_5051.jpg -> IMG_5278-scaled.jpg (poprawny URL z WP)
content = content.replace(
    'https://funlikehel.pl/wp-content/uploads/2026/04/IMG_5051.jpg',
    'https://funlikehel.pl/wp-content/uploads/2026/04/IMG_5278-scaled.jpg'
)
content = content.replace('wp-image-2059', 'wp-image-2060')

# Napraw tez stare referencje DSC08514 w galerii na nowe zdjecia cabrinha
content = content.replace(
    'https://funlikehel.pl/wp-content/uploads/2025/10/DSC08514-scaled.jpg" alt="FUN like HEL" class="wp-image-1758"',
    'https://funlikehel.pl/wp-content/uploads/2026/04/IMG_5292-scaled.jpg" alt="Kitesurfing FUN like HEL" class="wp-image-2061"'
)

result = api_post("/wp/v2/pages/1329", {"content": content})
if 'id' in result:
    print("OK! Hero -> IMG_5278")
else:
    print(f"ERR: {str(result)[:200]}")

# 2. Sprawdz aktualne pozycje menu i wyczysc stare
print("\n=== Naprawiam menu ===")
menu_items = api_get("/wp/v2/menu-items&menus=22&per_page=100")
print(f"Pozycje w menu: {len(menu_items)}")
for item in menu_items:
    title = item['title']['rendered']
    mid = item['id']
    parent = item['parent']
    order = item['menu_order']
    print(f"  ID:{mid} order:{order} parent:{parent} | {title}")
