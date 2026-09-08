import queue
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from trimesh.creation import box

from scadview.controller import Controller
from scadview.features import FeatureState
from scadview.mesh_loader_process import LoadMeshCommand, LoadResult
from scadview.module_loader import CreateMeshParameter


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
                generation=controller.current_generation,
            )
        )
        controller.check_load_queue()
        controller.set_feature_enabled("cutout", False)

        second_command = controller._command_queue.items.pop()
        assert isinstance(second_command, LoadMeshCommand)
        assert second_command.feature_states == {"cutout": False}
    finally:
        controller.close()


def test_controller_reconciles_parameters_and_reloads_with_values(monkeypatch):
    monkeypatch.setattr("scadview.controller.MpLoadQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MpCommandQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MeshLoaderProcess", DummyProcess)
    controller = Controller()
    try:
        controller.load_mesh("/tmp/model.py")
        controller._command_queue.items.clear()
        parameter = CreateMeshParameter("width", "float", 2.5)
        controller._load_queue.items.append(
            LoadResult(1, 1, box(), None, parameters=[parameter], generation=1)
        )
        controller.check_load_queue()

        controller.set_parameter_value("width", 3.5)

        command = controller._command_queue.items.pop()
        assert isinstance(command, LoadMeshCommand)
        assert command.parameter_values == {"width": 3.5}
    finally:
        controller.close()


def test_controller_ignores_stale_result(monkeypatch):
    monkeypatch.setattr("scadview.controller.MpLoadQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MpCommandQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MeshLoaderProcess", DummyProcess)
    controller = Controller()
    try:
        controller.load_mesh("/tmp/model.py")
        controller.load_mesh("/tmp/model.py")
        stale = LoadResult(1, 1, box(), None, generation=1)
        controller._load_queue.items.append(stale)

        result = controller.check_load_queue()

        assert result.mesh is None
        assert controller.current_mesh is None
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
        assert controller.set_debug_features(True) is True

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


def test_controller_debug_toggle_before_module_load_does_not_queue_reload(monkeypatch):
    monkeypatch.setattr("scadview.controller.MpLoadQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MpCommandQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MeshLoaderProcess", DummyProcess)
    controller = Controller()
    try:
        assert controller.set_debug_features(True) is False
        assert controller._command_queue.items == []
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


def test_parameter_value_change_does_not_rebuild_parameter_controls(monkeypatch):
    monkeypatch.setattr("scadview.controller.MpLoadQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MpCommandQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MeshLoaderProcess", DummyProcess)
    controller = Controller()
    try:
        parameter = CreateMeshParameter("width", "float", 2.5)
        controller._parameters = [parameter]
        controller._parameter_values = {"width": 2.5}
        on_parameters_change = Mock()
        controller.on_parameters_change.subscribe(on_parameters_change)

        controller.set_parameter_value("width", 3.5)

        on_parameters_change.notify.assert_not_called()
    finally:
        controller.close()


def test_controller_reset_parameter_values_restores_defaults_and_reloads(monkeypatch):
    monkeypatch.setattr("scadview.controller.MpLoadQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MpCommandQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MeshLoaderProcess", DummyProcess)
    controller = Controller()
    try:
        controller.load_mesh("/tmp/model.py")
        controller._command_queue.items.clear()
        parameters = [
            CreateMeshParameter("width", "float", 2.5),
            CreateMeshParameter("enabled", "bool", True),
        ]
        controller._load_queue.items.append(
            LoadResult(1, 1, box(), None, parameters=parameters, generation=1)
        )
        controller.check_load_queue()
        controller.set_parameter_value("width", 3.5)
        controller.set_parameter_value("enabled", False)
        controller._command_queue.items.clear()
        on_parameters_change = Mock()
        controller.on_parameters_change.subscribe(on_parameters_change)

        assert controller.reset_parameter_values() is True

        assert controller.parameter_values == {"width": 2.5, "enabled": True}
        on_parameters_change.assert_called_once_with(parameters)
        commands = controller._command_queue.items
        assert len(commands) == 1
        assert commands[0].parameter_values == {"width": 2.5, "enabled": True}
    finally:
        controller.close()


def test_controller_reset_parameter_values_is_noop_at_defaults(monkeypatch):
    monkeypatch.setattr("scadview.controller.MpLoadQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MpCommandQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MeshLoaderProcess", DummyProcess)
    controller = Controller()
    try:
        parameter = CreateMeshParameter("width", "float", 2.5)
        controller._parameters = [parameter]
        controller._parameter_values = {"width": 2.5}

        assert controller.reset_parameter_values() is False
        assert controller._command_queue.items == []
    finally:
        controller.close()
