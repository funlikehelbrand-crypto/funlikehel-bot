"""
SurfIQ Follow-up Email — after technical downtime
Sends to all Wave 1 recipients with explanation about server migration.

Usage:
  python send_surfiq_followup.py test     # test to Lukasz
  python send_surfiq_followup.py all      # send to all Wave 1
  python send_surfiq_followup.py list     # list targets
"""

import smtplib
import os
import sys
import csv
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

SMTP_HOST = "serwer2620595.home.pl"
SMTP_PORT = 587
SMTP_USER = "office@surfiq.eu"
SMTP_PASS = os.environ.get("SURFIQ_SMTP_PASS", "surfiq2026@")
BCC_COPY = "lukasz.michalina@gmail.com"

BROCHURE = os.path.join(os.path.dirname(__file__), "SurfIQ_Brochure_2026.pdf")
BANNER_URL = "https://surfiq.eu/assets/email_banner.png"
PIXEL_BASE = "https://surfiq.eu/api/px"
SITE_BASE = "https://surfiq.eu"
DEMO_BASE = "https://surfiq.eu/demo"


def utm(rid):
    return f"utm_source=email&utm_medium=followup&utm_campaign=wave1_followup&utm_content={rid}"


def site_url(rid):
    return f"{SITE_BASE}/?{utm(rid)}"


def demo_url(rid):
    return f"{DEMO_BASE}/?{utm(rid)}"


def pixel_tag(email="", campaign="wave1_followup"):
    return f'<img src="{PIXEL_BASE}?e={email}&c={campaign}" width="1" height="1" alt="" style="display:block;height:1px;width:1px;border:0;">'


def signature(name, role, phone, rid):
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
            <div style="font-size:15px;font-weight:700;color:#081D3A;line-height:1.3;">{name}</div>
            <div style="font-size:10px;color:#14D1C9;font-weight:600;letter-spacing:0.5px;margin-top:2px;">{role}</div>
            <div style="font-size:10px;color:#888;margin-top:2px;">LM GreenWaves sp. z o.o.</div>
          </td>
          <td style="padding-left:14px;vertical-align:top;font-size:12px;color:#555;">
            <div><span style="color:#14D1C9;font-weight:700;">T</span>&nbsp;
              <a href="tel:{phone}" style="color:#333;text-decoration:none;">{phone}</a></div>
            <div><span style="color:#14D1C9;font-weight:700;">E</span>&nbsp;
              <a href="mailto:office@surfiq.eu" style="color:#333;text-decoration:none;">office@surfiq.eu</a></div>
            <div><span style="color:#14D1C9;font-weight:700;">W</span>&nbsp;
              <a href="{site_url(rid)}" style="color:#14D1C9;text-decoration:none;font-weight:600;">surfiq.eu</a>
              &nbsp;|&nbsp;
              <a href="{demo_url(rid)}" style="color:#0D47A1;text-decoration:none;font-weight:600;">Request demo</a></div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>"""


SIG_LUCAS = lambda rid: signature("Lucas Al Chalabi", "FOUNDER &amp; CEO", "+48 887 801 809", rid)


def body_html(rid, school_name="your school", email=""):
    return f"""\
<html>
<body style="font-family:'Segoe UI',Calibri,Arial,sans-serif;font-size:14px;color:#333;line-height:1.7;max-width:640px;">

<p>Hi,</p>

<p>At the end of the day, we&rsquo;re coming back with great news. First of all &mdash; <strong>thank you for the enormous interest</strong> in SurfIQ over the past few days. The response has been truly overwhelming.</p>

<p>In fact, the volume of traffic was so high that it triggered a server migration on our end, which caused <a href="{site_url(rid)}" style="color:#14D1C9;font-weight:600;">surfiq.eu</a> to be temporarily unavailable. <strong>Everything is now fully back online and running smoothly.</strong></p>

<p>If you haven&rsquo;t had the chance yet, I&rsquo;d love to invite you to request a <strong>personalized demo</strong>:</p>

<p style="text-align:center;margin:25px 0;">
  <a href="{demo_url(rid)}" style="background:linear-gradient(135deg,#0D47A1,#14D1C9);color:#fff;padding:14px 40px;border-radius:30px;font-size:15px;font-weight:700;text-decoration:none;display:inline-block;">Request your personalized demo &rarr;</a>
</p>

<p>Fill in a short form and we&rsquo;ll set up a demo tailored to your school. The demo runs on real (anonymized) data from an actual kite school &mdash; 800+ students, 45 instructors, 2 locations:</p>

<ul style="margin:10px 0;padding-left:20px;">
  <li>Live weather dashboard (Windguru, Windy, Windfinder)</li>
  <li>Drag &amp; drop scheduling with wind awareness</li>
  <li>Student CRM with training history and certifications</li>
  <li>Finance module &mdash; revenue per sport, instructor, location</li>
  <li>AI-powered client communication (WhatsApp, IG, email)</li>
</ul>

<p>If you&rsquo;d prefer a personal walkthrough, I&rsquo;m happy to do a <strong>15-minute live call</strong> &mdash; no slides, no sales pitch, just the real product.</p>

<p>Best,</p>
<br>
{SIG_LUCAS(rid)}

<p style="font-size:11px;color:#999;margin-top:30px;border-top:1px solid #eee;padding-top:12px;">
LM GreenWaves sp. z o.o. &bull; ul. Pawinskiego 29/28, 02-106 Warsaw, Poland<br>
<a href="https://surfiq.eu/unsubscribe" style="color:#999;text-decoration:underline;">Unsubscribe</a> if you no longer wish to receive these emails.
</p>

{pixel_tag(email=email, campaign="wave1_followup")}

</body>
</html>"""


def body_plain(rid, school_name="your school"):
    return f"""Hi,

At the end of the day, we're coming back with great news. First of all -- thank you for the enormous interest in SurfIQ over the past few days. The response has been truly overwhelming.

In fact, the volume of traffic was so high that it triggered a server migration on our end, which caused surfiq.eu to be temporarily unavailable. Everything is now fully back online and running smoothly.

If you haven't had the chance yet, I'd love to invite you to request a personalized demo:

{demo_url(rid)}

Fill in a short form and we'll set up a demo tailored to your school. The demo runs on real (anonymized) data from an actual kite school -- 800+ students, 45 instructors, 2 locations:

- Live weather dashboard (Windguru, Windy, Windfinder)
- Drag & drop scheduling with wind awareness
- Student CRM with training history and certifications
- Finance module -- revenue per sport, instructor, location
- AI-powered client communication (WhatsApp, IG, email)

If you'd prefer a personal walkthrough, I'm happy to do a 15-minute live call -- no slides, no sales pitch, just the real product.

Best,
Lucas Al Chalabi
Founder & CEO, SurfIQ
LM GreenWaves sp. z o.o.
office@surfiq.eu | surfiq.eu | surfiq.eu/demo/

---
LM GreenWaves sp. z o.o. | ul. Pawinsking 29/28, 02-106 Warsaw, Poland
Unsubscribe: https://surfiq.eu/unsubscribe
"""


# Wave 1 recipients (same as original)
TARGETS = {
    "test": {
        "to": "lukaszmichalina@gmail.com",
        "school": "FUN like HEL",
    },
    "kbc_elgouna": {
        "to": "elgouna@kbc-world.com",
        "school": "KBC El Gouna",
    },
    "kbc_rassoma": {
        "to": "rassoma@kbc-world.com",
        "school": "KBC Ras Soma",
    },
    "riah": {
        "to": "info@riahkiteacademy.com",
        "school": "Riah Kite Academy",
    },
    "kitepower": {
        "to": "info@kitepowerelgouna.com",
        "school": "Kitepower El Gouna",
    },
    "harrynass": {
        "to": "info@harry-nass.com",
        "school": "Harry Nass",
    },
    "7bft": {
        "to": "7bft@somabay.com",
        "school": "7BFT KiteHouse",
    },
    "hurghadakite": {
        "to": "info@hurghadakite.com",
        "school": "Hurghada Kite",
    },
    "ghostbay": {
        "to": "info@ghostbaykite.com",
        "school": "Ghost Bay Kite",
    },
    "olekite": {
        "to": "info@olekite.com",
        "school": "OleKite",
    },
    "tornado": {
        "to": "safaga@tornadosurf.com",
        "school": "Tornado Surf",
    },
    "lostlagoon": {
        "to": "info@lost-lagoon.com",
        "school": "Lost Lagoon",
    },
    "ionclub": {
        "to": "safagakite@ion-club.net",
        "school": "ION CLUB Safaga",
    },
    "hawasafaga": {
        "to": "info@hawasafaga.com",
        "school": "Hawa Safaga",
    },
    "kitemood": {
        "to": "info@kitemood.com",
        "school": "Kite Mood",
    },
}

SUBJECT = "Thank you for the interest \u2014 SurfIQ demo is live"


def send(target_id):
    t = TARGETS[target_id]
    rid = target_id

    msg = MIMEMultipart("alternative")
    msg["From"] = f"Lucas Al Chalabi <{SMTP_USER}>"
    msg["To"] = t["to"]
    msg["Subject"] = SUBJECT
    msg["Reply-To"] = SMTP_USER

    msg.attach(MIMEText(body_plain(rid, t["school"]), "plain", "utf-8"))
    msg.attach(MIMEText(body_html(rid, t["school"], email=t["to"]), "html", "utf-8"))

    # Brochure disabled for follow-up (already sent in wave1)

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(SMTP_USER, SMTP_PASS)
    server.sendmail(SMTP_USER, [t["to"], BCC_COPY], msg.as_string())
    server.quit()

    log_send("send_surfiq_followup.py", t["to"], SUBJECT, "SENT", "wave1_followup")
    print(f"  SENT -> {t['to']}  (id={rid})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_surfiq_followup.py <target|all|list|test>")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "list":
        print(f"\nFollow-up targets ({len(TARGETS)}):\n")
        for k, v in TARGETS.items():
            print(f"  {k:<16} -> {v['to']:<35}  {v['school']}")
        sys.exit(0)

    if cmd == "all":
        skip = {"test"}
        targets = [k for k in TARGETS if k not in skip]
        print(f"\nSending follow-up to {len(targets)} recipients...\n")
        print(f"Subject: {SUBJECT}\n")
        for t in targets:
            try:
                send(t)
            except Exception as e:
                print(f"  FAIL -> {TARGETS[t]['to']}: {e}")
        print(f"\nDone. {len(targets)} follow-up emails sent.")
    elif cmd in TARGETS:
        send(cmd)
    else:
        print(f"Unknown target: {cmd}")
        print(f"Available: {', '.join(TARGETS.keys())}")
