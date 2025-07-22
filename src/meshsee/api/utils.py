import numpy as np
import trimesh


def manifold_to_trimesh(manifold):
    """
    Convert a manifold object to a Trimesh object.
    From [Manifold](https://colab.research.google.com/drive/1VxrFYHPSHZgUbl9TeWzCeovlpXrPQ5J5?usp=sharing#scrollTo=xCHqkWeJXgmJ)

    Args:
        manifold: A manifold object with vertex properties and triangle vertices.

    Returns:
        trimesh.Trimesh: A Trimesh object representing the manifold.
    """
    mesh = manifold.to_mesh()

    if mesh.vert_properties.shape[1] > 3:
        vertices = mesh.vert_properties[:, :3]
        colors = (mesh.vert_properties[:, 3:] * 255).astype(np.uint8)
    else:
        vertices = mesh.vert_properties
        colors = None

    return trimesh.Trimesh(
        vertices=vertices, faces=mesh.tri_verts, vertex_colors=colors
    )
