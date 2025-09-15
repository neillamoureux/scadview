import numpy as np
from shapely import box
from trimesh.creation import sweep_polygon

WIDTH = 10.0
THICK = 0.5
SLICES = 100
OVERSHOOT = (
    SLICES + 1
) / SLICES  # Overshoot by a slice along the path to close properly
MID_RADIUS = 30.0  # Radius of the strip along the center line


def create_mesh():
    bx = box(-WIDTH / 2.0, -THICK / 2.0, WIDTH / 2.0, THICK / 2.0)
    theta = np.linspace(0, 2 * np.pi * (SLICES + 1) / SLICES, SLICES)
    twist = np.linspace(0, np.pi * (SLICES + 1) / SLICES, SLICES)
    circle = MID_RADIUS * np.column_stack(
        (
            np.cos(theta),
            np.sin(theta),
            np.zeros(SLICES),
        )
    )
    return sweep_polygon(bx, circle, twist, connect=True, cap=False)
