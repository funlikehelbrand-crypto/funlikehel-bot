"""
Pobieranie kontaktów z Google Contacts (People API).
Zwraca kontakty z numerami telefonów — bazę klientów do SMS-ów.
"""

import logging
from googleapiclient.discovery import build
from google_auth import get_credentials

logger = logging.getLogger(__name__)


def get_contacts_with_phones(label: str = None) -> list[dict]:
    """
    Pobiera wszystkie kontakty Google z numerami telefonów.

    label — opcjonalnie filtruje po etykiecie/grupie (np. "Klienci FUN like HEL")
    Zwraca listę: [{"name": "Jan Kowalski", "phone": "48600000000", "email": "..."}, ...]
    """
    creds = get_credentials()
    service = build("people", "v1", credentials=creds, cache_discovery=False)

    contacts = []
    page_token = None

    while True:
        kwargs = {
            "resourceName": "people/me",
            "pageSize": 1000,
            "personFields": "names,phoneNumbers,emailAddresses,memberships",
        }
        if page_token:
            kwargs["pageToken"] = page_token

        result = service.people().connections().list(**kwargs).execute()
        connections = result.get("connections", [])

        for person in connections:
            phones = person.get("phoneNumbers", [])
            if not phones:
                continue  # pomijamy kontakty bez telefonu

            # Imię i nazwisko
            names = person.get("names", [])
            name = names[0].get("displayName", "") if names else ""

            # Email
            emails = person.get("emailAddresses", [])
            email = emails[0].get("value", "") if emails else ""

            # Etykiety/grupy
            memberships = person.get("memberships", [])
            group_names = [
                m.get("contactGroupMembership", {}).get("contactGroupResourceName", "")
                for m in memberships
            ]

            for phone_entry in phones:
                phone_raw = phone_entry.get("value", "")
                phone = _normalize_phone(phone_raw)
                if phone:
                    contacts.append({
                        "name": name,
                        "phone": phone,
                        "email": email,
                        "groups": group_names,
                    })

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    # Filtruj po etykiecie jeśli podana
    if label:
        contacts = _filter_by_label(service, contacts, label)

    logger.info("Pobrano %d kontaktów z numerami telefonów", len(contacts))
    return contacts


def _filter_by_label(service, contacts: list[dict], label: str) -> list[dict]:
    """Filtruje kontakty po nazwie grupy/etykiety."""
    # Pobierz wszystkie grupy kontaktów
    groups_result = service.contactGroups().list().execute()
    groups = groups_result.get("contactGroups", [])

    # Znajdź resource name grupy o podanej nazwie
    target_resource = None
    for group in groups:
        if group.get("name", "").lower() == label.lower() or \
           group.get("formattedName", "").lower() == label.lower():
            target_resource = group.get("resourceName", "")
            break

    if not target_resource:
        logger.warning("Nie znaleziono grupy '%s' w Google Contacts", label)
        return contacts  # zwróć wszystkie jeśli nie znaleziono

    filtered = [c for c in contacts if target_resource in c.get("groups", [])]
    logger.info("Po filtrze '%s': %d kontaktów", label, len(filtered))
    return filtered


def _normalize_phone(phone: str) -> str:
    """Normalizuje numer do formatu 48XXXXXXXXX."""
    phone = phone.strip().replace(" ", "").replace("-", "").replace("+", "")
    if not phone:
        return ""
    if len(phone) == 9 and phone.isdigit():
        phone = "48" + phone
    # Akceptuj numery z kodem Polski lub bez
    if len(phone) >= 9:
        return phone
    return ""
