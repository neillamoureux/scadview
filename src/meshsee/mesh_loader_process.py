import logging
import queue
from multiprocessing import Queue
from typing import Any, Generator, Generic, TypeVar, Type
from time import time

from manifold3d import Manifold
from trimesh import Trimesh

from meshsee.api.utils import manifold_to_trimesh
from meshsee.module_loader import ModuleLoader

logger = logging.getLogger(__name__)


CREATE_MESH_FUNCTION_NAME = "create_mesh"

T = TypeVar("T")


class MpQueue(Generic[T]):
    """
    Wrapper around queue to ensure only T is in the queue
    """

    def __init__(self, maxsize: int, type_: Type[T]):
        self._queue = Queue(maxsize=maxsize)
        self._type = type_

    def get_nowait(self) -> T:
        item = self._queue.get_nowait()  # type: ignore[reportUnknowVariableType] - can't resolve
        item = self._check_type(item)
        return item

    def put_nowait(self, item: T):
        return self._queue.put_nowait(item)

    def put_none(self, timeout: float | None = None):
        return self._queue.put(None, timeout=timeout)

    def get(self) -> T:
        return self._queue.get()  # type: ignore[reportUnknowVariableType] - can't resolve

    def _check_type(self, item: Any) -> T:
        if isinstance(item, self._type):
            return item
        raise ValueError(f"The item is not of type {self._type}, it is a {type(item)}")


MpMeshQueue = MpQueue[Trimesh | list[Trimesh]]


def load(file_path: str, mesh_queue: MpMeshQueue):
    for mesh in run_mesh_module(file_path):
        if isinstance(mesh, Manifold):
            mesh2 = manifold_to_trimesh(mesh)
        else:
            mesh2 = mesh
        mesh_put = False
        while not mesh_put:  # tends to be race conditions between full and empty
            try:
                mesh_queue.put_nowait(mesh2)
                mesh_put = True
            except queue.Full:
                try:
                    _ = mesh_queue.get_nowait()
                except queue.Empty:
                    pass


def run_mesh_module(module_path: str | None = None) -> Generator[Trimesh, None, None]:
    module_loader = ModuleLoader(CREATE_MESH_FUNCTION_NAME)
    t0 = time()
    for i, mesh in enumerate(module_loader.run_function(module_path)):
        logger.info(f"Loading mesh #{i + 1}")
        yield mesh
    t1 = time()
    logger.info(f"Load {module_path} took {(t1 - t0) * 1000:.1f}ms")
