import logging
import queue
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from meshsee.controller import Controller
from meshsee.mesh_loader import MeshLoader
from meshsee.ui.moderngl_widget import ModernglWidget

logger = logging.getLogger(__name__)


class MeshUpdateSignals(QObject):
    load_start = Signal()
    mesh_update = Signal()
    load_successful = Signal()
    stopped = Signal()
    error = Signal()


class LoadMeshRunnable(QRunnable):
    def __init__(
        self,
        controller: Controller,
        parent_signals_owner: QObject,
        file_path: str | None,
    ):
        super().__init__()
        self.setAutoDelete(False)  # Don't auto-delete in pool thread
        signals = MeshUpdateSignals(parent_signals_owner)
        self._mesh_loader = MeshLoader(
            file_path=file_path,
            controller=controller,
            load_start_callback=signals.load_start.emit,
            mesh_update_callback=signals.mesh_update.emit,
            load_successful_callback=signals.load_successful.emit,
            stopped_callback=signals.stopped.emit,
            error_callback=signals.error.emit,
        )
        self.signals = signals
        self.mesh_queue = self._mesh_loader.mesh_queue

    def run(self):
        self._mesh_loader.run()

    def stop(self):
        self._mesh_loader.stop()


class MeshHandler:
    """
    Handle logic of starting thread to load a mesh,
    as well as enabling / disabling reload and export widgets.
    """

    def __init__(
        self,
        controller: Controller,
        gl_widget: ModernglWidget,
        reload_enable_callback: Callable[[bool], None],
        export_enable_callback: Callable[[bool], None],
    ):
        self._controller = controller
        self._gl_widget = gl_widget
        self._enable_reload = reload_enable_callback
        self._enable_export = export_enable_callback
        self._mesh_loading_worker = None
        self._next_mesh_loading_worker = None
        self._first_mesh = False
        self._mesh_name: str = "Unknown from MeshHandler"

    def load_mesh(self, file_path: str | None):
        self._enable_reload(True)
        self._enable_export(False)
        self._mesh_name = file_path if file_path is not None else "Unknown"
        worker = LoadMeshRunnable(self._controller, self._gl_widget, file_path)
        if self._mesh_loading_worker is None:
            logger.debug(
                f"No current worker. Starting mesh loading worker for {self._mesh_name}"
            )
            self._start_worker(worker)
        else:
            logger.debug(
                f"Current worker exists; must stop before loading {self._mesh_name}"
            )
            self._next_mesh_loading_worker = worker
            self._mesh_loading_worker.stop()

    def _start_worker(self, worker: LoadMeshRunnable):
        self._mesh_loading_worker = worker
        self._mesh_loading_worker.signals.mesh_update.connect(self._update_mesh)
        self._mesh_loading_worker.signals.load_start.connect(self._start_load)
        self._mesh_loading_worker.signals.stopped.connect(self._start_next_worker)
        self._mesh_loading_worker.signals.load_successful.connect(self._load_successful)
        self._mesh_loading_worker.signals.error.connect(self._indicate_error)
        self._gl_widget.indicate_load_state("loading")
        logger.debug(f"Starting mesh loading worker for {self._mesh_name}")
        QThreadPool.globalInstance().start(self._mesh_loading_worker)

    def _start_next_worker(self):
        self._mesh_loading_worker = None
        if self._next_mesh_loading_worker is not None:
            self._start_worker(self._next_mesh_loading_worker)
            self._next_mesh_loading_worker = None

    def _start_load(self):
        self._first_mesh = True

    def _update_mesh(self):
        logger.debug("Getting latest mesh from queue for viewing")
        try:
            if self._mesh_loading_worker is None:
                raise ValueError("There is no worker to update the mesh")
            mesh = self._mesh_loading_worker.mesh_queue.get_nowait()
            self._gl_widget.load_mesh(mesh, self._mesh_name)
            if self._first_mesh:
                self._first_mesh = False
                self._gl_widget.frame()
        except queue.Empty:
            logger.debug("There is no mesh in the queue")

    def _load_successful(self):
        logger.debug("Mesh load successful")
        self._gl_widget.indicate_load_state("success")
        self._enable_export(True)

    def _indicate_error(self):
        self._gl_widget.indicate_load_state("error")

    def stop(self):
        if self._mesh_loading_worker is not None:
            self._mesh_loading_worker.stop()
            self._mesh_loading_worker = None
        self._next_mesh_loading_worker = None
