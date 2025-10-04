import logging
from meshsee import Color, set_mesh_color, text, linear_extrude, text_polys
from trimesh import Trimesh
from trimesh.creation import box
from pyrr.matrix44 import create_from_axis_rotation
import numpy as np
from shapely.affinity import scale as shapely_scale

SIZE = 50
TEXT_FRACTION = 0.8
TEXT_HEIGHT = SIZE / 10


def create_mesh():
    box_mesh = box(extents=(SIZE, SIZE, SIZE))
    set_mesh_color(box_mesh, Color.GRAY, alpha=0.5)

    x_polys = text_polys("X", halign="center", size=SIZE)
    y_polys = text_polys("Y", halign="center", size=SIZE)
    z_polys = text_polys("Z", halign="center", size=SIZE)
    x_bounds = [poly.bounds for poly in x_polys]
    y_bounds = [poly.bounds for poly in y_polys]
    z_bounds = [poly.bounds for poly in z_polys]
    x_maxx = max([b[2] for b in x_bounds])
    x_minx = min([b[0] for b in x_bounds])
    x_maxy = max([b[3] for b in x_bounds])
    x_miny = min([b[1] for b in x_bounds])
    x_extents = [x_maxx - x_minx, x_maxy - x_miny]
    y_maxx = max([b[2] for b in y_bounds])
    y_minx = min([b[0] for b in y_bounds])
    y_maxy = max([b[3] for b in y_bounds])
    y_miny = min([b[1] for b in y_bounds])
    y_extents = [y_maxx - y_minx, y_maxy - y_miny]
    z_maxx = max([b[2] for b in z_bounds])
    z_minx = min([b[0] for b in z_bounds])
    z_maxy = max([b[3] for b in z_bounds])
    z_miny = min([b[1] for b in z_bounds])
    z_extents = [z_maxx - z_minx, z_maxy - z_miny]
    maxx_extent = max(x_extents[0], y_extents[0], z_extents[0])
    maxy_extent = max(x_extents[1], y_extents[1], z_extents[1])
    max_extent = max(maxx_extent, maxy_extent)
    scale = (SIZE * TEXT_FRACTION / max_extent, SIZE * TEXT_FRACTION / max_extent)
    x_polys = [
        shapely_scale(poly, xfact=scale[0], yfact=scale[1], origin=(0, 0))
        for poly in x_polys
    ]
    y_polys = [
        shapely_scale(poly, xfact=scale[0], yfact=scale[1], origin=(0, 0))
        for poly in y_polys
    ]
    z_polys = [
        shapely_scale(poly, xfact=scale[0], yfact=scale[1], origin=(0, 0))
        for poly in z_polys
    ]
    x_mesh = linear_extrude(x_polys[0], TEXT_HEIGHT)
    logging.info(f"x_mesh is volume: {x_mesh.is_volume}")
    y_mesh = linear_extrude(y_polys[0], TEXT_HEIGHT)
    z_mesh = linear_extrude(z_polys[0], TEXT_HEIGHT)

    # max_xy_extent = max(
    #     x_polys.bounds[0:2].max(), y_mesh.extents[0:2].max(), z_mesh.extents[0:2].max()
    # )
    # scale_xy = (SIZE / max_xy_extent) * TEXT_FRACTION
    # x_mesh_max = x_mesh.extents[0:2].max()
    # scale_xy = (SIZE / x_mesh_max) * TEXT_FRACTION
    # scale = (scale_xy, scale_xy, TEXT_HEIGHT)
    # x_mesh.apply_scale(scale)
    # x_mesh = linear_extrude(x_mesh.vertices, TEXT_HEIGHT, scale=0.5)
    # y_mesh.apply_scale(scale)
    # z_mesh.apply_scale(scale)
    xy_center_mesh(x_mesh)
    x_mesh.apply_transform(
        create_from_axis_rotation((1, 0, 0), -np.pi / 2)
    ).apply_transform(
        create_from_axis_rotation((0, 0, 1), np.pi / 2)
    ).apply_translation(
        (SIZE / 2 + TEXT_HEIGHT, 0, 0)
    )
    xy_center_mesh(y_mesh)
    y_mesh.apply_transform(
        create_from_axis_rotation((1, 0, 0), -np.pi / 2)
    ).apply_translation((0, SIZE / 2 + TEXT_HEIGHT, 0))
    xy_center_mesh(z_mesh)
    z_mesh.apply_translation((0, 0, SIZE / 2))
    # set_mesh_color(x_mesh, Color.RED, alpha=0.5)
    # set_mesh_color(y_mesh, Color.GREEN, alpha=0.5)
    # set_mesh_color(z_mesh, Color.BLUE, alpha=0.5)
    # x_bounds = x_mesh.bounds
    # x_center = (x_bounds[0] + x_bounds[1]) / 2
    # x_mesh.apply_translation((0, -x_center[1], SIZE / 2))
    x_bot_mesh = x_mesh.copy().apply_translation((-SIZE, 0, 0))
    y_bot_mesh = y_mesh.copy().apply_translation((0, -SIZE, 0))
    z_bot_mesh = z_mesh.copy().apply_translation((0, 0, -SIZE))
    logging.info(f"Box mesh watertight: {box_mesh.is_watertight}")
    logging.info(f"X mesh watertight: {x_mesh.is_watertight}")
    logging.info(f"Y mesh watertight: {y_mesh.is_watertight}")
    logging.info(f"Z mesh watertight: {z_mesh.is_watertight}")
    logging.info(f"X bot mesh watertight: {x_bot_mesh.is_watertight}")
    logging.info(f"Y bot mesh watertight: {y_bot_mesh.is_watertight}")
    logging.info(f"Z bot mesh watertight: {z_bot_mesh.is_watertight}")
    logging.info(f"Box mesh volume: {box_mesh.is_volume}")
    logging.info(f"X mesh volume: {x_mesh.is_volume}")
    # yield box_mesh.union(x_mesh)
    # return [box_mesh, x_mesh, x_bot_mesh, y_mesh, y_bot_mesh, z_mesh, z_bot_mesh]
    return (
        box_mesh.union(x_mesh)
        # .union(y_mesh)
        # .union(z_mesh)
        # .difference(x_bot_mesh)
        # .difference(y_bot_mesh)
        # .difference(z_bot_mesh)
    )


def create_mesh_old():
    box_mesh = box(extents=(SIZE, SIZE, SIZE))
    set_mesh_color(box_mesh, Color.GRAY, alpha=0.5)

    x_mesh = text("X", halign="center", size=SIZE)
    y_mesh = text("Y", halign="center", size=SIZE)
    z_mesh = text("Z", halign="center", size=SIZE)
    max_xy_extent = max(
        x_polys.bounds[0:2].max(), y_mesh.extents[0:2].max(), z_mesh.extents[0:2].max()
    )
    scale_xy = (SIZE / max_xy_extent) * TEXT_FRACTION
    # x_mesh_max = x_mesh.extents[0:2].max()
    # scale_xy = (SIZE / x_mesh_max) * TEXT_FRACTION
    scale = (scale_xy, scale_xy, TEXT_HEIGHT)
    x_mesh.apply_scale(scale)
    # x_mesh = linear_extrude(x_mesh.vertices, TEXT_HEIGHT, scale=0.5)
    y_mesh.apply_scale(scale)
    z_mesh.apply_scale(scale)
    xy_center_mesh(x_mesh)
    x_mesh.apply_transform(
        create_from_axis_rotation((1, 0, 0), -np.pi / 2)
    ).apply_transform(
        create_from_axis_rotation((0, 0, 1), np.pi / 2)
    ).apply_translation(
        (SIZE / 2 + TEXT_HEIGHT, 0, 0)
    )
    xy_center_mesh(y_mesh)
    y_mesh.apply_transform(
        create_from_axis_rotation((1, 0, 0), -np.pi / 2)
    ).apply_translation((0, SIZE / 2 + TEXT_HEIGHT, 0))
    xy_center_mesh(z_mesh)
    z_mesh.apply_translation((0, 0, SIZE / 2))
    # set_mesh_color(x_mesh, Color.RED, alpha=0.5)
    # set_mesh_color(y_mesh, Color.GREEN, alpha=0.5)
    # set_mesh_color(z_mesh, Color.BLUE, alpha=0.5)
    # x_bounds = x_mesh.bounds
    # x_center = (x_bounds[0] + x_bounds[1]) / 2
    # x_mesh.apply_translation((0, -x_center[1], SIZE / 2))
    x_bot_mesh = x_mesh.copy().apply_translation((-SIZE, 0, 0))
    y_bot_mesh = y_mesh.copy().apply_translation((0, -SIZE, 0))
    z_bot_mesh = z_mesh.copy().apply_translation((0, 0, -SIZE))
    # yield box_mesh.union(x_mesh)
    # return [box_mesh, x_mesh, x_bot_mesh]
    return (
        box_mesh.union(x_mesh)
        .union(y_mesh)
        .union(z_mesh)
        .difference(x_bot_mesh)
        .difference(y_bot_mesh)
        .difference(z_bot_mesh)
    )
    # return [box_mesh, x_mesh, y_mesh, z_mesh]  # x_bot_mesh, y_bot_mesh, z_bot_mesh]


def create_unscaled_letter(letter: str, size: float) -> Trimesh:
    return text(letter, halign="center", size=size)


def xy_center_mesh(mesh: Trimesh) -> Trimesh:
    bounds = mesh.bounds
    center = (bounds[0] + bounds[1]) / 2
    mesh.apply_translation([-center[0], -center[1], 0])
    return mesh
