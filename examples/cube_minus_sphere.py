from trimesh.creation import box, icosphere


def create_mesh():
    scale = 100.0
    box_mesh = box([scale, scale, scale])
    sphere_mesh = icosphere(radius=0.6 * scale)
    sphere_mesh.metadata = {"meshsee": {"color": [1.0, 1.0, 0.0, 0.5]}}
    sphere_mesh2 = icosphere(radius=0.6 * scale)
    sphere_mesh2.metadata = {"meshsee": {"color": [1.0, 0.0, 1.0, 0.5]}}
    # return box_mesh.difference(sphere_mesh)
    return [
        # box_mesh.difference(sphere_mesh),
        sphere_mesh2.apply_translation([scale / 2, 0, 0]),
        sphere_mesh,
    ]
    return sphere_mesh
    return box_mesh
