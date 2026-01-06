import logging
import sys

import pytest

from scadview.logging_main import configure_logging, parse_logging_level


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


@pytest.fixture()
def parse_with_args(monkeypatch):
    def _parse(args):
        monkeypatch.setattr(sys, "argv", ["prog"] + args)
        parse_logging_level()

    return _parse


def _configure_root_with_handler(root, level=None):
    handler = logging.StreamHandler()
    root.addHandler(handler)
    if level is not None:
        root.setLevel(level)
        handler.setLevel(level)
    return handler


def test_configure_logging_sets_handler_and_listener(root_logger):
    listener = None
    try:
        listener = configure_logging(logging.INFO)
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)
        assert root_logger.handlers[0].level == logging.INFO
        assert listener._thread is not None
        assert listener._thread.is_alive()
    finally:
        if listener is not None:
            listener.stop()


def test_parse_logging_level_default_warning(root_logger, parse_with_args):
    handler = _configure_root_with_handler(root_logger, logging.DEBUG)
    parse_with_args([])
    assert root_logger.level == logging.WARNING
    assert handler.level == logging.WARNING


def test_parse_logging_level_verbose_info(root_logger, parse_with_args):
    handler = _configure_root_with_handler(root_logger)
    parse_with_args(["-v"])
    assert root_logger.level == logging.INFO
    assert handler.level == logging.INFO


def test_parse_logging_level_verbose_debug(root_logger, parse_with_args):
    handler = _configure_root_with_handler(root_logger)
    parse_with_args(["-vv"])
    assert root_logger.level == logging.DEBUG
    assert handler.level == logging.DEBUG


def test_parse_logging_level_explicit_overrides_verbose(root_logger, parse_with_args):
    handler = _configure_root_with_handler(root_logger)
    parse_with_args(["-v", "--log-level", "ERROR"])
    assert root_logger.level == logging.ERROR
    assert handler.level == logging.ERROR
