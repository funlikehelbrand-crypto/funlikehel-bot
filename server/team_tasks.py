"""
Team Tasks — przetwarzanie poleceń wewnętrznych od ekipy FUN like HEL.
Ekipa pisze maila na funlikehelbrand@gmail.com → bot parsuje → wykonuje zmianę → odpowiada.
"""

import json
import logging
import os
import re
from datetime import datetime

import anthropic
import requests
from dotenv import load_dotenv

load_dotenv("api.env")

logger = logging.getLogger(__name__)

# --- Config ---
WP_URL = "https://funlikehel.pl/wp-json/wp/v2"
WP_AUTH = ("Admin", "PDlm Q9wV AKvP tvlK uUEa 64zw")

TEAM_EMAILS = [
    "lukaszmichalina@gmail.com",
    "wojtekantosiewicz01@gmail.com",
    "alicja_al_chalabi@onet.pl",
    "madalenkiabramczyk@gmail.com",
]

# Strony WP — ID i nazwy
WP_PAGES = {
    "homepage": 1329,
    "oferta": 2033,
    "cennik": 3185,
    "team": 2189,
    "ekipa": 2189,
    "egipt": 2044,
    "hurghada": 2044,
    "jastarnia": 2182,
    "kontakt": 2042,
    "sklep": 2040,
    "obozy": 2037,
    "cabrinha": 2158,
}

claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

# --- Logi zadań ---
task_log = []


def is_team_member(email: str) -> bool:
    """Sprawdza czy nadawca jest członkiem ekipy."""
    return email.lower().strip() in TEAM_EMAILS


def process_team_email(sender: str, subject: str, body: str) -> str:
    """
    Główna funkcja — parsuje polecenie z maila i wykonuje zmianę.
    Zwraca tekst odpowiedzi do nadawcy.
    """
    sender_name = _get_team_name(sender)
    logger.info("TEAM TASK od %s (%s): %s", sender_name, sender, subject)

    # 1. Claude parsuje co trzeba zrobić
    task = _parse_task(sender_name, subject, body)

    if not task:
        return (
            f"Cześć {sender_name}!\n\n"
            "Nie udało mi się zrozumieć polecenia z Twojego maila. "
            "Opisz dokładniej co chcesz zmienić, np.:\n"
            "- \"Zmień cenę kite 2h na 600 zł na stronie cennik\"\n"
            "- \"Dodaj do opisu Magdy w team: lubi bieganie\"\n"
            "- \"Zmień tekst na stronie Egipt: zamiast X napisz Y\"\n\n"
            "Pozdrawiam,\nBot FLH"
        )

    # 2. Wykonaj zadanie
    result = _execute_task(task)

    # 3. Loguj
    task_log.append({
        "timestamp": datetime.now().isoformat(),
        "sender": sender,
        "subject": subject,
        "task": task,
        "result": result,
    })

    # 4. Odpowiedź
    return _format_reply(sender_name, task, result)


def _get_team_name(email: str) -> str:
    """Zwraca imię na podstawie emaila."""
    names = {
        "lukaszmichalina@gmail.com": "Łukasz",
        "wojtekantosiewicz01@gmail.com": "Wojtek",
        "alicja_al_chalabi@onet.pl": "Alicja",
        "madalenkiabramczyk@gmail.com": "Magda",
    }
    return names.get(email.lower().strip(), "Kolego/Koleżanko")


def _parse_task(sender_name: str, subject: str, body: str) -> dict | None:
    """Claude parsuje email i zwraca strukturę zadania."""
    prompt = f"""Jesteś asystentem szkoły FUN like HEL. Członek ekipy ({sender_name}) wysłał email z poleceniem.
Przeanalizuj treść i zwróć JSON z opisem zadania.

Email:
Temat: {subject}
Treść: {body[:2000]}

Zwróć TYLKO JSON (bez markdown):
{{
  "action": "edit_page" | "edit_price" | "add_member" | "edit_member" | "upload_photo" | "other",
  "page": "cennik" | "team" | "oferta" | "egipt" | "jastarnia" | "kontakt" | "homepage" | null,
  "description": "krótki opis co zmienić",
  "search_text": "tekst do znalezienia na stronie (jeśli edit_page)",
  "replace_text": "nowy tekst (jeśli edit_page)",
  "details": {{}}
}}

Jeśli nie da się sparsować polecenia, zwróć null.

Ważne:
- Dla edit_price: w details daj sport, pakiet, nowa_cena
- Dla edit_member: w details daj imie, pole (bio/role/hobby), nowa_wartosc
- Dla add_member: w details daj imie, rola, bio
- search_text i replace_text muszą być DOKŁADNE fragmenty HTML strony (z encjami HTML jeśli trzeba)"""

    try:
        response = claude_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Wyciągnij JSON
        if text.startswith("{"):
            return json.loads(text)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        logger.error("Błąd parsowania zadania: %s", e)
    return None


def _execute_task(task: dict) -> dict:
    """Wykonuje zadanie na WordPress."""
    action = task.get("action", "other")
    page = task.get("page")

    if action == "edit_page" and page:
        return _edit_wp_page(task)
    elif action == "edit_price" and page == "cennik":
        return _edit_wp_page(task)
    elif action in ("edit_member", "add_member") and page in ("team", "ekipa"):
        return _edit_wp_page(task)
    elif action == "other":
        return {
            "status": "manual",
            "message": f"Zadanie wymaga ręcznej interwencji: {task.get('description', '?')}",
        }
    else:
        return {
            "status": "unsupported",
            "message": f"Nie wiem jak wykonać akcję: {action} na stronie: {page}",
        }


def _edit_wp_page(task: dict) -> dict:
    """Edytuje stronę WP — znajduje tekst i podmienia."""
    page_slug = task.get("page", "")
    page_id = WP_PAGES.get(page_slug)

    if not page_id:
        return {"status": "error", "message": f"Nie znam strony: {page_slug}"}

    # Pobierz aktualną treść
    try:
        r = requests.get(
            f"{WP_URL}/pages/{page_id}",
            auth=WP_AUTH,
            params={"context": "edit", "_fields": "content"},
            timeout=15,
        )
        r.raise_for_status()
        current_content = r.json()["content"]["raw"]
    except Exception as e:
        return {"status": "error", "message": f"Nie mogę pobrać strony {page_slug}: {e}"}

    search = task.get("search_text", "")
    replace = task.get("replace_text", "")

    if not search or not replace:
        # Brak search/replace — użyj Claude do inteligentnej edycji
        return _smart_edit(page_id, page_slug, current_content, task)

    if search not in current_content:
        # Spróbuj fuzzy match
        return _smart_edit(page_id, page_slug, current_content, task)

    # Podmień
    new_content = current_content.replace(search, replace, 1)

    try:
        r = requests.post(
            f"{WP_URL}/pages/{page_id}",
            auth=WP_AUTH,
            json={"content": new_content},
            timeout=15,
        )
        r.raise_for_status()
        return {
            "status": "ok",
            "message": f"Strona '{page_slug}' zaktualizowana.",
            "page_url": f"https://funlikehel.pl/{page_slug}/",
            "change": f"Zamieniono: '{search[:80]}...' → '{replace[:80]}...'",
        }
    except Exception as e:
        return {"status": "error", "message": f"Błąd zapisu strony: {e}"}


def _smart_edit(page_id: int, page_slug: str, current_content: str, task: dict) -> dict:
    """Claude inteligentnie edytuje treść strony na podstawie opisu zadania."""
    description = task.get("description", "")
    details = task.get("details", {})

    # Daj Claude aktualną treść + polecenie
    prompt = f"""Jesteś asystentem edycji strony WordPress szkoły FUN like HEL.

AKTUALNA TREŚĆ STRONY (HTML):
{current_content[:6000]}

POLECENIE: {description}
SZCZEGÓŁY: {json.dumps(details, ensure_ascii=False)}

Wprowadź DOKŁADNIE tę zmianę w HTML i zwróć CAŁY zaktualizowany HTML.
Nie zmieniaj nic innego — tylko to co wynika z polecenia.
Zachowaj dokładnie ten sam format, style CSS, klasy, encje HTML.

Zwróć TYLKO HTML (bez markdown, bez ```):"""

    try:
        response = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        new_content = response.content[0].text.strip()

        # Walidacja — musi zawierać kluczowe elementy
        if "<style>" not in new_content and "<div" not in new_content:
            return {"status": "error", "message": "Claude zwrócił nieprawidłowy HTML"}

        # Zapisz na WP
        r = requests.post(
            f"{WP_URL}/pages/{page_id}",
            auth=WP_AUTH,
            json={"content": new_content},
            timeout=15,
        )
        r.raise_for_status()
        return {
            "status": "ok",
            "message": f"Strona '{page_slug}' zaktualizowana inteligentnie.",
            "page_url": f"https://funlikehel.pl/{page_slug}/",
            "change": description,
        }
    except Exception as e:
        return {"status": "error", "message": f"Błąd smart edit: {e}"}


def _format_reply(sender_name: str, task: dict, result: dict) -> str:
    """Formatuje odpowiedź mailową dla członka ekipy."""
    status = result.get("status", "error")

    if status == "ok":
        return (
            f"Cześć {sender_name}!\n\n"
            f"Zrobione! Oto co zmieniłem:\n\n"
            f"Zadanie: {task.get('description', '?')}\n"
            f"Strona: {result.get('page_url', '?')}\n"
            f"Zmiana: {result.get('change', '?')}\n\n"
            f"Sprawdź czy jest OK. Jeśli coś nie gra — odpisz co poprawić.\n\n"
            f"Pozdrawiam,\nBot FLH"
        )
    elif status == "manual":
        return (
            f"Cześć {sender_name}!\n\n"
            f"Rozumiem polecenie, ale nie mogę tego zrobić automatycznie:\n"
            f"{result.get('message', '?')}\n\n"
            f"Przekazuję Łukaszowi — zajmie się tym ręcznie.\n\n"
            f"Pozdrawiam,\nBot FLH"
        )
    else:
        return (
            f"Cześć {sender_name}!\n\n"
            f"Nie udało się wykonać zadania:\n"
            f"{result.get('message', 'nieznany błąd')}\n\n"
            f"Spróbuj opisać inaczej lub skontaktuj się z Łukaszem.\n\n"
            f"Pozdrawiam,\nBot FLH"
        )
