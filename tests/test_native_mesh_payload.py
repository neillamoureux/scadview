import queue
from threading import Event
from unittest.mock import patch

import numpy.testing as npt
import pytest
from manifold3d import Manifold
from trimesh import Trimesh
from trimesh.creation import box

from scadview.api.utils import manifold_to_trimesh
from scadview.features import FeatureState, feature
from scadview.mesh_loader_process import (
    ExportError,
    LoadEventChannel,
    LoadPhase,
    LoadWorker,
    _snapshot_export_source_at_protocol_boundary,
)
from scadview.mesh_payload import manifold_to_payload, mesh_to_payload


@pytest.mark.parametrize(
    "source",
    [
        Manifold(),
        Manifold.cube(),
        Manifold.sphere(1, 12).translate((3, 2, 1)),
        Manifold.cube().scale((1e-8, 1e-8, 1e-8)),
        Manifold.cube().set_properties(3, lambda position, old: [0.1, 0.3, 0.7]),
    ],
)
def test_native_payload_matches_normalized_triangle_geometry_and_shading(source):
    expected = mesh_to_payload(manifold_to_trimesh(source))
    with patch("scadview.api.utils.trimesh.Trimesh", side_effect=AssertionError):
        actual = manifold_to_payload(source)

    npt.assert_allclose(
        actual.vertices[actual.faces], expected.vertices[expected.faces]
    )
    npt.assert_allclose(actual.face_normals, expected.face_normals, atol=1e-7)
    npt.assert_array_equal(actual.color, expected.color)
    npt.assert_allclose(actual.bounds, expected.bounds)
    assert actual.scale == pytest.approx(expected.scale)
    for values in (actual.vertices, actual.faces, actual.face_normals, actual.color):
        assert values.flags.c_contiguous
        assert not values.flags.writeable


def test_native_payload_supports_debug_color_without_mutating_source():
    source = Manifold.cube()
    colored = manifold_to_payload(source, (0.2, 0.3, 0.4, 0.5))
    npt.assert_array_equal(colored.color, [51, 76, 102, 128])
    npt.assert_array_equal(manifold_to_payload(source).color, [128, 128, 128, 255])


@pytest.mark.parametrize("debug", [False, True])
def test_loader_retains_native_final_source_and_only_adapts_for_export(debug):
    source = Manifold.cube().translate((1.234567, 0, 0))
    results = LoadEventChannel(maxsize=10)
    with (
        patch("scadview.mesh_loader_process.ModuleLoader") as module,
        patch(
            "scadview.mesh_loader_process.manifold_to_trimesh",
            side_effect=AssertionError,
        ),
    ):
        module.return_value.run_function.return_value = iter([source])
        worker = LoadWorker("module.py", results, debug_features=debug, generation=6)
        worker.load()
    final = drain(results)[-1]
    assert final.phase is LoadPhase.FINAL
    assert final.exportable
    assert final.generation == 6
    assert worker.export_source is source
    assert worker.final_snapshot.payload is final.payload
    snapshot = _snapshot_export_source_at_protocol_boundary(worker.export_source)
    assert isinstance(snapshot, Trimesh)
    expected = manifold_to_trimesh(source)
    npt.assert_array_equal(snapshot.vertices, expected.vertices)
    npt.assert_array_equal(snapshot.faces, expected.faces)


def test_native_mixed_debug_list_preserves_palette_and_explicit_trimesh_color():
    native = Manifold.cube()
    authored = box()
    authored.metadata["scadview"] = {"color": [0.1, 0.2, 0.3, 0.4]}
    results = LoadEventChannel(maxsize=10)

    def generate(_path):
        feature("native", native)
        feature("authored", authored)
        yield native

    with (
        patch("scadview.mesh_loader_process.ModuleLoader") as module,
        patch(
            "scadview.mesh_loader_process.manifold_to_trimesh",
            side_effect=AssertionError,
        ),
    ):
        module.return_value.run_function.side_effect = generate
        worker = LoadWorker("module.py", results, debug_features=True)
        worker.load()
    final = drain(results)[-1]
    assert final.phase is LoadPhase.FINAL
    assert final.debug
    assert not final.exportable
    assert worker.export_source is None
    assert final.features == [
        FeatureState("native", True),
        FeatureState("authored", True),
    ]
    assert len(final.payload) == 2
    assert final.payload[0].color[3] == 128
    npt.assert_array_equal(final.payload[1].color, [26, 51, 76, 102])


def test_native_export_preserves_vertex_properties_and_isolated_geometry():
    source = Manifold.cube().set_properties(3, lambda position, old: [0.1, 0.3, 0.7])
    expected = manifold_to_trimesh(source)
    snapshot = _snapshot_export_source_at_protocol_boundary(source)
    assert isinstance(snapshot, Trimesh)
    source -= Manifold.cube().translate((0.5, 0.5, 0.5))
    npt.assert_array_equal(snapshot.vertices, expected.vertices)
    npt.assert_array_equal(snapshot.faces, expected.faces)
    npt.assert_array_equal(snapshot.visual.vertex_colors, expected.visual.vertex_colors)
    assert snapshot.volume == pytest.approx(1)


def test_native_export_adaptation_failure_is_structured():
    with patch(
        "scadview.mesh_loader_process.manifold_to_trimesh",
        side_effect=ValueError("adapter failed"),
    ):
        result = _snapshot_export_source_at_protocol_boundary(Manifold.cube())
    assert result == ExportError("ValueError", "adapter failed")


def test_native_transforms_leave_prior_source_and_readonly_output_unchanged():
    original = Manifold.cube()
    snapshot = original.to_mesh()
    source = original
    source -= Manifold.cube().translate((0.5, 0.5, 0.5))
    assert source is not original
    assert not snapshot.vert_properties.flags.writeable
    with pytest.raises(ValueError):
        snapshot.vert_properties[:] = 99
    actual = manifold_to_payload(original)
    npt.assert_array_equal(actual.bounds, [[0, 0, 0], [1, 1, 1]])


@pytest.mark.parametrize("cancel", [False, True])
def test_native_source_slot_coalesces_and_preserves_terminal_ownership(cancel):
    sources = [Manifold.cube().translate((index, 0, 0)) for index in range(10)]
    converting, generated, release = Event(), Event(), Event()
    converted = []
    results = LoadEventChannel(maxsize=20)
    worker = LoadWorker("module.py", results, generation=9)

    def generate(_path):
        yield sources[0]
        assert converting.wait(2)
        yield from sources[1:]
        generated.set()

    def convert(source, color=None):
        converted.append(source)
        if len(converted) == 1:
            converting.set()
            assert release.wait(3)
        return manifold_to_payload(source, color)

    with (
        patch("scadview.mesh_loader_process.ModuleLoader") as module,
        patch("scadview.mesh_loader_process.manifold_to_payload", side_effect=convert),
        patch(
            "scadview.mesh_loader_process.manifold_to_trimesh",
            side_effect=AssertionError,
        ),
    ):
        module.return_value.run_function.side_effect = generate
        worker.start()
        try:
            assert generated.wait(2)
            if cancel:
                worker.cancel()
        finally:
            release.set()
            worker.join(4)
    assert not worker.is_alive()
    values = drain(results)
    assert sum(value.complete for value in values) == 1
    final = values[-1]
    assert final.generation == 9
    assert final.sequence_number == 10
    if cancel:
        assert converted == sources[:1]
        assert final.phase is LoadPhase.CANCELLED
        assert worker.export_source is None
    else:
        assert converted == [sources[0], sources[-1]]
        assert final.phase is LoadPhase.FINAL
        assert worker.export_source is sources[-1]
        npt.assert_array_equal(final.payload.bounds, [[9, 0, 0], [10, 1, 1]])


def drain(results):
    values = []
    while True:
        try:
            values.append(results.get_nowait().result)
        except queue.Empty:
            return values
