from typing import IO

import numpy as np
import trimesh
from numpy.typing import NDArray
from PIL import Image


def surface(
    file: str, scale: tuple = (1.0, 1.0, 1.0), base: float = 0.0, invert: bool = False
) -> trimesh.Trimesh:
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
    delimiter = None
    if file.endswith(".csv"):
        delimiter = ","
    elif file.endswith(".tsv"):
        delimiter = "\t"
    elif file.endswith(".txt") or format(file).endswith(".dat"):
        delimiter = " "
    if delimiter is not None:
        # Load heightmap from text file
        heightmap = np.loadtxt(file, delimiter=delimiter)
        return _solid_from_heightmap(heightmap, scale=scale, base=base, invert=invert)
    else:
        # Assume it's an image file
        with open(file, "rb") as img_file:
            return _solid_from_image(img_file, scale=scale, base=base, invert=invert)


def _solid_from_image(
    image_file: IO,
    scale: tuple = (1.0, 1.0, 1.0),
    base: float = 0.0,
    invert: bool = False,
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
    # Note: values already inverted if invert=True
    heightmap = np.flipud(heightmap)  # preserve image orientation
    return _solid_from_heightmap(heightmap, scale=scale, base=base)


def _solid_from_heightmap(
    heightmap, scale=(1.0, 1.0, 1.0), base: float = 0.0, invert: bool = False
) -> trimesh.Trimesh:
    y_span, x_span = heightmap.shape
    v_count = y_span * x_span

    verts_top = _create_top_vertices(heightmap, scale, base=base, invert=invert)
    verts_bot = _create_bottom_vertices(verts_top)
    faces = _create_faces(y_span, x_span)
    # invert bottom faces so normals point outward
    faces_bot = faces[:, [0, 2, 1]] + v_count
    side_faces = _create_side_faces(y_span, x_span, v_count)
    return _assemble_solid(verts_top, verts_bot, faces, faces_bot, side_faces)


def _create_top_vertices(
    heightmap: NDArray[np.float32],
    scale: tuple,
    base: float = 0.0,
    invert: bool = False,
) -> NDArray[np.float32]:
    y_span, x_span = heightmap.shape
    xs = np.arange(x_span) * scale[0]
    ys = np.arange(y_span) * scale[1]
    xx, yy = np.meshgrid(xs, ys)
    if invert:
        heightmap = heightmap.max() - heightmap + heightmap.min()
    top_z = heightmap * scale[2] + base
    return np.column_stack([xx.ravel(), yy.ravel(), top_z.ravel()])


def _create_bottom_vertices(verts_top: NDArray[np.float32]) -> NDArray[np.float32]:
    verts_bot = verts_top.copy()
    verts_bot[:, 2] = 0.0
    return verts_bot


def _create_faces(y_span: int, x_span: int) -> NDArray[np.float32]:
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


def _create_side_faces(y_span: int, x_span: int, v_count: int) -> NDArray[np.float32]:
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

    return np.array(side_faces, dtype="f4")


def _assemble_solid(
    verts_top: NDArray[np.float32],
    verts_bot: NDArray[np.float32],
    faces: NDArray[np.float32],
    faces_bot: NDArray[np.float32],
    side_faces: NDArray[np.float32],
) -> trimesh.Trimesh:
    """
    Assemble the solid mesh from top vertices, bottom vertices, faces, bottom faces, and side faces.
    """
    verts = np.vstack([verts_top, verts_bot])
    all_faces = np.vstack([faces, faces_bot, side_faces])
    return trimesh.Trimesh(vertices=verts, faces=all_faces)


def mesh_from_heightmap(
    heightmap: NDArray[np.float32], scale: tuple = (1.0, 1.0, 1.0)
) -> trimesh.Trimesh:
    """
    Create a 3D mesh from a heightmap.

    Parameters
    ----------
    heightmap : NDArray[np.float32]
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
