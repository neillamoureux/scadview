import logging
import os
import queue

from trimesh import Trimesh
from trimesh.exchange import export

from scadview.features import FeatureState
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
        for fmt in export._mesh_exporters.keys()
        if fmt not in UNSUPPORTED_EXPORT_FORMATS
    ]


class Controller:
    def __init__(self):
        self.on_module_path_set = Observable()
        self.on_features_change = Observable()
        self.module_path = ""
        self._last_export_path = ""
        self._closed = False
        self._current_mesh: list[Trimesh] | Trimesh | None = None
        self._feature_states: list[FeatureState] = []
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
    def feature_states(self) -> list[FeatureState]:
        return self._feature_states

    @feature_states.setter
    def feature_states(self, value: list[FeatureState]):
        if self._feature_states == value:
            return
        self._feature_states = value
        self.on_features_change.notify(value)

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
            self.feature_states = []
        logger.info(f"Starting load of {module_path}")
        self._command_queue.put(LoadMeshCommand(module_path, self._feature_state_map()))

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
            self.feature_states = load_result.features or []
            self.load_status = load_result.status
        except queue.Empty:
            logger.debug("check_load_queue empty")
            load_result = LoadResult(0, 0, None, None, False)
        return load_result

    def set_feature_enabled(self, name: str, enabled: bool):
        if self.module_path == "":
            raise ValueError("No module loaded")
        feature_states = self._feature_state_map()
        if feature_states.get(name, True) == enabled:
            return
        feature_states[name] = enabled
        self.feature_states = self._feature_states_with_override(name, enabled)
        self._queue_feature_reload(feature_states)

    def export(self, file_path: str):
        # Cache the property so type narrowing is stable for the selected mesh.
        current_mesh = self.current_mesh
        if not current_mesh:
            logger.info("No mesh to export")
            return
        if isinstance(current_mesh, list):
            export_mesh = current_mesh[-1]
        else:
            export_mesh = current_mesh
        self._last_export_path = file_path
        # Trimesh exposes export at runtime, but its stubs do not model it.
        export_mesh.export(file_path)  # ty: ignore[unresolved-attribute]

    def default_export_path(self) -> str:
        if self._last_export_path != "":
            return self._last_export_path
        if self.module_path != "":
            return os.path.join(
                os.path.dirname(self.module_path),
                os.path.splitext(os.path.basename(self.module_path))[0],
            )
        raise ValueError("No module loaded")

    def close(self, timeout: float = 2.0) -> None:
        if self._closed:
            return
        self._closed = True

        try:
            self._command_queue.put(ShutDownCommand())
        except (BrokenPipeError, EOFError, OSError, ValueError):
            pass

        self._loader_process.join(timeout=timeout)
        if self._loader_process.is_alive():
            self._loader_process.terminate()
            self._loader_process.join(timeout=timeout)

        self._command_queue.close()
        self._load_queue.close()

    def _feature_state_map(self) -> dict[str, bool]:
        return {feature.name: feature.enabled for feature in self.feature_states}

    def _feature_states_with_override(
        self,
        name: str,
        enabled: bool,
    ) -> list[FeatureState]:
        updated_feature_states: list[FeatureState] = []
        found = False
        for feature in self.feature_states:
            if feature.name == name:
                updated_feature_states.append(FeatureState(name, enabled))
                found = True
            else:
                updated_feature_states.append(feature)
        if not found:
            updated_feature_states.append(FeatureState(name, enabled))
        return updated_feature_states

    def _queue_feature_reload(self, feature_states: dict[str, bool]):
        self.current_mesh = None
        self.load_status = LoadStatus.START
        self._command_queue.put(LoadMeshCommand(self.module_path, feature_states))

    def __del__(self):
        try:
            self.close(timeout=0.2)
        except Exception:
            pass
