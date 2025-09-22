import os
import signal
import subprocess
import tkinter as tk
from threading import Thread

import webview

# Path to your Django project directory
PROJECT_DIR = "D:\khushbu darji\GreyMarket"
MANAGE_PY = os.path.join(PROJECT_DIR, "manage.py")


# Start Django runserver in a subprocess
def run_django():
    global django_process
    django_process = subprocess.Popen(
        ["python", MANAGE_PY, "runserver", "127.0.0.1:8000"], cwd=PROJECT_DIR
    )


# Handle window close
def on_close():
    if django_process:
        os.kill(django_process.pid, signal.SIGTERM)
    window.destroy()


# Start Django server in a thread
django_thread = Thread(target=run_django)
django_thread.start()

# Create Tkinter window
window = tk.Tk()
window.protocol("WM_DELETE_WINDOW", on_close)

# Create webview
webview.create_window(
    "Ipo Utility", "http://127.0.0.1:8000", x=0, y=0, width=1024, height=768
)
webview.start(gui="tk")

on_close()
