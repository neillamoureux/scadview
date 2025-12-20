import logging
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from pathlib import Path

from meshsee.logconfig import setup_logging
from meshsee.ui.splash_window import (
    create_splash_window,  # type: ignore[reportUnknownVariableType]
)

logger = logging.getLogger(__name__)

SPLASH_IMAGE = Path(__file__).resolve().parent.parent / "resources" / "splash.png"
SPLASH_MIN_DISPLAY_TIME_MS = 1000
CHECK_INTERVAL_MS = 100
TITLE_TEXT = "Meshsee"
MESSAGE_TEXT = "First run may take longer to initialize; please wait..."


def start_splash_process() -> Connection:
    """Helper to start splash and return parent_conn."""
    parent_conn, child_conn = Pipe()
    p = Process(target=_splash_worker, args=(str(SPLASH_IMAGE), child_conn))
    p.start()
    return parent_conn


def stop_splash_process(conn: Connection) -> None:
    """Helper to stop splash process."""
    try:
        conn.send("CLOSE")
    except OSError:
        # Child may already be gone; ignore
        pass


def _splash_worker(image_path: str, conn: Connection) -> None:
    """Runs in a separate process: show Tk splash until told to close."""
    setup_logging()
    logger.debug(f"worker starting, image_path={image_path}")
    root, splash = create_splash_window(image_path)  # type: ignore[reportUnknownVariableType]

    def check_pipe():
        if conn.poll():
            msg = conn.recv()
            logger.debug(f"received message: {msg}")
            if msg == "CLOSE":
                splash.destroy()
                root.destroy()
                return
        root.after(CHECK_INTERVAL_MS, check_pipe)

    # enforce minimum display time before we even look at the pipe
    root.after(SPLASH_MIN_DISPLAY_TIME_MS, check_pipe)
    root.mainloop()
