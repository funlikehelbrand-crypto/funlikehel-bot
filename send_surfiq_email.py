"""Send SurfIQ cold emails via SMTP home.pl (office@surfiq.eu)."""
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

def _log_send(recipient, subject, status, campaign="cold"):
    with open(LOG_FILE, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "send_surfiq_email.py", recipient, subject, status, campaign])

SMTP_HOST = "serwer2620595.home.pl"
SMTP_PORT = 587
SMTP_USER = "office@surfiq.eu"
SMTP_PASS = os.environ.get("SURFIQ_SMTP_PASS", "surfiq2026@")
BCC_COPY = "lukasz.michalina@gmail.com"
FROM_NAME = "Lucas Al Chalabi"
FROM_ADDR = "office@surfiq.eu"

BROCHURE_PATH = os.path.join(os.path.dirname(__file__), "SurfIQ_Brochure_2026.pdf")

BANNER_URL = "https://surfiq.eu/assets/email_banner.png"
PIXEL_BASE = "https://surfiq.eu/api/px"

def _make_signature(name, role, phone, banner_url=BANNER_URL):
    return f"""\
<table cellpadding="0" cellspacing="0" border="0" style="font-family:'Segoe UI',Calibri,Arial,sans-serif;max-width:500px;">
  <tr>
    <td style="padding-bottom:10px;">
      <a href="https://surfiq.eu" style="text-decoration:none;">
        <img src="{banner_url}" alt="SurfIQ — Smarter Schools. Better Waves." width="500"
             style="display:block;border-radius:8px;">
      </a>
    </td>
  </tr>
  <tr>
    <td>
      <table cellpadding="0" cellspacing="0" border="0" width="100%">
        <tr>
          <td style="border-right:3px solid #14D1C9;padding-right:14px;vertical-align:top;width:180px;">
            <div style="font-size:15px;font-weight:700;color:#081D3A;">{name}</div>
            <div style="font-size:10px;color:#14D1C9;font-weight:600;letter-spacing:0.5px;margin-top:2px;">{role}</div>
            <div style="font-size:10px;color:#888;margin-top:2px;">LM GreenWaves sp. z o.o.</div>
          </td>
          <td style="padding-left:14px;vertical-align:top;font-size:12px;color:#555;">
            <div><span style="color:#14D1C9;font-weight:700;">T</span>&nbsp;
              <a href="tel:{phone}" style="color:#333;text-decoration:none;">{phone}</a></div>
            <div><span style="color:#14D1C9;font-weight:700;">E</span>&nbsp;
              <a href="mailto:office@surfiq.eu" style="color:#333;text-decoration:none;">office@surfiq.eu</a></div>
            <div><span style="color:#14D1C9;font-weight:700;">W</span>&nbsp;
              <a href="https://surfiq.eu" style="color:#14D1C9;text-decoration:none;font-weight:600;">surfiq.eu</a>
              &nbsp;|&nbsp;
              <a href="https://surfiq.eu/demo/" style="color:#0D47A1;text-decoration:none;font-weight:600;">Request demo</a></div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>"""

SIGNATURE_LUCAS = _make_signature("Lucas Al Chalabi", "FOUNDER &amp; CEO", "+48 887 801 809")
SIGNATURE_MAGDA = _make_signature("Magdalena Abramczyk", "OPERATIONS MANAGER", "+48 517 272 742")
SIGNATURE_LUKASZ = SIGNATURE_LUCAS  # alias

# Default signature
SIGNATURE_HTML = SIGNATURE_LUCAS


def _pixel_tag(email="", campaign="cold"):
    return f'<img src="{PIXEL_BASE}?e={email}&c={campaign}" width="1" height="1" alt="" style="display:block;height:1px;width:1px;border:0;">'


def _build_html(body_paragraphs: list[str], signature: str = None,
                utm_tag: str = "", recipient_email: str = "") -> str:
    sig = signature or SIGNATURE_LUKASZ
    # Inject UTM params into all surfiq.eu links in signature
    if utm_tag:
        utm = f"?utm_source=email&utm_medium=cold&utm_campaign=wave2&utm_content={utm_tag}"
        sig = sig.replace('href="https://surfiq.eu"', f'href="https://surfiq.eu/{utm}"')
        sig = sig.replace('href="https://surfiq.eu/demo/"', f'href="https://surfiq.eu/demo/{utm}"')
    paras = "\n".join(f"<p>{p}</p>" for p in body_paragraphs)

    # CTA button with UTM — points to demo form
    demo_url = "https://surfiq.eu/demo/"
    if utm_tag:
        demo_url = f"https://surfiq.eu/demo/?utm_source=email&utm_medium=cold&utm_campaign=wave2&utm_content={utm_tag}"

    cta_button = f'''<p style="text-align:center;margin:25px 0;">
      <a href="{demo_url}" style="background:linear-gradient(135deg,#0D47A1,#14D1C9);color:#fff;padding:14px 40px;border-radius:30px;font-size:15px;font-weight:700;text-decoration:none;display:inline-block;font-family:'Segoe UI',Calibri,Arial,sans-serif;">Request your personalized demo &rarr;</a>
    </p>'''

    pixel = _pixel_tag(email=recipient_email, campaign=utm_tag or "cold")

    return f"""\
<html><body style="font-family:'Segoe UI',Calibri,Arial,sans-serif;font-size:14px;color:#333;line-height:1.7;">
{paras}
{cta_button}
<p>Best,</p>
<br>
{sig}
{pixel}
</body></html>"""


def _build_plain(body_paragraphs: list[str], sender: str = "Lukasz Michalina") -> str:
    text = "\n\n".join(body_paragraphs)
    return f"""{text}

Best,
{sender}
SurfIQ | LM GreenWaves sp. z o.o.
office@surfiq.eu | surfiq.eu | surfiq.eu/demo/
"""


def send_email(to: str, subject: str, body_paragraphs: list[str],
               attach_brochure: bool = True, signature: str = None,
               sender_name: str = None, utm_tag: str = ""):
    s_name = sender_name or FROM_NAME
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{s_name} <{FROM_ADDR}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg["Reply-To"] = FROM_ADDR

    msg.attach(MIMEText(_build_plain(body_paragraphs, s_name), "plain", "utf-8"))
    msg.attach(MIMEText(_build_html(body_paragraphs, signature, utm_tag, recipient_email=to), "html", "utf-8"))

    if attach_brochure and os.path.exists(BROCHURE_PATH):
        with open(BROCHURE_PATH, "rb") as f:
            part = MIMEBase("application", "pdf")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment",
                            filename="SurfIQ_Brochure_2026.pdf")
            msg.attach(part)

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(SMTP_USER, SMTP_PASS)
    server.sendmail(SMTP_USER, [to, BCC_COPY], msg.as_string())
    server.quit()
    _log_send(to, subject, "SENT", utm_tag or "cold")
    print(f"SENT: {to} | Subject: {subject}")


# ── Email body templates ─────────────────────────────────────────────────────

_BODY_EN = [
    "Hi,",
    "After years of running kitesurf and windsurf schools ourselves, we kept hitting the same wall: no software on the market was actually built for water sports.",
    "Most systems were adapted from hotels, gyms, or generic booking platforms. None of them truly understood wind, tides, instructor rotations, boatman operations, rescue boats, or what it takes to manage a beach base day to day.",
    "That\u2019s why we created <strong>SurfIQ</strong> \u2014 a dedicated operating system for water sport schools, designed by people who have run kite and windsurf schools and know what the work of instructors, managers, and base crew actually looks like during the season.",
    "<strong>What makes SurfIQ different:</strong>"
    "<br>\u2022 Live weather from 3 sources (Windguru, Windy, Windfinder) \u2014 directly in your dashboard"
    "<br>\u2022 AI agents handling clients 24/7 via WhatsApp, Instagram, email, and SMS"
    "<br>\u2022 Full student CRM with history, certifications, notes, and training status"
    "<br>\u2022 Finance module with revenue breakdown by sport, instructor, margin per sport/instructor, and location"
    "<br>\u2022 Mobile app for instructors \u2014 built to work directly on the beach"
    "<br>\u2022 Boat management, rescue, boatman, location tracking, and weather condition changes",
    "SurfIQ integrates with your existing systems. We handle the full data import \u2014 students, bookings, instructors, training history, and payments \u2014 so you can start working from day one, with no chaos and no data loss.",
    "We deploy individually for each country \u2014 Spain, Italy, France, Greece, or any other market. <strong>The app works in your language</strong>, with local currency and region-specific settings. Currently available in Polish, English, and German, with additional languages added on request.",
    "<strong><a href=\"https://surfiq.eu/demo/\" style=\"color:#fff;\">Request your personalized demo</a></strong> &mdash; fill in a short form and we\u2019ll set up a demo tailored to your school, your sports, your team size, and your workflow.",
    "I\u2019m attaching a short overview of the system. You\u2019ll find more details and the full offer at <a href=\"https://surfiq.eu\" style=\"color:#14D1C9;font-weight:600;\">surfiq.eu</a>. If any of it resonates, I\u2019d love to show you a <strong>15-minute live demo</strong> \u2014 no slides, no sales pitch, just the real product.",
]

_BODY_PL = [
    "Cze\u015b\u0107!",
    "Po latach samodzielnego prowadzenia szk\u00f3\u0142 kitesurfingu i windsurfingu ci\u0105gle napotykali\u015bmy ten sam problem: \u017cadne dost\u0119pne na rynku oprogramowanie nie by\u0142o stworzone z my\u015bl\u0105 o sportach wodnych.",
    "Wi\u0119kszo\u015b\u0107 system\u00f3w by\u0142a adaptowana z hoteli, si\u0142owni albo klasycznych grafik\u00f3w rezerwacyjnych. \u017baden z nich realnie nie rozumia\u0142 wiatru, p\u0142yw\u00f3w, rotacji instruktor\u00f3w, pracy bosmana, \u0142\u00f3dek, akcji rescue ani codziennego zarz\u0105dzania baz\u0105 na pla\u017cy.",
    "Dlatego stworzy\u0142i\u015bmy <strong>SurfIQ</strong> \u2014 system operacyjny dedykowany szko\u0142om sport\u00f3w wodnych, zaprojektowany przez osoby, kt\u00f3re same prowadzi\u0142y szko\u0142y kite i windsurfingu oraz wiedz\u0105, jak wygl\u0105da praca instruktor\u00f3w, manager\u00f3w i obs\u0142ugi bazy w sezonie.",
    "<strong>Co wyr\u00f3\u017cnia SurfIQ:</strong>"
    "<br>\u2022 Pogoda z 3 \u017ar\u00f3de\u0142: Windguru, Windy i Windfinder \u2014 dost\u0119pna na \u017cywo bezpo\u015brednio w panelu"
    "<br>\u2022 Agenci AI obs\u0142uguj\u0105cy klient\u00f3w 24/7 przez WhatsApp, Instagram, e-mail i SMS"
    "<br>\u2022 CRM z pe\u0142n\u0105 histori\u0105 ucznia, certyfikatami, notatkami i statusem szkolenia"
    "<br>\u2022 Modu\u0142 finansowy z podzia\u0142em przychod\u00f3w wed\u0142ug sportu, instruktora, wygenerowanej mar\u017cy i lokalizacji"
    "<br>\u2022 Aplikacja mobilna dla instruktor\u00f3w \u2014 stworzona do pracy bezpo\u015brednio na pla\u017cy"
    "<br>\u2022 Obs\u0142uga \u0142\u00f3dek, rescue, bosmana, lokalizacji i zmian warunk\u00f3w pogodowych",
    "SurfIQ integruje si\u0119 z istniej\u0105cymi systemami szko\u0142y. Zajmujemy si\u0119 pe\u0142nym importem danych \u2014 uczni\u00f3w, rezerwacji, instruktor\u00f3w, historii szkole\u0144 i p\u0142atno\u015bci \u2014 dzi\u0119ki czemu mo\u017cesz rozpocz\u0105\u0107 prac\u0119 od pierwszego dnia, bez chaosu i utraty danych.",
    "<strong><a href=\"https://surfiq.eu/demo/\" style=\"color:#fff;\">Zam\u00f3w spersonalizowane demo</a></strong> &mdash; wype\u0142nij kr\u00f3tki formularz, a przygotujemy demo dopasowane do Twojej szko\u0142y, Twoich sport\u00f3w, wielko\u015bci zespo\u0142u i sposobu pracy.",
    "W za\u0142\u0105czniku kr\u00f3tki opis systemu. Wi\u0119cej szczeg\u00f3\u0142\u00f3w i pe\u0142n\u0105 ofert\u0119 znajdziesz na <a href=\"https://surfiq.eu\" style=\"color:#14D1C9;font-weight:600;\">surfiq.eu</a>. Je\u015bli co\u015b z tego do Ciebie przem\u00f3wi, ch\u0119tnie poka\u017c\u0119 Ci <strong>15-minutow\u0105 prezentacj\u0119 na \u017cywo</strong> \u2014 bez slajd\u00f3w i sprzeda\u017cowej gadki, tylko realny produkt.",
]

# ── Email targets ────────────────────────────────────────────────────────────

EMAILS = {
    "test": {
        "to": "lukasz.michalina@gmail.com",
        "subject": "A dedicated operating system for water sport schools",
        "body": _BODY_EN,
    },
    "kbc": {
        "to": "elgouna@kbc-world.com",
        "subject": "A dedicated operating system for water sport schools",
        "body": _BODY_EN,
    },
    "riah": {
        "to": "info@riahkiteacademy.com",
        "subject": "Built for kite schools — not adapted from hotels",
        "body": _BODY_EN,
    },
    "surfpeople": {
        "to": "info@surfpeople.pl",
        "subject": "System stworzony od zera dla szk\u00f3\u0142 sport\u00f3w wodnych",
        "body": _BODY_PL,
    },
    "kitepower": {
        "to": "info@kitepowerelgouna.com",
        "subject": "Finally \u2014 software built for how kite schools actually work",
        "body": _BODY_EN,
    },
    "harrynass": {
        "to": "info@harry-nass.com",
        "subject": "Multi-location management built for wind sport schools",
        "body": _BODY_EN,
    },
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_surfiq_email.py <test|kbc|riah|surfpeople|kitepower|harrynass|all>")
        print(f"Available: {', '.join(EMAILS.keys())}")
        sys.exit(1)

    target = sys.argv[1].lower()

    # Egypt emails use Lukasz signature, Poland/Germany use Magda
    EGYPT_KEYS = {"kbc", "riah", "kitepower", "harrynass"}
    PL_DE_KEYS = {"surfpeople"}

    if target == "all":
        for key in ["kbc", "riah", "surfpeople", "kitepower", "harrynass"]:
            e = EMAILS[key]
            if key in EGYPT_KEYS:
                send_email(e["to"], e["subject"], e["body"],
                           signature=SIGNATURE_LUCAS, sender_name="Lucas Al Chalabi",
                           utm_tag=key)
            else:
                send_email(e["to"], e["subject"], e["body"],
                           signature=SIGNATURE_MAGDA, sender_name="Magdalena Abramczyk",
                           utm_tag=key)
    elif target in EMAILS:
        e = EMAILS[target]
        if target in PL_DE_KEYS:
            send_email(e["to"], e["subject"], e["body"],
                       signature=SIGNATURE_MAGDA, sender_name="Magdalena Abramczyk",
                       utm_tag=target)
        else:
            send_email(e["to"], e["subject"], e["body"],
                       signature=SIGNATURE_LUCAS, sender_name="Lucas Al Chalabi",
                       utm_tag=target)
    else:
        print(f"Unknown target: {target}")
