from meshsee import linear_extrude
import numpy as np
import shapely.geometry as sg

POINTS = 5
R1, R2 = 1.0, 2.0
INNER_SCALE = 0.5
HEIGHT = 10.0
EXTRUDE_SCALE = 2.5
TWIST_ANGLE = 270
SLICES = 120


def create_mesh():
    # simple 2D star to demo twist/taper; will be projected if 3D is passed
    star = [
        (
            (
                R2 * np.cos(2 * np.pi * i / (2 * POINTS)),
                R2 * np.sin(2 * np.pi * i / (2 * POINTS)),
            )
            if i % 2 == 0
            else (
                R1 * np.cos(2 * np.pi * i / (2 * POINTS)),
                R1 * np.sin(2 * np.pi * i / (2 * POINTS)),
            )
        )
        for i in range(2 * POINTS)
    ]
    inner_star = [(INNER_SCALE * x, INNER_SCALE * y) for x, y in star]
    poly = sg.Polygon(star, [inner_star])

    return linear_extrude(
        poly,
        height=HEIGHT,  # OpenSCAD: required
        center=True,  # OpenSCAD default
        # convexity=10,  # accepted/ignored
        twist=TWIST_ANGLE,  # total degrees
        slices=SLICES,  # use fn if given; else 20
        scale=EXTRUDE_SCALE,  # scalar or (sx, sy)
        # fn=10,  # optional OpenSCAD-like override for slices
    )
