"""
Wstaw chat widget inline + social icons do WPCode footer
"""
import subprocess, re

COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"
subprocess.run(['curl', '-s', '-c', COOKIE, 'https://funlikehel.pl/wp-login.php'], capture_output=True)
with open(COOKIE, 'a') as f:
    f.write("funlikehel.pl\tFALSE\t/\tTRUE\t0\twordpress_test_cookie\tWP%20Cookie%20check\n")
subprocess.run(['curl', '-s', '-c', COOKIE, '-b', COOKIE,
    '-d', 'log=Admin&pwd=Japoniamarzen1!&wp-submit=Log+In&redirect_to=%2Fwp-admin%2F&testcookie=1',
    'https://funlikehel.pl/wp-login.php'], capture_output=True)

# Pobierz nonce WPCode
r = subprocess.run(['curl', '-s', '-b', COOKIE,
    'https://funlikehel.pl/wp-admin/admin.php?page=wpcode-headers-footers'],
    capture_output=True, text=True, encoding='utf-8')
nonce = re.findall(r'insert-headers-and-footers_nonce.*?value="([a-f0-9]+)"', r.stdout)
if not nonce:
    print("Brak nonce"); exit(1)
print(f"WPCode nonce: {nonce[0]}")

# Czytaj widget JS
with open("C:/Users/\u0141ukaszMichalina/funlikehel/server/static/chat-widget.js", "r", encoding="utf-8") as f:
    widget_js = f.read()

footer_code = """<style>
.flh-social{position:fixed;left:24px;bottom:24px;z-index:99998;display:flex;flex-direction:column;gap:10px}
.flh-social a{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;transition:transform .2s;box-shadow:0 2px 8px rgba(0,0,0,.2)}
.flh-social a:hover{transform:scale(1.15)}
.flh-social a svg{width:22px;height:22px;fill:#fff}
.flh-social .ig{background:linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888)}
.flh-social .yt{background:#FF0000}
.flh-social .tt{background:#000}
.flh-social .fb{background:#1877F2}
</style>
<div class="flh-social">
<a href="https://www.instagram.com/funlikehel/" target="_blank" class="ig" title="Instagram"><svg viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg></a>
<a href="https://www.youtube.com/@FunLikeHel" target="_blank" class="yt" title="YouTube"><svg viewBox="0 0 24 24"><path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg></a>
<a href="https://www.tiktok.com/@funlikehel" target="_blank" class="tt" title="TikTok"><svg viewBox="0 0 24 24"><path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"/></svg></a>
<a href="https://www.facebook.com/funlikehel" target="_blank" class="fb" title="Facebook"><svg viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg></a>
</div>
<script>
""" + widget_js + """
</script>"""

# Zapisz footer
r = subprocess.run(['curl', '-s', '-b', COOKIE,
    '-X', 'POST',
    'https://funlikehel.pl/wp-admin/admin.php?page=wpcode-headers-footers',
    '--data-urlencode', f'insert-headers-and-footers_nonce={nonce[0]}',
    '--data-urlencode', 'ihaf_insert_header=',
    '--data-urlencode', 'ihaf_insert_body=',
    '--data-urlencode', f'ihaf_insert_footer={footer_code}',
    '--data-urlencode', 'submit=Save Changes'],
    capture_output=True, text=True)
print(f"Status: {r.returncode}")

# Weryfikacja
r2 = subprocess.run(['curl', '-s', 'https://funlikehel.pl/'],
    capture_output=True, text=True, encoding='utf-8')
has_social = 'flh-social' in r2.stdout
has_chat = 'flh-chat-btn' in r2.stdout
print(f"Social icons: {'OK' if has_social else 'BRAK'}")
print(f"Chatbot: {'OK' if has_chat else 'BRAK'}")
