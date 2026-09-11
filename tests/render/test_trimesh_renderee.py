from unittest import mock

import numpy as np
from trimesh.creation import box

from scadview.mesh_payload import mesh_to_payload
from scadview.render.mesh_renderee import (
    MeshNullRenderee,
    OpaqueMeshRenderee,
    create_colors_array,
    create_edge_detect_array,
    create_mesh_renderee,
    is_alpha,
    sort_triangles,
)


def test_create_colors_array_repeats_mesh_color_per_corner():
    color = np.array([26, 51, 76, 255], dtype=np.uint8)
    result = create_colors_array(color, 5)
    assert result.shape == (5, 3, 4)
    np.testing.assert_array_equal(result, np.broadcast_to(color, result.shape))


def test_edge_markers_preserve_one_hot_corner_semantics():
    result = create_edge_detect_array(2)
    assert result.shape == (2, 9)
    np.testing.assert_array_equal(result[0], [255, 0, 0, 0, 255, 0, 0, 0, 255])


def test_payload_color_controls_alpha_classification():
    mesh = box()
    mesh.metadata["scadview"] = {"color": [0.2, 0.3, 0.4, 0.5]}
    assert is_alpha(mesh_to_payload(mesh))
    assert not is_alpha(mesh_to_payload(box()))


def test_opaque_renderee_keeps_gl_upload_lazy():
    ctx = mock.MagicMock()
    renderee = OpaqueMeshRenderee(ctx, mock.MagicMock(), mesh_to_payload(box()))
    assert renderee._vao is None
    renderee.render()
    assert renderee._vao is not None


def test_transparent_list_uses_one_global_sortable_renderee():
    first = box()
    first.metadata["scadview"] = {"color": [1.0, 0.0, 0.0, 0.5]}
    second = box()
    second.metadata["scadview"] = {"color": [0.0, 1.0, 0.0, 0.5]}
    ctx = mock.MagicMock()
    renderee = create_mesh_renderee(
        ctx,
        mock.MagicMock(),
        [mesh_to_payload(first), mesh_to_payload(second)],
        np.eye(4, dtype="f4"),
        np.eye(4, dtype="f4"),
    )
    renderee.render()
    assert ctx.buffer.call_count == 4


def test_empty_mesh_list_has_framing_points_without_gl_buffers():
    renderee = create_mesh_renderee(
        mock.MagicMock(),
        mock.MagicMock(),
        [],
        np.eye(4, dtype="f4"),
        np.eye(4, dtype="f4"),
    )
    assert isinstance(renderee._opaques_renderee, MeshNullRenderee)
    assert renderee.points.shape == (2, 3)


def test_transparent_sort_orders_triangle_depths():
    mesh = mesh_to_payload(box())
    triangles = mesh.vertices[mesh.faces]
    result = sort_triangles(triangles, np.eye(4, dtype="f4"), np.eye(4, dtype="f4"))
    assert result.shape == (len(mesh.faces),)
