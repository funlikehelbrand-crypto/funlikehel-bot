import os
"""SurfIQ Push Update — POLSKA wersja po polsku
Wysyła do polskich szkół z push_may25 z polskim tematem i treścią.
Tempo: 1 mail / 2 min (bezpieczne dla home.pl)
"""
import csv, smtplib, time, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime

SMTP_HOST = "serwer2620595.home.pl"
SMTP_PORT = 587
SMTP_USER = "office@surfiq.eu"
SMTP_PASS = os.environ.get("SURFIQ_SMTP_PASS", "surfiq2026@")
LOG_FILE = "email_send_log.csv"
CAMPAIGN = "push_may25_pl"
DELAY = 120  # 2 min

SCREENSHOT = os.path.expanduser("~/Downloads/surfiq_push_email.jpg")
MOCKUP = os.path.expanduser("~/Downloads/surfiq_phone_mockup_badge.png")

SUBJECT = "SurfIQ: Twoi kursanci dostają push notyfikacje na telefon"


def build_html(email, rid):
    return f'''<html><body style="font-family:'Segoe UI',Calibri,Arial,sans-serif;font-size:14px;color:#333;line-height:1.7;max-width:640px;margin:0 auto;padding:20px;">

<p>Cześć,</p>

<p>Właśnie wdrożyliśmy funkcję, o którą pytały szkoły &mdash; <strong>push notyfikacje prosto na telefon kursanta</strong>.</p>

<p style="margin:20px 0;padding:16px 20px;background:#f0fafa;border-left:4px solid #14D1C9;border-radius:4px;">
<strong>Co widzi kursant na swoim telefonie:</strong><br>
&bull; <strong>Przypomnienie o lekcji</strong> &mdash; "Jutro o 10:00 lekcja kite z Magdą"<br>
&bull; <strong>Alert wiatrowy</strong> &mdash; "22 węzły SW cały dzień &mdash; zarezerwuj sesję!"<br>
&bull; <strong>Potwierdzenie płatności</strong> &mdash; natychmiastowy paragon<br>
&bull; <strong>Nowe usługi</strong> &mdash; ogłoś obozy, eFoil, lekcje grupowe<br>
&bull; <strong>Dowolna wiadomość</strong> &mdash; wyślij cokolwiek do wszystkich lub wybranych grup
</p>

<p style="text-align:center;margin:24px 0;">
  <img src="cid:push_screenshot" alt="SurfIQ Push na telefonie" width="300" style="display:block;margin:0 auto;border-radius:16px;border:1px solid #e0e0e0;">
  <br>
  <span style="font-size:11px;color:#999;">Prawdziwe push notyfikacje z SurfIQ &mdash; z nazwą i logo Twojej szkoły</span>
</p>

<p><strong>Zero kosztów, zero konfiguracji dla kursantów.</strong> Instalują aplikację, logują się &mdash; i zaczynają dostawać powiadomienia. Bez grup WhatsApp, bez kosztów SMS, bez maili lądujących w spamie.</p>

<p>Aplikacja daje kursantom dostęp do:</p>
<ul style="margin:10px 0;padding-left:20px;">
  <li>Harmonogramu ich lekcji</li>
  <li>Prognozy pogody na żywo na Twoim spocie</li>
  <li>Bezpośredniego kontaktu ze szkołą</li>
</ul>

<p>Całość działa na SurfIQ &mdash; tym samym systemie, który zarządza rezerwacjami, instruktorami i finansami. Jeden panel, zero komplikacji.</p>

<p>Chcesz zobaczyć na żywo? Chętnie pokażę w 15 minut:</p>

<p style="text-align:center;margin:25px 0;">
  <a href="https://surfiq.eu/demo/?utm_source=email&utm_medium=update&utm_campaign={CAMPAIGN}&utm_content={rid}" style="background:linear-gradient(135deg,#0D47A1,#14D1C9);color:#fff;padding:14px 40px;border-radius:30px;font-size:15px;font-weight:700;text-decoration:none;display:inline-block;">Umów szybkie demo &rarr;</a>
</p>

<p style="text-align:center;margin:15px 0;">
  <a href="https://surfiq.eu/?utm_source=email&utm_medium=update&utm_campaign={CAMPAIGN}&utm_content={rid}#pricing" style="color:#14D1C9;font-size:13px;text-decoration:underline;">Zobacz cennik i moduły &rarr;</a>
</p>

<p>Pozdrawiam,</p>
<br>

<table cellpadding="0" cellspacing="0" border="0" style="font-family:'Segoe UI',Calibri,Arial,sans-serif;max-width:500px;">
  <tr>
    <td style="padding-bottom:10px;">
      <a href="https://surfiq.eu?utm_source=email&utm_medium=update&utm_campaign={CAMPAIGN}" style="text-decoration:none;">
        <img src="https://surfiq.eu/assets/email_banner.png" alt="SurfIQ" width="500" style="display:block;border-radius:8px;">
      </a>
    </td>
  </tr>
  <tr><td>
    <table cellpadding="0" cellspacing="0" border="0" width="100%">
      <tr>
        <td style="border-right:3px solid #14D1C9;padding-right:14px;vertical-align:top;width:180px;">
          <div style="font-size:15px;font-weight:700;color:#081D3A;">Magda Abramczyk</div>
          <div style="font-size:10px;color:#14D1C9;font-weight:600;letter-spacing:0.5px;margin-top:2px;">OPERATIONS MANAGER</div>
          <div style="font-size:10px;color:#888;margin-top:2px;">LM GreenWaves sp. z o.o.</div>
        </td>
        <td style="padding-left:14px;vertical-align:top;font-size:12px;color:#555;">
          <div><span style="color:#14D1C9;font-weight:700;">T</span>&nbsp;
            <a href="tel:+48517272742" style="color:#333;text-decoration:none;">+48 517 272 742</a></div>
          <div><span style="color:#14D1C9;font-weight:700;">E</span>&nbsp;
            <a href="mailto:office@surfiq.eu" style="color:#333;text-decoration:none;">office@surfiq.eu</a></div>
          <div><span style="color:#14D1C9;font-weight:700;">W</span>&nbsp;
            <a href="https://surfiq.eu?utm_source=email&utm_medium=update&utm_campaign={CAMPAIGN}" style="color:#14D1C9;text-decoration:none;font-weight:600;">surfiq.eu</a></div>
        </td>
      </tr>
    </table>
  </td></tr>
</table>

<p style="font-size:11px;color:#999;margin-top:30px;border-top:1px solid #eee;padding-top:12px;">
LM GreenWaves sp. z o.o. &bull; ul. Pawińskiego 29/28, 02-106 Warszawa<br>
<a href="https://surfiq.eu/unsubscribe?e={email}" style="color:#999;text-decoration:underline;">Wypisz się</a>
</p>

<img src="https://surfiq.eu/api/px?e={email}&c={CAMPAIGN}" width="1" height="1" style="display:none;">

</body></html>'''


def load_polish_recipients():
    """Load Polish school emails from all CSV files."""
    files = [
        'SurfIQ_Schools_All_Countries.csv',
        'SurfIQ_DeepSearch_2026_05_20.csv',
        'SurfIQ_DeepSearch_2026_05_21.csv',
        'surfiq_prospects_egypt_poland.csv',
        'SurfIQ_DB_New_2026_05_22.csv',
        'SurfIQ_DeepSearch_2026_05_22.csv',
    ]
    poland = {'poland', 'polska', 'pl'}
    seen = set()
    recipients = []
    for fname in files:
        path = os.path.join(os.path.dirname(__file__) or '.', fname)
        if not os.path.exists(path):
            continue
        for r in csv.DictReader(open(path, encoding='utf-8')):
            email = r.get('email', '').strip().lower()
            country = r.get('country', '').strip()
            if not email or '@' not in email:
                continue
            if country.lower() not in poland:
                continue
            if email in seen:
                continue
            seen.add(email)
            rid = email.split('@')[0].replace('.', '_')[:20]
            recipients.append({'email': email, 'rid': rid})
    return recipients


def load_already_sent():
    sent = set()
    if os.path.exists(LOG_FILE):
        for r in csv.DictReader(open(LOG_FILE, encoding='utf-8')):
            if r.get('campaign', '').strip() == CAMPAIGN:
                sent.add(r.get('recipient', '').strip().lower())
    return sent


def log_send(email, status):
    with open(LOG_FILE, 'a', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'send_surfiq_push_poland.py', email, SUBJECT, status, CAMPAIGN])


def main():
    recipients = load_polish_recipients()
    already = load_already_sent()
    todo = [r for r in recipients if r['email'] not in already]

    print(f"=== POLSKA PUSH UPDATE ===")
    print(f"Znaleziono: {len(recipients)} polskich szkół")
    print(f"Już wysłane: {len(already)}")
    print(f"Do wysłania: {len(todo)}")
    print(f"Tempo: 1 mail / {DELAY}s (~{len(todo) * DELAY // 60} min)")
    print()

    if not todo:
        print("Nic do wysłania!")
        return

    success = 0
    errors = 0

    smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60)
    smtp.starttls()
    smtp.login(SMTP_USER, SMTP_PASS)

    for i, r in enumerate(todo):
        email = r['email']
        rid = r['rid']
        html = build_html(email, rid)

        msg = MIMEMultipart('related')
        msg['From'] = f'Magda from SurfIQ <{SMTP_USER}>'
        msg['To'] = email
        msg['Subject'] = SUBJECT
        msg['Reply-To'] = SMTP_USER

        alt = MIMEMultipart('alternative')
        alt.attach(MIMEText(html, 'html', 'utf-8'))
        msg.attach(alt)

        # Embed screenshot
        if os.path.exists(SCREENSHOT):
            with open(SCREENSHOT, 'rb') as f:
                img = MIMEImage(f.read(), _subtype='jpeg')
                img.add_header('Content-ID', '<push_screenshot>')
                img.add_header('Content-Disposition', 'inline', filename='surfiq_push.jpg')
                msg.attach(img)

        try:
            smtp.sendmail(SMTP_USER, email, msg.as_string())
            log_send(email, 'SENT')
            success += 1
            print(f"[{i+1}/{len(todo)}] SENT: {email}")
        except Exception as e:
            err = str(e).replace('\n', ' ')[:100]
            log_send(email, f'FAIL: {err}')
            errors += 1
            print(f"[{i+1}/{len(todo)}] FAIL: {email} — {err}")
            if 'disconnect' in err.lower():
                try: smtp.quit()
                except: pass
                time.sleep(30)
                smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60)
                smtp.starttls()
                smtp.login(SMTP_USER, SMTP_PASS)

        if i < len(todo) - 1:
            time.sleep(DELAY)

    smtp.quit()
    print(f"\n=== DONE: {success} sent, {errors} failed ===")


if __name__ == '__main__':
    main()
