import logging
import os
import queue
from multiprocessing import Process

from trimesh import Trimesh
from trimesh.exchange import export

from meshsee.mesh_loader_process import (
    Command,
    LoadMeshCommand,
    MpCommandQueue,
    MpMeshQueue,
    MeshType,
    ShutDownCommand,
    run_loader,
)

logger = logging.getLogger(__name__)


def export_formats() -> list[str]:
    return [
        fmt
        for fmt in export._mesh_exporters.keys()  # pyright: ignore[reportPrivateUsage] - only way to access this
    ]


class Controller:

    def __init__(self):
        self._current_mesh: list[Trimesh] | Trimesh | None = None
        self._last_module_path = None
        self._last_export_path = None
        self._loader_queue: MpMeshQueue = MpMeshQueue(maxsize=1, type_=MeshType)
        self._command_queue = MpCommandQueue(maxsize=0, type_=Command)
        self._loader_process = Process(
            target=run_loader, args=(self._command_queue, self._loader_queue)
        )
        self._loader_process.start()

    @property
    def current_mesh(self) -> list[Trimesh] | Trimesh | None:
        return self._current_mesh

    @current_mesh.setter
    def current_mesh(self, mesh: Trimesh | None):
        self._current_mesh = mesh

    def load_mesh(self, module_path: str | None = None):
        self._current_mesh = None
        if module_path is None:
            module_path = self._last_module_path
        if module_path is None:
            raise ValueError("No module path selected for load")
        if module_path != self._last_module_path:
            self._last_export_path = (
                None  # Reset last export path if loading a new module
            )
            self._last_module_path = module_path
        logger.info(f"Starting load of {module_path}")
        self._command_queue.put(LoadMeshCommand(module_path))

    def check_load_queue(self) -> tuple[list[Trimesh] | Trimesh | None, bool]:
        try:
            mesh = self._loader_queue.get_nowait()
            self._current_mesh = mesh
        except queue.Empty:
            mesh = None
        return (mesh, not self._loader_process.is_alive())

    def export(self, file_path: str):
        if not self._current_mesh:
            logger.info("No mesh to export")
            return
        if isinstance(self._current_mesh, list):
            export_mesh = self._current_mesh[-1]

        else:
            export_mesh = self._current_mesh
        self._last_export_path = file_path
        export_mesh.export(file_path)

    def default_export_path(self) -> str:
        if self._last_export_path is not None:
            return self._last_export_path
        if self._last_module_path is not None:
            return os.path.join(
                os.path.dirname(self._last_module_path),
                os.path.splitext(os.path.basename(self._last_module_path))[0],
            )
        raise ValueError("No module loaded")

    def __del__(self):
        self._command_queue.put(ShutDownCommand())
        self._loader_process.terminate()
        # self._loader_process.join()
        # self._loader_process.close()
