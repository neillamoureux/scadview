import numpy as np
from time import time
import trimesh
from matplotlib import font_manager, ft2font
from matplotlib.font_manager import FontProperties, ttfFontProperty, weight_dict
from matplotlib.textpath import TextPath, TextToPath
from shapely.geometry import Point, Polygon
from trimesh.creation import extrude_polygon

# WEIGHTS = {
#     100: "UltraLight",
#     200: "Light",
#     400: "Regular",
#     500: "Medium",
#     600: "SemiBold",
#     700: "Bold",
#     800: "ExtraBold",
#     900: "Black",
# }


def create_mesh():
    # text = "Sophie is so cool!"
    text = " Sophie "
    font_size = 1.0  # in your mesh units
    extrude_height = 0.25  # depth of the 3D text
    fonts = list_system_fonts()
    font = "Arial"
    font_path = fonts.get(font, None)  # Use Arial as a default font if available
    if not font_path:
        raise ValueError(f"{font} font not found in system fonts.")
    print_font_properties(font_path)
    # mesh = extrude_text(
    #     text, font_path=font_path, font_size=font_size, extrude_height=extrude_height
    # )
    mesh = text_to_3d_mesh(
        text, font_path, pt_size=72, depth=10.0, spacing=0, valign="top"
    )
    return mesh


def list_system_fonts():
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
            # entry = ttfFontProperty(ft)
            # fname = entry.fname
            # name = entry.name
            # weight = entry.weight
            # if str(weight).lower() in ["400", "normal", "regular"]:
            #     weight = ""
            # else:
            #     weight = WEIGHTS.get(entry.weight, entry.weight)
            # style = entry.style
            # if str(style).lower() in ["normal", "regular"]:
            #     style = ""
            # else:
            #     style = WEIGHTS.get(entry.style, entry.style)
            # style = str(style).capitalize() if style else ""
            # css_style = f"{weight} {style}".strip()
            # if css_style == "":
            #     css_style = "Regular"
            # if multiple files share the same family name, keep first
            # print(f"Font: {name}, entry:{entry}, path: {fp}")
            fonts.setdefault(f"{ft.family_name}:style={ft.style_name}", fp)
            if ft.style_name == "Regular":
                # also add the font without style
                fonts.setdefault(f"{ft.family_name}", fp)
        except Exception as e:
            print(f"Error processing font {fp}: {e}")
            # corrupted font? skip
            # continue
    for name in sorted(fonts.keys()):
        print(name)
    print(weight_dict)
    return fonts


def text_to_3d_mesh(
    text: str,
    font_path: str,
    pt_size: float = 72,
    depth: float = 1.0,
    spacing: int = 0,
    valign: str = "baseline",
) -> trimesh.Trimesh:
    # 1. get all loops (exterior & interior)
    loops = loops_from_text(text, font_path, pt_size, spacing, valign)

    # 2. assemble shapely.Polygon objects with proper holes
    polys = polygons_with_holes(loops, is_loop_orientation_ok(loops))

    # 3. extrude each polygon (holes stay as voids!)
    meshes = [extrude_polygon(poly, height=depth) for poly in polys]

    # 4. stitch into one mesh
    return trimesh.util.concatenate(meshes)


def loops_from_text(text, font_path, pt_size=72, spacing=0, valign="baseline"):
    # ft2 = ft2font.FT2Font(font_path)
    # font_entry = font_manager.ttfFontProperty(ft2)

    # Note: to implement spacing, we need to call ft2font.FT2Font.get_kerning()
    # which requires a pair of glyphs indices, and a KERNING_DEFAULT mode.
    # For now, we will just ignore spacing.
    # See https://matplotlib.org/3.5.3/gallery/misc/font_indexing.html
    fp = FontProperties(fname=font_path, size=pt_size)
    tp = TextPath((0, 0), text, prop=fp)
    _, height, descent = TextToPath().get_text_width_height_descent(
        text, prop=fp, ismath=False
    )
    print(f"Text height: {height}, descent: {descent}")
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

    # Create a list of loops (exterior and interior)
    # Each loop is a tuple (kind, vertices) where kind is 'exterior' or 'interior'

    loops = []
    # x_offset = 0
    for poly in tp.to_polygons():
        # poly is a list of vertices for the whole text
        # we will split it into characters
        verts = np.array(poly)
        # compute signed area: + → CCW (exterior), – → CW (interior)
        area2 = np.dot(verts[:-1, 0], verts[1:, 1]) - np.dot(
            verts[:-1, 1], verts[1:, 0]
        )
        kind = "exterior" if area2 > 0 else "interior"
        loops.append((kind, verts + np.array([0, y_offset])))
        # x_offset += tp.get_extents().width + spacing

    # for ch in text:
    #     try:
    #         # try to build the path (will fail on ' ')
    #         tp = TextPath((0, 0), ch, prop=fp)
    #         polys = tp.to_polygons()
    #     except Exception:
    #         # no outline estimate with a '.':
    #         tp = TextPath((0, 0), ".", prop=fp)
    #         polys = []

    #     for verts in polys:
    #         # compute signed area: + → CCW (exterior), – → CW (interior)
    #         area2 = np.dot(verts[:-1, 0], verts[1:, 1]) - np.dot(
    #             verts[:-1, 1], verts[1:, 0]
    #         )
    #         kind = "exterior" if area2 > 0 else "interior"
    #         print(f"x_offset: {x_offset}, y_offset: {y_offset}")
    #         loops.append((kind, verts + np.array([x_offset, y_offset])))
    #         # loops.append((kind, verts))
    #     x_offset += tp.get_extents().width + spacing

    return loops


def print_font_properties(font_path):
    font = ft2font.FT2Font(font_path)

    print("Num faces:  ", font.num_faces)  # number of faces in file
    print("Num glyphs: ", font.num_glyphs)  # number of glyphs in the face
    print("Family name:", font.family_name)  # face family name
    print("Style name: ", font.style_name)  # face style name
    print("PS name:    ", font.postscript_name)  # the postscript name
    print("Num fixed:  ", font.num_fixed_sizes)  # number of embedded bitmaps

    # the following are only available if face.scalable
    if font.scalable:
        # the face global bounding box (xmin, ymin, xmax, ymax)
        print("Bbox:               ", font.bbox)
        # number of font units covered by the EM
        print("EM:                 ", font.units_per_EM)
        # the ascender in 26.6 units
        print("Ascender:           ", font.ascender)
        # the descender in 26.6 units
        print("Descender:          ", font.descender)
        # the height in 26.6 units
        print("Height:             ", font.height)
        # maximum horizontal cursor advance
        print("Max adv width:      ", font.max_advance_width)
        # same for vertical layout
        print("Max adv height:     ", font.max_advance_height)
        # vertical position of the underline bar
        print("Underline pos:      ", font.underline_position)
        # vertical thickness of the underline
        print("Underline thickness:", font.underline_thickness)


def is_loop_orientation_ok(loops):
    exteriors = [v for k, v in loops if k == "exterior"]
    interiors = [v for k, v in loops if k == "interior"]
    ext_with_holes = 0
    int_with_ext = 0
    for ext in exteriors:
        ext_poly = Polygon(ext)
        # check if any interior is inside this exterior
        for hole in interiors:
            cx, cy = hole[0]
            if ext_poly.contains(Point(cx, cy)):
                ext_with_holes += 1
    for inte in interiors:
        int_poly = Polygon(inte)
        # check if any interior is inside this exterior
        for ext in exteriors:
            cx, cy = ext[0]
            if int_poly.contains(Point(cx, cy)):
                int_with_ext += 1

    print(
        f"exteriors with holes: {ext_with_holes}, interiors with exteriors: {int_with_ext}"
    )
    return ext_with_holes >= int_with_ext


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


if __name__ == "__main__":
    create_mesh()
