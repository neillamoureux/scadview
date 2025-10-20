import numpy as np
from pyrr.matrix44 import create_from_axis_rotation
from trimesh import Trimesh
from trimesh.creation import box, cone

from meshsee import Color, set_mesh_color, text, linear_extrude

SIZE = 50
TEXT_FRACTION = 0.8
TEXT_HEIGHT = SIZE / 10
TEXT_SHRINK_FACTOR = 0.15


def create_mesh():
    box_mesh = box(extents=(SIZE, SIZE, SIZE))
    set_mesh_color(box_mesh, Color.GRAY, alpha=0.5)

    x_mesh = text("X", halign="center", size=SIZE)
    y_mesh = text("Y", halign="center", size=SIZE)
    z_mesh = text("Z", halign="center", size=SIZE)
    max_xy_extent = max(
        x_mesh.bounds[0:2].max(), y_mesh.extents[0:2].max(), z_mesh.extents[0:2].max()
    )
    scale_xy = (SIZE / max_xy_extent) * TEXT_FRACTION
    scale = (scale_xy, scale_xy, TEXT_HEIGHT)
    x_mesh.apply_scale(scale)
    y_mesh.apply_scale(scale)
    z_mesh.apply_scale(scale)
    x_mesh = shrink_towards_top(x_mesh, TEXT_SHRINK_FACTOR)
    y_mesh = shrink_towards_top(y_mesh, TEXT_SHRINK_FACTOR)
    z_mesh = shrink_towards_top(z_mesh, TEXT_SHRINK_FACTOR)

    xy_center_mesh(x_mesh)
    x_mesh.apply_transform(
        create_from_axis_rotation((1, 0, 0), np.pi / 2)
    ).apply_transform(
        create_from_axis_rotation((0, 0, 1), np.pi / 2)
    ).apply_translation(
        (SIZE / 2, 0, 0)
    )
    xy_center_mesh(y_mesh)
    y_mesh.apply_transform(
        create_from_axis_rotation((1, 0, 0), np.pi / 2)
    ).apply_translation((0, SIZE / 2, 0)).apply_transform(
        create_from_axis_rotation((0, 1, 0), np.pi)
    )
    xy_center_mesh(z_mesh)
    z_mesh.apply_translation((0, 0, SIZE / 2))
    x_bot_mesh = x_mesh.copy().apply_translation((-SIZE, 0, 0))
    y_bot_mesh = y_mesh.copy().apply_translation((0, -SIZE, 0))
    z_bot_mesh = z_mesh.copy().apply_translation((0, 0, -SIZE))
    # cne = cone(radius=SIZE / 2, height=SIZE, sections=32)
    return (
        box_mesh.union(x_mesh)
        .union(y_mesh)
        .union(z_mesh)
        # .union(cne)
        .difference(x_bot_mesh)
        .difference(y_bot_mesh)
        .difference(z_bot_mesh)
    )


def xy_center_mesh(mesh: Trimesh) -> Trimesh:
    bounds = mesh.bounds
    center = (bounds[0] + bounds[1]) / 2
    mesh.apply_translation([-center[0], -center[1], 0])
    return mesh


def shrink_towards_top(mesh: Trimesh, factor: float) -> Trimesh:
    """Shrink the mesh towards its top face by the given factor (0 to 1)."""
    centroid = mesh.centroid
    vertices = mesh.vertices.copy()
    for i, v in enumerate(vertices):
        # Calculate how far along the Z axis this vertex is (0 at base, 1 at top)
        t = factor * (v[2] - mesh.bounds[0][2]) / TEXT_HEIGHT
        # t = np.clip(t, 0, 1 - factor)
        # t = t / (1 - factor)
        # Linearly interpolate xy towards centroid as t increases
        new_xy = (1 - t) * v[:2] + t * centroid[:2]
        vertices[i][:2] = new_xy
    mesh.vertices = vertices
    return mesh
