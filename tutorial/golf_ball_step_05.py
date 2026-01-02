from trimesh.creation import icosphere

from meshsee import set_mesh_color

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
    ).apply_translation([0, GOLF_BALL_RADIUS, 0])
    set_mesh_color(ball, [1, 0, 0], alpha=0.5)
    set_mesh_color(dimple, [0, 0, 1], alpha=0.5)
    # return ball.difference(dimple)
    return [ball, dimple]
