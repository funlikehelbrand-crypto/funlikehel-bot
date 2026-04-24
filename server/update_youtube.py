"""
Aktualizuje tytuły, opisy i tagi wszystkich filmów FunLikeHel na YouTube.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from youtube import get_youtube_service

service = get_youtube_service()

# ---------------------------------------------------------------------------
# Stały szablon opisu (stopka)
# ---------------------------------------------------------------------------

FOOTER = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏄 FUN like HEL | Szkoła Kite & Wind
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎓 OFERTA SZKOLEŃ:
✅ Kitesurfing | Windsurfing | Wing | SUP | Wakeboarding
✅ Kursy dla dorosłych, dzieci i grup
✅ Obozy sportowe i wyjazdy integracyjne
✅ Femi Campy dla kobiet

📍 POLSKA — Jastarnia, kemping Sun4Hel (100m od morza)
📍 EGIPT — Hurghada, Cabrinha Test Center

💰 Pakiety Egipt od 1910 zł (8h kursu + transfer)

📞 Rezerwacje: 690 270 032
📧 funlikehelbrand@gmail.com
🌐 www.funlikehel.pl
📸 @funlikehel

👉 ZAREZERWUJ TERAZ: zadzwoń lub napisz na Instagram!
"""

TAGS = [
    "kitesurfing", "FunLikeHel", "kurs kitesurfingu", "szkoła kitesurfingu",
    "Jastarnia", "Egipt", "Hurghada", "sporty wodne", "windsurfing",
    "Cabrinha", "kiteboarding", "nauka kitesurfingu", "Półwysep Helski",
    "wing", "SUP", "obozy sportowe", "kite", "surf", "wakeboarding",
    "GirlsWhoKite", "OdZeraDoKajtera"
]

# ---------------------------------------------------------------------------
# Dane każdego filmu: (video_id, nowy_tytuł, intro_opisu)
# ---------------------------------------------------------------------------

VIDEOS = [
    (
        "mrAMvCpFRLk",
        "Kitesurfing z Ekipą — Przyjdź i Spróbuj! | FUN like HEL Egipt",
        "Kite smakuje lepiej w grupie! 🪁 Zbierz znajomych i przyjedźcie na kurs kitesurfingu do Egiptu. Szkolimy przez cały rok — latem na Bałtyku, zimą w słonecznej Hurghada.",
    ),
    (
        "uhq107eV0S0",
        "Sesja Kitesurfingowa | FUN like HEL Egipt",
        "Kolejna sesja na wodzie z ekipą FUN like HEL. Egipt, Hurghada — jeden z najlepszych spotów do kitesurfingu na świecie.",
    ),
    (
        "IzfjOMayFAA",
        "Od Zera do Kajtera — Historia Alicji 🌊 Kurs Kitesurfingu | FUN like HEL Egipt",
        "Od pierwszych kroków na spocie do samodzielnego pływania — oto historia Alicji i jej droga od zera do kajtera! 🌊☀️🪁 Ucząc się u nas w FUN like HEL, każdy może osiągnąć ten cel. Dołącz do nas!",
    ),
    (
        "dXjwdI9C3RA",
        "Wiki: Od Zera do Kajtera 🪁 Nauka Kitesurfingu | FUN like HEL Egipt",
        "Wiki pokazuje, że kitesurfingu może nauczyć się każdy! Od totalnego początku do pewnej jazdy — w naszej szkole FUN like HEL przeprowadzimy Cię przez każdy etap nauki. Szkolimy w Egipcie (Hurghada).",
    ),
    (
        "GBrRn9F75mA",
        "Freeride na Cabrinha — Low Wind Session | FUN like HEL Egipt",
        "Mało wiatru? Żaden problem! Cabrinha 15 radzi sobie świetnie nawet przy słabym wietrze. Freeride session z naszego spotu w Egipcie — Cabrinha Test Center FUN like HEL Hurghada.",
    ),
    (
        "VNlFrJaxy14",
        "Darkslide — Zmiana Halsu | Techniki Kitesurfingu | FUN like HEL Egipt",
        "Darkslide tack change — jedna z bardziej widowiskowych technik w kitesurfingu. Nagranie z naszego spotu w Egipcie. Chcesz nauczyć się takich sztuczek? Zapisz się na kurs zaawansowany!",
    ),
    (
        "-fhE4YwZzsE",
        "Kitesurfing w Egipcie — Najlepszy Spot w Hurghada | FUN like HEL",
        "Egipt to raj dla kitesurferów — ciepła, płytka woda, stały wiatr i słońce przez cały rok. Sprawdź nasz spot w Hurghada i zarezerwuj kurs już dziś!",
    ),
    (
        "DSAYmW5O6LE",
        "Bez Wiatru? Kajakujemy na El Gouna! 🌅 | FUN like HEL Egipt",
        "Kiedy wiatr nie dopisuje, nie marnujemy czasu! Kajaki na El Gouna o zachodzie słońca — kolejna atrakcja podczas pobytu w Egipcie z FUN like HEL. U nas nigdy się nie nudzisz!",
    ),
    (
        "x2KPwtAm_RM",
        "Odwiedź Nas — Cabrinha Test Center & Szkoła Kite | FUN like HEL Egipt",
        "Zapraszamy do naszej bazy w Egipcie! FUN like HEL to oficjalne Centrum Testowe Cabrinha w Hurghada. Przetestuj sprzęt, weź kurs i poczuj magię kitesurfingu na najlepszym spocie w Egipcie.",
    ),
    (
        "aIx1x2YwQF8",
        "Najlepszy Spot do Kitesurfingu w Egipcie — Płytka, Ciepła Woda | FUN like HEL Hurghada",
        "Nasz spot w Hurghada to jedno z najlepszych miejsc do kitesurfingu na świecie — płytka zatoka, ciepła woda, stały wiatr i widok jak z pocztówki. 🌊☀️ Idealne miejsce dla początkujących i zaawansowanych.",
    ),
    (
        "1WJPvqbOIY4",
        "Polska Szkoła Kite — Egipt & Półwysep Helski | FUN like HEL Cabrinha Test Center",
        "FUN like HEL to polska szkoła kitesurfingu działająca przez cały rok — latem w Jastarni na Półwyspie Helskim, zimą w Egipcie (Hurghada). Jesteśmy oficjalnym Centrum Testowym Cabrinha. Odwiedź nas!",
    ),
    (
        "qf5zkuZP6QU",
        "Kinga — Pierwszy Start na Wakeboardzie | FUN like HEL Egipt",
        "Kinga wsiada na wakeboard po raz pierwszy — i to o zachodzie słońca w Egipcie! 🌅 Kiedy nie wieje, pływamy na wakeboardzie. U nas nigdy się nie nudzisz!",
    ),
]

# ---------------------------------------------------------------------------
# Aktualizacja filmów
# ---------------------------------------------------------------------------

def update_video(video_id, title, intro):
    description = intro + FOOTER
    service.videos().update(
        part="snippet",
        body={
            "id": video_id,
            "snippet": {
                "title": title,
                "description": description,
                "tags": TAGS,
                "categoryId": "17",  # Sport
            },
        },
    ).execute()
    print(f"✅ Zaktualizowano: {title[:60]}...")


if __name__ == "__main__":
    print(f"Aktualizuję {len(VIDEOS)} filmów...\n")
    for vid_id, title, intro in VIDEOS:
        try:
            update_video(vid_id, title, intro)
        except Exception as e:
            print(f"❌ Błąd dla {vid_id}: {e}")
    print("\nGotowe!")
