# Hires-Bot Overview

1. **Config Files**
   - In the same folder, create or edit:
     - **config.txt** containing:
       ```
       TelegramApiServerPath=<full path to telegram-bot-api.exe>
       PythonScriptPath=<full path to post.py>
       telegram_api_id=123456
       telegram_api_hash=abcdef123456
       ```
     - **credentials.txt** containing:
       ```
       TOKEN=<your bot token>
       CHAT_ID=<your chat ID>
       ROOT_DIR=<absolute path to albums folder>
       ```
2. **Dependencies**
   - Install [streamrip](https://github.com/Anixxxxx/streamrip) and ensure it’s added to your system PATH.
   - Install required Python libs:
     ```
     pip install -r requirements.txt
     ```
3. **Usage**
   - Run gui.py to launch the bot interface. 
   - Click “Enable” to start the Telegram API server, “Send Albums” to post music, or “Download Song” to rip tracks via streamrip.
   - Press “Exit” when done (server cleanup is automatic).

