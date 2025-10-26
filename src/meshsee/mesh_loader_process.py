import queue
from multiprocessing import Queue
from typing import Any

from manifold3d import Manifold
from trimesh import Trimesh

from meshsee.api.utils import manifold_to_trimesh
from meshsee.controller import Controller


class MpMeshQueue:
    """
    Wrapper around queue to ensure only Trimesh is in the queue
    """

    def __init__(self):
        self._queue = Queue(maxsize=1)

    def get_nowait(self) -> Trimesh | list[Trimesh]:
        mesh = self._queue.get_nowait()  # type: ignore[reportUnknowVariableType] - can't resolve
        mesh = self._check_mesh_type(mesh)
        return mesh

    def put_nowait(self, mesh: Trimesh):
        return self._queue.put_nowait(mesh)

    def put_none(self, timeout: float | None = None):
        return self._queue.put(None, timeout=timeout)

    def empty(self) -> bool:
        return self._queue.empty()

    def get(self) -> Trimesh:
        return self._queue.get()  # type: ignore[reportUnknowVariableType] - can't resolve

    def _check_mesh_type(self, mesh: Any) -> Trimesh | list[Trimesh]:
        if isinstance(mesh, Trimesh):
            return mesh
        if isinstance(mesh, list):
            if len(mesh) > 0:  # type: ignore[reportUnknownArgumentType] - can't resolve
                if all([isinstance(mesh_item, Trimesh) for mesh_item in mesh]):  # type: ignore[reportUnknownVariableType] - can't resolve
                    return mesh  # type: ignore[reportUnknownVariableType] - can't resolve
            else:
                raise ValueError("The mesh is an empty list")
        raise ValueError(
            f"The mesh is not a Trimesh or a list of Trimesh, it is a {type(mesh)}"  # type: ignore[reportUnknownArgumentType] - can't resolve
        )


def load(file_path: str, mesh_queue: MpMeshQueue):
    for mesh in Controller().load_mesh(file_path):
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

    # mesh_queue.put_none()  # Sentinel to indicate end of loading
