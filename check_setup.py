"""Verify local dependencies without connecting to Telegram or music services."""
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import sys
import tkinter

from launch import prepare_environment


def main():
    project = prepare_environment()
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    for package in ("python-telegram-bot", "Pillow", "mutagen", "streamrip"):
        print(f"{package}: {importlib.metadata.version(package)}")
    print(f"Tcl/Tk: {tkinter.Tcl().eval('info patchlevel')}")

    commands = (
        ("streamrip", [shutil.which("rip"), "--version"]),
        ("FFmpeg", [shutil.which("ffmpeg"), "-version"]),
        ("FFprobe", [shutil.which("ffprobe"), "-version"]),
        ("7-Zip", [shutil.which("7z"), "i"]),
        ("Telegram API", [str(project / ".tools/telegram-bot-api/bin/telegram-bot-api.exe"), "--version"]),
    )
    for name, args in commands:
        if not args[0] or not Path(args[0]).is_file():
            raise RuntimeError(f"{name}: executable missing")
        result = subprocess.run(args, capture_output=True, text=True, errors="replace", timeout=30)
        if result.returncode:
            raise RuntimeError(f"{name}: command failed ({result.returncode}): {result.stderr}")
        output = (result.stdout or result.stderr).strip().splitlines()
        print(f"{name}: {output[0] if output else 'OK'}")

    for file_name, keys in (
        ("config.txt", ("telegram_api_id", "telegram_api_hash")),
        ("credentials.txt", ("TOKEN", "CHAT_ID", "CHAT_ID_LOW")),
    ):
        values = dict(line.split("=", 1) for line in (project / file_name).read_text().splitlines() if "=" in line)
        missing = [key for key in keys if not values.get(key, "").strip()]
        print(f"{file_name}: " + ("fill in " + ", ".join(missing) if missing else "values present (not authenticated)"))
    print("Dependency checks passed. Account authentication is a separate step.")


if __name__ == "__main__":
    main()
