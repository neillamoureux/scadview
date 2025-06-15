import logging

from meshsee.controller import Controller
from meshsee.logconfig import setup_logging
from meshsee.render.camera import CameraPerspective
from meshsee.render.gl_widget_adapter import GlWidgetAdapter
from meshsee.render.renderer import RendererFactory
from meshsee.ui.gl_ui import GlUi

setup_logging()
logger = logging.getLogger(__name__)


def main():
    logger.info("Meshee app starting up")
    renderer_factory = RendererFactory(CameraPerspective())
    gl_widget_adapter = GlWidgetAdapter(renderer_factory)
    controller = Controller()
    GlUi(controller, gl_widget_adapter).run()
    logger.info("Meshee app stopping")
