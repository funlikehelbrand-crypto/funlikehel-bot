<?php
/**
 * Plugin Name: FUN like HEL — Google Ads Tracking
 * Description: Dodaje tag sledzenia Google Ads (gtag.js) + sledzenie konwersji (klikniecie w telefon).
 * Version: 1.0
 * Author: FUN like HEL
 */

if (!defined('ABSPATH')) exit;

/**
 * 1. Wstrzyknij gtag.js do <head> na KAZDEJ stronie
 *    Google Ads ID: AW-8974478964
 */
add_action('wp_head', 'flh_gtag_head', 1);
function flh_gtag_head() {
    ?>
<!-- Google Ads gtag.js — FUN like HEL -->
<script async src="https://www.googletagmanager.com/gtag/js?id=AW-8974478964"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'AW-8974478964');
</script>
    <?php
}

/**
 * 2. Sledzenie klikniecia w link tel:690270032
 *    Konwersja "Klikniecie w telefon 690270032"
 *    Ladowane na stronie kontaktu/rezerwacji (page ID 2042)
 *    oraz na KAZDEJ stronie (numer moze byc w stopce/menu)
 */
add_action('wp_footer', 'flh_phone_click_tracking');
function flh_phone_click_tracking() {
    ?>
<!-- Google Ads: sledzenie klikniecia w telefon 690270032 -->
<script>
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('a[href*="tel:690270032"], a[href*="tel:+48690270032"], a[href*="tel:%2B48690270032"]').forEach(function(el) {
    el.addEventListener('click', function() {
      if (typeof gtag === 'function') {
        gtag('event', 'conversion', {
          'send_to': 'AW-8974478964/phone_click',
          'event_callback': function() {}
        });
      }
    });
  });
});
</script>
    <?php
}

/**
 * 3. Sledzenie konwersji "Rezerwacja terminu" na stronie page_id=2042
 *    Odpalane po uzyciu formularza (submit) — generic listener
 */
add_action('wp_footer', 'flh_reservation_tracking');
function flh_reservation_tracking() {
    if (!is_page(2042)) return;
    ?>
<!-- Google Ads: sledzenie konwersji rezerwacji na stronie kontaktu -->
<script>
document.addEventListener('DOMContentLoaded', function() {
  // Sluchaj submitow formularzy na stronie rezerwacji
  document.querySelectorAll('form').forEach(function(form) {
    form.addEventListener('submit', function() {
      if (typeof gtag === 'function') {
        gtag('event', 'conversion', {
          'send_to': 'AW-8974478964/7469585421',
          'event_callback': function() {}
        });
      }
    });
  });
});
</script>
    <?php
}

/**
 * 4. Sledzenie konwersji "Rezerwacja Hurghada" na stronie egipt-hurghada (page ID 2044)
 */
add_action('wp_footer', 'flh_hurghada_tracking');
function flh_hurghada_tracking() {
    if (!is_page(2044)) return;
    ?>
<!-- Google Ads: sledzenie konwersji rezerwacji Hurghada -->
<script>
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('form').forEach(function(form) {
    form.addEventListener('submit', function() {
      if (typeof gtag === 'function') {
        gtag('event', 'conversion', {
          'send_to': 'AW-8974478964/hurghada_rezerwacja',
          'event_callback': function() {}
        });
      }
    });
  });
});
</script>
    <?php
}
