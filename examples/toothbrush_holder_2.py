from typing import Generator

import numpy as np
from shapely.geometry import Polygon
from trimesh import Trimesh, transformations
from trimesh.creation import box, cylinder, extrude_polygon

from meshsee import text

"""
A toothbrush holder with a tube for each person in the household.
Each tube is made from a hexagonal grid bent into a tube shape.
Each tube is labeled with the person's name.
The tubes are arrange in a circle on a circular base plate.

The center axis of each tube extends from a circle on the base plate,
to a circle at the top of the tube.  
Both circles have the same radius, and are centered on the same axis
as the base plate.
The tubes are tilted to hold the toothbrushes at an angle.
"""

# Names to mark each holder tube
NAMES = [
    "NEIL",
    "ADAM",
    "SOPHIE",
]


TUBE_INNER_R = 9.5  #  Tube size for a toothbrush (radius)
TUBE_H = 100  # height of tube when standing upright
TILT = np.deg2rad(30)  # tilt of tube
TUBE_COUNT = len(NAMES)  # number of toothbrushes to hold
TUBE_WALL = 4  # Thickness of the tube wall
HEX_GRID_COLS = 6  # Count of cols in the hex grid that makes the tube
GRID_DIV_WIDTH = 2  # Thickeness of the divisions between the hex cells

POSITIONING_R = (
    28  # Radius of the circle on which the tubes tops / bottoms are positioned
)
# Radius of the circle the center of the tubes are positioned on
# (position_r)**2  = center_positioning_r**2  + (sin(tilt) * tube_h / 2)**2
CENTER_POSITIONING_R = np.sqrt(
    np.square(POSITIONING_R) - np.square(np.sin(TILT) * TUBE_H / 2)
)

FONT = "Helvetica"  # Font for names
FONT_H = TUBE_WALL  # Extruded height of the foont
FONT_SIZE = 8  # font "size"

BASE_R = 41  # Radius of the base
BASE_H = 5  # Height (thickness) of the base


def create_mesh() -> (
    Trimesh | list[Trimesh] | Generator[Trimesh | list[Trimesh], None, None]
):
    hex_grid = make_grid(TUBE_INNER_R, TUBE_H, TUBE_WALL, HEX_GRID_COLS, GRID_DIV_WIDTH)
    yield hex_grid

    # Each tube is moved radially in evenly spaced directions around the circle
    tube_move_directions = np.linspace(0.0, 2 * np.pi, len(NAMES) + 1)
    mesh = Trimesh()  # Keep the type checking happy
    mesh_started = False

    for name, direction in zip(NAMES, tube_move_directions):
        name_mesh = text(name, FONT_SIZE, font=FONT, halign="center").apply_scale(
            [1, 1, -FONT_H]
        )
        grid_mesh = add_name(
            hex_grid.copy(),
            TUBE_INNER_R,
            TUBE_H,
            TUBE_WALL,
            HEX_GRID_COLS,
            GRID_DIV_WIDTH,
            name_mesh,
        )
        yield grid_mesh

        tube = bend_grid(
            grid_mesh.copy(),
        )
        # Stand upright
        tube.apply_transform(
            transformations.rotation_matrix(np.pi / 2, [1, 0, 0], [0, 0, 0])
        )
        # Rotate to move name to outside
        tube.apply_transform(
            transformations.rotation_matrix(np.pi, [0, 0, 1], [0, 0, 0])
        )
        # Move center to origin
        tube.apply_translation((0, 0, -TUBE_H / 2))
        # Tilt
        tube.apply_transform(
            transformations.rotation_matrix(TILT, [1, 0, 0], [0, 0, 0])
        )
        # rotate around z
        tube.apply_transform(
            transformations.rotation_matrix(direction, [0, 0, 1], [0, 0, 0])
        )
        # Move bottom center to XY plane and push out to c center to CENTER_POSITIONING_R
        tube.apply_translation(
            (
                -CENTER_POSITIONING_R * np.cos(direction),
                -CENTER_POSITIONING_R * np.sin(direction),
                np.cos(TILT) * TUBE_H / 2,
            )
        )
        if not mesh_started:
            mesh = tube
            mesh_started = True
        else:
            mesh = mesh.union(tube)
        yield mesh

    base_top_at = (TUBE_INNER_R + TUBE_WALL + GRID_DIV_WIDTH * 2) * np.sin(TILT)
    base = cylinder(BASE_R, BASE_H).apply_translation([0, 0, base_top_at - BASE_H / 2])
    mesh = mesh.union(base)
    yield mesh

    cut_height = TUBE_INNER_R * 3.0

    cut_top_at = base_top_at - BASE_H
    cut = cylinder(BASE_R * 1.1, cut_height).apply_translation(
        [0, 0, cut_top_at - cut_height / 2]
    )
    yield mesh.difference(cut)


def make_grid(
    tube_inner_r: float,
    tube_h: float,
    tube_wall: float,
    grid_cols: int,
    grid_div_width: float,
):
    hex_cell_dims, rows = hex_cell_dims_for_tube(
        tube_inner_r, tube_h, tube_wall, grid_div_width, grid_cols
    )
    grid = hex_grid(hex_cell_dims, grid_cols, rows, grid_div_width)
    frame_dims = hex_grid_dims(hex_cell_dims, grid_cols, rows)
    bottom_frame = box(
        (frame_dims[0], grid_div_width, frame_dims[2])
    ).apply_translation((frame_dims[0] / 2, 0, frame_dims[2] / 2))
    top_frame = bottom_frame.copy().apply_translation((0, frame_dims[1], 0))
    return (
        grid.union(top_frame)
        .union(bottom_frame)
        .apply_translation([0, grid_div_width / 2, 0])
    )


def hex_cell_dims_for_tube(
    tube_inner_r: float,
    tube_h: float,
    tube_wall: float,
    grid_div_width: float,
    cols: int,
) -> tuple[tuple[float, float, float], int]:
    # cols must be even for this to work.
    # The last col is only .75 wide so it can mate with its
    # other side when bent into a tube

    # 2 * pi * tube_inner_r = cols * cell_dim_x * 0.75
    # 2 * pi * tube_inner_r = cell_dim_x * ( 0.75 * (cols - 1) + 1)
    # 2 * pi * tube_inner_r = cell_dim_x * ( 0.75 * cols + 0.25)
    # so cell_dim_x = 2 * pi * tube_inner_r / (cols * .75)

    cell_dim_x = 2 * np.pi * tube_inner_r / (cols * 0.75)
    rows = round(tube_h / cell_dim_x)
    cell_dim_y = (tube_h - grid_div_width) / rows
    return (cell_dim_x, cell_dim_y, tube_wall), rows


def add_name(
    grid_mesh: Trimesh,
    tube_inner_r: float,
    tube_h: float,
    tube_wall: float,
    grid_cols: int,
    grid_div_width: float,
    name_mesh: Trimesh,
) -> Trimesh:
    """
    Place name at top of grid, standing up at 90 degrees
    """
    hex_cell_dims, rows = hex_cell_dims_for_tube(
        tube_inner_r,
        tube_h,
        tube_wall,
        grid_div_width,
        grid_cols,
    )
    frame_dims = hex_grid_dims(hex_cell_dims, grid_cols, rows)
    name_mesh.apply_transform(
        transformations.rotation_matrix(np.pi, [0, 1, 0], [0, 0, 0])
    )
    name_mesh.apply_transform(
        transformations.rotation_matrix(np.pi / 2, [1, 0, 0], [0, 0, 0])
    )
    name_mesh.apply_translation(
        (frame_dims[0] / 2, frame_dims[1] + grid_div_width, frame_dims[2])
    )
    return grid_mesh.union(name_mesh)


def hex_grid(
    cell_dims: tuple[float, float, float],
    cols: int,
    rows: int,
    wall_width: float,
) -> Trimesh:
    """
    Create a hexagonal grid of cells with the given dimensions, number of columns and rows, and wall width.
    Each cell is a hexagon with a bounding box of the given cell dimensions.
    An inner hexagon is punched out of each cell to create the walls.
    The grid lies flat in the XY plane, with the Z axis pointing up.

    The hexagons are oriented such that the flat sides are parallel to the X axis.
    The first column's left hex vertices touch the Y axis, and the first row's bottom first hex vertices touch the X axis.
    The hexagons are arranged in a staggered pattern, with every second column offset by half the height of a hexagon.

    The cell dims are the dimension of the bounding box of the hexagon, not the hexagon itself.
    The wall width is the width of the walls between the cells.

    Horizontal walls are the flat sides of the hexagons, and vertical walls are the angled sides.
    Horizonal wall have the wall thickness in the y dimension.
    Vertical walls thickness is along x direction

    """
    base_dims = hex_grid_dims(cell_dims, cols, rows)
    grid = box(base_dims).apply_translation(
        (base_dims[0] / 2, base_dims[1] / 2, base_dims[2] / 2)
    )
    hole_dims = (
        cell_dims[0] - wall_width,
        cell_dims[1] - wall_width,
        cell_dims[2],
    )
    base_hole = hexagon(hole_dims)
    starting_offset = (
        cell_dims[0] / 2,
        cell_dims[1] / 2,
    )
    for row in range(-1, rows):
        for col in range(-1, cols + 1):
            offset = (
                col * cell_dims[0] * 0.75 + starting_offset[0],
                row * cell_dims[1] + starting_offset[1],
                0,
            )
            if col % 2 == 1:
                offset = (
                    offset[0],
                    offset[1] + cell_dims[1] / 2,
                    0,
                )
            inner_hex = base_hole.copy().apply_translation(offset)
            grid = grid.difference(inner_hex)
    return grid


def hexagon(
    cell_dims: tuple[float, float, float],
) -> Trimesh:
    # 6 vertices within the xy bounds extruded to the z dimension
    angles = np.linspace(0, 2 * np.pi, 7)[:-1]  # drop last to avoid duplicate
    points = np.column_stack((np.cos(angles), np.sin(angles)))
    x_span = max(points[:, 0]) - min(points[:, 0])
    y_span = max(points[:, 1]) - min(points[:, 1])
    x_scale = cell_dims[0] / x_span
    y_scale = cell_dims[1] / y_span
    points = points * np.array([x_scale, y_scale])

    return extrude_polygon(Polygon(points), cell_dims[2])


def hex_grid_dims(
    cell_dims: tuple[float, float, float],
    cols: int,
    rows: int,
) -> tuple[float, float, float]:
    return (
        cols * cell_dims[0] * 0.75,
        rows * cell_dims[1],
        cell_dims[2],
    )


def bend_grid(
    grid: Trimesh,
) -> Trimesh:
    grid = grid.subdivide().subdivide().subdivide().subdivide()
    bend = 2 * np.pi
    bent_verts = bend_x(
        grid.vertices,
        arc_radians=bend,
    )
    return Trimesh(vertices=bent_verts, faces=grid.faces)


def clean_mesh(mesh: Trimesh) -> Trimesh:
    mesh.merge_vertices()
    mesh.remove_degenerate_faces()
    mesh.fill_holes()
    mesh.remove_duplicate_faces()
    mesh.process(validate=True)
    return mesh


def bend_x(
    vertices: np.ndarray, arc_radians: float = np.pi / 2.0, x_gap=0.01
) -> np.ndarray:
    """
    Bend the mesh along the x-axis.

    The x coords are mapped to an arc in the xz plane.
    The arc starts at the minimum x value, and its length is equal to the range of x values in the mesh.
    rad_x = arc_radians * (x - min(x)) / (max(x) - min(x))
    inner_radius is computed so that inner_radius * arc_radians is the length of the arc.
    So inner_radius = (max(x) - min(x)) / arc_radians.
    x = (inner_radius  + z) * np.cos(rad_x) + (max(x) - min(x)) / 2
    z = (inner_radius + z) * np.sin(rad_x)
    y is unchanged.
    """
    x, y, z = vertices.T
    x_min = np.min(x)
    x_max = np.max(x)
    x_span = x_max - x_min + x_gap
    inner_radius = x_span / arc_radians
    rad_x = arc_radians * (x - x_min) / x_span
    x_new = -(inner_radius + z) * np.cos(rad_x)  # + inner_radius
    z_new = (inner_radius + z) * np.sin(rad_x)
    return np.stack((x_new, y, z_new), axis=-1)
