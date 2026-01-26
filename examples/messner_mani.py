from manifold3d import Manifold


def create_mesh():
    for mesh in create_messner(27, 3):
        latest = mesh
        yield mesh
    return latest


def create_messner(extent=1, n=1):
    mesh = Manifold.cube([extent, extent, extent], True)
    for i in range(0, n):
        grid_points_per_line = 3**i
        diff_extent = extent / grid_points_per_line / 3.0
        step = diff_extent * 3.0
        start = (-extent + diff_extent * 3) / 2.0
        for j in range(0, grid_points_per_line):
            x = start + j * step
            for k in range(0, grid_points_per_line):
                if j % 3 == 1 and k % 3 == 1:
                    continue
                y = start + k * step
                bx = Manifold.cube([diff_extent, diff_extent, extent], True)
                bx = bx.translate([x, y, 0])
                mesh -= bx
                yield mesh

                bx = Manifold.cube([diff_extent, extent, diff_extent], True)
                bx = bx.translate([x, 0, y])
                mesh -= bx
                yield mesh

                bx = Manifold.cube([extent, diff_extent, diff_extent], True)
                bx = bx.translate([0, x, y])
                mesh -= bx
                yield mesh
