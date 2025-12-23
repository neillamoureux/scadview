from __future__ import annotations

import logging
import multiprocessing.queues as mp_queues
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection

from meshsee.logging_main import log_queue
from meshsee.logging_worker import configure_worker_logging
from meshsee.ui.splash_window import (
    create_splash_window,  # type: ignore[reportUnknownVariableType]
)

logger = logging.getLogger(__name__)

SPLASH_MIN_DISPLAY_TIME_MS = 1000
CHECK_INTERVAL_MS = 100


def start_splash_process() -> Connection:
    """Helper to start splash and return parent_conn."""
    parent_conn, child_conn = Pipe()
    p = Process(target=_splash_worker, args=(child_conn, log_queue))
    p.start()
    return parent_conn


def stop_splash_process(conn: Connection) -> None:
    """Helper to stop splash process."""
    try:
        conn.send("CLOSE")
    except OSError:
        # Child may already be gone; ignore
        pass


def _splash_worker(conn: Connection, log_q: mp_queues.Queue[logging.LogRecord]) -> None:
    """Runs in a separate process: show Tk splash until told to close."""
    configure_worker_logging(log_q)
    logger.debug("worker starting")
    root, splash = create_splash_window()  # type: ignore[reportUnknownVariableType]

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
