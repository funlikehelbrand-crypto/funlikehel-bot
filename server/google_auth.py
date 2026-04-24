"""
Jednorazowa autoryzacja OAuth 2.0 dla Google Drive i Gmail.
Uruchom ten skrypt raz lokalnie: python google_auth.py
Zapisze token.json który należy wgrać do Secret Manager.
"""

import json
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/business.manage",
    "https://www.googleapis.com/auth/contacts",
    "https://www.googleapis.com/auth/adwords",
]

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.json")


def get_credentials() -> Credentials:
    """Zwraca ważne credentials.

    Kolejność:
    1. GOOGLE_TOKEN_JSON — zmienna środowiskowa (Secret Manager w Cloud Run)
    2. token.json        — plik lokalny (dev)
    3. Interaktywny flow — tylko lokalnie (wymaga przeglądarki)
    """
    creds = None

    token_json_str = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json_str:
        creds = Credentials.from_authorized_user_info(json.loads(token_json_str), SCOPES)
    elif os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Zapisz odświeżony token do pliku (tylko lokalnie)
            if not token_json_str:
                with open(TOKEN_FILE, "w") as f:
                    f.write(creds.to_json())
        else:
            # Interaktywny flow — tylko dev
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

    return creds


if __name__ == "__main__":
    creds = get_credentials()
    print("Autoryzacja zakończona. Plik token.json zapisany.")
    print()
    print("Wgraj token do Secret Manager:")
    print('  gcloud secrets create GOOGLE_TOKEN_JSON --data-file=token.json')
    print('  # lub aktualizacja:')
    print('  gcloud secrets versions add GOOGLE_TOKEN_JSON --data-file=token.json')
