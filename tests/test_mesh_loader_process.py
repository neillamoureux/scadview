import gc
import logging
import queue
import weakref
from dataclasses import FrozenInstanceError
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

import manifold3d
import numpy as np
import numpy.testing as npt
import pytest
from trimesh import Trimesh
from trimesh.creation import box, icosphere

from scadview.features import FeatureState, feature
from scadview.mesh_loader_process import (
    CreateMeshParameter,
    ExportCommand,
    ExportError,
    ExportResult,
    ExportWorker,
    LoadError,
    LoadEventChannel,
    LoadMeshCommand,
    LoadPhase,
    LoadResult,
    LoadResultEvent,
    LoadStatus,
    LoadWorker,
    MeshLoaderProcess,
    MpQueue,
    ShutDownCommand,
    _export_result_at_protocol_boundary,
)
from scadview.mesh_payload import MeshPayload, mesh_to_payload


@pytest.fixture
def mock_queue():
    with patch("scadview.mesh_loader_process.Queue") as mock_cls:
        yield mock_cls


@pytest.fixture
def mp_queue_int():
    yield MpQueue[int](maxsize=10, type_=int)


def test_mp_queue_init(mock_queue):
    MpQueue[int](maxsize=10, type_=int)
    mock_queue.assert_called_once_with(maxsize=10)


def test_mp_queue_put_correct_type(mock_queue, mp_queue_int):
    mp_queue_int.put(42)
    mock_queue.return_value.put.assert_called_with(42, block=True, timeout=None)


def test_mp_queue_put_wrong_type(mp_queue_int):
    with pytest.raises(ValueError):
        mp_queue_int.put(10.3)


def test_mp_queue_put_nowait(mock_queue, mp_queue_int):
    mp_queue_int.put_nowait(55)
    mock_queue.return_value.put.assert_called_once_with(55, block=False, timeout=None)


def test_mp_queue_put_nowait_wrong_type(mp_queue_int):
    with pytest.raises(ValueError):
        mp_queue_int = MpQueue[int](maxsize=10, type_=int)
        mp_queue_int.put_nowait(10.3)


def test_mp_queue_get_correct_type(mock_queue, mp_queue_int):
    q = mock_queue.return_value
    q.get.return_value = 43
    assert mp_queue_int.get() == 43


def test_mp_queue_get_wrong_type(mock_queue, mp_queue_int):
    q = mock_queue.return_value
    q.get.return_value = 43.3
    with pytest.raises(ValueError):
        mp_queue_int.get()


def test_mp_queue_get_nowait(mock_queue, mp_queue_int):
    q = mock_queue.return_value
    q.get.return_value = 43
    mp_queue_int.get_nowait()
    q.get.assert_called_once_with(block=False, timeout=None)


def test_mp_queue_get_nowait_wrong_type(mock_queue, mp_queue_int):
    q = mock_queue.return_value
    q.get.return_value = 43.3
    with pytest.raises(ValueError):
        mp_queue_int.get_nowait()


def test_mp_queue_close(mock_queue, mp_queue_int):
    mp_queue_int.close()
    mock_queue.return_value.close.assert_called_once_with()


def test_mp_queue_close_discards_pending_items(mock_queue, mp_queue_int):
    mp_queue_int.close(discard=True)

    mock_queue.return_value.cancel_join_thread.assert_called_once_with()
    mock_queue.return_value.close.assert_called_once_with()
    mock_queue.return_value.join_thread.assert_not_called()


def test_load_result_preserves_explicit_debug_state():
    mesh = mesh_to_payload(box())
    lr = LoadResult(
        1,
        2,
        [mesh],
        None,
        phase=LoadPhase.FINAL,
        revision=1,
        exportable=False,
        debug=True,
    )
    assert lr.debug
    lr = LoadResult(
        1,
        2,
        mesh,
        None,
        phase=LoadPhase.FINAL,
        revision=1,
        exportable=True,
        debug=False,
    )
    assert not lr.debug


def test_load_result_nested_state_is_immutable():
    payload = mesh_to_payload(box())
    features = [FeatureState("cutout", True)]
    parameters = [CreateMeshParameter("width", "float", 2.5)]
    error = LoadError("RuntimeError", "failed")
    result = LoadResult(
        1,
        1,
        [payload],
        error,
        features=features,
        parameters=parameters,
        phase=LoadPhase.ERROR,
        revision=1,
        exportable=False,
        debug=True,
    )

    features.append(FeatureState("other", False))
    parameters[0] = CreateMeshParameter("height", "float", 1.0)
    assert len(result.features) == 1
    assert result.parameters[0].name == "width"
    with pytest.raises(TypeError):
        result.payload.append(payload)
    with pytest.raises(TypeError):
        result.features[0] = FeatureState("other", False)
    with pytest.raises(FrozenInstanceError):
        result.error.message = "changed"


def test_load_result_status():
    mesh = mesh_to_payload(box())
    lr = LoadResult(
        1,
        2,
        mesh,
        LoadError("RuntimeError", "failed"),
        phase=LoadPhase.ERROR,
        revision=1,
        exportable=False,
        debug=False,
    )
    assert lr.status == LoadStatus.ERROR
    lr = LoadResult(
        1,
        2,
        [mesh],
        None,
        phase=LoadPhase.FINAL,
        revision=1,
        exportable=False,
        debug=True,
    )
    assert lr.status == LoadStatus.DEBUG
    lr = LoadResult(
        1,
        2,
        mesh,
        None,
        phase=LoadPhase.FINAL,
        revision=1,
        exportable=True,
        debug=False,
    )
    assert lr.status == LoadStatus.COMPLETE
    lr = LoadResult(
        1,
        2,
        mesh,
        None,
        phase=LoadPhase.PROGRESS,
        revision=1,
        exportable=False,
        debug=False,
    )
    assert lr.status == LoadStatus.START
    lr = LoadResult(
        1,
        2,
        None,
        None,
        phase=LoadPhase.PROGRESS,
        revision=1,
        exportable=False,
        debug=False,
    )
    assert lr.status == LoadStatus.START
    lr = LoadResult(
        1,
        2,
        None,
        None,
        phase=LoadPhase.CANCELLED,
        revision=1,
        exportable=False,
        debug=False,
    )
    assert lr.status == LoadStatus.CANCELLED


def test_load_result_exposes_explicit_phase_revision_and_exportability():
    payload = mesh_to_payload(box())

    progress = LoadResult(
        1,
        1,
        payload=payload,
        error=None,
        generation=4,
        revision=7,
        phase=LoadPhase.PROGRESS,
        exportable=False,
        debug=False,
    )
    final = LoadResult(
        1,
        1,
        payload=payload,
        error=None,
        generation=4,
        revision=8,
        phase=LoadPhase.FINAL,
        exportable=True,
        debug=False,
    )
    error = LoadResult(
        1,
        1,
        payload=None,
        error=LoadError("ValueError", "invalid mesh"),
        generation=4,
        revision=9,
        phase=LoadPhase.ERROR,
        exportable=False,
        debug=False,
    )
    cancelled = LoadResult(
        1,
        1,
        payload=None,
        error=None,
        generation=4,
        revision=10,
        phase=LoadPhase.CANCELLED,
        exportable=False,
        debug=False,
    )

    assert progress.phase is LoadPhase.PROGRESS
    assert final.phase is LoadPhase.FINAL
    assert final.exportable
    assert error.phase is LoadPhase.ERROR
    assert error.error == LoadError("ValueError", "invalid mesh")
    assert cancelled.phase is LoadPhase.CANCELLED
    assert [progress.revision, final.revision, error.revision, cancelled.revision] == [
        7,
        8,
        9,
        10,
    ]


def test_load_result_requires_explicit_state_fields():
    payload = mesh_to_payload(box())

    with pytest.raises(TypeError):
        LoadResult(1, 1, payload, None)


def test_load_result_completion_is_derived_from_phase():
    payload = mesh_to_payload(box())
    progress = LoadResult(
        1,
        1,
        payload,
        None,
        phase=LoadPhase.PROGRESS,
        revision=1,
        exportable=False,
        debug=False,
    )
    final = LoadResult(
        1,
        1,
        payload,
        None,
        phase=LoadPhase.FINAL,
        revision=2,
        exportable=True,
        debug=False,
    )

    assert not progress.complete
    assert final.complete
    with pytest.raises(AttributeError):
        setattr(final, "complete", False)


def test_load_result_has_one_immutable_explicit_payload_surface():
    result = LoadResult(
        1,
        1,
        payload=mesh_to_payload(box()),
        error=None,
        phase=LoadPhase.FINAL,
        revision=1,
        exportable=True,
        debug=False,
    )

    assert "CANCELLATION" not in LoadPhase.__members__
    assert not hasattr(result, "mesh")
    with pytest.raises(FrozenInstanceError):
        setattr(result, "payload", None)


@pytest.mark.parametrize(
    ("phase", "payload_kind", "error", "exportable", "debug"),
    [
        (LoadPhase.ERROR, "none", None, False, False),
        (LoadPhase.ERROR, "none", "failed", False, False),
        (
            LoadPhase.FINAL,
            "single",
            LoadError("ValueError", "failed"),
            False,
            False,
        ),
        (LoadPhase.PROGRESS, "single", None, True, False),
        (LoadPhase.CANCELLED, "single", None, True, False),
        (LoadPhase.FINAL, "list", None, True, True),
        (LoadPhase.FINAL, "single", None, False, False),
        (LoadPhase.FINAL, "single", None, False, True),
        (LoadPhase.FINAL, "list", None, False, False),
    ],
)
def test_load_result_rejects_inconsistent_state(
    phase, payload_kind, error, exportable, debug
):
    payload = mesh_to_payload(box())
    payload_by_kind = {"none": None, "single": payload, "list": [payload]}

    with pytest.raises(ValueError):
        LoadResult(
            1,
            1,
            payload_by_kind[payload_kind],
            error,
            phase=phase,
            revision=1,
            exportable=exportable,
            debug=debug,
        )


@pytest.mark.parametrize(
    ("phase", "error"),
    [
        (LoadPhase.ERROR, LoadError("RuntimeError", "failed")),
        (LoadPhase.CANCELLED, None),
    ],
)
def test_terminal_result_can_retain_nonexportable_prior_display_payload(
    phase,
    error,
):
    payload = mesh_to_payload(box())

    result = LoadResult(
        1,
        1,
        payload,
        error,
        phase=phase,
        revision=1,
        exportable=False,
        debug=False,
    )

    assert result.payload is payload
    assert not result.exportable


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("phase", None),
        ("revision", -1),
        ("revision", True),
        ("exportable", None),
        ("debug", None),
    ],
)
def test_load_result_rejects_invalid_explicit_state_field(field, value):
    state = {
        "phase": LoadPhase.PROGRESS,
        "revision": 1,
        "exportable": False,
        "debug": False,
    }
    state[field] = value

    with pytest.raises(ValueError):
        LoadResult(1, 1, None, None, **state)


def test_load_mesh_command_preserves_debug_features():
    command = LoadMeshCommand("test/path", debug_features=True)

    assert command.debug_features is True


def test_load_mesh_command_preserves_parameter_values_and_generation():
    command = LoadMeshCommand("test/path", {"cutout": False}, True, {"width": 3.5}, 4)

    assert command.parameter_values == {"width": 3.5}
    assert command.generation == 4


def test_load_worker_reports_parameters_and_generation(load_queue):
    parameters = [CreateMeshParameter("width", "float", 2.5)]
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        loader = mock_module_loader.return_value
        loader.parameters = parameters
        loader.run_function.return_value = iter([box()])
        worker = LoadWorker(
            "test/path",
            load_queue,
            parameter_values={"width": 3.5},
            generation=4,
        )
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)
    assert result.parameters == parameters
    assert result.generation == 4
    loader.run_function.assert_called_once_with("test/path", {"width": 3.5})


def test_load_worker_reports_parameters_when_execution_fails(load_queue):
    parameters = [CreateMeshParameter("width", "float", 2.5)]
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        loader = mock_module_loader.return_value
        loader.parameters = parameters
        loader.run_function.return_value = _raise_mesh_error()
        worker = LoadWorker("test/path", load_queue, generation=4)
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)
    assert result.error is not None
    assert result.parameters == parameters
    assert result.generation == 4


def test_load_worker_retains_only_the_final_successful_single_source(load_queue):
    first = box()
    final = icosphere()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        loader = mock_module_loader.return_value
        loader.run_function.return_value = iter([first, final])
        worker = LoadWorker("test/path", load_queue, generation=4)
        worker.load()

    assert worker.export_source is final


def test_load_worker_scalar_final_snapshot_is_atomic():
    publication_queue = LoadEventChannel(maxsize=10)
    source = box()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        loader = mock_module_loader.return_value
        loader.run_function.return_value = iter([source])
        with patch("scadview.mesh_loader_process.mesh_to_payload") as to_payload:
            to_payload.return_value = mesh_to_payload(source)
            worker = LoadWorker("test/path", publication_queue)
            worker.load()

    assert to_payload.call_count == 1
    first_result = publication_queue.get(timeout=1.0)
    final_result = publication_queue.get(timeout=1.0)
    _assert_payload_geometry(first_result.payload, source)
    _assert_payload_geometry(final_result.payload, source)
    assert first_result.phase is LoadPhase.PROGRESS
    assert final_result.phase is LoadPhase.FINAL
    assert final_result.exportable
    assert final_result.revision != first_result.revision
    assert worker.final_snapshot is not None
    assert worker.final_snapshot.source is source
    assert worker.final_snapshot.payload is final_result.payload


def test_load_worker_reuses_the_last_payload_for_the_final_error_result(load_queue):
    source = box()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        loader = mock_module_loader.return_value
        loader.run_function.return_value = _yield_then_raise(source)
        with patch("scadview.mesh_loader_process.mesh_to_payload") as to_payload:
            to_payload.return_value = mesh_to_payload(source)
            worker = LoadWorker("test/path", load_queue)
            worker.load()

    assert to_payload.call_count == 1
    load_queue.get(timeout=1.0)
    final_result = load_queue.get(timeout=1.0)
    _assert_payload_geometry(final_result.payload, source)
    assert final_result.error is not None
    assert final_result.error.type_name == "RuntimeError"
    assert final_result.phase is LoadPhase.ERROR
    assert not final_result.exportable


def test_load_worker_invalidates_export_source_for_debug_and_errors(load_queue):
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        loader = mock_module_loader.return_value
        loader.run_function.return_value = _raise_mesh_error()
        worker = LoadWorker("test/path", load_queue, generation=4)
        worker.load()

    assert worker.export_source is None


def test_load_worker_refreshes_final_payload_after_generator_mutates_source():
    publication_queue = LoadEventChannel(maxsize=10)
    source = box()
    initial_vertices = source.vertices.copy()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        loader = mock_module_loader.return_value
        loader.run_function.return_value = _mutate_after_last_yield(source)
        worker = LoadWorker("test/path", publication_queue)
        worker.load()

    first_result = publication_queue.get(timeout=1.0)
    final_result = publication_queue.get(timeout=1.0)
    assert isinstance(final_result.payload, MeshPayload)
    assert final_result.payload.color.tolist() == [32, 61, 92, 122]
    npt.assert_allclose(final_result.payload.vertices, source.vertices)
    assert worker.export_source is source
    assert worker.export_source.metadata == source.metadata
    assert worker.final_snapshot is not None
    assert worker.final_snapshot.source is source
    assert worker.final_snapshot.payload is final_result.payload
    assert final_result.exportable
    npt.assert_array_equal(
        worker.final_snapshot.payload.vertices, final_result.payload.vertices
    )
    npt.assert_array_equal(
        worker.final_snapshot.payload.color, final_result.payload.color
    )
    npt.assert_allclose(first_result.payload.vertices, initial_vertices)
    npt.assert_raises(
        AssertionError,
        npt.assert_allclose,
        first_result.payload.vertices,
        source.vertices,
    )


@pytest.mark.parametrize(
    ("mutate_source", "changed_payload_field"),
    [
        pytest.param(
            lambda mesh: mesh.vertices.__setitem__((0, 0), 9.125),
            "vertices",
            id="vertices",
        ),
        pytest.param(lambda mesh: _rotate_first_face(mesh), "faces", id="faces"),
        pytest.param(
            lambda mesh: _set_valid_face_normal(mesh),
            "face_normals",
            id="face-normals",
        ),
        pytest.param(
            lambda mesh: mesh.metadata.__setitem__(
                "scadview", {"color": [0.125, 0.24, 0.36, 0.48]}
            ),
            "color",
            id="color-metadata",
        ),
    ],
)
def test_load_worker_refreshes_final_list_payload_after_generator_mutation(
    load_queue,
    mutate_source,
    changed_payload_field,
):
    sources = [box(), box(extents=(2.0, 3.0, 4.0))]
    for source in sources:
        source.metadata["scadview"] = {"color": [0.2, 0.3, 0.4, 0.5]}
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        loader = mock_module_loader.return_value
        loader.run_function.return_value = _mutate_list_source_after_yield(
            sources, mutate_source
        )
        worker = LoadWorker("test/path", load_queue, generation=7)
        worker.load()

    progress = load_queue.get(timeout=1.0)
    final = load_queue.get(timeout=1.0)
    assert isinstance(progress.payload, list)
    assert isinstance(final.payload, list)
    expected = [mesh_to_payload(source) for source in sources]
    for final_payload, expected_payload in zip(final.payload, expected):
        npt.assert_allclose(final_payload.vertices, expected_payload.vertices)
        npt.assert_array_equal(final_payload.faces, expected_payload.faces)
        npt.assert_allclose(final_payload.face_normals, expected_payload.face_normals)
        npt.assert_array_equal(final_payload.color, expected_payload.color)
    assert not np.array_equal(
        getattr(progress.payload[1], changed_payload_field),
        getattr(final.payload[1], changed_payload_field),
    )
    assert final.phase is LoadPhase.FINAL
    assert final.revision != progress.revision
    assert final.debug
    assert not final.exportable
    assert worker.final_snapshot is None
    assert worker.export_source is None


@pytest.mark.parametrize(
    ("mutate_source", "error_type"),
    [
        pytest.param(
            lambda mesh: mesh.vertices.__setitem__((0, 0), 1e40),
            "ValueError",
            id="vertex",
        ),
        pytest.param(
            lambda mesh: mesh.faces.__setitem__((0, 0), len(mesh.vertices)),
            "IndexError",
            id="face",
        ),
        pytest.param(
            lambda mesh: _invalidate_face_normal(mesh),
            "ValueError",
            id="normal",
        ),
        pytest.param(
            lambda mesh: mesh.metadata.__setitem__(
                "scadview", {"color": [2.0, 0.0, 0.0, 1.0]}
            ),
            "ValueError",
            id="metadata",
        ),
    ],
)
def test_load_worker_publishes_one_error_for_invalid_post_yield_mutation(
    load_queue,
    mutate_source,
    error_type,
):
    source = box()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        loader = mock_module_loader.return_value
        loader.run_function.return_value = _mutate_source_after_yield(
            source, mutate_source
        )
        worker = LoadWorker("test/path", load_queue, generation=8)

        worker.load()

    results = _drain_load_results(load_queue)
    terminal_results = [result for result in results if result.complete]
    assert len(terminal_results) == 1
    assert terminal_results[0].phase is LoadPhase.ERROR
    assert terminal_results[0].error is not None
    assert terminal_results[0].error.type_name == error_type
    assert not terminal_results[0].exportable
    assert worker.final_snapshot is None
    assert worker.export_source is None


def test_load_worker_preserves_module_error_when_error_publication_fails(load_queue):
    source = box()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        loader = mock_module_loader.return_value
        loader.run_function.return_value = _yield_then_raise(source)
        worker = LoadWorker("test/path", load_queue, generation=8)
        feature_states = Mock(
            side_effect=[[], RuntimeError("terminal state failed"), []]
        )

        with patch.object(worker, "_current_feature_states", feature_states):
            worker.load()

    results = _drain_load_results(load_queue)
    terminal_results = [result for result in results if result.complete]
    assert len(terminal_results) == 1
    assert terminal_results[0].phase is LoadPhase.ERROR
    assert terminal_results[0].error == LoadError("RuntimeError", "mesh failed")
    assert not terminal_results[0].exportable
    assert worker.final_snapshot is None
    assert worker.export_source is None


def test_load_worker_clears_export_snapshot_when_final_publication_fails(load_queue):
    source = box()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        loader = mock_module_loader.return_value
        loader.run_function.return_value = iter([source])
        worker = LoadWorker("test/path", load_queue, generation=8)
        feature_states = Mock(
            side_effect=[[], RuntimeError("terminal state failed"), []]
        )

        with patch.object(worker, "_current_feature_states", feature_states):
            worker.load()

    results = _drain_load_results(load_queue)
    terminal_results = [result for result in results if result.complete]
    assert len(terminal_results) == 1
    assert terminal_results[0].phase is LoadPhase.ERROR
    assert terminal_results[0].error == LoadError(
        "RuntimeError", "terminal state failed"
    )
    assert not terminal_results[0].exportable
    assert worker.final_snapshot is None
    assert worker.export_source is None


def test_debug_single_mesh_fallback_retains_source_for_export(load_queue):
    source = box()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        loader = mock_module_loader.return_value
        loader.run_function.return_value = iter([source])
        worker = LoadWorker("test/path", load_queue, debug_features=True)
        worker.load()

    load_queue.get(timeout=1.0)
    final_result = load_queue.get(timeout=1.0)
    assert isinstance(final_result.payload, MeshPayload)
    assert final_result.phase is LoadPhase.FINAL
    assert final_result.exportable
    assert worker.export_source is source


def test_debug_mesh_list_does_not_retain_source_for_export(load_queue):
    source = box()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        loader = mock_module_loader.return_value

        def _run_function(_module_path):
            feature("support", source)
            yield box()

        loader.run_function.side_effect = _run_function
        worker = LoadWorker("test/path", load_queue, debug_features=True)
        worker.load()

    load_queue.get(timeout=1.0)
    final_result = load_queue.get(timeout=1.0)
    assert isinstance(final_result.payload, list)
    assert final_result.phase is LoadPhase.FINAL
    assert not final_result.exportable
    assert worker.export_source is None


def test_cancelled_load_publishes_cancellation_phase(load_queue):
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        mock_module_loader.return_value.run_function.return_value = iter([box()])
        worker = LoadWorker("test/path", load_queue, generation=5)
        worker.cancel()
        worker.load()

    result = load_queue.get(timeout=1.0)

    assert result.phase is LoadPhase.CANCELLED
    assert not result.exportable
    assert result.payload is None


def test_export_worker_uses_the_retained_source_without_payload_reconstruction():
    source = box()
    source.metadata["scadview"] = {"color": [0.123456, 0.2, 0.3, 0.4]}
    source.metadata["preserved"] = {"value": "exact"}
    completion_queue: queue.SimpleQueue[ExportResult] = queue.SimpleQueue()
    exported: list[Trimesh] = []

    source.export = lambda _: exported.append(source)
    ExportWorker(ExportCommand(3, 4, "/tmp/model.stl"), source, completion_queue).run()

    assert exported == [source]
    assert completion_queue.get_nowait() == ExportResult(3, 4)
    with pytest.raises(queue.Empty):
        completion_queue.get_nowait()
    assert source.metadata["preserved"] == {"value": "exact"}


def test_retained_source_export_preserves_precision_metadata_and_visuals(load_queue):
    source = Trimesh(
        vertices=np.array(
            [
                [0.123456789012345, 0.0, 0.0],
                [1.0, 0.987654321098765, 0.0],
                [0.0, 1.0, 0.246813579135792],
            ],
            dtype=np.float64,
        ),
        faces=np.array([[0, 1, 2]]),
        process=False,
    )
    color = [0.123456789, 0.234567891, 0.345678912, 0.456789123]
    face_colors = np.array([[11, 22, 33, 44]], dtype=np.uint8)
    source.metadata = {
        "scadview": {"color": color},
        "preserved": {"nested": ["metadata"]},
    }
    source.visual.face_colors = face_colors
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_loader:
        mock_loader.return_value.run_function.return_value = iter([source])
        worker = LoadWorker("test/path", load_queue, generation=9)
        worker.load()

    retained = worker.export_source
    assert retained is source
    exported: dict[str, object] = {}

    def record_export(path: str) -> None:
        exported["path"] = path
        exported["vertices"] = retained.vertices.copy()
        exported["metadata"] = retained.metadata.copy()
        exported["face_colors"] = retained.visual.face_colors.copy()

    source.export = record_export
    completion_queue: queue.SimpleQueue[ExportResult] = queue.SimpleQueue()
    ExportWorker(
        ExportCommand(9, 9, "/tmp/model.ply"), retained, completion_queue
    ).run()

    np.testing.assert_array_equal(exported["vertices"], source.vertices)
    assert exported["metadata"] == source.metadata
    np.testing.assert_array_equal(exported["face_colors"], face_colors)
    assert exported["path"] == "/tmp/model.ply"
    assert completion_queue.get_nowait() == ExportResult(9, 9)


@pytest.mark.parametrize("extension", ["stl", "obj", "ply", "off"])
def test_export_worker_dispatches_supported_format_by_path(extension, tmp_path):
    source = box()
    completion_queue: queue.SimpleQueue[ExportResult] = queue.SimpleQueue()
    output_path = tmp_path / f"model.{extension}"

    ExportWorker(ExportCommand(10, 2, str(output_path)), source, completion_queue).run()

    assert output_path.exists()
    assert completion_queue.get_nowait() == ExportResult(10, 2)


def test_export_worker_reports_exporter_errors():
    source = box()
    completion_queue: queue.SimpleQueue[ExportResult] = queue.SimpleQueue()

    def fail_export(_: str) -> None:
        raise OSError("disk full")

    source.export = fail_export
    ExportWorker(ExportCommand(3, 4, "/tmp/model.stl"), source, completion_queue).run()

    assert completion_queue.get_nowait() == ExportResult(
        3, 4, ExportError("OSError", "disk full")
    )


def test_export_worker_reports_unexpected_exporter_errors():
    source = box()
    completion_queue: queue.SimpleQueue[ExportResult] = queue.SimpleQueue()

    def fail_export(_: str) -> None:
        raise RuntimeError("unexpected exporter failure")

    source.export = fail_export
    ExportWorker(ExportCommand(3, 4, "/tmp/model.stl"), source, completion_queue).run()

    assert completion_queue.get_nowait() == ExportResult(
        3, 4, ExportError("RuntimeError", "unexpected exporter failure")
    )


def test_export_protocol_boundary_does_not_catch_process_control_exceptions():
    source = box()

    def interrupt_export(_: str) -> None:
        raise KeyboardInterrupt

    source.export = interrupt_export
    command = ExportCommand(3, 4, "/tmp/model.stl")

    with pytest.raises(KeyboardInterrupt):
        _export_result_at_protocol_boundary(command, source)


def test_loader_process_reports_stale_export_requests_reliably():
    process = object.__new__(MeshLoaderProcess)
    process._worker = None
    process._export_result_queue = Mock()
    process._accepting_exports = True

    process._start_export(ExportCommand(3, 4, "/tmp/model.stl"))

    assert process._export_result_queue.put.call_args.args[0] == ExportResult(
        3,
        4,
        ExportError("StaleSource", "No export source for the requested generation"),
    )


def test_loader_process_rejects_export_for_stale_generation():
    process = object.__new__(MeshLoaderProcess)
    process._worker = SimpleNamespace(generation=2, export_source=box())
    process._export_result_queue = Mock()
    process._accepting_exports = True

    process._start_export(ExportCommand(3, 1, "/tmp/model.stl"))

    assert process._export_result_queue.put.call_args.args[0] == ExportResult(
        3,
        1,
        ExportError("StaleSource", "No export source for the requested generation"),
    )


def test_loader_process_reports_export_snapshot_failure():
    source = box()
    source.copy = Mock(side_effect=MemoryError("snapshot allocation failed"))
    process = _export_process(source)

    process._start_export(ExportCommand(7, 1, "/tmp/model.stl"))

    process._export_result_queue.put.assert_called_once_with(
        ExportResult(
            7,
            1,
            ExportError("MemoryError", "snapshot allocation failed"),
        )
    )
    assert not process._active_export_workers


def test_accepted_export_uses_snapshot_after_source_mutation_and_reload():
    export_started = Event()
    release_export = Event()
    source = box()
    source.vertices[0] = (0.125, 0.25, 0.5)
    source.metadata["accepted"] = {"value": "before"}
    source.visual.face_colors[:] = (10, 20, 30, 40)
    snapshot = source.copy()
    exported: dict[str, object] = {}

    def blocking_export(export_source):
        def export(_: str) -> None:
            export_started.set()
            release_export.wait(timeout=2.0)
            exported["vertices"] = export_source.vertices.copy()
            exported["metadata"] = export_source.metadata.copy()
            exported["face_colors"] = export_source.visual.face_colors.copy()

        return export

    source.export = blocking_export(source)
    snapshot.export = blocking_export(snapshot)
    source.copy = Mock(return_value=snapshot)
    result_queue = Mock()
    process = object.__new__(MeshLoaderProcess)
    process._worker = SimpleNamespace(generation=1, export_source=source)
    process._export_result_queue = result_queue
    process._export_completions = queue.SimpleQueue()
    process._active_export_workers = set()
    process._accepting_exports = True

    process._start_export(ExportCommand(7, 1, "/tmp/model.stl"))
    assert export_started.wait(timeout=1.0)
    source.vertices[0] = (9.0, 8.0, 7.0)
    source.metadata["accepted"]["value"] = "after"
    source.visual.face_colors[:] = (90, 80, 70, 60)
    process._worker = SimpleNamespace(generation=2, export_source=box())
    release_export.set()
    workers = tuple(process._active_export_workers)
    for worker in workers:
        worker.join(timeout=2.0)
    process._reap_export_workers()

    assert all(not worker.is_alive() for worker in workers)
    source.copy.assert_called_once_with()
    npt.assert_array_equal(exported["vertices"], snapshot.vertices)
    assert exported["metadata"] == snapshot.metadata
    npt.assert_array_equal(exported["face_colors"], snapshot.visual.face_colors)
    result_queue.put.assert_called_once_with(ExportResult(7, 1))


def test_loader_event_loop_publishes_completed_exports_before_reaping_and_polling():
    source = box()
    source.export = Mock()
    result_queue = Mock()
    completion_queue: queue.SimpleQueue[ExportResult] = queue.SimpleQueue()
    export_worker = ExportWorker(
        ExportCommand(7, 1, "/tmp/model.stl"), source, completion_queue
    )
    export_worker.start()
    export_worker.join(timeout=1.0)
    assert not export_worker.is_alive()

    process = object.__new__(MeshLoaderProcess)
    process._worker = None
    process._command_queue = Mock()
    process._load_queue = Mock()
    process._load_events = LoadEventChannel()
    process._export_result_queue = result_queue
    process._export_completions = completion_queue
    process._active_load_workers = set()
    process._active_export_workers = {export_worker}
    process._accepting_exports = True
    process._log_queue = Mock()
    process._log_level = logging.INFO

    def shutdown_after_reap(timeout):
        assert timeout == process.COMMAND_QUEUE_CHECK_TIMEOUT
        assert not process._active_export_workers
        result_queue.put.assert_called_once_with(ExportResult(7, 1))
        return ShutDownCommand()

    process._command_queue.get.side_effect = shutdown_after_reap
    with patch("scadview.mesh_loader_process.configure_worker_logging"):
        process.run()

    result_queue.put.assert_called_once_with(ExportResult(7, 1))


def test_loader_coordinator_publishes_load_events_and_propagates_transport_failure():
    process = object.__new__(MeshLoaderProcess)
    process._load_events = LoadEventChannel()
    process._load_queue = Mock()
    process._load_queue.put.side_effect = OSError("load result queue closed")
    result = LoadResult(
        1,
        1,
        payload=None,
        error=None,
        generation=3,
        revision=1,
        phase=LoadPhase.PROGRESS,
        exportable=False,
        debug=False,
    )
    process._load_events.put_latest(LoadResultEvent(result))

    with pytest.raises(OSError, match="load result queue closed"):
        process._drain_load_events()

    process._load_queue.put.assert_called_once_with(
        result, timeout=LoadWorker.PUT_QUEUE_TIMEOUT
    )


def test_loader_repeated_completion_drains_do_not_publish_duplicates():
    process = _export_process(None)
    process._export_completions.put(ExportResult(7, 1))

    process._drain_export_completions()
    process._drain_export_completions()

    process._export_result_queue.put.assert_called_once_with(ExportResult(7, 1))


@pytest.mark.parametrize(
    "publication_error",
    [
        BrokenPipeError("export result pipe broken"),
        EOFError("export result pipe closed"),
        OSError("export result queue closed"),
        ValueError("export result queue unavailable"),
    ],
)
def test_loader_export_publication_failure_is_fatal_and_prevents_silent_reap(
    publication_error,
):
    source = box()
    completion_queue: queue.SimpleQueue[ExportResult] = queue.SimpleQueue()
    worker = ExportWorker(
        ExportCommand(7, 1, "/tmp/model.stl"), source, completion_queue
    )
    worker.start()
    worker.join(timeout=1.0)
    assert not worker.is_alive()
    process = _export_process(None)
    process._export_completions = completion_queue
    process._active_export_workers = {worker}
    process._export_result_queue.put.side_effect = publication_error

    with pytest.raises(type(publication_error), match=str(publication_error)):
        process._reap_export_workers()

    assert process._active_export_workers == {worker}
    process._export_result_queue.put.assert_called_once_with(ExportResult(7, 1))


def test_loader_tracks_cancelled_worker_while_starting_reload():
    previous_worker = Mock()
    previous_worker.is_alive.return_value = True
    current_worker = Mock()
    process = object.__new__(MeshLoaderProcess)
    process._worker = previous_worker
    process._load_queue = Mock()
    process._active_load_workers = {previous_worker}
    command = LoadMeshCommand("test/path", generation=2)

    with patch("scadview.mesh_loader_process.LoadWorker", return_value=current_worker):
        process._start_load(command)

    previous_worker.cancel.assert_called_once_with()
    current_worker.start.assert_called_once_with()
    assert process._worker is current_worker
    assert process._active_load_workers == {previous_worker, current_worker}


def test_loader_reaps_only_completed_load_workers():
    completed_worker = Mock()
    completed_worker.is_alive.return_value = False
    active_worker = Mock()
    active_worker.is_alive.return_value = True
    process = object.__new__(MeshLoaderProcess)
    process._active_load_workers = {completed_worker, active_worker}

    process._reap_load_workers()

    assert process._active_load_workers == {active_worker}


def test_loader_reaps_only_completed_export_workers():
    export_started = Event()
    release_export = Event()
    source = box()
    snapshot = source.copy()

    def blocking_export(_: str) -> None:
        export_started.set()
        release_export.wait(timeout=2.0)

    snapshot.export = blocking_export
    source.copy = Mock(return_value=snapshot)
    process = _export_process(source)
    process._start_export(ExportCommand(7, 1, "/tmp/model.stl"))
    assert export_started.wait(timeout=1.0)

    process._reap_export_workers()

    assert len(process._active_export_workers) == 1
    release_export.set()
    _join_export_workers(process)
    process._reap_export_workers()
    assert not process._active_export_workers
    process._export_result_queue.put.assert_called_once_with(ExportResult(7, 1))


def test_loader_workers_are_daemons_but_remain_explicitly_tracked(load_queue):
    load_worker = LoadWorker("test/path", load_queue)
    completion_queue: queue.SimpleQueue[ExportResult] = queue.SimpleQueue()
    export_worker = ExportWorker(
        ExportCommand(7, 1, "/tmp/model.stl"), box(), completion_queue
    )

    assert load_worker.daemon
    assert export_worker.daemon


def test_repeated_exports_release_finished_workers_and_old_generation_sources():
    process = _export_process(None)
    source_refs = []
    snapshot_refs = []

    for generation in range(1, 4):
        source = box()
        snapshot = source.copy()
        snapshot.export = Mock()
        source.copy = Mock(return_value=snapshot)
        source_ref = weakref.ref(source)
        snapshot_ref = weakref.ref(snapshot)
        source_refs.append(source_ref)
        snapshot_refs.append(snapshot_ref)
        process._worker = SimpleNamespace(
            generation=generation,
            export_source=source,
        )

        process._start_export(ExportCommand(generation, generation, "/tmp/model.stl"))
        _join_export_workers(process)
        process._reap_export_workers()

        assert not process._active_export_workers
        process._worker = None
        del source
        del snapshot
        gc.collect()
        assert source_ref() is None
        assert snapshot_ref() is None

    assert all(source_ref() is None for source_ref in source_refs)
    assert all(snapshot_ref() is None for snapshot_ref in snapshot_refs)


def test_loader_process_rejects_export_after_shutdown_begins():
    process = object.__new__(MeshLoaderProcess)
    process._accepting_exports = False
    process._export_result_queue = Mock()
    process._export_completions = queue.SimpleQueue()

    process._start_export(ExportCommand(3, 4, "/tmp/model.stl"))

    assert process._export_result_queue.put.call_args.args[0] == ExportResult(
        3,
        4,
        ExportError("ShuttingDown", "Loader is shutting down"),
    )


def test_loader_process_shutdown_closes_the_export_result_queue():
    process = object.__new__(MeshLoaderProcess)
    process._worker = None
    process._command_queue = Mock()
    process._load_queue = Mock()
    process._export_result_queue = Mock()
    process._export_completions = queue.SimpleQueue()
    process._active_load_workers = set()
    process._active_export_workers = set()
    process._accepting_exports = True

    process._shutdown()

    process._command_queue.close.assert_called_once_with()
    process._load_queue.close.assert_called_once_with()
    process._export_result_queue.close.assert_called_once_with()


def test_loader_shutdown_cancels_and_bounded_joins_all_load_workers():
    workers = [Mock(), Mock()]
    for worker in workers:
        worker.is_alive.side_effect = [True, False]
    process = object.__new__(MeshLoaderProcess)
    process._worker = workers[0]
    process._command_queue = Mock()
    process._load_queue = Mock()
    process._export_result_queue = Mock()
    process._export_completions = queue.SimpleQueue()
    process._active_load_workers = set(workers)
    process._active_export_workers = set()
    process._accepting_exports = True

    process._shutdown()

    for worker in workers:
        worker.cancel.assert_called_once_with()
        worker.join.assert_called_once_with(timeout=ANY)
        assert 0.0 <= worker.join.call_args.kwargs["timeout"] <= 1.0
    assert not process._active_load_workers
    assert process._worker is None
    process._command_queue.close.assert_called_once_with()
    process._load_queue.close.assert_called_once_with()
    process._export_result_queue.close.assert_called_once_with()


def test_loader_shutdown_waits_for_blocking_export_before_closing_queue():
    export_started = Event()
    release_export = Event()
    events: list[str] = []
    source = box()

    def blocking_export(_: str) -> None:
        export_started.set()
        release_export.wait(timeout=2.0)

    source.export = blocking_export
    result_queue = Mock()
    result_queue.put.side_effect = lambda _: events.append("put")
    result_queue.close.side_effect = lambda: events.append("close")
    completion_queue: queue.SimpleQueue[ExportResult] = queue.SimpleQueue()
    worker = ExportWorker(
        ExportCommand(3, 4, "/tmp/model.stl"), source, completion_queue
    )
    worker.start()
    assert export_started.wait(timeout=1.0)

    process = object.__new__(MeshLoaderProcess)
    process._worker = None
    process._command_queue = Mock()
    process._load_queue = Mock()
    process._export_result_queue = result_queue
    process._export_completions = completion_queue
    process._active_load_workers = set()
    process._active_export_workers = {worker}
    process._accepting_exports = True
    shutdown = Thread(target=process._shutdown)
    shutdown.start()
    release_export.set()
    shutdown.join(timeout=2.0)

    assert not shutdown.is_alive()
    assert events == ["put", "close"]


def test_loader_shutdown_publishes_completed_export_when_load_join_times_out():
    load_worker = Mock()
    load_worker.is_alive.return_value = True
    completion_queue: queue.SimpleQueue[ExportResult] = queue.SimpleQueue()
    export_worker = ExportWorker(
        ExportCommand(3, 4, "/tmp/model.stl"), box(), completion_queue
    )
    export_worker.start()
    export_worker.join(timeout=1.0)
    assert not export_worker.is_alive()
    process = object.__new__(MeshLoaderProcess)
    process._worker = load_worker
    process._command_queue = Mock()
    process._load_queue = Mock()
    process._export_result_queue = Mock()
    process._export_completions = completion_queue
    process._active_load_workers = {load_worker}
    process._active_export_workers = {export_worker}
    process._accepting_exports = True

    process._shutdown()

    process._export_result_queue.put.assert_called_once_with(ExportResult(3, 4))
    assert not process._active_export_workers
    process._export_result_queue.close.assert_not_called()


def test_export_shutdown_joins_multiple_workers_against_one_deadline():
    first_worker = Mock()
    first_worker.is_alive.return_value = False
    second_worker = Mock()
    second_worker.is_alive.return_value = False
    process = _export_process(None)
    process._active_export_workers = {first_worker, second_worker}

    with patch("scadview.mesh_loader_process.monotonic", side_effect=[90.0, 95.0]):
        assert process._join_export_workers(100.0)

    timeouts = {
        first_worker.join.call_args.kwargs["timeout"],
        second_worker.join.call_args.kwargs["timeout"],
    }
    assert timeouts == {5.0, 10.0}
    assert not process._active_export_workers


def _export_process(source):
    process = object.__new__(MeshLoaderProcess)
    process._worker = SimpleNamespace(generation=1, export_source=source)
    process._export_result_queue = Mock()
    process._export_completions = queue.SimpleQueue()
    process._active_export_workers = set()
    process._accepting_exports = True
    return process


def _join_export_workers(process):
    for worker in tuple(process._active_export_workers):
        worker.join(timeout=2.0)
        assert not worker.is_alive()


def _raise_mesh_error():
    raise RuntimeError("mesh failed")
    yield


def _yield_then_raise(mesh):
    yield mesh
    raise RuntimeError("mesh failed")


def _mutate_after_last_yield(mesh):
    yield mesh
    mesh.vertices[0] = (9.125, 8.25, 7.5)
    mesh.metadata["scadview"] = {"color": [0.125, 0.24, 0.36, 0.48]}


def _mutate_list_source_after_yield(meshes, mutate_source):
    yield meshes
    mutate_source(meshes[1])


def _rotate_first_face(mesh):
    mesh.faces[0] = np.roll(mesh.faces[0], 1)


def _set_valid_face_normal(mesh):
    face_normals = mesh.face_normals
    face_normals.setflags(write=True)
    face_normals[0] = (0.25, 0.5, 0.75)


def _mutate_source_after_yield(mesh, mutate_source):
    yield mesh
    mutate_source(mesh)


def _invalidate_face_normal(mesh):
    face_normals = mesh.face_normals
    face_normals.setflags(write=True)
    face_normals[0, 0] = np.inf


def _drain_load_results(load_queue):
    results = []
    while True:
        try:
            results.append(load_queue.get(timeout=0.1))
        except queue.Empty:
            return results


def test_load_worker_does_not_evict_newer_queued_result():
    load_queue = LoadEventChannel()
    newer_result = LoadResult(
        1,
        1,
        mesh_to_payload(box()),
        None,
        phase=LoadPhase.PROGRESS,
        revision=1,
        exportable=False,
        debug=False,
        generation=4,
    )
    load_queue.put_latest(LoadResultEvent(newer_result))
    worker = LoadWorker("test/path", load_queue, generation=3)

    worker.put_in_queue(
        LoadResult(
            1,
            1,
            None,
            None,
            phase=LoadPhase.PROGRESS,
            revision=1,
            exportable=False,
            debug=False,
            generation=3,
        )
    )

    assert load_queue.get(timeout=1.0) == newer_result


def test_cancelled_worker_does_not_publish_payload(load_queue):
    worker = LoadWorker("test/path", load_queue)
    worker.cancel()

    worker.put_in_queue(
        LoadResult(
            1,
            1,
            mesh_to_payload(box()),
            None,
            phase=LoadPhase.PROGRESS,
            revision=1,
            exportable=False,
            debug=False,
        )
    )

    with pytest.raises(queue.Empty):
        load_queue.get_nowait()


@pytest.fixture
def mesh(request):
    m = getattr(request, "param", box())
    return m


@pytest.fixture
def load_queue():
    queue = LoadEventChannel(maxsize=10)
    yield queue
    queue.close(discard=True)


@pytest.fixture
def load_worker(mesh, load_queue):
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value
        if isinstance(mesh, list):
            ml_instance.run_function.return_value = iter(mesh)
        else:
            ml_instance.run_function.return_value = iter([mesh])
        worker = LoadWorker("test/path", load_queue)
        yield worker
        LoadWorker.load_number = 0  # reset


@pytest.fixture
def started_load_worker(load_worker):
    load_worker.start()
    yield load_worker
    load_worker.cancel()
    load_worker.join(timeout=1.0)
    assert not load_worker.is_alive()


def test_load_worker_init(load_worker):
    assert load_worker.load_number == 0


def test_load_worker_put_in_queue(mesh, load_queue, started_load_worker):
    result = load_queue.get(timeout=1.0)
    assert result.load_number == 1
    assert result.sequence_number == 1
    _assert_payload_geometry(result.payload, mesh)
    assert not result.error
    assert not result.complete  # Even though no more meshes, not set complete

    # On get after last mesh, returns the last mesh with same load result and seq
    # with complete is True

    result = load_queue.get(timeout=1.0)
    assert result.load_number == 1
    assert result.sequence_number == 1
    _assert_payload_geometry(result.payload, mesh)
    assert not result.error
    assert result.complete


@pytest.mark.parametrize(
    "mesh", [[box(), icosphere()]], indirect=True, ids=["box and sphere"]
)
def test_load_worker_put_in_queue_multi_mesh(mesh, load_queue, started_load_worker):
    results = []
    while not results or not results[-1].complete:
        results.append(load_queue.get(timeout=1.0))
    for result in results:
        assert result.load_number == 1
        _assert_payload_geometry(result.payload, mesh[result.sequence_number - 1])
        assert not result.error
    assert results[-1].sequence_number == 2
    assert results[-1].phase is LoadPhase.FINAL
    assert [r.sequence_number for r in results] == sorted(
        r.sequence_number for r in results
    )


def test_load_worker_colors_mesh_list(load_queue):
    mesh_list = [box(), icosphere()]
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value
        ml_instance.run_function.return_value = iter([mesh_list])
        worker = LoadWorker("test/path", load_queue)
        LoadWorker.load_number = 0  # reset
        worker.start()
        worker.join(timeout=1.0)
        assert not worker.is_alive()
        worker.cancel()

    result = load_queue.get(timeout=1.0)
    assert isinstance(result.payload, list)
    load_queue.get(timeout=1.0)  # Otherwise hangs on windows.
    for payload in result.payload:
        assert isinstance(payload, MeshPayload)
        assert payload.color is not None
        assert payload.color[3] == 128


def test_load_worker_debugs_feature_sources_for_published_yields(load_queue):
    first_source = box()
    second_source = icosphere()
    first_result = box()
    second_result = icosphere()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value

        def _run_function(_module_path):
            feature("support", first_source)
            yield first_result
            feature("support", second_source)
            yield second_result

        ml_instance.run_function.side_effect = _run_function
        worker = LoadWorker("test/path", load_queue, debug_features=True)
        LoadWorker.load_number = 0
        worker.load()

    results = _drain_load_results(load_queue)
    for result in results:
        assert isinstance(result.payload, list)
        _assert_payload_geometry(result.payload[0], first_source)
        if result.sequence_number == 2:
            _assert_payload_geometry(result.payload[1], second_source)
        assert result.payload[0].color is not None
        assert result.payload[0].color[3] == 128
    assert results[-1].phase is LoadPhase.FINAL
    assert results[-1].sequence_number == 2


def test_load_worker_captures_feature_sources_after_generator_exhaustion(load_queue):
    yielded_mesh = box()
    late_source = icosphere()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value

        def _run_function(_module_path):
            yield yielded_mesh
            feature("late", late_source)

        ml_instance.run_function.side_effect = _run_function
        worker = LoadWorker("test/path", load_queue, debug_features=True)
        worker.load()

    results = _drain_load_results(load_queue)
    assert len(results) == 2
    final_load = results[-1]
    assert final_load.phase is LoadPhase.FINAL
    assert final_load.debug
    assert not final_load.exportable
    assert isinstance(final_load.payload, list)
    assert len(final_load.payload) == 1
    _assert_payload_geometry(final_load.payload[0], late_source)
    assert final_load.features == [FeatureState("late", True)]
    assert worker.export_source is None


@pytest.mark.parametrize("cancel_before_claim", [True, False])
def test_load_worker_terminal_claim_publishes_exactly_one_terminal_result(
    load_queue,
    cancel_before_claim,
):
    source = box()
    claim_entered = Event()
    release_claim = Event()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        loader = mock_module_loader.return_value
        loader.run_function.return_value = iter([source])
        worker = LoadWorker("test/path", load_queue, generation=11)
        claim = worker._claim_terminal

        def controlled_claim():
            claim_entered.set()
            if cancel_before_claim:
                release_claim.wait(timeout=1.0)
                return claim()
            result = claim()
            release_claim.wait(timeout=1.0)
            return result

        worker._claim_terminal = controlled_claim
        thread = Thread(target=worker.load)
        thread.start()
        assert claim_entered.wait(timeout=1.0)
        worker.cancel()
        release_claim.set()
        thread.join(timeout=1.0)

    assert not thread.is_alive()
    terminal_results = [
        result for result in _drain_load_results(load_queue) if result.complete
    ]
    assert len(terminal_results) == 1
    if cancel_before_claim:
        assert terminal_results[0].phase is LoadPhase.CANCELLED
        assert not terminal_results[0].exportable
        assert worker.final_snapshot is None
        assert worker.export_source is None
    else:
        assert terminal_results[0].phase is LoadPhase.FINAL
        assert terminal_results[0].exportable
        assert worker.export_source is source


def test_load_worker_debug_omits_disabled_feature_sources(load_queue):
    source = box()
    normal_mesh = icosphere()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value

        def _run_function(_module_path):
            feature("cutout", source)
            feature("guide", box())
            yield normal_mesh

        ml_instance.run_function.side_effect = _run_function
        worker = LoadWorker(
            "test/path",
            load_queue,
            feature_states={"cutout": False},
            debug_features=True,
        )
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)

    assert isinstance(result.payload, list)
    assert len(result.payload) == 1
    assert result.payload[0].color is not None
    assert result.payload[0].color[3] == 128


def test_load_worker_debug_converts_manifold_feature_sources(load_queue):
    source = manifold3d.Manifold.cube()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value

        def _run_function(_module_path):
            feature("cutout", source)
            yield box()

        ml_instance.run_function.side_effect = _run_function
        worker = LoadWorker("test/path", load_queue, debug_features=True)
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)

    assert isinstance(result.payload, list)
    assert len(result.payload) == 1
    assert isinstance(result.payload[0], MeshPayload)
    assert result.payload[0].color is not None
    assert result.payload[0].color[3] == 128


def test_load_worker_debug_omits_unregistered_meshes_from_feature_entries(
    load_queue,
):
    base = box()
    unregistered = icosphere()
    source = box()
    normal_mesh = base.union(unregistered)
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value

        def _run_function(_module_path):
            feature("guide", source)
            yield normal_mesh

        ml_instance.run_function.side_effect = _run_function
        worker = LoadWorker("test/path", load_queue, debug_features=True)
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)

    assert isinstance(result.payload, list)
    assert len(result.payload) == 1
    _assert_payload_geometry(result.payload[0], source)


def test_load_worker_debug_falls_back_to_normal_mesh_without_feature_sources(
    load_queue,
):
    normal_mesh = icosphere()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value
        ml_instance.run_function.return_value = iter([normal_mesh])
        worker = LoadWorker("test/path", load_queue, debug_features=True)
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)

    _assert_payload_geometry(result.payload, normal_mesh)


def test_load_worker_preserves_normal_mesh_when_feature_debug_is_off(load_queue):
    source = box()
    normal_mesh = icosphere()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value

        def _run_function(_module_path):
            feature("cutout", source)
            yield normal_mesh

        ml_instance.run_function.side_effect = _run_function
        worker = LoadWorker("test/path", load_queue, debug_features=False)
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)

    _assert_payload_geometry(result.payload, normal_mesh)


def test_load_worker_tracks_feature_states_and_filters_disabled_features(load_queue):
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value

        def _run_function(_module_path):
            yield feature("cutout", box())

        ml_instance.run_function.side_effect = _run_function
        worker = LoadWorker(
            "test/path",
            load_queue,
            feature_states={"cutout": False},
        )
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)
    assert result.payload is None
    assert result.features == [FeatureState("cutout", False)]
    result = load_queue.get(timeout=1.0)
    assert result.complete
    assert result.features == [FeatureState("cutout", False)]


def test_load_worker_errors_on_nan_vertices(load_queue):
    nan_mesh = box()
    nan_mesh.vertices[0] = [float("nan"), 0.0, 0.0]
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value
        ml_instance.run_function.return_value = iter([nan_mesh])
        worker = LoadWorker("test/path", load_queue)
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)
    assert result.error is not None
    assert result.error is not None
    assert result.error.type_name == "ValueError"
    assert result.status == LoadStatus.ERROR


def test_load_worker_errors_on_non_finite_manifold_vertices(load_queue):
    base_mesh = manifold3d.Manifold.cube().to_mesh()
    vertices = base_mesh.vert_properties.copy()
    vertices[0, 0] = float("inf")
    invalid_manifold = manifold3d.Manifold(
        manifold3d.Mesh(vertices.astype("f4"), base_mesh.tri_verts.copy())
    )
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value
        ml_instance.run_function.return_value = iter([invalid_manifold])
        worker = LoadWorker("test/path", load_queue)
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)
    assert result.error is not None
    assert result.error is not None
    assert result.error.type_name == "ValueError"
    assert result.status == LoadStatus.ERROR


def _assert_payload_geometry(payload, mesh):
    assert isinstance(payload, MeshPayload)
    assert not isinstance(payload, Trimesh)
    npt.assert_allclose(payload.vertices, mesh.vertices)
    npt.assert_array_equal(payload.faces, mesh.faces)
