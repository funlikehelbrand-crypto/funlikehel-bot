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

# 1. Usun puste kategorie
print("=== CZYSZCZE KATEGORIE ===")
empty_cats = [42, 40, 43, 39, 45, 38, 41]  # Bary, Deski, Foil, Latawce, Pokrowce, Uncategorized, Wing - stare puste
for cid in empty_cats:
    api("DELETE", f"/wc/v3/products/categories/{cid}&force=true")
print("  Usunieto puste kategorie")

# 2. Ustaw 4 produkty jako "featured" (promocyjne)
# Switchblade (6799), Spectrum (2359), Mantis (4249), H-Series (4999 promo)
print("\n=== USTAWIAM PROMOCYJNE ===")
featured_ids = [2191, 2177, 2203, 2213]  # Switchblade, Spectrum, Mantis, H-Series
for pid in featured_ids:
    result = api("PUT", f"/wc/v3/products/{pid}", {"featured": True})
    if not isinstance(result, dict) or 'id' not in result:
        result = api("POST", f"/wc/v3/products/{pid}", {"featured": True})
    if isinstance(result, dict) and 'id' in result:
        sys.stdout.buffer.write(f"  Featured: {result['name']}\n".encode('utf-8'))

# 3. Nowa strona sklepu z drzewem kategorii i promocjami
print("\n=== NOWA STRONA SKLEPU ===")

shop_content = """<!-- wp:heading {"level":1,"style":{"typography":{"fontSize":"42px"}}} -->
<h1 class="wp-block-heading" style="font-size:42px">Aquashop \u2014 Oficjalny Cabrinha Test Center</h1>
<!-- /wp:heading -->

<!-- wp:paragraph {"style":{"typography":{"fontSize":"18px"}}} -->
<p style="font-size:18px">Pe\u0142na kolekcja Cabrinha 2026. Ka\u017cdy produkt mo\u017cesz przetestowa\u0107 na wodzie w Jastarni lub Hurghadzie.</p>
<!-- /wp:paragraph -->

<!-- wp:group {"style":{"spacing":{"padding":{"top":"30px","bottom":"30px"}},"color":{"background":"#f5f5f5"},"border":{"radius":"12px"}}} -->
<div class="wp-block-group" style="background-color:#f5f5f5;padding-top:30px;padding-bottom:30px;border-radius:12px"><!-- wp:heading {"textAlign":"center","level":3} -->
<h3 class="wp-block-heading has-text-align-center">Znajd\u017a sw\u00f3j sprz\u0119t</h3>
<!-- /wp:heading -->
<!-- wp:columns {"align":"wide"} -->
<div class="wp-block-columns alignwide"><!-- wp:column {"textAlign":"center"} -->
<div class="wp-block-column has-text-align-center"><!-- wp:paragraph {"style":{"typography":{"fontSize":"32px"}}} --><p style="font-size:32px">\ud83e\ude81</p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><a href="#latawce"><strong>Latawce</strong></a><br>5 modeli</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column {"textAlign":"center"} -->
<div class="wp-block-column has-text-align-center"><!-- wp:paragraph {"style":{"typography":{"fontSize":"32px"}}} --><p style="font-size:32px">\ud83c\udfc4</p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><a href="#deski"><strong>Deski</strong></a><br>10 modeli</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column {"textAlign":"center"} -->
<div class="wp-block-column has-text-align-center"><!-- wp:paragraph {"style":{"typography":{"fontSize":"32px"}}} --><p style="font-size:32px">\ud83e\udeb6</p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><a href="#wing"><strong>Wing Foil</strong></a><br>4 modele</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column {"textAlign":"center"} -->
<div class="wp-block-column has-text-align-center"><!-- wp:paragraph {"style":{"typography":{"fontSize":"32px"}}} --><p style="font-size:32px">\u2699\ufe0f</p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><a href="#foile"><strong>Foile i Bary</strong></a><br>3 modele</p><!-- /wp:paragraph --></div>
<!-- /wp:column -->
<!-- wp:column {"textAlign":"center"} -->
<div class="wp-block-column has-text-align-center"><!-- wp:paragraph {"style":{"typography":{"fontSize":"32px"}}} --><p style="font-size:32px">\ud83c\udfaf</p><!-- /wp:paragraph -->
<!-- wp:paragraph --><p><a href="#akcesoria"><strong>Akcesoria</strong></a><br>5 produkt\u00f3w</p><!-- /wp:paragraph --></div>
<!-- /wp:column --></div>
<!-- /wp:columns --></div>
<!-- /wp:group -->

<!-- wp:group {"style":{"spacing":{"padding":{"top":"40px","bottom":"40px"}},"color":{"background":"#fff3e0"},"border":{"radius":"12px"}},"className":"promo-section"} -->
<div class="wp-block-group promo-section" style="background-color:#fff3e0;padding-top:40px;padding-bottom:40px;border-radius:12px"><!-- wp:heading {"textAlign":"center","level":2} -->
<h2 class="wp-block-heading has-text-align-center">\ud83d\udd25 Polecane produkty</h2>
<!-- /wp:heading -->
<!-- wp:woocommerce/product-collection {"queryId":10,"query":{"perPage":4,"pages":0,"offset":0,"postType":"product","order":"desc","orderBy":"date","search":"","exclude":[],"inherit":false,"taxQuery":{},"isProductCollectionBlock":true,"featured":true,"woocommerceOnSale":false,"woocommerceStockStatus":["instock","outofstock","onbackorder"],"woocommerceAttributes":[],"woocommerceHandPickedProducts":[]},"tagName":"div","displayLayout":{"type":"flex","columns":4}} -->
<div><!-- wp:woocommerce/product-template -->
<!-- wp:woocommerce/product-image {"imageSizing":"thumbnail"} /-->
<!-- wp:post-title {"isLink":true,"style":{"typography":{"fontSize":"16px"}}} /-->
<!-- wp:woocommerce/product-price /-->
<!-- wp:woocommerce/product-button {"style":{"typography":{"fontSize":"14px"}}} /-->
<!-- /wp:woocommerce/product-template --></div>
<!-- /wp:woocommerce/product-collection --></div>
<!-- /wp:group -->

<!-- wp:separator -->
<hr class="wp-block-separator"/>
<!-- /wp:separator -->

<!-- wp:html -->
<a id="latawce"></a>
<!-- /wp:html -->
<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"50px"}}}} -->
<h2 class="wp-block-heading" style="margin-top:50px">\ud83e\ude81 Latawce (Kites)</h2>
<!-- /wp:heading -->
<!-- wp:paragraph --><p>Od allroundu po big air i wave. Wszystkie modele Apex 2026 z Ultra HT Airframe i Teijin D2 Canopy.</p><!-- /wp:paragraph -->
<!-- wp:woocommerce/product-collection {"queryId":11,"query":{"perPage":6,"pages":0,"offset":0,"postType":"product","order":"asc","orderBy":"price","search":"","exclude":[],"inherit":false,"taxQuery":{"product_cat":[57]},"isProductCollectionBlock":true,"featured":false,"woocommerceOnSale":false,"woocommerceStockStatus":["instock"],"woocommerceAttributes":[],"woocommerceHandPickedProducts":[]},"tagName":"div","displayLayout":{"type":"flex","columns":3}} -->
<div><!-- wp:woocommerce/product-template -->
<!-- wp:woocommerce/product-image {"imageSizing":"thumbnail"} /-->
<!-- wp:post-title {"isLink":true,"style":{"typography":{"fontSize":"16px"}}} /-->
<!-- wp:woocommerce/product-price /-->
<!-- wp:woocommerce/product-button /-->
<!-- /wp:woocommerce/product-template --></div>
<!-- /wp:woocommerce/product-collection -->

<!-- wp:html -->
<a id="deski"></a>
<!-- /wp:html -->
<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"50px"}}}} -->
<h2 class="wp-block-heading" style="margin-top:50px">\ud83c\udfc4 Deski</h2>
<!-- /wp:heading -->
<!-- wp:paragraph --><p>Twin-tipy, surfboardy i foil boardy. Od Spectrum dla pocz\u0105tkuj\u0105cych po XCal Apex dla freestyle maszyn.</p><!-- /wp:paragraph -->
<!-- wp:woocommerce/product-collection {"queryId":12,"query":{"perPage":12,"pages":0,"offset":0,"postType":"product","order":"asc","orderBy":"price","search":"","exclude":[],"inherit":false,"taxQuery":{"product_cat":[54,55,56]},"isProductCollectionBlock":true,"featured":false,"woocommerceOnSale":false,"woocommerceStockStatus":["instock"],"woocommerceAttributes":[],"woocommerceHandPickedProducts":[]},"tagName":"div","displayLayout":{"type":"flex","columns":4}} -->
<div><!-- wp:woocommerce/product-template -->
<!-- wp:woocommerce/product-image {"imageSizing":"thumbnail"} /-->
<!-- wp:post-title {"isLink":true,"style":{"typography":{"fontSize":"16px"}}} /-->
<!-- wp:woocommerce/product-price /-->
<!-- wp:woocommerce/product-button /-->
<!-- /wp:woocommerce/product-template --></div>
<!-- /wp:woocommerce/product-collection -->

<!-- wp:html -->
<a id="wing"></a>
<!-- /wp:html -->
<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"50px"}}}} -->
<h2 class="wp-block-heading" style="margin-top:50px">\ud83e\udeb6 Wing Foil</h2>
<!-- /wp:heading -->
<!-- wp:paragraph --><p>Od AER 2 na start po Mantis Apex Aluula dla wymagaj\u0105cych. Plus nowy Vision do wave.</p><!-- /wp:paragraph -->
<!-- wp:woocommerce/product-collection {"queryId":13,"query":{"perPage":4,"pages":0,"offset":0,"postType":"product","order":"asc","orderBy":"price","search":"","exclude":[],"inherit":false,"taxQuery":{"product_cat":[58]},"isProductCollectionBlock":true,"featured":false,"woocommerceOnSale":false,"woocommerceStockStatus":["instock"],"woocommerceAttributes":[],"woocommerceHandPickedProducts":[]},"tagName":"div","displayLayout":{"type":"flex","columns":4}} -->
<div><!-- wp:woocommerce/product-template -->
<!-- wp:woocommerce/product-image {"imageSizing":"thumbnail"} /-->
<!-- wp:post-title {"isLink":true,"style":{"typography":{"fontSize":"16px"}}} /-->
<!-- wp:woocommerce/product-price /-->
<!-- wp:woocommerce/product-button /-->
<!-- /wp:woocommerce/product-template --></div>
<!-- /wp:woocommerce/product-collection -->

<!-- wp:html -->
<a id="foile"></a>
<!-- /wp:html -->
<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"50px"}}}} -->
<h2 class="wp-block-heading" style="margin-top:50px">\u2699\ufe0f Foile i Bary</h2>
<!-- /wp:heading -->
<!-- wp:paragraph --><p>Karbonowe foile i system kontroli Unify 2026.</p><!-- /wp:paragraph -->
<!-- wp:woocommerce/product-collection {"queryId":14,"query":{"perPage":4,"pages":0,"offset":0,"postType":"product","order":"asc","orderBy":"price","search":"","exclude":[],"inherit":false,"taxQuery":{"product_cat":[59,60]},"isProductCollectionBlock":true,"featured":false,"woocommerceOnSale":false,"woocommerceStockStatus":["instock"],"woocommerceAttributes":[],"woocommerceHandPickedProducts":[]},"tagName":"div","displayLayout":{"type":"flex","columns":3}} -->
<div><!-- wp:woocommerce/product-template -->
<!-- wp:woocommerce/product-image {"imageSizing":"thumbnail"} /-->
<!-- wp:post-title {"isLink":true,"style":{"typography":{"fontSize":"16px"}}} /-->
<!-- wp:woocommerce/product-price /-->
<!-- wp:woocommerce/product-button /-->
<!-- /wp:woocommerce/product-template --></div>
<!-- /wp:woocommerce/product-collection -->

<!-- wp:html -->
<a id="akcesoria"></a>
<!-- /wp:html -->
<!-- wp:heading {"level":2,"style":{"spacing":{"margin":{"top":"50px"}}}} -->
<h2 class="wp-block-heading" style="margin-top:50px">\ud83c\udfaf Akcesoria</h2>
<!-- /wp:heading -->
<!-- wp:paragraph --><p>Pompki, kaski, leash, pady, pokrowce \u2014 wszystko co potrzebujesz na wod\u0119.</p><!-- /wp:paragraph -->
<!-- wp:woocommerce/product-collection {"queryId":15,"query":{"perPage":6,"pages":0,"offset":0,"postType":"product","order":"asc","orderBy":"price","search":"","exclude":[],"inherit":false,"taxQuery":{"product_cat":[44]},"isProductCollectionBlock":true,"featured":false,"woocommerceOnSale":false,"woocommerceStockStatus":["instock"],"woocommerceAttributes":[],"woocommerceHandPickedProducts":[]},"tagName":"div","displayLayout":{"type":"flex","columns":3}} -->
<div><!-- wp:woocommerce/product-template -->
<!-- wp:woocommerce/product-image {"imageSizing":"thumbnail"} /-->
<!-- wp:post-title {"isLink":true,"style":{"typography":{"fontSize":"16px"}}} /-->
<!-- wp:woocommerce/product-price /-->
<!-- wp:woocommerce/product-button /-->
<!-- /wp:woocommerce/product-template --></div>
<!-- /wp:woocommerce/product-collection -->

<!-- wp:group {"style":{"spacing":{"padding":{"top":"40px","bottom":"40px"}},"color":{"background":"#e8f4f8"}}} -->
<div class="wp-block-group" style="background-color:#e8f4f8;padding-top:40px;padding-bottom:40px"><!-- wp:paragraph {"align":"center","style":{"typography":{"fontSize":"20px"}}} -->
<p class="has-text-align-center" style="font-size:20px">Chcesz przetestowa\u0107 sprz\u0119t na wodzie? \ud83d\udcde <a href="tel:690270032"><strong>690 270 032</strong></a></p>
<!-- /wp:paragraph --></div>
<!-- /wp:group -->"""

result = api("POST", "/wp/v2/pages/2040", {
    "content": shop_content,
    "title": "Sklep \u2014 Aquashop Cabrinha 2026",
})
if isinstance(result, dict) and 'id' in result:
    print(f"  OK: Sklep zaktualizowany")
else:
    print(f"  ERR: {str(result)[:200]}")

print("\nGOTOWE!")
