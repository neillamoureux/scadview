from unittest.mock import MagicMock, Mock, patch

import numpy as np

from scadview.render.camera import Camera
from scadview.render.renderer import Renderer


def test_window_size():
    context = MagicMock()
    m_proj = Mock()
    shader_vars = {
        "m_proj": m_proj,
        "m_camera": Mock(),
        "m_model": Mock(),
        "color": Mock(),
        "show_grid": Mock(),
        "show_edges": Mock(),
        "show_gnomon": Mock(),
    }
    context.program = Mock(return_value=shader_vars)
    camera = Camera()
    window_size = (50, 100)
    aspect_ratio = float(window_size[0]) / window_size[1]
    with patch("scadview.render.shader_program.isinstance") as mock_isinstance:
        mock_isinstance.return_value = True
        renderer = Renderer(context, camera, window_size)
        assert renderer.window_size == window_size
        assert renderer.aspect_ratio == aspect_ratio
        new_window_size = (320, 200)
        new_aspect_ratio = float(new_window_size[0]) / new_window_size[1]
        renderer.window_size = new_window_size
        assert renderer.window_size == new_window_size
        assert renderer.aspect_ratio == new_aspect_ratio
        assert camera.aspect_ratio == new_aspect_ratio


def test_frame():
    context = MagicMock()
    camera = Mock()
    window_size = (320, 200)
    with patch("scadview.render.shader_program.isinstance") as mock_isinstance:
        mock_isinstance.return_value = True
        renderer = Renderer(context, camera, window_size)
        renderer.frame(np.array([[1, 0, 0]]))
        camera.frame.assert_called()
