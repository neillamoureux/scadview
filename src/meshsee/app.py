import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


def main():
    app = App()
    app.run()


class App:
    MAIN_WINDOW_TITLE = "Meshsee"
    MAIN_WINDOW_SIZE = (800, 600)
    _instance = None

    def __init__(self):
        if self.__class__._instance is not None:
            raise RuntimeError("Only one instance of App is allowed")
        self.__class__._instance = self
        self._app = QApplication(sys.argv)
        self._main_window = MainWindow(self.MAIN_WINDOW_TITLE, self.MAIN_WINDOW_SIZE)

    def run(self):
        self._main_window.show()
        self._app.exec()

    @classmethod
    def instance(cls):
        return cls._instance


class MainWindow(QMainWindow):
    def __init__(self, title: str, size: tuple[int, int]):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(*size)
        self._main_layout = self._create_main_layout()

    def _create_main_layout(self) -> QVBoxLayout:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        self._gl_widget = self._create_graphics_widget()
        main_layout.addWidget(self._gl_widget)
        return main_layout

    def _create_graphics_widget(self):
        gl_widget = QWidget()
        gl_widget.setFocusPolicy(Qt.StrongFocus)
        return gl_widget
