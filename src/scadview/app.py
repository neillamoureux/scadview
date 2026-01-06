import logging
from multiprocessing.connection import Connection

from scadview.controller import Controller
from scadview.render.camera import CameraPerspective
from scadview.render.gl_widget_adapter import GlWidgetAdapter
from scadview.render.renderer import RendererFactory
from scadview.ui.splash import stop_splash_process
from scadview.ui.wx.gl_ui import GlUi

logger = logging.getLogger(__name__)


def main(splash_conn: Connection):
    logger.info("SCADview app starting up")
    renderer_factory = RendererFactory(CameraPerspective())
    gl_widget_adapter = GlWidgetAdapter(renderer_factory)
    controller = Controller()
    logger.warning("*** SCADview has initialized ***")
    stop_splash_process(splash_conn)
    GlUi(controller, gl_widget_adapter).run()
    logger.info("SCADview app stopping")
