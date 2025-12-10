import tkinter as tk
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from pathlib import Path
from tkinter import TclError

SPLASH_IMAGE = (
    Path(__file__).resolve()
    .parent.parent  
    / "resources"
    / "splash.png"
)
SPLASH_MIN_DISPLAY_TIME_MS = 1000
CHECK_INTERVAL_MS = 100
TITLE_TEXT = "Meshsee"
MESSAGE_TEXT = "First run may take longer to initialize; please wait..."


def start_splash_process() -> Connection:
    """Helper to start splash and return parent_conn."""
    parent_conn, child_conn = Pipe()
    p = Process(target=splash_worker, args=(str(SPLASH_IMAGE), child_conn))
    p.start()
    return parent_conn


def stop_splash_process(conn: Connection) -> None:
    """Helper to stop splash process."""
    try:
        conn.send("CLOSE")
    except OSError:
        # Child may already be gone; ignore
        pass


def splash_worker(image_path: str, conn: Connection) -> None:
    """Runs in a separate process: show Tk splash until told to close."""
    print(f"[splash] worker starting, image_path={image_path}")
    root = create_tk_root()
    splash = create_splash_window(root, image_path)

    def check_pipe():
        if conn.poll():
            msg = conn.recv()
            print(f"[splash] received message: {msg}")
            if msg == "CLOSE":
                splash.destroy()
                root.destroy()
                return
        root.after(CHECK_INTERVAL_MS, check_pipe)

    # enforce minimum display time before we even look at the pipe
    root.after(SPLASH_MIN_DISPLAY_TIME_MS, check_pipe)
    root.mainloop()


def create_tk_root() -> tk.Tk:
    # Hidden root; splash is a Toplevel
    # On Windows, can't seem to use the root as the splash
    root = tk.Tk()
    root.withdraw()
    return root


def create_splash_window(root: tk.Tk, image_path: str) -> tk.Toplevel:
    """Create and show the splash window."""
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)

    try:
        splash.attributes("-topmost", True)
    except tk.TclError:
        pass

    # Container frame (so text + image are together)
    frame = create_frame(splash)
    add_title(frame)
    add_message(frame)
    add_image(splash, image_path, frame)
    center_window(splash)

    # Bring to front (Windows can be picky)
    splash.lift()
    splash.update_idletasks()
    splash.after(10, lambda: splash.lift())

    return splash


def create_frame(parent: tk.Tk | tk.Toplevel) -> tk.Frame:
    frame = tk.Frame(parent, bg="white", padx=20, pady=20)
    frame.pack()
    return frame


def add_title(frame: tk.Frame) -> None:
    title_label = tk.Label(
        frame, text=TITLE_TEXT, font=("Helvetica", 20, "bold"), bg="white", fg="#333"
    )
    title_label.pack(pady=(0, 10))


def add_message(frame: tk.Frame) -> None:
    message_label = tk.Label(
        frame,
        text=MESSAGE_TEXT,
        font=("Helvetica", 12),
        bg="white",
        fg="#666",
        wraplength=400,
        justify="center",
    )
    message_label.pack(pady=(0, 12))


def add_image(window: tk.Tk | tk.Toplevel, image_path: str, frame: tk.Frame) -> None:
    if not Path(image_path).is_file():
        print(f"[splash] WARNING: splash image not found at {image_path}")
        return

    try:
        img = tk.PhotoImage(file=image_path)
    except TclError as e:
        print(f"[splash] Failed to load image '{image_path}': {e}")
        return

    # Keep reference to avoid garbage collection
    window._splash_image = img  # type: ignore[attr-defined]
    img_label = tk.Label(frame, image=img, bg="white")
    img_label.pack()


def center_window(win: tk.Tk | tk.Toplevel) -> None:
    win.update_idletasks()
    w = win.winfo_width()
    h = win.winfo_height()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    print(f"[splash] geometry w={w}, h={h}, sw={sw}, sh={sh}")

    if w <= 0 or h <= 0 or sw <= 0 or sh <= 0:
        # Fallback: let Tk choose, do not force geometry
        return

    x = (sw - w) // 2
    y = (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")
