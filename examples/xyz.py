from meshsee import text, set_mesh_color, Color
from trimesh.creation import box
from trimesh.transformations import rotation_matrix
import numpy as np

LETTER_DEPTH = 10
FRAME = 2


def create_mesh():
    x = center_mesh(
        create_letter("X", LETTER_DEPTH).apply_transform(
            rotation_matrix(np.pi / 2, (1, 0, 0))
            @ rotation_matrix(np.pi / 2, (0, 1, 0))
        )
    )
    y = center_mesh(
        create_letter("Y", LETTER_DEPTH).apply_transform(
            rotation_matrix(np.pi / 2, (1, 0, 0))
        )
    )
    z = center_mesh(create_letter("Z", LETTER_DEPTH))
    frame_dims = np.max(
        [
            x.extents + np.array((0, 1, 1)) * FRAME,
            y.extents + np.array((1, 0, 1)) * FRAME,
            z.extents + np.array((1, 1, 0)) * FRAME,
        ],
        axis=1,
    )
    x.apply_scale((1.1 * frame_dims[0] / LETTER_DEPTH, 1, 1))
    y.apply_scale((1, 1.1 * frame_dims[1] / LETTER_DEPTH, 1))
    z.apply_scale((1, 1, 1.1 * frame_dims[2] / LETTER_DEPTH))

    frame = box(frame_dims)
    return set_mesh_color(
        frame.difference(y).difference(x).difference(z), Color.SILVER, 0.7
    )


def create_letter(letter: str, depth: float):
    return text(letter).apply_scale((1.0, 1.0, depth))


def center_mesh(mesh):
    center = (mesh.bounds[0] + mesh.bounds[1]) / 2
    return mesh.apply_translation(-center)
