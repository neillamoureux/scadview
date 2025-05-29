import numpy as np
import pytest
from meshsee.surface import surface, mesh_from_heightmap
import trimesh
from PIL import Image


@pytest.fixture
def heightmap():
    # Note: avoid 0 z-values since the bottom vertices all have a 0 z-value
    # and this could duplicate a vertex, which mayu be removed by trimesh
    # and make it hard to validate vertex counts.
    # Also avoid z < 0 since this could cause the top of the mesh
    # to go through the bottom of the mesh.
    return np.arange(20, dtype=float).reshape((5, 4)) + 1


def check_mesh(mesh, heightmap, invert: str):
    __tracebackhide__ = True
    if invert == "image":
        heightmap = 1.0 - heightmap
    elif invert == "text":
        heightmap = heightmap.max() - heightmap + heightmap.min()
    elif invert != "none":
        raise ValueError(f"Invalid invert value: {invert}")
    assert isinstance(mesh, trimesh.Trimesh)
    check_vertex_count(mesh, heightmap)
    check_face_count(mesh, heightmap)
    expected_heights = heightmap.flatten()
    check_mesh_heights(mesh, expected_heights)
    check_mesh_heights(
        mesh, np.zeros(heightmap.size, dtype=float), offset=heightmap.size
    )
    assert mesh.is_watertight, "Mesh is not watertight"


def check_vertex_count(mesh, heightmap):
    __tracebackhide__ = True
    # Check if the mesh has the expected number of vertices
    expected_vertices = (
        heightmap.size * 2
    )  # 2 vertices per heightmap value (top and bottom)
    assert mesh.vertices.shape[0] == expected_vertices


def check_face_count(mesh, heightmap):
    __tracebackhide__ = True
    # Check if the mesh has the expected number of faces
    expected_faces = (heightmap.shape[0] - 1) * (heightmap.shape[1] - 1) * 4 + (
        heightmap.shape[0] + heightmap.shape[1] - 2
    ) * 4
    assert mesh.faces.shape[0] == expected_faces


def check_mesh_heights(mesh, expected_heights, offset=0):
    __tracebackhide__ = True
    # Check if the mesh vertices have the expected heights
    for i, height in enumerate(expected_heights):
        assert np.isclose(
            mesh.vertices[i + offset, 2], height
        ), f"Vertex {i} height mismatch"


@pytest.mark.parametrize(
    "extension, delimiter, invert",
    [
        ("csv", ",", "none"),
        ("tsv", "\t", "none"),
        ("txt", " ", "none"),
        ("dat", " ", "none"),
        ("csv", ",", "text"),
        ("tsv", "\t", "text"),
        ("txt", " ", "text"),
        ("dat", " ", "text"),
    ],
)
def test_surface_with_text_files(tmp_path, heightmap, extension, delimiter, invert):
    csv_path = tmp_path / f"heightmap.{extension}"
    np.savetxt(csv_path, heightmap, delimiter=delimiter)
    mesh = surface(str(csv_path), invert=(invert == "text"))
    check_mesh(mesh, heightmap, invert=invert)


@pytest.mark.parametrize("invert", [False, True])
def test_surface_with_image(tmp_path, heightmap, invert):
    # Create a simple grayscale image
    img = Image.fromarray(heightmap.astype(np.uint8), mode="L")
    img_path = tmp_path / "heightmap.png"
    img.save(img_path)
    mesh = surface(str(img_path), invert=invert)
    check_mesh(mesh, heightmap / 255.0, invert="image" if invert else "none")
    # assert isinstance(mesh, trimesh.Trimesh)


def test_surface_scale_argument(tmp_path, heightmap):
    # heightmap = np.array([[1, 2], [3, 4]], dtype=float)
    csv_path = tmp_path / "heightmap.csv"
    np.savetxt(csv_path, heightmap, delimiter=",")
    scale = (2.0, 3.0, 4.0)
    mesh = surface(str(csv_path), scale=scale)
    assert np.allclose(mesh.vertices[:, 0] % 2.0, 0)  # x scaled by 2
    assert np.allclose(mesh.vertices[:, 1] % 3.0, 0)  # y scaled by 3


def test_surface_invalid_file(tmp_path):
    # Should raise an error if file does not exist
    with pytest.raises(FileNotFoundError):
        surface(str(tmp_path / "does_not_exist.xyz"))


def test_mesh_from_heightmap_shape_and_faces(heightmap):
    # heightmap = np.array([[0, 1, 2], [3, 4, 5]], dtype=float)
    mesh = mesh_from_heightmap(heightmap)
    expected_vertices = heightmap.size
    assert mesh.vertices.shape == (expected_vertices, 3)
    expected_faces = (heightmap.shape[0] - 1) * (heightmap.shape[1] - 1) * 2
    assert mesh.faces.shape == (expected_faces, 3)
    check_mesh_heights(mesh, heightmap.flatten())
