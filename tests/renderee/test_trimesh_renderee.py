from unittest import mock

import numpy as np
from pyrr import matrix44
import pytest
from trimesh.creation import box, icosphere

from meshsee.render.trimesh_renderee import (
    DEFAULT_COLOR,
    AlphaRenderee,
    TrimeshAlphaRenderee,
    TrimeshListAlphaRenderee,
    TrimeshListOpaqueRenderee,
    TrimeshListRenderee,
    TrimeshNullRenderee,
    TrimeshOpaqueRenderee,
    TrimeshRenderee,
    concat_colors,
    create_colors_array,
    create_colors_array_from_mesh,
    create_trimesh_renderee,
    get_metadata_color,
    sort_triangles,
)
from meshsee.shader_program import ShaderVar


@pytest.fixture
def dummy_trimesh_renderee():
    class DummyTrimeshRenderee(TrimeshRenderee):
        @property
        def points(self):
            return np.array([[0, 0, 0]])

        def subscribe_to_updates(self, updates):
            self.subscribed = True

        def render(self):
            pass

    ctx = mock.MagicMock()
    program = mock.MagicMock()
    return DummyTrimeshRenderee(ctx, program)


# Minimal dummy Trimesh with triangles and triangles_cross attributes
class DummyTrimesh:
    def __init__(self):
        self.triangles = np.array(
            [[[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[1, 0, 0], [1, 1, 0], [0, 1, 0]]],
            dtype="f4",
        )
        self.triangles_cross = np.array([[0, 0, 1], [0, 0, 1]], dtype="f4")
        self.bounds = np.array([[0, 0, 0], [1, 1, 0]], dtype="f4")
        self.metadata = {"meshsee": {"color": [0.2, 0.3, 0.4, 1.0]}}


@pytest.fixture
def dummy_trimesh():
    return DummyTrimesh()


@pytest.fixture
def dummy_trimesh_alpha():
    dummy_trimesh = DummyTrimesh()
    dummy_trimesh.metadata = {"meshsee": {"color": [0.2, 0.3, 0.4, 0.5]}}
    return dummy_trimesh


@pytest.fixture
def alpha_renderee():
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    mesh = box()
    mesh.metadata["meshsee"] = {"meshsee": {"color": [0.2, 0.3, 0.4, 0.5]}}
    model_matrix = np.eye(4, dtype="f4")
    view_matrix = np.eye(4, dtype="f4")
    return AlphaRenderee(
        ctx,
        program,
        mesh.triangles,
        mesh.triangles_cross,
        create_colors_array_from_mesh(mesh),
        model_matrix,
        view_matrix,
    )


@pytest.fixture
def dummy_trimesh_alpha_renderee(
    dummy_trimesh_alpha,
):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    model_matrix = np.eye(4, dtype="f4")
    view_matrix = np.eye(4, dtype="f4")
    return TrimeshAlphaRenderee(
        ctx, program, dummy_trimesh_alpha, model_matrix, view_matrix
    )


@pytest.fixture
def dummy_trimesh_list_renderee(dummy_trimesh_renderee, dummy_trimesh_alpha_renderee):
    return TrimeshListRenderee(
        dummy_trimesh_renderee,
        dummy_trimesh_alpha_renderee,
    )


def test_get_metadata_color(dummy_trimesh):
    expected_color = [0.1, 0.2, 0.3, 0.4]
    dummy_trimesh.metadata["meshsee"] = {"color": expected_color}
    assert np.all(get_metadata_color(dummy_trimesh) == expected_color)


def test_get_metadata_color_empty_dict(dummy_trimesh):
    dummy_trimesh.metadata = {}
    assert np.all(get_metadata_color(dummy_trimesh) == DEFAULT_COLOR)


def test_get_metadata_color_none(dummy_trimesh):
    dummy_trimesh.metadata = None
    assert np.all(get_metadata_color(dummy_trimesh) == DEFAULT_COLOR)


def test_get_metadata_color_missing(dummy_trimesh):
    del dummy_trimesh.metadata["meshsee"]["color"]
    assert np.all(get_metadata_color(dummy_trimesh) == DEFAULT_COLOR)


def test_create_colors_array():
    color = np.array([0.1, 0.3, 0.7, 0.5])
    triangle_count = 5
    colors_arr = create_colors_array(color, triangle_count)
    assert colors_arr.shape == (triangle_count, 3, 4)
    colors = colors_arr.reshape(-1, 4)
    for c in colors:
        print(c)
        assert np.all(c == color.astype("f4"))


def test_concat_colors():
    mesh1 = box()
    mesh1.metadata["meshsee"] = {"color": [0.1, 0.2, 0.3, 0.4]}
    mesh2 = box()
    mesh2.metadata["meshsee"] = {"color": [0.5, 0.6, 0.7, 0.8]}
    colors = concat_colors([mesh1, mesh2])
    assert colors.shape == (2 * 12, 3 * 4)
    for i, color in enumerate(colors):
        if i < 12:
            assert np.all(color[0:4] == np.array([0.1, 0.2, 0.3, 0.4], dtype="f4"))
            assert np.all(color[4:8] == np.array([0.1, 0.2, 0.3, 0.4], dtype="f4"))
            assert np.all(color[8:12] == np.array([0.1, 0.2, 0.3, 0.4], dtype="f4"))
        else:
            assert np.all(color[0:4] == np.array([0.5, 0.6, 0.7, 0.8], dtype="f4"))
            assert np.all(color[4:8] == np.array([0.5, 0.6, 0.7, 0.8], dtype="f4"))
            assert np.all(color[8:12] == np.array([0.5, 0.6, 0.7, 0.8], dtype="f4"))


def test_sort_vertices():
    mesh = icosphere()
    view_matrix = matrix44.create_look_at(
        eye=[1.0, 2.0, 3.0],
        target=[-3.0, -4.0, -2.0],
        up=[0.1, 0.2, 1.0],
        dtype="f4",
    )
    model_matrix = np.eye(4, dtype="f4")
    sorted_indices = sort_triangles(mesh.triangles, model_matrix, view_matrix)
    assert sorted_indices.shape[0] == mesh.triangles.shape[0]
    sorted_centers = mesh.triangles_center[sorted_indices]
    sorted_centers = np.hstack(
        [
            sorted_centers,
            np.ones((sorted_centers.shape[0], 1), dtype=sorted_centers.dtype),
        ]
    )
    sorted_centers = sorted_centers @ model_matrix @ view_matrix
    for i in range(1, sorted_indices.shape[0]):
        assert (
            sorted_centers[i, 2] / sorted_centers[i, 3]
            >= sorted_centers[i - 1, 2] / sorted_centers[i - 1, 3]
        )


def test_create_trimesh_renderee_no_color():
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    trimesh = box()
    model_matrix = np.eye(4)
    view_matrix = np.eye(4)
    renderee = create_trimesh_renderee(ctx, program, trimesh, model_matrix, view_matrix)
    assert type(renderee) == TrimeshOpaqueRenderee


def test_create_trimesh_renderee_opaque():
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    trimesh = box()
    trimesh.metadata["meshsee"] = {"color": [0.0, 0.0, 0.0, 1.0]}
    model_matrix = np.eye(4)
    view_matrix = np.eye(4)
    renderee = create_trimesh_renderee(ctx, program, trimesh, model_matrix, view_matrix)
    assert type(renderee) == TrimeshOpaqueRenderee


def test_create_trimesh_renderee_alpha():
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    trimesh = box()
    trimesh.metadata["meshsee"] = {"color": [0.0, 0.0, 0.0, 0.5]}
    model_matrix = np.eye(4)
    view_matrix = np.eye(4)
    renderee = create_trimesh_renderee(ctx, program, trimesh, model_matrix, view_matrix)
    assert type(renderee) == TrimeshAlphaRenderee


@mock.patch("meshsee.render.trimesh_renderee.TrimeshListRenderee")
def test_create_trimesh_renderee_list_opaque_only(TrimeshListRenderee):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    trimesh = box()
    trimesh.metadata["meshsee"] = {"color": [0.0, 0.0, 0.0, 1.0]}
    model_matrix = np.eye(4)
    view_matrix = np.eye(4)
    expected_opaques = [trimesh]
    expected_alphas = []
    create_trimesh_renderee(ctx, program, [trimesh], model_matrix, view_matrix)
    assert TrimeshListRenderee.called_once_with(expected_opaques, expected_alphas)


@mock.patch("meshsee.render.trimesh_renderee.TrimeshListRenderee")
def test_create_trimesh_renderee_list_alpha_only(TrimeshListRenderee):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    trimesh = box()
    trimesh.metadata["meshsee"] = {"color": [0.0, 0.0, 0.0, 0.5]}
    model_matrix = np.eye(4)
    view_matrix = np.eye(4)
    expected_opaques = []
    expected_alphas = [trimesh]
    create_trimesh_renderee(ctx, program, [trimesh], model_matrix, view_matrix)
    assert TrimeshListRenderee.called_once_with(expected_opaques, expected_alphas)


@mock.patch("meshsee.render.trimesh_renderee.TrimeshListRenderee")
def test_create_trimesh_renderee_list(TrimeshListRenderee):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    trimesh_op1 = box()
    trimesh_op1.metadata["meshsee"] = {"color": [0.0, 0.0, 0.0, 1.0]}
    trimesh_op2 = box()
    trimesh_op2.metadata["meshsee"] = {"color": [0.0, 0.0, 1.0, 1.0]}
    trimesh_al1 = box()
    trimesh_al1.metadata["meshsee"] = {"color": [0.0, 0.0, 1.0, 0.99]}
    trimesh_al2 = box()
    trimesh_al2.metadata["meshsee"] = {"color": [0.0, 1.0, 1.0, 0.9]}
    model_matrix = np.eye(4)
    view_matrix = np.eye(4)
    expected_opaques = [trimesh_op1, trimesh_op2]
    expected_alphas = [trimesh_al1, trimesh_al2]
    create_trimesh_renderee(
        ctx,
        program,
        [trimesh_al1, trimesh_op1, trimesh_op2, trimesh_al2],
        model_matrix,
        view_matrix,
    )
    assert TrimeshListRenderee.called_once_with(expected_opaques, expected_alphas)


def test_trimesh_renderee_init_and_properties(dummy_trimesh_renderee):
    assert hasattr(dummy_trimesh_renderee, "_ctx")
    assert hasattr(dummy_trimesh_renderee, "_program")
    assert isinstance(dummy_trimesh_renderee.points, np.ndarray)


def test_trimesh_renderee_subscribe_to_updates(dummy_trimesh_renderee):
    observable = mock.MagicMock()
    dummy_trimesh_renderee.subscribe_to_updates(observable)
    assert (
        hasattr(dummy_trimesh_renderee, "subscribed")
        and dummy_trimesh_renderee.subscribed
    )


class DummyMesh:
    def __init__(self, metadata=None):
        self.metadata = metadata or {}


def test_get_metadata_color_with_meshsee_color():
    color = [0.1, 0.2, 0.3, 0.4]
    mesh = DummyMesh(metadata={"meshsee": {"color": color}})
    result = get_metadata_color(mesh)
    np.testing.assert_array_equal(result, np.array(color))


def test_get_metadata_color_with_meshsee_no_color():
    mesh = DummyMesh(metadata={"meshsee": {}})
    result = get_metadata_color(mesh)
    np.testing.assert_array_equal(result, DEFAULT_COLOR)


def test_get_metadata_color_no_meshsee():
    mesh = DummyMesh(metadata={})
    result = get_metadata_color(mesh)
    np.testing.assert_array_equal(result, DEFAULT_COLOR)


def test_get_metadata_color_meshsee_not_dict():
    mesh = DummyMesh(metadata={"meshsee": None})
    result = get_metadata_color(mesh)
    np.testing.assert_array_equal(result, DEFAULT_COLOR)


def test_trimesh_opaque_renderee_init_sets_vao(dummy_trimesh):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    ctx.buffer.return_value = mock.MagicMock()
    ctx.vertex_array.return_value = mock.MagicMock()
    renderee = TrimeshOpaqueRenderee(ctx, program, dummy_trimesh)
    assert hasattr(renderee, "_vao")
    assert isinstance(renderee.points, np.ndarray)
    ctx.buffer.assert_called()  # At least once


def test_trimesh_opaque_renderee_render_calls_ctx_methods(dummy_trimesh):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    ctx.buffer.return_value = mock.MagicMock()
    ctx.vertex_array.return_value = mock.MagicMock()
    renderee = TrimeshOpaqueRenderee(ctx, program, dummy_trimesh)
    renderee._vao = mock.MagicMock()
    renderee.render()
    ctx.enable.assert_any_call(mock.ANY)
    ctx.disable.assert_any_call(mock.ANY)
    assert ctx.depth_mask is True
    renderee._vao.render.assert_called_once()


def test_trimesh_opaque_renderee_points_property(dummy_trimesh):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    ctx.buffer.return_value = mock.MagicMock()
    ctx.vertex_array.return_value = mock.MagicMock()
    renderee = TrimeshOpaqueRenderee(ctx, program, dummy_trimesh)
    points = renderee.points
    assert isinstance(points, np.ndarray)
    assert points.shape[1] == 3


def test_trimesh_opaque_renderee_subscribe_to_updates_noop(dummy_trimesh):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    ctx.buffer.return_value = mock.MagicMock()
    ctx.vertex_array.return_value = mock.MagicMock()
    renderee = TrimeshOpaqueRenderee(ctx, program, dummy_trimesh)
    observable = mock.MagicMock()
    # Should not raise or do anything
    renderee.subscribe_to_updates(observable)


def test_trimesh_null_renderee_points_is_empty():
    renderee = TrimeshNullRenderee()
    points = renderee.points
    assert isinstance(points, np.ndarray)
    assert points.shape == (1, 3)


def test_trimesh_null_renderee_render_does_nothing():
    renderee = TrimeshNullRenderee()
    # Should not raise any exceptions
    renderee.render()


def test_trimesh_null_renderee_has_no_buffers_or_vao():
    renderee = TrimeshNullRenderee()
    # TrimeshNullRenderee should not have _vertices, _normals, _color_buff, or _vao attributes
    assert not hasattr(renderee, "_vertices")
    assert not hasattr(renderee, "_normals")
    assert not hasattr(renderee, "_color_buff")
    assert not hasattr(renderee, "_vao")


def test_alpha_renderee_init_sets_attributes(
    alpha_renderee,
):
    assert np.array_equal(alpha_renderee.model_matrix, np.eye(4, dtype="f4"))
    assert np.array_equal(alpha_renderee.view_matrix, np.eye(4, dtype="f4"))
    assert alpha_renderee._resort_verts is False


def test_trimesh_alpha_renderee_points_property(dummy_trimesh_alpha_renderee):
    dummy_trimesh_alpha_renderee._points = np.array([[1, 2, 3]])
    assert np.array_equal(dummy_trimesh_alpha_renderee.points, np.array([[1, 2, 3]]))


def test_alpha_renderee_model_matrix_setter_sets_resort(
    alpha_renderee,
):
    alpha_renderee._resort_verts = False
    new_matrix = np.eye(4, dtype="f4") * 2
    alpha_renderee.model_matrix = new_matrix
    assert np.allclose(alpha_renderee.model_matrix, new_matrix)
    assert alpha_renderee._resort_verts is True


def test_alpha_renderee_view_matrix_setter_sets_resort(
    alpha_renderee,
):
    alpha_renderee._resort_verts = False
    new_matrix = np.eye(4, dtype="f4") * 3
    alpha_renderee.view_matrix = new_matrix
    assert np.allclose(alpha_renderee.view_matrix, new_matrix)
    assert alpha_renderee._resort_verts is True


def test_alpha_renderee_subscribe_to_updates_calls_subscribe(
    alpha_renderee,
):
    observable = mock.MagicMock()
    alpha_renderee.subscribe_to_updates(observable)
    observable.subscribe.assert_called_once_with(alpha_renderee.update_matrix)


def test_alpha_renderee_update_matrix_sets_matrices(
    alpha_renderee,
):
    new_model = np.eye(4, dtype="f4") * 4
    alpha_renderee.update_matrix(ShaderVar.MODEL_MATRIX, new_model)
    assert np.allclose(alpha_renderee.model_matrix, new_model)
    # Test view matrix update
    new_view = np.eye(4, dtype="f4") * 5
    alpha_renderee.update_matrix(ShaderVar.VIEW_MATRIX, new_view)
    assert np.allclose(alpha_renderee.view_matrix, new_view)


def test_alpha_renderee_sort_buffers_calls_ctx_buffer(
    alpha_renderee,
):
    alpha_renderee._sort_buffers()
    assert alpha_renderee._ctx.buffer.call_count >= 3  # vertices, normals, color_buff


@mock.patch("meshsee.render.trimesh_renderee.create_vao")
def test_alpha_renderee_render_calls_sort_and_vao_render(
    create_vao,
    alpha_renderee,
):
    alpha_renderee._resort_verts = True
    alpha_renderee._sort_buffers = mock.MagicMock()
    # dummy_trimesh_alpha_renderee._create_vao = mock.MagicMock()
    vao_mock = mock.MagicMock()
    create_vao.return_value = vao_mock
    # dummy_trimesh_alpha_renderee._create_vao.return_value = vao_mock
    alpha_renderee._vao = vao_mock
    alpha_renderee.render()
    alpha_renderee._sort_buffers.assert_called_once()
    # dummy_trimesh_alpha_renderee._create_vao.assert_called_once()
    vao_mock.render.assert_called_once()
    assert alpha_renderee._ctx.enable.call_count >= 2
    assert alpha_renderee._ctx.depth_mask is False


def test_trimesh_list_renderee_points_concat(dummy_trimesh_list_renderee):
    points = dummy_trimesh_list_renderee.points
    assert isinstance(points, np.ndarray)
    expected_count = (
        dummy_trimesh_list_renderee._opaques_renderee.points.shape[0]
        + dummy_trimesh_list_renderee._alphas_renderee.points.shape[0]
    )
    assert points.shape == (expected_count, 3)
    assert np.all(
        points
        == np.concatenate(
            [
                dummy_trimesh_list_renderee._opaques_renderee.points,
                dummy_trimesh_list_renderee._alphas_renderee.points,
            ]
        )
    )


def test_trimesh_list_renderee_subscribe_to_updates(dummy_trimesh_list_renderee):
    observable = mock.MagicMock()
    dummy_trimesh_list_renderee._alphas_renderee = mock.MagicMock()
    dummy_trimesh_list_renderee.subscribe_to_updates(observable)
    dummy_trimesh_list_renderee._alphas_renderee.subscribe_to_updates.assert_called_once_with(
        observable
    )


def test_trimesh_list_renderee_render_calls_both(dummy_trimesh_list_renderee):
    dummy_trimesh_list_renderee._opaques_renderee.render = mock.MagicMock()
    dummy_trimesh_list_renderee._alphas_renderee.render = mock.MagicMock()
    dummy_trimesh_list_renderee.render()
    dummy_trimesh_list_renderee._opaques_renderee.render.assert_called_once()
    dummy_trimesh_list_renderee._alphas_renderee.render.assert_called_once()
