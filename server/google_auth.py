"""
Jednorazowa autoryzacja OAuth 2.0 dla Google Drive i Gmail.
Uruchom ten skrypt raz: python google_auth.py
Zapisze token.json który będzie używany przez serwer.

Na Renderze: ustaw zmienną środowiskową GOOGLE_TOKEN_JSON z zawartością token.json.
"""

import base64
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


def _decode_env_json(raw: str):
    """Dekoduj env var — próbuje raw JSON, potem base64, potem z czyszczeniem."""
    s = raw.strip()
    if not s:
        return None
    # 1) Spróbuj raw JSON
    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        pass
    # 2) Spróbuj base64
    try:
        decoded = base64.b64decode(s).decode("utf-8")
        json.loads(decoded)
        return decoded
    except Exception:
        pass
    # 3) Wyczyść cudzysłowy/BOM i spróbuj ponownie
    s = s.lstrip("\ufeff")
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        s = s[1:-1]
    try:
        json.loads(s)
        return s
    except json.JSONDecodeError:
        pass
    return None


def _bootstrap_from_env():
    """Jeśli pliki nie istnieją, spróbuj załadować z env vars."""
    import logging
    log = logging.getLogger(__name__)

    if not os.path.exists(TOKEN_FILE):
        token_raw = os.environ.get("GOOGLE_TOKEN_JSON", "")
        token_json = _decode_env_json(token_raw)
        if token_json:
            with open(TOKEN_FILE, "w") as f:
                f.write(token_json)
            log.info("token.json utworzony z env var (%d bytes)", len(token_json))
        elif token_raw.strip():
            log.error("GOOGLE_TOKEN_JSON nieprawidłowy (len=%d)", len(token_raw))

    if not os.path.exists(CREDENTIALS_FILE):
        creds_raw = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
        creds_json = _decode_env_json(creds_raw)
        if creds_json:
            with open(CREDENTIALS_FILE, "w") as f:
                f.write(creds_json)
            log.info("credentials.json utworzony z env var (%d bytes)", len(creds_json))
        elif creds_raw.strip():
            log.error("GOOGLE_CREDENTIALS_JSON nieprawidłowy (len=%d)", len(creds_raw))


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
        import logging as _log
        _log.getLogger(__name__).info(
            "Token state — creds=%s valid=%s expired=%s has_refresh=%s",
            bool(creds), getattr(creds, "valid", None),
            getattr(creds, "expired", None), bool(getattr(creds, "refresh_token", None))
        )
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(TOKEN_FILE, "w") as f:
                    f.write(creds.to_json())
            except Exception as refresh_err:
                _log.getLogger(__name__).error("Token refresh failed: %s", refresh_err)
                raise RuntimeError(f"Token refresh failed: {refresh_err}")
        elif os.path.exists(CREDENTIALS_FILE):
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        else:
            raise RuntimeError(
                f"Brak Google credentials. creds={bool(creds)} "
                f"expired={getattr(creds,'expired',None)} "
                f"refresh_token={bool(getattr(creds,'refresh_token',None))}"
            )

    return creds


if __name__ == "__main__":
    creds = get_credentials()
    print("Autoryzacja zakończona. Plik token.json zapisany.")
    print(f"Email: {creds.token}")
