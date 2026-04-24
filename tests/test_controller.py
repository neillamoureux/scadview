import queue
from pathlib import Path

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
