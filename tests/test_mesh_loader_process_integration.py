import logging
import multiprocessing as mp
import os
import queue
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from time import monotonic, sleep
from typing import Any

from trimesh import Trimesh

from scadview.controller import Controller
from scadview.features import FeatureState
from scadview.mesh_loader_process import (
    Command,
    ExportCommand,
    ExportResult,
    LoadError,
    LoadMeshCommand,
    LoadPhase,
    LoadResult,
    MeshLoaderProcess,
    MpCommandQueue,
    MpExportResultQueue,
    MpLoadQueue,
    ShutDownCommand,
)
from scadview.mesh_payload import MeshPayload

TIMEOUT_SECONDS = 5.0


@dataclass
class LoaderHarness:
    process: MeshLoaderProcess
    command_queue: MpCommandQueue
    load_queue: MpLoadQueue
    export_result_queue: MpExportResultQueue
    log_queue: Any


def test_real_loader_process_preserves_payload_export_reload_and_shutdown(tmp_path):
    load_release = tmp_path / "load-release"
    export_started = tmp_path / "export-started"
    export_release = tmp_path / "export-release"
    module_path = _write_reloadable_module(
        tmp_path,
        load_release,
        export_started,
        export_release,
    )
    harness = _start_loader_process()
    export_path = tmp_path / "source.ply"

    try:
        assert harness.process.pid not in (None, os.getpid())
        first_progress, first_final = _complete_load(
            harness, module_path, load_release, generation=1
        )
        _assert_payload_only(first_progress, first_final)

        harness.command_queue.put(ExportCommand(17, 1, str(export_path)))
        _wait_for_path(export_started)
        assert export_started.read_text(encoding="utf-8") == "retained"
        load_release.unlink()
        harness.command_queue.put(LoadMeshCommand(str(module_path), generation=2))
        second_progress = _get_load_result(harness.load_queue, 2, LoadPhase.PROGRESS)

        export_release.touch()
        export_result = harness.export_result_queue.get(timeout=TIMEOUT_SECONDS)
        assert export_result == ExportResult(17, 1)
        assert export_path.exists()

        load_release.touch()
        second_final = _get_load_result(harness.load_queue, 2, LoadPhase.FINAL)
        _assert_payload_only(second_progress, second_final)
        _shutdown_cleanly(harness)
    finally:
        _close_harness(harness)


def _write_reloadable_module(
    tmp_path: Path,
    load_release: Path,
    export_started: Path,
    export_release: Path,
) -> Path:
    module_path = tmp_path / "reloadable_mesh.py"
    module_path.write_text(
        f"""
from copy import deepcopy
from pathlib import Path
from time import monotonic, sleep

import numpy as np
from trimesh import Trimesh

LOAD_RELEASE = Path({str(load_release)!r})
EXPORT_STARTED = Path({str(export_started)!r})
EXPORT_RELEASE = Path({str(export_release)!r})


class BlockingExportMesh(Trimesh):
    def copy(self, include_cache=False, include_visual=True):
        return type(self)(
            vertices=self.vertices.copy(),
            faces=self.faces.copy(),
            face_normals=self.face_normals.copy(),
            visual=self.visual.copy() if include_visual else None,
            metadata=deepcopy(self.metadata),
            process=False,
        )

    def export(self, file_obj=None, file_type=None, **kwargs):
        EXPORT_STARTED.write_text(
            self.metadata["integration-source"], encoding="utf-8"
        )
        deadline = monotonic() + {TIMEOUT_SECONDS!r}
        while not EXPORT_RELEASE.exists():
            if monotonic() >= deadline:
                raise TimeoutError("timed out waiting to release export")
            sleep(0.01)
        return super().export(file_obj=file_obj, file_type=file_type, **kwargs)


def create_mesh():
    mesh = BlockingExportMesh(
        vertices=np.array(
            [[0.125, 0.0, 0.0], [1.0, 0.25, 0.0], [0.0, 1.0, 0.5]],
            dtype=np.float64,
        ),
        faces=np.array([[0, 1, 2]], dtype=np.int64),
        process=False,
    )
    mesh.metadata["integration-source"] = "retained"
    yield mesh
    deadline = monotonic() + {TIMEOUT_SECONDS!r}
    while not LOAD_RELEASE.exists():
        if monotonic() >= deadline:
            raise TimeoutError("timed out waiting to finalize load")
        sleep(0.01)
""".lstrip(),
        encoding="utf-8",
    )
    return module_path


def _start_loader_process() -> LoaderHarness:
    command_queue = MpCommandQueue(maxsize=0, type_=Command)
    load_queue = MpLoadQueue(maxsize=1, type_=LoadResult)
    export_result_queue = MpExportResultQueue(maxsize=0, type_=ExportResult)
    log_queue = mp.Queue(maxsize=100)
    process = MeshLoaderProcess(
        command_queue,
        load_queue,
        export_result_queue,
        log_queue,
        logging.CRITICAL,
    )
    process.start()
    return LoaderHarness(
        process,
        command_queue,
        load_queue,
        export_result_queue,
        log_queue,
    )


def _complete_load(
    harness: LoaderHarness,
    module_path: Path,
    load_release: Path,
    generation: int,
) -> tuple[LoadResult, LoadResult]:
    harness.command_queue.put(LoadMeshCommand(str(module_path), generation=generation))
    progress = _get_load_result(harness.load_queue, generation, LoadPhase.PROGRESS)
    load_release.touch()
    final = _get_load_result(harness.load_queue, generation, LoadPhase.FINAL)
    return progress, final


def _get_load_result(
    load_queue: MpLoadQueue,
    generation: int,
    phase: LoadPhase,
) -> LoadResult:
    deadline = monotonic() + TIMEOUT_SECONDS
    while True:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise AssertionError(
                f"Timed out waiting for generation {generation} {phase.value}"
            )
        try:
            result = load_queue.get(timeout=remaining)
        except queue.Empty:
            raise AssertionError(
                f"Timed out waiting for generation {generation} {phase.value}"
            )
        if result.generation == generation and result.phase is phase:
            return result


def _assert_payload_only(progress: LoadResult, final: LoadResult) -> None:
    assert progress.phase is LoadPhase.PROGRESS
    assert isinstance(progress.payload, MeshPayload)
    assert not progress.exportable
    assert final.phase is LoadPhase.FINAL
    assert isinstance(final.payload, MeshPayload)
    assert final.exportable
    assert final.revision > progress.revision
    assert not _contains_trimesh(progress)
    assert not _contains_trimesh(final)


def _contains_trimesh(value: Any) -> bool:
    if isinstance(value, Trimesh):
        return True
    if is_dataclass(value) and not isinstance(value, type):
        return any(
            _contains_trimesh(getattr(value, field.name)) for field in fields(value)
        )
    if isinstance(value, dict):
        return any(_contains_trimesh(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_trimesh(item) for item in value)
    return False


def _wait_for_path(path: Path) -> None:
    deadline = monotonic() + TIMEOUT_SECONDS
    while monotonic() < deadline:
        if path.exists():
            return
        sleep(0.01)
    raise AssertionError(f"Timed out waiting for {path.name}")


def _shutdown_cleanly(harness: LoaderHarness) -> None:
    harness.command_queue.put(ShutDownCommand())
    harness.process.join(timeout=TIMEOUT_SECONDS)
    assert not harness.process.is_alive()
    assert harness.process.exitcode == 0


def _close_harness(harness: LoaderHarness) -> None:
    if harness.process.is_alive():
        harness.process.terminate()
        harness.process.join(timeout=TIMEOUT_SECONDS)
    harness.command_queue.close(discard=True)
    harness.load_queue.close(discard=True)
    harness.export_result_queue.close(discard=True)
    harness.log_queue.cancel_join_thread()
    harness.log_queue.close()


def test_overlapping_real_loads_isolate_feature_state_and_debug_sources(tmp_path):
    first_started = tmp_path / "first-started"
    first_release = tmp_path / "first-release"
    second_started = tmp_path / "second-started"
    second_release = tmp_path / "second-release"
    module_path = _write_overlapping_feature_module(
        tmp_path,
        first_started,
        first_release,
        second_started,
        second_release,
    )
    harness = _start_loader_process()

    try:
        harness.command_queue.put(
            LoadMeshCommand(
                str(module_path),
                feature_states={"old": False},
                debug_features=True,
                parameter_values={"run": 1},
                generation=1,
            )
        )
        _wait_for_path(first_started)

        harness.command_queue.put(
            LoadMeshCommand(
                str(module_path),
                feature_states={"before": True, "after": False},
                debug_features=True,
                parameter_values={"run": 2},
                generation=2,
            )
        )
        _wait_for_path(second_started)

        first_release.touch()
        cancelled = _get_load_result(harness.load_queue, 1, LoadPhase.CANCELLED)
        assert cancelled.generation == 1

        second_release.touch()
        final = _get_load_result(harness.load_queue, 2, LoadPhase.FINAL)

        assert final.features == [
            FeatureState("before", True),
            FeatureState("after", False),
        ]
        assert final.debug
        assert not final.exportable
        assert isinstance(final.payload, list)
        assert len(final.payload) == 1
        assert final.payload[0].vertices[0, 0] == 10.0
        _shutdown_cleanly(harness)
    finally:
        _close_harness(harness)


def _write_overlapping_feature_module(
    tmp_path: Path,
    first_started: Path,
    first_release: Path,
    second_started: Path,
    second_release: Path,
) -> Path:
    module_path = tmp_path / "overlapping_feature_mesh.py"
    module_path.write_text(
        f"""
from pathlib import Path
from time import monotonic, sleep

import numpy as np
from trimesh import Trimesh

from scadview import feature

FIRST_STARTED = Path({str(first_started)!r})
FIRST_RELEASE = Path({str(first_release)!r})
SECOND_STARTED = Path({str(second_started)!r})
SECOND_RELEASE = Path({str(second_release)!r})


def create_mesh(run=0):
    if run == 1:
        feature("old", _triangle(1.0))
        FIRST_STARTED.touch()
        _wait_for(FIRST_RELEASE)
        return _triangle(2.0)

    feature("before", _triangle(10.0))
    SECOND_STARTED.touch()
    _wait_for(SECOND_RELEASE)
    feature("after", _triangle(20.0))
    return _triangle(30.0)


def _triangle(offset):
    return Trimesh(
        vertices=np.array(
            [
                [offset, 0.0, 0.0],
                [offset + 1.0, 0.0, 0.0],
                [offset, 1.0, 0.0],
            ],
            dtype=np.float64,
        ),
        faces=np.array([[0, 1, 2]], dtype=np.int64),
        process=False,
    )


def _wait_for(path):
    deadline = monotonic() + {TIMEOUT_SECONDS!r}
    while not path.exists():
        if monotonic() >= deadline:
            raise TimeoutError(f"timed out waiting for {{path.name}}")
        sleep(0.01)
""".lstrip(),
        encoding="utf-8",
    )
    return module_path


def test_controller_translates_forced_real_loader_death_once(tmp_path):
    started_path = tmp_path / "load-started"
    module_path = _write_blocking_module(tmp_path, started_path)
    controller = Controller()

    try:
        controller.load_mesh(str(module_path))
        _wait_for_path(started_path)
        controller._loader_process.terminate()
        controller._loader_process.join(timeout=TIMEOUT_SECONDS)
        assert not controller._loader_process.is_alive()

        result = controller.check_load_queue()
        assert result.phase is LoadPhase.ERROR
        assert result.generation == controller.current_generation
        assert result.error == LoadError(
            "LoaderProcessDied", "Mesh loader process exited"
        )

        repeated = controller.check_load_queue()
        assert repeated.phase is LoadPhase.CANCELLED
    finally:
        controller.close(timeout=TIMEOUT_SECONDS)


def _write_blocking_module(tmp_path: Path, started_path: Path) -> Path:
    module_path = tmp_path / "blocking_mesh.py"
    module_path.write_text(
        f"""
from pathlib import Path
from time import sleep

STARTED = Path({str(started_path)!r})


def create_mesh():
    STARTED.touch()
    while True:
        sleep(0.01)
""".lstrip(),
        encoding="utf-8",
    )
    return module_path
