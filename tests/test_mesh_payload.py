import pickle
from types import SimpleNamespace

import numpy as np
import pytest
from trimesh import Trimesh
from trimesh.creation import icosphere

import scadview
from scadview.mesh_payload import MeshPayload, mesh_to_payload, payload_to_trimesh


def _source(vertices, faces):
    return SimpleNamespace(
        vertices=vertices,
        faces=faces,
        face_normals=np.empty((len(faces), 3)),
        metadata={},
    )


def test_payload_module_is_not_a_top_level_public_export():
    assert not hasattr(scadview, "MeshPayload")


def test_mesh_to_payload_uses_compact_shapes_dtypes_and_contiguous_arrays(mesh):
    payload = mesh_to_payload(mesh)

    assert payload.vertices.shape == (3, 3)
    assert payload.vertices.dtype == np.float32
    assert payload.faces.shape == (1, 3)
    assert payload.faces.dtype == np.uint32
    assert payload.face_normals.shape == (1, 3)
    assert payload.face_normals.dtype == np.float32
    assert payload.bounds.shape == (2, 3)
    assert payload.bounds.dtype == np.float32
    assert all(array.flags.c_contiguous for array in _payload_arrays(payload))


def test_mesh_to_payload_copies_source_arrays(mesh):
    payload = mesh_to_payload(mesh)

    mesh.vertices[0, 0] = 99
    mesh.faces[0, 0] = 2

    assert payload.vertices[0, 0] == 0
    assert payload.faces[0, 0] == 0


def test_mesh_to_payload_preserves_flat_face_normals(mesh):
    payload = mesh_to_payload(mesh)

    np.testing.assert_allclose(payload.face_normals, [[0, 0, 1]])


def test_mesh_to_payload_rejects_non_finite_face_normals():
    mesh = _source(
        vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]]),
        faces=np.array([[0, 1, 2]]),
    )
    mesh.face_normals[0, 2] = np.nan

    with pytest.raises(ValueError, match="face normals"):
        mesh_to_payload(mesh)


def test_mesh_to_payload_uses_default_color(mesh):
    payload = mesh_to_payload(mesh)

    np.testing.assert_array_equal(payload.color, [128, 128, 128, 255])


def test_mesh_to_payload_converts_explicit_rgba_color(mesh):
    mesh.metadata["scadview"] = {"color": [0.2, 0.4, 0.6, 0.8]}

    payload = mesh_to_payload(mesh)

    np.testing.assert_array_equal(payload.color, [51, 102, 153, 204])


def test_mesh_to_payload_reports_bounds_and_scale(mesh):
    payload = mesh_to_payload(mesh)

    np.testing.assert_array_equal(payload.bounds, [[0, 0, 0], [3, 4, 0]])
    assert payload.scale == 5.0


def test_mesh_to_payload_handles_empty_geometry():
    mesh = Trimesh(
        vertices=np.empty((0, 3)), faces=np.empty((0, 3), dtype=np.int64), process=False
    )

    payload = mesh_to_payload(mesh)

    assert payload.vertices.shape == (0, 3)
    assert payload.faces.shape == (0, 3)
    assert payload.face_normals.shape == (0, 3)
    np.testing.assert_array_equal(payload.bounds, np.zeros((2, 3), dtype=np.float32))
    assert payload.scale == 0.0


def test_payload_to_trimesh_round_trips_geometry_and_color(mesh):
    mesh.metadata["scadview"] = {"color": [0.2, 0.4, 0.6, 0.8]}

    exported = payload_to_trimesh(mesh_to_payload(mesh))

    np.testing.assert_allclose(exported.vertices, mesh.vertices)
    np.testing.assert_array_equal(exported.faces, mesh.faces)
    assert exported.metadata["scadview"]["color"] == [0.2, 0.4, 0.6, 0.8]


@pytest.mark.parametrize(
    ("mesh", "message"),
    [
        (_source(vertices=np.empty((3, 2)), faces=np.empty((0, 3))), "vertices"),
        (_source(vertices=np.empty((3, 3)), faces=np.empty((1, 2))), "faces"),
        (_source(vertices=np.empty((3, 3)), faces=np.array([[-1, 0, 1]])), "negative"),
        (_source(vertices=np.empty((3, 3)), faces=np.array([[0, 1, 3]])), "range"),
        (
            _source(vertices=np.empty((3, 3)), faces=np.array([[0, 1, 2**32]])),
            "uint32",
        ),
    ],
)
def test_mesh_to_payload_rejects_invalid_index_shapes_and_values(mesh, message):
    with pytest.raises(ValueError, match=message):
        mesh_to_payload(mesh)


@pytest.mark.parametrize(
    "vertices",
    [
        np.array([[0.0, 0.0, np.nan], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        np.array([[0.0, 0.0, np.inf], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        np.array([[0.0, 0.0, 1e40], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
    ],
)
def test_mesh_to_payload_rejects_non_finite_or_float32_overflow_vertices(vertices):
    mesh = _source(vertices=vertices, faces=np.array([[0, 1, 2]]))

    with pytest.raises(ValueError, match="vertices"):
        mesh_to_payload(mesh)


def test_compact_payload_pickle_contains_no_trimesh_and_is_smaller():
    mesh = icosphere(subdivisions=4)

    payload = mesh_to_payload(mesh)
    serialized_payload = pickle.dumps(payload)
    serialized_mesh = pickle.dumps(mesh)

    assert isinstance(pickle.loads(serialized_payload), MeshPayload)
    assert all(not isinstance(value, Trimesh) for value in vars(payload).values())
    assert len(serialized_payload) < len(serialized_mesh)


@pytest.fixture
def mesh():
    return Trimesh(
        vertices=np.array([[0, 0, 0], [3, 0, 0], [0, 4, 0]]),
        faces=np.array([[0, 1, 2]]),
        process=False,
    )


def _payload_arrays(payload):
    return payload.vertices, payload.faces, payload.face_normals, payload.bounds
