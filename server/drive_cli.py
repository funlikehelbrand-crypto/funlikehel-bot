"""
Prosty interfejs CLI do zarządzania Google Drive.
Użycie: python drive_cli.py <komenda> [argumenty]

Komendy:
  list                     - lista plików
  images                   - lista zdjęć
  mkdir <nazwa>            - utwórz folder
  rename <id> <nowa_nazwa> - zmień nazwę
  trash <id>               - przenieś do kosza
  delete <id>              - usuń trwale
  search <słowo>           - szukaj plików
"""

import sys
from google_drive import list_files, list_images, create_folder, rename_file, trash_file, delete_file, search_files


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "list":
        files = list_files()
        for f in files:
            print(f"{f['id']}  {f['name']}  ({f['mimeType']})")

    elif cmd == "images":
        files = list_images()
        for f in files:
            print(f"{f['id']}  {f['name']}  {f.get('webViewLink', '')}")

    elif cmd == "mkdir":
        if len(sys.argv) < 3:
            print("Podaj nazwę folderu: python drive_cli.py mkdir <nazwa>")
            return
        name = " ".join(sys.argv[2:])
        folder = create_folder(name)
        print(f"Folder utworzony: {folder['name']}  ID: {folder['id']}")
        print(f"Link: {folder.get('webViewLink', '')}")

    elif cmd == "rename":
        if len(sys.argv) < 4:
            print("Użycie: python drive_cli.py rename <id> <nowa_nazwa>")
            return
        rename_file(sys.argv[2], sys.argv[3])
        print("Nazwa zmieniona.")

    elif cmd == "trash":
        trash_file(sys.argv[2])
        print("Przeniesiono do kosza.")

    elif cmd == "delete":
        confirm = input(f"Trwale usunąć plik {sys.argv[2]}? (tak/nie): ")
        if confirm == "tak":
            delete_file(sys.argv[2])
            print("Usunięto.")

    elif cmd == "search":
        files = search_files(" ".join(sys.argv[2:]))
        for f in files:
            print(f"{f['id']}  {f['name']}")

    else:
        print(f"Nieznana komenda: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
