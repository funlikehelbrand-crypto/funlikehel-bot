<?php
/**
 * Plugin Name: FUN like HEL — Rezerwacja Hurghada
 * Description: Endpoint REST API do rezerwacji kursow kitesurfingu w Hurghadzie. Zapisuje do bazy MySQL i wysyla email.
 * Version: 1.0
 * Author: FUN like HEL
 */

if (!defined('ABSPATH')) exit;

// --- Tworzenie tabeli przy aktywacji pluginu ---
register_activation_hook(__FILE__, 'flh_rezerwacja_create_table');

function flh_rezerwacja_create_table() {
    global $wpdb;
    $table = $wpdb->prefix . 'rezerwacja_hurghada';
    $charset = $wpdb->get_charset_collate();

    $sql = "CREATE TABLE IF NOT EXISTS $table (
        id bigint(20) NOT NULL AUTO_INCREMENT,
        name varchar(200) NOT NULL,
        email varchar(200) NOT NULL,
        phone varchar(50) DEFAULT '',
        package varchar(100) DEFAULT '',
        dates varchar(200) DEFAULT '',
        level varchar(100) DEFAULT '',
        persons int DEFAULT 1,
        message text DEFAULT '',
        created_at datetime DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id)
    ) $charset;";

    require_once ABSPATH . 'wp-admin/includes/upgrade.php';
    dbDelta($sql);
}

// --- Rejestracja endpointow REST API ---
add_action('rest_api_init', function () {
    register_rest_route('funlikehel/v1', '/rezerwacja', [
        'methods'  => 'POST',
        'callback' => 'flh_rezerwacja_submit',
        'permission_callback' => '__return_true',
    ]);

    register_rest_route('funlikehel/v1', '/rezerwacja', [
        'methods'  => 'GET',
        'callback' => 'flh_rezerwacja_list',
        'permission_callback' => function () {
            return current_user_can('manage_options');
        },
    ]);
});

// --- Zapis rezerwacji ---
function flh_rezerwacja_submit(WP_REST_Request $request) {
    global $wpdb;
    $table = $wpdb->prefix . 'rezerwacja_hurghada';

    $name    = sanitize_text_field($request->get_param('name') ?: '');
    $email   = sanitize_email($request->get_param('email') ?: '');
    $phone   = sanitize_text_field($request->get_param('phone') ?: '');
    $package = sanitize_text_field($request->get_param('package') ?: '');
    $dates   = sanitize_text_field($request->get_param('dates') ?: '');
    $level   = sanitize_text_field($request->get_param('level') ?: '');
    $persons = intval($request->get_param('persons') ?: 1);
    $message = sanitize_textarea_field($request->get_param('message') ?: '');

    if ($persons < 1) $persons = 1;
    if ($persons > 20) $persons = 20;

    // Walidacja
    if (empty($name) || empty($email) || empty($phone)) {
        return new WP_REST_Response([
            'status' => 'error',
            'message' => 'Imie, email i telefon sa wymagane.',
        ], 400);
    }

    // Zapis do bazy
    $wpdb->insert($table, [
        'name'       => $name,
        'email'      => $email,
        'phone'      => $phone,
        'package'    => $package,
        'dates'      => $dates,
        'level'      => $level,
        'persons'    => $persons,
        'message'    => $message,
        'created_at' => current_time('mysql'),
    ]);

    // Nazwy pakietow
    $pkg_names = [
        'zolty'       => 'Wariant Zolty (2300 zl)',
        'srebrny'     => 'Wariant Srebrny (3300 zl)',
        'bez_8h'      => 'Bez noclegu — 8h (1910 zl)',
        'bez_12h'     => 'Bez noclegu — 12h (2640 zl)',
    ];
    $pkg_label = isset($pkg_names[$package]) ? $pkg_names[$package] : $package;

    $level_names = [
        'poczatkujacy' => 'Poczatkujacy (nigdy nie probowalem)',
        'podstawowy'   => 'Podstawowy (mialem kilka lekcji)',
        'sredni'       => 'Sredniozaawansowany (jezdzze samodzielnie)',
        'zaawansowany' => 'Zaawansowany (chce sie rozwijac)',
    ];
    $level_label = isset($level_names[$level]) ? $level_names[$level] : $level;

    // Email powiadomienie
    $subject = "NOWA REZERWACJA Hurghada: $name — $pkg_label";
    $body  = "Nowa rezerwacja kursu kite w Hurghadzie!\n\n";
    $body .= "Imie: $name\n";
    $body .= "Email: $email\n";
    $body .= "Telefon: $phone\n";
    $body .= "Pakiet: $pkg_label\n";
    $body .= "Preferowany termin: $dates\n";
    $body .= "Poziom: $level_label\n";
    $body .= "Liczba osob: $persons\n";
    if (!empty($message)) {
        $body .= "Wiadomosc: $message\n";
    }
    $body .= "\nData zgloszenia: " . current_time('Y-m-d H:i:s') . "\n";
    $body .= "\n---\nOdpowiedz klientowi jak najszybciej!\n";

    wp_mail('funlikehelbrand@gmail.com', $subject, $body);

    return new WP_REST_Response([
        'status'  => 'ok',
        'message' => "Dziekujemy $name! Rezerwacja przyjeta. Odezwiemy sie w ciagu 24h!",
    ], 200);
}

// --- Lista rezerwacji (tylko admin) ---
function flh_rezerwacja_list(WP_REST_Request $request) {
    global $wpdb;
    $table = $wpdb->prefix . 'rezerwacja_hurghada';

    $results = $wpdb->get_results("SELECT * FROM $table ORDER BY created_at DESC LIMIT 100");

    return new WP_REST_Response([
        'count' => count($results),
        'items' => $results,
    ], 200);
}
