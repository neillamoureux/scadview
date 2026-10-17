"""Deterministic producer/converter handoff tests."""

import queue
from threading import Event
from unittest.mock import patch

import numpy.testing as npt
import pytest
from trimesh.creation import box

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


def drain_results(publications):
    results = []
    while True:
        try:
            results.append(publications.get_nowait().result)
        except queue.Empty:
            return results
