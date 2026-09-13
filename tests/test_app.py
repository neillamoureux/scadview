from unittest.mock import Mock

from scadview import app


def test_app_composes_scene_assets_before_renderer_factory(monkeypatch):
    assets = Mock()
    camera = Mock()
    factory = Mock()
    adapter = Mock()
    ui = Mock()
    monkeypatch.setattr(app, "create_scene_assets", lambda: assets)
    monkeypatch.setattr(app, "CameraPerspective", lambda: camera)
    monkeypatch.setattr(app, "RendererFactory", factory)
    monkeypatch.setattr(app, "GlWidgetAdapter", lambda value: adapter)
    monkeypatch.setattr(app, "Controller", Mock)
    monkeypatch.setattr(app, "GlUi", lambda *args: ui)
    monkeypatch.setattr(app, "stop_splash_process", Mock())
    debug_info_service = Mock()

    app.main(Mock(), debug_info_service)

    factory.assert_called_once_with(camera, assets, debug_info_service)
    ui.run.assert_called_once_with()
