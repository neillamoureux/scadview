from unittest.mock import Mock

import pytest

from scadview import app


def test_app_composes_scene_assets_before_renderer_factory(monkeypatch):
    assets = Mock()
    camera = Mock()
    factory = Mock()
    adapter = Mock()
    ui = Mock()
    controller = Mock()
    monkeypatch.setattr(app, "create_scene_assets", lambda: assets)
    monkeypatch.setattr(app, "CameraPerspective", lambda: camera)
    monkeypatch.setattr(app, "RendererFactory", factory)
    monkeypatch.setattr(app, "GlWidgetAdapter", lambda value: adapter)
    monkeypatch.setattr(app, "Controller", Mock(return_value=controller))
    monkeypatch.setattr(app, "GlUi", lambda *args: ui)
    monkeypatch.setattr(app, "stop_splash_process", Mock())
    debug_info_service = Mock()

    app.main(Mock(), debug_info_service)

    factory.assert_called_once_with(camera, assets, debug_info_service)
    ui.run.assert_called_once_with()
    controller.close.assert_called_once_with()


@pytest.mark.parametrize("failure_point", ["renderer", "run"])
def test_app_closes_controller_when_startup_or_run_raises(monkeypatch, failure_point):
    controller = Mock()
    monkeypatch.setattr(app, "Controller", Mock(return_value=controller))
    monkeypatch.setattr(app, "create_scene_assets", Mock())
    monkeypatch.setattr(app, "CameraPerspective", Mock())
    monkeypatch.setattr(app, "stop_splash_process", Mock())
    if failure_point == "renderer":
        monkeypatch.setattr(
            app, "RendererFactory", Mock(side_effect=RuntimeError("startup"))
        )
    else:
        monkeypatch.setattr(app, "RendererFactory", Mock())
        monkeypatch.setattr(app, "GlWidgetAdapter", Mock())
        monkeypatch.setattr(
            app,
            "GlUi",
            Mock(return_value=Mock(run=Mock(side_effect=RuntimeError("run")))),
        )

    with pytest.raises(RuntimeError):
        app.main(Mock(), Mock())

    controller.close.assert_called_once_with()
