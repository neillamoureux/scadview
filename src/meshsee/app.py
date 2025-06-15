from meshsee.camera import CameraPerspective
from meshsee.controller import Controller
from meshsee.gl_ui import GlUi
from meshsee.gl_widget_adapter import GlWidgetAdapter
from meshsee.renderer import RendererFactory


def main():
    renderer_factory = RendererFactory(CameraPerspective())
    gl_widget_adapter = GlWidgetAdapter(renderer_factory)
    controller = Controller()
    GlUi(controller, gl_widget_adapter).run()
