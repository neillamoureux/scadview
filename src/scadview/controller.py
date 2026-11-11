import logging
import os
import queue
from typing import cast

from trimesh.exchange import export

from scadview.features import FeatureState
from scadview.load_status import LoadStatus
from scadview.logging_main import log_queue
from scadview.mesh_loader_process import (
    Command,
    ExportCommand,
    ExportError,
    ExportResult,
    LoadError,
    LoadMeshCommand,
    LoadPhase,
    LoadResult,
    MeshLoaderProcess,
    MpCommandQueue,
    MpExportResultQueue,
    MpLoadQueue,
    ShutDownCommand,
)
from scadview.mesh_payload import MeshPayload
from scadview.module_loader import CreateMeshParameter, ScalarParameterValue
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
    def __init__(self) -> None:
        self.on_module_path_set = Observable()
        self.on_features_change = Observable()
        self.on_debug_features_change = Observable()
        self.on_parameters_change = Observable()
        self.module_path = ""
        self._last_export_path = ""
        self._closed = False
        self._current_mesh: list[MeshPayload] | MeshPayload | None = None
        self._exportable_payload: MeshPayload | None = None
        self._feature_states: list[FeatureState] = []
        self._debug_features = False
        self._parameters: list[CreateMeshParameter] = []
        self._parameter_values: dict[str, ScalarParameterValue] = {}
        self._current_generation = 0
        self._current_load_number = 0
        self._current_load_sequence_number = 0
        self._current_load_revision = 0
        self._effective_debug = False
        self._active_load_generation: int | None = None
        self._local_load_result: LoadResult | None = None
        self._next_export_request_id = 1
        self._pending_export_request_id: int | None = None
        self._pending_export_generation: int | None = None
        self._load_queue = MpLoadQueue(maxsize=1, type_=LoadResult)
        self._command_queue = MpCommandQueue(maxsize=0, type_=Command)
        self._export_result_queue = MpExportResultQueue(maxsize=0, type_=ExportResult)
        self._loader_process = MeshLoaderProcess(
            self._command_queue,
            self._load_queue,
            self._export_result_queue,
            log_queue=log_queue,
            log_level=logger.getEffectiveLevel(),
        )
        self._loader_process.start()
        self.on_load_status_change = Observable()
        self.on_export_result = Observable()
        self.on_export_availability_change = Observable()
        self._load_status = LoadStatus.NONE

    @property
    def current_mesh(self) -> list[MeshPayload] | MeshPayload | None:
        return self._current_mesh

    @current_mesh.setter
    def current_mesh(self, value: list[MeshPayload] | MeshPayload | None) -> None:
        self._current_mesh = value

    @property
    def feature_states(self) -> list[FeatureState]:
        return self._feature_states

    @feature_states.setter
    def feature_states(self, value: list[FeatureState]) -> None:
        if self._feature_states == value:
            return
        self._feature_states = value
        self.on_features_change.notify(value)

    @property
    def debug_features(self) -> bool:
        return self._debug_features

    @property
    def parameters(self) -> list[CreateMeshParameter]:
        return self._parameters

    @property
    def parameter_values(self) -> dict[str, ScalarParameterValue]:
        return self._parameter_values.copy()

    @property
    def current_generation(self) -> int:
        return self._current_generation

    @property
    def module_path(self) -> str:
        return self._module_path

    @module_path.setter
    def module_path(self, value: str) -> None:
        self._module_path = value
        self.on_module_path_set.notify(value)

    @property
    def load_status(self) -> LoadStatus:
        return self._load_status

    @load_status.setter
    def load_status(self, value: LoadStatus) -> None:
        if self._load_status == value:
            return
        self._load_status = value
        self.on_load_status_change.notify(value)

    def load_mesh(self, module_path: str) -> None:
        if not self._same_module(module_path):
            self._last_export_path = (
                ""  # Reset last export path if loading a new module
            )
            self.module_path = module_path
            self.feature_states = []
            self._parameters = []
            self._parameter_values = {}
            self.on_parameters_change.notify([])
        logger.info(f"Starting load of {module_path}")
        self._queue_load(self._feature_state_map())

    def reload_mesh(self) -> None:
        if self.module_path == "":
            raise ValueError("No previous load to reload")
        self.load_mesh(self.module_path)

    def check_load_queue(self) -> LoadResult | None:
        local_load_result = self._take_local_load_result()
        if local_load_result is not None:
            return local_load_result
        try:
            load_result = self._load_queue.get_nowait()
        except queue.Empty:
            return self._load_result_for_empty_queue()
        except (EOFError, OSError, ValueError) as error:
            return self._load_result_for_queue_error(error)
        return self._apply_load_result(load_result)

    def _take_local_load_result(self) -> LoadResult | None:
        load_result = self._local_load_result
        self._local_load_result = None
        return load_result

    def _load_result_for_empty_queue(self) -> LoadResult | None:
        if self._load_is_active() and not self._loader_process.is_alive():
            return self._complete_load_error(
                LoadError("LoaderProcessDied", "Mesh loader process exited")
            )
        logger.debug("check_load_queue empty")
        return None

    def _load_result_for_queue_error(self, error: Exception) -> LoadResult | None:
        if not self._load_is_active():
            return None
        return self._complete_load_error(LoadError(type(error).__name__, str(error)))

    def _complete_load_error(self, error: LoadError) -> LoadResult:
        result = self._apply_load_result(
            LoadResult(
                self._current_load_number,
                self._current_load_sequence_number,
                payload=self.current_mesh,
                error=error,
                features=self.feature_states.copy(),
                parameters=self.parameters.copy(),
                generation=self.current_generation,
                revision=self._current_load_revision + 1,
                phase=LoadPhase.ERROR,
                exportable=False,
                debug=self._effective_debug,
            )
        )
        assert result is not None
        return result

    def _apply_load_result(self, load_result: LoadResult) -> LoadResult | None:
        if load_result.generation != self.current_generation:
            logger.debug(
                "Discarding stale load result generation=%s current=%s",
                load_result.generation,
                self.current_generation,
            )
            return None
        self._record_load_result(load_result)
        self._reconcile_parameters(load_result.parameters or [])
        self._apply_load_payload(load_result)
        self.feature_states = load_result.features or []
        self._effective_debug = load_result.debug
        self.load_status = load_result.status
        self._notify_export_availability()
        return load_result

    def _record_load_result(self, load_result: LoadResult) -> None:
        self._current_load_number = load_result.load_number
        self._current_load_sequence_number = load_result.sequence_number
        self._current_load_revision = load_result.revision
        if load_result.complete:
            self._active_load_generation = None

    def _apply_load_payload(self, load_result: LoadResult) -> None:
        if load_result.payload is not None:
            logger.debug("check_load_queue got mesh")
            self.current_mesh = load_result.payload
        else:
            logger.debug("check_load_queue got mesh == None")
        self._exportable_payload = (
            cast(MeshPayload, load_result.payload) if load_result.exportable else None
        )

    def _load_is_active(self) -> bool:
        return self._active_load_generation == self.current_generation

    def set_feature_enabled(self, name: str, enabled: bool) -> None:
        if self.module_path == "":
            raise ValueError("No module loaded")
        feature_states = self._feature_state_map()
        if feature_states.get(name, True) == enabled:
            return
        feature_states[name] = enabled
        self.feature_states = self._feature_states_with_override(name, enabled)
        self._queue_feature_reload(feature_states)

    def set_debug_features(self, enabled: bool) -> bool:
        if self._debug_features == enabled:
            return False
        self._debug_features = enabled
        self.on_debug_features_change.notify(enabled)
        if self.module_path == "":
            return False
        self._queue_feature_reload(self._feature_state_map())
        return True

    def set_parameter_value(self, name: str, value: ScalarParameterValue) -> None:
        parameter = next((item for item in self.parameters if item.name == name), None)
        if parameter is None or type(value).__name__ != parameter.type:
            raise ValueError(f"Invalid value for parameter '{name}'")
        if self._parameter_values.get(name) == value:
            return
        self._parameter_values[name] = value
        self._queue_feature_reload(self._feature_state_map())

    def reset_parameter_values(self) -> bool:
        defaults = {parameter.name: parameter.default for parameter in self.parameters}
        if defaults == self._parameter_values:
            return False
        self._parameter_values = defaults
        self.on_parameters_change.notify(self._parameters)
        self._queue_feature_reload(self._feature_state_map())
        return True

    def export(self, file_path: str) -> bool:
        if self._closed or not self.exportable_payload or self.export_pending:
            logger.info("No mesh to export")
            return False
        self._last_export_path = file_path
        request_id = self._next_export_request_id
        self._next_export_request_id += 1
        self._pending_export_request_id = request_id
        self._pending_export_generation = self.current_generation
        self._notify_export_availability()
        command = ExportCommand(request_id, self.current_generation, file_path)
        try:
            self._command_queue.put(command)
        except (BrokenPipeError, EOFError, OSError, ValueError) as error:
            self._complete_pending_export_error(
                ExportError(type(error).__name__, str(error))
            )
            return False
        return True

    @property
    def exportable_payload(self) -> MeshPayload | None:
        """Return the payload explicitly marked exportable by the loader."""
        return self._exportable_payload

    @property
    def export_pending(self) -> bool:
        return self._pending_export_request_id is not None

    @property
    def export_available(self) -> bool:
        return self.exportable_payload is not None and not self.export_pending

    def check_export_queue(self) -> None:
        while True:
            try:
                result = self._export_result_queue.get_nowait()
            except queue.Empty:
                self._complete_export_after_loader_death()
                return
            except (EOFError, OSError, ValueError) as error:
                self._complete_pending_export_error(
                    ExportError(type(error).__name__, str(error))
                )
                return
            if (
                result.request_id == self._pending_export_request_id
                and result.generation == self._pending_export_generation
            ):
                self._complete_export(result)
                return
            logger.warning(
                "Discarding unrelated export result request=%s generation=%s",
                result.request_id,
                result.generation,
            )

    def _complete_export_after_loader_death(self) -> None:
        if self._pending_export_request_id is None:
            return
        if self._loader_process.is_alive():
            return
        self._complete_pending_export_error(
            ExportError("LoaderProcessDied", "Mesh loader process exited")
        )

    def _complete_pending_export_error(self, error: ExportError) -> None:
        request_id = self._pending_export_request_id
        generation = self._pending_export_generation
        if request_id is None or generation is None:
            return
        self._complete_export(ExportResult(request_id, generation, error))

    def _complete_export(self, result: ExportResult) -> None:
        self._clear_pending_export()
        self._notify_export_availability()
        self.on_export_result.notify(result)

    def _clear_pending_export(self) -> None:
        self._pending_export_request_id = None
        self._pending_export_generation = None

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
        self._export_result_queue.close()

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

    def _queue_feature_reload(self, feature_states: dict[str, bool]) -> None:
        self._queue_load(feature_states)

    def _queue_load(self, feature_states: dict[str, bool]) -> None:
        self.current_mesh = None
        self._exportable_payload = None
        self.load_status = LoadStatus.START
        self._current_generation += 1
        self._current_load_number = 0
        self._current_load_sequence_number = 0
        self._current_load_revision = 0
        self._active_load_generation = self.current_generation
        self._local_load_result = None
        self._notify_export_availability()
        try:
            self._command_queue.put(
                LoadMeshCommand(
                    self.module_path,
                    feature_states,
                    debug_features=self.debug_features,
                    parameter_values=self.parameter_values,
                    generation=self.current_generation,
                )
            )
        except (EOFError, OSError, ValueError) as error:
            self._local_load_result = self._complete_load_error(
                LoadError(type(error).__name__, str(error))
            )

    def _notify_export_availability(self) -> None:
        self.on_export_availability_change.notify(self.export_available)

    def _reconcile_parameters(self, parameters: list[CreateMeshParameter]) -> None:
        values = {
            parameter.name: self._parameter_values.get(
                parameter.name, parameter.default
            )
            for parameter in parameters
            if self._parameter_type_is_compatible(parameter)
        }
        if parameters == self._parameters and values == self._parameter_values:
            return
        self._parameters = parameters
        self._parameter_values = values
        self.on_parameters_change.notify(parameters)

    def _parameter_type_is_compatible(self, parameter: CreateMeshParameter) -> bool:
        old = next(
            (item for item in self._parameters if item.name == parameter.name), None
        )
        return old is None or old.type == parameter.type

    def _same_module(self, module_path: str) -> bool:
        return os.path.abspath(module_path) == os.path.abspath(self.module_path)
