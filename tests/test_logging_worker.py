import logging
import logging.handlers
import multiprocessing as mp

import pytest

from meshsee.logging_worker import configure_worker_logging


@pytest.fixture()
def root_logger():
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    root.handlers.clear()
    yield root
    root.handlers.clear()
    for handler in original_handlers:
        root.addHandler(handler)
    root.setLevel(original_level)


def test_configure_worker_logging_sets_queue_handler(root_logger):
    log_queue = mp.Queue()
    configure_worker_logging(log_queue, logging.INFO)

    assert root_logger.level == logging.INFO
    assert len(root_logger.handlers) == 1
    handler = root_logger.handlers[0]
    assert isinstance(handler, logging.handlers.QueueHandler)
    assert handler.level == logging.INFO
    assert handler.queue is log_queue
