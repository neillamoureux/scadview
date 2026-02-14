import numpy as np
import shapely.affinity as sa
import shapely.geometry as sg
import shapely.ops as so

from scadview import linear_extrude, set_mesh_color

WIDTH = 80.0
DEPTH = 70.0
HEIGHT = 140.0
TWIST = 90.0
SCALE = 1.5
SLICES = 120
FN = 96


def create_mesh():
    profile = heart_profile(WIDTH, DEPTH)
    vase = linear_extrude(
        profile,
        height=HEIGHT,
        center=False,
        twist=TWIST,
        slices=SLICES,
        scale=SCALE,
    )
    set_mesh_color(vase, (1.0, 0.1, 0.1))
    return vase


def heart_profile(width: float, depth: float) -> sg.Polygon:
    """
    Build a heart shape that fits inside a width x depth rectangle.
    The two lobes are half-circles (full circles used for union).
    """
    if width <= 0 or depth <= 0:
        raise ValueError("width and depth must be > 0")

    left_center, right_center, radius = _lobe_centers(width, depth)
    left_lobe, right_lobe = _lobe_circles(left_center, right_center, radius)
    bottom_point = (0.0, -depth / 2.0)
    triangle = _tangent_triangle(left_center, right_center, radius, bottom_point)

    heart = so.unary_union([left_lobe, right_lobe, triangle])
    if isinstance(heart, sg.MultiPolygon):
        heart = max(heart.geoms, key=lambda geom: geom.area)
    heart = sg.Polygon(heart.exterior.coords)

    # Ensure final bounds fit exactly (numerical safety).
    heart = _fit_to_bounds(heart, width, depth)
    # Shift to centroid so twist occurs about the base centroid.
    return _center_on_centroid(heart)


def _lobe_centers(
    width: float, depth: float
) -> tuple[tuple[float, float], tuple[float, float], float]:
    r = width / 4.0
    top_y = depth / 2.0
    center_y = top_y - r
    left_center = (-r, center_y)
    right_center = (r, center_y)
    return left_center, right_center, r


def _lobe_circles(
    left_center: tuple[float, float],
    right_center: tuple[float, float],
    radius: float,
) -> tuple[sg.Polygon, sg.Polygon]:
    left_lobe = sg.Point(left_center).buffer(radius, resolution=FN)
    right_lobe = sg.Point(right_center).buffer(radius, resolution=FN)
    return left_lobe, right_lobe


def _tangent_triangle(
    left_center: tuple[float, float],
    right_center: tuple[float, float],
    radius: float,
    bottom_point: tuple[float, float],
) -> sg.Polygon:
    left_tangent = _tangent_point_from_external_point(left_center, radius, bottom_point)
    right_tangent = _tangent_point_from_external_point(
        right_center, radius, bottom_point
    )
    return sg.Polygon([left_tangent, right_tangent, bottom_point])


def _tangent_point_from_external_point(
    center: tuple[float, float],
    radius: float,
    point: tuple[float, float],
) -> tuple[float, float]:
    cx, cy = center
    px, py = point
    vx = px - cx
    vy = py - cy
    d = (vx * vx + vy * vy) ** 0.5
    if d <= radius:
        raise ValueError("point must be outside circle for tangent construction")
    theta = np.arctan2(vy, vx)
    alpha = np.arccos(radius / d)
    t1 = (cx + radius * np.cos(theta + alpha), cy + radius * np.sin(theta + alpha))
    t2 = (cx + radius * np.cos(theta - alpha), cy + radius * np.sin(theta - alpha))
    return t1 if t1[1] < t2[1] else t2


def _fit_to_bounds(poly: sg.Polygon, width: float, depth: float) -> sg.Polygon:
    bounds = poly.bounds  # (minx, miny, maxx, maxy)
    scale_x = width / (bounds[2] - bounds[0])
    scale_y = depth / (bounds[3] - bounds[1])
    return sa.scale(poly, xfact=scale_x, yfact=scale_y, origin="center")


def _center_on_centroid(poly: sg.Polygon) -> sg.Polygon:
    centroid = poly.centroid
    return sa.translate(poly, xoff=-centroid.x, yoff=-centroid.y)


if __name__ == "__main__":
    create_mesh()
