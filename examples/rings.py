import numpy as np
import shapely.geometry as sg
import trimesh
from trimesh import Trimesh
from scipy.spatial import KDTree

NUM_SIDES = 6
R = 10.0
H = 10.0
SLICES = 7
TWIST = np.pi / 3


def create_mesh():
    radial_angles = np.linspace(0, 2 * np.pi, NUM_SIDES, endpoint=False)
    shell = np.column_stack((R * np.cos(radial_angles), R * np.sin(radial_angles)))
    hole = 0.5 * shell[::-1, :]  # smaller, reversed
    poly = sg.Polygon(shell, [hole])
    return le(poly, H, SLICES)


def le(poly: sg.Polygon, height: float, slices: int):
    verts_2d, poly_faces = trimesh.creation.triangulate_polygon(poly)
    faces = poly_faces.copy()[:, ::-1]

    # Find the boundary rings (exterior + interiors)
    # list of array(shape(mi, 2)) where mi is number of vertices in ring i
    # The length of the array is the number of rings (1 + number of holes)
    rings = [np.asarray(poly.exterior.coords[:-1])]
    rings += [np.asarray(r.coords[:-1]) for r in poly.interiors]
    # TODO: make sure shell ring is CCW and holes are CW

    # map ring vertices -> triangulation indices
    kdt = KDTree(verts_2d)
    # list of array(shape(mi,), intp) where mi is number of vertices in ring i
    rings_idxs = [  # pyright: ignore[reportUnknownVariableType] - scipy fn
        kdt.query(r, k=1)[1] for r in rings
    ]  # list of len(bndries) of array(shape(m,), intp)
    # ensure indices are intp
    rings_idxs = [
        np.asarray(ri, dtype=np.intp)
        for ri in rings_idxs  # pyright: ignore[reportUnknownVariableType] - scipy
    ]  # list of len(bndries) of array(shape(m,), intp)
    # Build the layers:
    # 1. base layer, including triangulated faces and boundary vertices (already done)
    # 2. extruded boundary vertices only, one per slice except the top layer
    # 3. The offset of the slice vertices in the vertex array is:
    #    len(verts_2d) + sum([bndry_idx.shape[0] for bndry_idx in bndries_idxes]) * slice_index
    # 5. The top layer vertices are the same as the base layer vertices, but at z=2*height
    # 6. The top layer offset is:
    #    len(verts_2d) + sum([bndry_idx.shape[0] for bndry_idx in bndries_idxes]) * slices
    # 7. For each layer, stitch the rings to the next layer

    poly_vert_count = len(verts_2d)
    ring_verts_per_layer = sum([len(ri) for ri in rings_idxs])
    verts_3d = np.column_stack((verts_2d, np.zeros(len(verts_2d))))
    for i in range(1, slices):
        layer_verts = np.vstack(
            [
                np.column_stack((ring, np.ones(len(ring)) * i * height / slices))
                for ring in rings
            ]
        )
        verts_3d = np.vstack((verts_3d, layer_verts))
    # Top layer
    verts_3d = np.vstack(
        [
            verts_3d,
            np.column_stack((verts_2d, np.ones(len(verts_2d)) * height)),
        ]
    )
    # stitch layers
    verts_index_offset_upper = 0
    for i in range(0, slices):
        verts_index_offset_lower = verts_index_offset_upper
        verts_index_offset_upper = poly_vert_count + i * ring_verts_per_layer
        ring_offset = 0
        for bi in rings_idxs:
            if i == 0:
                lower_idx = bi
            else:
                lower_idx = np.arange(
                    ring_offset,
                    ring_offset + len(bi),
                    dtype=np.int32,
                )
            if i == slices - 1:
                upper_idx = bi
            else:
                upper_idx = np.arange(
                    ring_offset,
                    ring_offset + len(bi),
                    dtype=np.int32,
                )
            new_faces = stitch_rings(
                lower_idx + verts_index_offset_lower,
                upper_idx + verts_index_offset_upper,
            )
            faces = np.vstack((faces, new_faces))
            ring_offset += len(bi)
    top_faces = poly_faces + poly_vert_count + (slices - 1) * ring_verts_per_layer
    faces = np.vstack((faces, top_faces))

    mesh = Trimesh(vertices=verts_3d, faces=faces)
    print(f"mesh is watertight: {mesh.is_watertight}")
    print(f"mesh is volume: {mesh.is_volume}")
    return mesh


def stitch_rings(ring_a_idx, ring_b_idx):
    assert ring_a_idx.shape[0] == ring_b_idx.shape[0]
    num_verts = ring_a_idx.shape[0]
    faces = []
    for i in range(num_verts):
        next_i = (i + 1) % num_verts
        faces.append([ring_a_idx[i], ring_a_idx[next_i], ring_b_idx[next_i]])
        faces.append([ring_a_idx[i], ring_b_idx[next_i], ring_b_idx[i]])
    faces = np.array(faces)
    return faces


if __name__ == "__main__":
    create_mesh()
