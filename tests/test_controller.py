import queue
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from trimesh.creation import box

from scadview.controller import Controller
from scadview.features import FeatureState
from scadview.mesh_loader_process import LoadMeshCommand, LoadResult


class DummyQueue:
    def __init__(self, *_, **__):
        self.items: list[object] = []

    def put(self, item: object, block: bool = True, timeout: float | None = None):
        self.items.append(item)

    def get_nowait(self) -> object:
        if not self.items:
            raise queue.Empty()
        return self.items.pop(0)

    def close(self):
        return None


class DummyProcess:
    def __init__(self, *_args, **_kwargs):
        self.started = False

    def start(self):
        self.started = True

    def join(self, timeout: float = 0.0):
        return None

    def is_alive(self) -> bool:
        return False

    def terminate(self):
        return None


def test_controller_reloads_with_updated_feature_state(monkeypatch):
    monkeypatch.setattr("scadview.controller.MpLoadQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MpCommandQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MeshLoaderProcess", DummyProcess)
    controller = Controller()

    try:
        model_path = str(Path("/tmp/model.py"))
        controller.load_mesh(model_path)
        first_command = controller._command_queue.items.pop()
        assert isinstance(first_command, LoadMeshCommand)
        assert first_command.feature_states == {}

        controller._load_queue.items.append(
            LoadResult(
                1,
                1,
                box(),
                None,
                False,
                [FeatureState("cutout", True)],
            )
        )
        controller.check_load_queue()
        controller.set_feature_enabled("cutout", False)

        second_command = controller._command_queue.items.pop()
        assert isinstance(second_command, LoadMeshCommand)
        assert second_command.feature_states == {"cutout": False}
    finally:
        controller.close()


def test_controller_reloads_with_session_persistent_feature_debug(monkeypatch):
    monkeypatch.setattr("scadview.controller.MpLoadQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MpCommandQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MeshLoaderProcess", DummyProcess)
    controller = Controller()

    try:
        first_path = str(Path("/tmp/first.py"))
        second_path = str(Path("/tmp/second.py"))
        controller.load_mesh(first_path)
        first_command = controller._command_queue.items.pop()
        assert isinstance(first_command, LoadMeshCommand)
        assert controller.debug_features is False
        assert first_command.debug_features is False

        controller.feature_states = [FeatureState("cutout", True)]
        controller.set_debug_features(True)

        debug_command = controller._command_queue.items.pop()
        assert isinstance(debug_command, LoadMeshCommand)
        assert controller.debug_features is True
        assert debug_command.debug_features is True
        assert debug_command.feature_states == {"cutout": True}
        assert controller.feature_states == [FeatureState("cutout", True)]

        controller.load_mesh(second_path)
        second_command = controller._command_queue.items.pop()
        assert isinstance(second_command, LoadMeshCommand)
        assert second_command.debug_features is True
    finally:
        controller.close()


def test_debug_features_toggle_starts_reload_polling():
    pytest.importorskip("wx")
    from scadview.ui.wx.main_frame import MainFrame

    controller = Mock()
    timer = Mock()
    gauge = Mock()
    event = Mock()
    event.IsChecked.return_value = True
    frame = SimpleNamespace(
        _controller=controller,
        _loader_timer=timer,
        _load_progress_gauge=gauge,
    )

    MainFrame._on_debug_features_toggle(frame, event)

    controller.set_debug_features.assert_called_once_with(True)
    timer.Start.assert_called_once()
    gauge.Pulse.assert_called_once()
