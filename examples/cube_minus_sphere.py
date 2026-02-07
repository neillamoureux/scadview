from trimesh.creation import box, icosphere


def create_mesh():
    scale = 100.0
    box_mesh = box([scale, scale, scale]).subdivide()
    box_mesh2 = box([scale, scale, scale]).subdivide()
    sphere_mesh = icosphere(radius=0.4 * scale, subdivisions=3)
    sphere_mesh2 = icosphere(radius=0.6 * scale, subdivisions=3)
    return [
        box_mesh,
        sphere_mesh2.apply_translation([scale / 2, 0, 0]),
        sphere_mesh,
        box_mesh2.apply_translation([scale / 2, scale / 2, scale / 2]),
    ]
