import numpy as np
from trimesh.creation import icosphere

GOLF_BALL_RADIUS = 42.67 / 2
DIMPLE_RADIUS_FRACTION = 1 / 4
SUBDIVISIONS = 2


def create_mesh():
    ball = icosphere(subdivisions=SUBDIVISIONS, radius=GOLF_BALL_RADIUS)
    print(
        f"Created ball with {len(ball.vertices)} vertices and {len(ball.faces)} faces"
    )
    dimples = []
    for face in ball.faces:
        verts = ball.vertices[face]
        face_center = verts.mean(axis=0)
        dist_to_center = np.linalg.norm(verts[0] - face_center)
        dimple_r = dist_to_center * DIMPLE_RADIUS_FRACTION
        dimple_mesh = icosphere(
            subdivisions=SUBDIVISIONS, radius=dimple_r, center=face_center
        )
        dimple_mesh.apply_translation(face_center)
        ball = ball.difference(dimple_mesh)
        dimples.append(dimple_mesh)
    # return [ball] + dimples
    return ball
