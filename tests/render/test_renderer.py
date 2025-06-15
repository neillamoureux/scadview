from unittest.mock import MagicMock, Mock, patch

import numpy as np

from meshsee.render.camera import Camera
from meshsee.render.renderer import Renderer


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
    with patch("meshsee.render.shader_program.isinstance") as mock_isinstance:
        mock_isinstance.return_value = True
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
    with patch("meshsee.render.shader_program.isinstance") as mock_isinstance:
        mock_isinstance.return_value = True
        renderer = Renderer(context, camera, aspect_ratio)
        renderer.frame(np.array([[1, 0, 0]]))
        camera.frame.assert_called()
