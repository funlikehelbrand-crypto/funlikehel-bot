"""
Porządkuje Google Drive:
- Usuwa puste duplikaty folderów
- Tworzy Księgowość/Faktury
- Przenosi istniejące foldery z fakturami
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import logging
from googleapiclient.discovery import build
from google_auth import get_credentials
from google_drive import create_folder, move_file, delete_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

service = build("drive", "v3", credentials=get_credentials())

def get_all_folders():
    result = service.files().list(
        q="mimeType='application/vnd.google-apps.folder' and trashed=false",
        pageSize=200,
        fields="files(id, name, parents)",
    ).execute()
    return result.get("files", [])

def count_children(folder_id):
    result = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id)",
        pageSize=10,
    ).execute()
    return len(result.get("files", []))

def delete_folder(folder_id, name):
    try:
        service.files().delete(fileId=folder_id).execute()
        logger.info("🗑️  Usunięto pusty folder: %s", name)
    except Exception as e:
        logger.warning("Nie można usunąć '%s': %s", name, e)

def main():
    folders = get_all_folders()

    # --- Foldery do usunięcia jeśli puste ---
    EMPTY_DELETABLE = [
        "DO_UPLOADU",
        "Sprzęt",
        "Filmy 360",
        "Social Media",
        "Promocyjne",
        "Szkoleniowe",
        "Filmy",
        "Marketing i logo",
        "Egipt",
        "Jastarnia",
        "Zdjęcia",
        "FunLikeHel",
        "Sklep",
        "wyjazdy integracyjne",
        "Zdj na stronę ",
        "Zdjęcia załogi ( tytuł zdjęcia - Imie=ę / ksywka )",
        "Socialmedia znaczniki itd grafiki etc.",
        "Kurs Wariant 3 - propozycja Hotelu ",
        "Faktury 12.25",  # pusty
    ]

    # Usuń puste foldery z listy
    for f in folders:
        if f["name"] in EMPTY_DELETABLE:
            if count_children(f["id"]) == 0:
                delete_folder(f["id"], f["name"])

    # --- Utwórz strukturę Księgowość ---
    logger.info("Tworzę folder Księgowość/Faktury...")
    ksiegowosc = create_folder("Księgowość")
    faktury_folder = create_folder("Faktury", ksiegowosc["id"])
    logger.info("✅ Księgowość/Faktury utworzone.")

    # --- Przenieś istniejące foldery faktur ---
    folders = get_all_folders()  # odśwież listę
    faktury_names = ["Faktury 06.25", "Faktury 07.25", "Faktury 08.25",
                     "Faktury 09.25", "Faktury 11.25"]

    for f in folders:
        if f["name"] in faktury_names:
            try:
                move_file(f["id"], faktury_folder["id"])
                logger.info("📁 Przeniesiono '%s' → Księgowość/Faktury/", f["name"])
            except Exception as e:
                logger.warning("Nie można przenieść '%s': %s", f["name"], e)

    logger.info("=== Gotowe ===")
    logger.info("Folder Faktury: https://drive.google.com/drive/folders/%s", faktury_folder["id"])

if __name__ == "__main__":
    main()
