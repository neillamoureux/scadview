import os
from meshsee import surface

IMAGE_DIMS = (1000, 1000)
STAMP_DIMS = (20, 20, 5)
BASE_HEIGHT = 3
INVERT = True


def create_mesh():
    scale = (
        STAMP_DIMS[0] / IMAGE_DIMS[0],
        STAMP_DIMS[1] / IMAGE_DIMS[1],
        STAMP_DIMS[2],
    )
    img_path = os.path.join(os.path.dirname(__file__), "ladybug_thick_nodots.png")
    ladybug = surface(
        img_path, scale=scale, base=BASE_HEIGHT, invert=INVERT, binary_split=True
    )
    return ladybug
