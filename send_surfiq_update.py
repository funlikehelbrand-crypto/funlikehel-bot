"""SurfIQ Product Update Email — Wave: update_may22
Send to all non-Poland recipients (already sent + new from pipeline).
Max 50 per run. Logs to email_send_log.csv.
"""
import csv, smtplib, time, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

SMTP_HOST = os.environ.get("SURFIQ_SMTP_HOST", "serwer2620595.home.pl")
SMTP_PORT = 587
SMTP_USER = os.environ.get("SURFIQ_SMTP_USER", "office@surfiq.eu")
SMTP_PASS = os.environ.get("SURFIQ_SMTP_PASS", "surfiq2026@")
MAX_SEND = 270  # home.pl DCC blocks after ~270/day
LOG_FILE = "email_send_log.csv"
BROCHURE = "SurfIQ_Brochure_2026.pdf"
CAMPAIGN = "update_may22"
BOUNCE_FILE = "surfiq_bounced_emails.txt"
UNSUB_FILE = "surfiq_unsubscribed.txt"


def load_exclusion_list():
    """Load bounced + unsubscribed emails to skip."""
    excluded = set()
    for f in [BOUNCE_FILE, UNSUB_FILE]:
        if os.path.exists(f):
            with open(f, "r") as fh:
                for line in fh:
                    email = line.strip().lower()
                    if email and "@" in email:
                        excluded.add(email)
    return excluded

def build_html(email, rid):
    return f'''<html><body style="font-family:'Segoe UI',Calibri,Arial,sans-serif;font-size:14px;color:#333;line-height:1.7;max-width:640px;margin:0 auto;padding:20px;">

<p>Hi,</p>

<p>Quick update from our side &mdash; we have just shipped new features in SurfIQ based on real feedback from schools using the system:</p>

<p style="margin:20px 0;padding:16px 20px;background:#f0fafa;border-left:4px solid #14D1C9;border-radius:4px;">
<strong>What&rsquo;s new on the dashboard:</strong><br>
&bull; <strong>Water temperature</strong> &mdash; live data right in your panel, next to wind and weather<br>
&bull; <strong>Tides &amp; water level at your spot</strong> &mdash; real-time, so you know when conditions are optimal<br>
&bull; <strong>Team TODO list</strong> &mdash; tasks assigned to specific team members with deadlines and status<br>
&bull; <strong>Windguru-style calendar</strong> &mdash; hours vertical, instructors in columns, wind data integrated
</p>

<p style="text-align:center;margin:24px 0;">
  <a href="https://surfiq.eu/demo/?utm_source=email&utm_medium=update&utm_campaign={CAMPAIGN}&utm_content={rid}" style="text-decoration:none;">
    <img src="https://surfiq.eu/assets/screenshots/update/dashboard_hurghada_dark.png" alt="SurfIQ Dashboard" width="600" style="display:block;margin:0 auto;border-radius:10px;border:1px solid #e0e0e0;max-width:100%;">
  </a>
  <span style="font-size:11px;color:#999;">Live dashboard: weather forecast, water temp 25&deg;C, wind rose, messages, team tasks</span>
</p>

<p>Every feature comes from real daily operations &mdash; we run two schools ourselves (Poland + Egypt), so we test everything on our own team first.</p>

<p>If you&rsquo;d like to see how it works in practice &mdash; happy to show you the live panel. 15 minutes, no strings attached.</p>

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
          <div style="font-size:15px;font-weight:700;color:#081D3A;">Lucas Al Chalabi</div>
          <div style="font-size:10px;color:#14D1C9;font-weight:600;letter-spacing:0.5px;margin-top:2px;">FOUNDER &amp; CEO</div>
          <div style="font-size:10px;color:#888;margin-top:2px;">LM GreenWaves sp. z o.o.</div>
        </td>
        <td style="padding-left:14px;vertical-align:top;font-size:12px;color:#555;">
          <div><span style="color:#14D1C9;font-weight:700;">T</span>&nbsp;
            <a href="tel:+48887801809" style="color:#333;text-decoration:none;">+48 887 801 809</a></div>
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


def load_already_sent_update():
    """Load emails that already got update_may22"""
    sent = set()
    if os.path.exists(LOG_FILE):
        for r in csv.DictReader(open(LOG_FILE, encoding='utf-8')):
            if r.get('campaign') == CAMPAIGN:
                sent.add(r['recipient'].strip().lower())
    return sent


def load_recipients():
    """Merge all CSVs, exclude Poland, return unique emails"""
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
        if not os.path.exists(fname):
            continue
        for r in csv.DictReader(open(fname, encoding='utf-8')):
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

    msg = MIMEMultipart('mixed')
    msg['From'] = 'Lucas Al Chalabi <office@surfiq.eu>'
    msg['To'] = email
    msg['Subject'] = 'SurfIQ Update: water temp, tides & team TODO on the dashboard'
    msg['Reply-To'] = 'office@surfiq.eu'

    alt = MIMEMultipart('alternative')
    alt.attach(MIMEText(html, 'html', 'utf-8'))
    msg.attach(alt)

    # Attach brochure
    with open(BROCHURE, 'rb') as f:
        part = MIMEBase('application', 'pdf')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment', filename='SurfIQ_Brochure_2026.pdf')
        msg.attach(part)

    smtp.sendmail(SMTP_USER, email, msg.as_string())
    return True


def log_send(email, status):
    with open(LOG_FILE, 'a', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'send_surfiq_update.py',
            email,
            'SurfIQ Update: water temp, tides & team TODO on the dashboard',
            status,
            CAMPAIGN,
        ])


if __name__ == '__main__':
    already_sent = load_already_sent_update()
    all_recipients = load_recipients()
    to_send = [r for r in all_recipients if r['email'] not in already_sent]

    print(f"Total non-Poland in pipeline: {len(all_recipients)}")
    print(f"Already sent update_may22: {len(already_sent)}")
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
                time.sleep(2)  # 2s delay between emails
            except Exception as e:
                log_send(r['email'], f'FAIL: {e}')
                print(f"  {i:>3}/{len(batch)} FAIL {r['email']:<45} {e}")

    print(f"\nDone. Sent: {len(batch)}. Remaining: {len(to_send) - len(batch)}")
