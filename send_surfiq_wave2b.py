"""
SurfIQ Wave 2B — Americas + Africa (Warm prospects)
With brochure, UTM tracking, auto-logging.
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

SMTP_HOST = "serwer2620595.home.pl"
SMTP_PORT = 587
SMTP_USER = "office@surfiq.eu"
SMTP_PASS = os.environ.get("SURFIQ_SMTP_PASS", "surfiq2026@")
BCC_COPY = "lukasz.michalina@gmail.com"
BROCHURE = os.path.join(os.path.dirname(__file__), "SurfIQ_Brochure_2026.pdf")
BANNER_URL = "https://surfiq.eu/assets/email_banner.png"
PIXEL_BASE = "https://surfiq.eu/api/px"
LOG_FILE = os.path.join(os.path.dirname(__file__), "email_send_log.csv")

def log_send(recipient, subject, status):
    with open(LOG_FILE, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "send_surfiq_wave2b.py", recipient, subject, status, "wave2b_warm"])

def utm(rid):
    return f"utm_source=email&utm_medium=cold&utm_campaign=wave2b&utm_content={rid}"

def site_url(rid):
    return f"https://surfiq.eu/?{utm(rid)}"

def demo_url(rid):
    return f"https://surfiq.eu/demo/?{utm(rid)}"

def pixel_tag(email="", campaign="wave2b"):
    return f'<img src="{PIXEL_BASE}?e={email}&c={campaign}" width="1" height="1" alt="" style="display:block;height:1px;width:1px;border:0;">'

def sig(rid):
    return f"""\
<table cellpadding="0" cellspacing="0" border="0" style="font-family:'Segoe UI',Calibri,Arial,sans-serif;max-width:500px;">
  <tr><td style="padding-bottom:10px;">
    <a href="{site_url(rid)}" style="text-decoration:none;">
      <img src="{BANNER_URL}" alt="SurfIQ" width="500" style="display:block;border-radius:8px;">
    </a>
  </td></tr>
  <tr><td>
    <table cellpadding="0" cellspacing="0" border="0" width="100%">
      <tr>
        <td style="border-right:3px solid #14D1C9;padding-right:14px;vertical-align:top;width:180px;">
          <div style="font-size:15px;font-weight:700;color:#081D3A;">Lucas Al Chalabi</div>
          <div style="font-size:10px;color:#14D1C9;font-weight:600;margin-top:2px;">FOUNDER &amp; CEO</div>
          <div style="font-size:10px;color:#888;margin-top:2px;">LM GreenWaves sp. z o.o.</div>
        </td>
        <td style="padding-left:14px;vertical-align:top;font-size:12px;color:#555;">
          <div><span style="color:#14D1C9;font-weight:700;">T</span>&nbsp;<a href="tel:+48887801809" style="color:#333;text-decoration:none;">+48 887 801 809</a></div>
          <div><span style="color:#14D1C9;font-weight:700;">E</span>&nbsp;<a href="mailto:office@surfiq.eu" style="color:#333;text-decoration:none;">office@surfiq.eu</a></div>
          <div><span style="color:#14D1C9;font-weight:700;">W</span>&nbsp;<a href="{site_url(rid)}" style="color:#14D1C9;text-decoration:none;font-weight:600;">surfiq.eu</a>&nbsp;|&nbsp;<a href="{demo_url(rid)}" style="color:#0D47A1;text-decoration:none;font-weight:600;">Request demo</a></div>
        </td>
      </tr>
    </table>
  </td></tr>
</table>"""

def body_html(rid, email=""):
    return f"""\
<html><body style="font-family:'Segoe UI',Calibri,Arial,sans-serif;font-size:14px;color:#333;line-height:1.7;max-width:640px;">
<p>Hi,</p>
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
<p><strong>SurfIQ integrates with your existing systems.</strong> We handle the full data import so you can start working from day one.</p>
<p>We deploy individually for each country. <strong>The app works in your language</strong>, with local currency and region-specific settings.</p>
<p style="text-align:center;margin:25px 0;">
  <a href="{demo_url(rid)}" style="background:linear-gradient(135deg,#0D47A1,#14D1C9);color:#fff;padding:14px 40px;border-radius:30px;font-size:15px;font-weight:700;text-decoration:none;display:inline-block;">Request your personalized demo &rarr;</a>
</p>
<p>Fill in a short form and we&rsquo;ll set up a <strong>personalized demo</strong> tailored to your school. I&rsquo;m attaching a short overview. If any of it resonates, I&rsquo;d love to show you a <strong>15-minute live call</strong>.</p>
<p>Best,</p><br>
{sig(rid)}
<p style="font-size:11px;color:#999;margin-top:30px;border-top:1px solid #eee;padding-top:12px;">
LM GreenWaves sp. z o.o. &bull; ul. Pawinskiego 29/28, 02-106 Warsaw, Poland<br>
<a href="https://surfiq.eu/unsubscribe" style="color:#999;text-decoration:underline;">Unsubscribe</a>
</p>
{pixel_tag(email=email, campaign="wave2b")}
</body></html>"""

TARGETS = {
    "northkite_br": ("reservas@preabeachexperience.com", "Built for kite schools on the Brazilian coast"),
    "agk_dr": ("agkiteboarding90@gmail.com", "A smarter system for your Cabarete kite school?"),
    "b4kite_tz": ("karibu@b4kite.surf", "Weather-driven scheduling for Zanzibar?"),
    "coconuts_tz": ("coconutskiteznz@gmail.com", "Built for kite schools — not hotels or gyms"),
    "aquaholics_tz": ("info@aquaholics-zanzibar.com", "A dedicated OS for Zanzibar water sports"),
    "coastline_za": ("coastline@peach-international.com", "Built for South African kite schools"),
    "openocean_za": ("info@openocean.africa", "A smarter way to run your kite school?"),
    "kitemotion_ke": ("kontakt@kitemotion.pl", "System stworzony dla szkol kite — nie hoteli"),
    "encolombia": ("info@encolombiakitesurf.com", "Built for Caribbean kite schools"),
    "cabokite_co": ("cabokitecenter@gmail.com", "A dedicated OS for Colombian kite schools"),
    "kitemex": ("info@kitemex.com", "Built for Mexican kite schools — not generic booking"),
    "laventana_mx": ("laventanacamps@gmail.com", "Weather intelligence for La Ventana?"),
    "fullview_mx": ("fullviewkite@gmail.com", "A smarter system for your Tulum kite school?"),
    "kitecamp_mx": ("info@kitecamptulum.com", "Built for Tulum kite schools"),
    "pdc_mx": ("info@pdckiteboarding.com", "Weather-driven scheduling for Playa del Carmen?"),
}

def send(target_id):
    to, subject = TARGETS[target_id]
    msg = MIMEMultipart("alternative")
    msg["From"] = f"Lucas Al Chalabi <{SMTP_USER}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg["Reply-To"] = SMTP_USER
    msg.attach(MIMEText(f"Hi,\n\nAfter years of running kitesurf schools ourselves...\n\nRequest your personalized demo: {demo_url(target_id)}\n\nBest,\nLucas Al Chalabi\noffice@surfiq.eu | surfiq.eu | surfiq.eu/demo/", "plain", "utf-8"))
    msg.attach(MIMEText(body_html(target_id, email=to), "html", "utf-8"))
    if os.path.exists(BROCHURE):
        with open(BROCHURE, "rb") as f:
            part = MIMEBase("application", "pdf")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename="SurfIQ_Overview_2026.pdf")
            msg.attach(part)
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
    server.ehlo(); server.starttls(); server.ehlo()
    server.login(SMTP_USER, SMTP_PASS)
    server.sendmail(SMTP_USER, [to, BCC_COPY], msg.as_string())
    server.quit()
    log_send(to, subject, "SENT")
    print(f"  SENT -> {to}  (id={target_id})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_surfiq_wave2b.py <target|all|list>")
        sys.exit(1)
    cmd = sys.argv[1].lower()
    if cmd == "list":
        for k, (e, s) in TARGETS.items():
            print(f"  {k:<16} -> {e:<42} {s[:50]}")
    elif cmd == "all":
        targets = list(TARGETS.keys())
        print(f"\nWave 2B: {len(targets)} recipients (Americas + Africa)\n")
        for t in targets:
            try:
                send(t)
            except Exception as e:
                print(f"  FAIL -> {TARGETS[t][0]}: {e}")
        print(f"\nDone. {len(targets)} emails sent.")
    elif cmd in TARGETS:
        send(cmd)
    else:
        print(f"Unknown: {cmd}")
