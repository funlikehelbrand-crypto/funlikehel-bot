"""
Operacje na Google Drive — przeglądanie plików i zdjęć szkoły FunLikeHel.
"""

from googleapiclient.discovery import build
from google_auth import get_credentials


def get_drive_service():
    return build("drive", "v3", credentials=get_credentials(), cache_discovery=False)


def list_files(folder_id: str = None, max_results: int = 20) -> list[dict]:
    """
    Zwraca listę plików z Drive (lub z konkretnego folderu).
    """
    service = get_drive_service()
    query = f"'{folder_id}' in parents" if folder_id else None

    results = service.files().list(
        q=query,
        pageSize=max_results,
        fields="files(id, name, mimeType, webViewLink, createdTime)",
    ).execute()

    return results.get("files", [])


def list_images(folder_id: str = None, max_results: int = 50) -> list[dict]:
    """
    Zwraca tylko pliki graficzne (zdjęcia) z Drive.
    """
    service = get_drive_service()
    image_query = "mimeType contains 'image/'"
    if folder_id:
        image_query += f" and '{folder_id}' in parents"

    results = service.files().list(
        q=image_query,
        pageSize=max_results,
        fields="files(id, name, mimeType, webViewLink, webContentLink, createdTime)",
    ).execute()

    return results.get("files", [])


def search_files(keyword: str, max_results: int = 10) -> list[dict]:
    """Szuka plików po nazwie."""
    service = get_drive_service()
    results = service.files().list(
        q=f"name contains '{keyword}'",
        pageSize=max_results,
        fields="files(id, name, mimeType, webViewLink, createdTime)",
    ).execute()
    return results.get("files", [])


def create_folder(name: str, parent_id: str = None) -> dict:
    """Tworzy folder na Drive."""
    service = get_drive_service()
    body = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        body["parents"] = [parent_id]

    folder = service.files().create(body=body, fields="id, name, webViewLink").execute()
    return folder


def rename_file(file_id: str, new_name: str) -> dict:
    """Zmienia nazwę pliku lub folderu."""
    service = get_drive_service()
    updated = service.files().update(
        fileId=file_id,
        body={"name": new_name},
        fields="id, name",
    ).execute()
    return updated


def move_file(file_id: str, new_parent_id: str) -> dict:
    """Przenosi plik do innego folderu."""
    service = get_drive_service()
    file = service.files().get(fileId=file_id, fields="parents").execute()
    parents = file.get("parents", [])

    kwargs = {
        "fileId": file_id,
        "addParents": new_parent_id,
        "fields": "id, name, parents",
    }
    if parents:
        kwargs["removeParents"] = ",".join(parents)

    return service.files().update(**kwargs).execute()


def delete_file(file_id: str):
    """Usuwa plik lub folder (przenosi do kosza)."""
    service = get_drive_service()
    service.files().delete(fileId=file_id).execute()


def trash_file(file_id: str) -> dict:
    """Przenosi plik do kosza (można przywrócić)."""
    service = get_drive_service()
    updated = service.files().update(
        fileId=file_id,
        body={"trashed": True},
        fields="id, name, trashed",
    ).execute()
    return updated
