import logging

from trimesh.creation import annulus, box, icosphere

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

MILLIS_PER_INCH = 25.4
STEM_R_MAX = 6.5 / 2.0
LIP = 0.125
TOP_R = 7.25 / 2.0


def create_mesh():
    logging.debug("Creating mushroom mesh")
    top = icosphere(radius=TOP_R * MILLIS_PER_INCH).apply_scale([1.0, 1.0, 0.5])
    cut = box(
        [9 * MILLIS_PER_INCH, 9 * MILLIS_PER_INCH, 4.5 * MILLIS_PER_INCH]
    ).apply_translation([0.0, 0.0, -4.5 / 2 * MILLIS_PER_INCH])

    cut.metadata = {"scadview": {"color": [0.0, 1.0, 0.0, 0.3]}}
    inner_top = icosphere(radius=(TOP_R - 0.1) * MILLIS_PER_INCH).apply_scale(
        [1.0, 1.0, 0.5]
    )
    top = top.difference(inner_top).difference(cut)
    stem = annulus(
        r_max=STEM_R_MAX * MILLIS_PER_INCH,
        r_min=(STEM_R_MAX - 0.1) * MILLIS_PER_INCH,
        height=2.0 * MILLIS_PER_INCH / 2.0,
    ).apply_translation([0.0, 0.0, -2.0 * MILLIS_PER_INCH / 4.0])
    join = annulus(
        r_max=TOP_R * MILLIS_PER_INCH,
        r_min=(STEM_R_MAX - 0.1) * MILLIS_PER_INCH,
        height=0.1 * MILLIS_PER_INCH,
    )
    edge = annulus(
        r_max=(STEM_R_MAX + 0.125) * MILLIS_PER_INCH,
        r_min=(STEM_R_MAX) * MILLIS_PER_INCH,
        height=0.1 * MILLIS_PER_INCH,
    ).apply_translation(
        [
            0.0,
            0.0,
            -2.0 * MILLIS_PER_INCH / 2.0,
        ]
    )
    return top.union(stem).union(join).union(edge)
