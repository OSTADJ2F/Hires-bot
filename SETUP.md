# Windows setup

The repository is cloned at `C:\Stuff\Telegram Bot`, on `main` with the original
GitHub remote. Double-click **start.bat** to open the app, or run:

```powershell
cd 'C:\Stuff\Telegram Bot'
.\start.bat
```

The launcher selects the project's Python environment and FFmpeg automatically.
The GUI can open before account credentials have been filled in.

## Fill in your account settings

Edit these local files; they are excluded from Git:

- **config.txt**: fill in `telegram_api_id` and `telegram_api_hash` from
  [my.telegram.org](https://my.telegram.org). The executable paths are already set.
- **credentials.txt**: fill in `TOKEN` from BotFather, `CHAT_ID` for the FLAC
  channel, and `CHAT_ID_LOW` for the MP3 channel. Use the same channel ID for both
  if desired. Give your bot permission to post in those channels.
- **streamrip.toml**: fill in the account settings for your music service. See the
  [streamrip documentation](https://github.com/nathom/streamrip/wiki).

### Qobuz login

The old email/password API login can reject credentials that work on Qobuz's
website ([upstream issue #954](https://github.com/nathom/streamrip/issues/954)).
For Qobuz, double-click **qobuz-login.cmd**, then sign in on Qobuz's website in
the fresh Edge/Chrome window. The helper watches only the successful Qobuz login
response, saves your numeric user ID and token to `streamrip.toml`, enables
`use_auth_token`, and closes its browser. It does not save your password or use
your existing browser profile. Stop any old streamrip login prompt with Ctrl+C
first; restart streamrip or the GUI after the helper finishes.

This uses streamrip 2.1.0's existing token support and the browser-login approach
documented in [upstream PR #955](https://github.com/nathom/streamrip/pull/955).
The helper does not download music or post to Telegram. Rerun it when your token
expires. Playwright is installed in `.venv`; it uses your installed Edge/Chrome,
so a separate Chromium download is not required.

If automatic capture fails, open Qobuz's web player and browser developer tools,
select **Network**, and sign in. Find a successful `user/login` response and
locally copy its `user.id` and `user_auth_token` values. Then run:

```powershell
.\.venv\Scripts\python.exe qobuz_login.py --manual
```

The user ID goes into `email_or_userid`; the token goes into `password_or_token`.
The helper updates these fields without printing their values or changing your
other service settings. Qobuz account authentication still needs to be completed
by you in the browser; offline tests cannot establish that your account works.

Both download folders and posting folders are set to `downloads\FLAC` and
`downloads\MP3` inside this project. To change them, update **download.txt** and
the matching `ROOT_DIR` / `ROOT_DIR_LOW` entries in **credentials.txt**.

The existing posting scripts delete an album folder after successfully posting
all its tracks and archive. Use these folders for the bot's working copies.

After filling in the credentials, reopen the app and click **Enable** to start
the local Telegram API server. It listens on `127.0.0.1:8081`. Its data and log
are kept under `.runtime\telegram`. **Disable**, **Exit**, or closing the window
stops the server process started by this app.

If this bot currently uses Telegram's hosted API, follow Telegram's
[migration instructions](https://github.com/tdlib/telegram-bot-api#moving-a-bot-to-a-local-server)
before switching it to the local server. Setup has not logged out or connected
your bot, downloaded music, or sent any posts.

## Installed environment

- Python **3.12.14**, in `.venv`, using the existing bundled interpreter at
  `C:\Users\amira\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.
  Keep this base interpreter available; recreate `.venv` if its location changes.
- `python-telegram-bot` **22.8**, Pillow **10.4.0**, mutagen **1.48.1**, and
  [nathom/streamrip](https://github.com/nathom/streamrip) **2.1.0**, plus their
  dependencies. Exact resolved versions are in **requirements-lock.txt**.
- FFmpeg / FFprobe **9.0.1** under `.tools\ffmpeg`, downloaded from
  [Gyan's Windows builds](https://www.gyan.dev/ffmpeg/builds/) and checked against
  the published SHA-256 checksum.
- The existing 7-Zip installation at `C:\Program Files\7-Zip\7z.exe`.
- Telegram Bot API **10.3**, built from
  [official source](https://github.com/tdlib/telegram-bot-api), installed at
  `.tools\telegram-bot-api\bin\telegram-bot-api.exe` with its runtime DLLs.
  Source commit: `e3e9dd8e5b3d7ab8537cd5a10dc31d5ffa8f82d1`.

The launcher adds tools to its own process PATH. No global PATH edits are needed.
Native build dependencies use Microsoft's vcpkg in
`C:\Users\amira\AppData\Local\Temp\hires-bot-vcpkg-20260918`; that temporary
directory is only needed to rebuild the server, not to run the installed app.

## Verification and maintenance

```powershell
.\.venv\Scripts\python.exe check_setup.py
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\rip.exe --config-path streamrip.toml config open
```

The dependency check runs offline and reports blank Telegram fields without
printing their values. Account authentication and real posting/downloading must
be checked after you enter your credentials.

Setup verification passed: Python dependency consistency, executable version
checks, hidden GUI startup/exit, server process handling with mocks, and generated
sample FLAC/MP3 encoding, metadata, JPEG thumbnail, and ZIP integrity checks. The
final optimized native build completed without Windows runtime linker warnings.

To recreate the Python environment with an installed Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

To rebuild the server, use Telegram's
[Windows build instructions](https://tdlib.github.io/telegram-bot-api/build.html?os=Windows).
Keep the vcpkg directory in a path without spaces; gperf's build does not support
spaces in its paths. The app source and installed server can stay here. Set
`$env:CL = '/MP8'` before the CMake build to compile source files in parallel.

Local setup changes add the missing dependency files, portable downloader lookup,
local configuration, and launcher. GUI startup defers credential loading until
posting, launches streamrip without shell parsing, preserves setup files on exit,
and manages only its own local API server process. No changes have been committed
or pushed to GitHub.
