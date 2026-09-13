from pathlib import Path
from unittest import mock

import numpy as np
from trimesh.creation import box

from scadview.mesh_payload import mesh_to_payload
from scadview.render.mesh_renderee import (
    OpaqueMeshRenderee,
    create_mesh_renderee,
    expand_payload,
)


def test_expand_payload_uses_indexed_vertices_and_flat_normals():
    payload = mesh_to_payload(box())

    triangles, normals, colors, edges = expand_payload(payload)

    assert triangles.shape == (len(payload.faces), 3, 3)
    assert normals.shape == triangles.shape
    assert colors.shape == (len(payload.faces), 3, 4)
    assert edges.shape == (len(payload.faces), 9)
    np.testing.assert_array_equal(normals[:, 0], payload.face_normals)
    np.testing.assert_array_equal(triangles[0], payload.vertices[payload.faces[0]])


def test_opaque_payload_upload_is_lazy():
    payload = mesh_to_payload(box())
    ctx = mock.MagicMock()
    renderee = OpaqueMeshRenderee(ctx, mock.MagicMock(), payload)

    assert renderee._vao is None
    renderee.render()
    assert renderee._vao is not None


def test_transparent_payloads_sort_globally_and_retain_colors():
    first = mesh_to_payload(box())
    second_mesh = box()
    second_mesh.metadata["scadview"] = {"color": [0.0, 1.0, 0.0, 0.5]}
    second = mesh_to_payload(second_mesh)
    ctx = mock.MagicMock()
    renderee = create_mesh_renderee(
        ctx,
        mock.MagicMock(),
        [first, second],
        np.eye(4, dtype="f4"),
        np.eye(4, dtype="f4"),
    )

    renderee.render()

    assert ctx.buffer.call_count == 8
    assert renderee.points.shape == (16, 3)


def test_empty_payload_list_has_safe_framing_points():
    renderee = create_mesh_renderee(
        mock.MagicMock(),
        mock.MagicMock(),
        [],
        np.eye(4, dtype="f4"),
        np.eye(4, dtype="f4"),
    )

    assert renderee.points.shape == (2, 3)


def test_render_package_has_no_trimesh_dependency_or_reconstruction():
    render_root = Path(__file__).parents[2] / "src" / "scadview" / "render"

    source = "\n".join(path.read_text() for path in render_root.glob("*.py"))

    assert "Trimesh" not in source
    assert "payload_to_trimesh" not in source
