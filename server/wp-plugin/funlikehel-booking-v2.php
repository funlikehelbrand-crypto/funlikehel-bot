<?php
/**
 * Plugin Name: FUN like HEL — Booking v2
 * Description: Multi-service booking form. Connects to FastAPI booking API.
 * Version: 2.0.0
 * Author: FUN like HEL
 */

if (!defined('ABSPATH')) exit;

// ---------------------------------------------------------------------------
// Admin menu — view bookings via API
// ---------------------------------------------------------------------------

add_action('admin_menu', function () {
    add_menu_page(
        'Rezerwacje FLH',
        'Rezerwacje',
        'manage_options',
        'flh-bookings',
        'flh_admin_bookings_page',
        'dashicons-calendar-alt',
        26
    );
});

function flh_admin_bookings_page() {
    $api_base  = get_option('flh_api_base_url', 'https://funlikehel-bot.onrender.com');
    $api_token = get_option('flh_booking_admin_token', '');
    $location  = sanitize_text_field($_GET['location'] ?? '');
    $status    = sanitize_text_field($_GET['status'] ?? '');

    $url = $api_base . '/api/admin/bookings';
    $params = [];
    if ($location) $params[] = "location=$location";
    if ($status)   $params[] = "status=$status";
    if ($params)   $url .= '?' . implode('&', $params);

    $response = wp_remote_get($url, [
        'headers' => ['X-Admin-Token' => $api_token],
        'timeout' => 15,
    ]);

    $bookings = [];
    $error    = '';
    if (is_wp_error($response)) {
        $error = $response->get_error_message();
    } else {
        $data = json_decode(wp_remote_retrieve_body($response), true);
        $bookings = $data['bookings'] ?? [];
    }

    $status_labels = [
        'pending'   => '<span style="color:#e67e22">⏳ Oczekuje</span>',
        'confirmed' => '<span style="color:#27ae60">✅ Potwierdzone</span>',
        'completed' => '<span style="color:#2980b9">🏄 Zakończone</span>',
        'cancelled' => '<span style="color:#c0392b">❌ Anulowane</span>',
        'no_show'   => '<span style="color:#95a5a6">👻 No-show</span>',
    ];
    $pay_labels = [
        'unpaid'       => '<span style="color:#e74c3c">Nieopłacone</span>',
        'deposit_paid' => '<span style="color:#f39c12">Zaliczka</span>',
        'paid'         => '<span style="color:#27ae60">Opłacone</span>',
        'refunded'     => '<span style="color:#8e44ad">Zwrócone</span>',
    ];

    ?>
    <div class="wrap">
        <h1>Rezerwacje FUN like HEL</h1>

        <form method="get" style="margin-bottom:16px">
            <input type="hidden" name="page" value="flh-bookings">
            <select name="location">
                <option value="">Wszystkie lokalizacje</option>
                <option value="hurghada" <?= $location === 'hurghada' ? 'selected' : '' ?>>Hurghada</option>
                <option value="hel" <?= $location === 'hel' ? 'selected' : '' ?>>Hel</option>
            </select>
            <select name="status">
                <option value="">Wszystkie statusy</option>
                <?php foreach (array_keys($status_labels) as $s): ?>
                    <option value="<?= $s ?>" <?= $status === $s ? 'selected' : '' ?>><?= ucfirst($s) ?></option>
                <?php endforeach; ?>
            </select>
            <input type="submit" class="button" value="Filtruj">
        </form>

        <?php if ($error): ?>
            <div class="notice notice-error"><p>Błąd API: <?= esc_html($error) ?></p></div>
        <?php elseif (empty($bookings)): ?>
            <p>Brak rezerwacji.</p>
        <?php else: ?>
            <table class="wp-list-table widefat fixed striped">
                <thead>
                    <tr>
                        <th>Nr ref.</th>
                        <th>Usługa</th>
                        <th>Klient</th>
                        <th>Lokalizacja</th>
                        <th>Osób</th>
                        <th>Daty</th>
                        <th>Cena</th>
                        <th>Status</th>
                        <th>Płatność</th>
                        <th>Akcje</th>
                    </tr>
                </thead>
                <tbody>
                <?php foreach ($bookings as $b): ?>
                    <tr>
                        <td><strong><?= esc_html($b['booking_ref']) ?></strong></td>
                        <td><?= esc_html($b['service_name']) ?></td>
                        <td>
                            <?= esc_html($b['customer_name']) ?><br>
                            <small><?= esc_html($b['customer_email']) ?></small><br>
                            <?php if ($b['customer_phone']): ?>
                                <small><?= esc_html($b['customer_phone']) ?></small>
                            <?php endif; ?>
                        </td>
                        <td><?= ucfirst(esc_html($b['location'])) ?></td>
                        <td><?= intval($b['persons']) ?></td>
                        <td>
                            <?php if ($b['start_date']): ?>
                                <?= esc_html($b['start_date']) ?> <?= esc_html($b['start_time']) ?>
                            <?php else: ?>
                                <em><?= esc_html($b['preferred_dates'] ?: '—') ?></em>
                            <?php endif; ?>
                        </td>
                        <td><?= number_format($b['total_price'], 0) ?> <?= esc_html($b['currency']) ?></td>
                        <td><?= $status_labels[$b['booking_status']] ?? esc_html($b['booking_status']) ?></td>
                        <td><?= $pay_labels[$b['payment_status']] ?? esc_html($b['payment_status']) ?></td>
                        <td>
                            <a href="<?= admin_url('admin.php?page=flh-booking-detail&ref=' . urlencode($b['booking_ref'])) ?>"
                               class="button button-small">Szczegóły</a>
                        </td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        <?php endif; ?>

        <hr>
        <h2>Ustawienia API</h2>
        <form method="post" action="options.php">
            <?php settings_fields('flh_booking_settings'); ?>
            <table class="form-table">
                <tr>
                    <th>URL API</th>
                    <td><input type="url" name="flh_api_base_url" class="regular-text"
                        value="<?= esc_attr(get_option('flh_api_base_url', 'https://funlikehel-bot.onrender.com')) ?>"></td>
                </tr>
                <tr>
                    <th>Admin Token</th>
                    <td><input type="password" name="flh_booking_admin_token" class="regular-text"
                        value="<?= esc_attr(get_option('flh_booking_admin_token', '')) ?>"></td>
                </tr>
            </table>
            <?php submit_button('Zapisz'); ?>
        </form>
    </div>
    <?php
}

add_action('admin_init', function () {
    register_setting('flh_booking_settings', 'flh_api_base_url');
    register_setting('flh_booking_settings', 'flh_booking_admin_token');
});

// REST endpoint to save plugin settings (used by deploy script)
add_action('rest_api_init', function () {
    register_rest_route('flh/v1', '/setup', [
        'methods'             => 'POST',
        'callback'            => function (WP_REST_Request $req) {
            if (!current_user_can('manage_options')) {
                return new WP_Error('forbidden', 'Forbidden', ['status' => 403]);
            }
            $url   = sanitize_text_field($req->get_param('flh_api_base_url') ?? '');
            $token = sanitize_text_field($req->get_param('flh_booking_admin_token') ?? '');
            if ($url)   update_option('flh_api_base_url', $url);
            if ($token) update_option('flh_booking_admin_token', $token);
            return ['ok' => true, 'url' => get_option('flh_api_base_url'), 'token_set' => !empty(get_option('flh_booking_admin_token'))];
        },
        'permission_callback' => function () { return current_user_can('manage_options'); },
    ]);
});


// ---------------------------------------------------------------------------
// Shortcodes — embed booking forms in pages
// ---------------------------------------------------------------------------

/**
 * [flh_booking_form location="hurghada"]
 * [flh_booking_form location="hel"]
 */
add_shortcode('flh_booking_form', function ($atts) {
    $atts = shortcode_atts(['location' => 'hurghada', 'lang' => 'pl'], $atts);
    $location = sanitize_text_field($atts['location']);
    $lang     = sanitize_text_field($atts['lang']);
    $api_base = get_option('flh_api_base_url', 'https://funlikehel-bot.onrender.com');

    ob_start();
    ?>
    <div class="flh-booking-form-wrap" id="flh-booking-<?= esc_attr($location) ?>">
        <div id="flh-step-1">
            <h3><?= $lang === 'en' ? 'Choose your activity' : 'Wybierz aktywność' ?></h3>
            <div id="flh-services-list" class="flh-services-grid"></div>
        </div>

        <div id="flh-step-2" style="display:none">
            <button onclick="flhGoBack()" class="flh-btn-back">&larr;
                <?= $lang === 'en' ? 'Back' : 'Wróć' ?></button>
            <h3 id="flh-selected-service-name"></h3>
            <p id="flh-selected-service-desc" class="flh-service-desc"></p>
            <div class="flh-service-meta" id="flh-service-meta"></div>
        </div>

        <form id="flh-booking-form" style="display:none">
            <input type="hidden" id="flh-service-slug" name="service_slug">
            <input type="hidden" name="location" value="<?= esc_attr($location) ?>">
            <input type="hidden" name="language" value="<?= esc_attr($lang) ?>">
            <input type="hidden" name="source" value="website">

            <div class="flh-form-group">
                <label><?= $lang === 'en' ? 'Your name *' : 'Twoje imię i nazwisko *' ?></label>
                <input type="text" name="customer_name" required minlength="2" maxlength="200"
                    placeholder="<?= $lang === 'en' ? 'Jan Kowalski' : 'Jan Kowalski' ?>">
            </div>
            <div class="flh-form-group">
                <label><?= $lang === 'en' ? 'Email *' : 'Email *' ?></label>
                <input type="email" name="customer_email" required
                    placeholder="jan@example.com">
            </div>
            <div class="flh-form-group">
                <label><?= $lang === 'en' ? 'Phone' : 'Telefon' ?></label>
                <input type="tel" name="customer_phone"
                    placeholder="+48 690 270 032">
            </div>
            <div class="flh-form-group">
                <label><?= $lang === 'en' ? 'Your level' : 'Twój poziom' ?></label>
                <select name="customer_level">
                    <option value=""><?= $lang === 'en' ? '— select —' : '— wybierz —' ?></option>
                    <option value="beginner"><?= $lang === 'en' ? 'Complete beginner' : 'Początkujący (zero)' ?></option>
                    <option value="basic"><?= $lang === 'en' ? 'Basic (first rides)' : 'Podstawowy (pierwsze jazdy)' ?></option>
                    <option value="intermediate"><?= $lang === 'en' ? 'Intermediate (rides both ways)' : 'Średniozaawansowany (jazda w obie strony)' ?></option>
                    <option value="advanced"><?= $lang === 'en' ? 'Advanced / jumps' : 'Zaawansowany / skoki' ?></option>
                </select>
            </div>
            <div class="flh-form-group">
                <label><?= $lang === 'en' ? 'Number of people *' : 'Liczba osób *' ?></label>
                <input type="number" name="persons" value="1" min="1" max="10" required>
            </div>
            <div class="flh-form-group">
                <label><?= $lang === 'en' ? 'Preferred dates' : 'Preferowane terminy' ?></label>
                <input type="text" name="preferred_dates"
                    placeholder="<?= $lang === 'en' ? 'e.g. 10-15 January or any week in February' : 'np. 10-15 stycznia lub dowolny tydzień w lutym' ?>">
            </div>
            <div class="flh-form-group">
                <label><?= $lang === 'en' ? 'Notes / special requests' : 'Uwagi / specjalne prośby' ?></label>
                <textarea name="special_requests" rows="3"
                    placeholder="<?= $lang === 'en' ? 'Any health issues, specific goals, group composition...' : 'Dolegliwości zdrowotne, cele, skład grupy...' ?>"></textarea>
            </div>

            <div id="flh-form-error" class="flh-error" style="display:none"></div>
            <div id="flh-form-success" class="flh-success" style="display:none"></div>

            <button type="submit" class="flh-btn-submit">
                <?= $lang === 'en' ? '📩 Send booking request' : '📩 Wyślij zgłoszenie' ?>
            </button>

            <p class="flh-policy-note">
                <?= $lang === 'en'
                    ? 'We will confirm within 24 hours. No payment required now.'
                    : 'Potwierdzimy w ciągu 24h. Płatność dopiero po potwierdzeniu.' ?>
            </p>
        </form>

        <div id="flh-booking-confirmed" style="display:none" class="flh-confirmed-box">
            <h3>✅ <?= $lang === 'en' ? 'Booking request sent!' : 'Zgłoszenie wysłane!' ?></h3>
            <p id="flh-confirm-message"></p>
            <p><?= $lang === 'en'
                ? 'Your booking reference: '
                : 'Numer referencyjny: ' ?><strong id="flh-confirm-ref"></strong></p>
            <p><?= $lang === 'en'
                ? 'Questions? Call us: '
                : 'Pytania? Dzwoń: ' ?><strong>690 270 032</strong></p>
        </div>
    </div>

    <style>
        .flh-booking-form-wrap { max-width: 680px; margin: 0 auto; font-family: inherit; }
        .flh-services-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin: 16px 0; }
        .flh-service-card { border: 2px solid #e0e0e0; border-radius: 10px; padding: 16px; cursor: pointer; transition: border-color .2s, box-shadow .2s; background: #fff; }
        .flh-service-card:hover { border-color: #0099cc; box-shadow: 0 2px 12px rgba(0,153,204,.15); }
        .flh-service-card h4 { margin: 0 0 6px; font-size: 15px; color: #1a1a2e; }
        .flh-service-card .price { font-weight: bold; color: #0099cc; font-size: 16px; }
        .flh-service-card .duration { color: #888; font-size: 13px; margin-top: 4px; }
        .flh-service-card .subtitle { color: #555; font-size: 12px; margin-top: 4px; }
        .flh-service-desc { color: #444; line-height: 1.6; }
        .flh-service-meta { background: #f7f9fc; border-radius: 8px; padding: 12px 16px; margin: 12px 0; font-size: 13px; }
        .flh-service-meta p { margin: 4px 0; }
        .flh-form-group { margin-bottom: 14px; }
        .flh-form-group label { display: block; font-weight: 600; margin-bottom: 4px; font-size: 14px; }
        .flh-form-group input, .flh-form-group select, .flh-form-group textarea { width: 100%; padding: 8px 12px; border: 1px solid #d0d0d0; border-radius: 6px; font-size: 15px; box-sizing: border-box; }
        .flh-btn-submit { background: #0099cc; color: #fff; border: none; padding: 14px 28px; border-radius: 8px; font-size: 16px; cursor: pointer; width: 100%; margin-top: 8px; }
        .flh-btn-submit:hover { background: #007aaa; }
        .flh-btn-back { background: none; border: none; color: #0099cc; cursor: pointer; font-size: 14px; padding: 0; margin-bottom: 12px; }
        .flh-error { background: #fce4e4; color: #c0392b; padding: 10px 14px; border-radius: 6px; margin: 10px 0; }
        .flh-success { background: #d4edda; color: #155724; padding: 10px 14px; border-radius: 6px; }
        .flh-confirmed-box { background: #eafaf1; border-left: 4px solid #27ae60; padding: 24px; border-radius: 8px; }
        .flh-policy-note { color: #888; font-size: 12px; text-align: center; margin-top: 8px; }
    </style>

    <script>
    (function() {
        var API_BASE = '<?= esc_js($api_base) ?>';
        var LOCATION = '<?= esc_js($location) ?>';
        var selectedService = null;
        var form = document.getElementById('flh-booking-form');

        // Load services
        fetch(API_BASE + '/api/services?location=' + LOCATION)
            .then(function(r){ return r.json(); })
            .then(function(data){
                var container = document.getElementById('flh-services-list');
                if (!data.services || !data.services.length) {
                    container.innerHTML = '<p>Brak dostępnych usług.</p>';
                    return;
                }
                data.services.forEach(function(svc){
                    var card = document.createElement('div');
                    card.className = 'flh-service-card';
                    var priceLabel = svc.base_price > 0
                        ? 'od ' + svc.base_price + ' ' + svc.currency
                        : 'Wycena indywidualna';
                    var durationLabel = svc.duration_hours > 0
                        ? svc.duration_hours + 'h'
                        : '';
                    card.innerHTML = '<h4>' + svc.name_pl + '</h4>' +
                        '<div class="subtitle">' + svc.subtitle_pl + '</div>' +
                        '<div class="price">' + priceLabel + '</div>' +
                        (durationLabel ? '<div class="duration">' + durationLabel + '</div>' : '');
                    card.onclick = function(){ flhSelectService(svc); };
                    container.appendChild(card);
                });
            })
            .catch(function(){ document.getElementById('flh-services-list').innerHTML = '<p>Błąd ładowania usług.</p>'; });

        window.flhSelectService = function(svc) {
            selectedService = svc;
            document.getElementById('flh-selected-service-name').textContent = svc.name_pl;
            document.getElementById('flh-selected-service-desc').textContent = svc.description_pl;

            var meta = '';
            if (svc.duration_hours > 0) meta += '<p>⏱ Czas trwania: <strong>' + svc.duration_hours + 'h</strong></p>';
            meta += '<p>👥 Liczba osób: <strong>' + svc.min_persons + (svc.max_persons > svc.min_persons ? '–' + svc.max_persons : '') + '</strong></p>';
            if (svc.included_pl) meta += '<p>✅ W cenie: ' + svc.included_pl + '</p>';
            if (svc.requirements_pl) meta += '<p>📋 Wymagania: ' + svc.requirements_pl + '</p>';
            if (svc.weather_note_pl) meta += '<p>🌬 Warunki: ' + svc.weather_note_pl + '</p>';
            document.getElementById('flh-service-meta').innerHTML = meta;

            document.getElementById('flh-step-1').style.display = 'none';
            document.getElementById('flh-step-2').style.display = '';
            document.getElementById('flh-service-slug').value = svc.slug;
            document.getElementById('flh-booking-form').style.display = '';
        };

        window.flhGoBack = function() {
            document.getElementById('flh-step-1').style.display = '';
            document.getElementById('flh-step-2').style.display = 'none';
            document.getElementById('flh-booking-form').style.display = 'none';
            selectedService = null;
        };

        form.addEventListener('submit', function(e){
            e.preventDefault();
            var errDiv = document.getElementById('flh-form-error');
            errDiv.style.display = 'none';

            var data = {};
            new FormData(form).forEach(function(v,k){ data[k] = v; });
            data.persons = parseInt(data.persons) || 1;

            var btn = form.querySelector('.flh-btn-submit');
            btn.disabled = true;
            btn.textContent = '⏳ Wysyłanie...';

            fetch(API_BASE + '/api/bookings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(function(r){
                if (!r.ok) return r.json().then(function(e){ throw e; });
                return r.json();
            })
            .then(function(res){
                form.style.display = 'none';
                document.getElementById('flh-step-2').style.display = 'none';
                var box = document.getElementById('flh-booking-confirmed');
                box.style.display = '';
                document.getElementById('flh-confirm-ref').textContent = res.booking_ref;
                document.getElementById('flh-confirm-message').textContent = res.message || '';
            })
            .catch(function(err){
                btn.disabled = false;
                btn.textContent = '📩 Wyślij zgłoszenie';
                errDiv.textContent = err.detail || 'Wystąpił błąd. Spróbuj ponownie lub zadzwoń: 690 270 032';
                errDiv.style.display = '';
            });
        });
    })();
    </script>
    <?php
    return ob_get_clean();
});
