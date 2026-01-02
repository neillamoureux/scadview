from trimesh.creation import icosphere


def create_mesh():
    ball = icosphere(subdivisions=2, radius=42.67 / 2)
    print(
        f"Created ball with {len(ball.vertices)} vertices and {len(ball.faces)} faces"
    )
    dimple = icosphere(subdivisions=2, radius=1 / 2).apply_translation([0, 0, 42.67])
    return ball.difference(dimple)
