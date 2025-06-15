import logging
import os
from copy import copy
from functools import cache
from typing import Any

import numpy as np
import trimesh
from matplotlib import font_manager, ft2font
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath, TextToPath
from numpy.typing import NDArray
from shapely.geometry import Point, Polygon
from trimesh import Trimesh
from trimesh.creation import extrude_polygon

logger = logging.getLogger(__name__)

DEFAULT_FONT = "DejaVuSansMono"  # Default font to use if not specified
RELATIVE_PATH_TO_FONT = "../resources/"
FONT_FILE = "DejaVuSansMono.ttf"  # Default font file name
DEFAULT_FONT_PATH = os.path.join(
    os.path.dirname(__file__), RELATIVE_PATH_TO_FONT, FONT_FILE
)
SIZE_MULTIPLIER = 1.374  # Used to convert pt size to mesh units


@cache
def list_system_fonts() -> dict[str, str]:
    """
    Returns a dict mapping font family names -> font file paths
    (only TrueType/OpenType fonts).
    """
    logger.info("Finding system fonts - this can take some time")
    # findSystemFonts returns absolute paths to .ttf/.otf files
    font_paths = font_manager.findSystemFonts(fontpaths=None, fontext="ttf")
    # also add OpenType fonts
    font_paths += font_manager.findSystemFonts(fontpaths=None, fontext="otf")
    fonts = {}
    for fp in font_paths:
        try:
            ft = ft2font.FT2Font(fp)
            fonts.setdefault(f"{ft.family_name}:style={ft.style_name}", fp)
            if ft.style_name == "Regular":
                # also add the font without style
                fonts.setdefault(f"{ft.family_name}", fp)
        except Exception:
            # corrupted font? skip
            continue
    if logger.isEnabledFor(logging.DEBUG):
        for font in sorted(fonts.keys()):
            logger.debug(f"Font: {font}")
    logger.info("Found system fonts")
    return fonts


def text(
    text: str,
    size: float = 10.0,
    font: str = DEFAULT_FONT,
    halign: str = "left",
    valign: str = "baseline",
    spacing: float = 0,
    direction: str = "ltr",
    language: str = "",
    script: str = "",
) -> Trimesh:
    """
    Create a 3D mesh from the given text using the specified font and size.
    :param text: The text to convert to a 3D mesh.
    :param size: The size of the text in mesh units.
    :param font: The font family name to use for the text.
    :param halign: Horizontal alignment of the text ('left', 'center', 'right').
    :param valign: Vertical alignment of the text ('baseline', 'top', 'bottom', 'center').
    :param spacing: Spacing between characters in mesh units (not used in this implementtion).
    :param direction: Text direction (only 'ltr' and 'rtl' are is supported in this implementation).
    :param language: Language of the text (not used in this implementation).
    :param script: Script of the text (not used in this implementation).
    :return: A trimesh.Trimesh object representing the 3D mesh of the text.
    """
    if text.strip() == "":
        # If the text is empty or contains only spaces, return an empty mesh
        return trimesh.Trimesh(vertices=np.empty((0, 3)), faces=np.empty((0, 3)))
    if direction == "ltr":
        ordered_text = text
    elif direction == "rtl":
        ordered_text = text[::-1]
    else:
        raise ValueError("direction must be ltr or rtl")
    font_path = list_system_fonts().get(font, None)
    if not font_path:
        logger.warning(
            f"Font '{font}' not found in system fonts. Using default font: {DEFAULT_FONT_PATH}"
        )
        # Use the default font if the specified font is not found
        font_path = DEFAULT_FONT_PATH
    loops = _loops_from_text(ordered_text, font_path, size, halign, valign)
    # polys = polygons_with_holes(loops, _is_loop_orientation_reversed(loops))
    polys = _make_polys(loops)
    meshes = [extrude_polygon(poly, height=1.0) for poly in polys]
    return trimesh.util.concatenate(meshes)


def _loops_from_text(
    text: str, font_path: str, size: float, halign: str, valign: str
) -> list[NDArray[np.float32]]:
    # Note: to implement spacing, we need to call ft2font.FT2Font.get_kerning()
    # which requires a pair of glyphs indices, and a KERNING_DEFAULT mode.
    # For now, we will just ignore spacing.
    # See https://matplotlib.org/3.5.3/gallery/misc/font_indexing.html
    fp = FontProperties(fname=font_path, size=size * SIZE_MULTIPLIER)
    x_offset, y_offset = _calc_offsets(text, fp, halign, valign)

    tp = TextPath((0, 0), text, prop=fp)
    loops = []
    for poly in tp.to_polygons():
        verts = np.array(poly, dtype="f4")
        loops.append(verts + np.array([x_offset, y_offset], dtype="f4"))
    return loops


def _calc_offsets(
    text: str, fp: FontProperties, halign: str, valign: str
) -> tuple[float, float]:
    """
    Calculate the x and y offsets based on the horizontal and vertical alignment of the text.
    :param text: The text to measure.
    :param fp: FontProperties object containing font information.
    :param halign: Horizontal alignment ('left', 'center', 'right').
    :param valign: Vertical alignment ('baseline', 'top', 'bottom', 'center').
    :return: A tuple (x_offset, y_offset) for the text.
    """
    width, height, descent = TextToPath().get_text_width_height_descent(
        text, prop=fp, ismath=False
    )
    y_offset = _calc_y_offset(valign, height, descent)
    x_offset = _calc_x_offset(halign, width)
    return x_offset, y_offset


def _calc_y_offset(valign: str, height: float, descent: float) -> float:
    if valign == "baseline":
        return 0.0
    elif valign == "top":
        return -height
    elif valign == "bottom":
        return descent
    elif valign == "center":
        return -(height - descent) / 2.0
    else:
        raise ValueError(f"Invalid valign: {valign}")


def _calc_x_offset(halign: str, width: float) -> float:
    """
    Calculate the x offset based on the horizontal alignment of the text.
    :param text: The text to measure.
    :param fp: FontProperties object containing font information.
    :param halign: Horizontal alignment ('left', 'center', 'right').
    :return: The x offset for the text.
    """
    if halign == "left":
        return 0.0
    elif halign == "center":
        return -width / 2.0
    elif halign == "right":
        return -width
    else:
        raise ValueError(f"Invalid halign: {halign}")


def _make_polys(loops: list[NDArray[np.float32]]) -> list[Polygon]:
    """
    Create a list of shapely.Polygon objects from the given loops.
    Each loop is a list of points (x, y) representing the vertices of the loop.
    The function determines the containment relationships between loops
    and creates polygons with holes accordingly.
    :param loops: List of loops, each loop is a list of points (x, y).
    :return: List of shapely.Polygon objects with holes.
    """
    return _assemble_polys(loops, _track_containment(loops))


def _track_containment(loops: list[NDArray[np.float32]]) -> list[dict[str, Any]]:
    # Track containment relationships between loops
    loops_cont = [{"contains": [], "exterior": True} for _ in loops]
    simple_polys = [Polygon(loop) for loop in loops]
    first_points = [Point(loop[0]) for loop in loops]
    for i, first_point_i in enumerate(first_points):
        for j, spoly_j in enumerate(simple_polys):
            if i == j:
                continue
            if first_point_i.within(spoly_j):
                # if within, flip the exterior flag.  An even number of containments implies exterior.
                loops_cont[i]["exterior"] = not loops_cont[i]["exterior"]
                loops_cont[j]["contains"].append(i)
    return loops_cont


def _assemble_polys(
    loops: list[NDArray[np.float32]], loops_cont: list[dict[str, Any]]
) -> list[Polygon]:
    # Determine which "contained" loops are contained by another loop and no others.
    # We only consider "exterior" loops
    for loop_cont in loops_cont:
        if loop_cont["exterior"]:
            loop_cont["holes"] = copy(
                loop_cont["contains"]
            )  # initialize holes with contained loops
    polys = []
    for i in range(len(loops)):
        if loops_cont[i]["exterior"]:
            for j in loops_cont[i]["contains"]:
                # remove contained loops that are also contained in interior loops from the holes list
                for k in loops_cont[j]["contains"]:
                    if k in loops_cont[i]["holes"]:
                        loops_cont[i]["holes"].remove(k)
            polys.append(Polygon(loops[i], [loops[j] for j in loops_cont[i]["holes"]]))
    return polys
