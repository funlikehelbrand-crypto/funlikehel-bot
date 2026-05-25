"""
SurfIQ Cold Email — Wave 1 (tracked)
- UTM links per recipient
- Tracking pixel per recipient
- Professional HTML signature with banner
- Brochure PDF attached

Usage:
  python send_surfiq_wave1.py test          # send test to Lukasz
  python send_surfiq_wave1.py kbc           # send to KBC
  python send_surfiq_wave1.py all           # send Wave 1 to all
  python send_surfiq_wave1.py list          # show all targets
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

# ── SMTP config ──
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


# ── UTM helpers ──
def utm(recipient_id):
    return f"utm_source=email&utm_medium=cold&utm_campaign=wave1&utm_content={recipient_id}"


def site_url(rid):
    return f"{SITE_BASE}/?{utm(rid)}"


def demo_url(rid):
    return f"{DEMO_BASE}/?{utm(rid)}"


def pixel_tag(rid, email="", campaign="wave1"):
    return f'<img src="{PIXEL_BASE}?e={email}&c={campaign}" width="1" height="1" alt="" style="display:block;height:1px;width:1px;border:0;">'


# ── Signature ──
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
SIG_MAGDA = lambda rid: signature("Magdalena Abramczyk", "OPERATIONS MANAGER", "+48 517 272 742", rid)


# ── Email body (English, universal) ──
def body_html(recipient_id, school_name="your school", personalization="", email=""):
    cta = demo_url(recipient_id)

    personal_line = ""
    if personalization:
        personal_line = f"<p>{personalization}</p>"

    return f"""\
<html>
<body style="font-family:'Segoe UI',Calibri,Arial,sans-serif;font-size:14px;color:#333;line-height:1.7;max-width:640px;">

{personal_line}

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
  <a href="{cta}" style="background:linear-gradient(135deg,#0D47A1,#14D1C9);color:#fff;padding:14px 40px;border-radius:30px;font-size:15px;font-weight:700;text-decoration:none;display:inline-block;">Request your personalized demo &rarr;</a>
</p>

<p>Fill in a short form and we&rsquo;ll set up a <strong>personalized demo</strong> tailored to your school &mdash; your sports, your team size, your workflow.</p>

<p>I&rsquo;m attaching a short overview of the system. You&rsquo;ll find more details and the full offer at <a href="{site_url(recipient_id)}" style="color:#14D1C9;font-weight:600;">surfiq.eu</a>. If any of it resonates, I&rsquo;d love to show you a <strong>15-minute live demo</strong> &mdash; no slides, no sales pitch, just the real product.</p>

<p>Best,</p>
<br>
{SIG_LUCAS(recipient_id)}

<p style="font-size:11px;color:#999;margin-top:30px;border-top:1px solid #eee;padding-top:12px;">
LM GreenWaves sp. z o.o. &bull; ul. Pawinskiego 29/28, 02-106 Warsaw, Poland<br>
<a href="https://surfiq.eu/unsubscribe" style="color:#999;text-decoration:underline;">Unsubscribe</a> if you no longer wish to receive these emails.
</p>

{pixel_tag(recipient_id, email=email, campaign="wave1")}

</body>
</html>"""


def body_plain(recipient_id, school_name="your school", personalization=""):
    personal = f"{personalization}\n\n" if personalization else ""
    return f"""{personal}After years of running kitesurf and windsurf schools ourselves, we kept hitting the same wall: no software on the market was actually built for water sports.

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

Request your personalized demo: {demo_url(recipient_id)}
Fill in a short form and we'll set up a demo tailored to your school — your sports, your team size, your workflow.

I'm attaching a short overview of the system. You'll find more details and the full offer at surfiq.eu. If any of it resonates, I'd love to show you a 15-minute live demo — no slides, no sales pitch, just the real product.

Best,
Lucas Al Chalabi
Founder & CEO, SurfIQ
LM GreenWaves sp. z o.o.
office@surfiq.eu | surfiq.eu | surfiq.eu/demo/

---
LM GreenWaves sp. z o.o. | ul. Pawińskiego 29/28, 02-106 Warsaw, Poland
Unsubscribe: https://surfiq.eu/unsubscribe
"""


# ── Recipients Wave 1 ──
WAVE1 = {
    "test": {
        "to": "lukaszmichalina@gmail.com",
        "subject": "SurfIQ — the operating system built for kite schools",
        "school": "FUN like HEL",
        "personal": "",
    },
    "test_magda": {
        "to": "madalenkiabramczyk@gmail.com",
        "subject": "SurfIQ — the operating system built for kite schools",
        "school": "FUN like HEL",
        "personal": "",
    },
    "kbc_elgouna": {
        "to": "elgouna@kbc-world.com",
        "subject": "Managing 45 instructors across El Gouna and Ras Soma?",
        "school": "KBC El Gouna",
        "personal": "Hi — I noticed you run KBC across El Gouna and Ras Soma with 45 instructors. That's exactly the scale we designed SurfIQ for.",
    },
    "kbc_rassoma": {
        "to": "rassoma@kbc-world.com",
        "subject": "Managing 45 instructors across El Gouna and Ras Soma?",
        "school": "KBC Ras Soma",
        "personal": "Hi — I noticed you run KBC across El Gouna and Ras Soma with 45 instructors. That's exactly the scale we designed SurfIQ for.",
    },
    "riah": {
        "to": "info@riahkiteacademy.com",
        "subject": "Built-in weather intelligence for your IKO-certified school?",
        "school": "Riah Kite Academy",
        "personal": "Hi — I noticed you're IKO and VDWS certified with 23 instructors in El Gouna. That's exactly the kind of professional operation we designed SurfIQ for.",
    },
    "kitepower": {
        "to": "info@kitepowerelgouna.com",
        "subject": "How do you schedule 36 instructors when the wind shifts?",
        "school": "Kitepower El Gouna",
        "personal": "Hi — honest question: when the wind shifts at 10 AM and you need to reassign 36 instructors across spots, how does that work today?",
    },
    "harrynass": {
        "to": "info@harry-nass.com",
        "subject": "Multi-location management for Hurghada + Dahab?",
        "school": "Harry Nass",
        "personal": "Hi — running Hurghada and Dahab with different wind conditions, shared instructors, and clients booking from 5 countries is a level of complexity no hotel booking software can handle.",
    },
    "7bft": {
        "to": "7bft@somabay.com",
        "subject": "A smarter system for 32 instructors in Soma Bay?",
        "school": "7BFT KiteHouse",
        "personal": "Hi — managing 32 instructors in Soma Bay with changing wind conditions every day is no small task. We built SurfIQ because we faced the same challenge.",
    },
    "hurghadakite": {
        "to": "info@hurghadakite.com",
        "subject": "Weather intelligence built into your booking system?",
        "school": "Hurghada Kite",
        "personal": "Hi — with 26 instructors across kite, windsurf, and wingfoil, you need a system that understands wind conditions, not just time slots.",
    },
    "ghostbay": {
        "to": "info@ghostbaykite.com",
        "subject": "A system built for kite schools, not hotels?",
        "school": "Ghost Bay Kite",
        "personal": "Hi — with 49 instructors in Safaga, you're running one of the biggest kite operations on the Red Sea. We built SurfIQ specifically for schools like yours.",
    },
    "olekite": {
        "to": "info@olekite.com",
        "subject": "IKO-certified? Built-in weather + AI for your school",
        "school": "OleKite",
        "personal": "Hi — as an IKO-certified school with 36 instructors in Hurghada, you know that weather drives everything. We built SurfIQ with that exact understanding.",
    },
    "tornado": {
        "to": "safaga@tornadosurf.com",
        "subject": "Kite + windsurf + wingfoil — one system for everything?",
        "school": "Tornado Surf",
        "personal": "Hi — managing 35 instructors across kite, wingfoil, and SUP in Soma Bay? We built SurfIQ because multi-sport scheduling in changing wind is a nightmare without the right tool.",
    },
    "lostlagoon": {
        "to": "info@lost-lagoon.com",
        "subject": "A dedicated OS for your flatwater kite school?",
        "school": "Lost Lagoon",
        "personal": "Hi — with 32 instructors across kite, windsurf, and wingfoil in Hurghada, you need more than a generic booking system.",
    },
    "ionclub": {
        "to": "safagakite@ion-club.net",
        "subject": "Multi-sport, multi-location — one panel?",
        "school": "ION CLUB Safaga",
        "personal": "Hi — ION CLUB runs one of the most professional operations on the Red Sea. With 37 instructors across multiple sports, your team deserves a tool built for this workflow.",
    },
    "hawasafaga": {
        "to": "info@hawasafaga.com",
        "subject": "36 instructors, 3 sports, one system?",
        "school": "Hawa Safaga",
        "personal": "Hi — with 36 instructors across kite, windsurf, and wingfoil in Safaga, scheduling around wind changes is your daily reality. We built SurfIQ for exactly this.",
    },
    "kitemood": {
        "to": "info@kitemood.com",
        "subject": "Built-in weather + AI agents for Marsa Alam?",
        "school": "Kite Mood",
        "personal": "Hi — Marsa Alam is a unique spot with unique wind conditions. SurfIQ was built to handle exactly that — weather-driven scheduling for kite schools.",
    },
}


def send(target_id):
    t = WAVE1[target_id]
    rid = target_id

    msg = MIMEMultipart("alternative")
    msg["From"] = f"Lucas Al Chalabi <{SMTP_USER}>"
    msg["To"] = t["to"]
    msg["Subject"] = t["subject"]
    msg["Reply-To"] = SMTP_USER

    msg.attach(MIMEText(body_plain(rid, t["school"], t["personal"]), "plain", "utf-8"))
    msg.attach(MIMEText(body_html(rid, t["school"], t["personal"], email=t["to"]), "html", "utf-8"))

    # Attach brochure
    if os.path.exists(BROCHURE):
        with open(BROCHURE, "rb") as f:
            part = MIMEBase("application", "pdf")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment",
                            filename="SurfIQ_Overview_2026.pdf")
            msg.attach(part)

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(SMTP_USER, SMTP_PASS)
    server.sendmail(SMTP_USER, [t["to"], BCC_COPY], msg.as_string())
    server.quit()

    log_send("send_surfiq_wave1.py", t["to"], t["subject"], "SENT", "wave1")
    print(f"  SENT -> {t['to']}  (id={rid}, subject={t['subject'][:50]})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_surfiq_wave1.py <target|all|list>")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "list":
        print(f"\nWave 1 targets ({len(WAVE1)}):\n")
        for k, v in WAVE1.items():
            print(f"  {k:<16} -> {v['to']:<35}  {v['school']}")
        sys.exit(0)

    if cmd == "all":
        skip = {"test", "test_magda"}
        targets = [k for k in WAVE1 if k not in skip]
        print(f"\nSending Wave 1 to {len(targets)} recipients...\n")
        for t in targets:
            try:
                send(t)
            except Exception as e:
                print(f"  FAIL -> {WAVE1[t]['to']}: {e}")
        print(f"\nDone. {len(targets)} emails sent.")
    elif cmd in WAVE1:
        send(cmd)
    else:
        print(f"Unknown target: {cmd}")
        print(f"Available: {', '.join(WAVE1.keys())}")
