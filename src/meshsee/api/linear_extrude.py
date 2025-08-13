from typing import Union

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


# ---------- helpers (unchanged in spirit) ----------
def _signed_area2d(ring_xy: NDArray[np.float32]) -> float:
    x, y = ring_xy[:, 0], ring_xy[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - y * np.roll(x, -1))


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
    return sg.Polygon(ext, [h[:-1] for h in holes])


def _as_polygon_2d(profile: ProfileType):
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

    pts = np.asarray(profile, dtype=float)
    if pts.ndim != 2 or pts.shape[1] not in (2, 3):
        raise ValueError("profile must be shapely.Polygon or Nx2/Nx3 points")

    if pts.shape[1] == 2:
        if not np.allclose(pts[0], pts[-1]):
            pts = np.vstack([pts, pts[0]])
        poly = sg.Polygon(pts)
        if not poly.is_valid:
            poly = so.unary_union(poly.buffer(0))
            if not isinstance(poly, sg.Polygon) or not poly.is_valid:
                raise ValueError("Invalid 2D polygon.")
        return _orient_like_openscad(poly)

    # Nx3 -> best-fit plane (right-handed)
    c = pts.mean(axis=0)
    X = pts - c
    _, _, Vt = np.linalg.svd(X, full_matrices=False)
    Q = Vt.T
    if np.linalg.det(Q) < 0:
        Q[:, 2] *= -1.0  # force right-handed
    local = X @ Q
    ring2d = local[:, :2]
    if not np.allclose(ring2d[0], ring2d[-1]):
        ring2d = np.vstack([ring2d, ring2d[0]])
    poly = sg.Polygon(ring2d)
    if not poly.is_valid:
        poly = so.unary_union(poly.buffer(0))
        if not isinstance(poly, sg.Polygon) or not poly.is_valid:
            raise ValueError("Projected profile isn't a valid simple polygon.")
    return _orient_like_openscad(poly)


# ---------- OpenSCAD-parity extrude ----------
def linear_extrude(
    profile,
    height: float,
    center: bool = False,
    convexity: int | float | None = None,
    twist: float = 0.0,
    slices: int | None = None,
    *,
    scale: float | tuple[float, float] | list[float] | NDArray[np.float32] = 1.0,
    fn: int | None = None,  # mimic $fn fallback for slices if you want
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
    poly_2d = _as_polygon_2d(profile)

    # resolve slices like OpenSCAD-ish
    if slices is None:
        if fn is not None and fn > 0:
            slices = int(fn)
        else:
            slices = 20  # pragmatic default when $fn is effectively 0/unspecified

    # triangulate face (handles holes)
    verts2d, faces2d = trimesh.creation.triangulate_polygon(poly_2d)
    v2 = np.asarray(verts2d)
    faces2d = np.asarray(faces2d, dtype=np.int64)

    # boundary loops for walls
    rings = [np.asarray(poly_2d.exterior.coords[:-1])]
    rings += [np.asarray(r.coords[:-1]) for r in poly_2d.interiors]

    # map ring vertices -> triangulation indices

    kdt = KDTree(v2)
    ring_idx = [kdt.query(r, k=1)[1] for r in rings]

    z0, z1 = (-height / 2.0, height / 2.0) if center else (0.0, height)
    zs = np.linspace(z0, z1, slices + 1)

    cx, cy = poly_2d.centroid.x, poly_2d.centroid.y
    if not isinstance(scale, (tuple, list, np.ndarray)):
        scale = (float(scale), float(scale))
    sx_final, sy_final = map(float, scale)

    # build layers with twist/taper
    layers = []
    for i, z in enumerate(zs):
        t = i / slices
        sx = 1.0 + t * (sx_final - 1.0)
        sy = 1.0 + t * (sy_final - 1.0)
        ang = np.deg2rad(t * twist)
        ca, sa = np.cos(ang), np.sin(ang)
        R = np.array([[ca, -sa], [sa, ca]])
        S = np.array([[sx, 0.0], [0.0, sy]])
        M = R @ S
        pts = (v2 - [cx, cy]) @ M.T + [cx, cy]
        layer = np.column_stack([pts, np.full(len(pts), z)])
        layers.append(layer)
    V = np.vstack(layers)
    N = len(v2)

    faces = []
    # bottom & top
    faces.extend(faces2d.tolist())
    faces.extend((faces2d + N * slices)[::-1, :].tolist())

    # walls (outer + holes)
    for loop in ring_idx:
        for k in range(slices):
            o0, o1 = N * k, N * (k + 1)
            for a, b in zip(loop, np.roll(loop, -1)):
                a0, a1 = o0 + a, o1 + a
                b0, b1 = o0 + b, o1 + b
                faces.append([a0, b0, b1])
                faces.append([a0, b1, a1])

    mesh = trimesh.Trimesh(
        vertices=V, faces=np.asarray(faces, dtype=np.int64), process=True
    )
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    # mesh.rezero()
    return mesh


# ---------- Example ----------
if __name__ == "__main__":
    # simple 2D star to demo twist/taper; will be projected if 3D is passed
    n = 5
    r1, r2 = 1.0, 2.0
    star = [
        (
            (r2 * np.cos(2 * np.pi * i / (2 * n)), r2 * np.sin(2 * np.pi * i / (2 * n)))
            if i % 2 == 0
            else (
                r1 * np.cos(2 * np.pi * i / (2 * n)),
                r1 * np.sin(2 * np.pi * i / (2 * n)),
            )
        )
        for i in range(2 * n)
    ]
    poly = sg.Polygon(star)

    m = linear_extrude(
        poly,
        height=20,  # OpenSCAD: required
        center=False,  # OpenSCAD default
        convexity=10,  # accepted/ignored
        twist=270,  # total degrees
        slices=None,  # use fn if given; else 20
        scale=0.6,  # scalar or (sx, sy)
        fn=120,  # optional OpenSCAD-like override for slices
    )
    m.show()
