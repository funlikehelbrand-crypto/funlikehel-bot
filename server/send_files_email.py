"""
Jednorazowy skrypt — wysyła pliki konfiguracyjne agentów na maila szkoły.
Po użyciu można usunąć.
"""

import base64
import sys
import os
from email.mime.text import MIMEText

sys.path.insert(0, os.path.dirname(__file__))

from googleapiclient.discovery import build
from google_auth import get_credentials

TO = "funlikehelbrand@gmail.com"
SUBJECT = "Pliki agentów Claude Code — do zainstalowania na drugim komputerze"

# --- Wczytaj pliki ---
BASE = os.path.dirname(os.path.dirname(__file__))

files_to_send = {
    ".claude/agents/tomek-agent.md": os.path.join(BASE, ".claude", "agents", "tomek-agent.md"),
    ".claude/agents/funlikehel-agent.md": os.path.join(BASE, ".claude", "agents", "funlikehel-agent.md"),
    "CLAUDE.md": os.path.join(BASE, "CLAUDE.md"),
}

body_parts = []
body_parts.append("""Cześć Alicja!

Ten mail zawiera pliki konfiguracyjne agentów Claude Code.
Trzeba je skopiować na drugi komputer, żeby agenty działały.

=== INSTRUKCJA ===

Na drugim komputerze, w folderze projektu funlikehel/, utwórz taką strukturę:

funlikehel/
├── .claude/
│   └── agents/
│       ├── tomek-agent.md      (plik nr 1 poniżej)
│       └── funlikehel-agent.md (plik nr 2 poniżej)
└── CLAUDE.md                   (plik nr 3 poniżej)

Kroki:
1. W folderze projektu utwórz folder: .claude/agents/
2. Skopiuj zawartość każdego pliku poniżej do odpowiedniego pliku
3. Gotowe — agenty będą działać po uruchomieniu Claude Code

=== PLIKI ===
""")

for i, (rel_path, abs_path) in enumerate(files_to_send.items(), 1):
    with open(abs_path, "r", encoding="utf-8") as f:
        content = f.read()
    body_parts.append(f"""
{'='*60}
PLIK {i}: {rel_path}
{'='*60}

{content}
""")

body_parts.append("""
=== KONIEC ===

Pozdrawiam,
Claude Code
""")

full_body = "\n".join(body_parts)

# --- Wyślij ---
creds = get_credentials()
service = build("gmail", "v1", credentials=creds)

message = MIMEText(full_body, "plain", "utf-8")
message["to"] = TO
message["subject"] = SUBJECT
raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

result = service.users().messages().send(
    userId="me",
    body={"raw": raw},
).execute()

print(f"Email wysłany! Message ID: {result['id']}")
