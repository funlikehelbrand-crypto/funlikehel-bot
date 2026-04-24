"""
1. Napraw nawigacje FSE - zamiast page-list daj konkretne 5 linkow
2. Trash stare strony (retry)
"""
import subprocess, json, sys

COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"

# Relogin
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
    print("FATAL: login failed")
    sys.exit(1)

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
# 1. NAPRAW NAWIGACJE FSE
# =====================================================
print("\n=== NAPRAWIAM NAWIGACJE FSE ===")

nav_content = (
    '<!-- wp:navigation-link {"label":"Oferta","type":"page","id":2033,"url":"https://funlikehel.pl/?page_id=2033","kind":"post-type","isTopLevelLink":true} /-->'
    '\n<!-- wp:navigation-link {"label":"Egipt","type":"page","id":2044,"url":"https://funlikehel.pl/?page_id=2044","kind":"post-type","isTopLevelLink":true} /-->'
    '\n<!-- wp:navigation-link {"label":"Obozy i Kolonie","type":"page","id":2037,"url":"https://funlikehel.pl/?page_id=2037","kind":"post-type","isTopLevelLink":true} /-->'
    '\n<!-- wp:navigation-link {"label":"Sklep","type":"page","id":2040,"url":"https://funlikehel.pl/?page_id=2040","kind":"post-type","isTopLevelLink":true} /-->'
    '\n<!-- wp:navigation-link {"label":"Kontakt","type":"page","id":2042,"url":"https://funlikehel.pl/?page_id=2042","kind":"post-type","isTopLevelLink":true} /-->'
)

result = api("POST", "/wp/v2/navigation/6", {
    "content": nav_content,
    "status": "publish"
})
if isinstance(result, dict) and 'id' in result:
    print("  OK: Nawigacja FSE ustawiona na 5 linkow")
else:
    print(f"  ERR: {str(result)[:200]}")

# =====================================================
# 2. TRASH STARE STRONY
# =====================================================
print("\n=== USUWAM STARE STRONY ===")

KEEP_IDS = {1329, 2033, 2044, 2037, 2040, 2042, 1214, 1215, 1216, 2101, 2102}

# Published
pages = api("GET", "/wp/v2/pages&per_page=100&status=publish")
if isinstance(pages, list):
    for p in pages:
        pid = p['id']
        title = p['title']['rendered']
        if pid not in KEEP_IDS:
            result = api("DELETE", f"/wp/v2/pages/{pid}")
            if isinstance(result, dict):
                sys.stdout.buffer.write(f"  Trash: {title} (ID:{pid})\n".encode('utf-8'))
            else:
                # Try POST status=trash
                result2 = api("POST", f"/wp/v2/pages/{pid}", {"status": "trash"})
                if isinstance(result2, dict) and result2.get('status') == 'trash':
                    sys.stdout.buffer.write(f"  Trash(2): {title} (ID:{pid})\n".encode('utf-8'))
                else:
                    sys.stdout.buffer.write(f"  ERR: {title} (ID:{pid})\n".encode('utf-8'))

# Drafty
pages_draft = api("GET", "/wp/v2/pages&per_page=100&status=draft")
if isinstance(pages_draft, list):
    for p in pages_draft:
        pid = p['id']
        title = p['title']['rendered']
        if pid not in KEEP_IDS:
            api("DELETE", f"/wp/v2/pages/{pid}")
            sys.stdout.buffer.write(f"  Trash draft: {title} (ID:{pid})\n".encode('utf-8'))

# =====================================================
# 3. WERYFIKACJA
# =====================================================
print("\n=== WERYFIKACJA ===")
remaining = api("GET", "/wp/v2/pages&per_page=100&status=publish")
if isinstance(remaining, list):
    print(f"  Pozostalo {len(remaining)} opublikowanych stron:")
    for p in remaining:
        sys.stdout.buffer.write(f"    {p['title']['rendered']}\n".encode('utf-8'))

# Sprawdz nawigacje
nav = api("GET", "/wp/v2/navigation/6&context=edit")
if isinstance(nav, dict):
    content = nav.get('content', {}).get('raw', '')
    sys.stdout.buffer.write(f"\n  Nawigacja FSE:\n  {content[:300]}\n".encode('utf-8'))

print("\nGOTOWE!")
