from trimesh.creation import box, cylinder

# x = width direction
# y = height direction
# z = depth direction

INNER_WIDTH = 6.36
OUTER_WIDTH = 8.22
INNER_HEIGHT = 8.96
OUTER_HEIGHT = 9.22
WALL_THICKNESS = 0.45
INNER_SIDE_HEIGHT = 6.39
DEPTH = 12.14
CAP_THICKNESS = 0.50
SCREW_HOLE_DIAMETER = 4.8

ARC_HEIGHT = (INNER_HEIGHT - INNER_SIDE_HEIGHT) / 2.0


def create_mesh():
    arc_radius = calc_arc_radius(INNER_WIDTH, ARC_HEIGHT)
    inner_shape = (
        box(extents=(INNER_WIDTH, INNER_SIDE_HEIGHT, DEPTH))
        .union(
            cylinder(  # Top and bottom arcs
                radius=arc_radius,
                height=DEPTH,
            )
            .intersection(  # remove middle part of cylinder
                box((INNER_SIDE_HEIGHT, 2 * arc_radius, DEPTH))
            )
            .apply_translation((0, INNER_SIDE_HEIGHT / 2 - arc_radius + ARC_HEIGHT, 0))
        )
        .apply_translation((0, 0, CAP_THICKNESS))  # raise to account for cap thickness
    )
    # outer shape is inner shape plus wall thickness around it, but no cap
    outer_arc_radius = arc_radius + WALL_THICKNESS
    outer_shape = box(
        extents=(
            INNER_WIDTH + 2 * WALL_THICKNESS,
            INNER_SIDE_HEIGHT,
            DEPTH,
        )
    ).union(
        cylinder(
            radius=outer_arc_radius,
            height=DEPTH,
        )
        .intersection(
            box((INNER_SIDE_HEIGHT + 2 * WALL_THICKNESS, 2 * outer_arc_radius, DEPTH))
        )
        .apply_translation(
            (
                0,
                (INNER_SIDE_HEIGHT + 2 * WALL_THICKNESS) / 2
                - outer_arc_radius
                + ARC_HEIGHT,
                0,
            )
        )
    )
    screw_hole = cylinder(
        radius=SCREW_HOLE_DIAMETER / 2,
        height=DEPTH + 2 * CAP_THICKNESS,
    )
    return outer_shape.difference(inner_shape).difference(screw_hole)


def calc_arc_radius(chord_length: float, arc_height: float) -> float:
    """Calculate the radius of an arc given its chord length and height."""

    # chord_length = 2 * sqrt(r^2 - (r - h)^2)
    # chord_length^2 = 4 * (r^2 - (r - h)^2)
    # chord_length^2 = 4 * (r^2 - (r^2 - 2rh + h^2))
    # chord_length^2 = 4 * (2rh - h^2)
    # chord_length^2 = 8rh - 4h^2
    # chord_length^2 + 4h^2 = 8rh
    return (chord_length**2) / (8 * arc_height) + (arc_height / 2)
