from enum import Enum, auto

import numpy as np
import shapely.geometry as sg
import shapely.ops as so
import trimesh
from numpy.typing import NDArray
from scipy.spatial import KDTree

ProfileType = (
    sg.Polygon
    | NDArray[np.float32]  # (N, 2) or (N, 3)
    | list[tuple[float, float]]
    | list[tuple[float, float, float]]
    | list[list[float]]
)


class _RingType(Enum):
    EXTERIOR = auto()
    INTERIOR = auto()


DEFAULT_SLICES = 20  # reasonable OpenSCAD-like fallback for slices


#  OpenSCAD-like extrude
def linear_extrude(
    profile: ProfileType,
    height: float,
    center: bool = False,
    convexity: int | float | None = None,
    twist: float = 0.0,
    slices: int | None = None,
    scale: float | tuple[float, float] | list[float] | NDArray[np.float32] = 1.0,
    fn: int | None = None,  # mimic $fn fallback for slices
) -> trimesh.Trimesh:
    """
    OpenSCAD-like linear_extrude(project-to-XY first).

    Signature & defaults mirror OpenSCAD:
      linear_extrude(height, center=false, convexity, twist=0, slices, scale)

    Notes:
      - `convexity` is accepted but ignored (OpenSCAD uses it for preview rays).
      - If `slices` is None and `fn` is provided (>0), uses `slices=fn`.
        Otherwise defaults to 20 (a reasonable OpenSCAD-like fallback).
      - `scale` may be scalar or (sx, sy).
    """
    _raise_if_profile_incorrect_type(profile)
    slices = _determine_slice_value(slices, fn)
    final_scale = _determine_final_scale(scale)

    poly = _as_poly_2d(profile)
    poly = _orient_polygon_rings(poly)
    verts_2d, poly_faces = trimesh.creation.triangulate_polygon(poly)
    verts_2d = verts_2d.astype(np.float32)

    rings = _collect_rings(poly, verts_2d)
    verts_3d = _build_layers(
        verts_2d, rings, slices, height, twist, final_scale, poly.centroid
    )

    # stitch layers
    faces = _stitch_layers(verts_2d, poly_faces, rings, slices)

    mesh = trimesh.Trimesh(vertices=verts_3d, faces=faces)
    if center:
        mesh = mesh.apply_translation((0, 0, -height / 2))
    return mesh


def _raise_if_profile_incorrect_type(profile: ProfileType):
    if not (
        _is_polygon(profile)
        or _is_ndarray_2dim_2d_or_3d_points(profile)
        or _is_list_2dim_2d_or_3d_points(profile)
    ):
        raise TypeError(
            "profile must be a non-empty shapely.Polygon, Nx2/Nx3 ndarray, or list of 2/3-float tuples/lists"
        )


def _is_polygon(profile: ProfileType) -> bool:
    return isinstance(profile, sg.Polygon)


def _is_ndarray_2dim_2d_or_3d_points(profile: ProfileType) -> bool:
    return (
        isinstance(profile, np.ndarray)
        and profile.ndim == 2
        and profile.shape[1] in (2, 3)
        and profile.size > 0
    )


def _is_list_2dim_2d_or_3d_points(profile: ProfileType) -> bool:
    return (
        isinstance(profile, list)
        and len(profile) > 0
        and (
            (
                all(
                    [
                        isinstance(vert, (tuple, list))  # type: ignore[reportUnecessaryIsInstance] - want to report to user if incorrect type
                        and len(vert) in (2, 3)
                        for vert in profile
                    ]
                )
            )
        )
    )


def _determine_slice_value(slices: int | None, fn: int | None):
    if slices is not None:
        return slices
    if fn is not None and fn > 0:
        return fn
    return DEFAULT_SLICES


def _determine_final_scale(
    scale: float | tuple[float, float] | list[float] | NDArray[np.float32],
) -> tuple[float, float]:
    if not isinstance(scale, (tuple, list, np.ndarray)):
        scale = (float(scale), float(scale))
    return (float(scale[0]), float(scale[1]))


def _as_poly_2d(profile: ProfileType) -> sg.Polygon:
    if isinstance(profile, sg.Polygon):
        poly = profile
    elif isinstance(profile, np.ndarray):
        if profile.shape[1] == 3:
            poly = sg.Polygon(profile[:, :2])
        else:
            poly = sg.Polygon(profile)
    else:
        if len(profile[0]) == 3:
            poly = sg.Polygon([p[:2] for p in profile])
        else:
            poly = sg.Polygon(profile)
    return poly


def _orient_polygon_rings(poly: sg.Polygon) -> sg.Polygon:
    # Exterior CCW, holes CW
    ext = np.asarray(poly.exterior.coords, dtype=np.float32)
    ext = _orient_ring(ext, _RingType.EXTERIOR)
    intrs = [
        _orient_ring(np.asarray(r.coords, dtype=np.float32), _RingType.INTERIOR)
        for r in poly.interiors
    ]
    return sg.Polygon(ext, intrs)


def _orient_ring(
    ring_xy: NDArray[np.float32], ring_type: _RingType
) -> NDArray[np.float32]:
    """
    We want exterior: CCW, signed area > 0, interior CW, signed area < 0
    """
    closed = _close_ring(ring_xy)
    area = _signed_area2d(closed)
    if ring_type == _RingType.EXTERIOR and area >= 0:
        return closed
    if ring_type == _RingType.INTERIOR and area <= 0:
        return closed
    return closed[::-1]


def _close_ring(ring_xy: NDArray[np.float32]) -> NDArray[np.float32]:
    if np.allclose(ring_xy[0], ring_xy[-1]):
        return ring_xy
    return np.vstack([ring_xy, ring_xy[0]])


def _signed_area2d(ring_xy: NDArray[np.float32]) -> float:
    x, y = ring_xy[:, 0], ring_xy[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - y * np.roll(x, -1))


def _collect_rings(
    poly: sg.Polygon, verts_2d: NDArray[np.float32]
) -> list[NDArray[np.float32]]:
    rings = [np.asarray(poly.exterior.coords[:-1])]
    rings += [np.asarray(r.coords[:-1]) for r in poly.interiors]
    return rings


def _build_layers(
    verts_2d: NDArray[np.float32],
    rings: list[NDArray[np.float32]],
    slices: int,
    height: float,
    twist: float,
    final_scale: tuple[float, float],
    centroid: sg.Point,
) -> NDArray[np.float32]:

    # botttom layer
    verts_3d = np.column_stack((verts_2d, np.zeros(len(verts_2d)))).astype(np.float32)

    # intermediate layers (slices - 1 of them)
    # Just add ring vertices at x = i * height / slices
    for i in range(1, slices):
        layer_verts = np.vstack(
            [
                np.column_stack((ring, np.ones(len(ring)) * i * height / slices))
                for ring in rings
            ],
            dtype=np.float32,
        )
        verts_3d = np.vstack(
            (
                verts_3d,
                _twist_scale_layer(
                    layer_verts, i, slices, twist, final_scale, centroid
                ),
            )
        )
    # Top layer
    top_layer = np.column_stack([verts_2d, np.ones(len(verts_2d)) * height]).astype(
        np.float32
    )
    verts_3d = np.vstack(
        [
            verts_3d,
            _twist_scale_layer(top_layer, slices, slices, twist, final_scale, centroid),
        ]
    )
    return verts_3d


def _twist_scale_layer(
    layer: NDArray[np.float32],
    layer_number: int,
    slices: int,
    twist: float,
    scale: tuple[float, float],
    centroid: sg.Point,
) -> NDArray[np.float32]:
    t = layer_number / slices
    sx = 1.0 + t * (scale[0] - 1.0)
    sy = 1.0 + t * (scale[1] - 1.0)
    angle = np.deg2rad(t * twist)
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    rot_mat = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
    scale_mat = np.array([[sx, 0.0], [0.0, sy]])
    transform_mat = rot_mat @ scale_mat
    pts = (layer[:, :2] - [centroid.x, centroid.y]) @ transform_mat.T + [
        centroid.x,
        centroid.y,
    ]
    return np.column_stack([pts, layer[:, 2]])


def _stitch_layers(
    verts_2d: NDArray[np.float32],
    poly_faces: NDArray[np.intp],
    rings: list[NDArray[np.float32]],
    slices: int,
) -> NDArray[np.intp]:
    rings_idxs = _find_boundary_rings_indexes(verts_2d, rings)
    poly_vert_count = len(verts_2d)
    ring_verts_per_layer = sum([len(ri) for ri in rings_idxs])
    verts_index_offset_upper = 0
    faces = poly_faces.copy()[:, ::-1]  # Reverse orientation for bottom

    for i in range(0, slices):
        # In each loop, determing how to index the rings
        # for slice; we need to stitch together the rings on the bottom edge of a slice
        # to the on on on the upper edge of the slice.
        # The bottom edge of the bottom slice and the top edge of the top slice
        # have the rings embedded in the fully polygon since the bottom
        # and top layer are a copy of the polygon.
        # These must use rings_indx to find the ring vertices
        # For other edges, the rings were added as a sequence, and so are
        # indexed simply by a range.
        verts_index_offset_lower = verts_index_offset_upper
        verts_index_offset_upper = poly_vert_count + i * ring_verts_per_layer
        ring_offset = 0
        for ring_idx in rings_idxs:
            if i == 0:  # Bottom edge of first slice
                lower_idx = ring_idx
            else:
                lower_idx = np.arange(
                    ring_offset,
                    ring_offset + len(ring_idx),
                    dtype=np.int32,
                )
            if i == slices - 1:  # Top edge of last slice
                upper_idx = ring_idx
            else:
                upper_idx = np.arange(
                    ring_offset,
                    ring_offset + len(ring_idx),
                    dtype=np.int32,
                )
            new_faces = _stitch_rings(
                (lower_idx + verts_index_offset_lower).astype(np.intp),
                (upper_idx + verts_index_offset_upper).astype(np.intp),
            )
            faces = np.vstack((faces, new_faces))
            ring_offset += len(ring_idx)
    top_faces = poly_faces + poly_vert_count + (slices - 1) * ring_verts_per_layer
    return np.vstack((faces, top_faces))


def _find_boundary_rings_indexes(
    verts_2d: NDArray[np.float32], rings: list[NDArray[np.float32]]
) -> list[NDArray[np.intp]]:
    # Find the boundary rings (exterior + interiors)
    # list of array(shape(mi, 2)) where mi is number of vertices in ring i
    # The length of the array is the number of rings (1 + number of holes)

    # map ring vertices -> triangulation indices
    kdt = KDTree(verts_2d)
    # list of array(shape(mi,), intp) where mi is number of vertices in ring i
    rings_idxs = [  # pyright: ignore[reportUnknownVariableType] - scipy fn
        kdt.query(r, k=1)[1] for r in rings
    ]  # list of len(bndries) of array(shape(m,), intp)
    # ensure indices are intp
    rings_idxs = [
        np.asarray(ri, dtype=np.intp)
        for ri in rings_idxs  # pyright: ignore[reportUnknownVariableType] - scipy
    ]  # list of len(bndries) of array(shape(m,), intp)
    return rings_idxs


def _stitch_rings(
    ring_a_idx: NDArray[np.intp], ring_b_idx: NDArray[np.intp]
) -> NDArray[np.intp]:
    assert ring_a_idx.shape[0] == ring_b_idx.shape[0]
    num_verts = ring_a_idx.shape[0]
    faces: NDArray[np.intp] = np.empty((2 * num_verts, 3), dtype=np.intp)
    for i in range(num_verts):
        next_i = (i + 1) % num_verts
        faces[2 * i] = np.array([ring_a_idx[i], ring_a_idx[next_i], ring_b_idx[next_i]])
        faces[2 * i + 1] = np.array([ring_a_idx[i], ring_b_idx[next_i], ring_b_idx[i]])
    return faces
