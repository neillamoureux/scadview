import logging
from multiprocessing.connection import Connection

from meshsee.controller import Controller
from meshsee.render.camera import CameraPerspective
from meshsee.render.gl_widget_adapter import GlWidgetAdapter
from meshsee.render.renderer import RendererFactory
from meshsee.ui.splash import stop_splash_process
from meshsee.ui.wx.gl_ui import GlUi

logger = logging.getLogger(__name__)


def main(splash_conn: Connection):
    logger.info("Meshee app starting up")
    renderer_factory = RendererFactory(CameraPerspective())
    gl_widget_adapter = GlWidgetAdapter(renderer_factory)
    controller = Controller()
    logger.warning("*** Meshee has initialized ***")
    stop_splash_process(splash_conn)
    GlUi(controller, gl_widget_adapter).run()
    logger.info("Meshee app stopping")
