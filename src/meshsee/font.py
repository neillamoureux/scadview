from matplotlib import font_manager
import trimesh
from trimesh.creation import extrude_polygon
from matplotlib.textpath import TextPath
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union


def create_mesh():
    text = "Hello, 3D!"
    font_size = 1.0  # in your mesh units
    extrude_height = 0.25  # depth of the 3D text
    fonts = list_system_fonts()
    font = "Papyrus"
    font_path = fonts.get(font, None)  # Use Arial as a default font if available
    if not font_path:
        raise ValueError(f"{font} font not found in system fonts.")

    # mesh = extrude_text(
    #     text, font_path=font_path, font_size=font_size, extrude_height=extrude_height
    # )
    mesh = text_to_3d_mesh(text, font_path, pt_size=72, depth=10.0)
    return mesh


def list_system_fonts():
    """
    Returns a dict mapping font family names -> font file paths
    (only TrueType/OpenType fonts).
    """
    # findSystemFonts returns absolute paths to .ttf/.otf files
    font_paths = font_manager.findSystemFonts(fontpaths=None, fontext="ttf")
    font_paths += font_manager.findSystemFonts(fontpaths=None, fontext="otf")
    print(f"Found {len(font_paths)} system fonts")
    print(font_paths)

    fonts = {}
    for fp in font_paths:
        try:
            name = font_manager.FontProperties(fname=fp).get_name()
            # if multiple files share the same family name, keep first
            fonts.setdefault(name, fp)
        except Exception as e:
            print(f"Error processing font {fp}: {e}")
            # corrupted font? skip
            # continue
    for name in sorted(fonts.keys()):
        print(name)
    return fonts


def extrude_text(
    text: str, font_path: str, font_size: float = 1.0, extrude_height: float = 0.25
):
    # Create a TextPath object
    tp = TextPath(
        (0, 0),
        text,
        size=font_size,
        prop=font_manager.FontProperties(fname=font_path, size=72),
    )
    # Convert to a shapely Polygon or MultiPolygon
    poly_verts = tp.to_polygons()
    # Remove holes: only keep the exterior ring of each polygon
    shapely_polys = [Polygon(v) for v in poly_verts if len(v) >= 3]
    text_shape = unary_union(shapely_polys)

    # poly = Polygon(
    #     tp.vertices, [tp.vertices[c] for c in tp.codes if c == 79]
    # )  # 79 is CLOSEPOLY
    # # Sometimes TextPath returns multiple disconnected shapes (e.g., for "i" or "!")
    # if not poly.is_valid or poly.is_empty:
    #     # Try to fix with buffer(0)
    #     poly = poly.buffer(0)
    # if isinstance(poly, Polygon):
    #     polygons = [poly]
    # elif isinstance(poly, MultiPolygon):
    #     polygons = list(poly.geoms)
    # else:
    #     raise ValueError("Could not convert text to polygon.")

    # Extrude each polygon and combine
    # meshes = []
    # for p in text_shape:
    #     mesh = extrude_polygon(p, extrude_height)
    #     meshes.append(mesh)
    #     # Combine all meshes into one
    # combined = trimesh.util.concatenate(meshes)
    # return combined

    # mesh = extrude_polygon(text_shape, extrude_height)
    # return mesh

    meshes = []
    if isinstance(text_shape, Polygon):
        meshes.append(extrude_polygon(text_shape, extrude_height))
    elif isinstance(text_shape, MultiPolygon):
        for poly in text_shape.geoms:
            meshes.append(extrude_polygon(poly, extrude_height))
    else:
        raise ValueError(f"Unexpected geometry type: {type(text_shape)}")
    # 4. combine into one mesh
    return trimesh.util.concatenate(meshes)

    # meshes = []
    # for p in polygons:
    #     mesh = extrude_polygon(p, extrude_height)
    #     meshes.append(mesh)
    # # Combine all meshes into one
    # combined = trimesh.util.concatenate(meshes)
    # return combined

    # meshes = []
    # for p in shapely_polys:
    #     # Only extrude the exterior (no holes)
    #     exterior = Polygon(p.exterior)
    #     mesh = extrude_polygon(exterior, extrude_height)
    #     meshes.append(mesh)
    # # Combine all meshes into one
    # combined = trimesh.util.concatenate(meshes)
    # for p in shapely_polys:
    #     # Only extrude the exterior (no holes)
    #     interiors = Polygon(p.interiors)
    #     mesh = extrude_polygon(interiors, extrude_height)
    #     combined.minus(mesh)
    #     # for i in interiors:
    #     #     mesh = extrude_polygon(i, extrude_height)
    #     #     combined.minus(mesh)
    # return combined


import numpy as np
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon, Point
from trimesh.creation import extrude_polygon
import trimesh


def loops_from_text(text, font_path, pt_size=72):
    tp = TextPath((0, 0), text, prop=FontProperties(fname=font_path, size=pt_size))
    loops = []
    for verts in tp.to_polygons():
        # compute signed area: + → CCW (exterior), – → CW (interior)
        area2 = np.dot(verts[:-1, 0], verts[1:, 1]) - np.dot(
            verts[:-1, 1], verts[1:, 0]
        )
        kind = "exterior" if area2 > 0 else "interior"
        loops.append((kind, verts))
    return loops


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


def text_to_3d_mesh(
    text: str, font_path: str, pt_size: float = 72, depth: float = 1.0
) -> trimesh.Trimesh:
    # 1. get all loops (exterior & interior)
    loops = loops_from_text(text, font_path, pt_size)

    # 2. assemble shapely.Polygon objects with proper holes
    polys = polygons_with_holes(loops, is_loop_orientation_ok(loops))

    # 3. extrude each polygon (holes stay as voids!)
    meshes = [extrude_polygon(poly, height=depth) for poly in polys]

    # 4. stitch into one mesh
    return trimesh.util.concatenate(meshes)


if __name__ == "__main__":
    create_mesh()
