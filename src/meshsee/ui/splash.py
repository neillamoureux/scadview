import tkinter as tk
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from pathlib import Path

SPLASH_IMAGE = Path(__file__) / ".." / ".." / "resources" / "splash.png"
SPLASH_MIN_DISPLAY_TIME_MS = 1000
CHECK_INTERVAL_MS = 100
TITLE_TEXT = "Meshsee"
MESSAGE_TEXT = "First run may take longer to initialize; please wait..."


def start_splash_process():
    """Helper to start splash and return (process, parent_conn)."""
    parent_conn, child_conn = Pipe()
    p = Process(target=splash_worker, args=(str(SPLASH_IMAGE), child_conn))
    p.start()
    return parent_conn


def stop_splash_process(conn: Connection):
    """Helper to stop splash process."""
    conn.send("CLOSE")
    pass


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

    # Container frame (so text + image are together)
    frame = create_frame(root)
    add_title(frame)
    add_message(frame)
    add_image(root, image_path, frame)
    center_frame(root, frame)


def create_frame(root: tk.Tk) -> tk.Frame:
    frame = tk.Frame(root, bg="white", padx=20, pady=20)
    frame.pack()
    return frame


def add_title(frame: tk.Frame):
    title_label = tk.Label(
        frame, text=TITLE_TEXT, font=("Helvetica", 20, "bold"), bg="white", fg="#333"
    )
    title_label.pack(pady=(0, 10))


def add_message(frame: tk.Frame):
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


def add_image(root: tk.Tk, image_path: str, frame: tk.Frame):
    img = tk.PhotoImage(file=image_path)
    # Keep reference to avoid garbage collection
    root._splash_image = img  # type: ignore[attr-defined]
    img_label = tk.Label(frame, image=img, bg="white")
    img_label.pack()


def center_frame(root: tk.Tk, frame: tk.Frame):
    root.update_idletasks()
    w = frame.winfo_width()
    h = frame.winfo_height()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()

    x = (sw - w) // 2
    y = (sh - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
