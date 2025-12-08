# splash_proc.py (you can also keep this in the same file; shown separate for clarity)
from multiprocessing import Process, Pipe
from multiprocessing.connection import Connection
from pathlib import Path
import tkinter as tk
from time import sleep

SPLASH_IMAGE = Path(__file__) / ".." / ".." / "resources" / "splash.png"


def splash_worker(image_path: str, conn: Connection):
    """Runs in a separate process: show Tk splash until told to close."""
    root = tk.Tk()
    root.overrideredirect(True)

    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass

    img = tk.PhotoImage(file=image_path)

    w, h = img.width(), img.height()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")

    label = tk.Label(root, image=img, borderwidth=0, highlightthickness=0)
    label.pack()

    # keep ref
    root._splash_image = img  # type: ignore[attr-defined]

    def check_pipe():
        # Check if main process sent a message
        if conn.poll():
            msg = conn.recv()
            if msg == "CLOSE":
                root.destroy()
                return
        # Check again in 100 ms
        root.after(100, check_pipe)

    root.after(1000, check_pipe)
    root.mainloop()


def start_splash_process():
    """Helper to start splash and return (process, parent_conn)."""
    parent_conn, child_conn = Pipe()
    p = Process(target=splash_worker, args=(str(SPLASH_IMAGE), child_conn))
    p.start()
    return p, parent_conn
