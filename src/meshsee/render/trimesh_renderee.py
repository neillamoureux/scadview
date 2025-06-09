from abc import ABC, abstractmethod

import moderngl
import numpy as np
from trimesh import Trimesh
from trimesh.bounds import corners

from meshsee.observable import Observable
from meshsee.render.label_renderee import Renderee
from meshsee.shader_program import ShaderVar


def create_vao(
    ctx: moderngl.Context,
    program: moderngl.Program,
    vertices: moderngl.Buffer,
    normals: moderngl.Buffer,
    colors: moderngl.Buffer,
) -> moderngl.VertexArray:
    return ctx.vertex_array(
        program,
        [
            (vertices, "3f4", "in_position"),
            (normals, "3f4", "in_normal"),
            (colors, "4f4", "in_color"),
        ],
        mode=moderngl.TRIANGLES,
    )


class TrimeshRenderee(Renderee):
    # def __init__(self, ctx: moderngl.Context, program: moderngl.Program):
    #     super().__init__(ctx, program)
    #     self._ctx = ctx
    #     self._program = program
    #     self._vertices = self._ctx.buffer(data=np.empty((1, 3)))
    #     self._normals = self._ctx.buffer(data=np.empty((1, 3)))
    #     self._color_buff = self._ctx.buffer(data=np.empty((1, 4)))

    @property
    @abstractmethod
    def points(self) -> np.ndarray: ...

    # def _create_vao(self) -> moderngl.VertexArray:
    #     return self._ctx.vertex_array(
    #         self._program,
    #         [
    #             (self._vertices, "3f4", "in_position"),
    #             (self._normals, "3f4", "in_normal"),
    #             (self._color_buff, "4f4", "in_color"),
    #         ],
    #         mode=moderngl.TRIANGLES,
    #     )

    @abstractmethod
    def subscribe_to_updates(self, updates: Observable): ...


class TrimeshOpaqueRenderee(TrimeshRenderee):
    DEFAULT_COLOR = np.array([0.5, 0.5, 0.5, 1.0], "f4")

    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        mesh: Trimesh,
    ):
        super().__init__(ctx, program)
        self._ctx = ctx
        self._program = program
        self._triangles = mesh.triangles.astype("f4")
        self._triangles_cross = mesh.triangles_cross
        self._points = corners(mesh.bounds)
        self._vertices = ctx.buffer(data=mesh.triangles.astype("f4"))
        self._normals = ctx.buffer(
            data=np.array([[v] * 3 for v in mesh.triangles_cross])
            .astype("f4")
            .tobytes()
        )
        self._colors = (
            np.tile(get_metadata_color(mesh), self._triangles.shape[0] * 3)
            .astype("f4")
            .reshape(-1, 3, 4)
        )
        self._color_buff = self._ctx.buffer(data=self._colors.tobytes())
        try:
            self._vao = create_vao(
                ctx, program, self._vertices, self._normals, self._color_buff
            )
        except Exception as e:
            print(f"Error creating vertex array: {e}")

    @property
    def points(self) -> np.ndarray:
        return self._points

    def subscribe_to_updates(self, updates: Observable):
        pass

    def render(self):
        self._ctx.enable(moderngl.DEPTH_TEST)
        self._ctx.disable(moderngl.BLEND)
        self._ctx.depth_mask = True
        self._vao.render()


class TrimeshNullRenderee(TrimeshRenderee):
    def __init__(self):
        self._points = np.empty((1, 3))

    @property
    def points(self) -> np.ndarray:
        return self._points

    def subscribe_to_updates(self, updates: Observable):
        pass

    def render(self):
        pass


class TrimeshAlphaRenderee(TrimeshOpaqueRenderee):
    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        mesh: Trimesh,
        model_matrix: np.ndarray,
        view_matrix: np.ndarray,
    ):
        super().__init__(ctx, program, mesh)
        self.model_matrix = model_matrix
        self.view_matrix = view_matrix
        self._resort_verts = True

    @property
    def points(self) -> np.ndarray:
        return self._points

    @property
    def model_matrix(self) -> np.ndarray:
        return self._model_matrix

    @model_matrix.setter
    def model_matrix(self, value: np.ndarray):
        self._model_matrix = value
        self._resort_verts = True

    @property
    def view_matrix(self) -> np.ndarray:
        return self._view_matrix

    @view_matrix.setter
    def view_matrix(self, value):
        self._view_matrix = value
        self._resort_verts = True

    def subscribe_to_updates(self, updates: Observable):
        updates.subscribe(self.update_matrix)

    def update_matrix(self, var: ShaderVar, matrix: np.ndarray):
        if var == ShaderVar.MODEL_MATRIX:
            self.model_matrix = matrix
        elif var == ShaderVar.VIEW_MATRIX:
            self.view_matrix = matrix
        elif var == ShaderVar.PROJECTION_MATRIX:
            self.projection_matrix = matrix

    def _sort_buffers(self):
        sorted_indices = sort_triangles(
            self._triangles, self.model_matrix, self.view_matrix
        )
        sorted_triangles = self._triangles[sorted_indices]
        sorted_triangles_cross = self._triangles_cross[sorted_indices]
        sorted_colors = self._colors[sorted_indices]
        self._vertices = self._ctx.buffer(data=sorted_triangles)
        self._normals = self._ctx.buffer(
            data=np.array([[v] * 3 for v in sorted_triangles_cross])
            .astype("f4")
            .tobytes()
        )
        self._color_buff = self._ctx.buffer(data=sorted_colors.tobytes())
        self._resort_verts = False

    def render(self):
        if self._resort_verts:
            self._sort_buffers()
            self._vao = create_vao(
                self._ctx,
                self._program,
                self._vertices,
                self._normals,
                self._color_buff,
            )
        self._ctx.blend_func = moderngl.DEFAULT_BLENDING
        self._ctx.enable(moderngl.DEPTH_TEST)
        self._ctx.enable(moderngl.BLEND)
        self._ctx.depth_mask = False
        self._vao.render()


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
    def points(self) -> np.ndarray:
        if len(self._renderees) == 0:
            return np.empty((1, 3))
        return np.concatenate([r.points for r in self._renderees], axis=0)

    @property
    def subscribe_to_updates(self, updates):
        pass

    def render(self):
        for renderee in self._renderees:
            renderee.render()


class TrimeshListAlphaRenderee(TrimeshAlphaRenderee):
    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        meshes: list[Trimesh],
        model_matrix: np.ndarray,
        view_matrix: np.ndarray,
    ):
        self._ctx = ctx
        self._program = program
        self.model_matrix = model_matrix
        self.view_matrix = view_matrix
        self._points = np.concatenate([corners(mesh.bounds) for mesh in meshes])
        self._triangles = np.concatenate([mesh.triangles for mesh in meshes]).astype(
            "f4"
        )
        self._triangles_cross = np.concatenate(
            [mesh.triangles_cross for mesh in meshes]
        ).astype("f4")
        self._vertices = ctx.buffer(data=self._triangles.tobytes())
        self._normals = ctx.buffer(
            data=np.array([[v] * 3 for v in self._triangles_cross])
            .astype("f4")
            .tobytes()
        )
        colors_list = []
        for mesh in meshes:
            color = get_metadata_color(mesh)
            n_triangles = mesh.triangles.shape[0]
            colors_list.append(np.tile(color, (n_triangles, 3)))
        self._colors = np.concatenate(colors_list, axis=0).astype("f4")
        self._color_buff = self._ctx.buffer(data=self._colors.tobytes())
        try:
            self._vao = create_vao(
                self._ctx,
                self._program,
                self._vertices,
                self._normals,
                self._color_buff,
            )
        except Exception as e:
            print(f"Error creating vertex array: {e}")
        self._resort_verts = True


class TrimeshListRenderee(TrimeshRenderee):
    def __init__(
        self,
        opaques_renderee: TrimeshListOpaqueRenderee,
        alphas_renderee: TrimeshListAlphaRenderee,
    ):
        self._opaques_renderee = opaques_renderee
        self._alphas_renderee = alphas_renderee

    @property
    def points(self) -> np.ndarray:
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
    model_matrix: np.ndarray,
    view_matrix: np.ndarray,
):
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
    model_matrix: np.ndarray,
    view_matrix: np.ndarray,
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


def get_metadata_color(mesh: Trimesh) -> np.ndarray:
    if "meshsee" in mesh.metadata:
        if mesh.metadata["meshsee"] is not None and "color" in mesh.metadata["meshsee"]:
            return np.array(mesh.metadata["meshsee"]["color"])
    return TrimeshOpaqueRenderee.DEFAULT_COLOR


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
    model_matrix: np.ndarray,
    view_matrix: np.ndarray,
):
    if len(alphas) == 0:
        return TrimeshNullRenderee()
    return TrimeshListAlphaRenderee(ctx, program, alphas, model_matrix, view_matrix)


def create_single_trimesh_renderee(
    ctx: moderngl.Context,
    program: moderngl.Program,
    mesh: Trimesh,
    model_matrix: np.ndarray,
    view_matrix: np.ndarray,
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
    triangles: np.ndarray, model_matrix: np.ndarray, view_matrix: np.ndarray
) -> list[int]:
    triangle_centers = np.mean(
        triangles,
        axis=1,
    )
    triangle_centers = np.hstack(
        [triangle_centers, np.ones((triangle_centers.shape[0], 1), dtype="f4")]
    )
    eye_verts = triangle_centers @ model_matrix @ view_matrix
    depths = eye_verts[:, 2] / eye_verts[:, 3]
    return np.argsort(depths)
