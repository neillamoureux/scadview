import logging
import os
import queue

from trimesh import Trimesh
from trimesh.exchange import export

from scadview.load_status import LoadStatus
from scadview.logging_main import log_queue
from scadview.mesh_loader_process import (
    Command,
    LoadMeshCommand,
    LoadResult,
    MeshLoaderProcess,
    MpCommandQueue,
    MpLoadQueue,
    ShutDownCommand,
)
from scadview.observable import Observable

logger = logging.getLogger(__name__)

UNSUPPORTED_EXPORT_FORMATS = ["dict", "dict64", "stl_ascii", "xyz"]


def export_formats() -> list[str]:
    return [
        fmt
        for fmt in export._mesh_exporters.keys()  # pyright: ignore[reportPrivateUsage] - only way to access this
        if fmt not in UNSUPPORTED_EXPORT_FORMATS
    ]


class Controller:
    def __init__(self):
        self.on_module_path_set = Observable()
        self.module_path = ""
        self._last_export_path = ""
        self._load_queue = MpLoadQueue(maxsize=1, type_=LoadResult)
        self._command_queue = MpCommandQueue(maxsize=0, type_=Command)
        self._loader_process = MeshLoaderProcess(
            self._command_queue,
            self._load_queue,
            log_queue=log_queue,
            log_level=logger.getEffectiveLevel(),
        )
        self._loader_process.start()
        self.on_load_status_change = Observable()
        self._load_status = LoadStatus.NONE

    @property
    def current_mesh(self) -> list[Trimesh] | Trimesh | None:
        return self._current_mesh

    @current_mesh.setter
    def current_mesh(self, value: list[Trimesh] | Trimesh | None):
        self._current_mesh = value

    @property
    def module_path(self) -> str:
        return self._module_path

    @module_path.setter
    def module_path(self, value: str):
        self._module_path = value
        self.on_module_path_set.notify(value)

    @property
    def load_status(self) -> LoadStatus:
        return self._load_status

    @load_status.setter
    def load_status(self, value: LoadStatus):
        if self._load_status == value:
            return
        self._load_status = value
        self.on_load_status_change.notify(value)

    def load_mesh(self, module_path: str):
        self.current_mesh = None
        self.load_status = LoadStatus.START
        if module_path != self.module_path:
            self._last_export_path = (
                ""  # Reset last export path if loading a new module
            )
            self.module_path = module_path
        logger.info(f"Starting load of {module_path}")
        self._command_queue.put(LoadMeshCommand(module_path))

    def reload_mesh(self):
        if self.module_path == "":
            raise ValueError("No previous load to reload")
        self.load_mesh(self.module_path)

    def check_load_queue(self) -> LoadResult:
        try:
            load_result = self._load_queue.get_nowait()
            if load_result.mesh is not None:
                logger.debug("check_load_queue got mesh")
                self.current_mesh = load_result.mesh
            else:
                logger.debug("check_load_queue got mesh == None")
            self.load_status = load_result.status
        except queue.Empty:
            logger.debug("check_load_queue empty")
            load_result = LoadResult(0, 0, None, None, False)
        return load_result

    def export(self, file_path: str):
        if not self.current_mesh:
            logger.info("No mesh to export")
            return
        if isinstance(self.current_mesh, list):
            export_mesh = self.current_mesh[-1]
        else:
            export_mesh = self.current_mesh
        self._last_export_path = file_path
        export_mesh.export(file_path)

    def default_export_path(self) -> str:
        if self._last_export_path != "":
            return self._last_export_path
        if self.module_path != "":
            return os.path.join(
                os.path.dirname(self.module_path),
                os.path.splitext(os.path.basename(self.module_path))[0],
            )
        raise ValueError("No module loaded")

    def __del__(self):
        self._command_queue.put(ShutDownCommand())
        self._loader_process.terminate()
