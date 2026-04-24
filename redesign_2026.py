import json
import base64
import urllib.request
import urllib.error
import os

auth_str = 'Admin:PDlm Q9wV AKvP tvlK uUEa 64zw'
auth = base64.b64encode(auth_str.encode()).decode()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def update_page(page_id, html_file):
    filepath = os.path.join(BASE_DIR, html_file)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    payload = json.dumps({'content': content}).encode('utf-8')

    req = urllib.request.Request(
        f'https://funlikehel.pl/wp-json/wp/v2/pages/{page_id}',
        data=payload,
        method='POST',
        headers={
            'Authorization': f'Basic {auth}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            print(f'OK page {page_id}: {data.get("link")}')
            return True
    except urllib.error.HTTPError as e:
        body = e.read()
        print(f'ERR page {page_id}: HTTP {e.code}')
        try:
            err = json.loads(body)
            print('  message:', err.get('message',''))
        except:
            print('  raw:', body[:300])
        return False

print('=== Redesign FUN like HEL 2026 ===')
print()
print('Aktualizacja Homepage (ID 1329)...')
update_page(1329, 'homepage_2026.html')

print()
print('Aktualizacja Ekipa (ID 2189)...')
update_page(2189, 'ekipa_2026.html')

print()
print('Gotowe!')
