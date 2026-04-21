import logging
from pathlib import Path
from typing import Any, Callable

tk: Any
try:
    import tkinter

    tk = tkinter

    tkinter_available = True
except ImportError:
    tkinter_available = False

    # Create a fake tk module that allows type hints to not cause a failure
    class _FakeTk:
        class Tk:
            pass

        Toplevel = None
        Frame = None
        Label = None
        TclError = Exception

    tk = _FakeTk

logger = logging.getLogger(__name__)

SPLASH_IMAGE = Path(__file__).resolve().parent.parent / "resources" / "splash.png"
TITLE_TEXT = "SCADview"
MESSAGE_TEXT = "First run may take longer to initialize; please wait..."


class NullRoot:
    """A dummy root  when we don't need a real Tk root."""

    def after(self, ms: int, _func: Callable[[], Any]) -> None:
        pass

    def mainloop(self) -> None:
        pass

    def destroy(self) -> None:
        pass


class NullSplash:
    """A dummy splash window when we don't need a real one."""

    def destroy(self) -> None:
        pass


def create_splash_window() -> tuple[Any, Any]:
    """Create and show the splash window."""
    logger.warning(f"***** {MESSAGE_TEXT} *****")
    if not tkinter_available:
        logger.warning("The splash screen is not available so it will not be shown.")
        return NullRoot(), NullSplash()
    root = _create_tk_root()
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)

    try:
        splash.attributes("-topmost", True)
    except tk.TclError:
        pass

    # Container frame (so text + image are together)
    frame = _create_frame(splash)
    _add_title(frame)
    _add_image(splash, str(SPLASH_IMAGE), frame)
    _add_message(frame)
    _center_window(splash)

    # Bring to front (Windows can be picky)
    splash.lift()
    splash.update_idletasks()
    splash.after(10, lambda: splash.lift())

    return root, splash


def _create_tk_root() -> Any:
    # Hidden root; splash is a Toplevel
    # On Windows, can't seem to use the root as the splash
    root = tk.Tk()
    root.withdraw()
    return root


def _create_frame(parent: Any) -> Any:
    frame = tk.Frame(parent, bg="white", padx=20, pady=20)
    frame.pack()
    return frame


def _add_title(frame: Any) -> None:
    title_label = tk.Label(
        frame, text=TITLE_TEXT, font=("Helvetica", 20, "bold"), bg="white", fg="#333"
    )
    title_label.pack(pady=(0, 10))


def _add_message(frame: Any) -> None:
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


def _add_image(window: Any, image_path: str, frame: Any) -> None:
    if not Path(image_path).is_file():
        logger.warning(f"splash image not found at {image_path}")
        return

    try:
        img = tk.PhotoImage(file=image_path)
    except tk.TclError as e:
        logger.debug(f"Failed to load image '{image_path}': {e}")
        return

    # Keep reference to avoid garbage collection
    setattr(window, "_splash_image", img)
    img_label = tk.Label(frame, image=img, bg="white")
    img_label.pack()


def _center_window(win: Any) -> None:
    win.update_idletasks()
    w = win.winfo_width()
    h = win.winfo_height()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    logger.debug(f"geometry w={w}, h={h}, sw={sw}, sh={sh}")

    if w <= 0 or h <= 0 or sw <= 0 or sh <= 0:
        # Fallback: let Tk choose, do not force geometry
        return

    x = (sw - w) // 2
    y = (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")
