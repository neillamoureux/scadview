import pytest
import numpy as np
from unittest import mock
from meshsee.render.trimesh_renderee import TrimeshRenderee
from meshsee.render.trimesh_renderee import get_metadata_color, TrimeshSolidRenderee


class DummyTrimeshRenderee(TrimeshRenderee):
    @property
    def points(self):
        return np.array([[0, 0, 0]])

    def subscribe_to_updates(self, updates):
        self.subscribed = True

    def render(self):
        pass


def test_trimesh_renderee_init_and_properties():
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    renderee = DummyTrimeshRenderee(ctx, program)
    assert hasattr(renderee, "_ctx")
    assert hasattr(renderee, "_program")
    assert hasattr(renderee, "_vertices")
    assert hasattr(renderee, "_normals")
    assert hasattr(renderee, "_color_buff")
    assert isinstance(renderee.points, np.ndarray)


def test_trimesh_renderee_create_vao_calls_vertex_array():
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    renderee = DummyTrimeshRenderee(ctx, program)
    renderee._vertices = mock.MagicMock()
    renderee._normals = mock.MagicMock()
    renderee._color_buff = mock.MagicMock()
    renderee._ctx.vertex_array = mock.MagicMock()
    vao = renderee._create_vao()
    renderee._ctx.vertex_array.assert_called_once()
    assert vao == renderee._ctx.vertex_array()


def test_trimesh_renderee_subscribe_to_updates():
    ctx = mock.MagicMock()
    program = mock.MagicMock()
    renderee = DummyTrimeshRenderee(ctx, program)
    observable = mock.MagicMock()
    renderee.subscribe_to_updates(observable)
    assert hasattr(renderee, "subscribed") and renderee.subscribed


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
