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
)

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
    poly_2d = _as_polygon_2d(profile)
    faces2d, verts2d = _triangulate_poly(poly_2d)
    boundaries_verts_idx = _index_boundaries_verts(poly_2d, verts2d)
    layer_heights = _calc_layer_heights(height, center, slices)
    centroid = poly_2d.centroid
    layers_stack = _build_layers(
        twist, slices, final_scale, verts2d, layer_heights, centroid
    )
    faces = _make_faces(slices, faces2d, boundaries_verts_idx, len(verts2d))
    mesh = trimesh.Trimesh(
        vertices=layers_stack, faces=np.asarray(faces, dtype=np.int64), process=True
    )
    _clean_mesh(mesh)
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


def _as_polygon_2d(profile: ProfileType) -> sg.Polygon:
    """
    Accept:
      - shapely.Polygon (2D/3D) -> drop Z
      - Nx2 points
      - Nx3 coplanar points -> best-fit plane, right-handed, drop Z
    Returns shapely.Polygon oriented like OpenSCAD.
    """
    if isinstance(profile, sg.Polygon):
        ext2 = np.asarray([(x, y) for x, y, *rest in profile.exterior.coords])
        holes2 = [[(x, y) for x, y, *rest in r.coords] for r in profile.interiors]
        poly = sg.Polygon(ext2, holes2)
        if not poly.is_valid:
            poly = so.unary_union(poly.buffer(0))  # "tidy" the polygon
            if not isinstance(poly, sg.Polygon) or not poly.is_valid:
                raise ValueError("Invalid polygon after dropping Z.")
        return _orient_like_openscad(poly)

    pts = np.asarray(profile, dtype=np.float32)
    if pts.ndim != 2 or pts.shape[1] not in (2, 3):
        raise ValueError("profile must be shapely.Polygon or Nx2/Nx3 points")

    if pts.shape[1] == 3:
        pts = pts[:, :2]
    if not np.allclose(pts[0], pts[-1]):
        pts = np.vstack([pts, pts[0]])
    poly = sg.Polygon(pts)
    if not poly.is_valid:
        poly = so.unary_union(poly.buffer(0))
        if not isinstance(poly, sg.Polygon) or not poly.is_valid:
            raise ValueError("Invalid 2D polygon.")
    return _orient_like_openscad(poly)


def _orient_like_openscad(poly: sg.Polygon) -> sg.Polygon:
    # Exterior CCW, holes CW
    ext = np.asarray(poly.exterior.coords, dtype=np.float32)
    if not np.allclose(ext[0], ext[-1]):
        ext = np.vstack([ext, ext[0]])
    if _signed_area2d(ext[:-1]) < 0:  # CW -> flip
        ext = ext[::-1]
    holes = []
    for r in poly.interiors:
        h = np.asarray(r.coords, dtype=np.float32)
        if not np.allclose(h[0], h[-1]):
            h = np.vstack([h, h[0]])
        if _signed_area2d(h[:-1]) > 0:  # CCW -> flip
            h = h[::-1]
        holes.append(h)
    return sg.Polygon(ext, [h[:-1] for h in holes])  # type: ignore[reportInvalidArgumentType] - can't resolve


def _signed_area2d(ring_xy: NDArray[np.float32]) -> float:
    x, y = ring_xy[:, 0], ring_xy[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - y * np.roll(x, -1))


def _triangulate_poly(
    poly_2d: sg.Polygon,
) -> tuple[NDArray[np.int32], NDArray[np.float32]]:
    verts2d, faces2d = trimesh.creation.triangulate_polygon(poly_2d)
    verts2d = np.asarray(verts2d, dtype=np.float32)
    faces2d = np.asarray(faces2d, dtype=np.int32)
    return faces2d, verts2d


def _index_boundaries_verts(
    poly_2d: sg.Polygon, verts2d: NDArray[np.float32]
) -> list[NDArray[np.intp]]:
    boundaries = [np.asarray(poly_2d.exterior.coords[:-1])]
    boundaries += [np.asarray(r.coords[:-1]) for r in poly_2d.interiors]

    # map ring vertices -> triangulation indices
    kdt = KDTree(verts2d)
    boundaries_verts_idx = [kdt.query(r, k=1)[1] for r in boundaries]
    # ensure indices are intp
    return [np.asarray(bvi, dtype=np.intp) for bvi in boundaries_verts_idx]


def _calc_layer_heights(
    height: float, center: bool, slices: int
) -> NDArray[np.float32]:
    z0, z1 = (-height / 2.0, height / 2.0) if center else (0.0, height)
    return np.linspace(z0, z1, slices + 1, dtype=np.float32)


def _build_layers(
    twist: float,
    slices: int,
    final_scale: tuple[float, float],
    verts2d: NDArray[np.float32],
    layer_heights: NDArray[np.float32],
    centroid: sg.Point,
) -> NDArray[np.float32]:
    layers = np.empty((0, 3), dtype=np.float32)
    for i, layer_height in enumerate(layer_heights):
        t = i / slices
        sx = 1.0 + t * (final_scale[0] - 1.0)
        sy = 1.0 + t * (final_scale[1] - 1.0)
        angle = np.deg2rad(t * twist)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        rot_mat = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
        scale_mat = np.array([[sx, 0.0], [0.0, sy]])
        transform_mat = rot_mat @ scale_mat
        pts = (verts2d - [centroid.x, centroid.y]) @ transform_mat.T + [
            centroid.x,
            centroid.y,
        ]
        layer = np.column_stack([pts, np.full(len(pts), layer_height)])
        layers = np.append(layers, layer, axis=0)
    return layers


def _make_faces(
    slices: int,
    faces2d: NDArray[np.int32],
    boundaries_verts_idx: list[NDArray[np.intp]],
    layer_vert_count: int,
) -> list[list[int]]:
    # bottom + top
    faces = faces2d.tolist()
    faces.extend((faces2d + layer_vert_count * slices)[::-1, :].tolist())

    # walls (outer + holes)
    for boundary_verts_idx in boundaries_verts_idx:
        for slice_num in range(slices):
            lower_layer_start, upper_layer_start = (
                layer_vert_count * slice_num,
                layer_vert_count * (slice_num + 1),
            )
            for a, b in zip(boundary_verts_idx, np.roll(boundary_verts_idx, -1)):
                lower_a, upper_a = lower_layer_start + a, upper_layer_start + a
                lower_b, upper_b = lower_layer_start + b, upper_layer_start + b
                faces.append([lower_a, lower_b, upper_b])
                faces.append([lower_a, upper_b, upper_a])
    return faces


def _clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    return mesh
