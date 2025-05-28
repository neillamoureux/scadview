from typing import IO

import numpy as np
from PIL import Image
import trimesh


def surface(file: str, scale: tuple = (1.0, 1.0, 1.0)) -> trimesh.Trimesh:
    """
    Create a 3D mesh on a base at z = 0.0 from a file containing heightmap data.

    Parameters
    ----------
    file : str
        Path to the file containing heightmap data. The file can be a CSV or an image.
    scale : tuple
        A tuple of three values (X, Y, Z) to scale the mesh in the respective dimensions.

    Returns
    -------
    trimesh.Trimesh
        A trimesh object representing the 3D mesh.
    """
    if file.endswith(".csv"):
        # Load heightmap from CSV file
        heightmap = np.loadtxt(file, delimiter=",")
        return solid_from_heightmap(heightmap, scale=scale)
    else:
        # Assume it's an image file
        with open(file, "rb") as img_file:
            return solid_from_image(img_file, scale=scale)


def solid_from_image(
    image_file: IO, scale: tuple = (1.0, 1.0, 1.0), invert: bool = True
) -> trimesh.Trimesh:
    """
    Create a 3D mesh from an image file.

    Parameters
    ----------
    image_file : IO
        A file-like object containing the image data.
    scale : tuple
        A tuple of three values (X, Y, Z) to scale the mesh in the respective dimensions.

    Returns
    -------
    trimesh.Trimesh
        A trimesh object representing the 3D mesh.
    """
    # Open the image file using PIL
    img = Image.open(image_file)
    # Convert to grayscale if not already
    img_gray = img.convert("L")
    # Convert to numpy array and normalize to [0, 1]
    if invert:
        heightmap = (255.0 - np.array(img_gray, dtype=np.float32)) / 255.0
    else:
        heightmap = np.array(img_gray, dtype=np.float32) / 255.0

    # Create a mesh from the heightmap
    return solid_from_heightmap(heightmap, scale=scale)


def solid_from_heightmap(heightmap, scale=(1.0, 1.0, 1.0)):
    y_span, x_span = heightmap.shape
    v_count = y_span * x_span

    verts_top = _create_top_vertices(heightmap, scale)
    verts_bot = _create_bottom_vertices(verts_top)
    faces = _create_faces(y_span, x_span, v_count)
    # invert bottom faces so normals point outward
    faces_bot = faces[:, [0, 2, 1]] + v_count
    side_faces = _create_side_faces(y_span, x_span, v_count)
    return _assemble_solid(verts_top, verts_bot, faces, faces_bot, side_faces)


def _create_top_vertices(heightmap: np.ndarray, scale: tuple) -> np.ndarray:
    y_span, x_span = heightmap.shape
    xs = np.arange(x_span) * scale[0]
    ys = np.arange(y_span) * scale[1]
    xx, yy = np.meshgrid(xs, ys)
    top_z = heightmap * scale[2]
    return np.column_stack([xx.ravel(), yy.ravel(), top_z.ravel()])


def _create_bottom_vertices(verts_top: np.ndarray) -> np.ndarray:
    verts_bot = verts_top.copy()
    verts_bot[:, 2] = 0.0
    return verts_bot


def _create_faces(y_span: int, x_span: int, v_count: int) -> np.ndarray:
    faces = []
    for i in range(y_span - 1):
        for j in range(x_span - 1):
            v0 = i * x_span + j
            v1 = v0 + 1
            v2 = v0 + x_span
            v3 = v2 + 1
            # two triangles per cell
            faces.append([v0, v2, v1])  # top
            faces.append([v1, v2, v3])
    return np.array(faces)


def _create_side_faces(y_span: int, x_span: int, v_count: int) -> list:
    side_faces = []

    # helper to add two tris between a top edge (i→j) and bottom (i+N→j+N)
    def wall(i, j):
        side_faces.append([i, j, j + v_count])
        side_faces.append([i, j + v_count, i + v_count])

    # bottom edge (row=0)
    for j in range(x_span - 1):
        wall(j, j + 1)
    # right edge (col=xspan-1)
    for i in range(y_span - 1):
        idx = i * x_span + (x_span - 1)
        wall(idx, idx + x_span)
    # top edge (row=yspan-1, backwards)
    for j in range(x_span - 1, 0, -1):
        idx = (y_span - 1) * x_span + j
        wall(idx, idx - 1)
    # left edge (col=0, backwards)
    for i in range(y_span - 1, 0, -1):
        idx = i * x_span
        wall(idx, idx - x_span)

    return np.array(side_faces)


def _assemble_solid(
    verts_top: np.ndarray,
    verts_bot: np.ndarray,
    faces: np.ndarray,
    faces_bot: np.ndarray,
    side_faces: np.ndarray,
) -> trimesh.Trimesh:
    """
    Assemble the solid mesh from top vertices, bottom vertices, faces, bottom faces, and side faces.
    """
    verts = np.vstack([verts_top, verts_bot])
    all_faces = np.vstack([faces, faces_bot, side_faces])
    return trimesh.Trimesh(vertices=verts, faces=all_faces)


def mesh_from_heightmap(
    heightmap: np.ndarray, scale: tuple = (1.0, 1.0, 1.0)
) -> trimesh.Trimesh:
    """
    Create a 3D mesh from a heightmap.

    Parameters
    ----------
    heightmap : np.ndarray
        A 2D numpy array representing the heightmap, where each value corresponds to the height at that point.
    scale : tuple
        A tuple of three values (X, Y, Z) to scale the mesh in the respective dimensions.

    Returns
    -------
    trimesh.Trimesh
        A trimesh object representing the 3D mesh.
    """
    H, W = heightmap.shape
    # 1) grid coordinates
    xs = np.arange(W) * scale[0]
    ys = np.arange(H) * scale[1]
    xx, yy = np.meshgrid(xs, ys)

    # 2) vertices: (N,3) array
    verts = np.column_stack([xx.ravel(), yy.ravel(), heightmap.ravel() * scale[2]])

    # 3) faces: two triangles per grid square
    faces = []
    for i in range(H - 1):
        for j in range(W - 1):
            v0 = i * W + j
            v1 = v0 + 1
            v2 = v0 + W
            v3 = v2 + 1
            # triangle 1
            faces.append([v0, v2, v1])
            # triangle 2
            faces.append([v1, v2, v3])
    faces = np.array(faces)

    # 4) build mesh
    return trimesh.Trimesh(vertices=verts, faces=faces)
