import logging

from scadview.controller import Controller
from scadview.debug_info import DebugInfoService
from scadview.render.camera import CameraPerspective
from scadview.render.gl_widget_adapter import GlWidgetAdapter
from scadview.render.renderer import RendererFactory
from scadview.scene_assets import create_scene_assets
from scadview.ui.splash import SplashConnection, stop_splash_process
from scadview.ui.wx.gl_ui import GlUi

logger = logging.getLogger(__name__)


def main(splash_conn: SplashConnection, debug_info_service: DebugInfoService) -> None:
    logger.info("SCADview app starting up")
    controller = Controller()
    try:
        renderer_factory = RendererFactory(
            CameraPerspective(), create_scene_assets(), debug_info_service
        )
        gl_widget_adapter = GlWidgetAdapter(renderer_factory)
        logger.warning("*** SCADview has initialized ***")
        stop_splash_process(splash_conn)
        GlUi(controller, gl_widget_adapter, debug_info_service).run()
    finally:
        controller.close()
        logger.info("SCADview app stopping")
