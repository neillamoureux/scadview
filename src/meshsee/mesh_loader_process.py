import logging
import queue
from threading import Thread
from multiprocessing import Queue
from time import time, sleep
from typing import Any, Generator, Generic, Type, TypeVar, Callable, Protocol

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
        return self.get(False)

    def put_nowait(self, item: T):
        return self._queue.put(item, False)

    def put(self, item: T, block: bool = True, timeout: float | None = None):
        item = self._check_type(item)
        return self._queue.put(item, block=block, timeout=timeout)

    # def put_none(self, timeout: float | None = None):
    #     return self._queue.put(None, timeout=timeout)

    def get(self, block: bool = True, timeout: float | None = None) -> T:
        item = self._queue.get(block=block, timeout=timeout)  # type: ignore[reportUnknowVariableType] - can't resolve
        return self._check_type(item)

    def _check_type(self, item: Any) -> T:
        if isinstance(item, self._type):
            return item
        raise ValueError(f"The item is not of type {self._type}, it is a {type(item)}")

    def close(self):
        self._queue.close()


class Command:
    pass


class LoadMeshCommand(Command):
    def __init__(self, module_path: str):
        self.module_path = module_path


class CancelLoadCommand(Command):
    pass


class ShutDownCommand(Command):
    pass


MeshType = Trimesh | list[Trimesh]
MpMeshQueue = MpQueue[MeshType]
MpCommandQueue = MpQueue[Command]


class LoadWorker(Thread):
    def __init__(self, module_path: str, mesh_queue: MpMeshQueue):
        super().__init__()
        self.module_path = module_path
        self.mesh_queue = mesh_queue
        self.cancelled = False

    def run(self):
        self.load()

    def load(self):
        for mesh in run_mesh_module(self.module_path):
            if self.cancelled:
                logger.info("LoadWorker cancelled, stopping load")
                return
            if isinstance(mesh, Manifold):
                mesh2 = manifold_to_trimesh(mesh)
            else:
                mesh2 = mesh
            mesh_put = False
            while not mesh_put:  # tends to be race conditions between full and empty
                if self.cancelled:
                    logger.info("LoadWorker cancelled, stopping load")
                    return
                try:
                    self.mesh_queue.put_nowait(mesh2)
                    mesh_put = True
                except queue.Full:
                    try:
                        _ = self.mesh_queue.get_nowait()
                    except queue.Empty:
                        pass

    def cancel(self):
        self.cancelled = True


def run_loader(command_queue: MpCommandQueue, mesh_queue: MpMeshQueue):
    worker = None
    while True:
        sleep(0.1)
        try:
            command = command_queue.get_nowait()
        except queue.Empty:
            continue
        if isinstance(command, LoadMeshCommand):
            if worker is not None and worker.is_alive():
                logger.info("Previous load still in progress, cancelling it")
                worker.cancel()
                worker.join()
            logger.info(f"Loading mesh from {command.module_path}")
            worker = LoadWorker(command.module_path, mesh_queue)
            worker.start()
        elif isinstance(command, CancelLoadCommand):
            logger.info("Load cancelled")
            if worker is not None and worker.is_alive():
                logger.info("Previous load still in progress, cancelling it")
                worker.cancel()
                worker.join()
                worker = None
            continue
        elif isinstance(command, ShutDownCommand):
            logger.info("Shutting down loader process")
            if worker is not None and worker.is_alive():
                logger.info("Previous load still in progress, cancelling it")
                worker.cancel()
                worker.join()
                command_queue.close()
                mesh_queue.close()
            return
        else:
            logger.warning(f"Unknown command received: {command}")


def run_mesh_module(module_path: str | None = None) -> Generator[Trimesh, None, None]:
    module_loader = ModuleLoader(CREATE_MESH_FUNCTION_NAME)
    t0 = time()
    for i, mesh in enumerate(module_loader.run_function(module_path)):
        logger.info(f"Loading mesh #{i + 1}")
        yield mesh
    t1 = time()
    logger.info(f"Load {module_path} took {(t1 - t0) * 1000:.1f}ms")
