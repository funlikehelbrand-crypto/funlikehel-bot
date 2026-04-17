"""
Jednorazowa autoryzacja OAuth 2.0 dla Google Drive i Gmail.
Uruchom ten skrypt raz: python google_auth.py
Zapisze token.json który będzie używany przez serwer.
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://mail.google.com/",                            # pełny dostęp Gmail (wysyłanie, czytanie, usuwanie)
    "https://www.googleapis.com/auth/drive",               # pełny dostęp do Drive
    "https://www.googleapis.com/auth/youtube.upload",      # upload filmów na YouTube
    "https://www.googleapis.com/auth/youtube.force-ssl",   # komentarze i zarządzanie kanałem
    "https://www.googleapis.com/auth/business.manage",     # Google Business Profile
    "https://www.googleapis.com/auth/contacts",             # pełny dostęp do kontaktów Google (odczyt + zapis)
]

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.json")


def get_credentials() -> Credentials:
    """Zwraca ważne credentials — odświeża token jeśli wygasł."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


if __name__ == "__main__":
    creds = get_credentials()
    print("Autoryzacja zakończona. Plik token.json zapisany.")
    print(f"Email: {creds.token}")
