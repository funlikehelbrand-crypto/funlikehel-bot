"""
YT Shorts Pipeline — FUN like HEL
Użycie: python yt_shorts_pipeline.py <plik_wideo> [--music <plik_muzyki>] [--title "Tytuł"]

Zasady muzyczne:
- Style: summer-house, afro-house, sport-action, high-energy, chill-beach
- BPM preferowane: 105–135
- NIE: acoustic, piano, slow, lo-fi, corporate, ambient
- Głośność z voice-over: 8–15%, bez mówienia: 25–35%
- Fade in: 0.5s, fade out: 1.0s
- Upload domyślnie NIEPUBLICZNY (--public żeby od razu opublikować)

Kroki:
1. Wczytaj wideo, oceń długość i format
2. Wykryj temat → dobierz styl muzyczny → wybierz track (round-robin)
3. Skonwertuj do 9:16, 1080×1920, domyślnie 35s (max 55s)
4. Wgraj jako NIEPUBLICZNY na YouTube + TikTok
5. Zwróć linki + informację o tracku i licencji
"""

import sys, io, os, argparse, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── Ścieżka do ffmpeg ─────────────────────────────────────────────────────────
try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = 'ffmpeg'

# ── Katalog muzyki ────────────────────────────────────────────────────────────
_MUSIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'music_library')


def _p(filename: str) -> str:
    return os.path.join(_MUSIC_DIR, filename)


# ── Pule muzyczne wg stylu (tylko dynamiczne, royalty-free) ──────────────────
# Lo-fi, ambient, acoustic — wykluczone zgodnie z zasadami
STYLE_POOLS = {
    'high-energy': [
        (_p('funky.mp3'),         'funky royalty-free | YT Audio Library', '~120 BPM'),
        (_p('funky_3_happy.mp3'), 'Topher Mohr — Happy Go Lucky | YT Audio Library', '~118 BPM'),
    ],
    'summer-house': [
        (_p('funky_2_hepcat.mp3'), 'Jingle Punks — Hep Cat | YT Audio Library', '~115 BPM'),
        (_p('funky_5_summer.mp3'), 'E.s.c.p — Summer | YT Audio Library', '~128 BPM'),
        (_p('funky_7_smile.mp3'),  'Silent Partner — Summer Smile | YT Audio Library', '~110 BPM'),
    ],
    'afro-house': [
        (_p('egipt_tropical.mp3'), 'MBB — Beach | royalty-free, no copyright', '~110 BPM'),
        (_p('funky_6_south.mp3'),  'Rondo Brothers — Southside | YT Audio Library', '~112 BPM'),
    ],
    'sport-action': [
        (_p('funky.mp3'),         'funky royalty-free | YT Audio Library', '~120 BPM'),
        (_p('funky_3_happy.mp3'), 'Topher Mohr — Happy Go Lucky | YT Audio Library', '~118 BPM'),
        (_p('funky_2_hepcat.mp3'), 'Jingle Punks — Hep Cat | YT Audio Library', '~115 BPM'),
    ],
    'chill-beach': [
        (_p('funky_4_green.mp3'), 'The Green Orbs | YT Audio Library', '~108 BPM'),
        (_p('hel_chill.mp3'),     'Scandinavianz — Sapporo | royalty-free, no copyright', '~105 BPM'),
    ],
    # 'reggaeton-vibe' — do uzupełnienia gdy pojawią się nowe track-i
}

# ── Topic → styl muzyczny ────────────────────────────────────────────────────
TOPIC_STYLE = {
    'kurs':       'sport-action',    # waterstart, nauka — energia, dynamika
    'freeride':   'high-energy',     # tricki, jumpy — maksymalna energia
    'cabrinha':   'sport-action',    # sprzęt, test center — elektronika
    'egipt':      'afro-house',      # tropical, Morze Czerwone — etnika
    'hel':        'chill-beach',     # Zatoka Pucka, Jastarnia — coastal vibe
    'klimat':     'chill-beach',     # baza, atmosfera — spokojny ale żywy
    'instruktor': 'summer-house',    # mówi do kamery — cichy ale dynamiczny beat
}

# ── Round-robin per styl ──────────────────────────────────────────────────────
def _next_track(style: str) -> tuple:
    """Zwraca kolejny track z danego stylu (round-robin)."""
    pool = STYLE_POOLS.get(style, STYLE_POOLS['summer-house'])
    index_file = os.path.join(_MUSIC_DIR, f'.idx_{style}')
    try:
        idx = int(open(index_file).read().strip())
    except Exception:
        idx = 0
    # Sprawdź czy plik istnieje
    for attempt in range(len(pool)):
        entry = pool[(idx + attempt) % len(pool)]
        if os.path.exists(entry[0]):
            actual_idx = (idx + attempt + 1) % len(pool)
            with open(index_file, 'w') as f:
                f.write(str(actual_idx))
            return entry  # (path, license_info, bpm_info)
    return pool[0]  # fallback

TAGS = [
    'kitesurfing', 'kite', 'kiteboarding', 'kurs kitesurfingu', 'nauka kitesurfingu',
    'szkoła kitesurfingu', 'sporty wodne', 'windsurfing', 'wing', 'SUP',
    'FunLikeHel', 'Hurghada', 'Egipt', 'Jastarnia', 'Półwysep Helski',
    'Cabrinha', 'OdZeraDoKajtera', 'GirlsWhoKite', 'wakeboarding', 'obozy sportowe',
    'kite school', 'Red Sea', 'kitesurf Poland', 'kite Hel', 'surf',
]

HASHTAGS = '#kitesurfing #FunLikeHel #KursKite #szkolaKite #Jastarnia #Egipt #kiteboarding #kite #Shorts #kitesurf #RedSea #Cabrinha'


def get_video_info(path: str) -> dict:
    """Zwraca duration, width, height używając ffprobe."""
    cmd = [
        FFMPEG.replace('ffmpeg', 'ffprobe'), '-v', 'quiet',
        '-print_format', 'json', '-show_streams', '-show_format', path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {'duration': 0, 'width': 0, 'height': 0}
    import json
    d = json.loads(r.stdout)
    info = {'duration': float(d.get('format', {}).get('duration', 0))}
    for s in d.get('streams', []):
        if s.get('codec_type') == 'video':
            info['width'] = s.get('width', 0)
            info['height'] = s.get('height', 0)
    return info


def has_audio_voice(path: str) -> bool:
    """Prosta heurystyka: zakłada że jest głos jeśli film ma ścieżkę audio."""
    cmd = [FFMPEG.replace('ffmpeg', 'ffprobe'), '-v', 'quiet',
           '-print_format', 'json', '-show_streams', path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return False
    import json
    d = json.loads(r.stdout)
    return any(s.get('codec_type') == 'audio' for s in d.get('streams', []))


def detect_topic(filename: str, title: str = '') -> str:
    """Wykrywa temat z nazwy pliku i tytułu."""
    text = (filename + ' ' + title).lower()
    if any(w in text for w in ['waterstart', 'kurs', 'kursant', 'nauka', 'lekcja', 'zero']):
        return 'kurs'
    if any(w in text for w in ['freeride', 'darkslide', 'sesja', 'tricki', 'jump']):
        return 'freeride'
    if any(w in text for w in ['cabrinha', 'latawiec', 'deska', 'sprzet', 'test center']):
        return 'cabrinha'
    if any(w in text for w in ['instruktor', 'teoria', 'zasady', 'bezpieczenstwo']):
        return 'instruktor'
    if any(w in text for w in ['zachod', 'klimat', 'spot', 'baza', 'atmosfera']):
        return 'klimat'
    if any(w in text for w in ['hel', 'jastarnia', 'zatoka', 'pucka', 'polska']):
        return 'hel'
    return 'egipt'  # domyślny


def process_video(input_path: str, music_path: str | None,
                  target_duration: int = 35, title: str = '') -> str:
    """
    Przetwarza wideo:
    - Przycina do target_duration sekund (domyślnie 35s, max 55s)
    - Konwertuje do 9:16, 1080×1920 (blur background dla landscape)
    - Dodaje muzykę: fade in 0.5s, fade out 1.0s
    - Głośność: 10% z voice-over, 30% bez mówienia
    Zwraca ścieżkę do przetworzonego pliku.
    """
    info = get_video_info(input_path)
    duration = min(info['duration'], target_duration)
    w, h = info['width'], info['height']
    is_portrait = h > w
    voice = has_audio_voice(input_path)
    # Z głosem/rozmową: 8-15% (używamy 10% jako środek)
    # Bez mówienia: 25-35% (używamy 30% jako środek)
    music_vol = '0.10' if voice else '0.30'

    out_path = input_path.rsplit('.', 1)[0] + '_shorts_ready.mp4'

    filters = []

    # 9:16 konwersja
    if not is_portrait:
        # Poziomy → scale + blur background (profesjonalnie, nie crop)
        filters.append(
            f'[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[bg];'
            f'[0:v]scale=-1:1080[fg];'
            f'[bg][fg]overlay=(W-w)/2:(H-h)/2[vout]'
        )
        vmap = '[vout]'
    else:
        # Już pionowy — scale do 1080×1920
        filters.append('[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[vout]')
        vmap = '[vout]'

    if music_path and os.path.exists(music_path):
        # Fade in 0.5s, fade out 1.0s (zgodnie z zasadami)
        fade_out_start = max(duration - 1.0, 0)
        music_filter = (
            f'[1:a]volume={music_vol},'
            f'afade=t=in:st=0:d=0.5,'
            f'afade=t=out:st={fade_out_start:.1f}:d=1.0[mout]'
        )
        if voice:
            # Miks głosu + muzyki
            audio_filter = f'{music_filter};[0:a][mout]amix=inputs=2:duration=shortest[aout]'
            audio_map = '[aout]'
        else:
            audio_filter = music_filter
            audio_map = '[mout]'

        filter_complex = ';'.join(filters) + ';' + audio_filter

        cmd = [
            FFMPEG, '-y',
            '-i', input_path,
            '-i', music_path,
            '-filter_complex', filter_complex,
            '-map', vmap,
            '-map', audio_map,
            '-t', str(duration),
            '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
            '-c:a', 'aac', '-b:a', '192k',
            '-movflags', '+faststart',
            out_path
        ]
    else:
        # Bez muzyki
        filter_complex = ';'.join(filters)
        cmd = [
            FFMPEG, '-y',
            '-i', input_path,
            '-filter_complex', filter_complex,
            '-map', vmap,
            '-map', '0:a?' ,
            '-t', str(duration),
            '-c:v', 'libx264', '-crf', '23', '-preset', 'fast',
            '-c:a', 'aac', '-b:a', '192k',
            '-movflags', '+faststart',
            out_path
        ]

    print(f'🎬 Przetwarzam wideo... ({duration:.0f}s, {"9:16" if is_portrait else "16:9→9:16"})')
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print('❌ Błąd ffmpeg:', r.stderr[-500:])
        sys.exit(1)
    print(f'✅ Gotowy plik: {out_path} ({os.path.getsize(out_path)//1024}KB)')
    return out_path


TIKTOK_HASHTAGS = '#kitesurfing #FunLikeHel #kite #kitesurf #kiteboarding #szkolaKite #Jastarnia #Egipt #Hurghada #Cabrinha #sportyWodne #kiteschool'


def build_tiktok_caption(title: str, topic: str) -> str:
    """Buduje caption TikTok (max 2200 znaków)."""
    topic_hooks = {
        'kurs':       'Nauka kite od zera — tak to wygląda! 🪁',
        'egipt':      'Egipt kitesurfing — polska baza w Hurghadzie! 🌊',
        'freeride':   'Sesja kite — czysta adrenalina! 🔥',
        'hel':        'Kitesurfing na Helu — najlepszy spot w Polsce! 🏄',
        'cabrinha':   'Cabrinha 2026 — test center Hurghada! 🪁',
        'instruktor': 'Instruktor kite FUN like HEL w akcji! 💪',
        'klimat':     'Klimat polskiej bazy kite w Egipcie ☀️',
    }
    hook = topic_hooks.get(topic, 'Kitesurfing z FUN like HEL!')
    short_title = title.replace('#Shorts', '').replace('| FUN like HEL', '').strip()
    return f"{hook}\n\n{short_title}\n\n📞 690 270 032 | funlikehel.pl\n\n{TIKTOK_HASHTAGS}"


def upload_to_tiktok(video_path: str, title: str, topic: str) -> str | None:
    """
    Wgrywa przetworzone wideo na TikTok jako publiczne.
    Zwraca publish_id lub None jeśli błąd (nie przerywa pipeline).
    """
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from tiktok import upload_video_file_sync
    except ImportError as e:
        print(f'⚠️  TikTok moduł niedostępny: {e}')
        return None

    caption = build_tiktok_caption(title, topic)
    print(f'📲 Wgrywam na TikTok... ({os.path.getsize(video_path) // 1024 // 1024}MB)')
    try:
        publish_id = upload_video_file_sync(video_path, caption)
        print(f'✅ TikTok OK — publish_id: {publish_id}')
        return publish_id
    except RuntimeError as e:
        if 'tiktok/login' in str(e).lower() or 'brak tokenu' in str(e).lower():
            print(f'⚠️  TikTok: brak autoryzacji. Otwórz https://funlikehel-bot.onrender.com/tiktok/login')
        else:
            print(f'⚠️  TikTok upload błąd: {e}')
        return None
    except Exception as e:
        print(f'⚠️  TikTok upload błąd: {e}')
        return None


def upload_to_youtube(video_path: str, title: str, description: str,
                      tags: list, unlisted: bool = False) -> str:
    """Wgrywa na YT jako niepubliczny, zwraca video_id."""
    sys.path.insert(0, os.path.dirname(__file__))
    from google_auth import get_credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = get_credentials()
    yt = build('youtube', 'v3', credentials=creds)

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '17',
            'defaultLanguage': 'pl',
        },
        'status': {
            'privacyStatus': 'unlisted' if unlisted else 'public',
            'selfDeclaredMadeForKids': False,
        }
    }

    media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True, chunksize=5*1024*1024)
    req = yt.videos().insert(part='snippet,status', body=body, media_body=media)

    response = None
    print('📤 Upload na YouTube...')
    while response is None:
        status, response = req.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f'   {pct}%', end='\r')

    return response['id']


def build_description(topic: str, short_title: str) -> str:
    topic_lines = {
        'kurs':       'Nauka kitesurfingu od zera — tak wyglada kurs kite w FUN like HEL!',
        'egipt':      'Kitesurfing w Egipcie — Hurghada, polska baza, platka laguna, staly wiatr.',
        'freeride':   'Sesja kitesurfingowa na Morzu Czerwonym — tak wyglada dzien na kite tripie!',
        'hel':        'Kitesurfing na Polwyspie Helskim — Jastarnia, Zatoka Pucka, najlepszy spot w Polsce.',
        'cabrinha':   'Cabrinha Test Center w Hurghadzie — testuj sprzet przed zakupem!',
        'instruktor': 'Instruktor FUN like HEL pokazuje zasady bezpieczenstwa na wodzie.',
        'klimat':     'Klimat polskiej bazy kite w Egipcie — tak wyglada dzien na spocie!',
    }
    return f"""{topic_lines.get(topic, short_title)}

👉 Chcesz sprobowac? Zadzwon: 690 270 032
🌐 www.funlikehel.pl | 📸 @funlikehel

🏄 FUN like HEL — polska szkola kite w Jastarni i Hurghadzie (Egipt)
✅ Kursy dla poczatkujacych i zaawansowanych
✅ Cabrinha Test Center — testuj sprzet przed zakupem
✅ Obozy kite dla grup i dzieci

{HASHTAGS}"""


def main():
    parser = argparse.ArgumentParser(description='FLH YT Shorts Pipeline — dual channel YT + TikTok')
    parser.add_argument('video', help='Sciezka do pliku wideo')
    parser.add_argument('--music', default=None, help='Sciezka do pliku muzyki (MP3/WAV) — nadpisuje auto-wybor')
    parser.add_argument('--title', default='', help='Tytul filmu')
    parser.add_argument('--topic', default=None, help='Temat: kurs/egipt/hel/cabrinha/freeride/klimat/instruktor')
    parser.add_argument('--duration', type=int, default=35, help='Docelowa dlugosc w sekundach (domyslnie 35, max 55)')
    parser.add_argument('--public', action='store_true', help='Uploaduj od razu jako PUBLICZNY (domyslnie: niepubliczny)')
    parser.add_argument('--no-tiktok', action='store_true', help='Pomin upload na TikTok')
    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f'❌ Plik nie istnieje: {args.video}')
        sys.exit(1)

    # 1. Wykryj temat → styl muzyczny → wybierz track (round-robin)
    topic = args.topic or detect_topic(os.path.basename(args.video), args.title)
    style = TOPIC_STYLE.get(topic, 'summer-house')

    if args.music:
        music_path = args.music
        music_license = 'dostarczona przez uzytkownika'
        music_bpm = '?'
    else:
        track = _next_track(style)
        music_path, music_license, music_bpm = track

    print(f'🎯 Temat: {topic}  |  styl: {style}')
    print(f'🎵 Track: {music_license}  ({music_bpm})')

    # 2. Dobierz tytuł
    title = args.title or os.path.basename(args.video).rsplit('.', 1)[0].replace('_', ' ')
    if '#Shorts' not in title:
        title = f'{title} #Shorts'
    if '| FUN like HEL' not in title:
        title = f'{title} | FUN like HEL'

    # 3. Przetwórz wideo: 9:16, fade 0.5s/1.0s, głośność wg voice detection
    target_dur = min(args.duration, 55)
    processed = process_video(args.video, music_path, target_duration=target_dur, title=title)

    # 4. Metadane
    description = build_description(topic, title)

    # 5. Upload YouTube (domyślnie NIEPUBLICZNY — sprawdź przed publikacją)
    is_unlisted = not args.public
    video_id = upload_to_youtube(processed, title, description, TAGS, unlisted=is_unlisted)

    # 6. Upload TikTok — ta sama przetworzona wersja 9:16
    tt_publish_id = None if args.no_tiktok else upload_to_tiktok(processed, title, topic)

    info = get_video_info(processed)
    visibility = 'NIEPUBLICZNY — sprawdź i opublikuj ręcznie' if is_unlisted else 'PUBLICZNY'

    print()
    print('=' * 60)
    print(f'✅ YouTube ({visibility}):')
    print(f'   🔗 https://studio.youtube.com/video/{video_id}/edit')
    print(f'   🔗 https://www.youtube.com/watch?v={video_id}')
    if tt_publish_id:
        print(f'✅ TikTok (procesowanie w tle):')
        print(f'   🔗 https://www.tiktok.com/@funlikehelbrand')
        print(f'   publish_id: {tt_publish_id}')
    else:
        print(f'⚠️  TikTok: pominięty (brak tokenu lub błąd)')
    print()
    print(f'📋 Tytuł:       {title}')
    print(f'⏱  Długość:     {info["duration"]:.0f}s')
    print(f'📐 Format:      9:16, 1080×1920')
    print(f'🎵 Muzyka:      {music_license}')
    print(f'🎼 BPM:         {music_bpm}')
    print(f'📄 Licencja:    YouTube Audio Library — royalty-free, bez ograniczeń')
    print()
    print('📌 Przypięty komentarz (skopiuj ręcznie):')
    print(f'   🪁 Kursy kite: funlikehel.pl | Tel: 690 270 032')
    print(f'   📍 Jastarnia + Hurghada (Egipt) | Cabrinha Test Center')
    print('=' * 60)
    if is_unlisted:
        print()
        print(f'💡 Aby opublikować: python yt_shorts_pipeline.py --publish-id {video_id}')
        print(f'   lub: --public flag przy następnym użyciu')


# Oddzielna komenda do publikacji po zatwierdzeniu
def publish_video(video_id: str):
    sys.path.insert(0, os.path.dirname(__file__))
    from google_auth import get_credentials
    from googleapiclient.discovery import build
    creds = get_credentials()
    yt = build('youtube', 'v3', credentials=creds)
    yt.videos().update(
        part='status',
        body={'id': video_id, 'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}}
    ).execute()
    print(f'✅ Opublikowano: https://youtu.be/{video_id}')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--publish-id':
        publish_video(sys.argv[2])
    else:
        main()
