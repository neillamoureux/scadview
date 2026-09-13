import os

import numpy as np
from trimesh import Trimesh

from scadview.mesh_loader_process import LoadPhase, LoadResult, LoadWorker
from tools.mesh_transfer_benchmark import (
    DISPLAY_LATENCY_PHASES,
    METRIC_NAMES,
    _compose_display_latency,
    _finalize_envelope,
    _grid_mesh,
    _measure_publication_transfer,
    discover_cases,
    measure_case,
    run_benchmark,
)


def test_discover_cases_includes_deterministic_transfer_shapes():
    cases = discover_cases()

    assert [case.name for case in cases] == [
        "high-sharing-small",
        "high-sharing-large",
        "mixed-transparency",
        "representative-large-model",
    ]
    assert all(case.meshes() for case in cases)


def test_cases_have_expected_vertex_and_face_counts():
    measurements = [measure_case(case, measure_gpu=False) for case in discover_cases()]

    assert measurements[0]["vertex_count"] == 1089
    assert measurements[0]["face_count"] == 2048
    assert measurements[1]["vertex_count"] == 16641
    assert measurements[1]["face_count"] == 32768
    assert measurements[2]["mesh_count"] == 3
    assert measurements[3]["face_count"] > measurements[1]["face_count"]


def test_grid_mesh_faces_are_non_degenerate():
    mesh = _grid_mesh(8)
    triangles = mesh.vertices[mesh.faces]
    double_areas = np.linalg.norm(
        np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]),
        axis=1,
    )

    assert np.all(double_areas > 0)


def test_run_benchmark_reports_environment_and_planned_metrics():
    report = run_benchmark(measure_gpu=False)

    assert report["benchmark_version"] == 3
    assert report["path"] == "trimesh"
    assert report["comparison_kind"] == "same-version-counterfactual"
    assert report["transfer_boundary"] == "child-to-main-process"
    assert report["environment"]["python_version"]
    assert report["environment"]["platform"]
    assert report["environment"]["numpy_version"]
    assert report["environment"]["trimesh_version"]
    assert report["command"]
    assert set(METRIC_NAMES) <= report["cases"][0].keys()


def test_run_benchmark_supports_compact_payload_path():
    report = run_benchmark(path="payload", measure_gpu=False, measure_peak_memory=False)

    assert report["path"] == "payload"
    assert report["cases"][0]["payload_conversion_ms"] >= 0
    assert report["cases"][0]["pickle_size_bytes"] < 100_000


def test_measurement_reports_one_queue_transfer_and_optional_memory():
    measurement = measure_case(discover_cases()[0], measure_gpu=False)

    assert measurement["pickle_size_bytes"] > 0
    assert measurement["mesh_creation_ms"] >= 0
    assert measurement["child_to_main_transfer_ms"] >= 0
    assert measurement["transfer_producer_pid"] != os.getpid()
    assert measurement["transfer_consumer_pid"] == os.getpid()
    assert measurement["renderer_preparation_ms"] >= 0
    assert measurement["renderer_upload_ms"] is None
    assert measurement["first_frame_ms"] is None
    assert measurement["post_mesh_creation_to_first_frame_ms"] is None
    assert measurement["main_process_peak_memory_bytes"] is not None
    assert measurement["loader_publication_peak_memory_bytes"] is not None
    assert measurement["export_request_completion_ms"] >= 0
    assert measurement["retained_source_kind"] == "single-final-source"
    assert measurement["retained_loader_process_rss_delta_bytes"] is not None
    assert measurement["retained_loader_process_baseline_rss_bytes"] > 0
    assert measurement["retained_loader_process_final_rss_bytes"] > 0


def test_aggregate_metric_is_emitted_for_both_transfer_paths():
    for path in ("trimesh", "payload"):
        measurement = measure_case(
            discover_cases()[0],
            measure_gpu=False,
            measure_peak_memory=False,
            path=path,
        )

        assert "post_mesh_creation_to_first_frame_ms" in measurement
        assert measurement["post_mesh_creation_to_first_frame_ms"] is None


def test_payload_publication_measures_production_finalization_in_child_process():
    transfer = _measure_publication_transfer([_grid_mesh(4)], "payload")

    assert transfer.producer_pid != os.getpid()
    assert transfer.consumer_pid == os.getpid()
    assert isinstance(transfer.envelope, LoadResult)
    assert transfer.envelope.phase is LoadPhase.FINAL
    assert transfer.envelope.exportable
    assert not _contains_trimesh(transfer.envelope.payload)
    assert transfer.metrics["payload_conversion_ms"] >= 0
    assert transfer.metrics["source_signature_ms"] >= 0
    assert transfer.metrics["source_signature_passes"] == 2
    assert transfer.metrics["envelope_finalization_ms"] >= 0
    assert transfer.metrics["loader_publication_ms"] == _compose_display_latency(
        transfer.metrics,
        (
            "payload_conversion_ms",
            "source_signature_ms",
            "envelope_finalization_ms",
        ),
    )


def test_payload_finalization_executes_both_production_signature_passes(monkeypatch):
    original_signature = LoadWorker._source_signature
    signed_sources = []

    def record_signature(worker, source):
        signed_sources.append(source)
        return original_signature(worker, source)

    monkeypatch.setattr(LoadWorker, "_source_signature", record_signature)

    envelope, metrics = _finalize_envelope([_grid_mesh(4)], "payload")

    assert isinstance(envelope, LoadResult)
    assert len(signed_sources) == 2
    assert metrics["source_signature_passes"] == len(signed_sources)


def test_display_latency_is_exactly_composed_from_documented_phases():
    measurement = {
        "loader_publication_ms": 1.25,
        "child_to_main_transfer_ms": 2.5,
        "renderer_preparation_ms": 3.75,
        "gpu_context_shader_setup_ms": 100.0,
        "renderer_upload_ms": 4.0,
        "first_frame_ms": 5.5,
    }

    assert "gpu_context_shader_setup_ms" not in DISPLAY_LATENCY_PHASES
    assert _compose_display_latency(measurement) == 17.0


def _contains_trimesh(value):
    if isinstance(value, Trimesh):
        return True
    if isinstance(value, list):
        return any(_contains_trimesh(item) for item in value)
    return False


def test_memory_measurement_can_be_disabled():
    measurement = measure_case(
        discover_cases()[0], measure_gpu=False, measure_peak_memory=False
    )

    assert measurement["peak_memory_supported"] is False
    assert measurement["main_process_peak_memory_bytes"] is None
    assert measurement["loader_publication_peak_memory_bytes"] is None
    assert measurement["retained_source_kind"] == "single-final-source"
    assert measurement["retained_loader_process_rss_delta_bytes"] is not None


def test_list_cases_report_separate_non_retained_memory_and_export_metrics():
    measurement = measure_case(
        discover_cases()[2],
        measure_gpu=False,
        measure_peak_memory=False,
        measure_retained_source_memory=True,
    )

    assert measurement["retained_source_kind"] == "list-or-debug-not-retained"
    assert measurement["retained_loader_process_rss_delta_bytes"] is None
    assert measurement["export_request_completion_ms"] is None
