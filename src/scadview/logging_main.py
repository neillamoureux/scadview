from __future__ import annotations

import argparse
import logging
import logging.handlers
import multiprocessing as mp
import multiprocessing.queues as mp_queues

LOG_QUEUE_SIZE = 1000
DEFAULT_LOG_LEVEL = logging.WARNING

log_queue: mp_queues.Queue[logging.LogRecord] = mp.Queue(maxsize=LOG_QUEUE_SIZE)


def configure_logging(log_level: int) -> logging.handlers.QueueListener:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(log_level)

    formatter = logging.Formatter(
        "%(asctime)s [%(processName)s %(process)d] %(levelname)s %(name)s: %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(log_level)
    root.addHandler(console)

    listener = logging.handlers.QueueListener(
        log_queue,
        console,
        respect_handler_level=False,
    )
    listener.start()

    return listener


def parse_logging_level() -> argparse.Namespace:
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
    parser.add_argument(
        "--debug-info-file",
        help="Write debug information JSON to this file path",
    )
    parser.add_argument(
        "--debug-info-redact-sensitive",
        dest="debug_info_redact_sensitive",
        action="store_true",
        default=True,
        help="Redact sensitive values in debug information output (default: enabled)",
    )
    parser.add_argument(
        "--no-debug-info-redact-sensitive",
        dest="debug_info_redact_sensitive",
        action="store_false",
        help="Disable sensitive value redaction in debug information output",
    )

    args = parser.parse_args()

    if args.log_level:
        level = getattr(logging, args.log_level)
    elif args.verbose == 1:
        level = logging.INFO
    elif args.verbose >= 2:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    logger = logging.getLogger()
    logger.warning(f"Setting logging to {level} ({logging.getLevelName(level)})")
    logger.setLevel(level=level)
    for handler in logger.handlers:
        handler.setLevel(level=level)

    return args
