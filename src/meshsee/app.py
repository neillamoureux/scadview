from meshsee.camera import Camera
from meshsee.controller import Controller
from meshsee.gl_ui import GlUi
from meshsee.gl_widget_adapter import GlWidgetAdapter
from meshsee.renderer import RendererFactory


def main():
    renderer_factory = RendererFactory(Camera())
    gl_widget_adapter = GlWidgetAdapter(renderer_factory)
    controller = Controller(gl_widget_adapter)
    app = App(GlUi(controller))
    app.run()


class App:
    def __init__(self, gl_ui: GlUi):
        self._gl_ui = gl_ui

    def run(self):
        self._gl_ui.run()
