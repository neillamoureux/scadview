from meshsee.camera import Camera
from meshsee.gl_ui import GlUi
from meshsee.gl_widget_adapter import GlWidgetAdapter
from meshsee.renderer import RendererFactory


def main():
    renderer_factory = RendererFactory(Camera())
    gl_widget_adapter = GlWidgetAdapter(renderer_factory)
    app = App(GlUi(gl_widget_adapter))
    app.run()


class App:
    def __init__(self, gl_ui: GlUi):
        self._gl_ui = gl_ui

    def run(self):
        self._gl_ui.run()
