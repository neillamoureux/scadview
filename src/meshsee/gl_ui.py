import os
import sys

from PySide6.QtCore import Qt
from PySide6 import QtGui
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QSplashScreen,
)

from meshsee.main_window import MainWindow
from meshsee.renderer import RendererFactory


def prepare_surface_format(gl_version: tuple[int, int]):
    # In macos, the surface format must be set before creating the application
    fmt = QtGui.QSurfaceFormat()
    fmt.setVersion(*gl_version)
    fmt.setProfile(QtGui.QSurfaceFormat.CoreProfile)
    QtGui.QSurfaceFormat.setDefaultFormat(fmt)


class GlUi:
    MAIN_WINDOW_TITLE = "Meshsee"
    MAIN_WINDOW_SIZE = (800, 600)
    BUTTON_STRIP_HEIGHT = 50
    GL_VERSION = (3, 3)
    _instance = None

    def __init__(self, renderer_factory: RendererFactory):
        if self.__class__._instance is not None:
            raise RuntimeError("Only one instance of App is allowed")
        self.__class__._instance = self
        prepare_surface_format(self.GL_VERSION)
        self._app = QApplication(sys.argv)
        self._show_splash()
        self._main_window = MainWindow(
            self.MAIN_WINDOW_TITLE, self.MAIN_WINDOW_SIZE, renderer_factory
        )

    def _show_splash(self):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        splash_image_path = os.path.join(current_dir, "splash.png")
        splash_pix = QPixmap(splash_image_path)
        splash = QSplashScreen(splash_pix)
        splash.show()
        splash.raise_()
        self._app.processEvents()
        splash.showMessage("Meshee is initializing...", Qt.AlignCenter)
        return splash

    def run(self):
        self._main_window.show()
        self._app.exec()

    @classmethod
    def instance(cls):
        return cls._instance
