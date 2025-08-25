import tkinter as tk
import asyncio
import subprocess
import os
import sys
import threading
from tkinter import scrolledtext, ttk
import tkinter.simpledialog as simpledialog
from postHi import main as postHi_main
from postLow import main as postLow_main
import re
from collections import deque

API_PATH = None
PY_PATH = None
TELEGRAM_API_ID   = None
TELEGRAM_API_HASH = None
FLAC_PATH = None
MP3_PATH = None
RIP_PATH = "C:/Users/amira/AppData/Local/Programs/Python/Python311/Scripts/rip.exe"
server_enabled = False

# Download queue variables
download_queue = deque()
downloading = False

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
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def run_hi_script():
                console.config(state='normal')
                console.insert('end', "> Starting FLAC albums posting (postHi)...\n", ('green',))
                console.config(state='disabled')
                
                await postHi_main()
                
                console.config(state='normal')
                console.insert('end', "> FLAC albums posting completed!\n", ('green',))
                console.config(state='disabled')
            
            loop.run_until_complete(run_hi_script())
        finally:
            # Clean up the event loop
            loop.close()
            root.after(0, on_bot_done)
    threading.Thread(target=task, daemon=True).start()

def run_low_bot():
    send_hi_button.config(state=tk.DISABLED)
    send_low_button.config(state=tk.DISABLED)
    send_both_button.config(state=tk.DISABLED)
    exit_button.config(state=tk.DISABLED)
    start_spinner()
    
    def task():
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def run_low_script():
                console.config(state='normal')
                console.insert('end', "> Starting MP3 albums posting (postLow)...\n", ('green',))
                console.config(state='disabled')
                
                await postLow_main()
                
                console.config(state='normal')
                console.insert('end', "> MP3 albums posting completed!\n", ('green',))
                console.config(state='disabled')
            
            loop.run_until_complete(run_low_script())
        finally:
            # Clean up the event loop
            loop.close()
            root.after(0, on_bot_done)
    threading.Thread(target=task, daemon=True).start()

def run_both_bots():
    send_hi_button.config(state=tk.DISABLED)
    send_low_button.config(state=tk.DISABLED)
    send_both_button.config(state=tk.DISABLED)
    exit_button.config(state=tk.DISABLED)
    start_spinner()
    
    def task():
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
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
            
            loop.run_until_complete(run_both_scripts())
        finally:
            # Clean up the event loop
            loop.close()
            root.after(0, on_bot_done)
    threading.Thread(target=task, daemon=True).start()

def add_to_queue():
    link = url_entry.get().strip()
    if not link:
        console.config(state='normal')
        console.insert('end', "> Please enter a link\n", ('red',))
        console.config(state='disabled')
        return
    
    flac_selected = flac_var.get()
    mp3_selected = mp3_var.get()
    
    if not flac_selected and not mp3_selected:
        console.config(state='normal')
        console.insert('end', "> Please select at least one quality option\n", ('red',))
        console.config(state='disabled')
        return
    
    # Add to queue
    queue_item = {
        'link': link,
        'flac': flac_selected,
        'mp3': mp3_selected
    }
    download_queue.append(queue_item)
    
    # Update queue display
    update_queue_display()
    
    # Clear the input
    url_entry.delete(0, tk.END)
    
    console.config(state='normal')
    qualities = []
    if flac_selected:
        qualities.append("FLAC")
    if mp3_selected:
        qualities.append("MP3")
    console.insert('end', f"> Added to queue: {link} ({', '.join(qualities)})\n", ('green',))
    console.config(state='disabled')

def update_queue_display():
    queue_listbox.delete(0, tk.END)
    for i, item in enumerate(download_queue):
        qualities = []
        if item['flac']:
            qualities.append("FLAC")
        if item['mp3']:
            qualities.append("MP3")
        display_text = f"{item['link']} - {', '.join(qualities)}"
        queue_listbox.insert(tk.END, display_text)
    
    # Update status label
    count = len(download_queue)
    status_text = f"Queue: {count} item{'s' if count != 1 else ''}"
    if downloading:
        status_text += " (Downloading...)"
    queue_status_label.config(text=status_text)

def clear_queue():
    global download_queue
    if downloading:
        console.config(state='normal')
        console.insert('end', "> Cannot clear queue while downloading\n", ('red',))
        console.config(state='disabled')
        return
    
    download_queue.clear()
    update_queue_display()
    console.config(state='normal')
    console.insert('end', "> Queue cleared\n", ('green',))
    console.config(state='disabled')

def remove_selected():
    selection = queue_listbox.curselection()
    if not selection:
        console.config(state='normal')
        console.insert('end', "> Please select an item to remove\n", ('red',))
        console.config(state='disabled')
        return
    
    if downloading:
        console.config(state='normal')
        console.insert('end', "> Cannot remove items while downloading\n", ('red',))
        console.config(state='disabled')
        return
    
    index = selection[0]
    if 0 <= index < len(download_queue):
        removed_item = list(download_queue)[index]
        # Convert deque to list, remove item, convert back
        queue_list = list(download_queue)
        queue_list.pop(index)
        download_queue.clear()
        download_queue.extend(queue_list)
        update_queue_display()
        console.config(state='normal')
        console.insert('end', f"> Removed from queue: {removed_item['link']}\n", ('green',))
        console.config(state='disabled')

def download_from_queue():
    global downloading
    if downloading:
        console.config(state='normal')
        console.insert('end', "> Download already in progress\n", ('red',))
        console.config(state='disabled')
        return
    
    if not download_queue:
        console.config(state='normal')
        console.insert('end', "> Queue is empty\n", ('red',))
        console.config(state='disabled')
        return
    
    downloading = True
    download_button.config(state=tk.DISABLED)
    add_queue_button.config(state=tk.DISABLED)
    clear_queue_button.config(state=tk.DISABLED)
    remove_button.config(state=tk.DISABLED)
    
    def task():
        try:
            # Read the latest download paths
            read_download_paths()
            
            total_items = len(download_queue)
            console.config(state='normal')
            console.insert('end', f"> Starting download of {total_items} items from queue\n", ('green',))
            console.config(state='disabled')
            
            current_item = 0
            while download_queue:
                current_item += 1
                item = download_queue.popleft()
                link = item['link']
                
                console.config(state='normal')
                console.insert('end', f"> [{current_item}/{total_items}] Processing: {link}\n", ('blue',))
                console.config(state='disabled')
                
                # Download FLAC first if selected
                if item['flac']:
                    console.config(state='normal')
                    console.insert('end', f"> Starting FLAC download (Quality 3) to: {FLAC_PATH}\n", ('green',))
                    console.config(state='disabled')
                    
                    flac_proc = subprocess.Popen(
                        f'"{RIP_PATH}" --no-progress -q 3 -f "{FLAC_PATH}" url "{link}"',
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        shell=True,
                        text=True
                    )
                    
                    # Read output in real-time
                    for line in flac_proc.stdout:
                        if line.strip():
                            console.config(state='normal')
                            console.insert('end', f"[FLAC] {line}", ('blue',))
                            console.config(state='disabled')
                            console.update()
                    
                    flac_proc.wait()
                    
                    if flac_proc.returncode == 0:
                        console.config(state='normal')
                        console.insert('end', f"> FLAC download completed successfully\n", ('green',))
                        console.config(state='disabled')
                    else:
                        console.config(state='normal')
                        console.insert('end', f"> FLAC download failed (exit code: {flac_proc.returncode})\n", ('red',))
                        console.config(state='disabled')
                
                # Download MP3 if selected
                if item['mp3']:
                    console.config(state='normal')
                    console.insert('end', f"> Starting MP3 download (Quality 1) to: {MP3_PATH}\n", ('green',))
                    console.config(state='disabled')
                    
                    mp3_proc = subprocess.Popen(
                        f'"{RIP_PATH}" --no-progress -q 1 -f "{MP3_PATH}" url "{link}"',
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        shell=True,
                        text=True
                    )
                    
                    # Read output in real-time
                    for line in mp3_proc.stdout:
                        if line.strip():
                            console.config(state='normal')
                            console.insert('end', f"[MP3] {line}", ('blue',))
                            console.config(state='disabled')
                            console.update()
                    
                    mp3_proc.wait()
                    
                    if mp3_proc.returncode == 0:
                        console.config(state='normal')
                        console.insert('end', f"> MP3 download completed successfully\n", ('green',))
                        console.config(state='disabled')
                    else:
                        console.config(state='normal')
                        console.insert('end', f"> MP3 download failed (exit code: {mp3_proc.returncode})\n", ('red',))
                        console.config(state='disabled')
                
                # Update queue display after each item
                root.after(0, update_queue_display)
            
            console.config(state='normal')
            console.insert('end', f"> All downloads completed!\n", ('green',))
            console.config(state='disabled')
            
        except Exception as e:
            console.config(state='normal')
            console.insert('end', f"Error during download: {e}\n", ('stderr',))
            console.config(state='disabled')
        finally:
            def reset_buttons():
                global downloading
                downloading = False
                download_button.config(state=tk.NORMAL)
                add_queue_button.config(state=tk.NORMAL)
                clear_queue_button.config(state=tk.NORMAL)
                remove_button.config(state=tk.NORMAL)
                update_queue_display()
            
            root.after(0, reset_buttons)
    
    threading.Thread(target=task, daemon=True).start()

def exit_app():
    if server_enabled:
        disable_server()
    do_garbage_collection()
    root.destroy()

root = tk.Tk()
root.title("Hires Bot GUI")
root.geometry("1200x700")

# Create main container with three sections
main_container = tk.Frame(root)
main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Left controls frame
left_frame = tk.Frame(main_container)
left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

# Bot controls section
bot_controls_frame = tk.LabelFrame(left_frame, text="Bot Controls", padx=5, pady=5)
bot_controls_frame.pack(fill=tk.X, pady=(0, 10))

send_hi_button = tk.Button(bot_controls_frame, text="Send FLAC Albums", command=run_hi_bot, state=tk.DISABLED)
send_hi_button.pack(fill=tk.X, pady=2)

send_low_button = tk.Button(bot_controls_frame, text="Send MP3 Albums", command=run_low_bot, state=tk.DISABLED)
send_low_button.pack(fill=tk.X, pady=2)

send_both_button = tk.Button(bot_controls_frame, text="Send All Albums", command=run_both_bots, state=tk.DISABLED)
send_both_button.pack(fill=tk.X, pady=2)

# Download section
download_frame = tk.LabelFrame(left_frame, text="Download Manager", padx=5, pady=5)
download_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

# URL input
tk.Label(download_frame, text="URL:").pack(anchor=tk.W)
url_entry = tk.Entry(download_frame, width=40)
url_entry.pack(fill=tk.X, pady=(0, 5))
url_entry.bind('<Return>', lambda event: add_to_queue())

# Quality selection
quality_frame = tk.Frame(download_frame)
quality_frame.pack(fill=tk.X, pady=(0, 5))

tk.Label(quality_frame, text="Quality:").pack(anchor=tk.W)
flac_var = tk.BooleanVar(value=True)
mp3_var = tk.BooleanVar(value=True)

flac_check = tk.Checkbutton(quality_frame, text="FLAC (Quality 3)", variable=flac_var)
flac_check.pack(anchor=tk.W)

mp3_check = tk.Checkbutton(quality_frame, text="MP3 (Quality 1)", variable=mp3_var)
mp3_check.pack(anchor=tk.W)

# Queue management buttons
buttons_frame = tk.Frame(download_frame)
buttons_frame.pack(fill=tk.X, pady=(0, 5))

add_queue_button = tk.Button(buttons_frame, text="Add to Queue", command=add_to_queue)
add_queue_button.pack(side=tk.LEFT, padx=(0, 2))

download_button = tk.Button(buttons_frame, text="Download", command=download_from_queue, bg="lightgreen")
download_button.pack(side=tk.LEFT, padx=2)

# Queue display
queue_status_label = tk.Label(download_frame, text="Queue: 0 items")
queue_status_label.pack(anchor=tk.W, pady=(5, 2))

queue_frame = tk.Frame(download_frame)
queue_frame.pack(fill=tk.BOTH, expand=True)

queue_listbox = tk.Listbox(queue_frame, height=8)
queue_scrollbar = tk.Scrollbar(queue_frame, orient=tk.VERTICAL, command=queue_listbox.yview)
queue_listbox.config(yscrollcommand=queue_scrollbar.set)
queue_listbox.bind('<Delete>', lambda event: remove_selected())

queue_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
queue_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Queue control buttons
queue_buttons_frame = tk.Frame(download_frame)
queue_buttons_frame.pack(fill=tk.X, pady=(5, 0))

remove_button = tk.Button(queue_buttons_frame, text="Remove Selected", command=remove_selected)
remove_button.pack(side=tk.LEFT, padx=(0, 2))

clear_queue_button = tk.Button(queue_buttons_frame, text="Clear Queue", command=clear_queue)
clear_queue_button.pack(side=tk.LEFT)

# Exit button
exit_button = tk.Button(left_frame, text="Exit", command=exit_app)
exit_button.pack(fill=tk.X)

# Middle console panel
middle_frame = tk.Frame(main_container)
middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

console_label = tk.Label(middle_frame, text="Console Output")
console_label.pack(anchor=tk.W)

console = scrolledtext.ScrolledText(middle_frame, state='disabled', width=60, height=35)
console.pack(fill=tk.BOTH, expand=True)
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
right_frame = tk.Frame(main_container)
right_frame.pack(side=tk.RIGHT, fill=tk.Y)

server_controls_frame = tk.LabelFrame(right_frame, text="Bot API Server", padx=5, pady=5)
server_controls_frame.pack(fill=tk.X)

server_status_circle = tk.Canvas(server_controls_frame, width=20, height=20, highlightthickness=0)
server_status_circle.pack(pady=(0, 5))
server_status_circle.create_oval(2, 2, 18, 18, fill="red")

enable_button = tk.Button(server_controls_frame, text="Enable", bg="lightgreen", command=enable_server)
enable_button.pack(fill=tk.X, pady=2)

disable_button = tk.Button(server_controls_frame, text="Disable", bg="lightcoral", command=disable_server)
disable_button.pack(fill=tk.X, pady=2)

# Initialize the queue display
update_queue_display()

root.mainloop()