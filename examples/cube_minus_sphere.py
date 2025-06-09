from trimesh.creation import box, icosphere


def create_mesh():
    scale = 100.0
    box_mesh = box([scale, scale, scale])
    box_mesh.metadata = {"meshsee": {"color": [1.0, 0.0, 1.0, 0.5]}}
    box_mesh2 = box([scale, scale, scale])
    box_mesh2.metadata = {"meshsee": {"color": [1.0, 0.0, 1.0, 0.5]}}
    sphere_mesh = icosphere(radius=0.4 * scale, subdivisions=3)
    sphere_mesh.metadata = {"meshsee": {"color": [1.0, 1.0, 0.0, 0.5]}}
    sphere_mesh2 = icosphere(radius=0.6 * scale, subdivisions=3)
    sphere_mesh2.metadata = {"meshsee": {"color": [1.0, 0.0, 1.0, 0.5]}}
    # return box_mesh.difference(sphere_mesh)
    final_mesh = box_mesh.difference(sphere_mesh)
    final_mesh.metadata = {"meshsee": {"color": [1.0, 0.0, 1.0, 0.5]}}
    solid_mesh = box_mesh.difference(sphere_mesh)
    print(solid_mesh.metadata)
    return [
        box_mesh,
        # sphere_mesh2.apply_translation([scale / 2, 0, 0]),
        sphere_mesh,
        box_mesh2.apply_translation([scale / 2, scale / 2, scale / 2]),
        box_mesh,
        final_mesh,
        # solid_mesh,
    ]
    # return sphere_mesh
    # return box_mesh
    # return solid_mesh
