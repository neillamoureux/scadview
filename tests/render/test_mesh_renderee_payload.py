from pathlib import Path
from unittest import mock

import numpy as np
import pytest
from trimesh.creation import box

from scadview.mesh_payload import MeshPayload, mesh_to_payload
from scadview.observable import Observable
from scadview.render import mesh_renderee
from scadview.render.camera import CameraPerspective
from scadview.render.mesh_renderee import (
    MeshListAlphaRenderee,
    OpaqueMeshRenderee,
    create_mesh_renderee,
    expand_payload,
    expand_payloads_without_edges,
    payload_corners,
)
from scadview.render.shader_program import ShaderVar


def test_expand_payload_uses_indexed_vertices_and_flat_normals():
    payload = mesh_to_payload(box())

    triangles, normals, colors, edges = expand_payload(payload)

    assert triangles.shape == (len(payload.faces), 3, 3)
    assert normals.shape == triangles.shape
    assert colors.shape == (len(payload.faces), 3, 4)
    assert edges.shape == (len(payload.faces), 9)
    np.testing.assert_array_equal(normals[:, 0], payload.face_normals)
    np.testing.assert_array_equal(triangles[0], payload.vertices[payload.faces[0]])


def test_edge_free_payload_aggregation_preserves_order_normals_and_colors():
    first = _payload(
        vertices=[[0, 0, 3], [1, 0, 3], [0, 1, 3], [1, 1, 3]],
        faces=[[0, 1, 2], [1, 3, 2]],
        normals=[[1, 2, 3], [4, 5, 6]],
        color=[10, 20, 30, 40],
    )
    empty = _payload(
        vertices=[],
        faces=[],
        normals=[],
        color=[50, 60, 70, 80],
    )
    second = _payload(
        vertices=[[10, 0, -2], [11, 0, -2], [10, 1, -2]],
        faces=[[0, 1, 2]],
        normals=[[7, 8, 9]],
        color=[90, 100, 110, 120],
    )

    triangles, normals, colors = expand_payloads_without_edges([first, empty, second])

    np.testing.assert_array_equal(
        triangles,
        np.array(
            [
                [[0, 0, 3], [1, 0, 3], [0, 1, 3]],
                [[1, 0, 3], [1, 1, 3], [0, 1, 3]],
                [[10, 0, -2], [11, 0, -2], [10, 1, -2]],
            ],
            dtype=np.float32,
        ),
    )
    np.testing.assert_array_equal(
        normals,
        np.array(
            [
                [[1, 2, 3]] * 3,
                [[4, 5, 6]] * 3,
                [[7, 8, 9]] * 3,
            ],
            dtype=np.float32,
        ),
    )
    np.testing.assert_array_equal(
        colors,
        np.array(
            [
                [[10, 20, 30, 40]] * 3,
                [[10, 20, 30, 40]] * 3,
                [[90, 100, 110, 120]] * 3,
            ],
            dtype=np.uint8,
        ),
    )
    assert triangles.dtype == np.float32
    assert normals.dtype == np.float32
    assert colors.dtype == np.uint8
    assert triangles.flags.c_contiguous
    assert normals.flags.c_contiguous
    assert colors.flags.c_contiguous


def test_edge_free_payload_aggregation_handles_no_faces():
    payload = _payload(
        vertices=[],
        faces=[],
        normals=[],
        color=None,
    )

    triangles, normals, colors = expand_payloads_without_edges([payload])

    assert triangles.shape == (0, 3, 3)
    assert normals.shape == (0, 3, 3)
    assert colors.shape == (0, 3, 4)
    assert triangles.dtype == np.float32
    assert normals.dtype == np.float32
    assert colors.dtype == np.uint8
    assert triangles.flags.c_contiguous
    assert normals.flags.c_contiguous
    assert colors.flags.c_contiguous


def test_edge_free_payload_aggregation_allocates_each_final_array_once():
    first = mesh_to_payload(box())
    second = mesh_to_payload(box())
    total_faces = len(first.faces) + len(second.faces)

    with mock.patch.object(mesh_renderee.np, "empty", wraps=np.empty) as allocate_array:
        expand_payloads_without_edges([first, second])

    assert allocate_array.call_args_list == [
        mock.call((total_faces, 3, 3), dtype=np.float32),
        mock.call((total_faces, 3, 3), dtype=np.float32),
        mock.call((total_faces, 3, 4), dtype=np.uint8),
    ]


def test_transparent_list_aggregates_without_per_mesh_edges_or_expansions():
    first = _payload(
        vertices=[[0, 0, 2], [1, 0, 2], [0, 1, 2], [1, 1, 2]],
        faces=[[0, 1, 2], [1, 3, 2]],
        normals=[[1, 0, 0], [0, 1, 0]],
        color=[255, 0, 0, 128],
    )
    empty = _payload(
        vertices=[],
        faces=[],
        normals=[],
        color=[0, 0, 255, 128],
    )
    second = _payload(
        vertices=[[0, 0, -2], [1, 0, -2], [0, 1, -2]],
        faces=[[0, 1, 2]],
        normals=[[0, 0, 1]],
        color=[0, 255, 0, 64],
    )
    ctx = mock.MagicMock()

    with (
        mock.patch.object(
            mesh_renderee,
            "expand_payload",
            side_effect=AssertionError("transparent preparation expanded a mesh"),
        ),
        mock.patch.object(
            mesh_renderee,
            "create_edge_detect_array",
            wraps=mesh_renderee.create_edge_detect_array,
        ) as create_edges,
        mock.patch.object(
            mesh_renderee,
            "create_vao_from_arrays",
            wraps=mesh_renderee.create_vao_from_arrays,
        ) as create_vao,
    ):
        renderee = MeshListAlphaRenderee(
            ctx,
            mock.MagicMock(),
            [first, empty, second],
            np.eye(4, dtype="f4"),
            np.eye(4, dtype="f4"),
        )
        updates = Observable()
        renderee.subscribe_to_updates(updates)
        create_edges.assert_not_called()

        renderee.render()
        updates.notify(
            ShaderVar.VIEW_MATRIX,
            np.diag([1, 1, -1, 1]).astype(np.float32),
        )
        renderee.render()

    assert create_edges.call_args_list == [mock.call(3), mock.call(3)]
    assert create_vao.call_count == 2
    triangles, normals, colors, edges = create_vao.call_args_list[0].args[2:]
    np.testing.assert_array_equal(triangles[:, :, 2], [[-2] * 3, [2] * 3, [2] * 3])
    np.testing.assert_array_equal(colors[0, 0], [0, 255, 0, 64])
    np.testing.assert_array_equal(colors[1:, 0], [[255, 0, 0, 128]] * 2)
    np.testing.assert_array_equal(normals[0, 0], [0, 0, 1])
    assert edges.shape == (3, 9)
    resorted_colors = create_vao.call_args_list[1].args[4]
    np.testing.assert_array_equal(resorted_colors[:2, 0], [[255, 0, 0, 128]] * 2)
    np.testing.assert_array_equal(resorted_colors[2, 0], [0, 255, 0, 64])


def test_transparent_single_payload_avoids_discarded_edge_allocation():
    mesh = box()
    mesh.metadata["scadview"] = {"color": [0.2, 0.3, 0.4, 0.5]}
    payload = mesh_to_payload(mesh)

    with (
        mock.patch.object(
            mesh_renderee,
            "expand_payload",
            side_effect=AssertionError("transparent preparation expanded a mesh"),
        ),
        mock.patch.object(
            mesh_renderee,
            "create_edge_detect_array",
            wraps=mesh_renderee.create_edge_detect_array,
        ) as create_edges,
    ):
        renderee = create_mesh_renderee(
            mock.MagicMock(),
            mock.MagicMock(),
            payload,
            np.eye(4, dtype="f4"),
            np.eye(4, dtype="f4"),
        )
        create_edges.assert_not_called()
        renderee.render()

    create_edges.assert_called_once_with(len(payload.faces))


def test_transparent_list_with_only_zero_face_payload_builds_empty_buffers():
    payload = _payload(
        vertices=[],
        faces=[],
        normals=[],
        color=[10, 20, 30, 128],
    )

    with mock.patch.object(mesh_renderee, "create_vao_from_arrays") as create_vao:
        renderee = MeshListAlphaRenderee(
            mock.MagicMock(),
            mock.MagicMock(),
            [payload],
            np.eye(4, dtype="f4"),
            np.eye(4, dtype="f4"),
        )
        renderee.render()

    triangles, normals, colors, edges = create_vao.call_args.args[2:]
    assert triangles.shape == (0, 3, 3)
    assert normals.shape == (0, 3, 3)
    assert colors.shape == (0, 3, 4)
    assert edges.shape == (0, 9)
    assert renderee.points.shape == (8, 3)


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
    ctx = mock.MagicMock()

    with mock.patch.object(
        mesh_renderee.np,
        "empty",
        side_effect=AssertionError("empty framing used uninitialized memory"),
    ):
        first = create_mesh_renderee(
            ctx,
            mock.MagicMock(),
            [],
            np.eye(4, dtype="f4"),
            np.eye(4, dtype="f4"),
        )
        second = create_mesh_renderee(
            ctx,
            mock.MagicMock(),
            [],
            np.eye(4, dtype="f4"),
            np.eye(4, dtype="f4"),
        )

    expected = np.zeros((2, 3), dtype=np.float32)
    np.testing.assert_array_equal(first.points, expected)
    np.testing.assert_array_equal(second.points, expected)
    np.testing.assert_array_equal(first.points, second.points)
    assert first.points.dtype == np.float32
    assert np.isfinite(first.points).all()
    ctx.buffer.assert_not_called()


def test_non_empty_payload_list_preserves_bounds_corner_order():
    first_mesh = box()
    second_mesh = box()
    second_mesh.apply_translation([10.0, 20.0, 30.0])
    second_mesh.metadata["scadview"] = {"color": [1.0, 1.0, 1.0, 0.5]}
    first = mesh_to_payload(first_mesh)
    second = mesh_to_payload(second_mesh)

    renderee = create_mesh_renderee(
        mock.MagicMock(),
        mock.MagicMock(),
        [first, second],
        np.eye(4, dtype="f4"),
        np.eye(4, dtype="f4"),
    )

    expected = np.concatenate([payload_corners(first), payload_corners(second)])
    np.testing.assert_array_equal(renderee.points, expected)


def _payload_with_bounds(bounds, *, color):
    minimum, maximum = np.asarray(bounds, dtype=np.float32)
    return _payload(
        vertices=[minimum, maximum],
        faces=[],
        normals=[],
        color=color,
    )


@pytest.mark.parametrize(
    ("mesh_specs", "expected"),
    [
        (
            [([[2, 3, 4], [5, 6, 7]], [1, 2, 3, 255])],
            [
                [2, 3, 4],
                [2, 3, 7],
                [2, 6, 4],
                [2, 6, 7],
                [5, 3, 4],
                [5, 3, 7],
                [5, 6, 4],
                [5, 6, 7],
            ],
        ),
        (
            [([[-7, -6, -5], [-4, -3, -2]], [1, 2, 3, 128])],
            [
                [-7, -6, -5],
                [-7, -6, -2],
                [-7, -3, -5],
                [-7, -3, -2],
                [-4, -6, -5],
                [-4, -6, -2],
                [-4, -3, -5],
                [-4, -3, -2],
            ],
        ),
        (
            [
                ([[2, 3, 4], [5, 6, 7]], [1, 2, 3, 255]),
                ([[-7, -6, -5], [-4, -3, -2]], [1, 2, 3, 128]),
            ],
            [
                [2, 3, 4],
                [2, 3, 7],
                [2, 6, 4],
                [2, 6, 7],
                [5, 3, 4],
                [5, 3, 7],
                [5, 6, 4],
                [5, 6, 7],
                [-7, -6, -5],
                [-7, -6, -2],
                [-7, -3, -5],
                [-7, -3, -2],
                [-4, -6, -5],
                [-4, -6, -2],
                [-4, -3, -5],
                [-4, -3, -2],
            ],
        ),
    ],
)
def test_non_empty_payload_list_frames_only_real_partition_bounds(mesh_specs, expected):
    payloads = [
        _payload_with_bounds(bounds, color=color) for bounds, color in mesh_specs
    ]
    renderee = create_mesh_renderee(
        mock.MagicMock(),
        mock.MagicMock(),
        payloads,
        np.eye(4, dtype="f4"),
        np.eye(4, dtype="f4"),
    )

    np.testing.assert_array_equal(renderee.points, np.asarray(expected, dtype="f4"))
    assert renderee.points.dtype == np.float32
    assert np.isfinite(renderee.points).all()
    camera = CameraPerspective()
    camera.frame(renderee.points)
    assert np.isfinite(camera.position).all()
    assert np.isfinite(camera.look_at).all()
    assert np.isfinite(camera.near)
    assert np.isfinite(camera.far)


def test_render_package_has_no_trimesh_dependency_or_reconstruction():
    render_root = Path(__file__).parents[2] / "src" / "scadview" / "render"

    source = "\n".join(path.read_text() for path in render_root.glob("*.py"))

    assert "Trimesh" not in source
    assert "payload_to_trimesh" not in source


def _payload(
    *,
    vertices,
    faces,
    normals,
    color,
) -> MeshPayload:
    vertex_array = np.asarray(vertices, dtype=np.float32).reshape((-1, 3))
    face_array = np.asarray(faces, dtype=np.uint32).reshape((-1, 3))
    normal_array = np.asarray(normals, dtype=np.float32).reshape((-1, 3))
    color_array = None if color is None else np.asarray(color, dtype=np.uint8)
    if len(vertex_array):
        bounds = np.array(
            [vertex_array.min(axis=0), vertex_array.max(axis=0)], dtype=np.float32
        )
    else:
        bounds = np.zeros((2, 3), dtype=np.float32)
    return MeshPayload(
        vertices=vertex_array,
        faces=face_array,
        face_normals=normal_array,
        color=color_array,
        bounds=bounds,
        scale=0.0,
    )
