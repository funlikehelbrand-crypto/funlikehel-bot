"""
SurfIQ — English Narrator Video Generator
~2:30 min presentation with edge-tts voiceover + screenshots + transitions

Usage: python generate_video_en.py
Output: SurfIQ_EN_Prezentacja.mp4 in the same folder
"""

import asyncio
import os
import subprocess
import sys
import textwrap
from pathlib import Path

# ──────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────
BASE = Path("C:/Users/ŁukaszMichalina/Funlikehel/surfiq-landing/assets")
SCREENS = BASE / "screenshots" / "final"
VIDEO_DIR = BASE / "video"
AUDIO_DIR = VIDEO_DIR / "audio_en"
SLIDES_DIR = VIDEO_DIR / "slides_en"
LOGO = BASE / "surfiq_correct_logo_full_white_bg.png"
OUTPUT = VIDEO_DIR / "SurfIQ_EN_Prezentacja.mp4"

AUDIO_DIR.mkdir(parents=True, exist_ok=True)
SLIDES_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────
# NARRATOR SCRIPT  (English, ~2:30 min)
# Each segment: (id, duration_sec, screenshot_file, narrator_text, overlay_lines)
# ──────────────────────────────────────────
SEGMENTS = [
    {
        "id": "00_hook",
        "duration": 18,
        "screenshot": SCREENS / "weather_dark.png",
        "text": (
            "It's six in the morning. Wind forecast shows eighteen knots from the southwest. "
            "You have twelve lessons scheduled, three instructors on the beach, "
            "and a client who just messaged asking if they can come for a kite session today. "
            "You open one panel. You see everything. "
            "The decision takes ten seconds. "
            "This is SurfIQ."
        ),
        "overlay": ["6 AM. 18 knots.", "One panel. Ten seconds.", "This is SurfIQ."],
    },
    {
        "id": "01_problem",
        "duration": 20,
        "screenshot": SCREENS / "calendar_dark.png",
        "text": (
            "If you run a kite, windsurf, or SUP school — you know the chaos. "
            "Bookings in spreadsheets. Weather across three browser tabs. "
            "Instructor schedules in your head. "
            "A client calls — you have no idea how many hours they had last year. "
            "Finances? You figure it out later. "
            "Every water sports school depends on the weather. "
            "And no existing booking system understands that. "
            "SurfIQ was built on the beach — by people who run a school "
            "and know that wind changes everything."
        ),
        "overlay": ["Spreadsheets? Three weather tabs?", "Built ON the beach.", "Wind changes everything."],
    },
    {
        "id": "02_dashboard",
        "duration": 20,
        "screenshot": SCREENS / "dashboard_dark.png",
        "text": (
            "The SurfIQ dashboard is your morning briefing in ten seconds. "
            "Weather from three sources — Windguru, Windy, and Windfinder — side by side. "
            "Temperature, wave height, wind direction. "
            "How many lessons today, how many instructors active, what revenue. "
            "Eight cards — everything you need to know before you step onto the beach."
        ),
        "overlay": ["Dashboard — 10 seconds, you know everything.", "3 weather sources | Lessons | Revenue | AI"],
    },
    {
        "id": "03_weather",
        "duration": 18,
        "screenshot": SCREENS / "weather_dark.png",
        "text": (
            "In no other industry does weather have such a direct impact on the schedule. "
            "That is why SurfIQ has a built-in weather module — "
            "not on a separate tab, not in a separate app. "
            "Three forecasts side by side, updated live. "
            "Wind speed, direction, gusts, wave height, and air temperature — "
            "all the data your instructors need, in one place."
        ),
        "overlay": ["Windguru + Windy + Windfinder", "Live. In one view."],
    },
    {
        "id": "04_mewia",
        "duration": 18,
        "screenshot": SCREENS / "mewia_dark.png",
        "text": (
            "Introducing MEWIA — the Multi-spot Engine with Wind Intelligence. "
            "MEWIA automatically analyses wind direction and recommends the optimal spot for each session. "
            "Wind from the north? MEWIA suggests transferring to the other side of the peninsula. "
            "Wind from the south? Stay on the bay. "
            "When conditions change, the Wind Alert notifies instructors instantly — "
            "so they never need to keep refreshing a weather app."
        ),
        "overlay": ["MEWIA — automatic spot selection", "Wind Alert — you hear it first."],
    },
    {
        "id": "05_bookings",
        "duration": 20,
        "screenshot": SCREENS / "bookings_dark.png",
        "text": (
            "Bookings in SurfIQ are not just a form. "
            "The system understands what a two-hour beginner kite course actually means. "
            "Create a booking in three clicks — sport, time slot, instructor. "
            "The system checks availability, weather suitability, and conflicts automatically. "
            "A drag-and-drop calendar with colour-coded sports. "
            "One glance tells you who is where, and when. "
            "Two thousand two hundred bookings handled in a single season — "
            "zero double bookings."
        ),
        "overlay": ["3 clicks = new booking", "Drag & drop | No conflicts", "2,228 bookings in one season"],
    },
    {
        "id": "06_calendar",
        "duration": 15,
        "screenshot": SCREENS / "calendar_dark.png",
        "text": (
            "The calendar view gives you the full picture of your week. "
            "Colour-coded by sport — blue for kite, green for windsurf, purple for SUP. "
            "Switch between day, week, and month views. "
            "Move sessions with a single drag. "
            "Your entire schedule, always under control."
        ),
        "overlay": ["Weekly calendar", "Colour-coded by sport | Drag to move"],
    },
    {
        "id": "07_ai_agent",
        "duration": 22,
        "screenshot": SCREENS / "inbox_dark.png",
        "text": (
            "It is eleven at night. You are home. "
            "A client from Warsaw messages on Instagram asking about kite course prices. "
            "A WhatsApp message comes in about weekend availability. "
            "An email arrives with a group booking request for eight people. "
            "SurfIQ AI Agent handles all of these — automatically, in under two minutes. "
            "It knows your pricing, availability, and locations. "
            "It qualifies the lead — sport, level, travel dates — and directs them to book. "
            "Six channels: Instagram, Facebook, WhatsApp, email, SMS, and TikTok. "
            "Twenty-four hours a day. "
            "You sleep. AI sells."
        ),
        "overlay": ["11 PM — client writes. AI replies.", "Under 2 min | 6 channels | 24/7", "You sleep. AI sells."],
    },
    {
        "id": "08_finances",
        "duration": 20,
        "screenshot": SCREENS / "finances_dark.png",
        "text": (
            "The season was good — but exactly how good? "
            "Which sport brought the most revenue? Who has an outstanding balance? "
            "The SurfIQ finance module answers all of this — "
            "without an accountant, without a spreadsheet. "
            "Daily, weekly, and seasonal revenue. "
            "Overdue payments highlighted in red. "
            "Breakdown by sport, instructor, and location. "
            "Three hundred and twenty-one thousand Polish zloty "
            "processed through the system in a single season. "
            "One-click export to PDF and CSV."
        ),
        "overlay": ["321,000 PLN processed in one season", "Overdue | Breakdown | PDF export"],
    },
    {
        "id": "09_crm",
        "duration": 16,
        "screenshot": SCREENS / "people_dark.png",
        "text": (
            "Eight hundred and twenty-four students in the database — "
            "each with a full history: lessons, PZKite and IKO certifications, "
            "instructor notes, and payment records. "
            "When a client returns a year later, you see everything at a glance. "
            "No digging through spreadsheets. No guessing. "
            "Just a complete picture of every student."
        ),
        "overlay": ["824 students. Full history.", "Lessons | Certificates | Notes"],
    },
    {
        "id": "10_reports",
        "duration": 14,
        "screenshot": SCREENS / "reports_dark.png",
        "text": (
            "Detailed reports and analytics give you the insights to run a smarter school. "
            "Revenue trends, instructor performance, most popular sports, peak booking hours. "
            "Everything you need to make data-driven decisions — "
            "not gut-feel ones."
        ),
        "overlay": ["Reports & Analytics", "Data-driven decisions."],
    },
    {
        "id": "11_cta",
        "duration": 18,
        "screenshot": LOGO,
        "text": (
            "SurfIQ. The operating system for water sports schools. "
            "Built by a school. Tested on one thousand students. "
            "Ready for yours. "
            "Fourteen days free. No credit card. No commitment. "
            "Just you and your panel. "
            "surfiq dot eu. "
            "Smarter schools. Better waves."
        ),
        "overlay": ["14 days free", "surfiq.eu", "Smarter schools. Better waves."],
    },
]

# ──────────────────────────────────────────
# STEP 1 — Generate voiceover with edge-tts
# ──────────────────────────────────────────
VOICE = "en-US-GuyNeural"   # Professional male US English

async def generate_tts():
    try:
        import edge_tts
    except ImportError:
        print("Installing edge-tts...")
        subprocess.run([sys.executable, "-m", "pip", "install", "edge-tts", "-q"], check=True)
        import edge_tts

    print(f"\n[TTS] Generating voiceover with voice: {VOICE}")
    for seg in SEGMENTS:
        out_file = AUDIO_DIR / f"vo_{seg['id']}.mp3"
        if out_file.exists():
            print(f"  [skip] {out_file.name} already exists")
            continue
        print(f"  Generating {out_file.name} ...")
        communicate = edge_tts.Communicate(
            seg["text"],
            VOICE,
            rate="-5%",   # slightly slower for clarity
            pitch="-3Hz"  # slightly lower, professional tone
        )
        await communicate.save(str(out_file))
        print(f"  Done: {out_file.name}")


# ──────────────────────────────────────────
# STEP 2 — Build slides with Pillow (screenshot + navy overlay + text)
# ──────────────────────────────────────────
NAVY  = (8, 29, 58)        # #081D3A
TURQ  = (20, 209, 201)     # #14D1C9
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

W, H = 1920, 1080

def build_slide(seg_id: str, screenshot_path: Path, overlay_lines: list[str]) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    out_path = SLIDES_DIR / f"slide_{seg_id}.png"
    if out_path.exists():
        print(f"  [skip] {out_path.name} already exists")
        return out_path

    print(f"  Building slide {out_path.name} ...")

    # ---- base: screenshot or fallback navy background ----
    if screenshot_path.exists():
        base = Image.open(screenshot_path).convert("RGBA")
        base = base.resize((W, H), Image.LANCZOS)
    else:
        print(f"    WARNING: screenshot not found: {screenshot_path}, using navy background")
        base = Image.new("RGBA", (W, H), (*NAVY, 255))

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.paste(base, (0, 0))

    # ---- bottom overlay bar ----
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    bar_h = 140
    bar_y = H - bar_h
    draw_ov.rectangle([(0, bar_y), (W, H)], fill=(*NAVY, 210))
    # turquoise accent line
    draw_ov.rectangle([(0, bar_y), (W, bar_y + 4)], fill=(*TURQ, 255))

    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    # ---- try to load a font, fall back to default ----
    font_large = None
    font_small = None
    font_paths = [
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                from PIL import ImageFont
                font_large = ImageFont.truetype(fp, 36)
                font_small = ImageFont.truetype(fp, 28)
                break
            except Exception:
                pass

    if font_large is None:
        from PIL import ImageFont
        font_large = ImageFont.load_default()
        font_small = font_large

    # ---- render overlay lines ----
    if overlay_lines:
        # First line in turquoise (larger), rest in white (smaller)
        y_pos = bar_y + 18
        for i, line in enumerate(overlay_lines):
            font = font_large if i == 0 else font_small
            color = TURQ if i == 0 else WHITE
            draw.text((40, y_pos), line, fill=color, font=font)
            y_pos += (font_large.size + 10) if i == 0 else (font_small.size + 8)

    # ---- SurfIQ logo watermark (top-right) ----
    if LOGO.exists():
        try:
            logo_img = Image.open(LOGO).convert("RGBA")
            logo_w, logo_h = logo_img.size
            target_h = 50
            ratio = target_h / logo_h
            logo_img = logo_img.resize((int(logo_w * ratio), target_h), Image.LANCZOS)
            # slight transparency
            r, g, b, a = logo_img.split()
            a = a.point(lambda p: int(p * 0.85))
            logo_img = Image.merge("RGBA", (r, g, b, a))
            lx = W - logo_img.width - 30
            ly = 20
            canvas.paste(logo_img, (lx, ly), logo_img)
        except Exception as e:
            print(f"    Logo paste skipped: {e}")

    # save as PNG
    canvas.convert("RGB").save(str(out_path), "PNG")
    return out_path


def build_all_slides():
    print("\n[SLIDES] Building slide images ...")
    for seg in SEGMENTS:
        build_slide(seg["id"], seg["screenshot"], seg["overlay"])


# ──────────────────────────────────────────
# STEP 3 — get audio duration via ffprobe
# ──────────────────────────────────────────
def get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 5.0


# ──────────────────────────────────────────
# STEP 4 — assemble video with ffmpeg
# ──────────────────────────────────────────
def build_video():
    print("\n[VIDEO] Assembling final video ...")

    segment_files = []

    for seg in SEGMENTS:
        seg_id = seg["id"]
        slide_path = SLIDES_DIR / f"slide_{seg_id}.png"
        audio_path = AUDIO_DIR / f"vo_{seg_id}.mp3"

        if not slide_path.exists():
            print(f"  ERROR: slide missing: {slide_path}")
            continue
        if not audio_path.exists():
            print(f"  ERROR: audio missing: {audio_path}")
            continue

        duration = get_audio_duration(audio_path)
        # add 0.8s padding after speech
        total_duration = duration + 0.8

        seg_video = SLIDES_DIR / f"seg_{seg_id}.mp4"
        segment_files.append(seg_video)

        print(f"  [{seg_id}] audio={duration:.1f}s  total={total_duration:.1f}s")

        # Build segment: still image + audio, fade in/out
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(slide_path),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-t", str(total_duration),
            # subtle zoom-in Ken Burns effect
            "-vf", f"scale=1920:1080,zoompan=z='min(zoom+0.0005,1.05)':d={int(total_duration*25)}:s=1920x1080:fps=25,"
                   f"fade=t=in:st=0:d=0.5,fade=t=out:st={total_duration-0.5}:d=0.5",
            "-shortest",
            str(seg_video),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            print(f"    ffmpeg error (see above)")

    # ---- concat all segments ----
    concat_file = VIDEO_DIR / "concat_en.txt"
    with open(concat_file, "w") as f:
        for sv in segment_files:
            if sv.exists():
                f.write(f"file '{str(sv).replace(chr(92), '/')}'\n")

    print(f"\n[VIDEO] Concatenating {len(segment_files)} segments -> {OUTPUT.name}")
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(OUTPUT),
    ]
    result = subprocess.run(cmd_concat, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode == 0:
        size_mb = OUTPUT.stat().st_size / (1024 * 1024)
        print(f"\n[DONE] Output: {OUTPUT.name}")
        print(f"       Size:   {size_mb:.1f} MB")
    else:
        print(f"[ERROR] concat failed (check ffmpeg output)")


# ──────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────
async def main():
    print("=" * 60)
    print(" SurfIQ - English Narrator Video Generator")
    print("=" * 60)

    # Step 1: TTS
    await generate_tts()

    # Step 2: Slides
    build_all_slides()

    # Step 3 + 4: Assemble video
    build_video()

    print("\nAll done.")


if __name__ == "__main__":
    asyncio.run(main())
