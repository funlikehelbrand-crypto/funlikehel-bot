import os
"""Send SurfIQ campaign status report to lukasz.michalina@gmail.com"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = "serwer2620595.home.pl"
SMTP_PORT = 587
SMTP_USER = "office@surfiq.eu"
SMTP_PASS = os.environ.get("SURFIQ_SMTP_PASS", "surfiq2026@")

msg = MIMEMultipart("alternative")
msg["From"] = "SurfIQ Campaign Bot <office@surfiq.eu>"
msg["To"] = "lukasz.michalina@gmail.com"
msg["Subject"] = "SurfIQ Campaign Status \u2014 2026-05-21"

text = """\
SurfIQ Campaign Status - 2026-05-21

TOTAL EMAILS SENT: 51

Wave 1 Follow-up (Egypt): 14 emails - ALL SENT (2026-05-20 18:01)
Wave 2 Cold (Global): 22 emails - ALL SENT (2026-05-20 18:02)
Wave 2b Warm (Targeted): 15 emails - ALL SENT (2026-05-20 18:34)

Pipeline: 51 new prospects from DeepSearch (Morocco, Germany, Spain, France, SE Asia, Africa, Americas)

Next: Monitor replies, check GA tracking, prepare Wave 3 + follow-ups.
"""

html = """\
<html><body style="font-family:'Segoe UI',Calibri,Arial,sans-serif;color:#222;max-width:700px;margin:0 auto;">

<div style="background:#081D3A;color:white;padding:20px 24px;border-radius:8px 8px 0 0;">
  <h1 style="margin:0;font-size:22px;">SurfIQ Cold Email Campaign &mdash; Status Report</h1>
  <p style="margin:4px 0 0;color:#14D1C9;font-size:13px;">Generated: 2026-05-21 | office@surfiq.eu</p>
</div>

<div style="padding:20px 24px;background:#f8f9fa;border:1px solid #e0e0e0;">

<h2 style="color:#081D3A;border-bottom:2px solid #14D1C9;padding-bottom:6px;">Campaign Summary</h2>

<table style="width:100%;border-collapse:collapse;margin-bottom:18px;">
<tr style="background:#081D3A;color:white;">
  <th style="padding:8px 12px;text-align:left;">Wave</th>
  <th style="padding:8px 12px;text-align:center;">Sent</th>
  <th style="padding:8px 12px;text-align:left;">Target</th>
  <th style="padding:8px 12px;text-align:left;">Date</th>
  <th style="padding:8px 12px;text-align:center;">Status</th>
</tr>
<tr style="background:white;">
  <td style="padding:8px 12px;font-weight:700;">Wave 1 Follow-up</td>
  <td style="padding:8px 12px;text-align:center;font-weight:700;color:#14D1C9;">14</td>
  <td style="padding:8px 12px;">Egypt (El Gouna, Hurghada, Soma Bay, Safaga)</td>
  <td style="padding:8px 12px;">2026-05-20 18:01</td>
  <td style="padding:8px 12px;text-align:center;"><span style="background:#28a745;color:white;padding:2px 8px;border-radius:4px;font-size:11px;">ALL SENT</span></td>
</tr>
<tr style="background:#f0f0f0;">
  <td style="padding:8px 12px;font-weight:700;">Wave 2 Cold</td>
  <td style="padding:8px 12px;text-align:center;font-weight:700;color:#14D1C9;">22</td>
  <td style="padding:8px 12px;">Global &mdash; Italy, Greece, Portugal, NL, Brazil, Caribbean, Zanzibar, SA, AU, Sri Lanka, Kos, Rhodes</td>
  <td style="padding:8px 12px;">2026-05-20 18:02</td>
  <td style="padding:8px 12px;text-align:center;"><span style="background:#28a745;color:white;padding:2px 8px;border-radius:4px;font-size:11px;">ALL SENT</span></td>
</tr>
<tr style="background:white;">
  <td style="padding:8px 12px;font-weight:700;">Wave 2b Warm</td>
  <td style="padding:8px 12px;text-align:center;font-weight:700;color:#14D1C9;">15</td>
  <td style="padding:8px 12px;">Brazil, DR, Zanzibar, South Africa, Poland, Colombia, Mexico</td>
  <td style="padding:8px 12px;">2026-05-20 18:34</td>
  <td style="padding:8px 12px;text-align:center;"><span style="background:#28a745;color:white;padding:2px 8px;border-radius:4px;font-size:11px;">ALL SENT</span></td>
</tr>
<tr style="background:#081D3A;color:white;">
  <td style="padding:8px 12px;font-weight:700;">TOTAL</td>
  <td style="padding:8px 12px;text-align:center;font-weight:700;font-size:18px;">51</td>
  <td colspan="3" style="padding:8px 12px;">All emails delivered via office@surfiq.eu (SMTP TLS)</td>
</tr>
</table>

<h2 style="color:#081D3A;border-bottom:2px solid #14D1C9;padding-bottom:6px;">Wave 1 Follow-up &mdash; Egypt (14 schools)</h2>
<p style="font-size:13px;color:#555;">Subject: <em>Thank you for the interest &mdash; SurfIQ demo is live</em></p>
<table style="width:100%;border-collapse:collapse;margin-bottom:18px;font-size:13px;">
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">KBC El Gouna (45 instr.)</td><td style="padding:4px 8px;">elgouna@kbc-world.com</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">KBC Ras Soma (45 instr.)</td><td style="padding:4px 8px;">rassoma@kbc-world.com</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Riah Kite Academy (23 instr.)</td><td style="padding:4px 8px;">info@riahkiteacademy.com</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Kitepower El Gouna (36 instr.)</td><td style="padding:4px 8px;">info@kitepowerelgouna.com</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Harry Nass (23 instr.)</td><td style="padding:4px 8px;">info@harry-nass.com</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">7BFT Soma Bay (32 instr.)</td><td style="padding:4px 8px;">7bft@somabay.com</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Hurghada Kite (26 instr.)</td><td style="padding:4px 8px;">info@hurghadakite.com</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Ghost Bay Kite (49 instr.)</td><td style="padding:4px 8px;">info@ghostbaykite.com</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Ole Kite (36 instr.)</td><td style="padding:4px 8px;">info@olekite.com</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Tornado Surf Safaga (35 instr.)</td><td style="padding:4px 8px;">safaga@tornadosurf.com</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Lost Lagoon (32 instr.)</td><td style="padding:4px 8px;">info@lost-lagoon.com</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">ION Club Safaga (37 instr.)</td><td style="padding:4px 8px;">safagakite@ion-club.net</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Hawa Safaga (36 instr.)</td><td style="padding:4px 8px;">info@hawasafaga.com</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Kite Mood (16 instr.)</td><td style="padding:4px 8px;">info@kitemood.com</td><td style="color:#28a745;">SENT</td></tr>
</table>

<h2 style="color:#081D3A;border-bottom:2px solid #14D1C9;padding-bottom:6px;">Wave 2 Cold &mdash; Global (22 schools)</h2>
<p style="font-size:13px;color:#555;">Personalized subjects per school. Regions: Italy, Greece, Portugal, Netherlands, Brazil, Caribbean, Zanzibar, Australia, Sri Lanka, Rhodes, Kos</p>
<table style="width:100%;border-collapse:collapse;margin-bottom:18px;font-size:13px;">
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Kite Village Sardegna</td><td style="padding:4px 8px;">Italy</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">DPC Sicily (Duotone)</td><td style="padding:4px 8px;">Italy</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Gargano Surf</td><td style="padding:4px 8px;">Italy</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Flisvos Kite Centre Naxos</td><td style="padding:4px 8px;">Greece</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Paros Kite</td><td style="padding:4px 8px;">Greece</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Kite Control Portugal</td><td style="padding:4px 8px;">Portugal</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Kitesurfschool.nl</td><td style="padding:4px 8px;">Netherlands</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Barrinha Kite School</td><td style="padding:4px 8px;">Brazil</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Laurel Eastman</td><td style="padding:4px 8px;">Caribbean</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Champion Kiteboarding</td><td style="padding:4px 8px;">Caribbean</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Kite Center Zanzibar</td><td style="padding:4px 8px;">Tanzania</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">DPC Zanzibar (Duotone)</td><td style="padding:4px 8px;">Tanzania</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Isla Kitesurfing</td><td style="padding:4px 8px;">IKO+VDWS</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Padayon Kiteboarding Boracay</td><td style="padding:4px 8px;">Philippines</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">High Five Cape Town</td><td style="padding:4px 8px;">South Africa</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Soul Kite Australia</td><td style="padding:4px 8px;">Australia</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Tribe Watersports</td><td style="padding:4px 8px;">Multi-loc.</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Kitesurfing Lanka</td><td style="padding:4px 8px;">Sri Lanka</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Kite Center Sri Lanka</td><td style="padding:4px 8px;">Sri Lanka</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Kitesurfing Kos</td><td style="padding:4px 8px;">Greece</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Kite Worldwide</td><td style="padding:4px 8px;">Multi-dest.</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Wet Skillz Rhodes</td><td style="padding:4px 8px;">Greece</td><td style="color:#28a745;">SENT</td></tr>
</table>

<h2 style="color:#081D3A;border-bottom:2px solid #14D1C9;padding-bottom:6px;">Wave 2b Warm &mdash; Targeted (15 schools)</h2>
<p style="font-size:13px;color:#555;">Brazil, Dominican Republic, Zanzibar, South Africa, Poland, Colombia, Mexico</p>
<table style="width:100%;border-collapse:collapse;margin-bottom:18px;font-size:13px;">
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Prea Beach Experience</td><td style="padding:4px 8px;">Brazil</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">AG Kiteboarding Cabarete</td><td style="padding:4px 8px;">Dom. Rep.</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">B4 Kite Zanzibar</td><td style="padding:4px 8px;">Tanzania</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Coconuts Kite Zanzibar</td><td style="padding:4px 8px;">Tanzania</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Aquaholics Zanzibar</td><td style="padding:4px 8px;">Tanzania</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Coastline SA</td><td style="padding:4px 8px;">South Africa</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Open Ocean Africa</td><td style="padding:4px 8px;">South Africa</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">KiteMotion</td><td style="padding:4px 8px;">Poland</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">En Colombia Kitesurf</td><td style="padding:4px 8px;">Colombia</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Cabo Kite Center</td><td style="padding:4px 8px;">Colombia</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">KiteMex</td><td style="padding:4px 8px;">Mexico</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">La Ventana Camps</td><td style="padding:4px 8px;">Mexico</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">Full View Kite Tulum</td><td style="padding:4px 8px;">Mexico</td><td style="color:#28a745;">SENT</td></tr>
<tr><td style="padding:4px 8px;">Kite Camp Tulum</td><td style="padding:4px 8px;">Mexico</td><td style="color:#28a745;">SENT</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:4px 8px;">PDC Kiteboarding</td><td style="padding:4px 8px;">Mexico</td><td style="color:#28a745;">SENT</td></tr>
</table>

<h2 style="color:#081D3A;border-bottom:2px solid #14D1C9;padding-bottom:6px;">Pipeline &mdash; DeepSearch 2026-05-21</h2>
<p>51 nowych prospektow znalezionych przez DeepSearch (jeszcze nie wysylano). Kraje:</p>
<table style="width:100%;border-collapse:collapse;margin-bottom:18px;font-size:13px;">
<tr style="background:#fff3cd;"><td style="padding:4px 8px;font-weight:700;">Morocco (Dakhla + Essaouira)</td><td style="padding:4px 8px;text-align:center;">9 schools</td></tr>
<tr><td style="padding:4px 8px;">Germany (Ostsee)</td><td style="padding:4px 8px;text-align:center;">4</td></tr>
<tr style="background:#fff3cd;"><td style="padding:4px 8px;">Spain (Fuerteventura, Lanzarote, Tarifa)</td><td style="padding:4px 8px;text-align:center;">5</td></tr>
<tr><td style="padding:4px 8px;">France</td><td style="padding:4px 8px;text-align:center;">4</td></tr>
<tr style="background:#fff3cd;"><td style="padding:4px 8px;">Montenegro + Croatia</td><td style="padding:4px 8px;text-align:center;">4</td></tr>
<tr><td style="padding:4px 8px;">Vietnam + Thailand + Philippines</td><td style="padding:4px 8px;text-align:center;">4</td></tr>
<tr style="background:#fff3cd;"><td style="padding:4px 8px;">South Africa, Cape Verde, Kenya, Madagascar, Mauritius</td><td style="padding:4px 8px;text-align:center;">7</td></tr>
<tr><td style="padding:4px 8px;">Dominican Republic, Colombia, Panama, Bonaire</td><td style="padding:4px 8px;text-align:center;">5</td></tr>
<tr style="background:#fff3cd;"><td style="padding:4px 8px;">Italy (Sardinia), UK, USA, Sweden, Denmark</td><td style="padding:4px 8px;text-align:center;">9</td></tr>
</table>

<h2 style="color:#081D3A;border-bottom:2px solid #14D1C9;padding-bottom:6px;">Inne kanaly marketingowe</h2>
<ul style="font-size:13px;">
  <li><strong>Facebook:</strong> SurfIQ page setup done, 7-day post series plan ready (Day 1: Dashboard), posty gotowe do publikacji</li>
  <li><strong>LinkedIn:</strong> Gotowe posty (LINKEDIN_SURFIQ_GOTOWE.md)</li>
  <li><strong>YouTube:</strong> Kanal setup, 5 wersji video prezentacji (v1-v5), scenariusz gotowy</li>
  <li><strong>Broszura PDF:</strong> EN + PL (3.5 MB), zalaczana do kazdego cold emaila</li>
  <li><strong>Landing:</strong> surfiq.eu z logo, screenshotami, video</li>
</ul>

<h2 style="color:#081D3A;border-bottom:2px solid #14D1C9;padding-bottom:6px;">Next Steps</h2>
<ol style="font-size:13px;">
  <li><strong>Monitor odpowiedzi</strong> &mdash; Wave 1 Egypt follow-up wyslany wczoraj, oczekiwany czas reakcji 2-5 dni</li>
  <li><strong>GA Tracking</strong> &mdash; Sprawdzic UTM wave1/wave2/wave2b w Google Analytics (G-T4HT1DG5RW)</li>
  <li><strong>Wave 3</strong> &mdash; 51 nowych prospektow z DeepSearch gotowych do spersonalizowanej wysylki</li>
  <li><strong>Follow-up Wave 2</strong> &mdash; Zaplanowac follow-up do Wave 2 (22 szkol globalnych) na 2026-05-23/24</li>
  <li><strong>Social media launch</strong> &mdash; Rozpoczac publikacje FB series + LinkedIn + YT</li>
</ol>

<div style="background:#081D3A;color:#14D1C9;padding:14px 20px;border-radius:0 0 8px 8px;text-align:center;font-size:12px;margin-top:20px;">
  Generated by SurfIQ Campaign Bot | GA: G-T4HT1DG5RW | SMTP: office@surfiq.eu
</div>

</div>
</body></html>
"""

msg.attach(MIMEText(text, "plain", "utf-8"))
msg.attach(MIMEText(html, "html", "utf-8"))

with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
    s.starttls()
    s.login(SMTP_USER, SMTP_PASS)
    s.sendmail(SMTP_USER, "lukasz.michalina@gmail.com", msg.as_string())
    print("EMAIL SENT OK to lukasz.michalina@gmail.com")
