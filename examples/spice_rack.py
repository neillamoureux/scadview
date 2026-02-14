import numpy as np
from shapely.geometry import Polygon
from trimesh import Trimesh, transformations
from trimesh.creation import box, extrude_polygon

BOTTLE_DIAMETER = 45.0
BOTTLE_HEIGHT = 120.0
BOTTLE_TOP = 30.0
TILT_DEGREES = 20.0

COLS = 4
ROWS = 3
ALT_ROW_DELTA = 1  # -1, 0, or 1: adjust every other column by this many rows
EXTRA_BOTTOM_ROWS = 1

CLEARANCE = 1.0
WALL_THICKNESS = 2.0
BASE_HEIGHT = 6.0
BOTTOM_POCKET_DEPTH = BASE_HEIGHT * 0.6


def create_mesh() -> Trimesh:
    slot_length = _slot_length()
    positions_full, positions_all = _slot_positions()
    if not positions_all:
        return Trimesh()

    inner_across_flats = BOTTLE_DIAMETER + CLEARANCE
    outer_across_flats = inner_across_flats + 2.0 * WALL_THICKNESS

    outer_slot = _build_slot_mesh(outer_across_flats, slot_length + WALL_THICKNESS)
    inner_slot = _build_slot_mesh(inner_across_flats, slot_length)

    min_y, max_y, min_z_all, max_z = _rack_bounds(positions_all, outer_across_flats)
    _, _, min_z_full, _ = _rack_bounds(positions_full, outer_across_flats)

    outer = _union_slots(outer_slot, positions_all)
    inner_full = _union_slots(inner_slot, positions_full)
    inner_extra = _union_slots(inner_slot, positions_all[len(positions_full) :])
    inner = inner_full
    if inner_extra is not None and inner is not None:
        inner_extra = _trim_above_z(inner_extra, min_z_full - BOTTOM_POCKET_DEPTH)
        inner = inner.union(inner_extra)
    elif inner_extra is not None:
        inner = _trim_above_z(inner_extra, min_z_full - BOTTOM_POCKET_DEPTH)

    back_plate = _back_plate(slot_length, min_y, max_y, min_z_all, max_z)
    base_plate = _base_plate(slot_length, min_y, max_y, min_z_full)

    rack = outer
    if inner is not None:
        rack = rack.difference(inner)
    rack = rack.union(back_plate).union(base_plate)
    return _trim_rack(rack, slot_length, min_y, max_y, min_z_full).apply_transform(
        transformations.rotation_matrix(np.deg2rad(90.0), [0, 0, 1], [0, 0, 0])
    )


def _slot_positions() -> tuple[
    list[tuple[float, float, float]], list[tuple[float, float, float]]
]:
    inner_across_flats = BOTTLE_DIAMETER + CLEARANCE
    spacing_across_flats = inner_across_flats + 2.0 * WALL_THICKNESS
    _, hex_height = _hex_dims(spacing_across_flats)
    col_spacing = _hex_col_spacing(spacing_across_flats)
    row_spacing = hex_height

    positions_full = _slot_positions_raw(
        col_spacing,
        row_spacing,
        hex_height,
        rows=ROWS,
        row_start=0,
        use_alt_delta=True,
    )
    y_center, z_min = _position_offsets(positions_full)
    positions_full = _apply_offsets(positions_full, y_center, z_min)

    positions_extra: list[tuple[float, float, float]] = []
    if EXTRA_BOTTOM_ROWS > 0:
        positions_extra = _slot_positions_raw(
            col_spacing,
            row_spacing,
            hex_height,
            rows=EXTRA_BOTTOM_ROWS,
            row_start=-EXTRA_BOTTOM_ROWS,
            use_alt_delta=False,
        )
        positions_extra = _apply_offsets(positions_extra, y_center, z_min)

    return positions_full, positions_full + positions_extra


def _slot_length() -> float:
    slot_length = BOTTLE_HEIGHT - BOTTLE_TOP
    if slot_length <= 0:
        raise ValueError("BOTTLE_TOP must be less than BOTTLE_HEIGHT")
    return slot_length


def _build_slot_mesh(across_flats: float, slot_length: float) -> Trimesh:
    prism = _hex_prism(across_flats, slot_length)
    prism.apply_translation((0.0, 0.0, -slot_length / 2.0))

    tilt_radians = np.deg2rad(90.0 + TILT_DEGREES)
    prism.apply_transform(
        transformations.rotation_matrix(tilt_radians, [0, 1, 0], [0, 0, 0])
    )
    prism.apply_translation((-prism.bounds[0, 0], 0.0, 0.0))
    return prism


def _hex_prism(across_flats: float, height: float) -> Trimesh:
    return extrude_polygon(_hexagon_polygon(across_flats), height)


def _hexagon_polygon(across_flats: float) -> Polygon:
    radius = across_flats / np.sqrt(3.0)
    angles = np.deg2rad(30.0 + np.arange(6) * 60.0)
    points = np.column_stack((np.cos(angles), np.sin(angles))) * radius
    return Polygon(points)


def _hex_dims(across_flats: float) -> tuple[float, float]:
    radius = across_flats / np.sqrt(3.0)
    width = 2.0 * radius
    height = np.sqrt(3.0) * radius
    return width, height


def _hex_col_spacing(across_flats: float) -> float:
    radius = across_flats / np.sqrt(3.0)
    return 1.5 * radius


def _slot_positions_raw(
    col_spacing: float,
    row_spacing: float,
    hex_height: float,
    rows: int,
    row_start: int,
    use_alt_delta: bool,
) -> list[tuple[float, float, float]]:
    rows_per_col: list[int] = []
    z_offsets: list[float] = []
    for col in range(COLS):
        # rows_in_col = rows + 1
        rows_in_col = rows
        if use_alt_delta and col % 2 == 1:
            rows_in_col += ALT_ROW_DELTA
        rows_per_col.append(max(1, rows_in_col))
        z_offsets.append(_calculate_z_offset(col, hex_height, use_alt_delta))

    positions: list[tuple[float, float, float]] = []
    for col in range(COLS):
        z_offset = z_offsets[col]
        for row in range(row_start, row_start + rows_per_col[col]):
            y = col * col_spacing
            z = row * row_spacing + z_offset
            positions.append((0.0, y, z))
    return positions


def _calculate_z_offset(col: int, hex_height: float, use_alt_delta: bool) -> float:
    if not use_alt_delta or ALT_ROW_DELTA == 0:
        return (hex_height / 2) if (col % 2 == 1) else 0.0
    if col % 2 == 1:
        return -ALT_ROW_DELTA * hex_height / 2
    return 0.0


def _position_offsets(
    positions: list[tuple[float, float, float]],
) -> tuple[float, float]:
    ys = [p[1] for p in positions]
    zs = [p[2] for p in positions]
    y_center = (min(ys) + max(ys)) / 2.0
    z_min = min(zs)
    return y_center, z_min


def _apply_offsets(
    positions: list[tuple[float, float, float]],
    y_center: float,
    z_min: float,
) -> list[tuple[float, float, float]]:
    return [(p[0], p[1] - y_center, p[2] - z_min) for p in positions]


def _union_slots(
    slot_mesh: Trimesh, positions: list[tuple[float, float, float]]
) -> Trimesh | None:
    if not positions:
        return None
    mesh = slot_mesh.copy().apply_translation(positions[0])
    for pos in positions[1:]:
        mesh = mesh.union(slot_mesh.copy().apply_translation(pos))
    return mesh


def _rack_bounds(
    positions: list[tuple[float, float, float]],
    across_flats: float,
) -> tuple[float, float, float, float]:
    width, height = _hex_dims(across_flats)
    half_w = width / 2.0
    half_h = height / 2.0
    min_y = min(p[1] - half_w for p in positions)
    max_y = max(p[1] + half_w for p in positions)
    min_z = min(p[2] - half_h for p in positions)
    max_z = max(p[2] + half_h for p in positions)
    return min_y, max_y, min_z, max_z


def _back_plate(
    slot_length: float,
    min_y: float,
    max_y: float,
    min_z: float,
    max_z: float,
) -> Trimesh:
    size_x = WALL_THICKNESS
    size_y = max_y - min_y
    size_z = max_z - min_z
    center = (
        slot_length + WALL_THICKNESS / 2.0,
        (min_y + max_y) / 2.0,
        (min_z + max_z) / 2.0,
    )
    return box((size_x, size_y, size_z)).apply_translation(center)


def _base_plate(
    slot_length: float,
    min_y: float,
    max_y: float,
    min_z: float,
) -> Trimesh:
    size_x = slot_length + WALL_THICKNESS
    size_y = max_y - min_y
    size_z = BASE_HEIGHT
    center = (
        size_x / 2.0,
        (min_y + max_y) / 2.0,
        min_z - BASE_HEIGHT / 2.0,
    )
    return box((size_x, size_y, size_z)).apply_translation(center)


def _trim_rack(
    rack: Trimesh,
    slot_length: float,
    min_y: float,
    max_y: float,
    min_z: float,
) -> Trimesh:
    size_x = slot_length + WALL_THICKNESS
    size_y = max_y - min_y
    size_z = (rack.bounds[1, 2] - (min_z - BASE_HEIGHT)) + WALL_THICKNESS
    center = (
        size_x / 2.0,
        (min_y + max_y) / 2.0,
        (min_z - BASE_HEIGHT) + size_z / 2.0,
    )
    trim = box((size_x, size_y, size_z)).apply_translation(center)
    return rack.intersection(trim)


def _trim_above_z(mesh: Trimesh, z_min: float) -> Trimesh:
    bounds = mesh.bounds
    size_x = bounds[1, 0] - bounds[0, 0]
    size_y = bounds[1, 1] - bounds[0, 1]
    size_z = bounds[1, 2] - z_min
    center = (
        (bounds[0, 0] + bounds[1, 0]) / 2.0,
        (bounds[0, 1] + bounds[1, 1]) / 2.0,
        z_min + size_z / 2.0,
    )
    trim = box((size_x, size_y, size_z)).apply_translation(center)
    return mesh.intersection(trim)


if __name__ == "__main__":
    create_mesh()
