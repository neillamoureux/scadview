from unittest import mock

import numpy as np
import pytest

from meshsee.render.trimesh_renderee import (
    DEFAULT_COLOR,
    TrimeshNullRenderee,
    TrimeshRenderee,
    TrimeshAlphaRenderee,
    TrimeshOpaqueRenderee,
    TrimeshListRenderee,
    TrimeshListOpaqueRenderee,
    TrimeshListAlphaRenderee,
    get_metadata_color,
    is_alpha,
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


def test_trimesh_alpha_renderee_init_sets_attributes(
    dummy_trimesh_alpha_renderee,
):
    assert np.array_equal(
        dummy_trimesh_alpha_renderee.model_matrix, np.eye(4, dtype="f4")
    )
    assert np.array_equal(
        dummy_trimesh_alpha_renderee.view_matrix, np.eye(4, dtype="f4")
    )
    assert dummy_trimesh_alpha_renderee._resort_verts is False


def test_trimesh_alpha_renderee_points_property(dummy_trimesh_alpha_renderee):
    dummy_trimesh_alpha_renderee._points = np.array([[1, 2, 3]])
    assert np.array_equal(dummy_trimesh_alpha_renderee.points, np.array([[1, 2, 3]]))


def test_trimesh_alpha_renderee_model_matrix_setter_sets_resort(
    dummy_trimesh_alpha_renderee,
):
    dummy_trimesh_alpha_renderee._resort_verts = False
    new_matrix = np.eye(4, dtype="f4") * 2
    dummy_trimesh_alpha_renderee.model_matrix = new_matrix
    assert np.allclose(dummy_trimesh_alpha_renderee.model_matrix, new_matrix)
    assert dummy_trimesh_alpha_renderee._resort_verts is True


def test_trimesh_alpha_renderee_view_matrix_setter_sets_resort(
    dummy_trimesh_alpha_renderee,
):
    dummy_trimesh_alpha_renderee._resort_verts = False
    new_matrix = np.eye(4, dtype="f4") * 3
    dummy_trimesh_alpha_renderee.view_matrix = new_matrix
    assert np.allclose(dummy_trimesh_alpha_renderee.view_matrix, new_matrix)
    assert dummy_trimesh_alpha_renderee._resort_verts is True


def test_trimesh_alpha_renderee_subscribe_to_updates_calls_subscribe(
    dummy_trimesh_alpha_renderee,
):
    observable = mock.MagicMock()
    dummy_trimesh_alpha_renderee.subscribe_to_updates(observable)
    observable.subscribe.assert_called_once_with(
        dummy_trimesh_alpha_renderee.update_matrix
    )


def test_trimesh_alpha_renderee_update_matrix_sets_matrices(
    dummy_trimesh_alpha_renderee,
):
    new_model = np.eye(4, dtype="f4") * 4
    dummy_trimesh_alpha_renderee.update_matrix(ShaderVar.MODEL_MATRIX, new_model)
    assert np.allclose(dummy_trimesh_alpha_renderee.model_matrix, new_model)
    # Test view matrix update
    new_view = np.eye(4, dtype="f4") * 5
    dummy_trimesh_alpha_renderee.update_matrix(ShaderVar.VIEW_MATRIX, new_view)
    assert np.allclose(dummy_trimesh_alpha_renderee.view_matrix, new_view)
    # Test projection matrix update
    new_proj = np.eye(4, dtype="f4") * 6
    dummy_trimesh_alpha_renderee.projection_matrix = None
    dummy_trimesh_alpha_renderee.update_matrix(ShaderVar.PROJECTION_MATRIX, new_proj)
    assert np.allclose(dummy_trimesh_alpha_renderee.projection_matrix, new_proj)


def test_trimesh_alpha_renderee_sort_buffers_calls_ctx_buffer(
    dummy_trimesh_alpha_renderee,
):
    dummy_trimesh_alpha_renderee._sort_buffers()
    assert (
        dummy_trimesh_alpha_renderee._ctx.buffer.call_count >= 3
    )  # vertices, normals, color_buff


@mock.patch("meshsee.render.trimesh_renderee.create_vao")
def test_trimesh_alpha_renderee_render_calls_sort_and_vao_render(
    create_vao,
    dummy_trimesh_alpha_renderee,
):
    dummy_trimesh_alpha_renderee._resort_verts = True
    dummy_trimesh_alpha_renderee._sort_buffers = mock.MagicMock()
    # dummy_trimesh_alpha_renderee._create_vao = mock.MagicMock()
    vao_mock = mock.MagicMock()
    create_vao.return_value = vao_mock
    # dummy_trimesh_alpha_renderee._create_vao.return_value = vao_mock
    dummy_trimesh_alpha_renderee._vao = vao_mock
    dummy_trimesh_alpha_renderee.render()
    dummy_trimesh_alpha_renderee._sort_buffers.assert_called_once()
    # dummy_trimesh_alpha_renderee._create_vao.assert_called_once()
    vao_mock.render.assert_called_once()
    assert dummy_trimesh_alpha_renderee._ctx.enable.call_count >= 2
    assert dummy_trimesh_alpha_renderee._ctx.depth_mask is False


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
