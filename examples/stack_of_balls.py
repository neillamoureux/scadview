from math import pi

from trimesh import Trimesh
from trimesh.creation import icosphere
from trimesh.transformations import rotation_matrix

from scadview import text


def create_mesh(
    levels: int = 3,
    ball_radius: float = 1.0,
    level_height: float = 2.0,
    label: str = "Stack",
    show_label: bool = True,
) -> Trimesh:
    """Create a centered square pyramid of balls and an optional label."""
    if levels < 1:
        raise ValueError("levels must be at least 1")
    if ball_radius <= 0:
        raise ValueError("ball_radius must be positive")
    if level_height <= 0:
        raise ValueError("level_height must be positive")

    meshes: list[Trimesh] = []
    for layer in range(levels):
        offset = layer / 2
        z = -layer * level_height
        for row in range(layer + 1):
            for column in range(layer + 1):
                center = (2.0 * (column - offset), 2.0 * (row - offset), z)
                meshes.append(
                    icosphere(radius=ball_radius, subdivisions=1).apply_translation(
                        center
                    )
                )

    if show_label and label:
        label_mesh = text(label, size=1.0, halign="center", valign="center")
        label_mesh.apply_scale((1.0, 1.0, 0.2))
        label_mesh.apply_transform(rotation_matrix(2 * pi / 3, (1.0, 1.0, 1.0)))
        label_mesh.apply_translation(
            [0.0, 0.0, ball_radius + 0.25 - label_mesh.bounds[0][2]]
        )
        meshes.append(label_mesh)

    unioned = meshes[0]
    for mesh in meshes[1:]:
        unioned = unioned.union(mesh)
    return unioned
