from meshsee import linear_extrude
import numpy as np
import shapely.geometry as sg


def create_mesh():
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

    return linear_extrude(
        poly,
        height=20,  # OpenSCAD: required
        center=True,  # OpenSCAD default
        convexity=10,  # accepted/ignored
        twist=270,  # total degrees
        slices=None,  # use fn if given; else 20
        scale=0.6,  # scalar or (sx, sy)
        fn=120,  # optional OpenSCAD-like override for slices
    )
