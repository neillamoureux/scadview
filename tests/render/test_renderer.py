from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from trimesh.creation import box

from scadview.load_status import LoadStatus
from scadview.mesh_payload import mesh_to_payload
from scadview.render.camera import Camera
from scadview.render.renderer import Renderer, RendererFactory
from scadview.scene_assets import SceneAssets


@pytest.fixture
def scene_assets():
    payload = mesh_to_payload(box())
    return SceneAssets(payload, payload, payload)


def test_window_size(scene_assets):
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
        renderer = Renderer(context, camera, window_size, scene_assets)
        assert renderer.window_size == window_size
        assert renderer.aspect_ratio == aspect_ratio
        new_window_size = (320, 200)
        new_aspect_ratio = float(new_window_size[0]) / new_window_size[1]
        renderer.window_size = new_window_size
        assert renderer.window_size == new_window_size
        assert renderer.aspect_ratio == new_aspect_ratio
        assert camera.aspect_ratio == new_aspect_ratio


def test_frame(scene_assets):
    context = MagicMock()
    camera = Mock()
    window_size = (320, 200)
    with patch("scadview.render.shader_program.isinstance") as mock_isinstance:
        mock_isinstance.return_value = True
        renderer = Renderer(context, camera, window_size, scene_assets)
        renderer.frame(np.array([[1, 0, 0]]))
        camera.frame.assert_called()


def test_renderer_reraises_shader_creation_failure(scene_assets):
    context = MagicMock()
    camera = Camera()
    context.program.side_effect = RuntimeError("shader compile failed")
    with pytest.raises(RuntimeError, match="shader compile failed"):
        Renderer(context, camera, (320, 200), scene_assets)


def test_renderer_factory_injects_scene_assets(monkeypatch, scene_assets):
    context = Mock()
    renderer = Mock()
    monkeypatch.setattr(
        "scadview.render.renderer.moderngl.create_context", lambda: context
    )
    monkeypatch.setattr("scadview.render.renderer.Renderer", renderer)
    factory = RendererFactory(Camera(), scene_assets)

    result = factory.make((320, 200))

    assert result is renderer.return_value
    renderer.assert_called_once_with(context, factory._camera, (320, 200), scene_assets)


def test_loading_status_uses_injected_loading_asset(monkeypatch, scene_assets):
    context = MagicMock()
    camera = Camera()
    with patch("scadview.render.shader_program.isinstance") as mock_isinstance:
        mock_isinstance.return_value = True
        renderer = Renderer(context, camera, (320, 200), scene_assets)
        with patch("scadview.render.renderer.create_mesh_renderee") as create_renderee:
            renderer.indicate_load_status(LoadStatus.START)

    assert create_renderee.call_args.args[2] is scene_assets.loading_mesh


def test_axes_scale_from_the_injected_unscaled_base_asset(monkeypatch, scene_assets):
    context = MagicMock()
    camera = Camera()
    with patch("scadview.render.shader_program.isinstance") as mock_isinstance:
        mock_isinstance.return_value = True
        renderer = Renderer(context, camera, (320, 200), scene_assets)

    assert renderer._base_axes is scene_assets.base_axes
    with patch.object(renderer, "_create_axes_renderee") as create_axes:
        renderer.scale = 12.0

    create_axes.assert_called_once_with()
