# album_bot.py  –  Python 3.10+, async
import shutil, asyncio, os, pathlib, re, io, subprocess
from PIL import Image
from mutagen.mp3 import MP3
from mutagen.id3 import ID3NoHeaderError
from telegram import Bot, InputFile
from telegram.request import HTTPXRequest
from telegram.error import RetryAfter, BadRequest
import sys

# on Windows, switch to the selector loop to avoid ProactorBasePipeTransport __del__ errors
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Read credentials from file
with open("credentials.txt", "r") as f:
    lines = f.read().splitlines()
    for line in lines:
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip().upper() == "TOKEN":
            TOKEN = v.strip()
        elif k.strip().upper() == "CHAT_ID":
            CHAT_ID = v.strip()
        elif k.strip().upper() == "CHAT_ID_LOW":
            CHAT_ID_LOW = v.strip()
        elif k.strip().upper() == "ROOT_DIR_LOW":
            ROOT_DIR_LOW = v.strip()
        elif k.strip().upper() == "ROOT_DIR":
            ROOT_DIR = v.strip()

# Use LOW versions if available, fallback to regular ones
CHAT_ID = locals().get('CHAT_ID_LOW', CHAT_ID)
ROOT_DIR = locals().get('ROOT_DIR_LOW', ROOT_DIR)

EXTRA_TEXT = "@amirlowres"

SEVEN_ZIP_PATH = r"C:\Program Files\7-Zip\7z.exe"

request = HTTPXRequest(read_timeout=300, write_timeout=300)
bot = Bot(
    token=TOKEN,
    request=request,
    base_url="http://127.0.0.1:8081/bot{token}",
    base_file_url="http://127.0.0.1:8081/file/bot{token}",
    local_mode=True,
)

async def safe_send(fn, *args, **kwargs):
    while True:
        try:
            return await fn(*args, **kwargs)
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except BadRequest as e:
            m = re.search(r"retry after (\d+)", str(e))
            if m:
                await asyncio.sleep(int(m.group(1)))
            else:
                raise

def to_hashtag(name: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", name)
    return "#" + "".join(t.title() for t in tokens)

def make_thumbnail(cover_path: pathlib.Path) -> io.BytesIO:
    img = Image.open(cover_path)
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf

def get_album_length(tracks: list[pathlib.Path]) -> str:
    total_length = 0
    for t in tracks:
        try:
            meta = MP3(t)
            total_length += meta.info.length
        except (ID3NoHeaderError, Exception):
            continue
    hours, remainder = divmod(int(total_length), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"

def get_mp3_metadata(track_path: pathlib.Path):
    """Extract metadata from MP3 file"""
    try:
        meta = MP3(track_path)
        
        # Get basic info
        bitrate_bps = getattr(meta.info, 'bitrate', 320000)  # Default to 320000 if not available
        bitrate = bitrate_bps // 1000  # Convert from bps to kbps
        
        # Extract ID3 tags
        album = meta.get("TALB", [str(track_path.parent.name)])[0] if meta.get("TALB") else str(track_path.parent.name)
        artist = meta.get("TPE1", [""])[0] if meta.get("TPE1") else ""
        title = meta.get("TIT2", [track_path.stem])[0] if meta.get("TIT2") else track_path.stem
        year = None
        if meta.get("TDRC"):
            year = str(meta.get("TDRC")[0])[:4]  # Extract year from date
        elif meta.get("TYER"):
            year = str(meta.get("TYER")[0])
            
        # Handle genres
        raw_genres = []
        if meta.get("TCON"):
            raw_genres = [str(g) for g in meta.get("TCON")]
            
        # Get track number
        track_num = "0"
        if meta.get("TRCK"):
            track_num = str(meta.get("TRCK")[0]).split("/")[0]
            
        return {
            'bitrate': bitrate,
            'album': album,
            'artist': artist,
            'title': title,
            'year': year,
            'genres': raw_genres,
            'track_number': track_num
        }
    except Exception as e:
        print(f"Error reading metadata from {track_path}: {e}")
        return {
            'bitrate': 320,
            'album': str(track_path.parent.name),
            'artist': "",
            'title': track_path.stem,
            'year': None,
            'genres': [],
            'track_number': "0"
        }

async def post_album(album_path: pathlib.Path):
    print(f"Posting album: {album_path.name}")  # Debug: Album posting start
    cover = album_path / "cover.jpg"
    tracks_all = list(album_path.rglob("*.mp3"))
    if not tracks_all:
        return

    # Get metadata from first track
    meta_data = get_mp3_metadata(tracks_all[0])
    
    album_name = meta_data['album']
    artist = meta_data['artist']
    raw_genres = meta_data['genres']
    year = meta_data['year']
    bitrate = meta_data['bitrate']

    genres = []
    for g in raw_genres:
        genres += [p.strip() for p in re.split(r"[;,/\\]", str(g)) if p.strip()]

    from telegram.helpers import escape_markdown
    escaped_album = escape_markdown(album_name, version=2)
    cap_lines = []
    cap_lines.append(f"*_{escaped_album}_*")  # Emojis at the start
    if year: cap_lines.append(escape_markdown(str(year), version=2))
    
    # Escape hashtags properly
    if artist:
        artist_hashtag = to_hashtag(artist)
        cap_lines.append(escape_markdown(artist_hashtag, version=2))
    
    for g in genres:
        genre_hashtag = to_hashtag(g)
        cap_lines.append(escape_markdown(genre_hashtag, version=2))
    
    # Quality text for MP3 - using bitrate instead of bit depth
    emoji = "💿"  # Generic medal for lower quality
    quality_text = escape_markdown(f'{bitrate} kbps MP3', version=2)
    cap_lines.append(f"{emoji} _{quality_text}_")
    
    album_len = get_album_length(tracks_all)
    cap_lines.append(f"⏱️ {escape_markdown(album_len, version=2)}")
    
    cap_lines.append(f"🌟 {escape_markdown(EXTRA_TEXT, version=2)}")
    caption_cover = "\n".join(cap_lines)

    print(f"Found {len(tracks_all)} tracks; sending cover photo.")  # Debug: Track and cover info
    await safe_send(
        bot.send_photo,
        chat_id=CHAT_ID,
        photo=make_thumbnail(cover),
        caption=caption_cover,
        parse_mode="MarkdownV2",
    )
    await asyncio.sleep(3)

    print("Sending cover file...")  # Debug: Sending cover file
    with open(cover, "rb") as f_cover:
        await safe_send(
            bot.send_document,
            chat_id=CHAT_ID,
            document=f_cover,
            caption=f"🎨 {EXTRA_TEXT}",  # Emojis at the start
        )
    await asyncio.sleep(3)

    print("Sending audio tracks...")  # Debug: Sending audio tracks
    subs    = [d for d in album_path.iterdir() if d.is_dir()]
    subdirs = sorted(subs) if subs else [album_path]

    for sub in subdirs:
        if subs:
            await safe_send(bot.send_message, chat_id=CHAT_ID, text=f"📀 {sub.name}")
            await asyncio.sleep(2)

        tracks = sorted(
            sub.glob("*.mp3"),
            key=lambda f: int(get_mp3_metadata(f)['track_number']),
        )

        for t in tracks:
            track_meta = get_mp3_metadata(t)
            title = track_meta['title']
            performer = track_meta['artist'] or artist
            
            with open(t, "rb") as fa, open(cover, "rb") as ft:
                await safe_send(
                    bot.send_audio,
                    chat_id=CHAT_ID,
                    audio=InputFile(fa, filename=t.name),
                    thumbnail=InputFile(ft, filename="cover.jpg"),
                    performer=performer,
                    title=title,
                    caption=f"🌟 {EXTRA_TEXT}",  # Emojis at the start
                )
            await asyncio.sleep(3)

    # ── archive ────────────────────────────────────────────
    def folder_size(p: pathlib.Path) -> int:
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

    parent      = album_path.parent
    seven       = SEVEN_ZIP_PATH or shutil.which("7z") or shutil.which("7z.exe")
    if not seven:
        raise FileNotFoundError("7z not found; set SEVEN_ZIP_PATH or add to PATH.")

    # Fix: Replace glob with iterdir and string checking
    for old in parent.iterdir():
        if old.is_file() and old.name.startswith(f"{album_path.name}.zip"):
            old.unlink()

    split_limit = 1900 * 1024 * 1024
    zip_base    = parent / album_path.name
    split       = folder_size(album_path) > split_limit

    print("Creating and sending archive for album:", album_path.name)  # Debug: Archive creation
    if split:
        subprocess.run([seven, "a", "-tzip", "-v1900m",
                        f"{zip_base}.zip", str(album_path)], check=True)
        # Fix: Replace glob with iterdir and filtering
        archives = sorted([f for f in parent.iterdir() 
                          if f.is_file() and f.name.startswith(f"{album_path.name}.zip.")])
    else:
        subprocess.run([seven, "a", "-tzip",
                        f"{zip_base}.zip", str(album_path)], check=True)
        archives = [parent / f"{album_path.name}.zip"]

    for z in archives:
        with open(z, "rb") as f_zip:
            await safe_send(
                bot.send_document,
                chat_id=CHAT_ID,
                document=InputFile(f_zip, filename=z.name),
                caption=f"🌟 {EXTRA_TEXT}",
                read_timeout=900,
            )
        await asyncio.sleep(3)
        z.unlink()

    shutil.rmtree(album_path)
    print("Finished sending album:", album_path.name)  # Debug: Album posting end

async def main():
    print("Starting to send MP3 albums...")  # Debug: Main start
    albums = sorted(d for d in pathlib.Path(ROOT_DIR).iterdir() if d.is_dir())
    if not albums:
        print("No albums to send. Exiting.")
        return
    for album in albums:
        await post_album(album)
        await asyncio.sleep(6)
    print("All MP3 albums sent. Exiting.")  # Debug: Main end

if __name__ == "__main__":
    asyncio.run(main())
