import numpy as np
from shapely.geometry import Polygon
from trimesh import Trimesh, transformations
from trimesh.creation import box, extrude_polygon
from meshsee import text

NAMES = [
    "NEIL",
    "ADAM",
    "SOPHIE",
]

FONT = "Helvetica"
FONT_H = 3
FONT_SIZE = 8


#  Hole size for a toothbrush
TUBE_INNER_R = 9
TUBE_H = 100
TILT = np.deg2rad(30)
TUBE_COUNT = len(NAMES)
TUBE_WALL = 2
TUBE_BASE = 2


COLS = 6
GRID_DIV_WIDTH = 1


def create_mesh() -> Trimesh | list[Trimesh]:
    tubes = []
    displacement_dirs = np.linspace(0, 2 * np.pi, len(NAMES) + 1)[:-1]
    for name, direction in zip(NAMES, displacement_dirs):
        name_mesh = text(name, FONT_SIZE, font=FONT).apply_scale([1, 1, FONT_H])

        rot = transformations.rotation_matrix(-direction, (0, 1, 0), (0, 0, 0))
        tilt_rot = transformations.rotation_matrix(TILT, (1, 0, 9), (0, 0, 0))
        tubes.append(
            tube(TUBE_INNER_R, TUBE_H, TUBE_WALL, COLS, GRID_DIV_WIDTH, name_mesh)
            .apply_transform(tilt_rot)
            .apply_transform(rot)
            .apply_translation(
                1.5 * TUBE_INNER_R * np.array([np.cos(direction), 0, np.sin(direction)])
            )
        )
        yield tubes[-1]
    yield tubes


def tube(
    tube_inner_r: float,
    tube_h: float,
    tube_wall: float,
    grid_cols: int,
    grid_div_width: float,
    name_mesh: Trimesh,
) -> Trimesh:
    hex_cell_dims, rows = hex_cell_dims_for_tube(
        tube_inner_r, tube_h, tube_wall, grid_cols
    )
    grid = hex_grid(hex_cell_dims, grid_cols, rows, grid_div_width)
    frame_dims = hex_grid_dims(hex_cell_dims, grid_cols, rows)
    bottom_frame = box(
        (frame_dims[0], grid_div_width, frame_dims[2])
    ).apply_translation((frame_dims[0] / 2, 0, frame_dims[2] / 2))
    top_frame = bottom_frame.copy().apply_translation((0, frame_dims[1], 0))
    name_rot = transformations.rotation_matrix(
        angle=-np.pi / 2.0,
        direction=[0, 0, 1],
        point=(0, 0, 0),
    )
    name_mesh.apply_transform(name_rot).apply_translation(
        (frame_dims[0] / 2, frame_dims[1], hex_cell_dims[2])
    )

    grid = (
        grid.union(top_frame)
        .union(bottom_frame)
        .union(name_mesh)
        .subdivide()
        .subdivide()
        .subdivide()
        .subdivide()
    )
    bend = 2 * np.pi
    bent_verts = bend_x(
        grid.vertices, arc_radians=2 * np.pi, x_overlap=hex_cell_dims[0] * 0.25
    )
    curved_mesh = Trimesh(vertices=bent_verts, faces=grid.faces)
    # rotate about the y axis so curved mesh edges lie on the xy plane (90 degrees - curve in degreees / 2.0
    rot = transformations.rotation_matrix(
        angle=np.pi / 2.0 - bend / 2.0,
        direction=[0, 1, 0],
        point=(0, 0, 0),
    )
    curved_mesh.apply_transform(rot).apply_translation([0, 0, -tube_inner_r])
    return curved_mesh
    # return [grid, curved_mesh]


def hex_cell_dims_for_tube(
    tube_inner_r: float, tube_h: float, tube_wall: float, cols: int
) -> tuple[tuple[float, float, float], int]:
    # cols must be even for this to work and must satisfy

    # 2 * pi * tube_inner_r = (cols - 1) * cell_dim_x * 0.75 + cell_dim_x,
    # so cell_dim_x = 2 * pi * tube_inner_r / ((cols * .75 + .25)

    cell_dim_x = 2 * np.pi * tube_inner_r / ((cols * 0.75) + 0.25)
    rows = round(tube_h / cell_dim_x)
    cell_dim_y = tube_h / rows
    return (cell_dim_x, cell_dim_y, tube_wall), rows


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
    # base_dims = (
    #     (cols - 1) * cell_dims[0] * 0.75 + cell_dims[0],
    #     rows * cell_dims[1],
    #     cell_dims[2],
    # )
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


def hex_grid_dims(
    cell_dims: tuple[float, float, float],
    cols: int,
    rows: int,
) -> tuple[float, float, float]:
    return (
        (cols - 1) * cell_dims[0] * 0.75 + cell_dims[0],
        rows * cell_dims[1],
        cell_dims[2],
    )


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


def bend_x(
    vertices: np.ndarray, arc_radians: float = np.pi / 2.0, x_overlap=0.0
) -> np.ndarray:
    """
    Bend the mesh along the x-axis.

    The x coords are mapped to an arc in the xz plane with the given inner radius.
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
    x_span = x_max - x_min - x_overlap
    inner_radius = x_span / arc_radians
    rad_x = arc_radians * (x - x_min) / x_span
    x_new = -(inner_radius + z) * np.cos(rad_x) + inner_radius
    z_new = (inner_radius + z) * np.sin(rad_x)
    return np.stack((x_new, y, z_new), axis=-1)
