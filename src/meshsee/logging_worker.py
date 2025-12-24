from __future__ import annotations

import logging
import logging.handlers
import multiprocessing.queues as mp_queues


def configure_worker_logging(
    log_queue: mp_queues.Queue[logging.LogRecord], log_level: int = logging.DEBUG
) -> None:
    queue_handler = logging.handlers.QueueHandler(log_queue)
    queue_handler.setLevel(log_level)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(queue_handler)
    root.setLevel(log_level)
