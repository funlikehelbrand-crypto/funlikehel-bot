import os
"""Send SurfIQ mailing report to lukasz"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

html = """<html><body style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#222;max-width:700px;margin:0 auto;padding:20px;">

<div style="background:#081D3A;color:white;padding:20px 24px;border-radius:8px 8px 0 0;">
  <h1 style="margin:0;font-size:22px;">SurfIQ Mailing &mdash; Raport 22-23.05.2026</h1>
  <p style="margin:4px 0 0;color:#14D1C9;font-size:13px;">534 maili, 70 opens, 15% open rate</p>
</div>

<div style="padding:20px 24px;background:#f8f9fa;border:1px solid #e0e0e0;">

<h2 style="color:#081D3A;border-bottom:2px solid #14D1C9;padding-bottom:6px;">Kampanie</h2>
<table style="width:100%;border-collapse:collapse;margin-bottom:18px;">
<tr style="background:#081D3A;color:white;">
  <th style="padding:8px 12px;text-align:left;">Kampania</th>
  <th style="padding:8px 12px;text-align:center;">SENT</th>
  <th style="padding:8px 12px;text-align:left;">Data</th>
</tr>
<tr><td style="padding:8px 12px;">Wave 1-2b Cold (EN)</td><td style="padding:8px 12px;text-align:center;">51</td><td style="padding:8px 12px;">20.05</td></tr>
<tr style="background:#f0f0f0;"><td style="padding:8px 12px;font-weight:700;">Product Update EN</td><td style="padding:8px 12px;text-align:center;font-weight:700;color:#14D1C9;">467</td><td style="padding:8px 12px;">22.05</td></tr>
<tr><td style="padding:8px 12px;font-weight:700;">Polska Wave 1 (PL)</td><td style="padding:8px 12px;text-align:center;font-weight:700;color:#14D1C9;">67</td><td style="padding:8px 12px;">23.05</td></tr>
<tr style="background:#081D3A;color:white;"><td style="padding:8px 12px;font-weight:700;">TOTAL unique</td><td style="padding:8px 12px;text-align:center;font-weight:700;font-size:18px;">534</td><td style="padding:8px 12px;">0 FAIL</td></tr>
</table>

<h2 style="color:#081D3A;border-bottom:2px solid #14D1C9;padding-bottom:6px;">Otwarcia</h2>
<table style="width:100%;border-collapse:collapse;margin-bottom:18px;">
<tr style="background:#081D3A;color:white;"><th style="padding:8px;text-align:left;">Metryka</th><th style="padding:8px;text-align:center;">Wartość</th></tr>
<tr><td style="padding:8px;">Email opens (22.05)</td><td style="padding:8px;text-align:center;font-weight:700;">57</td></tr>
<tr style="background:#f0f0f0;"><td style="padding:8px;">Email opens (23.05)</td><td style="padding:8px;text-align:center;font-weight:700;">13+</td></tr>
<tr style="background:#e8f4f8;"><td style="padding:8px;font-weight:700;">TOTAL opens</td><td style="padding:8px;text-align:center;font-weight:700;color:#14D1C9;font-size:18px;">70+</td></tr>
<tr><td style="padding:8px;">Open rate EN</td><td style="padding:8px;text-align:center;font-weight:700;">15.0%</td></tr>
<tr style="background:#f0f0f0;"><td style="padding:8px;">Kliknięcia surfiq.eu</td><td style="padding:8px;text-align:center;">0</td></tr>
<tr><td style="padding:8px;">Odpowiedzi</td><td style="padding:8px;text-align:center;">0 (jeszcze)</td></tr>
</table>

<h2 style="color:#081D3A;border-bottom:2px solid #14D1C9;padding-bottom:6px;">Rynki</h2>
<table style="width:100%;border-collapse:collapse;margin-bottom:18px;font-size:13px;">
<tr style="background:#081D3A;color:white;"><th style="padding:6px 8px;text-align:left;">Region</th><th style="padding:6px 8px;text-align:center;">Wysłano</th></tr>
<tr><td style="padding:6px 8px;">Polska</td><td style="padding:6px 8px;text-align:center;">67</td></tr>
<tr style="background:#f0f0f0;"><td style="padding:6px 8px;">Niemcy</td><td style="padding:6px 8px;text-align:center;">56</td></tr>
<tr><td style="padding:6px 8px;">Hiszpania</td><td style="padding:6px 8px;text-align:center;">61</td></tr>
<tr style="background:#f0f0f0;"><td style="padding:6px 8px;">Włochy</td><td style="padding:6px 8px;text-align:center;">49</td></tr>
<tr><td style="padding:6px 8px;">Egipt</td><td style="padding:6px 8px;text-align:center;">42</td></tr>
<tr style="background:#f0f0f0;"><td style="padding:6px 8px;">Francja</td><td style="padding:6px 8px;text-align:center;">39</td></tr>
<tr><td style="padding:6px 8px;">Portugalia</td><td style="padding:6px 8px;text-align:center;">25</td></tr>
<tr style="background:#f0f0f0;"><td style="padding:6px 8px;">Turcja</td><td style="padding:6px 8px;text-align:center;">23</td></tr>
<tr><td style="padding:6px 8px;">Brazylia</td><td style="padding:6px 8px;text-align:center;">23</td></tr>
<tr style="background:#f0f0f0;"><td style="padding:6px 8px;">Grecja</td><td style="padding:6px 8px;text-align:center;">12</td></tr>
<tr><td style="padding:6px 8px;">Maroko + Cape Verde</td><td style="padding:6px 8px;text-align:center;">30</td></tr>
<tr style="background:#f0f0f0;"><td style="padding:6px 8px;">Zanzibar + Afryka</td><td style="padding:6px 8px;text-align:center;">25</td></tr>
<tr><td style="padding:6px 8px;">Dominikana + Kolumbia + Meksyk</td><td style="padding:6px 8px;text-align:center;">23</td></tr>
<tr style="background:#f0f0f0;"><td style="padding:6px 8px;">Bałtyk (LT, LV, EE, DK)</td><td style="padding:6px 8px;text-align:center;">7</td></tr>
<tr><td style="padding:6px 8px;">Azja + Australia + inne</td><td style="padding:6px 8px;text-align:center;">19</td></tr>
</table>

<h2 style="color:#081D3A;border-bottom:2px solid #ff6b35;padding-bottom:6px;">Plan</h2>
<ol style="font-size:13px;">
  <li><strong>Polska:</strong> STOP wysyłki &mdash; czekamy na odpowiedzi (67 maili)</li>
  <li><strong>Egipt osobna kampania:</strong> jesteśmy na miejscu do 10.06 &mdash; demo na żywo</li>
  <li><strong>Follow-up 70 openerów:</strong> mocniejszy CTA, czysty tekst</li>
  <li><strong>Monitorować:</strong> GA4, odpowiedzi office@surfiq.eu</li>
</ol>

<div style="background:#081D3A;color:#14D1C9;padding:14px 20px;border-radius:0 0 8px 8px;text-align:center;font-size:12px;margin-top:20px;">
  SurfIQ Campaign Bot | 534 contacts | 70 opens | 15% open rate | DKIM active
</div>

</div>
</body></html>"""

msg = MIMEMultipart("alternative")
msg["From"] = "SurfIQ Campaign Bot <office@surfiq.eu>"
msg["To"] = "lukaszmichalina@gmail.com"
msg["Subject"] = "SurfIQ Mailing Report \u2014 534 maili, 70 opens, 15% open rate"
msg.attach(MIMEText(html, "html", "utf-8"))

with smtplib.SMTP("serwer2620595.home.pl", 587, timeout=30) as s:
    s.starttls()
    s.login(os.environ.get("SURFIQ_SMTP_USER", "office@surfiq.eu"), os.environ.get("SURFIQ_SMTP_PASS", "surfiq2026@"))
    s.sendmail("office@surfiq.eu", "lukaszmichalina@gmail.com", msg.as_string())
    print("REPORT SENT OK")
