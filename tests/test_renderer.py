from unittest.mock import MagicMock, Mock, patch

from meshsee.camera import Camera
from meshsee.renderer import Renderer


def test_aspect_ratio():
    context = MagicMock()
    m_proj = Mock()
    shader_vars = {
        "m_proj": m_proj,
        "m_camera": Mock(),
        "m_model": Mock(),
        "color": Mock(),
        "show_grid": Mock(),
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


def test_frame():
    context = MagicMock()
    camera = Mock()
    aspect_ratio = 1.6
    renderer = Renderer(context, camera, aspect_ratio)
    renderer.frame()
    camera.frame.assert_called()
