from trimesh.creation import box, icosphere


def create_mesh():
    box_mesh = box([1.0, 1.0, 1.0])
    sphere_mesh = icosphere(radius=0.6)
    sphere_mesh.metadata = {"meshsee": {"color": [1.0, 0.0, 0.0, 0.5]}}
    return [sphere_mesh, box_mesh.difference(sphere_mesh)]
    # return sphere_mesh
