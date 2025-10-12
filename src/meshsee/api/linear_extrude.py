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
    slices = _determine_slice_value(slices, fn)
    final_scale = _determine_final_scale(scale)

    _raise_if_profile_incorrect_type(profile)
    poly = _as_poly_2d(profile)
    poly = _orient_polygon_rings(poly)
    verts_2d, poly_faces = trimesh.creation.triangulate_polygon(poly)
    centroid = poly.centroid
    faces = poly_faces.copy()[:, ::-1]

    # Find the boundary rings (exterior + interiors)
    # list of array(shape(mi, 2)) where mi is number of vertices in ring i
    # The length of the array is the number of rings (1 + number of holes)
    rings = [np.asarray(poly.exterior.coords[:-1])]
    rings += [np.asarray(r.coords[:-1]) for r in poly.interiors]
    # TODO: make sure shell ring is CCW and holes are CW

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
    # Build the layers:
    # 1. base layer, including triangulated faces and boundary vertices (already done)
    # 2. extruded boundary vertices only, one per slice except the top layer
    # 3. The offset of the slice vertices in the vertex array is:
    #    len(verts_2d) + sum([bndry_idx.shape[0] for bndry_idx in bndries_idxes]) * slice_index
    # 5. The top layer vertices are the same as the base layer vertices, but at z=2*height
    # 6. The top layer offset is:
    #    len(verts_2d) + sum([bndry_idx.shape[0] for bndry_idx in bndries_idxes]) * slices
    # 7. For each layer, stitch the rings to the next layer

    poly_vert_count = len(verts_2d)
    ring_verts_per_layer = sum([len(ri) for ri in rings_idxs])
    verts_3d = np.column_stack((verts_2d, np.zeros(len(verts_2d))))

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
    # stitch layers
    verts_index_offset_upper = 0
    for i in range(0, slices):
        verts_index_offset_lower = verts_index_offset_upper
        verts_index_offset_upper = poly_vert_count + i * ring_verts_per_layer
        ring_offset = 0
        for bi in rings_idxs:
            if i == 0:
                lower_idx = bi
            else:
                lower_idx = np.arange(
                    ring_offset,
                    ring_offset + len(bi),
                    dtype=np.int32,
                )
            if i == slices - 1:
                upper_idx = bi
            else:
                upper_idx = np.arange(
                    ring_offset,
                    ring_offset + len(bi),
                    dtype=np.int32,
                )
            new_faces = stitch_rings(
                lower_idx + verts_index_offset_lower,
                upper_idx + verts_index_offset_upper,
            )
            faces = np.vstack((faces, new_faces))
            ring_offset += len(bi)
    top_faces = poly_faces + poly_vert_count + (slices - 1) * ring_verts_per_layer
    faces = np.vstack((faces, top_faces))

    mesh = trimesh.Trimesh(vertices=verts_3d, faces=faces)
    if center:
        mesh = mesh.apply_translation((0, 0, -height / 2))
    return mesh


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


def _raise_if_profile_incorrect_type(profile: ProfileType):
    if not (
        isinstance(profile, sg.Polygon)
        or (
            isinstance(profile, np.ndarray)
            and profile.ndim == 2
            and profile.shape[1] in (2, 3)
            and profile.size > 0
        )
        or (
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
    ):
        raise TypeError(
            "profile must be a non-empty shapely.Polygon, Nx2/Nx3 ndarray, or list of 2/3-float tuples/lists"
        )


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


def stitch_rings(
    ring_a_idx: NDArray[np.intp], ring_b_idx: NDArray[np.intp]
) -> NDArray[np.intp]:
    assert ring_a_idx.shape[0] == ring_b_idx.shape[0]
    num_verts = ring_a_idx.shape[0]
    faces: list[int] = []
    for i in range(num_verts):
        next_i = (i + 1) % num_verts
        faces.append([ring_a_idx[i], ring_a_idx[next_i], ring_b_idx[next_i]])
        faces.append([ring_a_idx[i], ring_b_idx[next_i], ring_b_idx[i]])
    final_faces = np.array(faces, dtype=np.intp)
    return final_faces


# #  OpenSCAD-like extrude
# def linear_extrude(
#     profile: ProfileType,
#     height: float,
#     center: bool = False,
#     convexity: int | float | None = None,
#     twist: float = 0.0,
#     slices: int | None = None,
#     scale: float | tuple[float, float] | list[float] | NDArray[np.float32] = 1.0,
#     fn: int | None = None,  # mimic $fn fallback for slices
# ) -> trimesh.Trimesh:
#     """
#     OpenSCAD-like linear_extrude(project-to-XY first).

#     Signature & defaults mirror OpenSCAD:
#       linear_extrude(height, center=false, convexity, twist=0, slices, scale)

#     Notes:
#       - `convexity` is accepted but ignored (OpenSCAD uses it for preview rays).
#       - If `slices` is None and `fn` is provided (>0), uses `slices=fn`.
#         Otherwise defaults to 20 (a reasonable OpenSCAD-like fallback).
#       - `scale` may be scalar or (sx, sy).
#     """
#     slices = _determine_slice_value(slices, fn)
#     final_scale = _determine_final_scale(scale)
#     poly_2d = _as_polygon_2d(profile)
#     faces2d, verts2d = _triangulate_poly(poly_2d)
#     boundaries_verts_idx = _index_boundaries_verts(poly_2d, verts2d)
#     layer_heights = _calc_layer_heights(height, center, slices)
#     centroid = poly_2d.centroid
#     layers_stack = _build_layers(
#         twist, slices, final_scale, verts2d, layer_heights, centroid
#     )
#     faces = _make_faces(slices, faces2d, boundaries_verts_idx, len(verts2d))
#     mesh = trimesh.Trimesh(
#         vertices=layers_stack, faces=np.asarray(faces, dtype=np.int64), process=True
#     )
#     _clean_mesh(mesh)
#     return mesh


# def _determine_slice_value(slices: int | None, fn: int | None):
#     if slices is not None:
#         return slices
#     if fn is not None and fn > 0:
#         return fn
#     return DEFAULT_SLICES


# def _determine_final_scale(
#     scale: float | tuple[float, float] | list[float] | NDArray[np.float32],
# ) -> tuple[float, float]:
#     if not isinstance(scale, (tuple, list, np.ndarray)):
#         scale = (float(scale), float(scale))
#     return (float(scale[0]), float(scale[1]))


# def _as_polygon_2d(profile: ProfileType) -> sg.Polygon:
#     """
#     Accept:
#       - shapely.Polygon (2D/3D) -> drop Z
#       - Nx2 points
#       - Nx3 coplanar points -> best-fit plane, right-handed, drop Z
#     Returns shapely.Polygon oriented like OpenSCAD.
#     """
#     if isinstance(profile, sg.Polygon):
#         ext2 = np.asarray([(x, y) for x, y, *_rest in profile.exterior.coords])
#         holes2 = [[(x, y) for x, y, *_rest in r.coords] for r in profile.interiors]
#         poly = sg.Polygon(ext2, holes2)
#         if not poly.is_valid:
#             poly = so.unary_union(poly.buffer(0))  # "tidy" the polygon
#             if not isinstance(poly, sg.Polygon) or not poly.is_valid:
#                 raise ValueError("Invalid polygon after dropping Z.")
#         return _orient_like_openscad(poly)

#     pts = np.asarray(profile, dtype=np.float32)
#     if pts.ndim != 2 or pts.shape[1] not in (2, 3):
#         raise ValueError("profile must be shapely.Polygon or Nx2/Nx3 points")

#     if pts.shape[1] == 3:
#         pts = pts[:, :2]
#     if not np.allclose(pts[0], pts[-1]):
#         pts = np.vstack([pts, pts[0]])
#     poly = sg.Polygon(pts)
#     if not poly.is_valid:
#         poly = so.unary_union(poly.buffer(0))
#         if not isinstance(poly, sg.Polygon) or not poly.is_valid:
#             raise ValueError("Invalid 2D polygon.")
#     return _orient_like_openscad(poly)


# def _orient_like_openscad(poly: sg.Polygon) -> sg.Polygon:
#     # Exterior CCW, holes CW
#     ext = np.asarray(poly.exterior.coords, dtype=np.float32)
#     if not np.allclose(ext[0], ext[-1]):
#         ext = np.vstack([ext, ext[0]])
#     if _signed_area2d(ext[:-1]) < 0:  # CW -> flip
#         ext = ext[::-1]
#     holes = []
#     for r in poly.interiors:
#         h = np.asarray(r.coords, dtype=np.float32)
#         if not np.allclose(h[0], h[-1]):
#             h = np.vstack([h, h[0]])
#         if _signed_area2d(h[:-1]) > 0:  # CCW -> flip
#             h = h[::-1]
#         holes.append(h)
#     return sg.Polygon(ext, [h[:-1] for h in holes])  # type: ignore[reportInvalidArgumentType] - can't resolve


# def _triangulate_poly(
#     poly_2d: sg.Polygon,
# ) -> tuple[NDArray[np.int32], NDArray[np.float32]]:
#     verts2d, faces2d = trimesh.creation.triangulate_polygon(poly_2d)
#     verts2d = np.asarray(verts2d, dtype=np.float32)
#     faces2d = np.asarray(faces2d, dtype=np.int32)
#     return faces2d, verts2d


# def _index_boundaries_verts(
#     poly_2d: sg.Polygon, verts2d: NDArray[np.float32]
# ) -> list[NDArray[np.intp]]:
#     boundaries = [np.asarray(poly_2d.exterior.coords[:-1])]
#     boundaries += [np.asarray(r.coords[:-1]) for r in poly_2d.interiors]

#     # map ring vertices -> triangulation indices
#     kdt = KDTree(verts2d)
#     boundaries_verts_idx = [  # pyright: ignore[reportUnknownVariableType] - scipy fn
#         kdt.query(r, k=1)[1] for r in boundaries
#     ]
#     # ensure indices are intp
#     return [
#         np.asarray(bvi, dtype=np.intp)
#         for bvi in boundaries_verts_idx  # pyright: ignore[reportUnknownVariableType] - scipy
#     ]


# def _calc_layer_heights(
#     height: float, center: bool, slices: int
# ) -> NDArray[np.float32]:
#     z0, z1 = (-height / 2.0, height / 2.0) if center else (0.0, height)
#     return np.linspace(z0, z1, slices + 1, dtype=np.float32)


# def _build_layers(
#     twist: float,
#     slices: int,
#     final_scale: tuple[float, float],
#     verts2d: NDArray[np.float32],
#     layer_heights: NDArray[np.float32],
#     centroid: sg.Point,
# ) -> NDArray[np.float32]:
#     layers = np.empty((0, 3), dtype=np.float32)
#     for i, layer_height in enumerate(layer_heights):
#         t = i / slices
#         sx = 1.0 + t * (final_scale[0] - 1.0)
#         sy = 1.0 + t * (final_scale[1] - 1.0)
#         angle = np.deg2rad(t * twist)
#         cos_a, sin_a = np.cos(angle), np.sin(angle)
#         rot_mat = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
#         scale_mat = np.array([[sx, 0.0], [0.0, sy]])
#         transform_mat = rot_mat @ scale_mat
#         pts = (verts2d - [centroid.x, centroid.y]) @ transform_mat.T + [
#             centroid.x,
#             centroid.y,
#         ]
#         layer = np.column_stack([pts, np.full(len(pts), layer_height)])
#         layers = np.append(layers, layer, axis=0)
#     return layers


# def _make_faces(
#     slices: int,
#     faces2d: NDArray[np.int32],
#     boundaries_verts_idx: list[NDArray[np.intp]],
#     layer_vert_count: int,
# ) -> list[list[int]]:
#     # bottom + top
#     faces = faces2d.tolist()
#     faces.extend((faces2d + layer_vert_count * slices)[::-1, :].tolist())

#     # walls (outer + holes)
#     for boundary_verts_idx in boundaries_verts_idx:
#         for slice_num in range(slices):
#             lower_layer_start, upper_layer_start = (
#                 layer_vert_count * slice_num,
#                 layer_vert_count * (slice_num + 1),
#             )
#             for a, b in zip(boundary_verts_idx, np.roll(boundary_verts_idx, -1)):
#                 lower_a, upper_a = lower_layer_start + a, upper_layer_start + a
#                 lower_b, upper_b = lower_layer_start + b, upper_layer_start + b
#                 faces.append([lower_a, lower_b, upper_b])
#                 faces.append([lower_a, upper_b, upper_a])
#     return faces


# def _clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
#     mesh.update_faces(mesh.nondegenerate_faces())
#     mesh.remove_unreferenced_vertices()
#     mesh.merge_vertices()
#     return mesh
