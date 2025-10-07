import numpy as np
import shapely.geometry as sg
import trimesh
from trimesh import Trimesh
from scipy.spatial import KDTree

NUM_SIDES = 6
R = 10.0
H = 10.0
SLICES = 3


def create_mesh():
    radial_angles = np.linspace(0, 2 * np.pi, NUM_SIDES, endpoint=False)
    shell = np.column_stack((R * np.cos(radial_angles), R * np.sin(radial_angles)))
    hole = 0.5 * shell[::-1, :]  # smaller, reversed
    poly = sg.Polygon(shell, [hole])
    verts_2d, poly_faces = trimesh.creation.triangulate_polygon(poly)
    faces = poly_faces.copy()[:, ::-1]

    # Find the boundary rings (exterior + interiors)
    # list of array(shape(mi, 2)) where mi is number of vertices in ring i
    # The length of the array is the number of rings (1 + number of holes)
    bndries = [np.asarray(poly.exterior.coords[:-1])]
    bndries += [np.asarray(r.coords[:-1]) for r in poly.interiors]
    # TODO: make sure shell ring is CCW and holes are CW

    # map ring vertices -> triangulation indices
    kdt = KDTree(verts_2d)
    # list of array(shape(mi,), intp) where mi is number of vertices in ring i
    bndries_idxes = [  # pyright: ignore[reportUnknownVariableType] - scipy fn
        kdt.query(r, k=1)[1] for r in bndries
    ]  # list of len(bndries) of array(shape(m,), intp)
    # ensure indices are intp
    bndries_idxes = [
        np.asarray(bvi, dtype=np.intp)
        for bvi in bndries_idxes  # pyright: ignore[reportUnknownVariableType] - scipy
    ]  # list of len(bndries) of array(shape(m,), intp)
    # Build the layers:
    # 1. base layer, including triangulated faces and boundary vertices (already done)
    # 2. extruded boundary vertices only, one per slice except the top layer
    # 3. The offset of the slice vertices in the vertex array is:
    #    len(verts_2d) + sum([bndry_idx.shape[0] for bndry_idx in bndries_idxes]) * slice_index
    # 5. The top layer vertices are the same as the base layer vertices, but at z=2*H
    # 6. The top layer offset is:
    #    len(verts_2d) + sum([bndry_idx.shape[0] for bndry_idx in bndries_idxes]) * SLICES
    # 7. For each layer, stitch the rings to the next layer

    poly_vert_count = len(verts_2d)
    bndry_verts_per_layer = sum([len(bi) for bi in bndries_idxes])
    verts_3d = np.column_stack((verts_2d, np.zeros(len(verts_2d))))
    for i in range(1, SLICES):
        layer_verts = np.vstack(
            [
                np.column_stack((bndry, np.ones(len(bndry)) * i * H / SLICES))
                for bndry in bndries
            ]
        )
        verts_3d = np.vstack((verts_3d, layer_verts))
    # Top layer
    verts_3d = np.vstack(
        [
            verts_3d,
            np.column_stack((verts_2d, np.ones(len(verts_2d)) * H)),
        ]
    )
    # stitch layers
    verts_index_offset_upper = 0
    for i in range(0, SLICES):
        verts_index_offset_lower = verts_index_offset_upper
        verts_index_offset_upper = poly_vert_count + i * bndry_verts_per_layer
        ring_offset = 0
        for bi in bndries_idxes:
            if i == 0:
                lower_idx = bi
            else:
                lower_idx = np.arange(
                    ring_offset,
                    ring_offset + len(bi),
                    dtype=np.int32,
                )
            if i == SLICES - 1:
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
    top_faces = poly_faces + poly_vert_count + (SLICES - 1) * bndry_verts_per_layer
    faces = np.vstack((faces, top_faces))

    # verts_index_offset_lower = 0
    # ring_offset = 0
    # verts_index_offset_upper = len(verts_2d)
    # # bottom layer, incliuding boundary vertices and triangulated faces
    # verts_3d = np.column_stack((verts_2d, np.zeros(len(verts_2d))))
    # # layer 1, extruded boundary vertices only
    # layer_1_verts = np.vstack(
    #     [
    #         np.column_stack((bndry, np.ones(len(bndry)) * H / SLICES))
    #         for bndry in bndries
    #     ]
    # )
    # verts_3d = np.vstack((verts_3d, layer_1_verts))
    # new_faces = stitch_rings(
    #     bndries_idxes[0] + verts_index_offset_lower,
    #     np.arange(
    #         verts_index_offset_upper + ring_offset,
    #         verts_index_offset_upper + ring_offset + len(bndries_idxes[0]),
    #         dtype=np.int32,
    #     ),
    # )
    # faces = np.vstack((faces, new_faces))
    # ring_offset += len(bndries_idxes[0])
    # new_faces = stitch_rings(
    #     bndries_idxes[1] + verts_index_offset_lower,
    #     np.arange(
    #         verts_index_offset_upper + ring_offset,
    #         verts_index_offset_upper + ring_offset + len(bndries_idxes[1]),
    #         dtype=np.int32,
    #     ),
    # )
    # faces = np.vstack((faces, new_faces))

    # # add layer 2
    # layer_2_verts = np.vstack(
    #     [
    #         np.column_stack((bndry, np.ones(len(bndry)) * H * 2 / SLICES))
    #         for bndry in bndries
    #     ]
    # )
    # verts_index_offset_lower = verts_index_offset_upper
    # ring_offset = 0
    # verts_index_offset_upper += len(layer_2_verts)
    # verts_3d = np.vstack((verts_3d, layer_2_verts))
    # new_faces = stitch_rings(
    #     np.arange(
    #         verts_index_offset_lower + ring_offset,
    #         verts_index_offset_lower + ring_offset + len(bndries_idxes[0]),
    #         dtype=np.int32,
    #     ),
    #     np.arange(
    #         verts_index_offset_upper + ring_offset,
    #         verts_index_offset_upper + ring_offset + len(bndries_idxes[0]),
    #         dtype=np.int32,
    #     ),
    # )
    # faces = np.vstack((faces, new_faces))
    # ring_offset += len(bndries_idxes[0])
    # new_faces = stitch_rings(
    #     np.arange(
    #         verts_index_offset_lower + ring_offset,
    #         verts_index_offset_lower + ring_offset + len(bndries_idxes[1]),
    #         dtype=np.int32,
    #     ),
    #     np.arange(
    #         verts_index_offset_upper + ring_offset,
    #         verts_index_offset_upper + ring_offset + len(bndries_idxes[1]),
    #         dtype=np.int32,
    #     ),
    # )
    # faces = np.vstack((faces, new_faces))

    # # add the top faces
    # verts_index_offset_lower = verts_index_offset_upper
    # ring_offset = 0
    # verts_index_offset_upper += len(layer_1_verts)
    # verts_3d = np.vstack(
    #     [
    #         verts_3d,
    #         np.column_stack((verts_2d, np.ones(len(verts_2d)) * 3 * H / SLICES)),
    #     ]
    # )
    # new_faces = stitch_rings(
    #     np.arange(
    #         verts_index_offset_lower + ring_offset,
    #         verts_index_offset_lower + ring_offset + len(bndries_idxes[0]),
    #         dtype=np.int32,
    #     ),
    #     bndries_idxes[0] + verts_index_offset_upper,
    # )
    # faces = np.vstack((faces, new_faces))
    # ring_offset += len(bndries_idxes[0])
    # new_faces = stitch_rings(
    #     np.arange(
    #         verts_index_offset_lower + ring_offset,
    #         verts_index_offset_lower + ring_offset + len(bndries_idxes[1]),
    #         dtype=np.int32,
    #     ),
    #     bndries_idxes[1] + verts_index_offset_upper,
    # )
    # faces = np.vstack((faces, new_faces))
    # top_faces = poly_faces + verts_index_offset_upper

    # faces = np.vstack((faces, top_faces))

    # for bndry_idx in bndries_idxes:
    #     for i in range(len(bndry_idx)):
    #         a = bndry_idx[i]
    #         b = bndry_idx[(i + 1) % len(bndry_idx)]
    #         faces.append([a, b, verts_index_offset])
    #         faces.append(
    #             [b, (b + 1) % len(bndry_idx) + faces_index_offset, verts_index_offset]
    #         )
    #         verts_3d = np.vstack((verts_3d, [verts_2d[b][0], verts_2d[b][1], 0.0]))
    #         verts_index_offset += 1
    #     faces_index_offset += len(bndry_idx)

    # ring_indexes = np.empty(shape=(0, NUM_SIDES), dtype=np.int32)
    # for i in range(SLICES):
    #     ring = np.column_stack(
    #         (
    #             R * np.cos(radial_angles),
    #             R * np.sin(radial_angles),
    #             i * H / SLICES * np.ones(NUM_SIDES),
    #         )
    #     )
    #     ring_index = np.linspace(
    #         i * NUM_SIDES, (i + 1) * NUM_SIDES - 1, NUM_SIDES, dtype=np.int32
    #     )
    #     vertices = np.vstack((vertices, ring))
    #     ring_indexes = np.vstack((ring_indexes, ring_index))
    # faces = stitch_ring_list(ring_indexes)
    mesh = Trimesh(vertices=verts_3d, faces=faces)
    print(f"mesh is watertight: {mesh.is_watertight}")
    print(f"mesh is volume: {mesh.is_volume}")
    return mesh

    # ring_0 = np.column_stack(
    #     (R * np.cos(radial_angles), R * np.sin(radial_angles), np.zeros(NUM_SIDES))
    # )
    # ring_0_perm = np.random.permutation(NUM_SIDES)
    # ring_0 = ring_0[ring_0_perm]
    # ring_0_idx = np.argsort(ring_0_perm)
    # ring_1 = np.column_stack(
    #     (R * np.cos(radial_angles), R * np.sin(radial_angles), H * np.ones(NUM_SIDES))
    # )
    # ring_1_perm = np.random.permutation(NUM_SIDES)
    # ring_1 = ring_1[ring_1_perm]
    # ring_1_idx = np.argsort(ring_1_perm) + NUM_SIDES
    # # vertices = np.vstack((ring_0, ring_1))
    # ring_2 = np.column_stack(
    #     (
    #         R * np.cos(radial_angles),
    #         R * np.sin(radial_angles),
    #         2 * H * np.ones(NUM_SIDES),
    #     )
    # )
    # ring_2_idx = np.linspace(2 * NUM_SIDES, 3 * NUM_SIDES - 1, NUM_SIDES, dtype=int)
    # # ring_2_perm = np.random.permutation(NUM_SIDES)
    # # ring_2 = ring_2[ring_2_perm]
    # # ring_2_idx = np.argsort(ring_2_perm) + 2 * NUM_SIDES
    # vertices = np.vstack((ring_0, ring_1, ring_2))

    # faces = stitch_ring_list([ring_0_idx, ring_1_idx, ring_2_idx])
    # # vertices, faces = stitch_ring_list([ring_0, ring_1], [ring_0_idx, ring_1_idx])
    # # vertices, faces = stitch_ring_list([ring_0, ring_1, ring_2])
    # # faces = []
    # # for i in range(NUM_SIDES):
    # #     next_i = (i + 1) % NUM_SIDES
    # #     faces.append([i, next_i, NUM_SIDES + next_i])
    # #     faces.append([i, NUM_SIDES + next_i, NUM_SIDES + i])
    # mesh = Trimesh(vertices=vertices, faces=faces)
    # return mesh


def stitch_ring_list(ring_indexes: list[np.ndarray]):
    all_faces = []
    for i in range(len(ring_indexes) - 1):
        ring_a_idx = ring_indexes[i]
        ring_b_idx = ring_indexes[i + 1]
        faces = stitch_rings(ring_a_idx, ring_b_idx)
        all_faces.append(faces)
    all_faces = np.vstack(all_faces)
    return all_faces
    # all_vertices = []
    # all_faces = []
    # vertex_offset = 0
    # for i in range(len(rings) - 1):
    #     ring_a = rings[i]
    #     ring_b = rings[i + 1]
    #     vertices, faces = stitch_rings(ring_a, ring_b)
    #     all_vertices.append(vertices)
    #     all_faces.append(faces + vertex_offset)
    #     vertex_offset += vertices.shape[0]
    # all_vertices = np.vstack(all_vertices)
    # all_faces = np.vstack(all_faces)
    # return all_vertices, all_faces


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
