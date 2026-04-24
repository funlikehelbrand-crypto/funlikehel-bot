import subprocess, json, sys

COOKIE = "C:/Users/\u0141ukaszMichalina/funlikehel/wp_cookies.txt"
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

def wc_block(query_id, cat_ids, cols=3, per_page=6):
    cats = cat_ids if isinstance(cat_ids, list) else [cat_ids]
    return (
        f'<!-- wp:woocommerce/product-collection {{"queryId":{query_id},"query":{{"perPage":{per_page},"pages":0,"offset":0,"postType":"product","order":"asc","orderBy":"price","search":"","exclude":[],"inherit":false,"taxQuery":{{"product_cat":{json.dumps(cats)}}},"isProductCollectionBlock":true,"featured":false,"woocommerceOnSale":false,"woocommerceStockStatus":["instock"],"woocommerceAttributes":[],"woocommerceHandPickedProducts":[]}},"tagName":"div","displayLayout":{{"type":"flex","columns":{cols}}}}} -->'
        '<div><!-- wp:woocommerce/product-template -->'
        '<!-- wp:woocommerce/product-image {"imageSizing":"thumbnail"} /-->'
        '<!-- wp:post-title {"isLink":true,"style":{"typography":{"fontSize":"15px"}}} /-->'
        '<!-- wp:woocommerce/product-price /-->'
        '<!-- /wp:woocommerce/product-template --></div>'
        '<!-- /wp:woocommerce/product-collection -->'
    )

content = (
    '<!-- wp:heading {"level":1,"style":{"typography":{"fontSize":"42px"}}} -->'
    '<h1 class="wp-block-heading" style="font-size:42px">Aquashop \u2014 Cabrinha 2026</h1>'
    '<!-- /wp:heading -->'

    '<!-- wp:paragraph {"style":{"typography":{"fontSize":"18px"}}} -->'
    '<p style="font-size:18px">Oficjalny Cabrinha Test Center. Ka\u017cdy produkt mo\u017cesz przetestowa\u0107 na wodzie w Jastarni lub Hurghadzie.</p>'
    '<!-- /wp:paragraph -->'

    '<!-- wp:list {"style":{"typography":{"fontSize":"16px"},"spacing":{"margin":{"top":"20px","bottom":"30px"}}}} -->'
    '<ul style="font-size:16px;margin-top:20px;margin-bottom:30px">'
    '<!-- wp:list-item --><li><a href="#latawce"><strong>Latawce</strong></a> \u2014 Switchblade, Drifter, Nitro, Moto X, Moto XL</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><a href="#deski"><strong>Deski Twin-Tip</strong></a> \u2014 ACE, Vapor, Spectrum, Stylus, XCal + wersje Apex</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><a href="#deski-surf"><strong>Deski Surf i Foil Board</strong></a> \u2014 Skillit, Logic</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><a href="#wing"><strong>Wing Foil</strong></a> \u2014 Mantis, Mantis Apex Aluula, AER 2, Vision</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><a href="#foile"><strong>Foile i Bary</strong></a> \u2014 H-Series, Prestige, Unify Control System</li><!-- /wp:list-item -->'
    '<!-- wp:list-item --><li><a href="#akcesoria"><strong>Akcesoria</strong></a> \u2014 pompki, kaski, leash, pady, pokrowce</li><!-- /wp:list-item -->'
    '</ul><!-- /wp:list -->'

    '<!-- wp:separator --><hr class="wp-block-separator"/><!-- /wp:separator -->'

    # LATAWCE
    '<!-- wp:html --><a id="latawce"></a><!-- /wp:html -->'
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Latawce</h2><!-- /wp:heading -->'
    '<!-- wp:paragraph --><p>Wszystkie modele Apex 2026 z Ultra HT Airframe i Teijin D2 Canopy.</p><!-- /wp:paragraph -->'
    + wc_block(11, 57, cols=3, per_page=6) +

    # DESKI TWIN-TIP
    '<!-- wp:html --><a id="deski"></a><!-- /wp:html -->'
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Deski Twin-Tip</h2><!-- /wp:heading -->'
    '<!-- wp:paragraph --><p>Od Spectrum dla pocz\u0105tkuj\u0105cych po XCal Apex dla freestyle.</p><!-- /wp:paragraph -->'
    + wc_block(12, 54, cols=4, per_page=12) +

    # DESKI SURF + FOIL BOARD
    '<!-- wp:html --><a id="deski-surf"></a><!-- /wp:html -->'
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Deski Surf i Foil Board</h2><!-- /wp:heading -->'
    + wc_block(16, [55, 56], cols=2, per_page=4) +

    # WING FOIL
    '<!-- wp:html --><a id="wing"></a><!-- /wp:html -->'
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Wing Foil</h2><!-- /wp:heading -->'
    '<!-- wp:paragraph --><p>Od AER 2 na start po Mantis Apex Aluula. Plus Vision do wave.</p><!-- /wp:paragraph -->'
    + wc_block(13, 58, cols=4, per_page=4) +

    # FOILE I BARY
    '<!-- wp:html --><a id="foile"></a><!-- /wp:html -->'
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Foile i Bary</h2><!-- /wp:heading -->'
    + wc_block(14, [59, 60], cols=3, per_page=4) +

    # AKCESORIA
    '<!-- wp:html --><a id="akcesoria"></a><!-- /wp:html -->'
    '<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"40px"}}}} -->'
    '<h2 class="wp-block-heading" style="margin-top:40px">Akcesoria</h2><!-- /wp:heading -->'
    + wc_block(15, 44, cols=3, per_page=6) +

    # CTA
    '<!-- wp:group {"style":{"spacing":{"padding":{"top":"40px","bottom":"40px"}},"color":{"background":"#e8f4f8"}}} -->'
    '<div class="wp-block-group" style="background-color:#e8f4f8;padding-top:40px;padding-bottom:40px">'
    '<!-- wp:paragraph {"align":"center","style":{"typography":{"fontSize":"20px"}}} -->'
    '<p class="has-text-align-center" style="font-size:20px">Chcesz przetestowa\u0107 sprz\u0119t na wodzie? \ud83d\udcde <a href="tel:690270032"><strong>690 270 032</strong></a></p>'
    '<!-- /wp:paragraph --></div><!-- /wp:group -->'
)

result = api("POST", "/wp/v2/pages/2040", {
    "content": content,
    "title": "Sklep \u2014 Aquashop Cabrinha 2026",
})
if isinstance(result, dict) and 'id' in result:
    print("OK: Sklep zaktualizowany")
else:
    print(f"ERR: {str(result)[:200]}")
