"""
SurfIQ — EN Video v2
- Screenshots change every ~5 seconds, matched to narration
- Official logo (logo_for_dark_bg.png) top-right
- 12 narration segments, multiple screenshots per segment
"""

import asyncio
import subprocess
import sys
import os
from pathlib import Path

BASE = Path("C:/Users/ŁukaszMichalina/Funlikehel/surfiq-landing/assets")
SCREENS = BASE / "screenshots" / "final"
MODS = BASE / "generated" / "modules"
GENS = BASE / "generated" / "v2"
PREM = BASE / "generated" / "premium"
VIDEO_DIR = BASE / "video"
AUDIO_DIR = VIDEO_DIR / "audio_en"
SLIDES_DIR = VIDEO_DIR / "slides_v2"
LOGO = BASE / "generated" / "logo_final" / "logo_for_dark_bg.png"
OUTPUT = VIDEO_DIR / "SurfIQ_EN_v3.mp4"

SLIDES_DIR.mkdir(parents=True, exist_ok=True)

# ── Screenshot sequence: each entry = (screenshot, duration_sec) ──
# Mapped to narration content, ~5s per screenshot
# Total should match narration length per segment

SEGMENTS = [
    {
        "id": "00_hook",
        "audio": AUDIO_DIR / "vo_00_hook.mp3",
        "shots": [
            (MODS / "mod_mewia.png", 5),
            (SCREENS / "dashboard_dark.png", 5),
            (MODS / "mod_calendar.png", 5),
            (MODS / "mod_ai.png", 5),
            (SCREENS / "dashboard_dark_zoom.png", 5),
        ],
    },
    {
        "id": "01_problem",
        "audio": AUDIO_DIR / "vo_01_problem.mp3",
        "shots": [
            (MODS / "mod_bookings.png", 5),
            (MODS / "mod_calendar.png", 5),
            (MODS / "mod_crm.png", 5),
            (MODS / "mod_equipment.png", 5),
            (MODS / "mod_finances.png", 5),
            (MODS / "mod_instructors.png", 5),
            (SCREENS / "dashboard_dark.png", 6),
        ],
    },
    {
        "id": "02_dashboard",
        "audio": AUDIO_DIR / "vo_02_dashboard.mp3",
        "shots": [
            (SCREENS / "dashboard_dark.png", 5),
            (SCREENS / "dashboard_dark_zoom.png", 5),
            (MODS / "mod_mewia.png", 5),
            (SCREENS / "dashboard_light.png", 5),
            (SCREENS / "dashboard_dark.png", 4),
        ],
    },
    {
        "id": "03_weather",
        "audio": AUDIO_DIR / "vo_03_weather.mp3",
        "shots": [
            (SCREENS / "weather_dark.png", 5),
            (MODS / "mod_mewia.png", 5),
            (SCREENS / "weather_light.png", 5),
            (SCREENS / "dashboard_dark_zoom.png", 5),
            (SCREENS / "weather_dark.png", 4),
        ],
    },
    {
        "id": "04_mewia",
        "audio": AUDIO_DIR / "vo_04_mewia.mp3",
        "shots": [
            (MODS / "mod_mewia.png", 5),
            (SCREENS / "mewia_dark.png", 5),
            (SCREENS / "mewia_light.png", 5),
            (MODS / "mod_mewia.png", 5),
            (SCREENS / "kitesafari_boats_dark.png", 5),
            (SCREENS / "mewia_dark.png", 5),
        ],
    },
    {
        "id": "05_bookings",
        "audio": AUDIO_DIR / "vo_05_bookings.mp3",
        "shots": [
            (MODS / "mod_bookings.png", 5),
            (SCREENS / "bookings_dark.png", 5),
            (MODS / "mod_calendar.png", 5),
            (SCREENS / "bookings_light.png", 5),
            (SCREENS / "services_dark.png", 5),
            (MODS / "mod_bookings.png", 5),
            (SCREENS / "calendar_dark.png", 3),
        ],
    },
    {
        "id": "06_calendar",
        "audio": AUDIO_DIR / "vo_06_calendar.mp3",
        "shots": [
            (MODS / "mod_calendar.png", 5),
            (SCREENS / "calendar_dark.png", 5),
            (SCREENS / "calendar_light.png", 5),
            (MODS / "mod_calendar.png", 5),
        ],
    },
    {
        "id": "07_ai_agent",
        "audio": AUDIO_DIR / "vo_07_ai_agent.mp3",
        "shots": [
            (MODS / "mod_ai.png", 5),
            (SCREENS / "inbox_dark.png", 5),
            (SCREENS / "inbox_light.png", 5),
            (MODS / "mod_ai.png", 5),
            (SCREENS / "inbox_dark.png", 5),
            (MODS / "mod_crm.png", 5),
            (SCREENS / "inbox_light.png", 5),
            (MODS / "mod_ai.png", 5),
            (SCREENS / "inbox_dark.png", 6),
        ],
    },
    {
        "id": "08_finances",
        "audio": AUDIO_DIR / "vo_08_finances.mp3",
        "shots": [
            (MODS / "mod_finances.png", 5),
            (SCREENS / "finances_dark.png", 5),
            (SCREENS / "reports_dark.png", 5),
            (MODS / "mod_finances.png", 5),
            (SCREENS / "finances_light.png", 5),
            (SCREENS / "reports_light.png", 5),
            (MODS / "mod_finances.png", 5),
        ],
    },
    {
        "id": "09_crm",
        "audio": AUDIO_DIR / "vo_09_crm.mp3",
        "shots": [
            (MODS / "mod_crm.png", 5),
            (SCREENS / "people_dark.png", 5),
            (MODS / "mod_instructors.png", 5),
            (SCREENS / "people_light.png", 5),
            (MODS / "mod_crm.png", 4),
        ],
    },
    {
        "id": "10_reports",
        "audio": AUDIO_DIR / "vo_10_reports.mp3",
        "shots": [
            (SCREENS / "reports_dark.png", 5),
            (MODS / "mod_finances.png", 5),
            (SCREENS / "reports_light.png", 5),
        ],
    },
    {
        "id": "11_cta",
        "audio": AUDIO_DIR / "vo_11_cta.mp3",
        "shots": [
            (MODS / "mod_calendar.png", 5),
            (MODS / "mod_ai.png", 5),
            (MODS / "mod_mewia.png", 5),
            (MODS / "mod_finances.png", 5),
            (MODS / "mod_bookings.png", 5),
            (LOGO, 5),
        ],
    },
]

W, H = 1920, 1080
NAVY = (8, 29, 58)


def get_duration(f):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(f)],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    try:
        return float(r.stdout.strip())
    except:
        return 5.0


def build_slide(img_path, out_path):
    """Resize screenshot to 1920x1080, add logo watermark."""
    from PIL import Image

    if out_path.exists():
        return

    if img_path.exists():
        base = Image.open(img_path).convert("RGBA")
        # If it's the logo (square/small), put it centered on navy bg
        if base.width < 800 or base.height < 400:
            canvas = Image.new("RGBA", (W, H), (*NAVY, 255))
            # Center logo
            ratio = min(600 / base.width, 400 / base.height)
            new_w, new_h = int(base.width * ratio), int(base.height * ratio)
            logo_resized = base.resize((new_w, new_h), Image.LANCZOS)
            x = (W - new_w) // 2
            y = (H - new_h) // 2
            canvas.paste(logo_resized, (x, y), logo_resized)
            base = canvas
        else:
            base = base.resize((W, H), Image.LANCZOS)
    else:
        base = Image.new("RGBA", (W, H), (*NAVY, 255))

    # Add logo watermark top-right (skip if this IS the logo slide)
    if "logo" not in str(img_path).lower() and LOGO.exists():
        try:
            logo_img = Image.open(LOGO).convert("RGBA")
            target_h = 40
            ratio = target_h / logo_img.height
            logo_img = logo_img.resize((int(logo_img.width * ratio), target_h), Image.LANCZOS)
            r, g, b, a = logo_img.split()
            a = a.point(lambda p: int(p * 0.7))
            logo_img = Image.merge("RGBA", (r, g, b, a))
            base.paste(logo_img, (W - logo_img.width - 20, 15), logo_img)
        except:
            pass

    base.convert("RGB").save(str(out_path), "PNG")


def main():
    print("=" * 60)
    print(" SurfIQ EN Video v2 — screenshots every 5s")
    print("=" * 60)

    all_segment_videos = []

    for seg in SEGMENTS:
        seg_id = seg["id"]
        audio_path = seg["audio"]
        audio_dur = get_duration(audio_path)
        shots = seg["shots"]

        print(f"\n[{seg_id}] audio={audio_dur:.1f}s, {len(shots)} screenshots")

        # Build slides for this segment
        shot_files = []
        for i, (img_path, dur) in enumerate(shots):
            slide_path = SLIDES_DIR / f"slide_{seg_id}_{i:02d}.png"
            build_slide(img_path, slide_path)
            shot_files.append((slide_path, dur))

        # Calculate total shot duration vs audio duration
        total_shot_dur = sum(d for _, d in shot_files)
        # Scale shot durations to match audio + 0.5s padding
        target_dur = audio_dur + 0.5
        scale = target_dur / total_shot_dur if total_shot_dur > 0 else 1

        # Build concat file for this segment's shots
        seg_concat = SLIDES_DIR / f"concat_{seg_id}.txt"
        with open(seg_concat, "w") as f:
            for slide_path, dur in shot_files:
                actual_dur = dur * scale
                f.write(f"file '{slide_path.name}'\n")
                f.write(f"duration {actual_dur:.2f}\n")
            # Last frame needs to be repeated for ffmpeg concat
            f.write(f"file '{shot_files[-1][0].name}'\n")

        # Build segment video: slideshow + audio
        seg_video = SLIDES_DIR / f"seg_{seg_id}.mp4"
        all_segment_videos.append(seg_video)

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(seg_concat),
            "-i", str(audio_path),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-vf", "fps=25,scale=1920:1080",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            str(seg_video),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                cwd=str(SLIDES_DIR))
        if result.returncode == 0:
            print(f"  OK: {seg_video.name} ({target_dur:.1f}s)")
        else:
            print(f"  ERROR: {result.stderr[-200:]}")

    # Concat all segments
    print(f"\nConcatenating {len(all_segment_videos)} segments...")
    final_concat = SLIDES_DIR / "concat_final.txt"
    with open(final_concat, "w") as f:
        for sv in all_segment_videos:
            if sv.exists():
                f.write(f"file '{sv.name}'\n")

    cmd_final = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(final_concat),
        "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(OUTPUT),
    ]
    result = subprocess.run(cmd_final, capture_output=True, text=True, encoding="utf-8", errors="replace",
                            cwd=str(SLIDES_DIR))

    if OUTPUT.exists():
        size_mb = OUTPUT.stat().st_size / (1024 * 1024)
        dur = get_duration(OUTPUT)
        print(f"\n[DONE] {OUTPUT.name}")
        print(f"  Size: {size_mb:.1f} MB")
        print(f"  Duration: {dur:.0f}s")
    else:
        print(f"[ERROR] Output not created")
        print(result.stderr[-500:])


if __name__ == "__main__":
    main()
