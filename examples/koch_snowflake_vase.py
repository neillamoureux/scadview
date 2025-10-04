import logging

import numpy as np
import shapely.geometry as sg
import trimesh.repair

from meshsee import linear_extrude

KOCH_DEFAULT_BUMP_LENGTH_FRACTION = np.sqrt(
    1.0 / 3.0**2 - 1.0 / 6.0**2
)  # 1/3 edge length, 1/6 from midpoint
# Bump length multiplier for the Koch snowflake
# Less that 0.58 does not create a bump, but a straight edge
# More than 1.75-ish creates intersecting edges
BUMP_LENGTH_FRACTION_MULTIPLIER = 1.0
ORDER = 4
R = 50
HEIGHT = 150
TWIST = 0
# TWIST = 60
TRIANGLE_VERTEX_COUNT = 3
SLICES = 20
# SCALE = (1.1, 1.5)  # scalar or (sx, sy)
SCALE = (1.0, 1.0)  # scalar or (sx, sy)


def create_mesh():
    radial_angles = np.linspace(0, 2 * np.pi, TRIANGLE_VERTEX_COUNT, endpoint=False)
    vertices_2d = np.column_stack(
        (R * np.cos(radial_angles), R * np.sin(radial_angles))
    )
    for i in range(ORDER):
        vertices_2d = _increase_order(vertices_2d)

    koch = linear_extrude(
        sg.Polygon(vertices_2d),
        height=HEIGHT,
        center=False,
        convexity=ORDER,
        twist=TWIST,
        slices=SLICES,
        scale=SCALE,
    )
    logging.info(f"koch is watertight: {koch.is_watertight}")
    logging.info(f"koch is volume: {koch.is_volume}")
    logging.info(f"koch is_winding_consistent: {koch.is_winding_consistent}")
    return koch


def _increase_order(vertices_2d):
    vertices_2d = [
        add_midpoint_bump(
            edges[0],
            edges[1],
            KOCH_DEFAULT_BUMP_LENGTH_FRACTION * BUMP_LENGTH_FRACTION_MULTIPLIER,
        )
        for edges in zip(vertices_2d, np.roll(vertices_2d, -1, axis=0))
    ]
    return np.concatenate(vertices_2d, axis=0)


def add_midpoint_bump(
    vertex_a, vertex_b, new_edge_length_fraction=KOCH_DEFAULT_BUMP_LENGTH_FRACTION
):
    midpoint = (vertex_a + vertex_b) / 2.0
    delta_vector = vertex_b - vertex_a
    edge_length = np.linalg.norm(delta_vector)
    new_edge_length = edge_length * new_edge_length_fraction

    # koch adds 2 points, each at 1/3 of the edge length, both 1/6 from the midpoint
    perp_vector_needed_length = np.sqrt(new_edge_length**2 - (edge_length / 6.0) ** 2)
    perp_vector = np.array([delta_vector[1], -delta_vector[0]])
    perp_vector /= np.linalg.norm(perp_vector)
    perp_vector *= perp_vector_needed_length  # Normalize to unit length
    new_vertex_0 = vertex_a + delta_vector / 3.0
    new_vertex_1 = midpoint + perp_vector
    new_vertex_2 = vertex_b - delta_vector / 3.0
    return np.array([vertex_a, new_vertex_0, new_vertex_1, new_vertex_2])


if __name__ == "__main__":
    create_mesh()
