"""
fb_publisher.py — publikuje posty na stronie Facebook Fun Like Hel przez Graph API.

Użycie:
    python fb_publisher.py --text "Treść posta"
    python fb_publisher.py --text "Treść" --link "https://funlikehel.pl"
    python fb_publisher.py --text "Treść" --image "/sciezka/do/zdjecia.jpg"
    python fb_publisher.py --dry-run --text "Treść"   # tylko podgląd

Import jako moduł:
    from fb_publisher import publish_post
    result = publish_post(text="Cześć!", link="https://funlikehel.pl")
"""

import argparse
import os
import sys
import requests
import logging

sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fb_publisher")

# ── Konfiguracja ──────────────────────────────────────────────────────────────

def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api.env")
    env = {}
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env

_ENV = _load_env()
PAGE_ID    = _ENV.get("FB_PAGE_ID", "763267196880291")
PAGE_TOKEN = _ENV.get("PAGE_ACCESS_TOKEN", "")
GRAPH_URL  = "https://graph.facebook.com/v25.0"


# ── Publikowanie tekstu (z opcjonalnym linkiem) ───────────────────────────────

def publish_post(text: str, link: str = None, dry_run: bool = False) -> dict:
    """
    Publikuje post tekstowy na stronie Fun Like Hel.
    Zwraca dict: {"success": True, "post_id": "...", "url": "..."} lub {"success": False, "error": "..."}
    """
    if not PAGE_TOKEN:
        return {"success": False, "error": "Brak PAGE_ACCESS_TOKEN w api.env"}

    payload = {"message": text, "access_token": PAGE_TOKEN}
    if link:
        payload["link"] = link

    if dry_run:
        log.info(f"[DRY-RUN] Publikacja posta:\n  Tekst: {text[:100]}...\n  Link: {link}")
        return {"success": True, "post_id": "dry-run", "url": None}

    r = requests.post(f"{GRAPH_URL}/{PAGE_ID}/feed", data=payload)
    result = r.json()

    if "id" in result:
        post_id = result["id"]
        url = f"https://www.facebook.com/{post_id.replace('_', '/posts/')}"
        log.info(f"Post opublikowany! ID: {post_id} | URL: {url}")
        return {"success": True, "post_id": post_id, "url": url}
    else:
        error = result.get("error", {}).get("message", str(result))
        log.error(f"Błąd publikacji: {error}")
        return {"success": False, "error": error}


# ── Publikowanie ze zdjęciem ──────────────────────────────────────────────────

def publish_post_with_image(text: str, image_path: str = None, image_url: str = None, dry_run: bool = False) -> dict:
    """
    Publikuje post ze zdjęciem. Podaj image_path (plik lokalny) lub image_url (URL).
    """
    if not PAGE_TOKEN:
        return {"success": False, "error": "Brak PAGE_ACCESS_TOKEN w api.env"}

    if dry_run:
        log.info(f"[DRY-RUN] Post ze zdjęciem:\n  Tekst: {text[:100]}\n  Zdjęcie: {image_path or image_url}")
        return {"success": True, "post_id": "dry-run", "url": None}

    # Krok 1: wgraj zdjęcie
    if image_path:
        with open(image_path, "rb") as f:
            r = requests.post(
                f"{GRAPH_URL}/{PAGE_ID}/photos",
                data={"caption": text, "published": "true", "access_token": PAGE_TOKEN},
                files={"source": f}
            )
    elif image_url:
        r = requests.post(
            f"{GRAPH_URL}/{PAGE_ID}/photos",
            data={"caption": text, "url": image_url, "published": "true", "access_token": PAGE_TOKEN}
        )
    else:
        return {"success": False, "error": "Podaj image_path lub image_url"}

    result = r.json()
    if "id" in result:
        post_id = result.get("post_id") or result["id"]
        log.info(f"Post ze zdjęciem opublikowany! ID: {post_id}")
        return {"success": True, "post_id": post_id, "url": f"https://www.facebook.com/{PAGE_ID}"}
    else:
        error = result.get("error", {}).get("message", str(result))
        log.error(f"Błąd publikacji ze zdjęciem: {error}")
        return {"success": False, "error": error}


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Publikuj post na stronie Fun Like Hel")
    parser.add_argument("--text",      required=True, help="Treść posta")
    parser.add_argument("--link",      default=None,  help="Opcjonalny link do dodania")
    parser.add_argument("--image",     default=None,  help="Ścieżka do zdjęcia (lokalny plik)")
    parser.add_argument("--image-url", default=None,  help="URL zdjęcia")
    parser.add_argument("--dry-run",   action="store_true", help="Tylko podgląd, nie publikuje")
    args = parser.parse_args()

    if args.image or args.image_url:
        result = publish_post_with_image(
            text=args.text,
            image_path=args.image,
            image_url=args.image_url,
            dry_run=args.dry_run
        )
    else:
        result = publish_post(text=args.text, link=args.link, dry_run=args.dry_run)

    if result["success"]:
        print(f"\nSukces! Post ID: {result['post_id']}")
        if result.get("url"):
            print(f"URL: {result['url']}")
    else:
        print(f"\nBłąd: {result['error']}")
        sys.exit(1)
