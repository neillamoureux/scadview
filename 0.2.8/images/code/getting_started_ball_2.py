from trimesh.creation import icosphere


def create_mesh():
    return icosphere(radius=40, subdivisions=2)
