import sys
from importlib.resources import as_file, files

from PySide6 import QtGui
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

import meshsee
import meshsee.resources
from meshsee.controller import Controller
from meshsee.render.gl_widget_adapter import GlWidgetAdapter
from meshsee.ui.main_window import MainWindow
from meshsee.ui.moderngl_widget import ModernglWidget


def prepare_surface_format(gl_version: tuple[int, int]):
    # In macos, the surface format must be set before creating the application
    fmt = QtGui.QSurfaceFormat()
    fmt.setVersion(*gl_version)
    fmt.setProfile(QtGui.QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    QtGui.QSurfaceFormat.setDefaultFormat(fmt)


def create_graphics_widget(gl_widget_adapter: GlWidgetAdapter) -> ModernglWidget:
    gl_widget = ModernglWidget(gl_widget_adapter)
    gl_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    return gl_widget


class GlUi:
    MAIN_WINDOW_TITLE = "Meshsee"
    MAIN_WINDOW_SIZE = (800, 600)
    BUTTON_STRIP_HEIGHT = 50
    GL_VERSION = (3, 3)
    _instance = None

    def __init__(self, controller: Controller, gl_widget_adapter: GlWidgetAdapter):
        if self.__class__._instance is not None:
            raise RuntimeError("Only one instance of App is allowed")
        self.__class__._instance = self
        prepare_surface_format(self.GL_VERSION)
        self._app = QApplication(sys.argv)
        self._app.setApplicationDisplayName(self.MAIN_WINDOW_TITLE)
        self._app.setApplicationName(self.MAIN_WINDOW_TITLE)
        self._show_splash()
        gl_widget = create_graphics_widget(gl_widget_adapter)
        self._main_window = MainWindow(
            self.MAIN_WINDOW_TITLE, self.MAIN_WINDOW_SIZE, controller, gl_widget
        )

    def _show_splash(self):
        splash_image = files(meshsee.resources).joinpath("splash.png")
        with as_file(splash_image) as splash_f:
            splash_pix = QPixmap(splash_f)
            splash = QSplashScreen(splash_pix)
            splash.show()
            splash.raise_()
            self._app.processEvents()
            splash.showMessage(
                "Meshsee is initializing...", Qt.AlignmentFlag.AlignCenter
            )
            return splash

    def run(self):
        self._main_window.show()
        self._app.exec()

    @classmethod
    def instance(cls):
        return cls._instance
