from trimesh.creation import box, icosphere

from meshsee import Color, set_mesh_color


def create_mesh():
    scale = 100.0
    box_mesh = set_mesh_color(
        box([scale, scale, scale]).subdivide(), Color.MAGENTA, 0.5
    )
    box_mesh2 = set_mesh_color(box([scale, scale, scale]).subdivide(), Color.GREEN, 0.5)
    sphere_mesh = set_mesh_color(
        icosphere(radius=0.4 * scale, subdivisions=3), Color.YELLOW, 0.5
    )
    sphere_mesh2 = set_mesh_color(
        icosphere(radius=0.6 * scale, subdivisions=3), Color.BEIGE, 0.5
    )
    # final_mesh = set_mesh_color(box_mesh.difference(sphere_mesh), Color.RED, 0.5)
    # solid_mesh = box_mesh.difference(sphere_mesh)
    return [
        box_mesh,
        sphere_mesh2.apply_translation([scale / 2, 0, 0]),
        sphere_mesh,
        box_mesh2.apply_translation([scale / 2, scale / 2, scale / 2]),
        # box_mesh,
        # final_mesh,
        # solid_mesh,
    ]
    # return sphere_mesh
    # return box_mesh
    # return solid_mesh
    # return final_mesh
