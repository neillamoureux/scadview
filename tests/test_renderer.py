from unittest.mock import MagicMock, Mock, patch

from pyrr import Matrix44
import numpy as np

from meshsee.camera import Camera
from meshsee.renderer import Renderer


# @patch("meshsee.renderer._make_axes")
# @patch("meshsee.renderer._make_default_mesh")
# def test_init(make_default_mesh, make_axes):
#     context = MagicMock()
#     camera = Camera()
#     aspect_ratio = 1.6
#     orig_frame = Renderer.frame
#     Renderer.frame = Mock()
#     orig_load_mesh = Renderer.load_mesh
#     Renderer.load_mesh = Mock()
#     orig_load_axes = Renderer._load_axes
#     Renderer._load_axes = Mock()
#     make_default_mesh.return_value = "default mesh"
#     make_axes.return_value = "axes"
#     renderer = Renderer(context, camera, aspect_ratio)
#     assert renderer.aspect_ratio == aspect_ratio
#     context.clear.assert_called_with(*Renderer.BACKGROUND_COLOR)
#     context.program.assert_called()
#     renderer.frame.assert_called_once()
#     assert renderer._default_mesh == "default mesh"
#     renderer.load_mesh.assert_called_with(renderer._default_mesh)
#     assert renderer._axes == "axes"
#     renderer._load_axes.assert_called_with(renderer._axes)
#     Renderer.frame = orig_frame
#     Renderer.load_mesh = orig_load_mesh
#     Renderer._load_axes = orig_load_axes


def test_aspect_ratio():
    context = MagicMock()
    m_proj = Mock()
    shader_vars = {
        "m_proj": m_proj,
        "m_camera": Mock(),
        "m_model": Mock(),
        "color": Mock(),
        "atlas": Mock(),
    }
    context.program = Mock(return_value=shader_vars)
    camera = Camera()
    aspect_ratio = 0.5
    renderer = Renderer(context, camera, aspect_ratio)
    assert renderer.aspect_ratio == aspect_ratio
    new_aspect_ratio = 1.6
    renderer.aspect_ratio = new_aspect_ratio
    assert renderer.aspect_ratio == new_aspect_ratio
    assert camera.aspect_ratio == new_aspect_ratio
    assert np.array_equal(m_proj.write.call_args[0][0], camera.projection_matrix)


def test_frame():
    context = MagicMock()
    camera = Mock()
    aspect_ratio = 1.6
    renderer = Renderer(context, camera, aspect_ratio)
    renderer.frame()
    camera.frame.assert_called()
