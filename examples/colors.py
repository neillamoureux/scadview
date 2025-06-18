from meshsee import Color, set_mesh_color, text


def create_mesh():
    all_meshes = []
    for i, color in enumerate(Color):
        mesh = set_mesh_color(text(color.name), color, 1.0).apply_translation(
            [0, (len(Color) - i) * 15, 0]
        )
        all_meshes.append(mesh)
    return all_meshes
