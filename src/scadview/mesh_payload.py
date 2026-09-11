"""Internal indexed mesh data used beyond source-geometry boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from trimesh import Trimesh

DEFAULT_COLOR = np.array([128, 128, 128, 255], dtype=np.uint8)
FLOAT32_MAX = np.finfo(np.float32).max
UINT32_MAX = np.iinfo(np.uint32).max


@dataclass(frozen=True)
class MeshPayload:
    """Compact indexed geometry and rendering summaries for one mesh."""

    vertices: NDArray[np.float32]
    faces: NDArray[np.uint32]
    face_normals: NDArray[np.float32]
    color: NDArray[np.uint8] | None
    bounds: NDArray[np.float32]
    scale: float


def mesh_to_payload(mesh: Trimesh) -> MeshPayload:
    """Convert a normalized source mesh to compact internal data."""
    vertices = _compact_float_array(mesh.vertices, "vertices")
    faces = _compact_faces(mesh.faces, len(vertices))
    face_normals = _compact_float_array(mesh.face_normals, "face normals")
    _validate_face_normals(face_normals, len(faces))
    bounds, scale = _bounds_and_scale(vertices)
    return MeshPayload(
        vertices=vertices,
        faces=faces,
        face_normals=face_normals,
        color=_mesh_color(mesh.metadata),
        bounds=bounds,
        scale=scale,
    )


def _compact_float_array(values: Any, name: str) -> NDArray[np.float32]:
    array = np.asarray(values)
    _validate_three_columns(array, name)
    if not np.issubdtype(array.dtype, np.number):
        raise ValueError(f"{name} must contain numeric values")
    if not np.isfinite(array).all() or np.abs(array).max(initial=0) > FLOAT32_MAX:
        raise ValueError(f"{name} must contain finite float32 values")
    return np.array(array, dtype=np.float32, order="C", copy=True)


def _validate_three_columns(array: NDArray[Any], name: str) -> None:
    if array.ndim != 2 or array.shape[1] != 3:
        raise ValueError(f"{name} must have shape (N, 3)")


def _compact_faces(values: Any, vertex_count: int) -> NDArray[np.uint32]:
    faces = np.asarray(values)
    _validate_three_columns(faces, "faces")
    _validate_face_values(faces, vertex_count)
    return np.array(faces, dtype=np.uint32, order="C", copy=True)


def _validate_face_values(faces: NDArray[Any], vertex_count: int) -> None:
    if not np.issubdtype(faces.dtype, np.number):
        raise ValueError("faces must contain numeric indices")
    if not np.isfinite(faces).all() or not np.equal(faces, np.floor(faces)).all():
        raise ValueError("faces must contain finite integer indices")
    if np.any(faces < 0):
        raise ValueError("faces cannot contain negative indices")
    if np.any(faces > UINT32_MAX):
        raise ValueError("faces must be representable as uint32")
    if np.any(faces >= vertex_count):
        raise ValueError("faces contain indices outside the vertex range")


def _validate_face_normals(normals: NDArray[np.float32], face_count: int) -> None:
    if len(normals) != face_count:
        raise ValueError("face normals must have one value per face")


def _bounds_and_scale(
    vertices: NDArray[np.float32],
) -> tuple[NDArray[np.float32], float]:
    if not len(vertices):
        return np.zeros((2, 3), dtype=np.float32), 0.0
    bounds = np.array([vertices.min(axis=0), vertices.max(axis=0)], dtype=np.float32)
    return np.ascontiguousarray(bounds), float(np.linalg.norm(bounds[1] - bounds[0]))


def _mesh_color(metadata: Any) -> NDArray[np.uint8]:
    color = _metadata_color(metadata)
    if color is None:
        return DEFAULT_COLOR.copy()
    return np.rint(np.asarray(color) * 255).astype(np.uint8)


def _metadata_color(metadata: Any) -> list[float] | None:
    if not isinstance(metadata, dict) or "scadview" not in metadata:
        return None
    scadview = metadata["scadview"]
    if scadview is None or "color" not in scadview:
        return None
    color = scadview["color"]
    if not isinstance(color, list) or len(color) != 4:
        raise ValueError("SCADview color must be a list of four floats")
    if not all(isinstance(component, float) for component in color):
        raise ValueError("SCADview color must be a list of four floats")
    if not all(0.0 <= component <= 1.0 for component in color):
        raise ValueError("SCADview color components must be in the range [0.0, 1.0]")
    return color


def payload_to_trimesh(payload: MeshPayload) -> Trimesh:
    """Reconstruct an export mesh from compact internal data."""
    mesh = Trimesh(
        vertices=payload.vertices.copy(), faces=payload.faces.copy(), process=False
    )
    if payload.color is not None:
        mesh.metadata["scadview"] = {"color": (payload.color / 255).tolist()}
    return mesh
