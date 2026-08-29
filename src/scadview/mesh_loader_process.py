from __future__ import annotations

import colorsys
import logging
import queue
from dataclasses import dataclass
from multiprocessing import Process, Queue
from multiprocessing import queues as mp_queues
from threading import Thread
from time import time
from typing import Any, Generator, Generic, Type, TypeVar

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
from scadview.module_loader import ModuleLoader

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

    def __init__(self, maxsize: int, type_: Type[T]):
        self._queue = Queue(maxsize=maxsize)
        self._type = type_

    def get_nowait(self) -> T:
        return self.get(False)

    def put_nowait(self, item: T):
        return self.put(item, False)

    def put(self, item: T, block: bool = True, timeout: float | None = None):
        item = self._check_type(item)
        return self._queue.put(item, block=block, timeout=timeout)

    def get(self, block: bool = True, timeout: float | None = None) -> T:
        item = self._queue.get(block=block, timeout=timeout)
        return self._check_type(item)

    def _check_type(self, item: Any) -> T:
        if isinstance(item, self._type):
            return item
        raise ValueError(f"The item is not of type {self._type}, it is a {type(item)}")

    def close(self):
        self._queue.close()
        self._queue.join_thread()


class Command:
    pass


class LoadMeshCommand(Command):
    def __init__(
        self,
        module_path: str,
        feature_states: dict[str, bool] | None = None,
        debug_features: bool = False,
    ):
        self.module_path = module_path
        self.feature_states = feature_states or {}
        self.debug_features = debug_features


class CancelLoadCommand(Command):
    pass


class ShutDownCommand(Command):
    pass


MeshType = Trimesh | list[Trimesh]
CreateMeshItemType = Trimesh | Manifold | FeatureMesh | NullFeatureMesh
CreateMeshResultType = CreateMeshItemType | list[CreateMeshItemType]


@dataclass
class LoadResult:
    load_number: int
    sequence_number: int
    mesh: MeshType | None
    error: Exception | None
    complete: bool = False
    features: list[FeatureState] | None = None

    @property
    def debug(self) -> bool:
        return isinstance(self.mesh, list)

    @property
    def status(self) -> LoadStatus:
        if self.error is not None:
            return LoadStatus.ERROR
        if self.debug:
            return LoadStatus.DEBUG
        if self.complete:
            return LoadStatus.COMPLETE
        if self.mesh is not None:
            return LoadStatus.START
        return LoadStatus.NONE


MpLoadQueue = MpQueue[LoadResult]
MpCommandQueue = MpQueue[Command]


def debug_color() -> Generator[tuple[float, float, float], None, None]:
    """
    Generate a random color for debugging purposes
    """
    hue = 0.0
    while True:
        hue = (hue + COLOR_GOLDEN_ANGLE) % 1.0
        yield colorsys.hsv_to_rgb(hue, 1.0, 1.0)


class LoadWorker(Thread):
    PUT_QUEUE_TIMEOUT = 0.1
    load_number = 0

    def __init__(
        self,
        module_path: str,
        load_queue: MpLoadQueue,
        feature_states: dict[str, bool] | None = None,
        debug_features: bool = False,
    ):
        super().__init__()
        self.module_path = module_path
        self.load_queue = load_queue
        self.cancelled = False
        self.feature_states = feature_states or {}
        self.debug_features = debug_features
        self._loaded_feature_states: list[FeatureState] = []
        self._feature_sources = []

    def run(self):
        LoadWorker.load_number += 1
        self.load()

    def load(self):
        sequence_number = 0
        self.load_start_time = time()
        last_mesh = None
        try:
            for mesh in self.run_mesh_module():
                last_mesh = mesh
                sequence_number += 1
                if self.cancelled:
                    logger.info("LoadWorker cancelled, stopping load")
                    return
                self._update_mesh(sequence_number, mesh)
        except Exception as e:
            logger.exception("Failed to load mesh from %s", self.module_path)
            self._update_mesh(sequence_number, last_mesh, final=True, error=e)
            return
        self._update_mesh(sequence_number, last_mesh, final=True)

    def _update_mesh(
        self,
        sequence_number: int,
        mesh: CreateMeshResultType | None,
        final: bool = False,
        error: Exception | None = None,
    ):
        tmesh = self._ensure_trimesh(mesh) if mesh is not None else None
        tmesh = self._select_debug_mesh(tmesh)
        self._color_if_debug(tmesh)

        self.put_in_queue(
            LoadResult(
                self.load_number,
                sequence_number,
                tmesh,
                error=error,
                complete=final,
                features=self._current_feature_states(),
            )
        )

    def _ensure_trimesh(self, mesh: CreateMeshResultType | None) -> MeshType | None:
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
            return self._ensure_trimesh(operand.native())
        if isinstance(mesh, Trimesh):
            return mesh
        if isinstance(mesh, Manifold):
            return manifold_to_trimesh(mesh)
        if isinstance(mesh, list):
            result: list[Trimesh] = []
            for m in mesh:
                if isinstance(m, FeatureMesh):
                    operand = m.as_operand()
                    if operand.is_empty():
                        continue
                    if isinstance(operand, BooleanMesh):
                        m = operand.native()
                if isinstance(m, Trimesh):
                    result.append(m)
                elif isinstance(m, Manifold):
                    result.append(manifold_to_trimesh(m))
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

    def _select_debug_mesh(self, mesh: MeshType | None) -> MeshType | None:
        if not self.debug_features:
            return mesh
        sources = [source.mesh for source in self._feature_sources if source.enabled]
        if not sources:
            return mesh
        return self._ensure_trimesh(sources)

    def _color_if_debug(self, tmesh: MeshType | None):
        if isinstance(tmesh, list):
            for tm, color in zip(tmesh, debug_color()):
                if "scadview" not in tm.metadata:
                    set_mesh_color(tm, color, alpha=DEBUG_COLOR_ALPHA)

    def put_in_queue(self, result: LoadResult):
        result_put = False
        while not result_put:  # tends to be race conditions between full and empty
            if self.cancelled:
                logger.info("LoadWorker cancelled, stopping load")
                return
            try:
                self.load_queue.put(result, timeout=self.PUT_QUEUE_TIMEOUT)
                result_put = True
            except queue.Full:
                try:
                    _ = self.load_queue.get_nowait()
                except queue.Empty:
                    pass

    def run_mesh_module(self) -> Generator[CreateMeshResultType, None, None]:
        module_loader = ModuleLoader(CREATE_MESH_FUNCTION_NAME)
        set_enabled_feature_states(self.feature_states)
        begin_feature_capture()
        t0 = time()
        try:
            for i, mesh in enumerate(module_loader.run_function(self.module_path)):
                logger.info(f"Loading mesh #{i + 1}")
                self._check_mesh_type(mesh)
                self._feature_sources = get_feature_sources()
                yield mesh
        finally:
            t1 = time()
            logger.info(f"Load {self.module_path} took {(t1 - t0) * 1000:.1f}ms")
            set_enabled_feature_states(None)

    def _current_feature_states(self) -> list[FeatureState]:
        feature_states = get_feature_states()
        if feature_states:
            self._loaded_feature_states = feature_states
        return self._loaded_feature_states

    def _check_mesh_type(self, mesh: Any):
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

    def _check_trimesh_vertices(self, mesh: Trimesh):
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

    def _check_manifold(self, mesh: Manifold, list_index: int | None = None):
        status = mesh.status()
        if status == ManifoldError.NoError:
            return
        prefix = "Manifold mesh"
        if list_index is not None:
            prefix = f"Manifold mesh[{list_index}]"
        raise ValueError(f"{prefix} has invalid status: {status.name}")

    def cancel(self):
        self.cancelled = True


class MeshLoaderProcess(Process):
    COMMAND_QUEUE_CHECK_TIMEOUT = 0.1

    def __init__(
        self,
        command_queue: MpCommandQueue,
        load_queue: MpLoadQueue,
        log_queue: mp_queues.Queue[logging.LogRecord],
        log_level: int,
    ):
        super().__init__()
        self._command_queue = command_queue
        self._load_queue = load_queue
        self._worker: LoadWorker | None = None
        self._log_queue = log_queue
        self._log_level = log_level

    def run(self) -> None:
        # Set logging level for the loaded module; it can be changed in that module
        configure_worker_logging(self._log_queue, logging.DEBUG)

        # Set the level for the logger in the function to the level passed
        logger.setLevel(self._log_level)

        while True:
            try:
                command = self._command_queue.get(
                    timeout=self.COMMAND_QUEUE_CHECK_TIMEOUT
                )
            except queue.Empty:
                continue
            if isinstance(command, LoadMeshCommand):
                self.cancel()
                logger.info(f"Loading mesh from {command.module_path}")
                self._worker = LoadWorker(
                    command.module_path,
                    self._load_queue,
                    feature_states=command.feature_states,
                    debug_features=command.debug_features,
                )
                self._worker.start()
            elif isinstance(command, CancelLoadCommand):
                logger.info("Load cancelled")
                self.cancel()
                continue
            elif isinstance(command, ShutDownCommand):
                logger.info("Shutting down loader process")
                self.cancel(close_queues=True)
                return
            else:
                logger.warning(f"Unknown command received: {command}")

    def cancel(self, close_queues: bool = False):
        if self._worker is not None and self._worker.is_alive():
            logger.info("Cancelling in progress load")
            self._worker.cancel()
        if close_queues:
            self._command_queue.close()
            self._load_queue.close()
        self._worker = None
