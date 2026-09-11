from __future__ import annotations

from abc import abstractmethod
from typing import cast

import moderngl
import numpy as np
from numpy.typing import NDArray

from scadview.mesh_payload import DEFAULT_COLOR, MeshPayload
from scadview.observable import Observable
from scadview.render.label_renderee import Renderee
from scadview.render.shader_program import ShaderVar


def create_mesh_renderee(
    ctx: moderngl.Context,
    program: moderngl.Program,
    mesh: MeshPayload | list[MeshPayload],
    model_matrix: NDArray[np.float32],
    view_matrix: NDArray[np.float32],
    name: str = "Unknown create_mesh_renderee",
) -> MeshRenderee:
    if isinstance(mesh, list):
        meshes = cast(list[MeshPayload], mesh)
        return create_mesh_list_renderee(
            ctx, program, meshes, model_matrix, view_matrix, name
        )
    return create_single_mesh_renderee(
        ctx, program, mesh, model_matrix, view_matrix, name
    )


def create_mesh_list_renderee(
    ctx: moderngl.Context,
    program: moderngl.Program,
    meshes: list[MeshPayload],
    model_matrix: NDArray[np.float32],
    view_matrix: NDArray[np.float32],
    name: str,
) -> MeshListRenderee:
    opaques, alphas = split_opaque_alpha(meshes)
    opaque_renderee = create_mesh_list_opaque_renderee(ctx, program, opaques)
    alpha_renderee = create_mesh_list_alpha_renderee(
        ctx, program, alphas, model_matrix, view_matrix, name
    )
    return MeshListRenderee(opaque_renderee, alpha_renderee)


def create_single_mesh_renderee(
    ctx: moderngl.Context,
    program: moderngl.Program,
    mesh: MeshPayload,
    model_matrix: NDArray[np.float32],
    view_matrix: NDArray[np.float32],
    name: str,
) -> MeshRenderee:
    if is_alpha(mesh):
        return AlphaMeshRenderee(ctx, program, mesh, model_matrix, view_matrix, name)
    return OpaqueMeshRenderee(ctx, program, mesh, name=name)


def create_mesh_list_opaque_renderee(
    ctx: moderngl.Context, program: moderngl.Program, meshes: list[MeshPayload]
) -> MeshListOpaqueRenderee | MeshNullRenderee:
    if not meshes:
        return MeshNullRenderee()
    return MeshListOpaqueRenderee(ctx, program, meshes)


def create_mesh_list_alpha_renderee(
    ctx: moderngl.Context,
    program: moderngl.Program,
    meshes: list[MeshPayload],
    model_matrix: NDArray[np.float32],
    view_matrix: NDArray[np.float32],
    name: str,
) -> MeshListAlphaRenderee | MeshNullRenderee:
    if not meshes:
        return MeshNullRenderee()
    return MeshListAlphaRenderee(ctx, program, meshes, model_matrix, view_matrix, name)


def split_opaque_alpha(
    meshes: list[MeshPayload],
) -> tuple[list[MeshPayload], list[MeshPayload]]:
    opaques: list[MeshPayload] = []
    alphas: list[MeshPayload] = []
    for mesh in meshes:
        (alphas if is_alpha(mesh) else opaques).append(mesh)
    return opaques, alphas


def is_alpha(mesh: MeshPayload) -> bool:
    color = mesh.color if mesh.color is not None else DEFAULT_COLOR
    return int(color[3]) < 255


def expand_payload(
    payload: MeshPayload,
) -> tuple[
    NDArray[np.float32],
    NDArray[np.float32],
    NDArray[np.uint8],
    NDArray[np.uint8],
]:
    triangles = np.ascontiguousarray(payload.vertices[payload.faces], dtype="f4")
    normals = np.ascontiguousarray(
        np.broadcast_to(payload.face_normals[:, np.newaxis, :], triangles.shape),
        dtype="f4",
    )
    color = payload.color if payload.color is not None else DEFAULT_COLOR
    colors = np.broadcast_to(color, (len(payload.faces), 3, 4)).copy()
    edges = create_edge_detect_array(len(payload.faces))
    return triangles, normals, colors, edges


def create_colors_array(
    color: NDArray[np.uint8], triangle_count: int
) -> NDArray[np.uint8]:
    return np.broadcast_to(color, (triangle_count, 3, 4)).copy()


def create_edge_detect_array(triangle_count: int) -> NDArray[np.uint8]:
    return np.tile(
        np.array([255, 0, 0, 0, 255, 0, 0, 0, 255], dtype=np.uint8),
        (triangle_count, 1),
    )


def create_vao_from_payload(
    ctx: moderngl.Context, program: moderngl.Program, payload: MeshPayload
) -> moderngl.VertexArray:
    return create_vao_from_arrays(ctx, program, *expand_payload(payload))


def create_vao_from_arrays(
    ctx: moderngl.Context,
    program: moderngl.Program,
    triangles: NDArray[np.float32],
    normals_arr: NDArray[np.float32],
    colors_arr: NDArray[np.uint8],
    edge_detect_arr: NDArray[np.uint8],
) -> moderngl.VertexArray:
    vertices = ctx.buffer(data=np.ascontiguousarray(triangles).tobytes())
    normals = ctx.buffer(data=np.ascontiguousarray(normals_arr).tobytes())
    colors = ctx.buffer(data=np.ascontiguousarray(colors_arr).tobytes())
    edge_detect = ctx.buffer(data=np.ascontiguousarray(edge_detect_arr).tobytes())
    return create_vao(ctx, program, vertices, normals, colors, edge_detect)


def create_vao(
    ctx: moderngl.Context,
    program: moderngl.Program,
    vertices: moderngl.Buffer,
    normals: moderngl.Buffer,
    colors: moderngl.Buffer,
    edge_detect: moderngl.Buffer,
) -> moderngl.VertexArray:
    return ctx.vertex_array(
        program,
        [
            (vertices, "3f4", "in_position"),
            (normals, "3f4", "in_normal"),
            (colors, "4f1", "in_color"),
            (edge_detect, "3f1", "in_edge_detect"),
        ],
        mode=moderngl.TRIANGLES,
    )


def payload_corners(payload: MeshPayload) -> NDArray[np.float32]:
    minimum, maximum = payload.bounds
    x0, y0, z0 = minimum
    x1, y1, z1 = maximum
    return np.array(
        [
            [x0, y0, z0],
            [x0, y0, z1],
            [x0, y1, z0],
            [x0, y1, z1],
            [x1, y0, z0],
            [x1, y0, z1],
            [x1, y1, z0],
            [x1, y1, z1],
        ],
        dtype="f4",
    )


class MeshRenderee(Renderee):
    @property
    @abstractmethod
    def points(self) -> NDArray[np.float32]: ...

    @abstractmethod
    def subscribe_to_updates(self, updates: Observable) -> None: ...


class OpaqueMeshRenderee(MeshRenderee):
    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        mesh: MeshPayload,
        cull_back_face: bool = False,
        name: str = "Unnamed Mesh",
    ):
        super().__init__(ctx, program, name)
        self._mesh = mesh
        self._vao: moderngl.VertexArray | None = None
        self._points = payload_corners(mesh)
        self._cull_back_face = cull_back_face

    @property
    def points(self) -> NDArray[np.float32]:
        return self._points

    def subscribe_to_updates(self, updates: Observable) -> None:
        return None

    def render(self) -> None:
        if self._cull_back_face:
            self._ctx.enable(moderngl.CULL_FACE)
            self._ctx.front_face = "ccw"
            self._ctx.cull_face = "back"
        else:
            self._ctx.disable(moderngl.CULL_FACE)
        self._ctx.enable(moderngl.DEPTH_TEST)
        self._ctx.disable(moderngl.BLEND)
        self._ctx.depth_mask = True  # ty: ignore[unresolved-attribute]
        if self._vao is None:
            self._vao = create_vao_from_payload(self._ctx, self._program, self._mesh)
        self._vao.render()


class MeshNullRenderee(MeshRenderee):
    def __init__(self):
        self._points = np.empty((1, 3), dtype="f4")

    @property
    def points(self) -> NDArray[np.float32]:
        return self._points

    def subscribe_to_updates(self, updates: Observable) -> None:
        return None

    def render(self) -> None:
        return None


class AlphaRenderee(Renderee):
    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        triangles: NDArray[np.float32],
        normals: NDArray[np.float32],
        colors: NDArray[np.uint8],
        model_matrix: NDArray[np.float32],
        view_matrix: NDArray[np.float32],
        name: str = "Unknown AlphaRenderee",
    ):
        super().__init__(ctx, program, name)
        self._triangles = triangles
        self._normals = normals
        self._colors = colors
        self._model_matrix = model_matrix
        self._view_matrix = view_matrix
        self._resort_verts = True
        self._vao: moderngl.VertexArray | None = None

    @property
    def model_matrix(self) -> NDArray[np.float32]:
        return self._model_matrix

    @model_matrix.setter
    def model_matrix(self, value: NDArray[np.float32]) -> None:
        self._model_matrix = value
        self._resort_verts = True

    @property
    def view_matrix(self) -> NDArray[np.float32]:
        return self._view_matrix

    @view_matrix.setter
    def view_matrix(self, value: NDArray[np.float32]) -> None:
        self._view_matrix = value
        self._resort_verts = True

    def subscribe_to_updates(self, updates: Observable) -> None:
        updates.subscribe(self.update_matrix)

    def update_matrix(self, var: ShaderVar, matrix: NDArray[np.float32]) -> None:
        if var == ShaderVar.MODEL_MATRIX:
            self.model_matrix = matrix
        elif var == ShaderVar.VIEW_MATRIX:
            self.view_matrix = matrix

    def _sort_buffers(self) -> None:
        sorted_indices = sort_triangles(
            self._triangles, self.model_matrix, self.view_matrix
        )
        self._vao = create_vao_from_arrays(
            self._ctx,
            self._program,
            self._triangles[sorted_indices],
            self._normals[sorted_indices],
            self._colors[sorted_indices],
            create_edge_detect_array(len(self._triangles)),
        )
        self._resort_verts = False

    def render(self) -> None:
        if self._resort_verts:
            self._sort_buffers()
        self._ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self._ctx.enable(moderngl.DEPTH_TEST)
        self._ctx.enable(moderngl.BLEND)
        self._ctx.depth_mask = False  # ty: ignore[unresolved-attribute]
        try:
            vao = self._vao
            if vao is None:
                raise RuntimeError("transparent mesh VAO was not created")
            vao.render()
        finally:
            self._ctx.depth_mask = True  # ty: ignore[unresolved-attribute]


class AlphaMeshRenderee(MeshRenderee):
    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        mesh: MeshPayload,
        model_matrix: NDArray[np.float32],
        view_matrix: NDArray[np.float32],
        name: str = "Unknown AlphaMesh",
    ):
        triangles, normals, colors, _ = expand_payload(mesh)
        self._alpha_renderee = AlphaRenderee(
            ctx, program, triangles, normals, colors, model_matrix, view_matrix, name
        )
        self._points = payload_corners(mesh)
        self.name = name

    @property
    def points(self) -> NDArray[np.float32]:
        return self._points

    def subscribe_to_updates(self, updates: Observable) -> None:
        updates.subscribe(self._alpha_renderee.update_matrix)

    def render(self) -> None:
        self._alpha_renderee.render()


class MeshListOpaqueRenderee(MeshRenderee):
    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        meshes: list[MeshPayload],
        name: str = "Unknown MeshList",
    ):
        super().__init__(ctx, program, name)
        self._renderees = [OpaqueMeshRenderee(ctx, program, mesh) for mesh in meshes]

    @property
    def points(self) -> NDArray[np.float32]:
        return np.concatenate([r.points for r in self._renderees], axis=0, dtype="f4")

    def subscribe_to_updates(self, updates: Observable) -> None:
        return None

    def render(self) -> None:
        for renderee in self._renderees:
            renderee.render()


class MeshListAlphaRenderee(MeshRenderee):
    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        meshes: list[MeshPayload],
        model_matrix: NDArray[np.float32],
        view_matrix: NDArray[np.float32],
        name: str = "Unknown MeshListAlpha",
    ):
        expanded = [expand_payload(mesh) for mesh in meshes]
        self._alpha_renderee = AlphaRenderee(
            ctx,
            program,
            np.ascontiguousarray(np.concatenate([item[0] for item in expanded])),
            np.ascontiguousarray(np.concatenate([item[1] for item in expanded])),
            np.ascontiguousarray(np.concatenate([item[2] for item in expanded])),
            model_matrix,
            view_matrix,
            name,
        )
        self._points = np.concatenate([payload_corners(mesh) for mesh in meshes])

    @property
    def points(self) -> NDArray[np.float32]:
        return self._points

    def subscribe_to_updates(self, updates: Observable) -> None:
        updates.subscribe(self._alpha_renderee.update_matrix)

    def render(self) -> None:
        self._alpha_renderee.render()


class MeshListRenderee(MeshRenderee):
    def __init__(
        self,
        opaques_renderee: MeshListOpaqueRenderee | MeshNullRenderee,
        alphas_renderee: MeshListAlphaRenderee | MeshNullRenderee,
    ):
        self._opaques_renderee = opaques_renderee
        self._alphas_renderee = alphas_renderee

    @property
    def points(self) -> NDArray[np.float32]:
        return np.concatenate(
            [self._opaques_renderee.points, self._alphas_renderee.points], axis=0
        )

    def subscribe_to_updates(self, updates: Observable) -> None:
        self._alphas_renderee.subscribe_to_updates(updates)

    def render(self) -> None:
        self._opaques_renderee.render()
        self._alphas_renderee.render()


def sort_triangles(
    triangles: NDArray[np.float32],
    model_matrix: NDArray[np.float32],
    view_matrix: NDArray[np.float32],
) -> NDArray[np.intp]:
    vertices = triangles.reshape(-1, 3)
    vertices_4d = np.hstack([vertices, np.ones((len(vertices), 1), dtype="f4")])
    eye_verts = vertices_4d @ model_matrix @ view_matrix
    depths = eye_verts[:, 2] / eye_verts[:, 3]
    max_depths = np.max(depths.reshape(-1, 3), axis=1)
    return np.argsort(max_depths)
