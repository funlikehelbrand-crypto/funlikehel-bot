"""
Jednorazowa autoryzacja OAuth 2.0 dla Google Drive i Gmail.
Uruchom ten skrypt raz: python google_auth.py
Zapisze token.json który będzie używany przez serwer.

Na Renderze: ustaw zmienną środowiskową GOOGLE_TOKEN_JSON z zawartością token.json.
"""

import json
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
    "https://www.googleapis.com/auth/contacts",            # pełny dostęp do kontaktów Google (odczyt + zapis)
    "https://www.googleapis.com/auth/analytics.readonly",  # GA4 Data API — raporty ruchu
]

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.json")


def _bootstrap_from_env():
    """Jeśli pliki nie istnieją, spróbuj załadować z env vars."""
    if not os.path.exists(TOKEN_FILE):
        token_json = os.environ.get("GOOGLE_TOKEN_JSON", "").strip()
        if token_json:
            try:
                # Waliduj JSON przed zapisem
                json.loads(token_json)
                with open(TOKEN_FILE, "w") as f:
                    f.write(token_json)
            except json.JSONDecodeError as e:
                import logging
                logging.getLogger(__name__).error("GOOGLE_TOKEN_JSON nieprawidłowy JSON: %s", e)

    if not os.path.exists(CREDENTIALS_FILE):
        creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "").strip()
        if creds_json:
            try:
                json.loads(creds_json)
                with open(CREDENTIALS_FILE, "w") as f:
                    f.write(creds_json)
            except json.JSONDecodeError as e:
                import logging
                logging.getLogger(__name__).error("GOOGLE_CREDENTIALS_JSON nieprawidłowy JSON: %s", e)


def get_credentials() -> Credentials:
    """Zwraca ważne credentials — odświeża token jeśli wygasł."""
    _bootstrap_from_env()

    creds = None

    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Błąd ładowania token.json: %s", e)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        elif os.path.exists(CREDENTIALS_FILE):
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        else:
            raise RuntimeError(
                "Brak Google credentials. Ustaw GOOGLE_TOKEN_JSON lub GOOGLE_CREDENTIALS_JSON."
            )

    return creds


if __name__ == "__main__":
    creds = get_credentials()
    print("Autoryzacja zakończona. Plik token.json zapisany.")
    print(f"Email: {creds.token}")
