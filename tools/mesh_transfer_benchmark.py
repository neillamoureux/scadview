"""Measure loader publication, process transfer, and mesh replacement."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import pickle
import platform
import subprocess
import tempfile
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Any, Literal, cast

import moderngl
import numpy as np
from trimesh import Trimesh

from scadview.mesh_loader_process import (
    ExportCommand,
    ExportResult,
    ExportWorker,
    FinalMeshSnapshot,
    LoadPhase,
    LoadResult,
    LoadWorker,
    MpExportResultQueue,
    MpLoadQueue,
    MpQueue,
)
from scadview.mesh_payload import MeshPayload, mesh_to_payload
from scadview.render.mesh_renderee import create_vao_from_arrays, expand_payload

PublicationPath = Literal["trimesh", "payload"]
PUBLICATION_PHASES = (
    "payload_conversion_ms",
    "source_signature_ms",
    "envelope_finalization_ms",
)
DISPLAY_LATENCY_PHASES = (
    "loader_publication_ms",
    "child_to_main_transfer_ms",
    "renderer_preparation_ms",
    "renderer_upload_ms",
    "first_frame_ms",
)
METRIC_NAMES = (
    "vertex_count",
    "face_count",
    "mesh_count",
    "pickle_size_bytes",
    "mesh_creation_ms",
    "payload_conversion_ms",
    "source_signature_ms",
    "source_signature_passes",
    "envelope_finalization_ms",
    "loader_publication_ms",
    "child_to_main_transfer_ms",
    "transfer_producer_pid",
    "transfer_consumer_pid",
    "post_mesh_creation_to_first_frame_ms",
    "peak_memory_supported",
    "main_process_peak_memory_bytes",
    "loader_publication_peak_memory_bytes",
    "renderer_preparation_ms",
    "gpu_context_shader_setup_ms",
    "renderer_upload_ms",
    "first_frame_ms",
    "gpu_measurement_error",
    "export_request_completion_ms",
    "retained_loader_process_rss_delta_bytes",
    "retained_loader_process_baseline_rss_bytes",
    "retained_loader_process_final_rss_bytes",
    "retained_source_kind",
    "retained_memory_supported",
    "retained_memory_error",
)


@dataclass(frozen=True)
class BenchmarkCase:
    """A deterministic mesh-transfer workload."""

    name: str
    create_meshes: Callable[[], list[Trimesh]]

    def meshes(self) -> list[Trimesh]:
        return self.create_meshes()


@dataclass(frozen=True)
class TrimeshTransferEnvelope:
    """Counterfactual final envelope carrying complete source meshes."""

    load_number: int
    generation: int
    sequence_number: int
    revision: int
    phase: LoadPhase
    payload: Trimesh | list[Trimesh]
    exportable: bool
    error: None
    debug: bool
    features: list[Any]
    parameters: list[Any]


@dataclass(frozen=True)
class PublicationTransfer:
    """A finalized envelope and its measured child-to-main publication stages."""

    envelope: LoadResult | TrimeshTransferEnvelope
    metrics: dict[str, Any]
    pickle_size_bytes: int
    producer_pid: int
    consumer_pid: int


def main() -> None:
    arguments = _parse_arguments()
    report = run_benchmark(
        measure_gpu=not arguments.no_gpu,
        measure_peak_memory=not arguments.no_peak_memory,
        measure_retained_source_memory=not arguments.no_retained_source_memory,
        path=arguments.path,
    )
    _write_report(report, arguments.output)


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-gpu", action="store_true")
    parser.add_argument("--no-peak-memory", action="store_true")
    parser.add_argument("--no-retained-source-memory", action="store_true")
    parser.add_argument("--path", choices=("trimesh", "payload"), default="trimesh")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def run_benchmark(
    *,
    measure_gpu: bool = True,
    measure_peak_memory: bool = True,
    measure_retained_source_memory: bool = True,
    path: PublicationPath = "trimesh",
) -> dict[str, Any]:
    """Measure every workload using the selected transfer representation."""
    return {
        "benchmark_version": 4,
        "command": "uv run --no-sync python -m tools.mesh_transfer_benchmark",
        "comparison_kind": "same-version-counterfactual",
        "transfer_boundary": "child-to-main-process",
        "multiprocessing_start_method": mp.get_start_method(),
        "display_latency_phases": list(DISPLAY_LATENCY_PHASES),
        "gpu_setup_scope": (
            "cold standalone context and shader setup per case; excluded from "
            "mesh replacement latency"
        ),
        "environment": _environment_metadata(),
        "path": path,
        "cases": [
            measure_case(
                case,
                measure_gpu=measure_gpu,
                measure_peak_memory=measure_peak_memory,
                measure_retained_source_memory=measure_retained_source_memory,
                path=path,
            )
            for case in discover_cases()
        ],
    }


def _environment_metadata() -> dict[str, str]:
    return {
        "machine": platform.machine(),
        "moderngl_version": version("moderngl"),
        "numpy_version": version("numpy"),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "trimesh_version": version("trimesh"),
    }


def discover_cases() -> tuple[BenchmarkCase, ...]:
    """Return all deterministic workloads in a stable comparison order."""
    return (
        BenchmarkCase("high-sharing-small", lambda: [_grid_mesh(32)]),
        BenchmarkCase("high-sharing-large", lambda: [_grid_mesh(128)]),
        BenchmarkCase("mixed-transparency", _mixed_transparency_meshes),
        BenchmarkCase("representative-large-model", _representative_large_model),
    )


def measure_case(
    case: BenchmarkCase,
    *,
    measure_gpu: bool = True,
    measure_peak_memory: bool = True,
    measure_retained_source_memory: bool = True,
    path: PublicationPath = "trimesh",
) -> dict[str, Any]:
    """Measure one workload without making timing assertions."""
    if measure_peak_memory:
        tracemalloc.start()
    try:
        measurement = _measure_case(
            case,
            measure_gpu,
            measure_peak_memory,
            path,
            measure_retained_source_memory,
        )
        if measure_peak_memory:
            measurement["main_process_peak_memory_bytes"] = (
                tracemalloc.get_traced_memory()[1]
            )
            measurement["peak_memory_supported"] = True
        else:
            measurement["main_process_peak_memory_bytes"] = None
            measurement["peak_memory_supported"] = False
        return measurement
    finally:
        if measure_peak_memory:
            tracemalloc.stop()


def _measure_case(
    case: BenchmarkCase,
    measure_gpu: bool,
    measure_peak_memory: bool,
    path: PublicationPath,
    measure_retained_source_memory: bool,
) -> dict[str, Any]:
    start = perf_counter()
    meshes = case.meshes()
    mesh_creation_ms = _elapsed_ms(start)
    transfer = _measure_publication_transfer(
        meshes,
        path,
        measure_peak_memory=measure_peak_memory,
    )
    prepared, preparation_ms = _prepare_renderer_data(transfer.envelope, path)
    gpu_measurements = _measure_gpu(prepared) if measure_gpu else _no_gpu_measurement()
    export_completion_ms = (
        _export_request_completion(meshes[-1]) if len(meshes) == 1 else None
    )
    retained_memory = _retained_source_memory_for_case(
        meshes, measure_retained_source_memory
    )
    measurement = {
        "case": case.name,
        "mesh_count": len(meshes),
        "vertex_count": sum(len(mesh.vertices) for mesh in meshes),
        "face_count": sum(len(mesh.faces) for mesh in meshes),
        "pickle_size_bytes": transfer.pickle_size_bytes,
        "mesh_creation_ms": mesh_creation_ms,
        **transfer.metrics,
        "transfer_producer_pid": transfer.producer_pid,
        "transfer_consumer_pid": transfer.consumer_pid,
        "export_request_completion_ms": export_completion_ms,
        "renderer_preparation_ms": preparation_ms,
        **retained_memory,
        **gpu_measurements,
    }
    measurement["post_mesh_creation_to_first_frame_ms"] = _compose_display_latency(
        measurement
    )
    return measurement


def _measure_publication_transfer(
    meshes: list[Trimesh],
    path: PublicationPath,
    *,
    measure_peak_memory: bool = False,
) -> PublicationTransfer:
    parent_connection, child_connection = mp.Pipe()
    result_queue: Any
    if path == "payload":
        result_queue = MpLoadQueue(maxsize=1, type_=LoadResult)
    else:
        result_queue = MpQueue(maxsize=1, type_=TrimeshTransferEnvelope)
    process = mp.Process(
        target=_publication_process,
        args=(child_connection, result_queue, meshes, path, measure_peak_memory),
    )
    process.start()
    child_connection.close()
    try:
        if not parent_connection.poll(30):
            raise RuntimeError("Timed out waiting for benchmark publication setup")
        publication = parent_connection.recv()
        if isinstance(publication, str):
            raise RuntimeError(publication)
        producer_pid, metrics, pickle_size_bytes = publication
        start = perf_counter()
        parent_connection.send("publish")
        envelope = result_queue.get(timeout=30)
        transfer_ms = _elapsed_ms(start)
        metrics["child_to_main_transfer_ms"] = transfer_ms
        return PublicationTransfer(
            envelope=envelope,
            metrics=metrics,
            pickle_size_bytes=pickle_size_bytes,
            producer_pid=producer_pid,
            consumer_pid=os.getpid(),
        )
    finally:
        parent_connection.close()
        process.join(timeout=30)
        if process.is_alive():
            process.terminate()
            process.join()
        result_queue.close()


def _publication_process(
    connection: Any,
    result_queue: Any,
    meshes: list[Trimesh],
    path: PublicationPath,
    measure_peak_memory: bool,
) -> None:
    if measure_peak_memory:
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        tracemalloc.start()
    try:
        envelope, metrics = _finalize_envelope(meshes, path)
        metrics["loader_publication_peak_memory_bytes"] = (
            tracemalloc.get_traced_memory()[1] if measure_peak_memory else None
        )
        connection.send((os.getpid(), metrics, _serialized_size(envelope)))
        if connection.recv() != "publish":
            raise RuntimeError("Unexpected benchmark publication command")
        result_queue.put(envelope)
    except Exception as error:
        connection.send(f"{type(error).__name__}: {error}")
    finally:
        if measure_peak_memory:
            tracemalloc.stop()
        connection.close()


def _finalize_envelope(
    meshes: list[Trimesh], path: PublicationPath
) -> tuple[LoadResult | TrimeshTransferEnvelope, dict[str, Any]]:
    source: Trimesh | list[Trimesh] = meshes[0] if len(meshes) == 1 else meshes
    start = perf_counter()
    payload = _publication_payload(source, path)
    payload_conversion_ms = _elapsed_ms(start) if path == "payload" else 0.0

    worker = object.__new__(LoadWorker)
    start = perf_counter()
    source_signature = worker._source_signature(source)
    source_signature_ms = _elapsed_ms(start)

    start = perf_counter()
    _progress_envelope(source, payload, path)
    envelope_finalization_ms = _elapsed_ms(start)

    start = perf_counter()
    source_changed = worker._source_changed(source, source_signature)
    source_signature_ms = round(source_signature_ms + _elapsed_ms(start), 3)
    if source_changed:
        raise RuntimeError("Deterministic benchmark source changed during finalization")

    start = perf_counter()
    envelope = _final_envelope(worker, source, payload, path)
    envelope_finalization_ms = round(envelope_finalization_ms + _elapsed_ms(start), 3)
    metrics: dict[str, Any] = {
        "payload_conversion_ms": payload_conversion_ms,
        "source_signature_ms": source_signature_ms,
        "source_signature_passes": 2,
        "envelope_finalization_ms": envelope_finalization_ms,
    }
    metrics["loader_publication_ms"] = _compose_display_latency(
        metrics, PUBLICATION_PHASES
    )
    return envelope, metrics


def _publication_payload(
    source: Trimesh | list[Trimesh], path: PublicationPath
) -> MeshPayload | list[MeshPayload] | Trimesh | list[Trimesh]:
    if path == "trimesh":
        return source
    if isinstance(source, list):
        source_meshes = cast(list[Trimesh], source)
        return [mesh_to_payload(mesh) for mesh in source_meshes]
    return mesh_to_payload(source)


def _progress_envelope(
    source: Trimesh | list[Trimesh],
    payload: MeshPayload | list[MeshPayload] | Trimesh | list[Trimesh],
    path: PublicationPath,
) -> LoadResult | TrimeshTransferEnvelope:
    if path == "trimesh":
        return TrimeshTransferEnvelope(
            1,
            1,
            1,
            1,
            LoadPhase.PROGRESS,
            source,
            False,
            None,
            isinstance(source, list),
            [],
            [],
        )
    load_payload = cast(MeshPayload | list[MeshPayload], payload)
    return LoadResult(
        1,
        1,
        payload=load_payload,
        error=None,
        generation=1,
        revision=1,
        phase=LoadPhase.PROGRESS,
        exportable=False,
        debug=isinstance(payload, list),
        features=[],
        parameters=[],
    )


def _final_envelope(
    worker: LoadWorker,
    source: Trimesh | list[Trimesh],
    payload: MeshPayload | list[MeshPayload] | Trimesh | list[Trimesh],
    path: PublicationPath,
) -> LoadResult | TrimeshTransferEnvelope:
    if path == "trimesh":
        return TrimeshTransferEnvelope(
            1,
            1,
            1,
            2,
            LoadPhase.FINAL,
            source,
            not isinstance(source, list),
            None,
            isinstance(source, list),
            [],
            [],
        )
    load_payload = cast(MeshPayload | list[MeshPayload], payload)
    snapshot: FinalMeshSnapshot | None = worker._final_snapshot(
        source, load_payload, None
    )
    return LoadResult(
        1,
        1,
        payload=load_payload,
        error=None,
        generation=1,
        revision=2,
        phase=LoadPhase.FINAL,
        exportable=snapshot is not None,
        debug=isinstance(payload, list),
        features=[],
        parameters=[],
    )


def _export_request_completion(mesh: Trimesh) -> float:
    result_queue = MpExportResultQueue(maxsize=0, type_=ExportResult)
    with tempfile.TemporaryDirectory() as directory:
        command = ExportCommand(1, 0, str(Path(directory) / "mesh.stl"))
        worker = ExportWorker(command, mesh, result_queue)
        start = perf_counter()
        worker.start()
        result = result_queue.get(timeout=10)
        worker.join(timeout=10)
    result_queue.close()
    if result.error is not None:
        raise RuntimeError(result.error.message)
    return _elapsed_ms(start)


def _retained_source_memory_for_case(
    meshes: list[Trimesh], enabled: bool
) -> dict[str, Any]:
    if len(meshes) != 1:
        return _unmeasured_retained_source_memory("list-or-debug-not-retained")
    if not enabled:
        return _unmeasured_retained_source_memory("single-final-source")
    return _retained_source_memory(meshes[-1])


def _retained_source_memory(mesh: Trimesh) -> dict[str, Any]:
    parent_connection, child_connection = mp.Pipe()
    process = mp.Process(
        target=_report_retained_source_memory, args=(child_connection,)
    )
    process.start()
    child_connection.close()
    try:
        parent_connection.send(mesh)
        if not parent_connection.poll(10):
            return _unavailable_retained_source_memory(
                "Timed out waiting for retained-memory measurement"
            )
        baseline, final, delta, error = parent_connection.recv()
        if error is not None:
            return _unavailable_retained_source_memory(error)
        if baseline is None or final is None or delta is None:
            return _unavailable_retained_source_memory(
                "Retained-memory measurement returned incomplete RSS values"
            )
        return _measured_retained_source_memory(baseline, final, delta)
    except (EOFError, OSError, TypeError, ValueError) as error:
        return _unavailable_retained_source_memory(f"{type(error).__name__}: {error}")
    finally:
        parent_connection.close()
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join()


def _report_retained_source_memory(connection: Any) -> None:
    mesh: Trimesh | None = None
    try:
        baseline, baseline_error = _current_rss_bytes()
        mesh = connection.recv()
        final, final_error = _current_rss_bytes()
        error = baseline_error or final_error
        delta = final - baseline if baseline is not None and final is not None else None
        connection.send((baseline, final, delta, error))
    finally:
        del mesh
        connection.close()


def _measured_retained_source_memory(
    baseline: int, final: int, delta: int
) -> dict[str, Any]:
    return {
        "retained_source_kind": "single-final-source",
        "retained_memory_supported": True,
        "retained_memory_error": None,
        "retained_loader_process_baseline_rss_bytes": baseline,
        "retained_loader_process_final_rss_bytes": final,
        "retained_loader_process_rss_delta_bytes": delta,
    }


def _unavailable_retained_source_memory(error: str) -> dict[str, Any]:
    return {
        "retained_source_kind": "single-final-source",
        "retained_memory_supported": False,
        "retained_memory_error": error,
        "retained_loader_process_baseline_rss_bytes": None,
        "retained_loader_process_final_rss_bytes": None,
        "retained_loader_process_rss_delta_bytes": None,
    }


def _unmeasured_retained_source_memory(source_kind: str) -> dict[str, Any]:
    return {
        "retained_source_kind": source_kind,
        "retained_memory_supported": None,
        "retained_memory_error": None,
        "retained_loader_process_baseline_rss_bytes": None,
        "retained_loader_process_final_rss_bytes": None,
        "retained_loader_process_rss_delta_bytes": None,
    }


def _current_rss_bytes() -> tuple[int | None, str | None]:
    try:
        output = subprocess.check_output(
            ["ps", "-o", "rss=", "-p", str(os.getpid())], text=True
        )
        return int(output.strip()) * 1024, None
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        return None, f"{type(error).__name__}: {error}"


def _grid_mesh(
    cells: int, *, offset: tuple[float, float, float] = (0, 0, 0)
) -> Trimesh:
    coordinates = np.linspace(-1.0, 1.0, cells + 1, dtype=np.float64)
    x_values, y_values = np.meshgrid(coordinates, coordinates, indexing="xy")
    vertices = np.column_stack(
        (x_values.ravel(), y_values.ravel(), np.zeros(x_values.size))
    )
    vertices += np.asarray(offset)
    row = np.arange(cells, dtype=np.int64)[:, None] * (cells + 1)
    column = np.arange(cells, dtype=np.int64)[None, :]
    bottom_left = (row + column).ravel()
    faces = np.column_stack(
        (
            np.concatenate((bottom_left, bottom_left + 1)),
            np.concatenate((bottom_left + cells + 1, bottom_left + cells + 2)),
            np.concatenate((bottom_left + cells + 2, bottom_left + cells + 1)),
        )
    )
    return Trimesh(vertices=vertices, faces=faces, process=False)


def _mixed_transparency_meshes() -> list[Trimesh]:
    meshes = [_grid_mesh(24, offset=(index * 2.5, 0, index)) for index in range(3)]
    _set_color(meshes[0], [0.2, 0.4, 0.8, 1.0])
    _set_color(meshes[1], [0.9, 0.3, 0.2, 0.45])
    _set_color(meshes[2], [0.3, 0.8, 0.4, 0.7])
    return meshes


def _representative_large_model() -> list[Trimesh]:
    return [
        _grid_mesh(128, offset=(x * 2.1, y * 2.1, z * 0.2))
        for x, y, z in ((0, 0, 0), (1, 0, 1), (0, 1, 2), (1, 1, 3), (2, 1, 4))
    ]


def _set_color(mesh: Trimesh, color: list[float]) -> None:
    mesh.metadata["scadview"] = {"color": color}


def _serialized_size(value: Any) -> int:
    return len(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))


def _prepare_renderer_data(
    envelope: LoadResult | TrimeshTransferEnvelope,
    path: PublicationPath,
) -> tuple[list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]], float]:
    start = perf_counter()
    values = envelope.payload
    items = values if isinstance(values, list) else [values]
    if path == "trimesh":
        prepared = [_expand_trimesh(cast(Trimesh, mesh)) for mesh in items]
    else:
        prepared = [expand_payload(cast(MeshPayload, payload)) for payload in items]
    return prepared, _elapsed_ms(start)


def _expand_trimesh(
    mesh: Trimesh,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    triangles = np.ascontiguousarray(mesh.triangles, dtype="f4")
    normals = np.ascontiguousarray(
        np.broadcast_to(mesh.triangles_cross[:, np.newaxis, :], triangles.shape),
        dtype="f4",
    )
    color = [128, 128, 128, 255]
    metadata = mesh.metadata
    if isinstance(metadata, dict) and metadata.get("scadview") is not None:
        color = (
            np.rint(np.asarray(metadata["scadview"]["color"]) * 255)
            .astype(np.uint8)
            .tolist()
        )
    colors = np.broadcast_to(
        np.asarray(color, dtype=np.uint8), (len(triangles), 3, 4)
    ).copy()
    edges = np.tile(
        np.array([255, 0, 0, 0, 255, 0, 0, 0, 255], dtype=np.uint8),
        (len(triangles), 1),
    )
    return triangles, normals, colors, edges


def _measure_gpu(
    prepared: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
) -> dict[str, float | str | None]:
    try:
        return _measure_gpu_with_context(prepared)
    except (moderngl.Error, OSError, RuntimeError, ValueError) as error:
        return {
            "gpu_context_shader_setup_ms": None,
            "renderer_upload_ms": None,
            "first_frame_ms": None,
            "gpu_measurement_error": str(error),
        }


def _measure_gpu_with_context(
    prepared: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
) -> dict[str, float | str | None]:
    setup_start = perf_counter()
    context = moderngl.create_standalone_context()
    try:
        program = context.program(
            vertex_shader=_VERTEX_SHADER, fragment_shader=_FRAGMENT_SHADER
        )
        context.finish()
        setup_ms = _elapsed_ms(setup_start)
        start = perf_counter()
        vaos = [
            create_vao_from_arrays(context, program, triangles, normals, colors, edges)
            for triangles, normals, colors, edges in prepared
        ]
        context.finish()
        upload_ms = _elapsed_ms(start)
        start = perf_counter()
        for vao in vaos:
            vao.render()
        context.finish()
        return {
            "gpu_context_shader_setup_ms": setup_ms,
            "renderer_upload_ms": upload_ms,
            "first_frame_ms": _elapsed_ms(start),
            "gpu_measurement_error": None,
        }
    finally:
        context.release()


def _no_gpu_measurement() -> dict[str, float | str | None]:
    return {
        "gpu_context_shader_setup_ms": None,
        "renderer_upload_ms": None,
        "first_frame_ms": None,
        "gpu_measurement_error": "GPU measurement disabled",
    }


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 3)


def _compose_display_latency(
    measurement: dict[str, Any],
    phases: tuple[str, ...] = DISPLAY_LATENCY_PHASES,
) -> float | None:
    values = [measurement.get(phase) for phase in phases]
    if any(not isinstance(value, (int, float)) for value in values):
        return None
    return round(sum(cast(float, value) for value in values), 3)


def _write_report(report: dict[str, Any], output: Path | None) -> None:
    serialized = json.dumps(report, indent=4, sort_keys=True)
    if output is None:
        print(serialized)
        return
    output.write_text(f"{serialized}\n", encoding="utf-8")


_VERTEX_SHADER = """
#version 330
in vec3 in_position;
in vec3 in_normal;
in vec4 in_color;
in vec3 in_edge_detect;
out vec3 normal;
out vec4 color;
out vec3 edge_detect;
void main() {
    normal = in_normal;
    color = in_color;
    edge_detect = in_edge_detect;
    gl_Position = vec4(in_position, 1.0);
}
"""

_FRAGMENT_SHADER = """
#version 330
in vec3 normal;
in vec4 color;
in vec3 edge_detect;
out vec4 frag_color;
void main() {
    frag_color = color + vec4(normal + edge_detect, 0.0) * 0.0;
}
"""


if __name__ == "__main__":
    main()
