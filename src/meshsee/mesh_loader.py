import logging
import queue
from time import time
from typing import Callable

from manifold3d import Manifold
from trimesh import Trimesh

from meshsee.api.utils import manifold_to_trimesh
from meshsee.controller import Controller

logger = logging.getLogger(__name__)


class MeshQueue:
    def __init__(self):
        self._queue = queue.Queue(maxsize=1)

    def get_nowait(self) -> Trimesh:
        mesh = self._queue.get_nowait()  # type: ignore[reportUnknowVariableType] - can't resolve
        if isinstance(mesh, Trimesh):
            return mesh
        if isinstance(mesh, object):
            raise ValueError(f"Mesh queue has a non-mesh item of type {type(mesh)}")
        raise ValueError(f"Mesh queue as a non-mesh item {mesh}")

    def put_nowait(self, mesh: Trimesh):
        return self._queue.put_nowait(mesh)


class MeshLoader:
    """
    Pure python mesh loader to be run in a thread.
    """

    FRAME_PER_SECOND = 30
    UPDATE_MESH_INTERVAL_MS = 1000 / FRAME_PER_SECOND

    def __init__(
        self,
        controller: Controller,
        file_path: str | None,
        load_start_callback: Callable[[], None],
        mesh_update_callback: Callable[[], None],
        load_successful_callback: Callable[[], None],
        stopped_callback: Callable[[], None],
        error_callback: Callable[[], None],
    ):
        self._controller = controller
        self._file_path = file_path
        self._load_start_callback = load_start_callback
        self._mesh_update_callback = mesh_update_callback
        self._load_successful_callback = load_successful_callback
        self._stopped_callback = stopped_callback
        self._error_callback = error_callback
        self._stop_requested = False
        self._stopped = False
        self._first_mesh = True
        self._last_mesh_update = time()
        self._latest_unloaded_mesh = None
        self.mesh_queue = MeshQueue()

    def run(self):
        logger.info("Mesh loading about to start.")
        if self._file_path is not None:
            self._load_start_callback()
        if self._stop_requested:
            logger.warning(
                "A stop of the mesh load has been made before the load started.  The mesh will not be loaded."
            )
            self._signal_stop()
            return
        try:
            logger.debug(f"About to load {self._file_path}")
            for mesh in self._controller.load_mesh(self._file_path):
                logger.debug(
                    f"In load iteration.  _stop_requested is {self._stop_requested}"
                )
                if self._stop_requested:
                    self._signal_stop()
                    return
                self._update_if_time(mesh)
            logger.info(f"Finished loading {self._file_path}")
            self._load_successful_callback()
        except Exception as e:
            logger.exception(f"Error while loading mesh: {e}")
            self._error_callback()
        finally:
            if self._latest_unloaded_mesh is not None:
                self._update_mesh(self._latest_unloaded_mesh)
            self._signal_stop()

    def stop(self):
        self._stop_requested = True
        logger.debug("Current mesh loading stop requested")

    def _signal_stop(self):
        if not self._stopped:
            self._stopped = True
            self._stopped_callback()
            logger.info("Current mesh loading stopping")

    def _update_if_time(self, mesh: Trimesh):
        logger.debug(f"_update_if_time.  _first_mesh is {self._first_mesh}")
        if self._first_mesh:
            self._update_mesh(mesh)
            self._first_mesh = False
            return
        if time() - self._last_mesh_update > self.UPDATE_MESH_INTERVAL_MS / 1000:
            self._update_mesh(mesh)
        else:
            self._latest_unloaded_mesh = mesh

    def _update_mesh(self, mesh: Trimesh | Manifold):
        logger.debug("_update_mesh")
        if isinstance(mesh, Manifold):
            mesh2 = manifold_to_trimesh(mesh)
        elif isinstance(mesh, Trimesh):
            mesh2 = mesh
        self._last_mesh_update = time()
        self._latest_unloaded_mesh = None
        logger.debug("Placing latest mesh in queue for viewing")
        try:
            self.mesh_queue.put_nowait(mesh2)
        except queue.Full:
            _ = self.mesh_queue.get_nowait()
            self.mesh_queue.put_nowait(mesh2)
        if not self._stopped:
            self._mesh_update_callback()
