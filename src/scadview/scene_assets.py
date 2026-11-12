from dataclasses import dataclass

from trimesh import Trimesh
from trimesh.creation import box

from scadview.mesh_payload import MeshPayload, mesh_to_payload
from scadview.resources.xyz_cube import create_mesh

AXIS_LENGTH = 10000.0
AXIS_WIDTH = 1.0
AXIS_DEPTH = 1.0


@dataclass(frozen=True)
class SceneAssets:
    startup_mesh: MeshPayload
    loading_mesh: MeshPayload
    base_axes: MeshPayload


def create_scene_assets() -> SceneAssets:
    return SceneAssets(
        startup_mesh=mesh_to_payload(create_startup_source_mesh()),
        loading_mesh=mesh_to_payload(create_loading_source_mesh()),
        base_axes=mesh_to_payload(create_base_axes_source_mesh()),
    )


def create_startup_source_mesh() -> Trimesh:
    return create_mesh()


def create_loading_source_mesh() -> Trimesh:
    return box([1.0, 1.0, 1.0])


def create_base_axes_source_mesh() -> Trimesh:
    return (
        box([AXIS_LENGTH, AXIS_DEPTH, AXIS_WIDTH])
        .union(box([AXIS_LENGTH, AXIS_WIDTH, AXIS_DEPTH]))
        .union(box([AXIS_WIDTH, AXIS_LENGTH, AXIS_DEPTH]))
        .union(box([AXIS_DEPTH, AXIS_LENGTH, AXIS_WIDTH]))
        .union(box([AXIS_DEPTH, AXIS_WIDTH, AXIS_LENGTH]))
        .union(box([AXIS_WIDTH, AXIS_DEPTH, AXIS_LENGTH]))
    )
