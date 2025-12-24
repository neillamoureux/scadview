from __future__ import annotations

import argparse
import logging
import logging.handlers
import multiprocessing as mp
import multiprocessing.queues as mp_queues

LOG_QUEUE_SIZE = 1000

log_queue: mp_queues.Queue[logging.LogRecord] = mp.Queue(maxsize=LOG_QUEUE_SIZE)


class MainProcessLevelFilter(logging.Filter):
    def __init__(self, min_level: int) -> None:
        super().__init__()
        self._min_level = min_level

    def filter(self, record: logging.LogRecord) -> bool:
        return not (
            record.processName == "MainProcess" and record.levelno < self._min_level
        )


def configure_logging(
    log_level: int, main_process_level: int | None = None
) -> logging.handlers.QueueListener:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(log_level)

    formatter = logging.Formatter(
        "%(asctime)s [%(processName)s %(process)d] %(levelname)s %(name)s: %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.DEBUG)
    console.addFilter(MainProcessLevelFilter(main_process_level or log_level))
    root.addHandler(console)

    listener = logging.handlers.QueueListener(
        log_queue,
        console,
        respect_handler_level=True,
    )
    listener.start()

    return listener


def get_logging_level_from_args(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v=INFO, -vv=DEBUG)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level directly",
    )

    parsed = parser.parse_args(args=args)

    if parsed.log_level:
        return getattr(logging, parsed.log_level)
    if parsed.verbose == 1:
        return logging.INFO
    if parsed.verbose >= 2:
        return logging.DEBUG
    return logging.WARNING


def parse_logging_level() -> int:
    level = get_logging_level_from_args()

    logger = logging.getLogger()
    logger.warning(f"Setting logging to {level} ({logging.getLevelName(level)})")
    logger.setLevel(level=level)
    return level
