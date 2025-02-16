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
    # MAIN_WINDOW_TITLE = "Meshsee"
    # MAIN_WINDOW_SIZE = (800, 600)
    # BUTTON_STRIP_HEIGHT = 50
    # GL_VERSION = (3, 3)
    # _instance = None

    def __init__(self, gl_ui: GlUi):
        # if self.__class__._instance is not None:
        #     raise RuntimeError("Only one instance of App is allowed")
        # self.__class__._instance = self
        # prepare_surface_format(self.GL_VERSION)
        # self._app = QApplication(sys.argv)
        # self._show_splash()
        # renderer_factory = RendererFactory(Camera())
        self._gl_ui = gl_ui
        # self._main_window = MainWindow(
        #     self.MAIN_WINDOW_TITLE, self.MAIN_WINDOW_SIZE, renderer_factory
        # )

    def run(self):
        self._gl_ui.run()
        # self._main_window.show()
        # self._app.exec()

    # @classmethod
    # def instance(cls):
    #     return cls._instance
