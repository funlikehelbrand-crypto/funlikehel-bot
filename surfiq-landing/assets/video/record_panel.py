"""
SurfIQ — Screen recording of live panel via Playwright (headless)
Records browser navigating through all modules, then merges with English narration.
"""

import time
import subprocess
import sys
import asyncio
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path("C:/Users/ŁukaszMichalina/Funlikehel/surfiq-landing/assets/video")
RECORDING_DIR = BASE / "recording"
RECORDING_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR = BASE / "audio_en"
OUTPUT = BASE / "SurfIQ_Panel_Demo.mp4"

PANEL_URL = "https://panel.funlikehel.pl"
EMAIL = "funlikehelbrand@gmail.com"
PASSWORD = "Sebastian10"

# Sections: (name, selector_text, wait_sec, scroll)
SECTIONS = [
    ("Dashboard", None, 5, True),
    ("Grafik", "Grafik", 5, True),
    ("Rezerwacje", "Rezerwacje", 5, True),
    ("Ludzie", "Ludzie", 5, True),
    ("Pogoda", "Pogoda", 5, False),
    ("Finanse", "Finanse", 5, True),
    ("Usługi", "Usługi", 4, True),
    ("Płatności", "Płatności", 4, True),
    ("Sprzęt", "Sprzęt", 4, True),
    ("Sklep", "Sklep", 4, True),
    ("Raporty", "Raporty", 5, True),
    ("Obozy", "Obozy", 4, True),
    ("Ustawienia", "Ustawienia", 3, False),
]


def record():
    print("=" * 60)
    print(" SurfIQ — Panel Screen Recording (headless)")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu"]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(RECORDING_DIR),
            record_video_size={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        # ---- LOGIN ----
        print("\n[1/3] Logging in...")
        page.goto(PANEL_URL, timeout=30000)
        time.sleep(8)  # wait for SPA to render

        # Try to find and fill login form
        try:
            # Look for email input
            inputs = page.locator('input')
            count = inputs.count()
            print(f"  Found {count} inputs")

            if count >= 2:
                inputs.nth(0).fill(EMAIL)
                time.sleep(0.3)
                inputs.nth(1).fill(PASSWORD)
                time.sleep(0.3)

                # Try submit button
                btns = page.locator('button, [role="button"]')
                for i in range(btns.count()):
                    btn = btns.nth(i)
                    txt = btn.inner_text()
                    if any(w in txt.lower() for w in ['zaloguj', 'log in', 'sign in', 'submit']):
                        btn.click()
                        print(f"  Clicked: {txt}")
                        break
                else:
                    page.keyboard.press("Enter")
                    print("  Pressed Enter")

                time.sleep(8)  # wait for dashboard
                print("  Logged in!")
            else:
                print("  No login form, maybe already in?")
                time.sleep(3)
        except Exception as e:
            print(f"  Login error: {e}")
            time.sleep(3)

        # Screenshot to verify
        page.screenshot(path=str(RECORDING_DIR / "verify_login.png"))
        print(f"  Verify screenshot saved")

        # ---- NAVIGATE SECTIONS ----
        print("\n[2/3] Navigating sections...")
        for name, selector, wait, scroll in SECTIONS:
            if selector is None:
                print(f"  [{name}] Already here (dashboard)")
                time.sleep(wait)
                if scroll:
                    page.evaluate("window.scrollBy({top: 400, behavior: 'smooth'})")
                    time.sleep(1.5)
                    page.evaluate("window.scrollBy({top: -400, behavior: 'smooth'})")
                    time.sleep(1)
                continue

            try:
                print(f"  [{name}] Clicking '{selector}'...")
                # Try multiple selectors
                clicked = False
                for sel in [
                    f'a:has-text("{selector}")',
                    f'div[role="link"]:has-text("{selector}")',
                    f'text="{selector}"',
                    f'[data-testid*="{selector.lower()}"]',
                ]:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible(timeout=2000):
                            el.click()
                            clicked = True
                            break
                    except:
                        continue

                if not clicked:
                    # Last resort - click any element containing text
                    page.click(f'text={selector}', timeout=3000)

                time.sleep(wait)

                if scroll:
                    page.evaluate("window.scrollBy({top: 400, behavior: 'smooth'})")
                    time.sleep(1.5)
                    page.evaluate("window.scrollBy({top: -400, behavior: 'smooth'})")
                    time.sleep(1)

                print(f"    OK: {name}")
            except Exception as e:
                print(f"    Skip {name}: {e}")

        # Back to dashboard
        print("\n  Back to dashboard...")
        try:
            page.click('text=Dashboard', timeout=3000)
        except:
            try:
                page.click('text=Strona', timeout=3000)
            except:
                pass
        time.sleep(3)

        # ---- CLOSE & SAVE ----
        print("\n[3/3] Saving recording...")
        video_path = page.video.path()
        page.close()
        context.close()
        browser.close()

    print(f"\n  Raw video: {video_path}")
    return Path(video_path)


def merge_with_narration(raw_video: Path):
    """Merge raw panel recording with existing English narration audio."""
    print("\n[MERGE] Combining recording with narration...")

    # First concat all narration audio
    audio_files = sorted(AUDIO_DIR.glob("vo_*.mp3"))
    if not audio_files:
        print("  No narration audio found! Skipping merge.")
        # Just convert webm to mp4
        subprocess.run([
            "ffmpeg", "-y", "-i", str(raw_video),
            "-c:v", "libx264", "-c:a", "aac",
            "-movflags", "+faststart",
            str(OUTPUT)
        ], capture_output=True)
        return

    # Concat all narration into one file
    narration_concat = BASE / "narration_full.txt"
    narration_mp3 = BASE / "narration_full.mp3"

    with open(narration_concat, "w") as f:
        for af in audio_files:
            f.write(f"file '{af.name}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(narration_concat),
        "-c:a", "libmp3lame", "-b:a", "128k",
        str(narration_mp3)
    ], capture_output=True, cwd=str(AUDIO_DIR))
    print(f"  Narration: {narration_mp3}")

    # Get durations
    def get_duration(f):
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(f)],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        try:
            return float(r.stdout.strip())
        except:
            return 0

    vid_dur = get_duration(raw_video)
    nar_dur = get_duration(narration_mp3)
    print(f"  Video: {vid_dur:.1f}s, Narration: {nar_dur:.1f}s")

    # Merge: video + narration audio (speed up/slow down video to match narration)
    if vid_dur > 0 and nar_dur > 0:
        speed = vid_dur / nar_dur
        print(f"  Speed factor: {speed:.2f}x")

        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(raw_video),
            "-i", str(narration_mp3),
            "-filter_complex",
            f"[0:v]setpts={1/speed}*PTS[v]",
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            str(OUTPUT)
        ], capture_output=True, text=True, encoding="utf-8", errors="replace")
    else:
        # fallback: just overlay
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(raw_video),
            "-i", str(narration_mp3),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-c:a", "aac",
            "-shortest", "-movflags", "+faststart",
            str(OUTPUT)
        ], capture_output=True)

    if OUTPUT.exists():
        size_mb = OUTPUT.stat().st_size / (1024 * 1024)
        dur = get_duration(OUTPUT)
        print(f"\n[DONE] {OUTPUT.name}")
        print(f"  Size: {size_mb:.1f} MB")
        print(f"  Duration: {dur:.0f}s")
    else:
        print("[ERROR] Output not created")


if __name__ == "__main__":
    raw = record()
    if raw and raw.exists():
        merge_with_narration(raw)
