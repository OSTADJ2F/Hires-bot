# Hires-bot

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/downloads/)
[![Windows](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D6)](https://github.com/OSTADJ2F/Hires-bot)
[![streamrip 2.1.0](https://img.shields.io/badge/streamrip-2.1.0-green)](https://github.com/nathom/streamrip)
[![Telegram Bot API](https://img.shields.io/badge/telegram-local%20Bot%20API%2010.3-229ED9)](https://github.com/tdlib/telegram-bot-api)

Download hi-res music with [streamrip](https://github.com/nathom/streamrip) and publish
albums to your Telegram channels — cover art, tagged tracks, and a ZIP archive —
through a local Telegram Bot API server that supports large files.

## What this does

Hires-bot is a Windows desktop app (Tkinter GUI) with two halves:

1. **Download manager** — paste a Qobuz / Tidal / Deezer / SoundCloud album or
   track URL, tick FLAC and/or MP3, queue it, and hit **Download**. FLAC rips at
   streamrip quality 3 (24-bit, up to 96 kHz); MP3 rips at quality 1 (320 kbps).
   Every queued link downloads (`--no-db`; the files on disk are the source of
   truth, so re-queueing after posting or deleting just works).
2. **Telegram publisher** — one click posts each album folder to your channels:
   cover photo with a formatted caption (album, year, artist/genre hashtags,
   quality, duration), the cover file, every track as audio with thumbnail,
   then a 7-Zip archive (split at ~1900 MB for Telegram limits). Successfully
   posted album folders are deleted automatically.

Typical flow: queue a Qobuz album URL → download FLAC + MP3 → **Send All Albums**
→ the hi-res channel gets FLAC, the low-res channel gets MP3.

## Features

- Queue-based downloads: add, remove, clear, and batch-rip multiple URLs.
- Dual-quality pipeline: FLAC channel (`postHi.py`) and MP3 channel (`postLow.py`).
- Rich captions (MarkdownV2): hashtags, bit depth / sample rate or bitrate,
  album duration, channel tag.
- Local Bot API server on `127.0.0.1:8081` — no hosted-API file-size bottleneck.
- Qobuz token login helper (`qobuz-login.cmd`) using your real browser, so you
  never store your password (see
  [upstream issue #954](https://github.com/nathom/streamrip/issues/954) and
  [PR #955](https://github.com/nathom/streamrip/pull/955)).
- Channel-ID helper (`get_channel_id.py`), environment checker (`check_setup.py`),
  and one-click launcher (`start.bat`).

## Compatibility

| Component | Supported |
|---|---|
| OS | Windows 10 / 11, 64-bit |
| Python | 3.12 (project `.venv` included; recreate with `requirements-lock.txt`) |
| Music sources | Qobuz (primary, auth-token login), Tidal, Deezer, SoundCloud via streamrip |
| Telegram | Any bot from [@BotFather](https://t.me/BotFather); local Bot API 10.3 server bundled under `.tools` |
| Download tools | FFmpeg / FFprobe 9.0.1 (bundled), 7-Zip (you set its path as `SevenZipPath` in `config.txt`) |
| Key packages | `python-telegram-bot` 22.8, `streamrip` 2.1.0, `Pillow` 10.4.0, `mutagen` 1.48.1, `playwright` 1.63.0 |

> You need your own paid streaming subscription for hi-res downloads, your own
> Telegram bot, and channels where that bot is an admin.

## Quick start

```powershell
cd 'C:\Stuff\Telegram Bot'
.\start.bat
```

If this is a fresh clone, follow the full setup guide below first.

## Full setup guide

### 1. Prerequisites

- [Python 3.12](https://www.python.org/downloads/) (only needed to recreate
  `.venv`; the prepared folder already contains one).
- [7-Zip](https://www.7-zip.org/) installed — note the full path to `7z.exe`
  (default `C:\Program Files\7-Zip\7z.exe`); you enter it in `config.txt` below.
- A Telegram bot token from [@BotFather](https://t.me/BotFather).
- API credentials from [my.telegram.org](https://my.telegram.org)
  (`telegram_api_id` + `telegram_api_hash`) for the local Bot API server.
- A Qobuz (or Tidal / Deezer) account for streamrip.

### 2. Get the code and environment

```powershell
git clone https://github.com/OSTADJ2F/Hires-bot.git
cd Hires-bot
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

The prepared checkout already ships `.venv`, `.tools` (FFmpeg + Telegram Bot API),
and `streamrip.toml`, so you can usually skip straight to configuration.

### 3. Configure the app

Copy each `.example` file to its real name (the real files are git-ignored), then
fill them in:

| File | Copy from | Contents |
|---|---|---|
| `config.txt` | `config.example` | `TelegramApiServerPath`, `PythonScriptPath`, `SevenZipPath`, `telegram_api_id`, `telegram_api_hash` |
| `credentials.txt` | `credentials.example` | `TOKEN`, `CHAT_ID`, `CHAT_ID_LOW`, `ROOT_DIR`, `ROOT_DIR_LOW` |
| `download.txt` | `download.example` | `FLAC_PATH`, `MP3_PATH` |
| `streamrip.toml` | (shipped) | Music-service account + quality settings (see below) |

Example `config.txt`:

```
TelegramApiServerPath=C:\Stuff\Telegram Bot\.tools\telegram-bot-api\bin\telegram-bot-api.exe
PythonScriptPath=C:\Stuff\Telegram Bot\postHi.py
SevenZipPath=C:\Program Files\7-Zip\7z.exe
telegram_api_id=123456
telegram_api_hash=abcdef123456
```

`SevenZipPath` is the full path to your `7z.exe` — no hardcoded location in the
code; the posting scripts and the launcher both use this value (falling back to
`7z` on `PATH` if it is empty). Update it if you installed 7-Zip elsewhere.

Example `credentials.txt` (use the same channel ID twice if you only run one channel):

```
TOKEN=<bot token from BotFather>
CHAT_ID=<FLAC channel ID>
CHAT_ID_LOW=<MP3 channel ID>
ROOT_DIR=C:\Stuff\Telegram Bot\downloads\FLAC
ROOT_DIR_LOW=C:\Stuff\Telegram Bot\downloads\MP3
```

Example `download.txt` (must match the `ROOT_DIR` entries above — posting
deletes album folders after sending, so these are working copies):

```
FLAC_PATH=C:\Stuff\Telegram Bot\downloads\FLAC
MP3_PATH=C:\Stuff\Telegram Bot\downloads\MP3
```

To find a channel ID, run `get_channel_id.py`, post something in your private
channel, and copy the printed ID.

### 4. Log in to Qobuz (or your music service)

Email/password API logins are rejected for credentials that work on the Qobuz
website ([upstream issue #954](https://github.com/nathom/streamrip/issues/954)).
Use the browser-token helper instead:

1. Double-click **`qobuz-login.cmd`**.
2. Sign in on the Qobuz website in the fresh Edge/Chrome window.
3. The helper saves your numeric user ID + token to `streamrip.toml`
   (`use_auth_token = true`) and closes the browser. Your password is never saved.

Manual fallback (from the [streamrip wiki](https://github.com/nathom/streamrip/wiki)):

```powershell
.\.venv\Scripts\python.exe qobuz_login.py --manual
```

For Tidal / Deezer / SoundCloud, fill in the matching section of `streamrip.toml`
per the [streamrip documentation](https://github.com/nathom/streamrip/wiki).
Key download settings: `[qobuz] quality = 3`, MP3 jobs override with `-q 1`,
`[database] downloads_enabled = false` (every queued link downloads; files on
disk are the source of truth), artwork embedded + saved as `cover.jpg`
(which the posting scripts require).

### 5. Verify

```powershell
.\.venv\Scripts\python.exe check_setup.py
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

`check_setup.py` verifies Python packages, FFmpeg/FFprobe, 7-Zip, and the local
Bot API binary without contacting Telegram or music services.

### 6. Run

Double-click **`start.bat`** (or `.\start.bat` from PowerShell). The launcher
puts `.venv`, FFmpeg, and 7-Zip on `PATH` automatically — no global PATH edits.

## Usage

1. Click **Enable** to start the local Bot API server (status dot turns green;
   logs under `.runtime\telegram\`). If your bot previously used Telegram's
   hosted API, migrate it first per the
   [tdlib migration instructions](https://github.com/tdlib/telegram-bot-api#moving-a-bot-to-a-local-server).
2. Paste an album/track URL, tick **FLAC** and/or **MP3**, **Add to Queue**,
   then **Download**. Watch progress in the console panel.
3. Click **Send FLAC Albums**, **Send MP3 Albums**, or **Send All Albums**.
   Each album posts cover → tracks → archive, then its folder is removed.
4. **Disable** or **Exit** (or just close the window) to stop the server you
   started. `download.txt` changes apply immediately without restarting.

Each Telegram post contains: cover photo with caption, `cover.jpg` document,
one audio message per track (performer, title, thumbnail), and a `.zip`
archive of the album folder.

## Project structure

```
gui.py             Tkinter app: server controls, download queue, console
launch.py          Sets PATH/chdir, then runs gui.py (.venv-aware)
start.bat          One-click Windows launcher
postHi.py          Posts FLAC albums (ROOT_DIR -> CHAT_ID, @amirhires)
postLow.py         Posts MP3 albums (ROOT_DIR_LOW -> CHAT_ID_LOW, @amirlowres)
get_channel_id.py  Helper: resolves a private channel ID for credentials.txt
qobuz_login.py     Browser-token login helper (+ qobuz-login.cmd)
check_setup.py     Offline dependency/environment verification
tests/             Unit tests (Qobuz login helper)
streamrip.toml     streamrip config (git-ignored, has your tokens)
```

Local setup notes live in [SETUP.md](SETUP.md), including the exact pinned
environment (Python 3.12.14, FFmpeg 9.0.1, Bot API 10.3 build info) and rebuild
instructions ([Telegram Windows build docs](https://tdlib.github.io/telegram-bot-api/build.html?os=Windows)).

## Troubleshooting

| Symptom | Fix |
|---|---|
| GUI says a link is "already downloaded" but the files are gone | Fixed in the current version: the app passes `--no-db` and ships `[database] downloads_enabled = false`. Re-queue the link. |
| Qobuz login fails with website-working credentials | Rerun `qobuz-login.cmd`; tokens expire. See [issue #954](https://github.com/nathom/streamrip/issues/954). |
| **Enable** fails / server exits | Check `telegram_api_id/hash` in `config.txt` and `.runtime\telegram\server.log`. |
| Posts fail with file errors | Confirm the bot is admin in both channels and the IDs in `credentials.txt` are correct. |
| `cover.jpg` missing errors | Keep `save_artwork = true` in `streamrip.toml`; posters require it. |
| `7z not found` when posting | Set `SevenZipPath` in `config.txt` to your full `7z.exe` path (or add 7-Zip to `PATH`). |

## Links

- This project: [OSTADJ2F/Hires-bot](https://github.com/OSTADJ2F/Hires-bot)
- Downloader: [nathom/streamrip](https://github.com/nathom/streamrip) ·
  [wiki](https://github.com/nathom/streamrip/wiki) ·
  [Qobuz login issue #954](https://github.com/nathom/streamrip/issues/954) ·
  [browser-login PR #955](https://github.com/nathom/streamrip/pull/955)
- Telegram: [Bot API server (tdlib)](https://github.com/tdlib/telegram-bot-api) ·
  [local-server migration](https://github.com/tdlib/telegram-bot-api#moving-a-bot-to-a-local-server) ·
  [Windows build docs](https://tdlib.github.io/telegram-bot-api/build.html?os=Windows) ·
  [BotFather](https://t.me/BotFather) · [my.telegram.org](https://my.telegram.org)
- Tools: [FFmpeg Windows builds (Gyan)](https://www.gyan.dev/ffmpeg/builds/) ·
  [7-Zip](https://www.7-zip.org/) · [Python downloads](https://www.python.org/downloads/)

## Disclaimer

For personal use with accounts and content you are entitled to access. Respect
your streaming service's terms, Telegram's terms, and applicable copyright law.
This project is not affiliated with Qobuz, Tidal, Deezer, SoundCloud, or Telegram.
