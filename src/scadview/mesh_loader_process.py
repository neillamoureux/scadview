from __future__ import annotations

import colorsys
import logging
import queue
from dataclasses import dataclass
from enum import Enum
from multiprocessing import Process, Queue
from multiprocessing import queues as mp_queues
from threading import Condition, Event, Lock, Thread
from time import monotonic, time
from typing import (
    Any,
    Generator,
    Generic,
    Iterable,
    NoReturn,
    Self,
    SupportsIndex,
    Type,
    TypeVar,
    cast,
)

import numpy as np
from manifold3d import Error as ManifoldError
from manifold3d import Manifold
from trimesh import Trimesh

from scadview.api.colors import set_mesh_color
from scadview.api.utils import manifold_to_trimesh
from scadview.features import (
    BooleanMesh,
    FeatureMesh,
    FeatureState,
    NullFeatureMesh,
    begin_feature_capture,
    get_feature_sources,
    get_feature_states,
    set_enabled_feature_states,
)
from scadview.load_status import LoadStatus
from scadview.logging_worker import configure_worker_logging
from scadview.mesh_payload import MeshPayload, manifold_to_payload, mesh_to_payload
from scadview.module_loader import (
    CreateMeshParameter,
    ModuleLoader,
    ScalarParameterValue,
)

logger = logging.getLogger(__name__)


CREATE_MESH_FUNCTION_NAME = "create_mesh"
COLOR_GOLDEN_ANGLE = (
    0.381966  # "golden angle"/360 to ensure good distribution of colors
)
DEBUG_COLOR_ALPHA = 0.5

T = TypeVar("T")


class MpQueue(Generic[T]):
    """
    Wrapper around queue to ensure only T is in the queue
    """

    def __init__(self, maxsize: int, type_: Type[T]) -> None:
        self._queue = Queue(maxsize=maxsize)
        self._type = type_

    def get_nowait(self) -> T:
        return self.get(False)

    def put_nowait(self, item: T) -> None:
        return self.put(item, False)

    def put(self, item: T, block: bool = True, timeout: float | None = None) -> None:
        item = self._check_type(item)
        return self._queue.put(item, block=block, timeout=timeout)

    def get(self, block: bool = True, timeout: float | None = None) -> T:
        item = self._queue.get(block=block, timeout=timeout)
        return self._check_type(item)

    def _check_type(self, item: Any) -> T:
        if isinstance(item, self._type):
            return item
        raise ValueError(f"The item is not of type {self._type}, it is a {type(item)}")

    def close(self, discard: bool = False) -> None:
        if discard:
            self._queue.cancel_join_thread()
        self._queue.close()
        if not discard:
            self._queue.join_thread()


class LoadEventChannel:
    def __init__(self, maxsize: int = 1) -> None:
        self._queue: queue.Queue[LoadResult] = queue.Queue(maxsize=maxsize)
        self._put_lock = Lock()

    def put_latest(self, result: LoadResult, timeout: float = 0.1) -> None:
        with self._put_lock:
            while True:
                try:
                    self._queue.put(result, timeout=timeout)
                    return
                except queue.Full:
                    try:
                        queued = self._queue.get_nowait()
                    except queue.Empty:
                        continue
                    if queued.generation > result.generation:
                        result = queued

    def get_nowait(self) -> LoadResult:
        return self._queue.get_nowait()

    def get(self, block: bool = True, timeout: float | None = None) -> LoadResult:
        return self._queue.get(block=block, timeout=timeout)

    def close(self, discard: bool = False) -> None:
        if discard:
            while True:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    return


class Command:
    pass


class LoadMeshCommand(Command):
    def __init__(
        self,
        module_path: str,
        feature_states: dict[str, bool] | None = None,
        debug_features: bool = False,
        parameter_values: dict[str, ScalarParameterValue] | None = None,
        generation: int = 0,
    ) -> None:
        self.module_path = module_path
        self.feature_states = feature_states or {}
        self.debug_features = debug_features
        self.parameter_values = parameter_values or {}
        self.generation = generation


class CancelLoadCommand(Command):
    pass


@dataclass(frozen=True)
class ExportCommand(Command):
    request_id: int
    generation: int
    path: str


class ShutDownCommand(Command):
    pass


NativeMeshType = Trimesh | Manifold
SourceMeshType = NativeMeshType | list[NativeMeshType]
MeshType = MeshPayload | list[MeshPayload]
CreateMeshItemType = Trimesh | Manifold | FeatureMesh | NullFeatureMesh
CreateMeshResultType = CreateMeshItemType | list[CreateMeshItemType]


@dataclass(frozen=True)
class LoadError:
    type_name: str
    message: str


class FrozenList(list[Any]):
    def _raise_immutable(self, *_args: Any, **_kwargs: Any) -> NoReturn:
        raise TypeError("Load result collections are immutable")

    __delitem__ = __setitem__ = _raise_immutable
    append = clear = extend = insert = pop = remove = reverse = sort = _raise_immutable

    def __iadd__(self, _value: Iterable[Any]) -> Self:
        self._raise_immutable()

    def __imul__(self, _value: Any) -> Self:
        self._raise_immutable()

    def __reduce__(self) -> tuple[type[FrozenList], tuple[list[Any]]]:
        return type(self), (list(self),)

    def __reduce_ex__(
        self, _protocol: SupportsIndex
    ) -> tuple[type[FrozenList], tuple[list[Any]]]:
        return self.__reduce__()


class LoadPhase(Enum):
    PROGRESS = "progress"
    FINAL = "final"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class FinalMeshSnapshot:
    source: NativeMeshType
    payload: MeshPayload


@dataclass(frozen=True)
class LoadResult:
    load_number: int
    sequence_number: int
    payload: MeshType | None
    error: LoadError | None
    phase: LoadPhase
    revision: int
    exportable: bool
    debug: bool
    features: list[FeatureState] | None = None
    parameters: list[CreateMeshParameter] | None = None
    generation: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.payload, list):
            object.__setattr__(self, "payload", FrozenList(self.payload))
        if self.features is not None:
            object.__setattr__(self, "features", FrozenList(self.features))
        if self.parameters is not None:
            object.__setattr__(self, "parameters", FrozenList(self.parameters))
        self._validate_explicit_state()
        self._validate_error_state()
        self._validate_debug_state()
        self._validate_exportable_state()

    def _validate_explicit_state(self) -> None:
        if not isinstance(self.phase, LoadPhase):
            raise ValueError("Load result phase must be a LoadPhase")
        if (
            not isinstance(self.revision, int)
            or isinstance(self.revision, bool)
            or self.revision < 0
        ):
            raise ValueError("Load result revision must be a non-negative integer")
        if not isinstance(self.exportable, bool) or not isinstance(self.debug, bool):
            raise ValueError("Load result exportable and debug state must be boolean")

    def _validate_error_state(self) -> None:
        if self.phase is LoadPhase.ERROR:
            if not isinstance(self.error, LoadError):
                raise ValueError("Error-phase load results require a LoadError")
            return
        if self.error is not None:
            raise ValueError("Only error-phase load results may contain an error")

    def _validate_debug_state(self) -> None:
        if isinstance(self.payload, list) and not self.debug:
            raise ValueError("List payloads must be explicitly marked as debug")
        if isinstance(self.payload, MeshPayload) and self.debug:
            raise ValueError("Single payloads must be explicitly marked non-debug")

    def _validate_exportable_state(self) -> None:
        final_single_payload = (
            self.phase is LoadPhase.FINAL
            and isinstance(self.payload, MeshPayload)
            and not self.debug
        )
        if self.exportable and not final_single_payload:
            raise ValueError("Only final single-payload load results are exportable")
        if final_single_payload and not self.exportable:
            raise ValueError(
                "Final non-debug single-payload load results must be exportable"
            )

    @property
    def complete(self) -> bool:
        return self.phase in {
            LoadPhase.FINAL,
            LoadPhase.ERROR,
            LoadPhase.CANCELLED,
        }

    @property
    def status(self) -> LoadStatus:
        if self.phase is LoadPhase.ERROR:
            return LoadStatus.ERROR
        if self.phase is LoadPhase.CANCELLED:
            return LoadStatus.CANCELLED
        if self.phase is LoadPhase.FINAL and self.debug:
            return LoadStatus.DEBUG
        if self.phase is LoadPhase.FINAL:
            return LoadStatus.COMPLETE
        if self.phase is LoadPhase.PROGRESS:
            return LoadStatus.START
        return LoadStatus.NONE


@dataclass(frozen=True)
class ExportError:
    type_name: str
    message: str


@dataclass(frozen=True)
class ExportResult:
    request_id: int
    generation: int
    error: ExportError | None = None


MpLoadQueue = MpQueue[LoadResult]
MpCommandQueue = MpQueue[Command]
MpExportResultQueue = MpQueue[ExportResult]


def debug_color() -> Generator[tuple[float, float, float], None, None]:
    """
    Generate a random color for debugging purposes
    """
    hue = 0.0
    while True:
        hue = (hue + COLOR_GOLDEN_ANGLE) % 1.0
        yield colorsys.hsv_to_rgb(hue, 1.0, 1.0)


@dataclass(frozen=True)
class SourceProgress:
    sequence_number: int
    mesh: SourceMeshType | None
    features: list[FeatureState]


class SourceProgressChannel:
    def __init__(self) -> None:
        self._condition = Condition()
        self._pending: SourceProgress | None = None
        self._closed = False

    def put_latest(self, source: SourceProgress) -> None:
        with self._condition:
            if not self._closed:
                self._pending = source
                self._condition.notify()

    def take(self) -> SourceProgress | None:
        with self._condition:
            self._condition.wait_for(lambda: self._pending is not None or self._closed)
            source, self._pending = self._pending, None
            return source

    def close(self, discard: bool = False) -> None:
        with self._condition:
            self._closed = True
            if discard:
                self._pending = None
            self._condition.notify_all()


class LoadWorker(Thread):
    PUT_QUEUE_TIMEOUT = 0.1
    load_number = 0
    _load_number_lock = Lock()

    def __init__(
        self,
        module_path: str,
        load_queue: LoadEventChannel,
        feature_states: dict[str, bool] | None = None,
        debug_features: bool = False,
        parameter_values: dict[str, ScalarParameterValue] | None = None,
        generation: int = 0,
    ) -> None:
        super().__init__(daemon=True)
        self.module_path = module_path
        self.load_queue = load_queue
        self.cancelled = False
        self.feature_states = feature_states or {}
        self.debug_features = debug_features
        self.parameter_values = parameter_values or {}
        self.generation = generation
        self._parameters: list[CreateMeshParameter] | None = None
        self._loaded_feature_states: list[FeatureState] = []
        self._feature_sources = []
        self.final_snapshot: FinalMeshSnapshot | None = None
        self._revision = 0
        self._terminal_lock = Lock()
        self._terminal_claimed = False
        self._sources = SourceProgressChannel()
        self._conversion_failed = Event()
        self._progress_payload: MeshType | None = None

    @property
    def export_source(self) -> NativeMeshType | None:
        if self.final_snapshot is None:
            return None
        return self.final_snapshot.source

    def run(self) -> None:
        with self._load_number_lock:
            LoadWorker.load_number += 1
            self.load_number = LoadWorker.load_number
        self.load()

    def load(self) -> None:
        sequence_number = 0
        self.load_start_time = time()
        last_mesh: CreateMeshResultType | None = None
        terminal_phase = LoadPhase.FINAL
        terminal_error = None
        converter = Thread(target=self._convert_progress, daemon=True)
        converter.start()
        try:
            for mesh in self.run_mesh_module():
                sequence_number += 1
                if self.cancelled:
                    logger.info("LoadWorker cancelled, stopping load")
                    terminal_phase = LoadPhase.CANCELLED
                    break
                if self._conversion_failed.is_set():
                    break
                last_mesh = mesh
                prepared = self._prepare_source(mesh)
                self._sources.put_latest(
                    SourceProgress(
                        sequence_number,
                        self._copy_progress_source(prepared),
                        self._current_feature_states(),
                    )
                )
        except Exception as error:
            logger.exception("Failed to load mesh from %s", self.module_path)
            terminal_phase = LoadPhase.ERROR
            terminal_error = LoadError(type(error).__name__, str(error))
        finally:
            self._sources.close(discard=self.cancelled)
            converter.join()
        self._publish_terminal_result(
            sequence_number,
            last_mesh,
            self._progress_payload,
            terminal_phase,
            terminal_error,
        )

    def _convert_progress(self) -> None:
        source: SourceProgress | None = None
        try:
            while (source := self._sources.take()) is not None:
                if self.cancelled:
                    return
                payload = self._payload_mesh(source.mesh)
                self._progress_payload = payload
                self._publish_result(
                    source.sequence_number,
                    payload,
                    debug=isinstance(source.mesh, list),
                    features=source.features,
                )
        except Exception as error:
            logger.exception("Failed to convert mesh from %s", self.module_path)
            self._conversion_failed.set()
            self._sources.close(discard=True)
            self._publish_terminal_result(
                source.sequence_number if source is not None else 0,
                None,
                self._progress_payload,
                LoadPhase.ERROR,
                LoadError(type(error).__name__, str(error)),
                features=source.features if source is not None else [],
            )

    def _copy_progress_source(
        self, mesh: SourceMeshType | None
    ) -> SourceMeshType | None:
        if isinstance(mesh, list):
            source_meshes = cast(list[NativeMeshType], mesh)
            return [self._copy_progress_mesh(item) for item in source_meshes]
        return self._copy_progress_mesh(mesh) if mesh is not None else None

    def _copy_progress_mesh(self, mesh: NativeMeshType) -> NativeMeshType:
        if isinstance(mesh, Manifold):
            return mesh
        snapshot = mesh.copy()
        # The public setter may discard supplied normals that differ from geometry.
        snapshot._cache["face_normals"] = mesh.face_normals.copy()
        return snapshot

    def _publish_terminal_result(
        self,
        sequence_number: int,
        mesh: CreateMeshResultType | None,
        payload: MeshType | None,
        phase: LoadPhase,
        error: LoadError | None,
        features: list[FeatureState] | None = None,
    ) -> None:
        if not self._claim_terminal():
            return
        if self.cancelled:
            phase = LoadPhase.CANCELLED
            error = None
        try:
            if phase is LoadPhase.CANCELLED:
                self.final_snapshot = None
                self._publish_result(
                    sequence_number,
                    payload,
                    phase=phase,
                    allow_cancelled=True,
                    debug=isinstance(payload, list),
                    features=features,
                )
                return
            self._publish_final_result(
                sequence_number,
                mesh,
                payload,
                error,
                features,
            )
        except Exception as finalization_error:
            logger.exception("Failed to finalize mesh from %s", self.module_path)
            self.final_snapshot = None
            load_error = error or LoadError(
                type(finalization_error).__name__, str(finalization_error)
            )
            self._publish_terminal_error(sequence_number, payload, load_error, features)

    def _claim_terminal(self) -> bool:
        with self._terminal_lock:
            if self._terminal_claimed:
                return False
            self._terminal_claimed = True
            return True

    def _publish_terminal_error(
        self,
        sequence_number: int,
        payload: MeshType | None,
        error: LoadError,
        features: list[FeatureState] | None = None,
    ) -> None:
        self._revision += 1
        self.put_in_queue(
            LoadResult(
                self.load_number,
                sequence_number,
                payload=payload,
                error=error,
                features=list(self._loaded_feature_states)
                if features is None
                else features,
                parameters=self._parameters,
                generation=self.generation,
                revision=self._revision,
                phase=LoadPhase.ERROR,
                exportable=False,
                debug=isinstance(payload, list),
            ),
            allow_cancelled=True,
        )

    def _prepare_mesh(
        self,
        mesh: CreateMeshResultType | SourceMeshType | None,
    ) -> tuple[SourceMeshType | None, MeshType | None]:
        tmesh = self._prepare_source(mesh)
        return tmesh, self._payload_mesh(tmesh)

    def _prepare_source(
        self, mesh: CreateMeshResultType | SourceMeshType | None
    ) -> SourceMeshType | None:
        tmesh = self._resolve_source(mesh) if mesh is not None else None
        tmesh = self._select_debug_mesh(tmesh)
        self._color_if_debug(tmesh)
        return tmesh

    def _publish_result(
        self,
        sequence_number: int,
        payload: MeshType | None,
        error: LoadError | None = None,
        phase: LoadPhase = LoadPhase.PROGRESS,
        allow_cancelled: bool = False,
        exportable: bool = False,
        debug: bool = False,
        features: list[FeatureState] | None = None,
    ) -> None:
        self._revision += 1
        self.put_in_queue(
            LoadResult(
                self.load_number,
                sequence_number,
                payload=payload,
                error=error,
                features=self._current_feature_states()
                if features is None
                else features,
                parameters=self._parameters,
                generation=self.generation,
                revision=self._revision,
                phase=phase,
                exportable=exportable,
                debug=debug,
            ),
            allow_cancelled=allow_cancelled,
        )

    def _publish_final_result(
        self,
        sequence_number: int,
        mesh: CreateMeshResultType | None,
        payload: MeshType | None,
        error: LoadError | None = None,
        features: list[FeatureState] | None = None,
    ) -> None:
        source = None
        if error is None:
            source, payload = self._prepare_mesh(mesh)
        snapshot = self._final_snapshot(source, payload, error)
        self.final_snapshot = snapshot
        self._publish_result(
            sequence_number,
            payload,
            error,
            phase=LoadPhase.ERROR if error is not None else LoadPhase.FINAL,
            allow_cancelled=True,
            exportable=snapshot is not None,
            debug=isinstance(payload, list),
            features=features,
        )

    def _final_snapshot(
        self,
        mesh: SourceMeshType | None,
        payload: MeshType | None,
        error: LoadError | None,
    ) -> FinalMeshSnapshot | None:
        if error is not None or not isinstance(mesh, (Trimesh, Manifold)):
            return None
        if not isinstance(payload, MeshPayload):
            return None
        return FinalMeshSnapshot(mesh, payload)

    def _resolve_source(
        self, mesh: CreateMeshResultType | SourceMeshType | None
    ) -> SourceMeshType | None:
        if mesh is None:
            return None
        if isinstance(mesh, NullFeatureMesh):
            return None
        if isinstance(mesh, FeatureMesh):
            operand = mesh.as_operand()
            if operand.is_empty():
                return None
            if not isinstance(operand, BooleanMesh):
                raise TypeError(f"Expected non-empty feature mesh, got {type(operand)}")
            return self._resolve_source(operand.native())
        if isinstance(mesh, (Trimesh, Manifold)):
            return mesh
        if isinstance(mesh, list):
            result: list[NativeMeshType] = []
            for m in mesh:
                if isinstance(m, FeatureMesh):
                    operand = m.as_operand()
                    if operand.is_empty():
                        continue
                    if isinstance(operand, BooleanMesh):
                        m = operand.native()
                if isinstance(m, (Trimesh, Manifold)):
                    result.append(m)
                else:
                    raise TypeError(
                        f"Expected mesh item to be of type Trimesh or Manifold, got {type(m)}"
                    )
            if not result:
                return None
            return result
        raise TypeError(
            "Expected mesh to be of type Trimesh, FeatureMesh, list[Trimesh], "
            f"Manifold, or list[Manifold], got {type(mesh)}"
        )

    def _select_debug_mesh(self, mesh: SourceMeshType | None) -> SourceMeshType | None:
        if not self.debug_features:
            return mesh
        sources = [source.mesh for source in self._feature_sources if source.enabled]
        if not sources:
            return mesh
        return self._resolve_source(sources)

    def _color_if_debug(self, tmesh: SourceMeshType | None) -> None:
        if isinstance(tmesh, list):
            for tm, color in zip(tmesh, debug_color()):
                if isinstance(tm, Trimesh) and "scadview" not in tm.metadata:
                    set_mesh_color(tm, color, alpha=DEBUG_COLOR_ALPHA)

    def _payload_mesh(self, mesh: SourceMeshType | None) -> MeshType | None:
        if mesh is None:
            return None
        if isinstance(mesh, list):
            source_meshes = cast(list[NativeMeshType], mesh)
            return [
                self._payload_item(item, (*color, DEBUG_COLOR_ALPHA))
                for item, color in zip(source_meshes, debug_color())
            ]
        return self._payload_item(mesh)

    def _payload_item(
        self,
        mesh: NativeMeshType,
        color: tuple[float, float, float, float] | None = None,
    ) -> MeshPayload:
        if isinstance(mesh, Manifold):
            return manifold_to_payload(mesh, color)
        return mesh_to_payload(mesh)

    def put_in_queue(
        self,
        result: LoadResult,
        allow_cancelled: bool = False,
    ) -> None:
        if self.cancelled and not allow_cancelled:
            logger.info("LoadWorker cancelled, stopping load")
            return
        self.load_queue.put_latest(result, timeout=self.PUT_QUEUE_TIMEOUT)

    def run_mesh_module(self) -> Generator[CreateMeshResultType, None, None]:
        module_loader = ModuleLoader(CREATE_MESH_FUNCTION_NAME)
        set_enabled_feature_states(self.feature_states)
        begin_feature_capture()
        t0 = time()
        try:
            function_results = self._function_results(module_loader)
            self._parameters = self._module_parameters(module_loader)
            for i, mesh in enumerate(function_results):
                logger.info(f"Loading mesh #{i + 1}")
                self._check_mesh_type(mesh)
                self._feature_sources = get_feature_sources()
                yield mesh
        finally:
            self._feature_sources = get_feature_sources()
            self._loaded_feature_states = get_feature_states()
            t1 = time()
            logger.info(f"Load {self.module_path} took {(t1 - t0) * 1000:.1f}ms")
            set_enabled_feature_states(None)

    def _function_results(
        self, module_loader: ModuleLoader
    ) -> Generator[Any, None, None]:
        if self.parameter_values:
            return module_loader.run_function(self.module_path, self.parameter_values)
        return module_loader.run_function(self.module_path)

    def _module_parameters(
        self, module_loader: ModuleLoader
    ) -> list[CreateMeshParameter]:
        parameters = module_loader.parameters
        if isinstance(parameters, list):
            return parameters
        return []

    def _current_feature_states(self) -> list[FeatureState]:
        feature_states = get_feature_states()
        if feature_states:
            self._loaded_feature_states = feature_states
        return self._loaded_feature_states

    def _check_mesh_type(self, mesh: Any) -> None:
        if isinstance(mesh, FeatureMesh):
            self._check_feature_mesh(mesh)
            return
        if isinstance(mesh, NullFeatureMesh):
            return
        if isinstance(mesh, Trimesh):
            self._check_trimesh_vertices(mesh)
            return
        if isinstance(mesh, Manifold):
            self._check_manifold(mesh)
            return
        if isinstance(mesh, list):
            for i, m in enumerate(mesh):
                if isinstance(m, FeatureMesh):
                    self._check_feature_mesh(m, i)
                    continue
                if isinstance(m, NullFeatureMesh):
                    continue
                if isinstance(m, Trimesh):
                    self._check_trimesh_vertices(m)
                    continue
                if isinstance(m, Manifold):
                    self._check_manifold(m, i)
                    continue
                if not isinstance(m, Trimesh) and not isinstance(m, Manifold):
                    raise TypeError(
                        f"Expected mesh[{i}] to be of type Trimesh, FeatureMesh "
                        f"or Manifold, got {type(m)}"
                    )
            return
        raise TypeError(
            "Expected mesh to be of type Trimesh, FeatureMesh, list[Trimesh], "
            f"Manifold, or list[Manifold], got {type(mesh)}"
        )

    def _check_feature_mesh(
        self,
        feature_mesh: FeatureMesh,
        list_index: int | None = None,
    ):
        operand = feature_mesh.as_operand()
        if operand.is_empty():
            return
        if not isinstance(operand, BooleanMesh):
            raise TypeError(f"Expected non-empty feature mesh, got {type(operand)}")
        resolved_mesh = operand.native()
        if isinstance(resolved_mesh, Trimesh):
            self._check_trimesh_vertices(resolved_mesh)
            return
        if isinstance(resolved_mesh, Manifold):
            self._check_manifold(resolved_mesh, list_index)
            return
        if list_index is None:
            raise TypeError(
                "Expected feature mesh to resolve to Trimesh or Manifold, "
                f"got {type(resolved_mesh)}"
            )
        raise TypeError(
            f"Expected feature mesh[{list_index}] to resolve to Trimesh or "
            f"Manifold, got {type(resolved_mesh)}"
        )

    def _check_trimesh_vertices(self, mesh: Trimesh) -> None:
        if mesh.vertices.size == 0:
            return
        invalid_indices = np.argwhere(~np.isfinite(mesh.vertices))
        if invalid_indices.size == 0:
            return
        first_invalid = invalid_indices[0]
        vertex_index = int(first_invalid[0])
        coord_index = int(first_invalid[1])
        invalid_value = mesh.vertices[vertex_index, coord_index]
        raise ValueError(
            f"Mesh contains non-finite vertex coordinate {invalid_value} at vertices[{vertex_index}][{coord_index}]"
        )

    def _check_manifold(self, mesh: Manifold, list_index: int | None = None) -> None:
        status = mesh.status()
        if status == ManifoldError.NoError:
            return
        prefix = "Manifold mesh"
        if list_index is not None:
            prefix = f"Manifold mesh[{list_index}]"
        raise ValueError(f"{prefix} has invalid status: {status.name}")

    def cancel(self) -> None:
        with self._terminal_lock:
            if self._terminal_claimed:
                return
            self.cancelled = True
            self._sources.close(discard=True)


class MeshLoaderProcess(Process):
    COMMAND_QUEUE_CHECK_TIMEOUT = 0.1
    LOAD_SHUTDOWN_TIMEOUT = 1.0
    EXPORT_SHUTDOWN_TIMEOUT = 1.0

    def __init__(
        self,
        command_queue: MpCommandQueue,
        load_queue: MpLoadQueue,
        export_result_queue: MpExportResultQueue,
        log_queue: mp_queues.Queue[logging.LogRecord],
        log_level: int,
    ) -> None:
        super().__init__()
        self._command_queue = command_queue
        self._load_queue = load_queue
        self._export_result_queue = export_result_queue
        self._worker: LoadWorker | None = None
        self._active_load_workers: set[LoadWorker] = set()
        self._load_events: LoadEventChannel | None = None
        self._active_export_workers: set[ExportWorker] = set()
        self._export_completions: queue.SimpleQueue[ExportResult] | None = None
        self._accepting_exports = True
        self._log_queue = log_queue
        self._log_level = log_level

    def run(self) -> None:
        self._load_events = LoadEventChannel()
        if self._export_completions is None:
            self._export_completions = queue.SimpleQueue()
        # Set logging level for the loaded module; it can be changed in that module
        configure_worker_logging(self._log_queue, logging.DEBUG)

        # Set the level for the logger in the function to the level passed
        logger.setLevel(self._log_level)

        while True:
            self._drain_load_events()
            self._reap_load_workers()
            self._reap_export_workers()
            try:
                command = self._command_queue.get(
                    timeout=self.COMMAND_QUEUE_CHECK_TIMEOUT
                )
            except queue.Empty:
                continue
            if isinstance(command, LoadMeshCommand):
                self._start_load(command)
            elif isinstance(command, CancelLoadCommand):
                logger.info("Load cancelled")
                self.cancel()
                continue
            elif isinstance(command, ExportCommand):
                self._start_export(command)
            elif isinstance(command, ShutDownCommand):
                logger.info("Shutting down loader process")
                self._shutdown()
                return
            else:
                logger.warning(f"Unknown command received: {command}")

    def _drain_load_events(self) -> None:
        load_events = getattr(self, "_load_events", None)
        if load_events is None:
            return
        while True:
            try:
                result = load_events.get_nowait()
            except queue.Empty:
                return
            self._publish_load_result(result)

    def _publish_load_result(self, result: LoadResult) -> None:
        while True:
            try:
                self._load_queue.put(result, timeout=LoadWorker.PUT_QUEUE_TIMEOUT)
                return
            except queue.Full:
                try:
                    queued_result = self._load_queue.get_nowait()
                except queue.Empty:
                    continue
                if queued_result.generation > result.generation:
                    result = queued_result

    def _reap_load_workers(self) -> None:
        for worker in tuple(self._active_load_workers):
            if not worker.is_alive():
                self._active_load_workers.remove(worker)

    def _reap_export_workers(self) -> None:
        self._drain_export_completions()
        for worker in tuple(self._active_export_workers):
            if not worker.is_alive():
                worker.join()
                self._drain_export_completions()
                self._active_export_workers.remove(worker)

    def _drain_export_completions(self) -> None:
        if self._export_completions is None:
            raise RuntimeError("Export completion channel is not initialized")
        while True:
            try:
                result = self._export_completions.get_nowait()
            except queue.Empty:
                return
            self._publish_completed_export_result(result)

    def _start_load(self, command: LoadMeshCommand) -> None:
        self.cancel()
        logger.info(f"Loading mesh from {command.module_path}")
        load_events = getattr(self, "_load_events", None)
        if load_events is None:
            load_events = LoadEventChannel()
            self._load_events = load_events
        worker = LoadWorker(
            command.module_path,
            load_events,
            feature_states=command.feature_states,
            debug_features=command.debug_features,
            parameter_values=command.parameter_values,
            generation=command.generation,
        )
        self._worker = worker
        self._active_load_workers.add(worker)
        worker.start()

    def cancel(self, close_queues: bool = False) -> None:
        for worker in tuple(self._active_load_workers):
            if worker.is_alive():
                logger.info("Cancelling in progress load")
                worker.cancel()
        if close_queues:
            self._command_queue.close()
            self._load_queue.close()
            self._export_result_queue.close()
        self._worker = None

    def _shutdown(self) -> None:
        self._accepting_exports = False
        self.cancel()
        load_deadline = monotonic() + self.LOAD_SHUTDOWN_TIMEOUT
        load_workers_finished = self._join_load_workers(load_deadline)
        export_deadline = monotonic() + self.EXPORT_SHUTDOWN_TIMEOUT
        export_workers_finished = self._join_export_workers(export_deadline)
        if not load_workers_finished or not export_workers_finished:
            return
        self._drain_load_events()
        self._drain_export_completions()
        self._command_queue.close()
        self._load_queue.close()
        self._export_result_queue.close()

    def _join_load_workers(self, deadline: float) -> bool:
        all_finished = True
        for worker in tuple(self._active_load_workers):
            worker.join(timeout=max(0.0, deadline - monotonic()))
            if worker.is_alive():
                logger.warning(
                    "Load worker did not finish before loader shutdown deadline"
                )
                all_finished = False
                continue
            self._active_load_workers.remove(worker)
        return all_finished

    def _join_export_workers(self, deadline: float) -> bool:
        all_finished = True
        for worker in tuple(self._active_export_workers):
            worker.join(timeout=max(0.0, deadline - monotonic()))
            if worker.is_alive():
                logger.warning(
                    "Export worker did not finish before loader shutdown deadline"
                )
                all_finished = False
                continue
            self._drain_export_completions()
            self._active_export_workers.remove(worker)
        self._drain_export_completions()
        return all_finished

    def _start_export(self, command: ExportCommand) -> None:
        if not self._accepting_exports:
            self._publish_export_result(
                command,
                ExportError("ShuttingDown", "Loader is shutting down"),
            )
            return
        source = self._export_source(command.generation)
        if source is None:
            self._publish_export_result(
                command,
                ExportError(
                    "StaleSource", "No export source for the requested generation"
                ),
            )
            return
        snapshot = _snapshot_export_source_at_protocol_boundary(source)
        if isinstance(snapshot, ExportError):
            self._publish_export_result(command, snapshot)
            return
        if self._export_completions is None:
            raise RuntimeError("Export completion channel is not initialized")
        worker = ExportWorker(command, snapshot, self._export_completions)
        self._active_export_workers.add(worker)
        worker.start()

    def _export_source(self, generation: int) -> NativeMeshType | None:
        if self._worker is None or self._worker.generation != generation:
            return None
        return self._worker.export_source

    def _publish_export_result(
        self, command: ExportCommand, error: ExportError | None
    ) -> None:
        self._publish_completed_export_result(
            ExportResult(command.request_id, command.generation, error)
        )

    def _publish_completed_export_result(self, result: ExportResult) -> None:
        self._export_result_queue.put(result)


def _snapshot_export_source_at_protocol_boundary(
    source: NativeMeshType,
) -> Trimesh | ExportError:
    try:
        if isinstance(source, Manifold):
            return manifold_to_trimesh(source)
        return source.copy()
    except Exception as error:
        return ExportError(type(error).__name__, str(error))


class ExportWorker(Thread):
    def __init__(
        self,
        command: ExportCommand,
        source: Trimesh,
        completion_queue: queue.SimpleQueue[ExportResult],
    ) -> None:
        super().__init__(daemon=True)
        self._command = command
        self._source = source
        self._completion_queue = completion_queue

    def run(self) -> None:
        result = _export_result_at_protocol_boundary(self._command, self._source)
        self._completion_queue.put(result)


def _export_result_at_protocol_boundary(
    command: ExportCommand, source: Trimesh
) -> ExportResult:
    try:
        source.export(command.path)
    except Exception as error:
        export_error = ExportError(type(error).__name__, str(error))
    else:
        export_error = None
    return ExportResult(command.request_id, command.generation, export_error)
