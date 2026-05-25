"""
SurfIQ — Send to ALL Egypt schools from CSV
Uses approved Wave 1 template with auto-personalization per school.
Skips schools already in Wave 1 (send_surfiq_wave1.py).
"""

import csv
import smtplib
import time
import os
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

LOG_FILE = os.path.join(os.path.dirname(__file__), "email_send_log.csv")

def log_send(script, recipient, subject, status, campaign=""):
    with open(LOG_FILE, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), script, recipient, subject, status, campaign])

# ── SMTP ──
SMTP_HOST = "serwer2620595.home.pl"
SMTP_PORT = 587
SMTP_USER = "office@surfiq.eu"
SMTP_PASS = os.environ.get("SURFIQ_SMTP_PASS", "surfiq2026@")
BCC_COPY = "lukasz.michalina@gmail.com"

CSV_PATH = os.path.join(os.path.dirname(__file__), "surfiq_prospects_egypt_poland.csv")
BROCHURE = os.path.join(os.path.dirname(__file__), "SurfIQ_Brochure_2026.pdf")
BANNER_URL = "https://surfiq.eu/assets/email_banner.png"
PIXEL_BASE = "https://surfiq.eu/api/px"
SITE_BASE = "https://surfiq.eu"

# Wave 1 emails already handled by send_surfiq_wave1.py
WAVE1_EMAILS = {
    "elgouna@kbc-world.com", "rassoma@kbc-world.com", "info@riahkiteacademy.com",
    "info@kitepowerelgouna.com", "info@harry-nass.com", "7bft@somabay.com",
    "info@hurghadakite.com", "info@ghostbaykite.com", "info@olekite.com",
    "safaga@tornadosurf.com", "info@lost-lagoon.com", "safagakite@ion-club.net",
    "info@hawasafaga.com", "info@kitemood.com",
}

# Skip junk emails (sentry, wix, etc.)
SKIP_PATTERNS = ["sentry", "wix", "mustermann", "dp-wired"]


def utm(rid):
    return f"utm_source=email&utm_medium=cold&utm_campaign=wave1_egypt&utm_content={rid}"


def site_url(rid):
    return f"{SITE_BASE}/?{utm(rid)}"


DEMO_BASE = "https://surfiq.eu/demo"


def demo_url(rid):
    return f"{DEMO_BASE}/?{utm(rid)}"


def pixel_tag(rid, email="", campaign="wave1_egypt"):
    return f'<img src="{PIXEL_BASE}?e={email}&c={campaign}" width="1" height="1" alt="" style="display:block;height:1px;width:1px;border:0;">'


def signature(rid):
    return f"""\
<table cellpadding="0" cellspacing="0" border="0" style="font-family:'Segoe UI',Calibri,Arial,sans-serif;max-width:500px;">
  <tr>
    <td style="padding-bottom:10px;">
      <a href="{site_url(rid)}" style="text-decoration:none;">
        <img src="{BANNER_URL}" alt="SurfIQ — Smarter Schools. Better Waves." width="500"
             style="display:block;border-radius:8px;">
      </a>
    </td>
  </tr>
  <tr>
    <td>
      <table cellpadding="0" cellspacing="0" border="0" width="100%">
        <tr>
          <td style="border-right:3px solid #14D1C9;padding-right:14px;vertical-align:top;width:180px;">
            <div style="font-size:15px;font-weight:700;color:#081D3A;line-height:1.3;">Lucas Al Chalabi</div>
            <div style="font-size:10px;color:#14D1C9;font-weight:600;letter-spacing:0.5px;margin-top:2px;">FOUNDER &amp; CEO</div>
            <div style="font-size:10px;color:#888;margin-top:2px;">LM GreenWaves sp. z o.o.</div>
          </td>
          <td style="padding-left:14px;vertical-align:top;font-size:12px;color:#555;">
            <div><span style="color:#14D1C9;font-weight:700;">T</span>&nbsp;
              <a href="tel:+48887801809" style="color:#333;text-decoration:none;">+48 887 801 809</a></div>
            <div><span style="color:#14D1C9;font-weight:700;">E</span>&nbsp;
              <a href="mailto:office@surfiq.eu" style="color:#333;text-decoration:none;">office@surfiq.eu</a></div>
            <div><span style="color:#14D1C9;font-weight:700;">W</span>&nbsp;
              <a href="{site_url(rid)}" style="color:#14D1C9;text-decoration:none;font-weight:600;">surfiq.eu</a></div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>"""


def make_subject(school_name, num_instructors, city):
    n = int(num_instructors) if num_instructors and num_instructors.isdigit() else 0
    if n >= 30:
        return f"Managing {n} instructors in {city}? There's a better way."
    elif n >= 15:
        return f"A smarter system for your {city} school?"
    else:
        return f"Built for kite schools — not hotels or gyms"


def make_personal(school_name, num_instructors, city, sports):
    n = int(num_instructors) if num_instructors and num_instructors.isdigit() else 0
    sport_list = sports.replace(",", ", ") if sports else "water sports"
    if n >= 20:
        return f"Hi &mdash; with {n} instructors running {sport_list} in {city}, you need a system that was built for this exact workflow."
    elif n >= 5:
        return f"Hi &mdash; as a {sport_list} school in {city}, you know that weather drives everything. We built SurfIQ with that understanding."
    else:
        return f"Hi &mdash; we built SurfIQ specifically for schools like yours in {city}."


def body_html(rid, personal, cta, email=""):
    demo_cta = demo_url(rid)
    return f"""\
<html>
<body style="font-family:'Segoe UI',Calibri,Arial,sans-serif;font-size:14px;color:#333;line-height:1.7;max-width:640px;">

<p>{personal}</p>

<p>After years of running kitesurf and windsurf schools ourselves, we kept hitting the same wall: no software on the market was actually built for water sports.</p>

<p>Most systems were adapted from hotels, gyms, or generic booking platforms. None of them truly understood wind, tides, instructor rotations, boatman operations, rescue boats, or what it takes to manage a beach base day to day.</p>

<p>That&rsquo;s why we created <strong>SurfIQ</strong> &mdash; a dedicated operating system for water sport schools, designed by people who have run kite and windsurf schools and know what the work of instructors, managers, and base crew actually looks like during the season.</p>

<p style="margin:20px 0;padding:16px 20px;background:#f0fafa;border-left:4px solid #14D1C9;border-radius:4px;">
<strong>What makes SurfIQ different:</strong><br>
&bull; Live weather from 3 sources (Windguru, Windy, Windfinder) &mdash; directly in your dashboard<br>
&bull; AI agents handling clients 24/7 via WhatsApp, Instagram, email, and SMS<br>
&bull; Full student CRM with history, certifications, notes, and training status<br>
&bull; Finance module with revenue breakdown by sport, instructor, margin per sport/instructor, and location<br>
&bull; Mobile app for instructors &mdash; built to work directly on the beach<br>
&bull; Transfer to 2nd Spot &mdash; wind shifts? The system picks the best spot, assigns the boat, and notifies your crew automatically
</p>

<p><strong>SurfIQ integrates with your existing systems.</strong> We handle the full data import &mdash; students, bookings, instructors, training history, and payments &mdash; so you can start working from day one, with no chaos and no data loss.</p>

<p style="text-align:center;margin:25px 0;">
  <a href="{demo_cta}" style="background:linear-gradient(135deg,#0D47A1,#14D1C9);color:#fff;padding:14px 40px;border-radius:30px;font-size:15px;font-weight:700;text-decoration:none;display:inline-block;">Request your personalized demo &rarr;</a>
</p>

<p>Fill in a short form and we&rsquo;ll set up a <strong>personalized demo</strong> tailored to your school &mdash; your sports, your team size, your workflow.</p>

<p>I&rsquo;m attaching a short overview of the system. You&rsquo;ll find more details and the full offer at <a href="{cta}" style="color:#14D1C9;font-weight:600;">surfiq.eu</a>. If any of it resonates, I&rsquo;d love to show you a <strong>15-minute live demo</strong> &mdash; no slides, no sales pitch, just the real product.</p>

<p>Best,</p>
<br>
{signature(rid)}

<p style="font-size:11px;color:#999;margin-top:30px;border-top:1px solid #eee;padding-top:12px;">
LM GreenWaves sp. z o.o. &bull; ul. Pawinskiego 29/28, 02-106 Warsaw, Poland<br>
<a href="https://surfiq.eu/unsubscribe" style="color:#999;text-decoration:underline;">Unsubscribe</a> if you no longer wish to receive these emails.
</p>

{pixel_tag(rid, email=email, campaign="wave1_egypt")}

</body>
</html>"""


def body_plain(rid, personal, cta):
    demo_cta = demo_url(rid)
    return f"""{personal}

After years of running kitesurf and windsurf schools ourselves, we kept hitting the same wall: no software on the market was actually built for water sports.

Most systems were adapted from hotels, gyms, or generic booking platforms. None of them truly understood wind, tides, instructor rotations, boatman operations, rescue boats, or what it takes to manage a beach base day to day.

That's why we created SurfIQ — a dedicated operating system for water sport schools, designed by people who have run kite and windsurf schools and know what the work of instructors, managers, and base crew actually looks like during the season.

What makes SurfIQ different:
- Live weather from 3 sources (Windguru, Windy, Windfinder) — directly in your dashboard
- AI agents handling clients 24/7 via WhatsApp, Instagram, email, and SMS
- Full student CRM with history, certifications, notes, and training status
- Finance module with revenue breakdown by sport, instructor, margin per sport/instructor, and location
- Mobile app for instructors — built to work directly on the beach
- Transfer to 2nd Spot — wind shifts? The system picks the best spot, assigns the boat, and notifies your crew automatically

SurfIQ integrates with your existing systems. We handle the full data import — students, bookings, instructors, training history, and payments — so you can start working from day one, with no chaos and no data loss.

Request your personalized demo: {demo_cta}
Fill in a short form and we'll set up a demo tailored to your school — your sports, your team size, your workflow.

I'm attaching a short overview of the system. You'll find more details and the full offer at surfiq.eu. If any of it resonates, I'd love to show you a 15-minute live demo — no slides, no sales pitch, just the real product.

Best,
Lucas Al Chalabi
Founder & CEO, SurfIQ
LM GreenWaves sp. z o.o.
office@surfiq.eu | surfiq.eu

---
LM GreenWaves sp. z o.o. | ul. Pawińskiego 29/28, 02-106 Warsaw, Poland
Unsubscribe: https://surfiq.eu/unsubscribe
"""


def send_all_egypt():
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get("country", "").strip() == "Egypt"]

    # Deduplicate by email
    seen = set()
    targets = []
    for r in rows:
        email = r.get("email", "").strip()
        if not email or email in seen or email in WAVE1_EMAILS:
            continue
        if any(p in email.lower() for p in SKIP_PATTERNS):
            continue
        seen.add(email)
        targets.append(r)

    print(f"\nEgypt schools to send (excluding Wave 1): {len(targets)}\n")

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(SMTP_USER, SMTP_PASS)

    sent = 0
    failed = 0

    for i, r in enumerate(targets):
        email = r.get("email", "").strip()
        school = r.get("school_name", "").strip()[:60]
        city = r.get("city", "").strip() or "Egypt"
        n_instr = r.get("num_instructors", "").strip()
        sports = r.get("sport_types", "").strip()

        rid = f"eg_{r.get('id','0').strip()}"
        subject = make_subject(school, n_instr, city)
        personal = make_personal(school, n_instr, city, sports)
        cta = site_url(rid)

        msg = MIMEMultipart("alternative")
        msg["From"] = f"Lucas Al Chalabi <{SMTP_USER}>"
        msg["To"] = email
        msg["Subject"] = subject
        msg["Reply-To"] = SMTP_USER

        msg.attach(MIMEText(body_plain(rid, personal, cta), "plain", "utf-8"))
        msg.attach(MIMEText(body_html(rid, personal, cta, email=email), "html", "utf-8"))

        if os.path.exists(BROCHURE):
            with open(BROCHURE, "rb") as bf:
                part = MIMEBase("application", "pdf")
                part.set_payload(bf.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment",
                                filename="SurfIQ_Overview_2026.pdf")
                msg.attach(part)

        try:
            server.sendmail(SMTP_USER, [email, BCC_COPY], msg.as_string())
            sent += 1
            log_send("send_surfiq_egypt_all.py", email, subject, "SENT", "wave1_egypt_all")
            print(f"  [{sent}] SENT -> {email}  ({school[:30]})")
        except Exception as e:
            failed += 1
            print(f"  [!] FAIL -> {email}: {e}")
            # Reconnect if needed
            try:
                server.noop()
            except:
                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASS)

        # 5 second delay between emails to avoid rate limiting
        if i < len(targets) - 1:
            time.sleep(5)

    server.quit()
    print(f"\nDone. Sent: {sent}, Failed: {failed}")


if __name__ == "__main__":
    send_all_egypt()
