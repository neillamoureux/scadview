from trimesh.creation import icosphere

GOLF_BALL_RADIUS = 42.67 / 2
DIMPLE_RADIUS = 10
SUBDIVISIONS = 2


def create_mesh():
    ball = icosphere(subdivisions=SUBDIVISIONS, radius=GOLF_BALL_RADIUS)
    print(
        f"Created ball with {len(ball.vertices)} vertices and {len(ball.faces)} faces"
    )
    dimple = icosphere(
        subdivisions=SUBDIVISIONS, radius=DIMPLE_RADIUS
    ).apply_translation([0, GOLF_BALL_RADIUS / 2, 0])
    # return ball.difference(dimple)
    return [ball, dimple]
