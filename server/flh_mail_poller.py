"""
FLH Mail Poller — polling info@funlikehel.pl via IMAP
Saves new emails to Supabase conversations + messages (panel Messages)
"""

import imaplib
import email
import email.header
import logging
import os
import re
from datetime import datetime

logger = logging.getLogger(__name__)

IMAP_HOST = "serwer2620595.home.pl"
IMAP_PORT = 993
IMAP_USER = "info@funlikehel.pl"
IMAP_PASS = os.environ.get("FLH_MAIL_PASS", "paulinamaja")

# Supabase sync
import requests as _req

_SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://pmkzzchckmpcmvtdhxwh.supabase.co")
_SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

IGNORED_SENDERS = [
    "noreply", "no-reply", "mailer-daemon", "postmaster",
    "dmarc", "bounce", "notifications@", "info@funlikehel.pl",
    "office@surfiq.eu", "funlikehelbrand@gmail.com",
    "fastmaildmarc", "yahoo.com/dmarc", "google.com/dmarc",
]


def _decode_header(raw):
    """Decode email header (handles encoded words)."""
    if not raw:
        return ""
    decoded = email.header.decode_header(raw)
    parts = []
    for data, charset in decoded:
        if isinstance(data, bytes):
            parts.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(data)
    return " ".join(parts)


def _extract_email(sender):
    """Extract email from 'Name <email>' format."""
    match = re.search(r'[\w.+-]+@[\w.-]+', sender or '')
    return match.group(0).lower() if match else sender.lower() if sender else ''


def _is_ignored(sender_email):
    """Check if sender should be ignored."""
    s = sender_email.lower()
    return any(ign in s for ign in IGNORED_SENDERS)


def _get_body(msg):
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")[:1000]
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")[:1000] if payload else ""
    return ""


def _sync_to_supabase(sender_email, sender_name, subject, body):
    """Save email to Supabase conversations + messages."""
    if not _SUPABASE_KEY:
        return
    try:
        h = {
            "apikey": _SUPABASE_KEY,
            "Authorization": f"Bearer {_SUPABASE_KEY}",
            "Content-Type": "application/json",
        }

        # Check if conversation exists
        r = _req.get(
            f"{_SUPABASE_URL}/rest/v1/conversations?contact_email=eq.{sender_email}&channel=eq.email&limit=1",
            headers={**h, "Prefer": "return=representation"},
        )

        now = datetime.utcnow().isoformat() + "Z"

        if r.status_code == 200 and r.json():
            conv_id = r.json()[0]["id"]
            _req.patch(
                f"{_SUPABASE_URL}/rest/v1/conversations?id=eq.{conv_id}",
                headers={**h, "Prefer": "return=minimal"},
                json={
                    "last_message_text": (body or "")[:200],
                    "last_message_at": now,
                    "status": "new",
                    "unread_count": r.json()[0].get("unread_count", 0) + 1,
                },
            )
        else:
            # Get tenant_id for FLH
            tr = _req.get(
                f"{_SUPABASE_URL}/rest/v1/tenants?slug=eq.funlikehel&select=id&limit=1",
                headers={**h, "Prefer": "return=representation"},
            )
            tenant_id = tr.json()[0]["id"] if tr.status_code == 200 and tr.json() else None

            conv_data = {
                "channel": "email",
                "contact_name": sender_name or sender_email.split("@")[0],
                "contact_email": sender_email,
                "status": "new",
                "unread_count": 1,
                "last_message_text": (body or "")[:200],
                "last_message_at": now,
                "tags": ["email", "info@funlikehel.pl"],
            }
            if tenant_id:
                conv_data["tenant_id"] = tenant_id

            r2 = _req.post(
                f"{_SUPABASE_URL}/rest/v1/conversations",
                headers={**h, "Prefer": "return=representation"},
                json=conv_data,
            )
            conv_id = r2.json()[0]["id"] if r2.status_code in (200, 201) and r2.json() else None

        if conv_id:
            msg_data = {
                "conversation_id": conv_id,
                "sender_type": "customer",
                "sender_name": sender_name or sender_email,
                "body": f"[{subject}]\n{body[:500]}",
                "delivery_status": "read",
            }
            # Get tenant_id
            tr = _req.get(
                f"{_SUPABASE_URL}/rest/v1/tenants?slug=eq.funlikehel&select=id&limit=1",
                headers={**h, "Prefer": "return=representation"},
            )
            if tr.status_code == 200 and tr.json():
                msg_data["tenant_id"] = tr.json()[0]["id"]

            _req.post(
                f"{_SUPABASE_URL}/rest/v1/messages",
                headers={**h, "Prefer": "return=minimal"},
                json=msg_data,
            )
            logger.info("[FLH Mail] Synced: %s | %s", sender_email, subject[:50])

    except Exception as e:
        logger.warning("[FLH Mail] Supabase sync failed: %s", e)


def poll_flh_inbox():
    """Poll info@funlikehel.pl for new unseen emails, sync to panel."""
    try:
        imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        imap.login(IMAP_USER, IMAP_PASS)
        imap.select("INBOX")

        # Get UNSEEN emails
        status, data = imap.search(None, "UNSEEN")
        if status != "OK" or not data[0]:
            logger.info("[FLH Mail] No new emails")
            imap.logout()
            return 0

        ids = data[0].split()
        logger.info("[FLH Mail] %d new emails", len(ids))

        synced = 0
        for mid in ids:
            try:
                status, msg_data = imap.fetch(mid, "(RFC822)")
                if status != "OK":
                    continue

                msg = email.message_from_bytes(msg_data[0][1])
                sender_raw = _decode_header(msg.get("From", ""))
                subject = _decode_header(msg.get("Subject", ""))
                sender_email = _extract_email(sender_raw)
                sender_name = sender_raw.split("<")[0].strip().strip('"') if "<" in sender_raw else sender_email

                if _is_ignored(sender_email):
                    logger.info("[FLH Mail] Ignored: %s", sender_email)
                    continue

                body = _get_body(msg)
                _sync_to_supabase(sender_email, sender_name, subject, body)
                synced += 1

            except Exception as e:
                logger.warning("[FLH Mail] Error processing email %s: %s", mid, e)

        imap.logout()
        return synced

    except Exception as e:
        logger.error("[FLH Mail] IMAP error: %s", e)
        return 0
