import numpy as np
from trimesh.creation import box, cylinder
from trimesh.transformations import translation_matrix

# Dimensions of the brick (H)/ plate (h)
DIMS = (10, 20)
IS_PLATE = False


class LegoBrick:

    # Lego constants
    P = 8.0  # multiplier for the peg size
    h = 3.2  # height of a plate
    H = 3 * h  # height of a brick

    # INTER_PEG_DISTANCE = 8.0
    VERTICAL_WALL_THICKNESS = 1.5
    INNER_VERTICAL_WALL_THICKNESS = 0.8
    INNER_VERTICAL_WALL_HEIGHT = 6.3
    HORIZONTAL_WALL_THICKNESS = 1.0
    PEG_D = 4.8 + 0.1  # since my printer seems to make it too small
    PEG_H = 1.8
    UNDER_PEG_D = 2.6
    UNDER_CIRCLE_ID = 4.8
    UNDER_CIRCLE_OD = 6.5
    INTER_BRICK_GAP = 0.2

    def __init__(self, peg_dims, is_plate=False):
        self.peg_dims = peg_dims
        self.is_plate = is_plate
        self.brick = self.create_mesh()

    def create_mesh(self):
        # Create a box
        brk_dims = self.brick_dims()
        brick = box(brk_dims)
        yield brick
        colors = np.tile([128, 0, 0, 255], (len(brick.vertices), 1))
        brick.visual.vertex_colors = colors
        # Move bottom of the box to the origin
        bx_translation = translation_matrix([dim / 2 for dim in brk_dims])
        inner_brk_dims = self.inner_brick_dims()
        inner_brick = box(inner_brk_dims)
        yield inner_brick
        move_by = [dim / 2 for dim in inner_brk_dims]
        move_by[0] = move_by[0] + self.VERTICAL_WALL_THICKNESS
        move_by[1] = move_by[1] + self.VERTICAL_WALL_THICKNESS
        move_by[2] = inner_brk_dims[2] / 2
        inner_brick_translation = translation_matrix(move_by)
        brick.apply_transform(bx_translation)
        inner_brick.apply_transform(inner_brick_translation)
        brick = brick.difference(inner_brick)
        yield brick
        for i in range(self.peg_dims[0]):
            for j in range(self.peg_dims[1]):
                peg = self.create_peg_at((i, j))
                brick = brick.union(peg)
                yield brick
        for i in range(self.peg_dims[0] - 1):
            for j in range(self.peg_dims[1] - 1):
                under_cyl = self.create_under_cylinder_at((i, j))
                brick = brick.union(under_cyl)
                yield brick
        # return brick

    def brick_dims(self):
        return [
            self.P * self.peg_dims[0] - self.INTER_BRICK_GAP,
            self.P * self.peg_dims[1] - self.INTER_BRICK_GAP,
            self.height(),
        ]

    def height(self):
        return self.h if self.is_plate else self.H

    def inner_brick_dims(self):
        brk_dims = self.brick_dims()
        return [
            brk_dims[0] - 2 * self.VERTICAL_WALL_THICKNESS,
            brk_dims[1] - 2 * self.VERTICAL_WALL_THICKNESS,
            brk_dims[2] - self.HORIZONTAL_WALL_THICKNESS,
        ]

    def create_peg_at(self, peg_grid):
        peg = cylinder(self.PEG_D / 2, self.PEG_H)
        peg_translation = translation_matrix(
            [
                self.P * (peg_grid[0] + 0.5) - self.INTER_BRICK_GAP / 2,
                self.P * (peg_grid[1] + 0.5) - self.INTER_BRICK_GAP / 2,
                self.height() + self.PEG_H / 2,
            ]
        )
        peg.apply_transform(peg_translation)
        return peg

    def create_under_cylinder_at(self, cyl_grid):
        cyl_height = self.height() - self.HORIZONTAL_WALL_THICKNESS
        cyl = cylinder(self.UNDER_CIRCLE_OD / 2, cyl_height)
        inner_cl = cylinder(self.UNDER_CIRCLE_ID / 2, cyl_height)
        cyl = cyl.difference(inner_cl)
        cyl_translation = translation_matrix(
            [
                self.P * (cyl_grid[0] + 1.0) - self.INTER_BRICK_GAP / 2,
                self.P * (cyl_grid[1] + 1.0) - self.INTER_BRICK_GAP / 2,
                cyl_height / 2,
            ]
        )
        cyl.apply_transform(cyl_translation)
        return cyl


def create_mesh():
    brick = LegoBrick(DIMS, IS_PLATE)
    return brick.create_mesh()
