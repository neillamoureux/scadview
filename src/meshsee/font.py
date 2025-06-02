import os
from functools import cache
from time import time

import numpy as np
import trimesh
from matplotlib import font_manager, ft2font
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath, TextToPath
from shapely.geometry import Point, Polygon
from trimesh import Trimesh
from trimesh.creation import extrude_polygon

DEFAULT_FONT = "DejaVuSansMono"  # Default font to use if not specified
RELATIVE_PATH_TO_FONT = "./"
FONT_FILE = "DejaVuSansMono.ttf"  # Default font file name
DEFAULT_FONT_PATH = os.path.join(
    os.path.dirname(__file__), RELATIVE_PATH_TO_FONT, FONT_FILE
)
SIZE_MULTIPLIER = 1.374  # Used to convert pt size to mesh units


def create_mesh():
    t = "".join(chr(i) for i in range(32, 127))
    # t = "A0"
    font = "Palatino Linotype:style=Italic"
    return text(t, font=font, size=100).apply_scale((1.0, 1.0, 10.0))


@cache
def list_system_fonts() -> dict[str:str]:
    """
    Returns a dict mapping font family names -> font file paths
    (only TrueType/OpenType fonts).
    """
    # findSystemFonts returns absolute paths to .ttf/.otf files
    start = time()
    font_paths = font_manager.findSystemFonts(fontpaths=None, fontext="ttf")
    print(
        f"Found {len(font_paths)} system TrueType fonts in {time() - start:.2f} seconds"
    )
    # also add OpenType fonts
    start = time()
    font_paths += font_manager.findSystemFonts(fontpaths=None, fontext="otf")
    print(
        f"Found {len(font_paths)} system OpenType fonts in {time() - start:.2f} seconds"
    )
    print(f"Found {len(font_paths)} system fonts")

    fonts = {}
    for fp in font_paths:
        try:
            ft = ft2font.FT2Font(fp)
            fonts.setdefault(f"{ft.family_name}:style={ft.style_name}", fp)
            if ft.style_name == "Regular":
                # also add the font without style
                fonts.setdefault(f"{ft.family_name}", fp)
        except Exception as e:
            # corrupted font? skip
            continue
    for font, path in sorted(fonts.items()):
        print(f"Font: {font}")
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
    :param direction: Text direction (only 'ltr' is supported in this implementation).
    :param language: Language of the text (not used in this implementation).
    :param script: Script of the text (not used in this implementation).
    :return: A trimesh.Trimesh object representing the 3D mesh of the text.
    """
    font_path = list_system_fonts().get(font, None)
    # font_path = None
    if not font_path:
        print(
            f"Font '{font}' not found in system fonts. Using default font: {DEFAULT_FONT_PATH}"
        )
        # Use the default font if the specified font is not found
        font_path = DEFAULT_FONT_PATH
    loops = loops_from_text(text, font_path, size, valign)
    # polys = polygons_with_holes(loops, _is_loop_orientation_reversed(loops))
    polys = _make_polys(loops)
    meshes = [extrude_polygon(poly, height=1.0) for poly in polys]
    return trimesh.util.concatenate(meshes)


def text_to_3d_mesh(
    text: str,
    font_path: str,
    pt_size: float = 72,
    depth: float = 1.0,
    spacing: int = 0,
    valign: str = "baseline",
) -> trimesh.Trimesh:
    # 1. get all loops (exterior & interior)
    loops = loops_from_text(text, font_path, pt_size, valign)
    polys = _make_polys([loop[1] for loop in loops])

    # 2. assemble shapely.Polygon objects with proper holes
    # polys = polygons_with_holes(loops, _is_loop_orientation_reversed(loops))

    # 3. extrude each polygon (holes stay as voids!)
    meshes = [extrude_polygon(poly, height=depth) for poly in polys]

    # 4. stitch into one mesh
    return trimesh.util.concatenate(meshes)


def loops_from_text(text, font_path, size=10, valign="baseline"):
    # Note: to implement spacing, we need to call ft2font.FT2Font.get_kerning()
    # which requires a pair of glyphs indices, and a KERNING_DEFAULT mode.
    # For now, we will just ignore spacing.
    # See https://matplotlib.org/3.5.3/gallery/misc/font_indexing.html
    fp = FontProperties(fname=font_path, size=size * SIZE_MULTIPLIER)
    y_offset = _calc_y_offset(text, fp, valign)

    # Create a list of loops (exterior and interior)
    # Each loop is a tuple (kind, vertices) where kind is 'exterior' or 'interior'
    tp = TextPath((0, 0), text, prop=fp)
    loops = []
    for poly in tp.to_polygons():
        verts = np.array(poly)
        # compute signed area: + → CCW (exterior), – → CW (interior)
        area2 = _signed_area(verts)
        kind = "exterior" if area2 > 0 else "interior"
        # loops.append((kind, verts + np.array([0, y_offset])))
        loops.append(verts + np.array([0, y_offset]))
    return loops


def _calc_y_offset(text: str, fp: FontProperties, valign: str):
    _, height, descent = TextToPath().get_text_width_height_descent(
        text, prop=fp, ismath=False
    )
    if valign == "baseline":
        y_offset = 0.0
    elif valign == "top":
        y_offset = -height
    elif valign == "bottom":
        y_offset = +descent
    elif valign == "center":
        y_offset = -(height - descent) / 2.0
    else:
        raise ValueError(f"Invalid valign: {valign}")
    return y_offset


def _signed_area(verts):
    return np.dot(verts[:-1, 0], verts[1:, 1]) - np.dot(verts[:-1, 1], verts[1:, 0])


def _is_loop_orientation_reversed(loops):
    """
    We assume that the exteriors are CCW and holes (interiors) are CW.
    We count how many holew are inside exteriors,
    and how many exteriors are inside exteriors.
    We should find all holes are inside exteriors,
    and no exteriors are inside holes.
    If this is not the case, we will swap exteriors and interiors.
    """
    exteriors = [v for k, v in loops if k == "exterior"]
    interiors = [v for k, v in loops if k == "interior"]
    holes_within_ext = 0
    ext_within_holes = 0
    for ext in exteriors:
        ext_poly = Polygon(ext)
        # check if any hole is inside this exterior
        for hole in interiors:
            cx, cy = hole[0]  # Check the first point of the hole
            if ext_poly.contains(Point(cx, cy)):
                holes_within_ext += 1
    for hole in interiors:
        hole_poly = Polygon(hole)
        # check if any interior is inside this exterior
        for ext in exteriors:
            cx, cy = ext[0]
            if hole_poly.contains(Point(cx, cy)):
                ext_within_holes += 1
    return holes_within_ext >= ext_within_holes


def polygons_with_holes(loops, loop_orientation_ok):
    # separate exteriors & interiors
    exteriors = [v for k, v in loops if k == "exterior"]
    interiors = [v for k, v in loops if k == "interior"]
    if not loop_orientation_ok:
        # swap exteriors and interiors if orientation is not ok
        exteriors, interiors = interiors, exteriors
    result = []
    for ext in exteriors:
        ext_poly = Polygon(ext)
        # find holes inside this exterior
        holes = []
        for hole in interiors:
            # sample a point from hole to test containment
            cx, cy = hole.mean(axis=0)
            if ext_poly.contains(Point(cx, cy)):
                holes.append(hole)
        result.append(Polygon(ext, holes))
    return result


def _make_polys(loops):
    """
    Create a list of shapely.Polygon objects from the given loops.
    Each loop is a list of points (x, y) representing the vertices of the loop.
    The function determines the containment relationships between loops
    and creates polygons with holes accordingly.
    :param loops: List of loops, each loop is a list of points (x, y).
    :return: List of shapely.Polygon objects with holes.
    """
    # Track containment relationships between loops
    loop_cont = [{"contains": [], "exterior": True, "holes": []} for _ in loops]
    simple_polys = [Polygon(loop) for loop in loops]
    rep_points = [Point(loop[0]) for loop in loops]
    for i, rep_point_i in enumerate(rep_points):
        for j, spoly_j in enumerate(simple_polys):
            if i == j:
                continue
            if rep_point_i.within(spoly_j):
                # if within, flip the exterior flag.  An even number of containments implies exterior.
                loop_cont[i]["exterior"] = not loop_cont[i]["exterior"]
                loop_cont[j]["contains"].append(i)
                loop_cont[j]["holes"].append(
                    i
                )  # initially assume all contained loops are holes
    polys = []
    # Determine which "contained" loops are contained by another loop and no others.
    # We only consider loops "exterior" loops
    for i in range(len(loops)):
        if loop_cont[i]["exterior"]:
            for j in loop_cont[i]["contains"]:
                # remove contained loops that are contained in interior loops from the holes
                for k in loop_cont[j]["contains"]:
                    if k in loop_cont[i]["holes"]:
                        loop_cont[i]["holes"].remove(k)
            polys.append(Polygon(loops[i], [loops[j] for j in loop_cont[i]["holes"]]))
    return polys


if __name__ == "__main__":
    create_mesh()
