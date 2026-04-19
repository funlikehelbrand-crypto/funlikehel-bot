<?php
/**
 * Plugin Name: FUN like HEL — Ekipa API
 * Description: Endpoint REST API do zapisu klientow z formularza /ekipa/. Zapisuje do bazy MySQL i wysyla email.
 * Version: 1.0
 * Author: FUN like HEL
 */

if (!defined('ABSPATH')) exit;

// --- Tworzenie tabeli przy aktywacji pluginu ---
register_activation_hook(__FILE__, 'flh_ekipa_create_table');

function flh_ekipa_create_table() {
    global $wpdb;
    $table = $wpdb->prefix . 'ekipa';
    $charset = $wpdb->get_charset_collate();

    $sql = "CREATE TABLE IF NOT EXISTS $table (
        id bigint(20) NOT NULL AUTO_INCREMENT,
        name varchar(200) NOT NULL,
        email varchar(200) NOT NULL,
        phone varchar(50) DEFAULT '',
        sport varchar(100) DEFAULT '',
        locations varchar(200) DEFAULT '',
        created_at datetime DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id)
    ) $charset;";

    require_once ABSPATH . 'wp-admin/includes/upgrade.php';
    dbDelta($sql);
}

// --- Rejestracja endpointu REST API ---
add_action('rest_api_init', function () {
    register_rest_route('funlikehel/v1', '/ekipa', [
        'methods'  => 'POST',
        'callback' => 'flh_ekipa_signup',
        'permission_callback' => '__return_true', // publiczny endpoint
    ]);

    register_rest_route('funlikehel/v1', '/ekipa', [
        'methods'  => 'GET',
        'callback' => 'flh_ekipa_list',
        'permission_callback' => function () {
            return current_user_can('manage_options');
        },
    ]);
});

// --- Zapis klienta ---
function flh_ekipa_signup(WP_REST_Request $request) {
    global $wpdb;
    $table = $wpdb->prefix . 'ekipa';

    $name      = sanitize_text_field($request->get_param('name') ?: '');
    $email     = sanitize_email($request->get_param('email') ?: '');
    $phone     = sanitize_text_field($request->get_param('phone') ?: '');
    $sport     = sanitize_text_field($request->get_param('sport') ?: '');
    $locations = $request->get_param('locations');

    if (is_array($locations)) {
        $locations = implode(',', array_map('sanitize_text_field', $locations));
    } else {
        $locations = sanitize_text_field($locations ?: '');
    }

    // Walidacja
    if (empty($name) || empty($email)) {
        return new WP_REST_Response([
            'status' => 'error',
            'message' => 'Imie i email sa wymagane.',
        ], 400);
    }

    // Zapis do bazy
    $wpdb->insert($table, [
        'name'       => $name,
        'email'      => $email,
        'phone'      => $phone,
        'sport'      => $sport,
        'locations'  => $locations,
        'created_at' => current_time('mysql'),
    ]);

    // Email powiadomienie
    $subject = "Nowy zapis do ekipy: $name";
    $body  = "Nowy klient zapisal sie do ekipy FUN like HEL!\n\n";
    $body .= "Imie: $name\n";
    $body .= "Email: $email\n";
    $body .= "Telefon: $phone\n";
    $body .= "Sport: $sport\n";
    $body .= "Lokalizacja: $locations\n";
    $body .= "Data: " . current_time('Y-m-d H:i:s') . "\n";

    wp_mail('funlikehelbrand@gmail.com', $subject, $body);

    return new WP_REST_Response([
        'status'  => 'ok',
        'message' => "Czesc $name! Jestes w ekipie!",
    ], 200);
}

// --- Lista zapisanych (tylko admin) ---
function flh_ekipa_list(WP_REST_Request $request) {
    global $wpdb;
    $table = $wpdb->prefix . 'ekipa';

    $results = $wpdb->get_results("SELECT * FROM $table ORDER BY created_at DESC LIMIT 100");

    return new WP_REST_Response([
        'count' => count($results),
        'items' => $results,
    ], 200);
}
