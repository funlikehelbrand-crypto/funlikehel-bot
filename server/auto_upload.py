"""
Auto-upload filmów z folderu Drive "YT do wrzucenia" na YouTube.

Konwencja nazwy pliku:
  Tytuł filmu [instrukcja].mp4

Przykłady:
  Freeride Egipt Cabrinha.mp4                    → tytuł: "Freeride Egipt Cabrinha"
  Kurs kitesurfingu Jastarnia [dodaj muzykę].mp4 → tytuł: "Kurs kitesurfingu Jastarnia", instrukcja: "dodaj muzykę"
  Sesja wingfoil [przyspiesz film].mp4           → tytuł: "Sesja wingfoil", instrukcja: "przyspiesz film"

Po wgraniu na YouTube plik jest USUWANY z Drive.
"""

import json
import logging
import os
import re
import subprocess
import tempfile
import httpx
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth import get_credentials
from google_drive import delete_file

logger = logging.getLogger(__name__)

UPLOAD_FOLDER_ID = "1gdsJGsKQfCiw2f8lHweLOOmm5L3oHOvO"  # folder "YT do wrzucenia"

YOUTUBE_TAGS = [
    "kitesurfing", "FunLikeHel", "kurs kitesurfingu", "szkoła kitesurfingu",
    "Jastarnia", "Egipt", "Hurghada", "sporty wodne", "windsurfing",
    "Cabrinha", "kiteboarding", "Półwysep Helski", "wing", "SUP",
]

YOUTUBE_DESCRIPTION_TEMPLATE = """{title}

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


YOUTUBE_SHORTS_DESCRIPTION_TEMPLATE = """{title}

#Shorts #FunLikeHel #kitesurfing #Egipt #sportyWodne

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏄 FUN like HEL | Szkoła Kite & Wind
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 POLSKA — Jastarnia | 📍 EGIPT — Hurghada

📞 690 270 032
🌐 www.funlikehel.pl
📸 @funlikehel
"""

SHORT_MAX_SECONDS = 15  # filmy <= 15s wrzucane jako Short


def get_video_duration(file_path: str) -> float:
    """
    Zwraca czas trwania wideo w sekundach używając ffprobe.
    Jeśli ffprobe niedostępny — zwraca 999 (traktuje jako normalny film).
    """
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", file_path],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception as e:
        logger.warning("Nie można sprawdzić długości '%s': %s — traktuję jako film.", file_path, e)
        return 999.0


INSTRUCTION_KEYWORDS = [
    "dodaj muzyke", "dodaj muzykę", "dodaj muzyk",
    "przyspiesz film", "zwolnij film",
    "przytnij", "skróć", "skroc",
    "dodaj napisy", "dodaj napis",
    "dodaj logo", "dodaj intro", "dodaj outro",
    "zmień kolor", "zmien kolor",
    "kite jak dron",  # tymczasowo jako instrukcja stylu
]


def parse_filename(filename: str) -> tuple[str, str | None]:
    """
    Parsuje nazwę pliku na tytuł YT i opcjonalne instrukcje.

    Obsługuje dwa formaty:
    1. "Tytuł [instrukcja].mp4"  — instrukcja w nawiasach kwadratowych
    2. "Piękny spot, płytka woda, dodaj muzykę.mp4"  — instrukcja jako fraza kluczowa

    Zwraca: (czysty_tytuł, instrukcja lub None)
    """
    name = os.path.splitext(filename)[0].strip()

    # Format 1: nawiasy kwadratowe
    match = re.search(r'\[(.+?)\]', name)
    if match:
        instrukcja = match.group(1).strip()
        tytul = name[:match.start()].strip().rstrip(",").strip()
        return _clean_title(tytul), instrukcja

    # Format 2: wykryj instrukcje po słowach kluczowych
    name_lower = name.lower()
    found_instructions = []
    clean_parts = name
    used_positions = set()

    for kw in INSTRUCTION_KEYWORDS:
        if kw in name_lower:
            idx = name_lower.find(kw)
            if idx in used_positions:
                continue
            # Wytnij frazę instrukcji (do końca lub do przecinka)
            end = name.find(",", idx + len(kw))
            fragment = name[idx: end if end != -1 else len(name)]
            frag_stripped = fragment.strip().rstrip(",").strip()
            if frag_stripped not in found_instructions:
                found_instructions.append(frag_stripped)
            used_positions.update(range(idx, idx + len(fragment)))
            clean_parts = clean_parts.replace(fragment, "")

    instrukcja = " | ".join(found_instructions) if found_instructions else None
    tytul = _clean_title(clean_parts)

    return tytul, instrukcja


def _clean_title(title: str) -> str:
    """Czyści tytuł: usuwa nadmiarowe przecinki, spacje, zamienia _ na spacje."""
    title = title.replace("_", " ").replace("-", " ")
    # Usuń wielokrotne przecinki/spacje
    title = re.sub(r'[,\s]+$', '', title)
    title = re.sub(r'^[,\s]+', '', title)
    title = re.sub(r',\s*,', ',', title)
    title = re.sub(r'\s+', ' ', title)
    # Capitalize pierwsza litera
    return title.strip().capitalize()


def get_drive_service():
    return build("drive", "v3", credentials=get_credentials())


def get_youtube_service():
    return build("youtube", "v3", credentials=get_credentials())


def get_new_videos() -> list[dict]:
    """Pobiera filmy z folderu YT do wrzucenia."""
    service = get_drive_service()
    result = service.files().list(
        q=f"'{UPLOAD_FOLDER_ID}' in parents and mimeType contains 'video/' and trashed=false",
        fields="files(id, name, mimeType)",
    ).execute()
    return result.get("files", [])


def download_file(file_id: str, filename: str, max_retries: int = 3) -> str:
    """Pobiera plik z Drive do katalogu tymczasowego. Ponawia przy timeoucie."""
    creds = get_credentials()
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    headers = {"Authorization": f"Bearer {creds.token}"}
    tmp_path = os.path.join(tempfile.gettempdir(), filename)

    # connect=30s, read=600s — duże pliki wideo mogą ważyć setki MB
    timeout = httpx.Timeout(connect=30.0, read=600.0, write=30.0, pool=30.0)

    for attempt in range(1, max_retries + 1):
        try:
            with httpx.stream("GET", url, headers=headers,
                              follow_redirects=True, timeout=timeout) as r:
                r.raise_for_status()
                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_bytes(chunk_size=4 * 1024 * 1024):  # 4 MB chunks
                        f.write(chunk)
            return tmp_path
        except (httpx.TimeoutException, httpx.ReadError) as e:
            logger.warning("Pobieranie '%s' — próba %d/%d nieudana: %s", filename, attempt, max_retries, e)
            if attempt == max_retries:
                raise
    return tmp_path  # unreachable, ale mypy jest spokojniejszy


def upload_to_youtube(file_path: str, title: str, instrukcja: str | None, is_short: bool = False) -> str:
    """Uploaduje film na YouTube, zwraca video_id."""
    service = get_youtube_service()

    if is_short:
        yt_title = f"{title} #Shorts"
        description = YOUTUBE_SHORTS_DESCRIPTION_TEMPLATE.format(title=title)
    else:
        yt_title = title
        description = YOUTUBE_DESCRIPTION_TEMPLATE.format(title=title)

    if instrukcja:
        logger.info("Instrukcja do filmu '%s': %s", title, instrukcja)

    body = {
        "snippet": {
            "title": yt_title,
            "description": description,
            "tags": YOUTUBE_TAGS,
            "categoryId": "17",  # Sport
        },
        "status": {
            "privacyStatus": "public",
        },
    }

    media = MediaFileUpload(file_path, resumable=True, chunksize=10 * 1024 * 1024)
    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info("Upload YT '%s': %d%%", title, int(status.progress() * 100))

    video_id = response["id"]
    logger.info("✅ Wgrany na YT: https://youtube.com/watch?v=%s | Tytuł: %s", video_id, title)
    return video_id


def process_upload_folder():
    """Sprawdza folder i uploaduje nowe filmy na YouTube, po czym usuwa je z Drive."""
    videos = get_new_videos()

    if not videos:
        return

    logger.info("Znaleziono %d nowych filmów w 'YT do wrzucenia'.", len(videos))

    for video in videos:
        file_id = video["id"]
        filename = video["name"]
        title, instrukcja = parse_filename(filename)

        logger.info("Film: %s | Tytuł YT: %s | Instrukcja: %s", filename, title, instrukcja or "brak")

        tmp_path = None
        try:
            tmp_path = download_file(file_id, filename)
            upload_to_youtube(tmp_path, title, instrukcja)

            # Usuń z Drive po udanym uploadzie
            delete_file(file_id)
            logger.info("🗑️ Plik '%s' usunięty z Drive.", filename)

        except Exception as e:
            err_str = str(e)
            if "quotaExceeded" in err_str:
                logger.warning("⏸️ Limit YouTube API wyczerpany — przerywam, pliki zostaną w Drive do jutra.")
                break  # nie próbuj kolejnych filmów, limit i tak odrzuci
            logger.error("❌ Błąd przy uploadzie '%s': %s", filename, e)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    process_upload_folder()
