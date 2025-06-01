import tkinter as tk
import asyncio
import subprocess
import os
import sys
import threading
from tkinter import scrolledtext
import tkinter.simpledialog as simpledialog
from postHi import main as postHi_main
from postLow import main as postLow_main
import re

API_PATH = None
PY_PATH = None
TELEGRAM_API_ID   = None
TELEGRAM_API_HASH = None
FLAC_PATH = None
MP3_PATH = None
server_enabled = False

def read_config():
    global API_PATH, PY_PATH, TELEGRAM_API_ID, TELEGRAM_API_HASH
    if not os.path.exists("config.txt"):
        return
    with open("config.txt", "r") as f:
        for line in f:
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip().lower() == "telegramapiserverpath":
                API_PATH = v.strip()
            elif k.strip().lower() == "pythonscriptpath":
                PY_PATH = v.strip()
            elif k.strip().lower() == "telegram_api_id":
                TELEGRAM_API_ID = v.strip()
            elif k.strip().lower() == "telegram_api_hash":
                TELEGRAM_API_HASH = v.strip()

def read_download_paths():
    global FLAC_PATH, MP3_PATH
    if not os.path.exists("download.txt"):
        # Set default paths if file doesn't exist
        FLAC_PATH = "C:\\Users\\amira\\StreamripDownloads\\FLAC"
        MP3_PATH = "C:\\Users\\amira\\StreamripDownloads\\MP3"
        return
    with open("download.txt", "r") as f:
        for line in f:
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip().upper() == "FLAC_PATH":
                FLAC_PATH = v.strip()
            elif k.strip().upper() == "MP3_PATH":
                MP3_PATH = v.strip()

read_config()
read_download_paths()

def update_server_status(canvas, enabled):
    canvas.delete("all")
    color = "green" if enabled else "red"
    canvas.create_oval(2, 2, 18, 18, fill=color)
    # Update send buttons availability based on server status
    if enabled:
        send_hi_button.config(state=tk.NORMAL)
        send_low_button.config(state=tk.NORMAL)
        send_both_button.config(state=tk.NORMAL)
    else:
        send_hi_button.config(state=tk.DISABLED)
        send_low_button.config(state=tk.DISABLED)
        send_both_button.config(state=tk.DISABLED)

def enable_server():
    global server_enabled
    if server_enabled:
        return
    # ...start telegram API server...
    subprocess.run([
        "powershell",
        "-command",
        f"$process = Start-Process -FilePath '{API_PATH}' -ArgumentList '--api-id','{TELEGRAM_API_ID}','--api-hash','{TELEGRAM_API_HASH}','--local' -PassThru -WindowStyle Hidden; $process.Id | Out-File -FilePath 'api_server_pid.txt' -Encoding ASCII"
    ], check=True)
    server_enabled = True
    update_server_status(server_status_circle, True)

def disable_server():
    global server_enabled
    if not server_enabled:
        return
    # ...terminate the API server...
    if os.path.exists("api_server_pid.txt"):
        with open("api_server_pid.txt", "r") as f:
            pid = f.read().strip()
        if pid:
            subprocess.run(["powershell", "-command", f"Stop-Process -Id {pid} -Force"], shell=True)
    subprocess.run(["powershell", "-command", "Stop-Process -Name 'telegram-bot-api' -Force -ErrorAction SilentlyContinue"], shell=True)

    if os.path.exists("api_server_pid.txt"):
        os.remove("api_server_pid.txt")
    server_enabled = False
    update_server_status(server_status_circle, False)

def do_garbage_collection():
    # ...replicate .bat cleanup: remove leftover files...
    if os.path.exists("api_server_pid.txt"):
        os.remove("api_server_pid.txt")
    for f in os.listdir():
        lower_f = f.lower()
        if lower_f.endswith(".pid"):
            os.remove(f)
        elif lower_f.endswith(".txt") and f not in ["bot_log.txt","credentials.txt","config.txt","download.txt"]:
            os.remove(f)
        elif lower_f.endswith(".binlog"):
            os.remove(f)
    # Check for folders containing .binlog
    for root_dir, dirs, files in os.walk(os.getcwd()):
        for fl in files:
            if fl.lower().endswith(".binlog"):
                folder_path = os.path.join(root_dir, fl)
                folder_dir = os.path.dirname(folder_path)
                if folder_dir != os.getcwd() and os.path.exists(folder_dir):
                    try:
                        os.rmdir(folder_dir)
                    except OSError:
                        subprocess.run(["rmdir", "/s", "/q", folder_dir], shell=True)

spinner_label = None
spinner_running = False

def start_spinner():
    global spinner_label, spinner_running
    spinner_running = True
    spinner_label = tk.Label(left_frame, text="")
    spinner_label.pack()
    animate_spinner()

def stop_spinner():
    global spinner_running, spinner_label
    spinner_running = False
    if spinner_label:
        spinner_label.pack_forget()
        spinner_label = None

spinner_chars = ['|', '/', '-', '\\']
spinner_index = 0

def animate_spinner():
    global spinner_index
    if not spinner_running:
        return
    spinner_label.config(text=spinner_chars[spinner_index])
    spinner_index = (spinner_index + 1) % len(spinner_chars)
    root.after(100, animate_spinner)

def on_bot_done():
    stop_spinner()
    # Only enable buttons if server is running
    if server_enabled:
        send_hi_button.config(state=tk.NORMAL)
        send_low_button.config(state=tk.NORMAL)
        send_both_button.config(state=tk.NORMAL)
    exit_button.config(state=tk.NORMAL)

def run_hi_bot():
    send_hi_button.config(state=tk.DISABLED)
    send_low_button.config(state=tk.DISABLED)
    send_both_button.config(state=tk.DISABLED)
    exit_button.config(state=tk.DISABLED)
    start_spinner()
    
    def task():
        async def run_hi_script():
            console.config(state='normal')
            console.insert('end', "> Starting FLAC albums posting (postHi)...\n", ('green',))
            console.config(state='disabled')
            
            await postHi_main()
            
            console.config(state='normal')
            console.insert('end', "> FLAC albums posting completed!\n", ('green',))
            console.config(state='disabled')
        
        asyncio.run(run_hi_script())
        root.after(0, on_bot_done)
    threading.Thread(target=task, daemon=True).start()

def run_low_bot():
    send_hi_button.config(state=tk.DISABLED)
    send_low_button.config(state=tk.DISABLED)
    send_both_button.config(state=tk.DISABLED)
    exit_button.config(state=tk.DISABLED)
    start_spinner()
    
    def task():
        async def run_low_script():
            console.config(state='normal')
            console.insert('end', "> Starting MP3 albums posting (postLow)...\n", ('green',))
            console.config(state='disabled')
            
            await postLow_main()
            
            console.config(state='normal')
            console.insert('end', "> MP3 albums posting completed!\n", ('green',))
            console.config(state='disabled')
        
        asyncio.run(run_low_script())
        root.after(0, on_bot_done)
    threading.Thread(target=task, daemon=True).start()

def run_both_bots():
    send_hi_button.config(state=tk.DISABLED)
    send_low_button.config(state=tk.DISABLED)
    send_both_button.config(state=tk.DISABLED)
    exit_button.config(state=tk.DISABLED)
    start_spinner()
    
    def task():
        async def run_both_scripts():
            console.config(state='normal')
            console.insert('end', "> Starting FLAC albums posting (postHi)...\n", ('green',))
            console.config(state='disabled')
            
            # Run postHi first
            await postHi_main()
            
            console.config(state='normal')
            console.insert('end', "> FLAC albums posting completed. Starting MP3 albums posting (postLow)...\n", ('green',))
            console.config(state='disabled')
            
            # Run postLow after postHi completes
            await postLow_main()
            
            console.config(state='normal')
            console.insert('end', "> All albums posting completed!\n", ('green',))
            console.config(state='disabled')
        
        asyncio.run(run_both_scripts())
        root.after(0, on_bot_done)
    threading.Thread(target=task, daemon=True).start()

def download_song():
    link = simpledialog.askstring("Download Song", "Enter link:")
    if not link:
        return
    download_button.config(state=tk.DISABLED)
    console.config(state='normal')
    console.insert('end', f"> Downloading FLAC (Quality 3) and MP3 (Quality 1) versions for: {link}\n", ('stdout',))
    console.config(state='disabled')
    
    def task():
        try:
            # Read the latest download paths
            read_download_paths()
            
            # Download FLAC version (Quality 3)
            console.config(state='normal')
            console.insert('end', f"> Starting FLAC download (Quality 3) to: {FLAC_PATH}\n", ('green',))
            console.config(state='disabled')
            
            flac_proc = subprocess.Popen(
                f'rip -q 3 -f "{FLAC_PATH}" --no-progress url "{link}"',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                text=True
            )
            for line in flac_proc.stdout:
                print(line, end='')
            for line in flac_proc.stderr:
                print(line, end='', file=sys.stderr)
            flac_proc.wait()
            
            console.config(state='normal')
            console.insert('end', f"> FLAC download completed\n", ('green',))
            console.config(state='disabled')
            
            # Download MP3 version (Quality 1)
            console.config(state='normal')
            console.insert('end', f"> Starting MP3 download (Quality 1) to: {MP3_PATH}\n", ('green',))
            console.config(state='disabled')
            
            mp3_proc = subprocess.Popen(
                f'rip -q 1 -f "{MP3_PATH}" --no-progress url "{link}"',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                text=True
            )
            for line in mp3_proc.stdout:
                print(line, end='')
            for line in mp3_proc.stderr:
                print(line, end='', file=sys.stderr)
            mp3_proc.wait()
            
            console.config(state='normal')
            console.insert('end', f"> MP3 download completed\n", ('green',))
            console.insert('end', f"> All downloads finished!\n", ('green',))
            console.config(state='disabled')
            
        except Exception as e:
            console.config(state='normal')
            console.insert('end', f"Error during download: {e}\n", ('stderr',))
            console.config(state='disabled')
        finally:
            root.after(0, lambda: download_button.config(state=tk.NORMAL))
    
    threading.Thread(target=task, daemon=True).start()

def exit_app():
    if server_enabled:
        disable_server()
    do_garbage_collection()
    root.destroy()

root = tk.Tk()
root.title("Hires Bot GUI")

# Left controls
left_frame = tk.Frame(root)
left_frame.pack(side=tk.LEFT, padx=10, pady=10)

send_hi_button = tk.Button(left_frame, text="Send FLAC Albums", command=run_hi_bot, state=tk.DISABLED)
send_hi_button.pack(padx=5, pady=5)

send_low_button = tk.Button(left_frame, text="Send MP3 Albums", command=run_low_bot, state=tk.DISABLED)
send_low_button.pack(padx=5, pady=5)

send_both_button = tk.Button(left_frame, text="Send All Albums", command=run_both_bots, state=tk.DISABLED)
send_both_button.pack(padx=5, pady=5)

download_button = tk.Button(left_frame, text="Download Song", command=download_song)
download_button.pack(padx=5, pady=5)

exit_button = tk.Button(left_frame, text="Exit", command=exit_app)
exit_button.pack(padx=5, pady=5)

# Middle console panel
middle_frame = tk.Frame(root)
middle_frame.pack(side=tk.LEFT, padx=10, pady=10, expand=True, fill=tk.BOTH)

console = scrolledtext.ScrolledText(middle_frame, state='disabled', width=80, height=20)
console.pack(expand=True, fill=tk.BOTH)
console.tag_config('stdout', foreground='black')
console.tag_config('stderr', foreground='red')
console.tag_config('red', foreground='red')
console.tag_config('green', foreground='green')
console.tag_config('yellow', foreground='goldenrod')
console.tag_config('blue', foreground='blue')
ANSI_PATTERN = re.compile(r'(\x1b\[[0-9;]*m)')

class TextRedirector:
    def __init__(self, widget, default_tag):
        self.widget = widget
        self.default_tag = default_tag
        self.current_tags = (default_tag,)

    def write(self, msg):
        self.widget.configure(state='normal')
        parts = ANSI_PATTERN.split(msg)
        for part in parts:
            if ANSI_PATTERN.match(part):
                # parse codes like "\x1b[31m"
                codes = part[2:-1].split(';')
                # reset on code "0"
                if '0' in codes:
                    self.current_tags = (self.default_tag,)
                # simple color mapping
                if '31' in codes:
                    self.current_tags = ('red',)
                elif '32' in codes:
                    self.current_tags = ('green',)
                elif '33' in codes:
                    self.current_tags = ('yellow',)
                elif '34' in codes:
                    self.current_tags = ('blue',)
                continue
            # handle carriage return: delete current line before writing
            if '\r' in part:
                # move to end, then delete back to line start
                self.widget.mark_set("insert", "end")
                self.widget.delete("insert linestart", "insert")
                part = part.replace('\r', '')
            if part:
                self.widget.insert('end', part, self.current_tags)
        self.widget.configure(state='disabled')
        self.widget.see('end')

    def flush(self):
        pass

sys.stdout = TextRedirector(console, 'stdout')
sys.stderr = TextRedirector(console, 'stderr')

# Right server controls
right_frame = tk.Frame(root)
right_frame.pack(side=tk.RIGHT, padx=10, pady=10)

tk.Label(right_frame, text="Bot API Server").pack()
server_status_circle = tk.Canvas(right_frame, width=20, height=20, highlightthickness=0)
server_status_circle.pack()
server_status_circle.create_oval(2, 2, 18, 18, fill="red")

enable_button = tk.Button(right_frame, text="Enable", bg="green", command=enable_server)
enable_button.pack(padx=5, pady=5)

disable_button = tk.Button(right_frame, text="Disable", bg="red", command=disable_server)
disable_button.pack(padx=5, pady=5)

root.mainloop()