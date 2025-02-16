import os
import sys

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QSplashScreen,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from meshsee.camera import Camera
from meshsee.moderngl_widget import (
    ModernglWidget,
    prepare_surface_format,
    RendererFactory,
)


def main():
    app = App()
    app.run()


class App:
    MAIN_WINDOW_TITLE = "Meshsee"
    MAIN_WINDOW_SIZE = (800, 600)
    BUTTON_STRIP_HEIGHT = 50
    GL_VERSION = (3, 3)
    _instance = None

    def __init__(self):
        if self.__class__._instance is not None:
            raise RuntimeError("Only one instance of App is allowed")
        self.__class__._instance = self
        prepare_surface_format(self.GL_VERSION)
        self._app = QApplication(sys.argv)
        self._show_splash()
        self._camera = Camera()
        renderer_factory = RendererFactory(self._camera)
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


class MainWindow(QMainWindow):
    BUTTON_STRIP_HEIGHT = 50

    def __init__(self, title: str, size: tuple[int, int], camera: Camera):
        super().__init__()
        self._camera = camera
        self.setWindowTitle(title)
        self.resize(*size)
        self._main_layout = self._create_main_layout()

    def _create_main_layout(self) -> QVBoxLayout:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        self._gl_widget = self._create_graphics_widget()
        main_layout.addWidget(self._gl_widget)
        file_buttons = self._create_file_buttons()
        main_layout.addWidget(file_buttons)
        camera_buttons = self._create_camera_buttons()
        main_layout.addWidget(camera_buttons)
        # Stretching to make main_widget occupy remaining space
        # main_layout.setStretch(0, 1)  # First widget gets a stretch factor of 1
        # main_layout.setStretch(1, 0)  # Button strip does not stretch

        return main_layout

    def _create_graphics_widget(self):
        gl_widget = ModernglWidget(self._camera)
        gl_widget.setFocusPolicy(Qt.StrongFocus)
        return gl_widget

    def _create_file_buttons(self):
        file_button_strip = QWidget()
        file_button_layout = QHBoxLayout()
        file_button_strip.setLayout(file_button_layout)
        file_button_strip.setFixedHeight(self.BUTTON_STRIP_HEIGHT)

        load_file_btn = QPushButton("Load File")
        # load_file_btn.clicked.connect(self.load_file)
        file_button_layout.addWidget(load_file_btn)

        reload_file_btn = QPushButton("Reload File")
        # reload_file_btn.clicked.connect(self.reload)
        file_button_layout.addWidget(reload_file_btn)

        export_stl_btn = QPushButton("Export STL")
        # export_stl_btn.clicked.connect(self.export_stl)
        file_button_layout.addWidget(export_stl_btn)

        return file_button_strip

    def _create_camera_buttons(self):
        camera_button_strip = QWidget()
        camera_button_layout = QHBoxLayout()
        camera_button_strip.setLayout(camera_button_layout)
        camera_button_strip.setFixedHeight(
            self.BUTTON_STRIP_HEIGHT
        )  # Set fixed height for the button strip

        # Add buttons to the button layout
        view_from_xyz_btn = QPushButton("View from XYZ")
        view_from_xyz_btn.clicked.connect(self._gl_widget.view_from_xyz)
        camera_button_layout.addWidget(view_from_xyz_btn)

        view_from_x_positive_btn = QPushButton("View from X+")
        # view_from_x_positive_btn.clicked.connect(self.view_from_x_positive)
        camera_button_layout.addWidget(view_from_x_positive_btn)

        view_from_y_positive_btn = QPushButton("View from Y+")
        # view_from_y_positive_btn.clicked.connect(self.view_from_y_positive)
        camera_button_layout.addWidget(view_from_y_positive_btn)

        view_from_z_positive_btn = QPushButton("View from Z+")
        # view_from_z_positive_btn.clicked.connect(self.view_from_z_positive)
        camera_button_layout.addWidget(view_from_z_positive_btn)

        orbit_btn = QPushButton("Orbit")
        # orbit_btn.clicked.connect(self.orbit)
        camera_button_layout.addWidget(orbit_btn)

        return camera_button_strip
