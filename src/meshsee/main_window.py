from typing import Callable
from time import time
import queue

from PySide6.QtCore import Signal, QObject, Qt, QRunnable, QThreadPool
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from manifold3d import Manifold
from trimesh import Trimesh

from meshsee.controller import Controller, export_formats
from meshsee.moderngl_widget import (
    ModernglWidget,
)

from meshsee.utils import manifold_to_trimesh


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
        self._main_layout = self._create_main_layout()
        self._mesh_handler = MeshHandler(
            controller=controller,
            gl_widget=self._gl_widget,
            reload_file_btn=self._reload_file_btn,
            export_btn=self._export_btn,
        )

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
        return main_layout

    def _create_graphics_widget(self) -> ModernglWidget:
        gl_widget = ModernglWidget(self._controller._gl_widget_adapter)
        gl_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        return gl_widget

    def _create_file_buttons(self) -> QWidget:
        file_button_strip = QWidget()
        file_button_layout = QHBoxLayout()
        file_button_strip.setLayout(file_button_layout)
        file_button_strip.setFixedHeight(self.BUTTON_STRIP_HEIGHT)

        load_file_btn = QPushButton("Load .py")
        load_file_btn.clicked.connect(self.load_file)
        file_button_layout.addWidget(load_file_btn)

        self._reload_file_btn = QPushButton("Reload .py")
        self._reload_file_btn.setDisabled(True)
        self._reload_file_btn.clicked.connect(self.reload)
        file_button_layout.addWidget(self._reload_file_btn)

        self._export_btn = QPushButton("Export")
        self._export_btn.setDisabled(True)
        self._export_btn.clicked.connect(self.export)
        file_button_layout.addWidget(self._export_btn)

        return file_button_strip

    def _create_camera_buttons(self) -> QWidget:
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

        orthogonal_camera_btn = QPushButton("Ortho")
        orthogonal_camera_btn.clicked.connect(self._gl_widget.use_orthogonal_camera)
        camera_button_layout.addWidget(orthogonal_camera_btn)

        perspective_camera_btn = QPushButton("Persp")
        perspective_camera_btn.clicked.connect(self._gl_widget.use_perspective_camera)
        camera_button_layout.addWidget(perspective_camera_btn)

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
        self._mesh_handler.load_mesh(file_path)

    def export(self):
        filt = ";;".join([f"{fmt.upper()} (*.{fmt})" for fmt in export_formats()])
        file_path, _ = QFileDialog.getSaveFileName(self, "Export File", filter=filt)
        if file_path:
            self._controller.export(file_path)


class MeshUpdateSignals(QObject):
    load_start = Signal()
    mesh_update = Signal()
    load_successful = Signal()
    stopped = Signal()


class MeshHandler:
    """
    Handle logic of starting thread to load a mesh,
    as well as enabling / disabling reload and export widgets.
    """

    def __init__(
        self,
        controller: Controller,
        gl_widget: ModernglWidget,
        reload_file_btn: QWidget,
        export_btn: QWidget,
    ):
        self._controller = controller
        self._gl_widget = gl_widget
        self._reload_file_btn = reload_file_btn
        self._export_btn = export_btn
        self._mesh_loading_worker = None
        self._next_mesh_loading_worker = None
        self._first_mesh = False

    def load_mesh(self, file_path: str | None):
        self._reload_file_btn.setEnabled(True)
        self._export_btn.setDisabled(True)
        worker = LoadMeshRunnable(self._controller, file_path)
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
        self._mesh_loading_worker.signals.load_successful.connect(self._load_successful)
        QThreadPool.globalInstance().start(self._mesh_loading_worker)

    def _start_next_worker(self):
        self._mesh_loading_worker = None
        if self._next_mesh_loading_worker is not None:
            self._start_worker(self._next_mesh_loading_worker)
            self._next_mesh_loading_worker = None

    def _start_load(self):
        self._first_mesh = True

    def _update_mesh(self):
        print("Getting latest mesh from queue for viewing")
        try:
            if self._mesh_loading_worker is None:
                raise ValueError("There is no worker to update the mesh")
            mesh = self._mesh_loading_worker.mesh_queue.get_nowait()
            self._gl_widget.load_mesh(mesh)
            if self._first_mesh:
                self._first_mesh = False
                self._gl_widget.frame()
        except queue.Empty:
            pass

    def _load_successful(self):
        self._export_btn.setEnabled(True)


class LoadMeshRunnable(QRunnable):
    UPDATE_MESH_INTERVAL_MS = 100

    def __init__(
        self,
        controller: Controller,
        file_path: str | None,
    ):
        super().__init__()
        signals = MeshUpdateSignals()
        self._mesh_loader = MeshLoader(
            file_path=file_path,
            controller=controller,
            load_start_callback=signals.load_start.emit,
            mesh_update_callback=signals.mesh_update.emit,
            load_successful_callback=signals.load_successful.emit,
            stopped_callback=signals.stopped.emit,
        )
        self.signals = signals
        self.mesh_queue = self._mesh_loader.mesh_queue

    def run(self):
        self._mesh_loader.run()

    def stop(self):
        self._mesh_loader.stop()


class MeshLoader:
    """
    Pure python mesh loader to be run in a thread.
    """

    UPDATE_MESH_INTERVAL_MS = 100

    def __init__(
        self,
        controller: Controller,
        file_path: str | None,
        load_start_callback: Callable[[], None],
        mesh_update_callback: Callable[[], None],
        load_successful_callback: Callable[[], None],
        stopped_callback=Callable[[], None],
    ):
        self._controller = controller
        self._file_path = file_path
        self._load_start_callback = load_start_callback
        self._mesh_update_callback = mesh_update_callback
        self._load_successful_callback = load_successful_callback
        self._stopped_callback = stopped_callback
        self._stop_requested = False
        self._stopped = False
        self._first_mesh = True
        self._last_mesh_update = time()
        self._latest_unloaded_mesh = None
        self.mesh_queue = queue.Queue(maxsize=1)

    def run(self):
        print("Mesh loading about to start")
        if self._file_path is not None:
            self._load_start_callback()
        if self._stop_requested:
            self._signal_stop()
            return
        try:
            for mesh in self._controller.load_mesh(self._file_path):
                if self._stop_requested:
                    self._signal_stop()
                    return
                self._update_if_time(mesh)
            self._load_successful_callback()
        except Exception:
            if self._latest_unloaded_mesh is not None:
                self._update_mesh(self._latest_unloaded_mesh)
        finally:
            self._signal_stop()

    def stop(self):
        self._stop_requested = True
        print("Current mesh loading stop requested")

    def _signal_stop(self):
        if not self._stopped:
            self._stopped = True
            self._stopped_callback()
            print("Current mesh loading stopping")

    def _update_if_time(self, mesh: Trimesh):
        if self._first_mesh:
            self._update_mesh(mesh)
            self._first_mesh = False
            return
        if time() - self._last_mesh_update > self.UPDATE_MESH_INTERVAL_MS / 1000:
            self._update_mesh(mesh)
        else:
            self._latest_unloaded_mesh = mesh

    def _update_mesh(self, mesh):
        mesh2 = mesh
        if isinstance(mesh, Manifold):
            mesh2 = manifold_to_trimesh(mesh)
        self._last_mesh_update = time()
        self._latest_unloaded_mesh = None
        print("Placing latest mesh in queue for viewing")
        try:
            self.mesh_queue.put_nowait(mesh2)
        except queue.Full:
            _ = self.mesh_queue.get_nowait()
            self.mesh_queue.put_nowait(mesh2)
        if not self._stopped:
            self._mesh_update_callback()
