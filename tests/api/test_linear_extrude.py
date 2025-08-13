import numpy as np
import shapely.geometry as sg
import pytest
import trimesh

# Change this to your module path
from meshsee.api.linear_extrude import linear_extrude


def _rect_xy(w=2.0, h=1.0):
    x = w / 2
    y = h / 2
    return np.array([[-x, -y], [x, -y], [x, y], [-x, y], [-x, -y]], dtype=float)


def _square_3d(size=1.0, tilt_deg=20.0, axis="x"):
    """Return a tilted 3D loop (Nx3) to exercise 'project to XY'."""
    s = size / 2
    ring = np.array(
        [[-s, -s, 0], [s, -s, 0], [s, s, 0], [-s, s, 0], [-s, -s, 0]], dtype=float
    )
    th = np.deg2rad(tilt_deg)
    if axis == "x":
        R = np.array(
            [[1, 0, 0], [0, np.cos(th), -np.sin(th)], [0, np.sin(th), np.cos(th)]]
        )
    elif axis == "y":
        R = np.array(
            [[np.cos(th), 0, np.sin(th)], [0, 1, 0], [-np.sin(th), 0, np.cos(th)]]
        )
    else:
        R = np.array(
            [[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]]
        )
    return (ring @ R.T) + np.array([0, 0, 0.25])  # shift off z=0 slightly


def _bounds_z(mesh: trimesh.Trimesh):
    zmin = mesh.vertices[:, 2].min()
    zmax = mesh.vertices[:, 2].max()
    return float(zmin), float(zmax)


def test_basic_extrude_rectangle_center_default_false():
    prof = _rect_xy(2.0, 1.0)
    h = 10.0
    m = linear_extrude(prof, height=h)  # center should default to False
    assert m.is_watertight
    zmin, zmax = _bounds_z(m)
    assert np.isclose(zmin, 0.0, atol=1e-6)
    assert np.isclose(zmax, h, atol=1e-6)

    # Volume ≈ area * height
    area = sg.Polygon(prof).area
    assert np.isclose(m.volume, area * h, rtol=1e-3)


def test_center_true():
    prof = _rect_xy(2.0, 1.0)
    h = 8.0
    m = linear_extrude(prof, height=h, center=True)
    zmin, zmax = _bounds_z(m)
    assert np.isclose(zmin, -h / 2, atol=1e-6)
    assert np.isclose(zmax, h / 2, atol=1e-6)


def test_projection_from_3d_loop():
    prof3d = _square_3d(size=2.0, tilt_deg=30, axis="y")
    m = linear_extrude(prof3d, height=5.0)
    # Assert bottom face has same vertices as prof3d without the z coord
    # Do not check the last vertex on prof3d since it just closes the poly
    # and is removed by linear_extrude
    verts_near_z0 = m.vertices[np.isclose(m.vertices[:, 2], 0.0, atol=1e-6)]
    assert np.allclose(
        verts_near_z0,
        np.column_stack([prof3d[:-1, :2], np.zeros(prof3d.shape[0] - 1)]),
        atol=1e-6,
    )
    assert m.is_watertight
    # Bounds should start at z=0 when center=False
    zmin, zmax = _bounds_z(m)
    assert np.isclose(zmin, 0.0, atol=1e-6)
    assert zmax > 0


def test_hole_preserved_and_volume():
    outer = sg.Polygon(_rect_xy(4.0, 4.0))
    inner = sg.Polygon(_rect_xy(2.0, 2.0))
    poly_with_hole = sg.Polygon(outer.exterior.coords, [inner.exterior.coords])
    h = 3.0
    m = linear_extrude(poly_with_hole, height=h)
    assert m.is_watertight
    # volume should be (outer_area - inner_area) * height
    want = (outer.area - inner.area) * h
    assert np.isclose(m.volume, want, rtol=2e-3)


def test_fn_controls_slices_when_slices_none():
    prof = _rect_xy(2.0, 1.0)
    fn = 40
    m = linear_extrude(prof, height=5.0, slices=None, fn=fn)
    # number of distinct z levels should be fn+1
    z_levels = np.unique(np.round(m.vertices[:, 2], 9))
    assert len(z_levels) == fn + 1


def test_slices_exact_levels():
    prof = _rect_xy(2.0, 1.0)
    S = 7
    m = linear_extrude(prof, height=3.0, slices=S)
    z_levels = np.unique(np.round(m.vertices[:, 2], 9))
    assert len(z_levels) == S + 1


def test_twist_and_scale_affect_geometry():
    # Use an anisotropic rectangle so x/y scaling can be measured
    prof = _rect_xy(4.0, 2.0)
    h = 6.0
    sx, sy = 0.5, 1.5
    S = 60
    m = linear_extrude(prof, height=h, twist=180, scale=(sx, sy), slices=S)

    # Compare bottom vs top XY extents relative to centroid
    verts = m.vertices
    zmin, zmax = verts[:, 2].min(), verts[:, 2].max()
    bot = verts[np.isclose(verts[:, 2], zmin, atol=1e-7)][:, :2]
    top = verts[np.isclose(verts[:, 2], zmax, atol=1e-7)][:, :2]

    c_bot = bot.mean(axis=0)
    c_top = top.mean(axis=0)

    halfspan_bot = np.ptp(bot - c_bot, axis=0) / 2.0
    halfspan_top = np.ptp(top - c_top, axis=0) / 2.0

    # Allow some slack for triangulation/internal vertices
    rx = halfspan_top[0] / halfspan_bot[0]
    ry = halfspan_top[1] / halfspan_bot[1]
    assert np.isclose(rx, sx, rtol=0.1)
    assert np.isclose(ry, sy, rtol=0.1)


def test_top_and_bottom_normals():
    prof = _rect_xy(2.0, 1.0)
    h = 4.0
    m = linear_extrude(prof, height=h, slices=12)
    m.rezero()
    zmin, zmax = _bounds_z(m)

    # Pick faces whose centroids are near top or bottom
    centroids = m.triangles_center
    normals = m.face_normals
    top_mask = np.isclose(centroids[:, 2], zmax, atol=1e-6)
    bot_mask = np.isclose(centroids[:, 2], zmin, atol=1e-6)

    # Top faces should mostly point +Z, bottom faces mostly -Z
    top_dots = normals[top_mask] @ np.array([0, 0, 1.0])
    bot_dots = normals[bot_mask] @ np.array([0, 0, -1.0])
    # Require majority pointing correct way
    assert np.mean(top_dots > 0.5) > 0.8
    assert np.mean(bot_dots < -0.5) > 0.8


def test_watertight_and_manifold():
    prof = _rect_xy(3.0, 1.0)
    m = linear_extrude(prof, height=2.0, twist=90, slices=40, scale=0.8)
    assert m.is_watertight
    # Zero boundary edges implies manifold closed surface
    assert m.euler_number == 2  # sphere-like topology for a solid prism
