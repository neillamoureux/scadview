import argparse
import logging


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if setup_logging() is called more than once
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - [%(threadName)s] - %(message)s"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)


def set_logging_level():
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
    logger.warning(f"Setting debug to {level} ({logging.getLevelName(level)})")
    logger.setLevel(level=level)
