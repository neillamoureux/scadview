"""Measure the current Trimesh mesh-transfer and rendering path."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import pickle
import platform
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Any
from typing import Literal

import moderngl
import numpy as np
from trimesh import Trimesh

from scadview.mesh_payload import mesh_to_payload
from scadview.render.mesh_renderee import create_vao_from_arrays, expand_payload

METRIC_NAMES = (
    "vertex_count",
    "face_count",
    "mesh_count",
    "pickle_size_bytes",
    "trimesh_conversion_ms",
    "payload_conversion_ms",
    "post_create_mesh_to_first_frame_ms",
    "pickle_encode_ms",
    "pickle_decode_ms",
    "queue_round_trip_ms",
    "peak_memory_supported",
    "peak_memory_bytes",
    "renderer_preparation_ms",
    "renderer_upload_ms",
    "first_frame_ms",
    "gpu_measurement_error",
)


@dataclass(frozen=True)
class BenchmarkCase:
    """A deterministic mesh-transfer workload."""

    name: str
    create_meshes: Callable[[], list[Trimesh]]

    def meshes(self) -> list[Trimesh]:
        return self.create_meshes()


def main() -> None:
    arguments = _parse_arguments()
    report = run_benchmark(
        measure_gpu=not arguments.no_gpu,
        measure_peak_memory=not arguments.no_peak_memory,
        path=arguments.path,
    )
    _write_report(report, arguments.output)


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-gpu", action="store_true")
    parser.add_argument("--no-peak-memory", action="store_true")
    parser.add_argument("--path", choices=("trimesh", "payload"), default="trimesh")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def run_benchmark(
    *,
    measure_gpu: bool = True,
    measure_peak_memory: bool = True,
    path: Literal["trimesh", "payload"] = "trimesh",
) -> dict[str, Any]:
    """Measure every workload using the selected transfer representation."""
    return {
        "benchmark_version": 1,
        "command": "uv run python -m tools.mesh_transfer_benchmark",
        "environment": _environment_metadata(),
        "path": path,
        "cases": [
            measure_case(
                case,
                measure_gpu=measure_gpu,
                measure_peak_memory=measure_peak_memory,
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
    path: Literal["trimesh", "payload"] = "trimesh",
) -> dict[str, Any]:
    """Measure one workload without making timing assertions."""
    if measure_peak_memory:
        tracemalloc.start()
    try:
        measurement = _measure_case(case, measure_gpu, path)
        if measure_peak_memory:
            measurement["peak_memory_bytes"] = tracemalloc.get_traced_memory()[1]
            measurement["peak_memory_supported"] = True
        else:
            measurement["peak_memory_bytes"] = None
            measurement["peak_memory_supported"] = False
        return measurement
    finally:
        if measure_peak_memory:
            tracemalloc.stop()


def _measure_case(
    case: BenchmarkCase,
    measure_gpu: bool,
    path: Literal["trimesh", "payload"],
) -> dict[str, Any]:
    start = perf_counter()
    meshes = case.meshes()
    trimesh_conversion_ms = _elapsed_ms(start)
    aggregate_start = perf_counter()
    payloads, payload_conversion_ms = _to_payloads(meshes, path)
    transfer_values: list[Any] = meshes if path == "trimesh" else payloads
    serialized, encode_ms = _pickle_encode(transfer_values)
    _, decode_ms = _pickle_decode(serialized)
    queue_round_trip_ms = _queue_round_trip(transfer_values)
    prepared, preparation_ms = _prepare_renderer_data(meshes, payloads, path)
    gpu_measurements = _measure_gpu(prepared) if measure_gpu else _no_gpu_measurement()
    aggregate_ms = _elapsed_ms(aggregate_start)
    if gpu_measurements["first_frame_ms"] is None:
        aggregate_ms = None
    return {
        "case": case.name,
        "mesh_count": len(meshes),
        "vertex_count": sum(len(mesh.vertices) for mesh in meshes),
        "face_count": sum(len(mesh.faces) for mesh in meshes),
        "pickle_size_bytes": len(serialized),
        "trimesh_conversion_ms": trimesh_conversion_ms,
        "payload_conversion_ms": payload_conversion_ms,
        "post_create_mesh_to_first_frame_ms": aggregate_ms,
        "pickle_encode_ms": encode_ms,
        "pickle_decode_ms": decode_ms,
        "queue_round_trip_ms": queue_round_trip_ms,
        "renderer_preparation_ms": preparation_ms,
        **gpu_measurements,
    }


def _to_payloads(
    meshes: list[Trimesh], path: Literal["trimesh", "payload"]
) -> tuple[list[Any], float]:
    if path == "trimesh":
        return [], 0.0
    start = perf_counter()
    payloads = [mesh_to_payload(mesh) for mesh in meshes]
    return payloads, _elapsed_ms(start)


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
            np.concatenate((bottom_left + cells + 1, bottom_left + cells + 1)),
            np.concatenate((bottom_left + cells + 2, bottom_left + 1)),
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


def _pickle_encode(meshes: list[Trimesh]) -> tuple[bytes, float]:
    start = perf_counter()
    serialized = pickle.dumps(meshes, protocol=pickle.HIGHEST_PROTOCOL)
    return serialized, _elapsed_ms(start)


def _pickle_decode(serialized: bytes) -> tuple[list[Trimesh], float]:
    start = perf_counter()
    meshes = pickle.loads(serialized)
    return meshes, _elapsed_ms(start)


def _queue_round_trip(meshes: list[Trimesh]) -> float:
    queue: mp.Queue[list[Trimesh]] = mp.Queue(maxsize=1)
    try:
        start = perf_counter()
        queue.put(meshes)
        queue.get()
        return _elapsed_ms(start)
    finally:
        queue.close()
        queue.join_thread()


def _prepare_renderer_data(
    meshes: list[Trimesh],
    payloads: list[Any],
    path: Literal["trimesh", "payload"],
) -> tuple[list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]], float]:
    start = perf_counter()
    if path == "trimesh":
        prepared = [_expand_trimesh(mesh) for mesh in meshes]
    else:
        prepared = [expand_payload(payload) for payload in payloads]
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
            "renderer_upload_ms": None,
            "first_frame_ms": None,
            "gpu_measurement_error": str(error),
        }


def _measure_gpu_with_context(
    prepared: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
) -> dict[str, float | str | None]:
    context = moderngl.create_standalone_context()
    try:
        program = context.program(
            vertex_shader=_VERTEX_SHADER, fragment_shader=_FRAGMENT_SHADER
        )
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
            "renderer_upload_ms": upload_ms,
            "first_frame_ms": _elapsed_ms(start),
            "gpu_measurement_error": None,
        }
    finally:
        context.release()


def _no_gpu_measurement() -> dict[str, float | str | None]:
    return {
        "renderer_upload_ms": None,
        "first_frame_ms": None,
        "gpu_measurement_error": "GPU measurement disabled",
    }


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 3)


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
