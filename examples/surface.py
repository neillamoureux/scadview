import os

from scadview import surface


def create_mesh():
    pixel_size = (388, 400)
    desired_x_size = 200.0
    height = 10.0
    scale = desired_x_size / pixel_size[0]
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    mesh = surface(
        os.path.join(parent_dir, "../src/scadview/resources/splash.png"),
        scale=(scale, scale, height),
        invert=True,
        base=0.0,
    )
    return mesh
