import tkinter as tk
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from pathlib import Path

SPLASH_IMAGE = Path(__file__) / ".." / ".." / "resources" / "splash.png"
SPLASH_MIN_DISPLAY_TIME_MS = 1000
CHECK_INTERVAL_MS = 100


def start_splash_process():
    """Helper to start splash and return (process, parent_conn)."""
    parent_conn, child_conn = Pipe()
    p = Process(target=splash_worker, args=(str(SPLASH_IMAGE), child_conn))
    p.start()
    return parent_conn


def stop_splash_process(conn: Connection):
    """Helper to stop splash process."""
    conn.send("CLOSE")


def splash_worker(image_path: str, conn: Connection):
    """Runs in a separate process: show Tk splash until told to close."""
    root = create_tk_root()
    create_splash_window(root, image_path)

    def check_pipe():
        # Check if main process sent a message
        if conn.poll():
            msg = conn.recv()
            if msg == "CLOSE":
                root.destroy()
                return
        # Check again in CHECK_INTERVAL_MS ms
        root.after(CHECK_INTERVAL_MS, check_pipe)

    root.after(SPLASH_MIN_DISPLAY_TIME_MS, check_pipe)
    root.mainloop()


def create_tk_root():
    root = tk.Tk()
    root.overrideredirect(True)

    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    return root


def create_splash_window(root: tk.Tk, image_path: str):
    """Create and show the splash window."""
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
