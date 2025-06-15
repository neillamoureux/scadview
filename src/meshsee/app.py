from meshsee.render.camera import CameraPerspective
from meshsee.controller import Controller
from meshsee.ui.gl_ui import GlUi
from meshsee.render.gl_widget_adapter import GlWidgetAdapter
from meshsee.render.renderer import RendererFactory


def main():
    renderer_factory = RendererFactory(CameraPerspective())
    gl_widget_adapter = GlWidgetAdapter(renderer_factory)
    controller = Controller()
    GlUi(controller, gl_widget_adapter).run()
