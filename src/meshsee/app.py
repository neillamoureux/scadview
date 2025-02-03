import sys

from PySide6.QtWidgets import QApplication, QMainWindow


def main():
    app = App()
    app.run()


class App:
    MAIN_WINDOW_TITLE = "Meshsee"
    MAIN_WINDOW_SIZE = (800, 600)

    def __init__(self):
        self._app = QApplication(sys.argv)
        self._main_window = MainWindow()
        self._main_window.setWindowTitle(self.MAIN_WINDOW_TITLE)
        self._main_window.resize(*self.MAIN_WINDOW_SIZE)

    def run(self):
        self._main_window.show()
        self._app.exec()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
