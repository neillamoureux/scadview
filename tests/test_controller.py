import gc
import queue
import weakref
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from trimesh.creation import box

from scadview.controller import Controller
from scadview.features import FeatureState
from scadview.load_status import LoadStatus
from scadview.mesh_loader_process import LoadMeshCommand, LoadResult
from scadview.mesh_payload import MeshPayload, mesh_to_payload
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


class ExportMesh:
    def __init__(self, error: OSError | None = None):
        self.error = error
        self.paths: list[str] = []

    def export(self, path: str):
        if self.error is not None:
            raise self.error
        self.paths.append(path)


def _controller(monkeypatch):
    monkeypatch.setattr("scadview.controller.MpLoadQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MpCommandQueue", DummyQueue)
    monkeypatch.setattr("scadview.controller.MeshLoaderProcess", DummyProcess)
    return Controller()


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

        payload = mesh_to_payload(box())
        controller._load_queue.items.append(
            LoadResult(
                1,
                1,
                payload,
                None,
                False,
                [FeatureState("cutout", True)],
                generation=controller.current_generation,
            )
        )
        controller.check_load_queue()
        assert controller.current_mesh is payload
        assert isinstance(controller.current_mesh, MeshPayload)
        controller.set_feature_enabled("cutout", False)

        second_command = controller._command_queue.items.pop()
        assert isinstance(second_command, LoadMeshCommand)
        assert second_command.feature_states == {"cutout": False}
    finally:
        controller.close()


def test_controller_retains_only_current_completed_single_payload(monkeypatch):
    controller = _controller(monkeypatch)
    payload = mesh_to_payload(box())
    try:
        controller.load_mesh("/tmp/model.py")
        controller._load_queue.items.append(
            LoadResult(1, 1, payload, None, complete=True, generation=1)
        )

        controller.check_load_queue()

        assert controller.current_mesh is payload
        assert controller.exportable_payload is payload
    finally:
        controller.close()


def test_controller_rejects_stale_payload_without_replacing_current_payload(
    monkeypatch,
):
    controller = _controller(monkeypatch)
    current_payload = mesh_to_payload(box())
    stale_payload = mesh_to_payload(box(extents=(2, 2, 2)))
    try:
        controller.current_mesh = current_payload
        controller._current_generation = 2
        controller._load_queue.items.append(
            LoadResult(1, 1, stale_payload, None, complete=True, generation=1)
        )

        controller.check_load_queue()

        assert controller.current_mesh is current_payload
        assert controller.exportable_payload is None
    finally:
        controller.close()


def test_controller_does_not_export_debug_payload_lists(monkeypatch):
    controller = _controller(monkeypatch)
    try:
        controller.current_mesh = [mesh_to_payload(box())]
        controller.load_status = LoadStatus.DEBUG

        controller.export("/tmp/model.stl")

        assert controller.exportable_payload is None
        assert controller._last_export_path == ""
    finally:
        controller.close()


def test_controller_exports_payload_geometry_and_scadview_color(monkeypatch):
    controller = _controller(monkeypatch)
    source = box()
    source.metadata["scadview"] = {"color": [0.2, 0.4, 0.6, 0.8]}
    payload = mesh_to_payload(source)
    exported: list[object] = []

    def capture_export(mesh, path):
        exported.extend((mesh, path))

    monkeypatch.setattr("trimesh.Trimesh.export", capture_export)
    try:
        controller.current_mesh = payload
        controller.load_status = LoadStatus.COMPLETE

        controller.export("/tmp/model.stl")

        export_mesh, export_path = exported
        assert export_path == "/tmp/model.stl"
        assert isinstance(export_mesh, type(source))
        assert export_mesh.metadata["scadview"]["color"] == [0.2, 0.4, 0.6, 0.8]
        assert export_mesh.vertices.tolist() == source.vertices.tolist()
        assert export_mesh.faces.tolist() == source.faces.tolist()
    finally:
        controller.close()


@pytest.mark.parametrize("suffix", ["stl", "ply"])
def test_controller_dispatches_supported_export_formats(monkeypatch, suffix):
    controller = _controller(monkeypatch)
    export_mesh = ExportMesh()
    monkeypatch.setattr("scadview.controller.payload_to_trimesh", lambda _: export_mesh)
    try:
        controller.current_mesh = mesh_to_payload(box())
        controller.load_status = LoadStatus.COMPLETE

        controller.export(f"/tmp/model.{suffix}")

        assert export_mesh.paths == [f"/tmp/model.{suffix}"]
    finally:
        controller.close()


def test_controller_releases_temporary_export_mesh_after_dispatch(monkeypatch):
    controller = _controller(monkeypatch)
    reference: list[weakref.ReferenceType[ExportMesh]] = []

    def make_export_mesh(_):
        export_mesh = ExportMesh()
        reference.append(weakref.ref(export_mesh))
        return export_mesh

    monkeypatch.setattr("scadview.controller.payload_to_trimesh", make_export_mesh)
    try:
        controller.current_mesh = mesh_to_payload(box())
        controller.load_status = LoadStatus.COMPLETE

        controller.export("/tmp/model.stl")
        gc.collect()

        assert reference[0]() is None
        assert controller.current_mesh is not None
    finally:
        controller.close()


def test_controller_propagates_exporter_errors(monkeypatch):
    controller = _controller(monkeypatch)
    export_mesh = ExportMesh(OSError("disk full"))
    monkeypatch.setattr("scadview.controller.payload_to_trimesh", lambda _: export_mesh)
    try:
        controller.current_mesh = mesh_to_payload(box())
        controller.load_status = LoadStatus.COMPLETE

        with pytest.raises(OSError, match="disk full"):
            controller.export("/tmp/model.stl")
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
            LoadResult(
                1,
                1,
                mesh_to_payload(box()),
                None,
                parameters=[parameter],
                generation=1,
            )
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
        stale = LoadResult(1, 1, mesh_to_payload(box()), None, generation=1)
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
            LoadResult(
                1,
                1,
                mesh_to_payload(box()),
                None,
                parameters=parameters,
                generation=1,
            )
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
