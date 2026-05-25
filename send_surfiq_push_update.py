import os
"""SurfIQ Push Notifications Update — Campaign: push_may25
New campaign: mobile app + push notifications for students.
Signature: Magda.
"""
import csv, smtplib, time, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

SMTP_HOST = "serwer2620595.home.pl"
SMTP_PORT = 587
SMTP_USER = "office@surfiq.eu"
SMTP_PASS = os.environ.get("SURFIQ_SMTP_PASS", "surfiq2026@")
MAX_SEND = 270  # home.pl daily limit ~270
LOG_FILE = "email_send_log.csv"
BROCHURE = "SurfIQ_Brochure_2026.pdf"
CAMPAIGN = "push_may25"
SCREENSHOT = os.path.expanduser("~/Downloads/surfiq_push_email.jpg")
MOCKUP = os.path.expanduser("~/Downloads/surfiq_phone_mockup_badge.png")

SUBJECT = "SurfIQ Update: your students now get push notifications"


def build_html(email, rid):
    return f'''<html><body style="font-family:'Segoe UI',Calibri,Arial,sans-serif;font-size:14px;color:#333;line-height:1.7;max-width:640px;margin:0 auto;padding:20px;">

<p>Hi,</p>

<p>We just shipped something schools have been asking for &mdash; <strong>push notifications straight to your students' phones</strong>.</p>

<p style="margin:20px 0;padding:16px 20px;background:#f0fafa;border-left:4px solid #14D1C9;border-radius:4px;">
<strong>What your students see on their phone:</strong><br>
&bull; <strong>Lesson reminders</strong> &mdash; "Your kite lesson tomorrow at 10:00 with Magda"<br>
&bull; <strong>Wind alerts</strong> &mdash; "22 kn steady SW all day &mdash; book your session!"<br>
&bull; <strong>Payment confirmations</strong> &mdash; instant receipt after every payment<br>
&bull; <strong>New services &amp; promos</strong> &mdash; announce camps, eFoil, group sessions<br>
&bull; <strong>Custom messages</strong> &mdash; send anything to all students or specific groups
</p>

<p style="text-align:center;margin:24px 0;">
  <img src="cid:push_screenshot" alt="SurfIQ Push Notifications on phone" width="300" style="display:block;margin:0 auto;border-radius:16px;border:1px solid #e0e0e0;">
  <br>
  <span style="font-size:11px;color:#999;">Real push notifications from SurfIQ &mdash; branded with your school name and logo</span>
</p>

<p style="text-align:center;margin:24px 0;">
  <img src="cid:phone_mockup" alt="SurfIQ app on phone" width="200" style="display:block;margin:0 auto;border-radius:12px;">
  <br>
  <span style="font-size:11px;color:#999;">Your school&rsquo;s branded app &mdash; installed on every student&rsquo;s phone</span>
</p>

<p><strong>Zero cost, zero setup for students.</strong> They install the app, log in &mdash; and start receiving notifications. No WhatsApp groups, no SMS fees, no email that goes to spam.</p>

<p>The app also gives students access to:</p>
<ul style="margin:10px 0;padding-left:20px;">
  <li>Their upcoming bookings &amp; schedule</li>
  <li>Live weather &amp; wind forecast at your spot</li>
  <li>Direct contact with the school</li>
</ul>

<p>Everything runs on SurfIQ &mdash; the same system that manages your bookings, instructors, and finances. One platform, zero friction.</p>

<p>If you&rsquo;d like to see it live &mdash; happy to show you in 15 minutes:</p>

<p style="text-align:center;margin:25px 0;">
  <a href="https://surfiq.eu/demo/?utm_source=email&utm_medium=update&utm_campaign={CAMPAIGN}&utm_content={rid}" style="background:linear-gradient(135deg,#0D47A1,#14D1C9);color:#fff;padding:14px 40px;border-radius:30px;font-size:15px;font-weight:700;text-decoration:none;display:inline-block;">Book a quick demo &rarr;</a>
</p>

<p>Best,</p>
<br>

<table cellpadding="0" cellspacing="0" border="0" style="font-family:'Segoe UI',Calibri,Arial,sans-serif;max-width:500px;">
  <tr>
    <td style="padding-bottom:10px;">
      <a href="https://surfiq.eu?utm_source=email&utm_medium=update&utm_campaign={CAMPAIGN}&utm_content={rid}" style="text-decoration:none;">
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
LM GreenWaves sp. z o.o. &bull; ul. Pawińskiego 29/28, 02-106 Warsaw, Poland<br>
<a href="https://surfiq.eu/unsubscribe?e={email}" style="color:#999;text-decoration:underline;">Unsubscribe</a>
</p>

<img src="https://surfiq.eu/api/px?e={email}&c={CAMPAIGN}" width="1" height="1" style="display:none;">

</body></html>'''


def load_already_sent():
    sent = set()
    if os.path.exists(LOG_FILE):
        for r in csv.DictReader(open(LOG_FILE, encoding='utf-8')):
            if r.get('campaign') == CAMPAIGN:
                sent.add(r['recipient'].strip().lower())
    return sent


def load_recipients():
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
            if country.lower() in poland:
                continue
            if email in seen:
                continue
            seen.add(email)
            name = r.get('school_name', '').strip()
            rid = email.split('@')[0].replace('.', '_')[:20]
            recipients.append({'email': email, 'country': country, 'name': name, 'rid': rid})
    return recipients


def send_email(recipient, smtp):
    email = recipient['email']
    rid = recipient['rid']
    html = build_html(email, rid)

    msg = MIMEMultipart('related')
    msg['From'] = 'Magda from SurfIQ <office@surfiq.eu>'
    msg['To'] = email
    msg['Subject'] = SUBJECT
    msg['Reply-To'] = 'office@surfiq.eu'

    alt = MIMEMultipart('alternative')
    alt.attach(MIMEText(html, 'html', 'utf-8'))
    msg.attach(alt)

    # Embed screenshot as inline image
    with open(SCREENSHOT, 'rb') as f:
        img = MIMEImage(f.read(), _subtype='jpeg')
        img.add_header('Content-ID', '<push_screenshot>')
        img.add_header('Content-Disposition', 'inline', filename='surfiq_push.jpg')
        msg.attach(img)

    # Embed phone mockup as second inline image
    with open(MOCKUP, 'rb') as f:
        img2 = MIMEImage(f.read(), _subtype='png')
        img2.add_header('Content-ID', '<phone_mockup>')
        img2.add_header('Content-Disposition', 'inline', filename='surfiq_app.png')
        msg.attach(img2)

    smtp.sendmail(SMTP_USER, email, msg.as_string())
    return True


def log_send(email, status):
    with open(LOG_FILE, 'a', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'send_surfiq_push_update.py',
            email,
            SUBJECT,
            status,
            CAMPAIGN,
        ])


def send_test(test_email='lukaszmichalina@gmail.com'):
    """Send test to single address"""
    r = {'email': test_email, 'rid': 'test', 'country': 'PL', 'name': 'TEST'}
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASS)
        send_email(r, smtp)
    print(f"TEST SENT to {test_email}")


if __name__ == '__main__':
    import sys
    if '--test' in sys.argv:
        send_test()
        sys.exit(0)

    already_sent = load_already_sent()
    all_recipients = load_recipients()
    to_send = [r for r in all_recipients if r['email'] not in already_sent]

    # Also exclude bounced
    bounced_file = 'surfiq_bounced_emails.txt'
    if os.path.exists(bounced_file):
        bounced = {l.strip().lower() for l in open(bounced_file) if l.strip()}
        to_send = [r for r in to_send if r['email'] not in bounced]

    print(f"Total non-Poland in pipeline: {len(all_recipients)}")
    print(f"Already sent {CAMPAIGN}: {len(already_sent)}")
    print(f"To send now: {len(to_send)} (max {MAX_SEND})")
    print()

    batch = to_send[:MAX_SEND]

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASS)

        for i, r in enumerate(batch, 1):
            try:
                send_email(r, smtp)
                log_send(r['email'], 'SENT')
                print(f"  {i:>3}/{len(batch)} SENT {r['email']:<45} ({r['country']})")
                time.sleep(3)  # 3s delay — safe for home.pl
            except Exception as e:
                log_send(r['email'], f'FAIL: {e}')
                print(f"  {i:>3}/{len(batch)} FAIL {r['email']:<45} {e}")

    print(f"\nDone. Sent: {len(batch)}. Remaining: {len(to_send) - len(batch)}")
