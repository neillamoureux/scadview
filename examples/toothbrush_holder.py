import numpy as np
from shapely.geometry import Polygon
from trimesh import Trimesh, transformations
from trimesh.creation import box, extrude_polygon

HEX_CELL_DIMS = (10, 15, 3)
COLS = 12
ROWS = 6
WALL_WIDTH = 2


def create_mesh() -> Trimesh | list[Trimesh]:
    # return rect_frame((10, 15, 5), 3, (0, 0))
    # grid = hex_grid((10, 15, 1), 12, 6, 0.5).subdivide().subdivide().subdivide()
    # grid = hex_grid((10, 15, 1), 12, 6, 0.5)
    grid = hex_grid(HEX_CELL_DIMS, COLS, ROWS, WALL_WIDTH)
    frame_dims = (
        HEX_CELL_DIMS[0] * (COLS - 1) * 0.75 + HEX_CELL_DIMS[0] + 2 * WALL_WIDTH,
        HEX_CELL_DIMS[1] * ROWS + 2 * WALL_WIDTH,
        HEX_CELL_DIMS[2],
    )
    bottom_frame = box(
        (frame_dims[0], WALL_WIDTH / 2, frame_dims[2])
    ).apply_translation((frame_dims[0] / 2, -WALL_WIDTH / 4, frame_dims[2] / 2))
    top_frame = bottom_frame.copy().apply_translation(
        (0, frame_dims[1] - WALL_WIDTH * 1.5, 0)
    )
    grid = (
        grid.union(top_frame)
        .union(bottom_frame)
        .subdivide()
        .subdivide()
        .subdivide()
        .subdivide()
    )
    return grid.apply_translation((10, 10, 0))
    # return grid.union(bottom_frame)
    bend = 2 * np.pi
    bent_verts = bend_x(
        grid.vertices, arc_radians=2 * np.pi, x_overlap=HEX_CELL_DIMS[0] * 0.5
    )
    curved_mesh = Trimesh(vertices=bent_verts, faces=grid.faces)
    # rotate about the y axis so curved mesh edges lie on the xy plane (90 degrees - curve in degreees / 2.0
    rot = transformations.rotation_matrix(
        angle=np.pi / 2.0 - bend / 2.0,
        direction=[0, 1, 0],
        point=(0, 0, 0),
    )
    curved_mesh.apply_transform(rot)
    return curved_mesh
    return [grid, curved_mesh]


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
    base_dims = (
        (cols - 1) * cell_dims[0] * 0.75 + cell_dims[0],
        rows * cell_dims[1],
        cell_dims[2],
    )
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

    # return base_box
    # grid_dims = (
    #     cols * cell_dims[0] * 1.5,
    #     rows * cell_dims[1] * np.sqrt(3) / 2,
    #     cell_dims[2],
    # )
    # grid = box(grid_dims).apply_translation(
    #     (grid_dims[0] / 2, grid_dims[1] / 2, grid_dims[2] / 2)
    # )
    # # return grid
    # cell_hole_dims = (
    #     cell_dims[0] - wall_width,
    #     cell_dims[1] - wall_width,
    #     cell_dims[2],
    # )
    # cell_hole = box(cell_hole_dims).apply_translation(
    #     (
    #         cell_dims[0] / 2 - wall_width / 2,
    #         cell_dims[1] / 2 - wall_width / 2,
    #         cell_dims[2] / 2,
    #     )
    # )
    # for row in range(rows):
    #     for col in range(cols):
    #         offset = (
    #             col * cell_dims[0] * 1.5 + wall_width / 2,
    #             row * cell_dims[1] * np.sqrt(3) / 2 + wall_width / 2,
    #             0,
    #         )
    #         if col % 2 == 1:
    #             offset = (
    #                 offset[0],
    #                 offset[1] + cell_dims[1] * np.sqrt(3) / 4,
    #                 offset[2],
    #             )
    #         inner_box = cell_hole.copy().apply_translation(offset)
    #         grid = grid.difference(inner_box)
    # return grid


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


def rect_grid(
    cell_dims: tuple[float, float, float],
    cols: int,
    rows: int,
    wall_width: float,
) -> Trimesh:
    grid_dims = (
        cols * cell_dims[0],
        rows * cell_dims[1],
        cell_dims[2],
    )
    grid = box(grid_dims).apply_translation(
        (grid_dims[0] / 2, grid_dims[1] / 2, grid_dims[2] / 2)
    )
    # return grid
    cell_hole_dims = cell_dims[0] - wall_width, cell_dims[1] - wall_width, cell_dims[2]
    cell_hole = box(cell_hole_dims).apply_translation(
        (
            cell_dims[0] / 2 - wall_width / 2,
            cell_dims[1] / 2 - wall_width / 2,
            cell_dims[2] / 2,
        )
    )
    for row in range(rows):
        for col in range(cols):
            offset = (
                col * cell_dims[0] + wall_width / 2,
                row * cell_dims[1] + wall_width / 2,
                0,
            )
            inner_box = cell_hole.copy().apply_translation(offset)
            grid = grid.difference(inner_box)
    return grid


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
    print(np.shape(vertices), np.shape(x), np.shape(y), np.shape(z))
    x_min = np.min(x)
    x_max = np.max(x)
    x_span = x_max - x_min - x_overlap
    print(f"x_min: {x_min}, x_max: {x_max}, x_span: {x_span}")
    inner_radius = x_span / arc_radians
    rad_x = arc_radians * (x - x_min) / x_span
    x_new = -(inner_radius + z) * np.cos(rad_x) + inner_radius
    z_new = (inner_radius + z) * np.sin(rad_x)
    print(f"x_new: {np.shape(x_new)}, z_new: {np.shape(z_new)}")
    return np.stack((x_new, y, z_new), axis=-1)


def rect_frame(
    dims: tuple[float, float, float],
    wall_width: float,
    hole_offset: tuple[float, float] = (0, 0),
) -> Trimesh:
    """
    Create a rectangular frame: a rectangle with a central rectangular hole.  The hole is centered by default,
    aand is offset by the given hole_offset.
    The frame lies flat in the XY plane, with the Z axis pointing up
    """
    outer_box = box(dims)
    inner_box = box(
        [dims[0] - 2 * wall_width, dims[1] - 2 * wall_width, dims[2]]
    ).apply_translation([hole_offset[0], hole_offset[1], 0])
    return outer_box.difference(inner_box)
