"""
notifier.py — wysyłka alertów mailowych przez SMTP
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
log = logging.getLogger(__name__)

# ── Konfiguracja SMTP z .env ─────────────────────────────────────────────────

SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASS: str = os.getenv("SMTP_PASS", "")
MAIL_FROM: str = os.getenv("MAIL_FROM", SMTP_USER)
MAIL_TO: str = os.getenv("MAIL_TO", "")

# ── Szablony maili ───────────────────────────────────────────────────────────

ALERT_LABELS = {
    "SUPER_LOT": "SUPER LOT",
    "GOOD_DEAL": "GOOD DEAL",
    "PRICE_DROP": "PRICE DROP",
}

ALERT_EMOJI = {
    "SUPER_LOT": "🔥",
    "GOOD_DEAL": "✈️",
    "PRICE_DROP": "📉",
}

ALERT_REASONS = {
    "SUPER_LOT": "cena poniżej progu {threshold} PLN",
    "GOOD_DEAL": "cena poniżej progu {threshold} PLN",
    "PRICE_DROP": "cena spadła o {drop_pct:.0f}% względem ostatniej zapisanej ceny ({prev_price:.0f} PLN)",
}


def _format_date(iso_date: Optional[str]) -> str:
    if not iso_date:
        return "brak daty"
    try:
        dt = datetime.strptime(iso_date, "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y")
    except ValueError:
        return iso_date


def build_subject(offer: dict, alert_type: str) -> str:
    label = ALERT_LABELS.get(alert_type, alert_type)
    emoji = ALERT_EMOJI.get(alert_type, "")
    origin = offer.get("origin") or offer.get("origin_iata") or "?"
    dest = offer.get("destination") or offer.get("dest_iata") or "?"
    price = int(offer["price"])
    return f"{emoji} {label}: {origin} → {dest} za {price} PLN"


def build_body_plain(offer: dict, alert_type: str, reason: str) -> str:
    label = ALERT_LABELS.get(alert_type, alert_type)
    origin = offer.get("origin") or offer.get("origin_iata") or "?"
    dest = offer.get("destination") or offer.get("dest_iata") or "?"
    dep = _format_date(offer.get("dep_date"))
    ret_ = _format_date(offer.get("ret_date")) if offer.get("ret_date") else "tylko lot w jedną stronę"
    price = int(offer["price"])
    airline = offer.get("airline") or "brak danych"
    url = offer.get("url") or "#"

    return (
        f"Znaleziono tani lot czarterowy.\n"
        f"\n"
        f"Trasa:        {origin} → {dest}\n"
        f"Data wylotu:  {dep}\n"
        f"Powrót:       {ret_}\n"
        f"Cena:         {price} PLN\n"
        f"Linia:        {airline}\n"
        f"Typ alertu:   {label}\n"
        f"Powód:        {reason}\n"
        f"Link:         {url}\n"
        f"\n"
        f"---\n"
        f"Charter Monitor | chartershop.pl\n"
        f"Wygenerowano: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
    )


def build_body_html(offer: dict, alert_type: str, reason: str) -> str:
    label = ALERT_LABELS.get(alert_type, alert_type)
    emoji = ALERT_EMOJI.get(alert_type, "")
    origin = offer.get("origin") or offer.get("origin_iata") or "?"
    dest = offer.get("destination") or offer.get("dest_iata") or "?"
    dep = _format_date(offer.get("dep_date"))
    ret_ = _format_date(offer.get("ret_date")) if offer.get("ret_date") else "tylko lot w jedną stronę"
    price = int(offer["price"])
    airline = offer.get("airline") or "brak danych"
    url = offer.get("url") or "#"

    color_map = {
        "SUPER_LOT": "#e53e3e",
        "GOOD_DEAL": "#3182ce",
        "PRICE_DROP": "#805ad5",
    }
    badge_color = color_map.get(alert_type, "#718096")

    return f"""<!DOCTYPE html>
<html lang="pl">
<head><meta charset="UTF-8"><title>Charter Alert</title></head>
<body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f7f7f7;">
  <div style="background:white;border-radius:8px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,.08);">

    <div style="background:{badge_color};color:white;padding:10px 16px;border-radius:6px;
                display:inline-block;font-weight:bold;font-size:18px;margin-bottom:20px;">
      {emoji} {label}
    </div>

    <h2 style="margin:0 0 4px;color:#1a202c;">{origin} → {dest}</h2>
    <p style="font-size:32px;font-weight:bold;color:{badge_color};margin:8px 0 20px;">
      {price} PLN
    </p>

    <table style="width:100%;border-collapse:collapse;">
      <tr>
        <td style="padding:6px 0;color:#718096;width:130px;">Data wylotu</td>
        <td style="padding:6px 0;font-weight:bold;">{dep}</td>
      </tr>
      <tr>
        <td style="padding:6px 0;color:#718096;">Powrót</td>
        <td style="padding:6px 0;">{ret_}</td>
      </tr>
      <tr>
        <td style="padding:6px 0;color:#718096;">Linia lotnicza</td>
        <td style="padding:6px 0;">{airline}</td>
      </tr>
      <tr>
        <td style="padding:6px 0;color:#718096;">Powód alertu</td>
        <td style="padding:6px 0;">{reason}</td>
      </tr>
    </table>

    <a href="{url}"
       style="display:block;margin-top:24px;background:{badge_color};color:white;
              text-align:center;padding:12px;border-radius:6px;text-decoration:none;
              font-weight:bold;font-size:16px;">
      Zobacz ofertę na chartershop.pl →
    </a>

    <p style="margin-top:20px;font-size:11px;color:#a0aec0;text-align:center;">
      Charter Monitor | {datetime.now().strftime('%d.%m.%Y %H:%M')}
    </p>
  </div>
</body>
</html>"""


def send_alert(
    offer: dict,
    alert_type: str,
    threshold: Optional[float] = None,
    prev_price: Optional[float] = None,
    drop_pct: Optional[float] = None,
) -> bool:
    """
    Wysyła maila z alertem cenowym.
    Zwraca True jeśli sukces, False jeśli błąd.
    """
    reason_tpl = ALERT_REASONS.get(alert_type, alert_type)
    reason = reason_tpl.format(
        threshold=int(threshold or 0),
        prev_price=prev_price or 0,
        drop_pct=drop_pct or 0,
    )
    subject = build_subject(offer, alert_type)
    body_plain = build_body_plain(offer, alert_type, reason)
    body_html = build_body_html(offer, alert_type, reason)
    return _smtp_send(subject, body_plain, body_html)


def _smtp_send(subject: str, body_plain: str, body_html: str) -> bool:
    """Wspólna funkcja wysyłki przez SMTP."""
    if not SMTP_USER or not SMTP_PASS or not MAIL_TO:
        log.error("Brak konfiguracji SMTP w .env (SMTP_USER, SMTP_PASS, MAIL_TO wymagane)")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM or SMTP_USER
    msg["To"] = MAIL_TO
    msg.attach(MIMEText(body_plain, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        log.info("Wysyłanie '%s' na %s ...", subject, MAIL_TO)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, MAIL_TO, msg.as_string())
        log.info("Mail wysłany pomyślnie.")
        return True
    except smtplib.SMTPAuthenticationError:
        log.error(
            "Błąd autoryzacji SMTP — sprawdź SMTP_USER i SMTP_PASS w .env. "
            "Dla Gmaila użyj hasła aplikacji (App Password)."
        )
    except smtplib.SMTPException as exc:
        log.error("Błąd SMTP: %s", exc)
    except OSError as exc:
        log.error("Błąd połączenia z serwerem SMTP: %s", exc)
    return False


def send_report(offers: list[dict]) -> bool:
    """
    Wysyła raport z wszystkimi znalezionymi ofertami — niezależnie od progów cenowych.
    Używany w trybie --report.
    """
    today = datetime.now().strftime("%d.%m.%Y")
    count = len(offers)
    subject = f"Charter Monitor — raport {today} ({count} ofert Egipt/Hurghada)"

    if not offers:
        log.info("Brak ofert — mail nie wysłany.")
        return False

    # Sortuj: najpierw najtańsze
    offers_sorted = sorted(offers, key=lambda o: o["price"])

    # Plain text
    lines = [
        f"Znaleziono {count} ofertę/oferty lotów do Egiptu/Hurghady.\n",
        f"Źródło: https://chartershop.pl\n",
        "─" * 50,
    ]
    for o in offers_sorted:
        label = _price_label(o["price"])
        origin = o.get("origin") or o.get("origin_iata") or "?"
        dest = o.get("destination") or o.get("dest_iata") or "?"
        dep = _format_date(o.get("dep_date"))
        price = int(o["price"])
        airline = o.get("airline") or "?"
        url = o.get("url") or "#"
        lines.append(
            f"\n{label} {origin} → {dest}\n"
            f"  Data:    {dep}\n"
            f"  Cena:    {price} PLN\n"
            f"  Linia:   {airline}\n"
            f"  Link:    {url}\n"
        )
    lines.append(f"\n---\nCharter Monitor | {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
    body_plain = "\n".join(lines)

    # HTML
    rows_html = ""
    for o in offers_sorted:
        label = _price_label(o["price"])
        badge_color = _price_color(o["price"])
        origin = o.get("origin") or o.get("origin_iata") or "?"
        dest = o.get("destination") or o.get("dest_iata") or "?"
        dep = _format_date(o.get("dep_date"))
        price = int(o["price"])
        airline = o.get("airline") or "?"
        url = o.get("url") or "#"
        rows_html += f"""
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;">
            <span style="background:{badge_color};color:white;padding:2px 7px;
                         border-radius:4px;font-size:11px;font-weight:bold;">
              {label}
            </span>
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;font-weight:bold;">
            {origin} → {dest}
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;">{dep}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;color:{badge_color};
                     font-weight:bold;font-size:16px;">{price} PLN</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;">{airline}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;">
            <a href="{url}" style="color:#3182ce;text-decoration:none;">Zamów →</a>
          </td>
        </tr>"""

    body_html = f"""<!DOCTYPE html>
<html lang="pl">
<head><meta charset="UTF-8"><title>Charter Monitor</title></head>
<body style="font-family:Arial,sans-serif;max-width:750px;margin:0 auto;padding:20px;background:#f7f7f7;">
  <div style="background:white;border-radius:8px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,.08);">

    <h2 style="margin:0 0 4px;color:#1a202c;">Charter Monitor</h2>
    <p style="color:#718096;margin:0 0 20px;">
      Loty Warszawa/Katowice → Hurghada/Egipt · najbliższe 2 tygodnie · {today}
    </p>

    <table style="width:100%;border-collapse:collapse;">
      <thead>
        <tr style="background:#f7fafc;">
          <th style="padding:8px;text-align:left;font-size:12px;color:#718096;border-bottom:2px solid #e2e8f0;"></th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#718096;border-bottom:2px solid #e2e8f0;">Trasa</th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#718096;border-bottom:2px solid #e2e8f0;">Data</th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#718096;border-bottom:2px solid #e2e8f0;">Cena</th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#718096;border-bottom:2px solid #e2e8f0;">Linia</th>
          <th style="padding:8px;text-align:left;font-size:12px;color:#718096;border-bottom:2px solid #e2e8f0;">Link</th>
        </tr>
      </thead>
      <tbody>{rows_html}
      </tbody>
    </table>

    <p style="margin-top:20px;font-size:11px;color:#a0aec0;text-align:center;">
      Charter Monitor | {datetime.now().strftime('%d.%m.%Y %H:%M')} |
      <a href="https://chartershop.pl" style="color:#a0aec0;">chartershop.pl</a>
    </p>
  </div>
</body>
</html>"""

    return _smtp_send(subject, body_plain, body_html)


def _price_label(price: float) -> str:
    if price <= 600:
        return "SUPER LOT"
    if price <= 800:
        return "GOOD DEAL"
    return "LOT"


def _price_color(price: float) -> str:
    if price <= 600:
        return "#e53e3e"
    if price <= 800:
        return "#3182ce"
    return "#718096"


def send_test_email() -> bool:
    """Wysyła testowego maila do weryfikacji konfiguracji SMTP."""
    dummy_offer = {
        "route_key": "KTW→HRG|2026-05-12",
        "origin": "Katowice",
        "origin_iata": "KTW",
        "destination": "Hurghada",
        "dest_iata": "HRG",
        "dep_date": "2026-05-12",
        "ret_date": None,
        "price": 499.0,
        "airline": "W6 1234",
        "url": "https://chartershop.pl/booking.html?id=TEST",
    }
    log.info("Wysyłanie testowego maila...")
    return send_alert(
        offer=dummy_offer,
        alert_type="SUPER_LOT",
        threshold=600,
    )
