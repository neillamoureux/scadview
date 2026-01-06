import os

import numpy as np
from trimesh import Trimesh, transformations

from scadview import surface


def create_mesh():
    pixel_size = (388, 400)
    desired_x_size = 200.0
    height = 20.0
    scale = desired_x_size / pixel_size[0]
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    mesh = surface(
        os.path.join(parent_dir, "../src/scadview/resources/splash.png"),
        scale=(scale, scale, height),
        invert=True,
        base=0.0,
    )
    # return mesh
    curve = 2 * np.pi  # / 6.0
    curved_verts = bend_x(mesh.vertices, arc_radians=curve)
    curved_mesh = Trimesh(vertices=curved_verts, faces=mesh.faces)
    # rotate about the y axis so curved mesh edges lie on the xy plane (90 degrees - curve in degreees / 2.0)
    rot = transformations.rotation_matrix(
        angle=np.pi / 2.0 - curve / 2.0,
        direction=[0, 1, 0],
        point=(0, 0, 0),
    )
    curved_mesh.apply_transform(rot)
    return curved_mesh


def bend_x(vertices: np.ndarray, arc_radians: float = np.pi / 2.0) -> np.ndarray:
    """
    Bend the mesh along the x-axis.

    The x coords are mapped to an arc in the xz plane with the given inner radius.
    The arc starts at the minimum x value, and its length is equal to the range of x values in the mesh.
    rad_x = arc_radians * (x - min(x)) / (max(x) - min(x))
    inner_radius is computed so that inner_radius * arc_radians is the length of the arc.
    So inner_radius = (max(x) - min(x)) / arc_radians.
    x = (inner_radius  + z) * np.cos(rad_x) + (max(x) - min(x)) / 2
    z = (inner_radius + z) * np.sin(rad_x)
    y is unchanged.
    """
    x, y, z = vertices.T
    print(np.shape(vertices), np.shape(x), np.shape(y), np.shape(z))
    x_min = np.min(x)
    x_max = np.max(x)
    x_span = x_max - x_min
    print(f"x_min: {x_min}, x_max: {x_max}, x_span: {x_span}")
    inner_radius = x_span / arc_radians
    rad_x = arc_radians * (x - x_min) / x_span
    x_new = -(inner_radius + z) * np.cos(rad_x) + inner_radius
    z_new = (inner_radius + z) * np.sin(rad_x)
    print(f"x_new: {np.shape(x_new)}, z_new: {np.shape(z_new)}")
    return np.stack((x_new, y, z_new), axis=-1)


def recompute_trimesh(mesh):
    mesh._cache.clear()
    mesh.fix_normals()


if __name__ == "__main__":
    mesh = create_mesh()
