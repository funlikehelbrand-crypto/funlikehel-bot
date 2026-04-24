import subprocess, json, sys

NONCE = "c0655d99ca"
COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"

# Pobierz content strony glownej
r = subprocess.run(['curl', '-s', '-b', COOKIE, '-H', f'X-WP-Nonce: {NONCE}',
    'https://funlikehel.pl/?rest_route=/wp/v2/pages/1329&context=edit'],
    capture_output=True, text=True, encoding='utf-8')
d = json.loads(r.stdout)
content = d['content']['raw']

print(f"Content dlugosc: {len(content)}")
print(f"Stare URL w tresci: {'DSC08514' in content}")

# Podmien hero
old_url = 'https://funlikehel.pl/wp-content/uploads/2025/10/DSC08514-scaled.jpg'
new_url = 'https://funlikehel.pl/wp-content/uploads/2026/04/IMG_5051.jpg'

content_new = content.replace(old_url, new_url).replace('wp-image-1758', 'wp-image-2059')
print(f"Nowe URL w tresci: {new_url in content_new}")

# Zapisz do pliku zeby curl mogl wczytac
payload_path = "C:/Users/\u0141ukaszMichalina/funlikehel/payload_hero.json"
with open(payload_path, 'w', encoding='utf-8') as f:
    json.dump({'content': content_new}, f, ensure_ascii=False)

r2 = subprocess.run(['curl', '-s', '-b', COOKIE,
    '-H', f'X-WP-Nonce: {NONCE}',
    '-H', 'Content-Type: application/json',
    '-X', 'POST',
    'https://funlikehel.pl/?rest_route=/wp/v2/pages/1329',
    '--data-binary', f'@{payload_path}'],
    capture_output=True, text=True, encoding='utf-8')

try:
    d2 = json.loads(r2.stdout)
    if 'id' in d2:
        print(f"OK! Hero podmieniony. Link: {d2['link']}")
    else:
        print(f"ERR: {r2.stdout[:300]}")
except Exception as e:
    print(f"ERR parse: {e}")
    print(r2.stdout[:200])
