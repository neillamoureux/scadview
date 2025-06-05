from unittest import mock

import numpy as np
import pytest

from meshsee.render.trimesh_renderee import (
    TrimeshNullRenderee,
    TrimeshRenderee,
    TrimeshSolidRenderee,
    TrimeshTransparentRenderee,
    TrimeshListRenderee,
    TrimeshListSolidRenderee,
    TrimeshListTransparentRenderee,
    get_metadata_color,
    is_transparent,
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
def dummy_trimesh_transparent():
    dummy_trimesh = DummyTrimesh()
    dummy_trimesh.metadata = {"meshsee": {"color": [0.2, 0.3, 0.4, 0.5]}}
    return dummy_trimesh


# @pytest.fixture
# def dummy_trimesh_transparent():
#     # Minimal dummy Trimesh with triangles and triangles_cross attributes, transparent color
#     class DummyTrimesh:
#         def __init__(self):
#             self.triangles = np.array(
#                 [[[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[1, 0, 0], [1, 1, 0], [0, 1, 0]]],
#                 dtype="f4",
#             )
#             self.triangles_cross = np.array([[0, 0, 1], [0, 0, 1]], dtype="f4")
#             self.bounds = np.array([[0, 0, 0], [1, 1, 0]], dtype="f4")
#             self.metadata = {"meshsee": {"color": [0.2, 0.3, 0.4, 0.5]}}  # alpha < 1

#     return DummyTrimesh()


@pytest.fixture
def trimesh_transparent_renderee(
    dummy_trimesh_transparent,
):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    model_matrix = np.eye(4, dtype="f4")
    view_matrix = np.eye(4, dtype="f4")
    return TrimeshTransparentRenderee(
        ctx, program, dummy_trimesh_transparent, model_matrix, view_matrix
    )


@pytest.fixture
def trimesh_list_renderee(dummy_trimesh, dummy_trimesh_transparent):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    model_matrix = np.eye(4, dtype="f4")
    view_matrix = np.eye(4, dtype="f4")
    # Patch TrimeshListSolidRenderee and TrimeshListTransparentRenderee to track calls
    return TrimeshListRenderee(
        ctx,
        program,
        [dummy_trimesh, dummy_trimesh_transparent],
        model_matrix,
        view_matrix,
    )


def test_trimesh_renderee_init_and_properties(dummy_trimesh_renderee):
    # ctx = mock.MagicMock()
    # program = mock.MagicMock()
    # dummy_trimesh_renderee = DummyTrimeshRenderee(ctx, program)
    assert hasattr(dummy_trimesh_renderee, "_ctx")
    assert hasattr(dummy_trimesh_renderee, "_program")
    assert hasattr(dummy_trimesh_renderee, "_vertices")
    assert hasattr(dummy_trimesh_renderee, "_normals")
    assert hasattr(dummy_trimesh_renderee, "_color_buff")
    assert isinstance(dummy_trimesh_renderee.points, np.ndarray)


def test_trimesh_renderee_create_vao_calls_vertex_array(dummy_trimesh_renderee):
    # ctx = mock.MagicMock()
    # program = mock.MagicMock()
    # dummy_trimesh_renderee = DummyTrimeshRenderee(ctx, program)
    dummy_trimesh_renderee._vertices = mock.MagicMock()
    dummy_trimesh_renderee._normals = mock.MagicMock()
    dummy_trimesh_renderee._color_buff = mock.MagicMock()
    dummy_trimesh_renderee._ctx.vertex_array = mock.MagicMock()
    vao = dummy_trimesh_renderee._create_vao()
    dummy_trimesh_renderee._ctx.vertex_array.assert_called_once()
    assert vao == dummy_trimesh_renderee._ctx.vertex_array()


def test_trimesh_renderee_subscribe_to_updates(dummy_trimesh_renderee):
    # ctx = mock.MagicMock()
    # program = mock.MagicMock()
    # dummy_trimesh_renderee = DummyTrimeshRenderee(ctx, program)
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
    np.testing.assert_array_equal(result, TrimeshSolidRenderee.DEFAULT_COLOR)


def test_get_metadata_color_no_meshsee():
    mesh = DummyMesh(metadata={})
    result = get_metadata_color(mesh)
    np.testing.assert_array_equal(result, TrimeshSolidRenderee.DEFAULT_COLOR)


def test_get_metadata_color_meshsee_not_dict():
    mesh = DummyMesh(metadata={"meshsee": None})
    result = get_metadata_color(mesh)
    np.testing.assert_array_equal(result, TrimeshSolidRenderee.DEFAULT_COLOR)


def test_trimesh_solid_renderee_init_sets_buffers_and_vao(dummy_trimesh):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    ctx.buffer.return_value = mock.MagicMock()
    ctx.vertex_array.return_value = mock.MagicMock()
    renderee = TrimeshSolidRenderee(ctx, program, dummy_trimesh)
    assert hasattr(renderee, "_vertices")
    assert hasattr(renderee, "_normals")
    assert hasattr(renderee, "_color_buff")
    assert hasattr(renderee, "_vao")
    assert isinstance(renderee.points, np.ndarray)
    ctx.buffer.assert_called()  # At least once


def test_trimesh_solid_renderee_render_calls_ctx_methods(dummy_trimesh):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    ctx.buffer.return_value = mock.MagicMock()
    ctx.vertex_array.return_value = mock.MagicMock()
    renderee = TrimeshSolidRenderee(ctx, program, dummy_trimesh)
    renderee._vao = mock.MagicMock()
    renderee.render()
    ctx.enable.assert_any_call(mock.ANY)
    ctx.disable.assert_any_call(mock.ANY)
    assert ctx.depth_mask is True
    renderee._vao.render.assert_called_once()


def test_trimesh_solid_renderee_points_property(dummy_trimesh):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    ctx.buffer.return_value = mock.MagicMock()
    ctx.vertex_array.return_value = mock.MagicMock()
    renderee = TrimeshSolidRenderee(ctx, program, dummy_trimesh)
    points = renderee.points
    assert isinstance(points, np.ndarray)
    assert points.shape[1] == 3


def test_trimesh_solid_renderee_subscribe_to_updates_noop(dummy_trimesh):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    ctx.buffer.return_value = mock.MagicMock()
    ctx.vertex_array.return_value = mock.MagicMock()
    renderee = TrimeshSolidRenderee(ctx, program, dummy_trimesh)
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


def test_trimesh_transparent_renderee_init_sets_attributes(
    trimesh_transparent_renderee,
):
    assert np.array_equal(
        trimesh_transparent_renderee.model_matrix, np.eye(4, dtype="f4")
    )
    assert np.array_equal(
        trimesh_transparent_renderee.view_matrix, np.eye(4, dtype="f4")
    )
    assert trimesh_transparent_renderee._resort_verts is True


def test_trimesh_transparent_renderee_points_property(trimesh_transparent_renderee):
    trimesh_transparent_renderee._points = np.array([[1, 2, 3]])
    assert np.array_equal(trimesh_transparent_renderee.points, np.array([[1, 2, 3]]))


def test_trimesh_transparent_renderee_model_matrix_setter_sets_resort(
    trimesh_transparent_renderee,
):
    trimesh_transparent_renderee._resort_verts = False
    new_matrix = np.eye(4, dtype="f4") * 2
    trimesh_transparent_renderee.model_matrix = new_matrix
    assert np.allclose(trimesh_transparent_renderee.model_matrix, new_matrix)
    assert trimesh_transparent_renderee._resort_verts is True


def test_trimesh_transparent_renderee_view_matrix_setter_sets_resort(
    trimesh_transparent_renderee,
):
    trimesh_transparent_renderee._resort_verts = False
    new_matrix = np.eye(4, dtype="f4") * 3
    trimesh_transparent_renderee.view_matrix = new_matrix
    assert np.allclose(trimesh_transparent_renderee.view_matrix, new_matrix)
    assert trimesh_transparent_renderee._resort_verts is True


def test_trimesh_transparent_renderee_subscribe_to_updates_calls_subscribe(
    trimesh_transparent_renderee,
):
    observable = mock.MagicMock()
    trimesh_transparent_renderee.subscribe_to_updates(observable)
    observable.subscribe.assert_called_once_with(
        trimesh_transparent_renderee.update_matrix
    )


def test_trimesh_transparent_renderee_update_matrix_sets_matrices(
    trimesh_transparent_renderee,
):
    new_model = np.eye(4, dtype="f4") * 4
    trimesh_transparent_renderee.update_matrix(ShaderVar.MODEL_MATRIX, new_model)
    assert np.allclose(trimesh_transparent_renderee.model_matrix, new_model)
    # Test view matrix update
    new_view = np.eye(4, dtype="f4") * 5
    trimesh_transparent_renderee.update_matrix(ShaderVar.VIEW_MATRIX, new_view)
    assert np.allclose(trimesh_transparent_renderee.view_matrix, new_view)
    # Test projection matrix update
    new_proj = np.eye(4, dtype="f4") * 6
    trimesh_transparent_renderee.projection_matrix = None
    trimesh_transparent_renderee.update_matrix(ShaderVar.PROJECTION_MATRIX, new_proj)
    assert np.allclose(trimesh_transparent_renderee.projection_matrix, new_proj)


def test_trimesh_transparent_renderee_sort_buffers_calls_ctx_buffer(
    trimesh_transparent_renderee,
):
    trimesh_transparent_renderee._sort_buffers()
    assert (
        trimesh_transparent_renderee._ctx.buffer.call_count >= 3
    )  # vertices, normals, color_buff


def test_trimesh_transparent_renderee_render_calls_sort_and_vao_render(
    trimesh_transparent_renderee,
):
    trimesh_transparent_renderee._resort_verts = True
    trimesh_transparent_renderee._sort_buffers = mock.MagicMock()
    trimesh_transparent_renderee._create_vao = mock.MagicMock()
    vao_mock = mock.MagicMock()
    trimesh_transparent_renderee._create_vao.return_value = vao_mock
    trimesh_transparent_renderee._vao = vao_mock
    trimesh_transparent_renderee.render()
    trimesh_transparent_renderee._sort_buffers.assert_called_once()
    trimesh_transparent_renderee._create_vao.assert_called_once()
    vao_mock.render.assert_called_once()
    assert trimesh_transparent_renderee._ctx.enable.call_count >= 2
    assert trimesh_transparent_renderee._ctx.depth_mask is False

    # def make_dummy_mesh(color=[0.2, 0.3, 0.4, 1.0]):
    #     class DummyTrimesh:
    #         def __init__(self):
    #             self.triangles = np.array(
    #                 [[[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[1, 0, 0], [1, 1, 0], [0, 1, 0]]],
    #                 dtype="f4",
    #             )
    #             self.triangles_cross = np.array([[0, 0, 1], [0, 0, 1]], dtype="f4")
    #             self.bounds = np.array([[0, 0, 0], [1, 1, 0]], dtype="f4")
    #             self.metadata = {"meshsee": {"color": color}}
    #     return DummyTrimesh()


def test_trimesh_list_renderee_init_splits_meshes(trimesh_list_renderee):
    # ctx = mock.MagicMock()
    # program = mock.MagicMock()
    # model_matrix = np.eye(4, dtype="f4")
    # view_matrix = np.eye(4, dtype="f4")
    # mesh1 = make_dummy_mesh([0.2, 0.3, 0.4, 1.0])  # solid
    # mesh2 = make_dummy_mesh([0.2, 0.3, 0.4, 0.5])  # transparent

    # Patch TrimeshListSolidRenderee and TrimeshListTransparentRenderee to track calls
    # solid_mock = mock.MagicMock()
    # transparent_mock = mock.MagicMock()
    # monkeypatch.setattr(
    #     "meshsee.render.trimesh_renderee.TrimeshListSolidRenderee",
    #     lambda *a, **kw: solid_mock,
    # )
    # monkeypatch.setattr(
    #     "meshsee.render.trimesh_renderee.TrimeshListTransparentRenderee",
    #     lambda *a, **kw: transparent_mock,
    # )
    # monkeypatch.setattr(
    #     "meshsee.render.trimesh_renderee.TrimeshNullRenderee",
    #     lambda *a, **kw: mock.MagicMock(),
    # )

    # renderee = TrimeshListRenderee(
    #     ctx, program, [dummy_mesh, dummy_mesh_transparent], model_matrix, view_matrix
    # )
    assert hasattr(trimesh_list_renderee, "_solid_renderee")
    assert len(trimesh_list_renderee._solid_meshes) == 1
    assert not is_transparent(trimesh_list_renderee._solid_meshes[0])
    assert hasattr(trimesh_list_renderee, "_transparent_renderee")
    assert len(trimesh_list_renderee._transparent_meshes) == 1
    assert is_transparent(trimesh_list_renderee._transparent_meshes[0])

    # assert (
    #     solid_mock is renderee._solid_renderee
    #     or transparent_mock is renderee._transparent_renderee
    # )


def test_trimesh_list_renderee_points_concat(monkeypatch):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    model_matrix = np.eye(4, dtype="f4")
    view_matrix = np.eye(4, dtype="f4")
    solid_points = np.ones((2, 3))
    transparent_points = np.zeros((3, 3))
    solid_mock = mock.MagicMock(points=solid_points)
    transparent_mock = mock.MagicMock(points=transparent_points)
    monkeypatch.setattr(
        "meshsee.render.trimesh_renderee.TrimeshListSolidRenderee",
        lambda *a, **kw: solid_mock,
    )
    monkeypatch.setattr(
        "meshsee.render.trimesh_renderee.TrimeshListTransparentRenderee",
        lambda *a, **kw: transparent_mock,
    )
    monkeypatch.setattr(
        "meshsee.render.trimesh_renderee.TrimeshNullRenderee",
        lambda *a, **kw: mock.MagicMock(points=np.empty((0, 3))),
    )
    mesh1 = make_dummy_mesh([0.2, 0.3, 0.4, 1.0])
    mesh2 = make_dummy_mesh([0.2, 0.3, 0.4, 0.5])
    renderee = __import__(
        "meshsee.render.trimesh_renderee", fromlist=["TrimeshListRenderee"]
    ).TrimeshListRenderee(ctx, program, [mesh1, mesh2], model_matrix, view_matrix)
    points = renderee.points
    assert isinstance(points, np.ndarray)
    assert points.shape == (5, 3)
    assert np.all(points[:2] == 1)
    assert np.all(points[2:] == 0)


def test_trimesh_list_renderee_subscribe_to_updates(monkeypatch):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    model_matrix = np.eye(4, dtype="f4")
    view_matrix = np.eye(4, dtype="f4")
    solid_mock = mock.MagicMock()
    transparent_mock = mock.MagicMock()
    monkeypatch.setattr(
        "meshsee.render.trimesh_renderee.TrimeshListSolidRenderee",
        lambda *a, **kw: solid_mock,
    )
    monkeypatch.setattr(
        "meshsee.render.trimesh_renderee.TrimeshListTransparentRenderee",
        lambda *a, **kw: transparent_mock,
    )
    monkeypatch.setattr(
        "meshsee.render.trimesh_renderee.TrimeshNullRenderee",
        lambda *a, **kw: mock.MagicMock(),
    )
    mesh1 = make_dummy_mesh([0.2, 0.3, 0.4, 1.0])
    mesh2 = make_dummy_mesh([0.2, 0.3, 0.4, 0.5])
    renderee = __import__(
        "meshsee.render.trimesh_renderee", fromlist=["TrimeshListRenderee"]
    ).TrimeshListRenderee(ctx, program, [mesh1, mesh2], model_matrix, view_matrix)
    observable = mock.MagicMock()
    renderee.subscribe_to_updates(observable)
    transparent_mock.subscribe_to_updates.assert_called_once_with(observable)


def test_trimesh_list_renderee_render_calls_both(monkeypatch):
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    model_matrix = np.eye(4, dtype="f4")
    view_matrix = np.eye(4, dtype="f4")
    solid_mock = mock.MagicMock()
    transparent_mock = mock.MagicMock()
    monkeypatch.setattr(
        "meshsee.render.trimesh_renderee.TrimeshListSolidRenderee",
        lambda *a, **kw: solid_mock,
    )
    monkeypatch.setattr(
        "meshsee.render.trimesh_renderee.TrimeshListTransparentRenderee",
        lambda *a, **kw: transparent_mock,
    )
    monkeypatch.setattr(
        "meshsee.render.trimesh_renderee.TrimeshNullRenderee",
        lambda *a, **kw: mock.MagicMock(),
    )
    mesh1 = make_dummy_mesh([0.2, 0.3, 0.4, 1.0])
    mesh2 = make_dummy_mesh([0.2, 0.3, 0.4, 0.5])
    renderee = __import__(
        "meshsee.render.trimesh_renderee", fromlist=["TrimeshListRenderee"]
    ).TrimeshListRenderee(ctx, program, [mesh1, mesh2], model_matrix, view_matrix)
    renderee.render()
    solid_mock.render.assert_called_once()
    transparent_mock.render.assert_called_once()
