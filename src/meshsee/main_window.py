from time import time

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

from meshsee.controller import Controller, export_formats
from meshsee.moderngl_widget import (
    ModernglWidget,
)


class MainWindow(QMainWindow):
    BUTTON_STRIP_HEIGHT = 50
    UPDATE_MESH_INTERVAL_MS = 100

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
        self._export_btn = None
        self._main_layout = self._create_main_layout()
        self._mesh_loading_worker = None
        self._next_mesh_loading_worker = None
        self._first_mesh = False
        self._last_mesh_update = time()
        self._latest_unloaded_mesh = None

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

        load_file_btn = QPushButton("Load .py")
        load_file_btn.clicked.connect(self.load_file)
        file_button_layout.addWidget(load_file_btn)

        reload_file_btn = QPushButton("Reload .py")
        reload_file_btn.clicked.connect(self.reload)
        file_button_layout.addWidget(reload_file_btn)

        self._export_btn = QPushButton("Export")
        self._export_btn.setDisabled(True)
        self._export_btn.clicked.connect(self.export)
        file_button_layout.addWidget(self._export_btn)

        return file_button_strip

    def _create_camera_buttons(self):
        camera_button_strip = QWidget()
        camera_button_layout = QHBoxLayout()
        camera_button_strip.setLayout(camera_button_layout)
        camera_button_strip.setFixedHeight(
            self.BUTTON_STRIP_HEIGHT
        )  # Set fixed height for the button strip

        # Add buttons to the button layout
        frame_btn = QPushButton("Frame")
        frame_btn.clicked.connect(self._gl_widget.frame)
        camera_button_layout.addWidget(frame_btn)

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

        grid_btn = QPushButton("Grid")
        grid_btn.setCheckable(True)
        grid_btn.setChecked(self._gl_widget.show_grid)
        grid_btn.clicked.connect(self._gl_widget.toggle_grid)
        camera_button_layout.addWidget(grid_btn)

        return camera_button_strip

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "Python Files (*.py)"
        )
        self._load_mesh(file_path)

    def reload(self):
        self._load_mesh(None)

    def _load_mesh(self, file_path: str | None):
        worker = LoadMeshRunnable(self._controller, file_path, self._gl_widget)
        if self._mesh_loading_worker is None:
            self._start_worker(worker)
        else:
            self._next_mesh_loading_worker = worker
            self._mesh_loading_worker.stop()

    def _start_worker(self, worker):
        self._mesh_loading_worker = worker
        self._mesh_loading_worker.signals.mesh_update.connect(self._update_mesh)
        self._mesh_loading_worker.signals.load_start.connect(self._start_load)
        self._mesh_loading_worker.signals.stopped.connect(self._start_next_worker)
        QThreadPool.globalInstance().start(self._mesh_loading_worker)

    def _start_next_worker(self):
        self._export_btn.setEnabled(True)
        self._mesh_loading_worker = None
        if self._next_mesh_loading_worker is not None:
            self._start_worker(self._next_mesh_loading_worker)
            self._next_mesh_loading_worker = None
        else:
            if self._latest_unloaded_mesh is not None:
                self._update_mesh(self._latest_unloaded_mesh, force=True)

    def _start_load(self):
        self._first_mesh = True

    def _update_mesh(self, mesh: Trimesh, force=False):
        self._latest_unloaded_mesh = None
        if self._first_mesh:
            self._gl_widget.load_mesh(mesh)
            self._last_mesh_update = time()
            self._gl_widget.frame()
            self._first_mesh = False
            return
        if force:
            self._gl_widget.load_mesh(mesh)
            self._last_mesh_update = time()
            return
        if time() - self._last_mesh_update > self.UPDATE_MESH_INTERVAL_MS / 1000:
            self._latest_unloaded_mesh = None
            self._gl_widget.load_mesh(mesh)
            self._last_mesh_update = time()
        else:
            self._latest_unloaded_mesh = mesh

    def export(self):
        filt = ";;".join([f"{fmt.upper()} (*.{fmt})" for fmt in export_formats()])
        file_path, _ = QFileDialog.getSaveFileName(self, "Export File", filter=filt)
        if file_path:
            self._controller.export(file_path)


class MeshUpdateSignals(QObject):
    mesh_update = Signal(Trimesh)
    load_start = Signal()
    stopped = Signal()


class LoadMeshRunnable(QRunnable):
    def __init__(
        self, controller: Controller, file_path: str, gl_widget: ModernglWidget
    ):
        super().__init__()
        self._controller = controller
        self._file_path = file_path
        self._gl_widget = gl_widget
        self.signals = MeshUpdateSignals()
        self._stop_requested = False
        self._stopped = False

    def run(self):
        if self._file_path is not None:
            self.signals.load_start.emit()
        if self._stop_requested:
            self.signal_stop()
            return
        for mesh in self._controller.load_mesh(self._file_path):
            if self._stop_requested:
                self.signal_stop()
                return
            self.signals.mesh_update.emit(mesh)
        self.signal_stop()

    def stop(self):
        self._stop_requested = True
        if self._stopped:  # Signal stop immediately if already stopped
            self.signal_stop()

    def signal_stop(self):
        self._stopped = True
        self.signals.stopped.emit()
