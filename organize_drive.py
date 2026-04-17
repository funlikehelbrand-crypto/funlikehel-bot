"""
Organizuje pliki na Google Drive według struktury FunLikeHel.
"""

import logging
from googleapiclient.discovery import build
from google_auth import get_credentials
from google_drive import create_folder, move_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

def get_service():
    return build("drive", "v3", credentials=get_credentials())

def get_all_files(service):
    result = service.files().list(
        pageSize=100,
        fields="files(id, name, mimeType, parents)",
    ).execute()
    return result.get("files", [])

def main():
    service = get_service()
    logger.info("Pobieram listę plików...")
    files = get_all_files(service)

    # --- Tworzenie struktury folderów ---
    logger.info("Tworzę strukturę folderów...")

    root         = create_folder("FunLikeHel")["id"]
    f_zdjecia    = create_folder("Zdjęcia", root)["id"]
    f_jastarnia  = create_folder("Jastarnia", f_zdjecia)["id"]
    f_egipt      = create_folder("Egipt", f_zdjecia)["id"]
    f_marketing  = create_folder("Marketing i logo", f_zdjecia)["id"]
    f_filmy      = create_folder("Filmy", root)["id"]
    f_szkolenia  = create_folder("Szkoleniowe", f_filmy)["id"]
    f_promo      = create_folder("Promocyjne", f_filmy)["id"]
    f_social     = create_folder("Social Media", f_filmy)["id"]
    f_360        = create_folder("Filmy 360", f_filmy)["id"]
    f_sprzet     = create_folder("Sprzęt", root)["id"]

    logger.info("Struktura folderów utworzona.")

    # --- Reguły przenoszenia plików ---
    # Klucz: fragment nazwy pliku → folder docelowy
    FILM_SZKOLENIOWE = ["zmiana halsu", "downloop", "hals", "technik"]
    FILM_PROMO       = ["alice", "karo", "water"]
    LOGO             = ["logo"]
    FILMY_360_NAME   = ["filmy 360"]
    CABRINHA_NAME    = ["cabrinha"]

    moved = 0
    for f in files:
        name  = f["name"].lower()
        fid   = f["id"]
        mime  = f["mimeType"]
        is_folder = mime == "application/vnd.google-apps.folder"

        # Foldery specjalne
        if is_folder:
            if any(k in name for k in FILMY_360_NAME):
                try:
                    move_file(fid, f_filmy)
                    logger.info("Przenoszę folder '%s' → Filmy/", f["name"])
                    moved += 1
                except Exception as e:
                    logger.warning("Nie mogę przenieść folderu '%s': %s", f["name"], e)
                continue
            if any(k in name for k in CABRINHA_NAME):
                try:
                    move_file(fid, f_sprzet)
                    logger.info("Przenoszę folder '%s' → Sprzęt/", f["name"])
                    moved += 1
                except Exception as e:
                    logger.warning("Nie mogę przenieść folderu '%s' (prawdopodobnie udostępniony zewnętrznie): %s", f["name"], e)
                continue
            continue  # inne foldery pomijamy

        def move(file_id, dest, label):
            try:
                move_file(file_id, dest)
                logger.info("Przenoszę '%s' → %s", f["name"], label)
                return 1
            except Exception as e:
                logger.warning("Pomijam '%s': %s", f["name"], e)
                return 0

        # Logo
        if any(k in name for k in LOGO):
            moved += move(fid, f_marketing, "Marketing i logo/")

        # Filmy szkoleniowe
        elif mime.startswith("video") and any(k in name for k in FILM_SZKOLENIOWE):
            moved += move(fid, f_szkolenia, "Szkoleniowe/")

        # Filmy promocyjne
        elif mime.startswith("video") and any(k in name for k in FILM_PROMO):
            moved += move(fid, f_promo, "Promocyjne/")

        # Pozostałe filmy → Social Media
        elif mime.startswith("video"):
            moved += move(fid, f_social, "Social Media/")

        # Zdjęcia — marzec 2026 prawdopodobnie Egipt (sezon zimowy)
        elif mime.startswith("image") and name.startswith("20260"):
            moved += move(fid, f_egipt, "Zdjęcia/Egipt/")

        # Pozostałe zdjęcia → Jastarnia
        elif mime.startswith("image"):
            moved += move(fid, f_jastarnia, "Zdjęcia/Jastarnia/")

    logger.info("=== Gotowe. Przeniesiono %d plików/folderów. ===", moved)
    print("""
Nowa struktura na Drive:
📁 FunLikeHel/
├── 📁 Zdjęcia/
│   ├── 📁 Jastarnia/
│   ├── 📁 Egipt/
│   └── 📁 Marketing i logo/
├── 📁 Filmy/
│   ├── 📁 Szkoleniowe/
│   ├── 📁 Promocyjne/
│   ├── 📁 Social Media/
│   └── 📁 Filmy 360/
└── 📁 Sprzęt/
    └── 📁 Cabrinha/
""")

if __name__ == "__main__":
    main()
