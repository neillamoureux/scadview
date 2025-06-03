from trimesh.creation import box, icosphere


def create_mesh():
    box_mesh = box([1.0, 1.0, 1.0])
    sphere_mesh = icosphere(radius=0.6)
    return [box_mesh.difference(sphere_mesh), sphere_mesh]
