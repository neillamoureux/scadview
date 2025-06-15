import logging
from abc import abstractmethod

import moderngl
import numpy as np
from numpy.typing import NDArray
from trimesh import Trimesh
from trimesh.bounds import corners

from meshsee.observable import Observable
from meshsee.render.label_renderee import Renderee
from meshsee.render.shader_program import ShaderVar

logger = logging.getLogger(__name__)

DEFAULT_COLOR = np.array([0.5, 0.5, 0.5, 1.0], "f4")


def create_vao_from_mesh(
    ctx: moderngl.Context, program: moderngl.Program, mesh: Trimesh
) -> moderngl.VertexArray:
    return create_vao_from_arrays(
        ctx,
        program,
        mesh.triangles,
        mesh.triangles_cross,
        create_colors_array_from_mesh(mesh),
    )


def create_colors_array_from_mesh(mesh: Trimesh) -> NDArray[np.float32]:
    return create_colors_array(get_metadata_color(mesh), mesh.triangles.shape[0])


def get_metadata_color(mesh: Trimesh) -> NDArray[np.float32]:
    if isinstance(mesh.metadata, dict) and "meshsee" in mesh.metadata:
        if mesh.metadata["meshsee"] is not None and "color" in mesh.metadata["meshsee"]:
            return np.array(mesh.metadata["meshsee"]["color"])
    return DEFAULT_COLOR


def create_colors_array(
    color: NDArray[np.float32], triangle_count: int
) -> NDArray[np.float32]:
    return np.tile(color, triangle_count * 3).astype("f4").reshape(-1, 3, 4)


def create_vao_from_arrays(
    ctx: moderngl.Context,
    program: moderngl.Program,
    triangles: NDArray[np.float32],
    triangles_cross: NDArray[np.float32],
    colors_arr: NDArray[np.float32],
) -> moderngl.VertexArray:
    vertices = ctx.buffer(data=triangles.astype("f4").tobytes())
    normals = ctx.buffer(
        data=np.array([[v] * 3 for v in triangles_cross]).astype("f4").tobytes()
    )
    colors = ctx.buffer(data=colors_arr.astype("f4").tobytes())
    return create_vao(ctx, program, vertices, normals, colors)


def create_vao(
    ctx: moderngl.Context,
    program: moderngl.Program,
    vertices: moderngl.Buffer,
    normals: moderngl.Buffer,
    colors: moderngl.Buffer,
) -> moderngl.VertexArray:
    try:
        return ctx.vertex_array(
            program,
            [
                (vertices, "3f4", "in_position"),
                (normals, "3f4", "in_normal"),
                (colors, "4f4", "in_color"),
            ],
            mode=moderngl.TRIANGLES,
        )
    except Exception as e:
        logger.exception(f"Error creating vertex array: {e}")
        raise e


def concat_colors(meshes: list[Trimesh]) -> NDArray[np.float32]:
    colors_list = []
    for mesh in meshes:
        color = get_metadata_color(mesh)
        n_triangles = mesh.triangles.shape[0]
        colors_list.append(np.tile(color, (n_triangles, 3)))
    return np.concatenate(colors_list, axis=0).astype("f4")


class TrimeshRenderee(Renderee):
    @property
    @abstractmethod
    def points(self) -> NDArray[np.float32]: ...

    @abstractmethod
    def subscribe_to_updates(self, updates: Observable): ...


class TrimeshOpaqueRenderee(TrimeshRenderee):
    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        mesh: Trimesh,
    ):
        super().__init__(ctx, program)
        self._ctx = ctx
        self._program = program
        self._vao = create_vao_from_mesh(ctx, program, mesh)
        self._points = corners(mesh.bounds)

    @property
    def points(self) -> NDArray[np.float32]:
        return self._points.astype("f4")

    def subscribe_to_updates(self, updates: Observable):
        pass

    def render(self):
        self._ctx.enable(moderngl.DEPTH_TEST)
        self._ctx.disable(moderngl.BLEND)
        self._ctx.depth_mask = True  # type: ignore[attr-defined]
        self._vao.render()


class TrimeshNullRenderee(TrimeshRenderee):
    def __init__(self):
        self._points = np.empty((1, 3), dtype="f4")

    @property
    def points(self) -> NDArray[np.float32]:
        return self._points

    def subscribe_to_updates(self, updates: Observable):
        pass

    def render(self):
        pass


class AlphaRenderee(Renderee):
    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        triangles: NDArray[np.float32],
        triangles_cross: NDArray[np.float32],
        colors_arr: NDArray[np.float32],
        model_matrix: NDArray[np.float32],
        view_matrix: NDArray[np.float32],
    ):
        super().__init__(ctx, program)
        self._triangles = triangles
        self._triangles_cross = triangles_cross
        self._colors_arr = colors_arr
        self._model_matrix = model_matrix
        self._view_matrix = view_matrix
        self._resort_verts = True
        self._sort_buffers()

    @property
    def model_matrix(self) -> NDArray[np.float32]:
        return self._model_matrix

    @model_matrix.setter
    def model_matrix(self, value: NDArray[np.float32]):
        self._model_matrix = value
        self._resort_verts = True

    @property
    def view_matrix(self) -> NDArray[np.float32]:
        return self._view_matrix

    @view_matrix.setter
    def view_matrix(self, value):
        self._view_matrix = value
        self._resort_verts = True

    def subscribe_to_updates(self, updates: Observable):
        updates.subscribe(self.update_matrix)

    def update_matrix(self, var: ShaderVar, matrix: NDArray[np.float32]):
        if var == ShaderVar.MODEL_MATRIX:
            self.model_matrix = matrix
        elif var == ShaderVar.VIEW_MATRIX:
            self.view_matrix = matrix

    def _sort_buffers(self):
        sorted_indices = sort_triangles(
            self._triangles, self.model_matrix, self.view_matrix
        )
        sorted_triangles = self._triangles[sorted_indices]
        sorted_triangles_cross = self._triangles_cross[sorted_indices]
        sorted_colors = self._colors_arr[sorted_indices]
        self._vao = create_vao_from_arrays(
            self._ctx,
            self._program,
            sorted_triangles,
            sorted_triangles_cross,
            sorted_colors,
        )
        self._resort_verts = False

    def render(self):
        if self._resort_verts:
            self._sort_buffers()
        self._ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self._ctx.enable(moderngl.DEPTH_TEST)
        self._ctx.enable(moderngl.BLEND)
        self._ctx.depth_mask = False  # type: ignore[attr-defined]
        self._vao.render()


class TrimeshAlphaRenderee(TrimeshRenderee):
    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        mesh: Trimesh,
        model_matrix: NDArray[np.float32],
        view_matrix: NDArray[np.float32],
    ):
        self._alpha_renderee = AlphaRenderee(
            ctx,
            program,
            mesh.triangles,
            mesh.triangles_cross,
            create_colors_array_from_mesh(mesh),
            model_matrix,
            view_matrix,
        )
        self._points = corners(mesh.bounds)

    @property
    def points(self):
        return self._points.astype("f4")

    def subscribe_to_updates(self, updates: Observable):
        updates.subscribe(self._alpha_renderee.update_matrix)

    def render(self):
        self._alpha_renderee.render()


class TrimeshListOpaqueRenderee(TrimeshRenderee):
    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        meshes: list[Trimesh],
    ):
        super().__init__(ctx, program)
        self._renderees = [TrimeshOpaqueRenderee(ctx, program, mesh) for mesh in meshes]

    @property
    def points(self) -> NDArray[np.float32]:
        if len(self._renderees) == 0:
            return np.empty((1, 3), dtype="f4")
        return np.concatenate([r.points for r in self._renderees], axis=0, dtype="f4")

    def subscribe_to_updates(self, updates):
        pass

    def render(self):
        for renderee in self._renderees:
            renderee.render()


class TrimeshListAlphaRenderee(TrimeshRenderee):
    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        meshes: list[Trimesh],
        model_matrix: NDArray[np.float32],
        view_matrix: NDArray[np.float32],
    ):
        self._alpha_renderee = AlphaRenderee(
            ctx,
            program,
            np.concatenate([mesh.triangles for mesh in meshes]).astype("f4"),
            np.concatenate([mesh.triangles_cross for mesh in meshes]).astype("f4"),
            concat_colors(meshes),
            model_matrix,
            view_matrix,
        )

        self._points = np.concatenate([corners(mesh.bounds) for mesh in meshes]).astype(
            "f4"
        )

    @property
    def points(self):
        return self._points

    def subscribe_to_updates(self, updates: Observable):
        updates.subscribe(self._alpha_renderee.update_matrix)

    def render(self):
        self._alpha_renderee.render()


class TrimeshListRenderee(TrimeshRenderee):
    def __init__(
        self,
        opaques_renderee: TrimeshListOpaqueRenderee | TrimeshNullRenderee,
        alphas_renderee: TrimeshListAlphaRenderee | TrimeshNullRenderee,
    ):
        self._opaques_renderee = opaques_renderee
        self._alphas_renderee = alphas_renderee

    @property
    def points(self) -> NDArray[np.float32]:
        return np.concatenate(
            [self._opaques_renderee.points, self._alphas_renderee.points], axis=0
        )

    def subscribe_to_updates(self, updates: Observable):
        self._alphas_renderee.subscribe_to_updates(updates)

    def render(self):
        self._opaques_renderee.render()
        self._alphas_renderee.render()


def create_trimesh_renderee(
    ctx: moderngl.Context,
    program: moderngl.Program,
    mesh: Trimesh | list[Trimesh],
    model_matrix: NDArray[np.float32],
    view_matrix: NDArray[np.float32],
) -> TrimeshRenderee:
    if isinstance(mesh, list):
        if not all(isinstance(m, Trimesh) for m in mesh):
            raise TypeError("All elements in the mesh list must be Trimesh instances.")
        return create_trimesh_list_renderee(
            ctx,
            program,
            mesh,
            model_matrix,
            view_matrix,
        )
    elif isinstance(mesh, Trimesh):
        return create_single_trimesh_renderee(
            ctx, program, mesh, model_matrix, view_matrix
        )
    elif not isinstance(mesh, Trimesh):
        raise TypeError("mesh must be a Trimesh or a list of Trimesh objects.")


def create_trimesh_list_renderee(
    ctx: moderngl.Context,
    program: moderngl.Program,
    meshes: list[Trimesh],
    model_matrix: NDArray[np.float32],
    view_matrix: NDArray[np.float32],
) -> TrimeshListRenderee:
    if not all(isinstance(m, Trimesh) for m in meshes):
        raise TypeError("All elements in the mesh list must be Trimesh instances.")
    opaques, alphas = split_opaque_alpha(meshes)
    opaques_renderee = create_trimesh_list_opaque_renderee(ctx, program, opaques)
    alphas_renderee = create_trimesh_list_alpha_renderee(
        ctx, program, alphas, model_matrix, view_matrix
    )
    return TrimeshListRenderee(opaques_renderee, alphas_renderee)


def split_opaque_alpha(meshes: list[Trimesh]):
    alphas = []
    opaques = []
    for mesh in meshes:
        if is_alpha(mesh):
            alphas.append(mesh)
        else:
            opaques.append(mesh)
    return opaques, alphas


def is_alpha(mesh: Trimesh) -> bool:
    return get_metadata_color(mesh)[3] < 1.0


def create_trimesh_list_opaque_renderee(
    ctx: moderngl.Context, program: moderngl.Program, opaques: list[Trimesh]
):
    if len(opaques) == 0:
        return TrimeshNullRenderee()
    return TrimeshListOpaqueRenderee(ctx, program, opaques)


def create_trimesh_list_alpha_renderee(
    ctx: moderngl.Context,
    program: moderngl.Program,
    alphas: list[Trimesh],
    model_matrix: NDArray[np.float32],
    view_matrix: NDArray[np.float32],
):
    if len(alphas) == 0:
        return TrimeshNullRenderee()
    return TrimeshListAlphaRenderee(ctx, program, alphas, model_matrix, view_matrix)


def create_single_trimesh_renderee(
    ctx: moderngl.Context,
    program: moderngl.Program,
    mesh: Trimesh,
    model_matrix: NDArray[np.float32],
    view_matrix: NDArray[np.float32],
) -> TrimeshRenderee:
    if is_alpha(mesh):
        return TrimeshAlphaRenderee(
            ctx,
            program,
            mesh,
            model_matrix,
            view_matrix,
        )
    else:
        return TrimeshOpaqueRenderee(ctx, program, mesh)


def sort_triangles(
    triangles: NDArray[np.float32],
    model_matrix: NDArray[np.float32],
    view_matrix: NDArray[np.float32],
) -> NDArray[np.intp]:
    vertices = triangles.reshape(-1, 3)
    vertices = np.hstack([vertices, np.ones((vertices.shape[0], 1), dtype="f4")])
    eye_verts = vertices @ model_matrix @ view_matrix
    depths = eye_verts[:, 2] / eye_verts[:, 3]
    max_depths = np.max(depths.reshape(-1, 3), axis=1)
    return np.argsort(max_depths)
