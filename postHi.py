# album_bot.py  –  Python 3.10+, async
import shutil, asyncio, os, pathlib, re, io, subprocess
from PIL import Image
from mutagen.flac import FLAC
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
        elif k.strip().upper() == "ROOT_DIR":
            ROOT_DIR = v.strip()

EXTRA_TEXT = "@amirhires"

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
        meta = FLAC(t)
        total_length += meta.info.length
    hours, remainder = divmod(int(total_length), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"

async def post_album(album_path: pathlib.Path):
    print(f"Posting album: {album_path.name}")  # Debug: Album posting start
    cover = album_path / "cover.jpg"
    tracks_all = list(album_path.rglob("*.flac"))
    if not tracks_all:
        return

    meta        = FLAC(tracks_all[0])
    sr_khz      = meta.info.sample_rate // 1000
    bit_depth   = meta.info.bits_per_sample
    album_name  = meta.get("album",  [album_path.name])[0]
    artist      = meta.get("artist", [""])[0]
    raw_genres  = meta.get("genre",  [])
    year        = meta.get("date", meta.get("year", [None]))[0]

    genres = []
    for g in raw_genres:
        genres += [p.strip() for p in re.split(r"[;,/\\]", g) if p.strip()]

    from telegram.helpers import escape_markdown
    escaped_album = escape_markdown(album_name, version=2)
    cap_lines = []
    cap_lines.append(f"*_{escaped_album}_*")  # Emojis at the start
    if year: cap_lines.append(escape_markdown(str(year), version=2))
    
    # Escape hashtags properly
    artist_hashtag = to_hashtag(artist)
    cap_lines.append(escape_markdown(artist_hashtag, version=2))
    
    for g in genres:
        genre_hashtag = to_hashtag(g)
        cap_lines.append(escape_markdown(genre_hashtag, version=2))
    
    # Italic quality text - properly formatted
    if bit_depth == 24:
        emoji = "🥇"
    else:
        emoji = "🥈"
    quality_text = escape_markdown(f'{bit_depth} bit / {sr_khz} kHz', version=2)
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
            sub.glob("*.flac"),
            key=lambda f: int(FLAC(f).get("tracknumber", ["0"])[0]),
        )

        for t in tracks:
            title = FLAC(t).get("title", [t.stem])[0]
            with open(t, "rb") as fa, open(cover, "rb") as ft:
                await safe_send(
                    bot.send_audio,
                    chat_id=CHAT_ID,
                    audio=InputFile(fa, filename=t.name),
                    thumbnail=InputFile(ft, filename="cover.jpg"),
                    performer=artist,
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
                caption=f"🗂 {EXTRA_TEXT}",
                read_timeout=900,
            )
        await asyncio.sleep(3)
        z.unlink()

    shutil.rmtree(album_path)
    print("Finished sending album:", album_path.name)  # Debug: Album posting end

async def main():
    print("Starting to send albums...")  # Debug: Main start
    albums = sorted(d for d in pathlib.Path(ROOT_DIR).iterdir() if d.is_dir())
    if not albums:
        print("No albums to send. Exiting.")
        return
    for album in albums:
        await post_album(album)
        await asyncio.sleep(6)
    print("All albums sent. Exiting.")  # Debug: Main end

if __name__ == "__main__":
    asyncio.run(main())
