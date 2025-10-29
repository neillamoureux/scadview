import logging
import os
import queue

from trimesh import Trimesh
from trimesh.exchange import export

from meshsee.mesh_loader_process import (
    Command,
    LoadMeshCommand,
    MeshLoaderProcess,
    LoadResult,
    MpCommandQueue,
    MpLoadQueue,
    ShutDownCommand,
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
        self._load_queue = MpLoadQueue(maxsize=1, type_=LoadResult)
        self._command_queue = MpCommandQueue(maxsize=0, type_=Command)
        self._loader_process = MeshLoaderProcess(self._command_queue, self._load_queue)
        self._loader_process.start()

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

    def check_load_queue(self) -> LoadResult:
        try:
            load_result = self._load_queue.get_nowait()
            if load_result.mesh is not None:
                self._current_mesh = load_result.mesh
        except queue.Empty:
            load_result = LoadResult(0, 0, None, None, False)
        return load_result

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
