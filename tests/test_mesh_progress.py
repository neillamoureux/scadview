"""Deterministic producer/converter handoff tests."""

import queue
from threading import Event
from unittest.mock import patch

import numpy.testing as npt
import pytest
from trimesh.creation import box

from scadview.features import FeatureState, feature
from scadview.mesh_loader_process import LoadEventChannel, LoadPhase, LoadWorker
from scadview.mesh_payload import mesh_to_payload


@pytest.mark.parametrize("ending", ["final", "error", "cancel", "conversion-error"])
@pytest.mark.parametrize("as_list", [False, True])
def test_coalesces_before_conversion_with_safe_source_reuse(ending, as_list):
    converting = Event()
    generated = Event()
    release_conversion = Event()
    source = box()
    source.metadata["scadview"] = {"color": [0.2, 0.3, 0.4, 1.0]}
    initial_vertices = source.vertices.copy()
    initial_normals = source.face_normals.copy()
    yielded = [source] if as_list else source
    converted = []
    publications = LoadEventChannel(maxsize=20)
    worker = LoadWorker("test/path", publications, generation=17)

    def generate(_path):
        yield yielded
        assert converting.wait(2)
        source.face_normals.setflags(write=True)
        source.face_normals[:] = [1.0, 0.0, 0.0]
        source.metadata["scadview"]["color"][0] = 0.8
        for index in range(1, 10):
            source.vertices = initial_vertices + index
            if ending in ("cancel", "error") and index == 9:
                yield source if as_list else [source]
            else:
                yield yielded
        source.vertices = initial_vertices + 10
        generated.set()
        if ending == "error":
            raise RuntimeError("generator failed")

    def convert(mesh):
        if not converted:
            converting.set()
            assert release_conversion.wait(3)
            npt.assert_array_equal(mesh.face_normals, initial_normals)
            assert mesh.metadata["scadview"]["color"][0] == 0.2
        converted.append(mesh.vertices.copy())
        if ending == "conversion-error":
            raise ValueError("conversion failed")
        return mesh_to_payload(mesh)

    with (
        patch("scadview.mesh_loader_process.ModuleLoader") as loader,
        patch("scadview.mesh_loader_process.mesh_to_payload", side_effect=convert),
    ):
        loader.return_value.run_function.side_effect = generate
        worker.start()
        try:
            assert generated.wait(2), "generation must advance during conversion"
            if ending == "cancel":
                worker.cancel()
        finally:
            release_conversion.set()
            worker.join(4)

    assert not worker.is_alive()
    results = drain_results(publications)
    terminal = [result for result in results if result.complete]
    assert len(terminal) == 1
    assert all(result.generation == 17 for result in results)
    assert [r.revision for r in results] == sorted({r.revision for r in results})
    npt.assert_array_equal(converted[0], initial_vertices)
    assert len(converted) <= 3
    assert all(result.sequence_number in (1, 10) for result in results)
    final = terminal[0]
    if ending == "final":
        assert final.phase is LoadPhase.FINAL
        payload = final.payload[0] if as_list else final.payload
        npt.assert_allclose(payload.vertices, source.vertices)
        assert final.debug is as_list
        assert final.exportable is not as_list
        if not as_list:
            assert worker.export_source is source
            assert worker.final_snapshot.payload is final.payload
    elif ending == "cancel":
        assert final.phase is LoadPhase.CANCELLED
        assert final.debug is as_list
        assert worker.export_source is None
        assert len(converted) == 1
    else:
        assert final.phase is LoadPhase.ERROR
        expected = "generator failed" if ending == "error" else "conversion failed"
        assert final.error.message == expected
        assert worker.export_source is None


def test_terminal_replaces_progress_in_full_result_queue():
    publications = LoadEventChannel()
    source = box()
    with patch("scadview.mesh_loader_process.ModuleLoader") as loader:
        loader.return_value.run_function.return_value = iter([source] * 20)
        worker = LoadWorker("test/path", publications, generation=3)
        worker.start()
        worker.join(4)
    assert not worker.is_alive()
    final = publications.get(timeout=1)
    assert final.phase is LoadPhase.FINAL
    assert final.sequence_number == 20
    npt.assert_allclose(final.payload.vertices, source.vertices)


@pytest.mark.parametrize("ending", ["return", "yield", "raise"])
def test_converter_error_arrives_before_blocked_generator_finishes(ending):
    resumed, release = Event(), Event()
    source = box()
    source.metadata["scadview"] = {"color": [2.0, 0.0, 0.0, 1.0]}
    publications = LoadEventChannel(maxsize=10)

    def generate(_path):
        feature("visible", box())
        yield source
        resumed.set()
        assert release.wait(5)
        if ending == "yield":
            yield box()
        elif ending == "raise":
            raise RuntimeError("later generator failure")

    with patch("scadview.mesh_loader_process.ModuleLoader") as loader:
        loader.return_value.run_function.side_effect = generate
        worker = LoadWorker("test/path", publications, generation=17)
        worker.start()
        try:
            assert resumed.wait(2)
            terminal = publications.get(timeout=2)
            assert terminal.phase is LoadPhase.ERROR
            assert terminal.error.type_name == "ValueError"
            assert "color components" in terminal.error.message
            assert terminal.features == [FeatureState("visible", True)]
            assert terminal.generation == 17
            assert not terminal.exportable
            assert worker.is_alive()
            assert worker.export_source is None
            worker.cancel()
        finally:
            release.set()
            worker.join(3)
    assert not worker.is_alive()
    assert drain_results(publications) == []


@pytest.mark.parametrize("mutation", ["append", "replace", "remove", "clear", "fill"])
def test_final_result_reads_original_list_after_last_yield(mutation):
    sources = [] if mutation == "fill" else [box(), box(extents=[2, 2, 2])]
    publications = LoadEventChannel(maxsize=10)

    def generate(_path):
        yield sources
        if mutation in ("append", "fill"):
            sources.append(box(extents=[3, 3, 3]))
        elif mutation == "replace":
            sources[0] = box(extents=[4, 4, 4])
        elif mutation == "remove":
            sources.pop()
        else:
            sources.clear()

    with patch("scadview.mesh_loader_process.ModuleLoader") as loader:
        loader.return_value.run_function.side_effect = generate
        worker = LoadWorker("test/path", publications)
        worker.load()
    final = drain_results(publications)[-1]
    assert final.phase is LoadPhase.FINAL
    assert not final.exportable
    assert worker.export_source is None
    if not sources:
        assert final.payload is None
    else:
        assert final.debug
        assert len(final.payload) == len(sources)
        for payload, source in zip(final.payload, sources):
            npt.assert_array_equal(payload.vertices, source.vertices)


@pytest.mark.parametrize("cancel_before_claim", [True, False])
def test_converter_error_and_cancellation_share_one_terminal_claim(cancel_before_claim):
    resumed, release_generator = Event(), Event()
    claim_entered, release_claim = Event(), Event()
    publications = LoadEventChannel(maxsize=10)
    source = box()
    source.metadata["scadview"] = {"color": [2.0, 0.0, 0.0, 1.0]}

    def generate(_path):
        yield source
        resumed.set()
        assert release_generator.wait(5)

    with patch("scadview.mesh_loader_process.ModuleLoader") as loader:
        loader.return_value.run_function.side_effect = generate
        worker = LoadWorker("test/path", publications)
        claim = worker._claim_terminal

        def controlled_claim():
            if cancel_before_claim:
                claim_entered.set()
                assert release_claim.wait(3)
                return claim()
            claimed = claim()
            claim_entered.set()
            assert release_claim.wait(3)
            return claimed

        worker._claim_terminal = controlled_claim
        worker.start()
        try:
            assert resumed.wait(2)
            assert claim_entered.wait(2)
            worker.cancel()
            release_claim.set()
            terminal = publications.get(timeout=2)
            expected = LoadPhase.CANCELLED if cancel_before_claim else LoadPhase.ERROR
            assert terminal.phase is expected
            assert not terminal.exportable
            assert worker.export_source is None
        finally:
            release_claim.set()
            release_generator.set()
            worker.join(3)
    assert not worker.is_alive()
    assert drain_results(publications) == []


def drain_results(publications):
    results = []
    while True:
        try:
            results.append(publications.get_nowait())
        except queue.Empty:
            return results
