from PySide6.QtCore import Signal, QObject, Qt, QRunnable, QThreadPool
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trimesh import Trimesh

from meshsee.controller import Controller
from meshsee.moderngl_widget import (
    ModernglWidget,
)


class MainWindow(QMainWindow):
    BUTTON_STRIP_HEIGHT = 50

    def __init__(
        self,
        title: str,
        size: tuple[int, int],
        controller: Controller,
    ):
        super().__init__()
        self._controller = controller
        self.setWindowTitle(title)
        self.resize(*size)
        self._main_layout = self._create_main_layout()
        self._mesh_loading_worker = None
        self._first_mesh = False

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
        gl_widget = ModernglWidget(self._controller._gl_widget_adapter)
        gl_widget.setFocusPolicy(Qt.StrongFocus)
        return gl_widget

    def _create_file_buttons(self):
        file_button_strip = QWidget()
        file_button_layout = QHBoxLayout()
        file_button_strip.setLayout(file_button_layout)
        file_button_strip.setFixedHeight(self.BUTTON_STRIP_HEIGHT)

        load_file_btn = QPushButton("Load File")
        load_file_btn.clicked.connect(self.load_file)
        file_button_layout.addWidget(load_file_btn)

        reload_file_btn = QPushButton("Reload File")
        reload_file_btn.clicked.connect(self.reload)
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

        view_from_x_btn = QPushButton("View from X+")
        view_from_x_btn.clicked.connect(self._gl_widget.view_from_x)
        camera_button_layout.addWidget(view_from_x_btn)

        view_from_y_btn = QPushButton("View from Y+")
        view_from_y_btn.clicked.connect(self._gl_widget.view_from_y)
        camera_button_layout.addWidget(view_from_y_btn)

        view_from_z_btn = QPushButton("View from Z+")
        view_from_z_btn.clicked.connect(self._gl_widget.view_from_z)
        camera_button_layout.addWidget(view_from_z_btn)

        orbit_btn = QPushButton("Orbit")
        # orbit_btn.clicked.connect(self.orbit)
        camera_button_layout.addWidget(orbit_btn)

        return camera_button_strip

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Python Files (*.py)"
        )
        self._load_mesh(file_path)

    def reload(self):
        self._load_mesh(None)

    def _load_mesh(self, file_path: str | None):
        if self._mesh_loading_worker is not None:
            self._mesh_loading_worker.stop()
        self._mesh_loading_worker = LoadMeshRunnable(self._controller, file_path, self._gl_widget)
        self._mesh_loading_worker.signals.mesh_update.connect(self._update_mesh)
        QThreadPool.globalInstance().start(self._mesh_loading_worker)
        
    def _update_mesh(self, mesh: Trimesh):
        if mesh is None:
            self._first_mesh = True
            return
        self._gl_widget.load_mesh(mesh)
        if self._first_mesh:
            self._gl_widget.frame()
            self._first_mesh = False


class MeshUpdateSignals(QObject):
    mesh_update = Signal(Trimesh)

class LoadMeshRunnable(QRunnable):
    def __init__(self, controller: Controller, file_path: str, gl_widget: ModernglWidget):
        super().__init__()
        self._controller = controller
        self._file_path = file_path
        self._gl_widget = gl_widget
        self.signals = MeshUpdateSignals()
        self._stop_requested = False

    def run(self):
        if self._file_path is not None:
            self.signals.mesh_update.emit(None) # signals a new laod
        if self._stop_requested:
            return
        for mesh in self._controller.load_mesh(self._file_path):
            if self._stop_requested:
                return
            self.signals.mesh_update.emit(mesh)

    def stop(self):
        self._stop_requested = True
