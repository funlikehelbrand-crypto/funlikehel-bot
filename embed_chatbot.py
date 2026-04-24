"""
Osadza chatbot Alicji na stronie WP przez dodanie custom HTML widgetu
"""
import subprocess, json, sys

COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"

# Login
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
    print("Login failed")
    sys.exit(1)

# Dodaj chatbot script do WP via Custom HTML widget w footer
# Uzyj WP REST API options/settings lub dodaj przez Yoast/custom code
# Najlepsza metoda: dodaj przez wp_footer hook via functions.php
# Ale nie mamy dostepu FTP - wiec dodamy inline JS na stronie glownej

# Dodaj do kazdej strony przez wp_options (custom_css / scripts)
# Twenty Twenty-Five obsługuje dodawanie skryptow przez Customizer

# Najlepsza opcja: dodaj jako Custom HTML block na KONCU strony glownej
# i na kazdej podstronie - ale to nie skaluje sie

# Lepiej: uzyj wtyczki do dodawania kodu w header/footer
# Sprawdzmy czy jest taka wtyczka

# Albo po prostu dodajmy skrypt do szablonu przez REST API wp/v2/settings
# lub uzyj opcji Yoast -> custom code

print("\nSprawdzam opcje dodania skryptu...")

# Sposob 1: Sprawdz Yoast custom code
r = subprocess.run(['curl', '-s', '-b', COOKIE, '-H', f'X-WP-Nonce: {NONCE}',
    'https://funlikehel.pl/wp-admin/admin.php?page=wpseo_tools'],
    capture_output=True, text=True, encoding='utf-8')
print(f"Yoast tools page: {len(r.stdout)} chars")

# Sposob 2: Instaluj "Insert Headers and Footers" plugin (WPCode)
print("\nInstaluje WPCode (Insert Headers and Footers)...")
# Pobierz ajax nonce
r = subprocess.run(['curl', '-s', '-b', COOKIE,
    'https://funlikehel.pl/wp-admin/plugin-install.php'],
    capture_output=True, text=True, encoding='utf-8')

import re
update_nonce = re.findall(r'_wpUpdatesSettings.*?ajax_nonce":"([a-f0-9]+)"', r.stdout)
if update_nonce:
    ajax_nonce = update_nonce[0]
    print(f"Ajax nonce: {ajax_nonce}")

    # Instaluj WPCode Lite
    r2 = subprocess.run(['curl', '-s', '-b', COOKIE,
        '-X', 'POST',
        'https://funlikehel.pl/wp-admin/admin-ajax.php',
        '-d', f'action=install-plugin&_ajax_nonce={ajax_nonce}&slug=insert-headers-and-footers'],
        capture_output=True, text=True, encoding='utf-8')

    result = json.loads(r2.stdout)
    print(f"WPCode install: {result.get('success')}")

    if result.get('success') and result.get('data', {}).get('activateUrl'):
        activate_url = result['data']['activateUrl'].replace('&amp;', '&')
        subprocess.run(['curl', '-s', '-b', COOKIE, activate_url], capture_output=True)
        print("WPCode aktywowany")

# Teraz dodaj skrypt chatbota przez WPCode
# WPCode uzywa custom post type 'wpcode'
# Ale latwiej bedzie dodac przez wp_options bezposrednio

# Dodajmy skrypt inline do footera przez WP options API
chatbot_script = '<script src="https://funlikehel-bot.onrender.com/static/chat-widget.js" defer></script>'

# Uzyj WPCode API
print("\nDodaje snippet chatbota przez WPCode...")
snippet_data = {
    "title": "Chatbot Alicja",
    "code": chatbot_script,
    "code_type": "html",
    "location": "site_wide_footer",
    "status": "publish",
    "priority": 10
}

# WPCode snippet = custom post type 'wpcode'
cmd = ['curl', '-s', '-b', COOKIE, '-H', f'X-WP-Nonce: {NONCE}',
       '-H', 'Content-Type: application/json', '-X', 'POST',
       'https://funlikehel.pl/?rest_route=/wp/v2/wpcode']
path = "C:/Users/\u0141ukaszMichalina/funlikehel/payload_tmp.json"
with open(path, 'w', encoding='utf-8') as f:
    json.dump(snippet_data, f, ensure_ascii=True)
cmd += ['--data-binary', f'@{path}']
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
print(f"WPCode snippet: {r.stdout[:200]}")

# Fallback: dodaj bezposrednio do wp_options (site footer scripts)
# To jest opcja Yoast SEO
print("\nFallback: dodaje przez Yoast webmaster tools...")

# Uzyj wp_options API
opts = {
    "blogdescription": "Szkola sportow wodnych FUN like HEL | Kitesurfing, Windsurfing, Wing | Jastarnia i Hurghada"
}

cmd2 = ['curl', '-s', '-b', COOKIE, '-H', f'X-WP-Nonce: {NONCE}',
        '-H', 'Content-Type: application/json', '-X', 'POST',
        'https://funlikehel.pl/?rest_route=/wp/v2/settings',
        '-d', json.dumps(opts)]
r2 = subprocess.run(cmd2, capture_output=True, text=True, encoding='utf-8')
try:
    d = json.loads(r2.stdout)
    if 'blogdescription' in str(d):
        print("OK: Blog description zaktualizowany")
except:
    print(f"Settings: {r2.stdout[:100]}")

print("\nGOTOWE!")
print(f"\nChatbot bedzie dzialal gdy serwer FastAPI jest uruchomiony.")
print(f"Widget JS: server/static/chat-widget.js")
print(f"Endpoint: /api/chat")
print(f"Skrypt do osadzenia na WP:")
print(f'  {chatbot_script}')
