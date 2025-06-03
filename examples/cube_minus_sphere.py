from trimesh.creation import box, icosphere


def create_mesh():
    scale = 100.0
    box_mesh = box([scale, scale, scale])
    sphere_mesh = icosphere(radius=0.6 * scale)
    sphere_mesh.metadata = {"meshsee": {"color": [1.0, 1.0, 0.0, 0.5]}}
    # box_mesh.difference(sphere_mesh)
    return [
        box_mesh.difference(sphere_mesh),
        sphere_mesh,
    ]
    # return sphere_mesh
