from time import sleep

from trimesh.creation import box


def create_mesh():
    b = box([10, 10, 20])
    for _ in range(100):
        yield b
        sleep(0.1)
        b.apply_translation([0.2, 0, 0])
