from trimesh.creation import icosphere


def create_mesh():
    ball = ball = icosphere(subdivisions=2, radius=42.67 / 2)
    print(
        f"Created ball with {len(ball.vertices)} vertices and {len(ball.faces)} faces"
    )
    return ball
