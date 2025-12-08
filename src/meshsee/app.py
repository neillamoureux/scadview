import argparse
import logging

from meshsee.controller import Controller
from meshsee.logconfig import setup_logging
from meshsee.render.camera import CameraPerspective
from meshsee.render.gl_widget_adapter import GlWidgetAdapter
from meshsee.render.renderer import RendererFactory
from meshsee.ui.wx.gl_ui import GlUi
from meshsee.ui.splash import stop_splash_process
from multiprocessing.connection import Connection


setup_logging()
logger = logging.getLogger(__name__)


def main(splash_conn: Connection):
    set_logging_level()
    logger.info("Meshee app starting up")
    renderer_factory = RendererFactory(CameraPerspective())
    gl_widget_adapter = GlWidgetAdapter(renderer_factory)
    controller = Controller()
    stop_splash_process(splash_conn)
    GlUi(controller, gl_widget_adapter).run()
    logger.info("Meshee app stopping")


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
