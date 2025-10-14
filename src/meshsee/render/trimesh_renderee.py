import logging
from abc import abstractmethod

import moderngl
import numpy as np
from numpy.typing import NDArray
from trimesh import Trimesh
from trimesh.bounds import (
    corners,  # pyright: ignore[reportUnknownVariableType] can't resolve
)

from meshsee.observable import Observable
from meshsee.render.label_renderee import Renderee
from meshsee.render.shader_program import ShaderVar

logger = logging.getLogger(__name__)

DEFAULT_COLOR = [0.5, 0.5, 0.5, 1.0]


def create_vao_from_mesh(
    ctx: moderngl.Context, program: moderngl.Program, mesh: Trimesh
) -> moderngl.VertexArray:
    return create_vao_from_arrays(
        ctx,
        program,
        mesh.triangles,
        mesh.triangles_cross,
        create_colors_array_from_mesh(mesh),
        create_edge_detect_array(mesh.triangles.shape[0]),
    )


def create_colors_array_from_mesh(mesh: Trimesh) -> NDArray[np.uint8]:
    return create_colors_array(get_metadata_color(mesh), mesh.triangles.shape[0])


def get_metadata_color(mesh: Trimesh) -> NDArray[np.uint8]:
    metadata: dict[str, dict[str, list[float]]]
    metadata = mesh.metadata  # pyright: ignore[reportUnknownVariableType]
    if (
        isinstance(
            metadata, dict
        )  # pyright: ignore[reportUnnecessaryIsInstance] - needed since ignoring type in line above
        and "meshsee" in metadata
    ):
        if (
            metadata["meshsee"]
            is not None  # pyright: ignore[reportUnnecessaryComparison] - needed since ignoring type above
            and "color" in metadata["meshsee"]
        ):
            color = metadata["meshsee"]["color"]
            if len(color) == 4 and all(isinstance(c, float) for c in color):
                return convert_color_to_uint8(metadata["meshsee"]["color"])
            else:
                raise ValueError(
                    "The color in mesh.metadata['meshsee']['color'] must be a list of 4 floats"
                )
    return convert_color_to_uint8(DEFAULT_COLOR)


def convert_color_to_uint8(color: list[float]) -> NDArray[np.uint8]:
    return (np.array(color) * 255).round().astype(np.uint8)


def create_colors_array(
    color: NDArray[np.uint8], triangle_count: int
) -> NDArray[np.uint8]:
    return np.tile(color, triangle_count * 3).astype(np.uint8).reshape(-1, 3, 4)


def create_edge_detect_array(triangle_count: int) -> NDArray[np.uint8]:
    return np.tile(
        np.array([255, 0, 0, 0, 255, 0, 0, 0, 255], dtype=np.uint8), triangle_count
    )


def create_vao_from_arrays(
    ctx: moderngl.Context,
    program: moderngl.Program,
    triangles: NDArray[np.float32],
    triangles_cross: NDArray[np.float32],
    colors_arr: NDArray[np.uint8],
    edge_detect_arr: NDArray[np.uint8],
) -> moderngl.VertexArray:
    vertices = ctx.buffer(data=triangles.astype("f4").tobytes())
    normals = ctx.buffer(
        data=np.array([[v] * 3 for v in triangles_cross]).astype("f4").tobytes()
    )
    colors = ctx.buffer(data=colors_arr.tobytes())
    edge_detect = ctx.buffer(data=edge_detect_arr.tobytes())
    return create_vao(ctx, program, vertices, normals, colors, edge_detect)


def create_vao(
    ctx: moderngl.Context,
    program: moderngl.Program,
    vertices: moderngl.Buffer,
    normals: moderngl.Buffer,
    colors: moderngl.Buffer,
    edge_detect: moderngl.Buffer,
) -> moderngl.VertexArray:
    try:
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
    except Exception as e:
        logger.exception(f"Error creating vertex array: {e}")
        raise e


def concat_colors(meshes: list[Trimesh]) -> NDArray[np.uint8]:
    colors_list = np.empty(
        (0, 12),
        dtype=np.uint8,  # 12 = 4 color components * 3 vertices per triangle
    )
    for mesh in meshes:
        color = get_metadata_color(mesh)
        n_triangles = mesh.triangles.shape[0]
        colors_list = np.append(colors_list, np.tile(color, (n_triangles, 3)), axis=0)
    return colors_list


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
        cull_back_face: bool = False,
        name: str = "Unnamed Trimesh",
    ):
        super().__init__(ctx, program, name)
        self._ctx = ctx
        self._program = program
        self._mesh = mesh
        self._vao = None
        self._points = corners(mesh.bounds)
        self._cull_back_face = cull_back_face

    @property
    def points(self) -> NDArray[np.float32]:
        return self._points.astype("f4")

    def subscribe_to_updates(self, updates: Observable):
        pass

    def render(self):
        if self._cull_back_face:
            self._ctx.enable(moderngl.CULL_FACE)
            self._ctx.front_face = "ccw"
            self._ctx.cull_face = "back"  # Cull back-facing triangles
        else:
            self._ctx.disable(moderngl.CULL_FACE)
        self._ctx.enable(moderngl.DEPTH_TEST)
        self._ctx.disable(moderngl.BLEND)
        self._ctx.depth_mask = True  # type: ignore[attr-defined]
        if (
            self._vao is None
        ):  # Lazily create the _vao so that it is created during the render when the context is active
            self._vao = create_vao_from_mesh(self._ctx, self._program, self._mesh)
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
        colors_arr: NDArray[np.uint8],
        model_matrix: NDArray[np.float32],
        view_matrix: NDArray[np.float32],
        name: str = "Unknown AlphaRenderee",
    ):
        super().__init__(ctx, program, name)
        self._triangles = triangles
        self._triangles_cross = triangles_cross
        self._colors_arr = colors_arr
        self._model_matrix = model_matrix
        self._view_matrix = view_matrix
        self._resort_verts = True

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
    def view_matrix(self, value: NDArray[np.float32]):
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
        edge_detect_arr = create_edge_detect_array(self._triangles.shape[0])
        self._vao = create_vao_from_arrays(
            self._ctx,
            self._program,
            sorted_triangles,
            sorted_triangles_cross,
            sorted_colors,
            edge_detect_arr,
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
        name: str = "Unknown TrimeshAlpha",
    ):
        self._alpha_renderee = AlphaRenderee(
            ctx,
            program,
            mesh.triangles,
            mesh.triangles_cross,
            create_colors_array_from_mesh(mesh),
            model_matrix,
            view_matrix,
            name,
        )
        self._points = corners(mesh.bounds)
        self.name = name

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
        name: str = "Unknown TrimeshList",
    ):
        super().__init__(ctx, program, name)
        self._renderees = [TrimeshOpaqueRenderee(ctx, program, mesh) for mesh in meshes]

    @property
    def points(self) -> NDArray[np.float32]:
        if len(self._renderees) == 0:
            return np.empty((1, 3), dtype="f4")
        return np.concatenate([r.points for r in self._renderees], axis=0, dtype="f4")

    def subscribe_to_updates(self, updates: Observable):
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
        name: str = "Unknow TrimeshListAlpha",
    ):
        self._alpha_renderee = AlphaRenderee(
            ctx,
            program,
            np.concatenate([mesh.triangles for mesh in meshes]).astype("f4"),
            np.concatenate([mesh.triangles_cross for mesh in meshes]).astype("f4"),
            concat_colors(meshes),
            model_matrix,
            view_matrix,
            name,
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
    name: str = "Unknown create_trimesh_renderee",
) -> TrimeshRenderee:
    if isinstance(mesh, list):
        return create_trimesh_list_renderee(
            ctx,
            program,
            mesh,
            model_matrix,
            view_matrix,
            name,
        )
    else:
        return create_single_trimesh_renderee(
            ctx,
            program,
            mesh,
            model_matrix,
            view_matrix,
            name,
        )


def create_trimesh_list_renderee(
    ctx: moderngl.Context,
    program: moderngl.Program,
    meshes: list[Trimesh],
    model_matrix: NDArray[np.float32],
    view_matrix: NDArray[np.float32],
    name: str,
) -> TrimeshListRenderee:
    opaques, alphas = split_opaque_alpha(meshes)
    opaques_renderee = create_trimesh_list_opaque_renderee(ctx, program, opaques)
    alphas_renderee = create_trimesh_list_alpha_renderee(
        ctx,
        program,
        alphas,
        model_matrix,
        view_matrix,
        name,
    )
    return TrimeshListRenderee(opaques_renderee, alphas_renderee)


def split_opaque_alpha(meshes: list[Trimesh]) -> tuple[list[Trimesh], list[Trimesh]]:
    alphas: list[Trimesh] = []
    opaques: list[Trimesh] = []
    for mesh in meshes:
        if is_alpha(mesh):
            alphas.append(mesh)
        else:
            opaques.append(mesh)
    return opaques, alphas


def is_alpha(mesh: Trimesh) -> bool:
    return get_metadata_color(mesh)[3] < 255


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
    name: str,
):
    if len(alphas) == 0:
        return TrimeshNullRenderee()
    return TrimeshListAlphaRenderee(
        ctx, program, alphas, model_matrix, view_matrix, name
    )


def create_single_trimesh_renderee(
    ctx: moderngl.Context,
    program: moderngl.Program,
    mesh: Trimesh,
    model_matrix: NDArray[np.float32],
    view_matrix: NDArray[np.float32],
    name: str,
) -> TrimeshRenderee:
    if is_alpha(mesh):
        return TrimeshAlphaRenderee(
            ctx,
            program,
            mesh,
            model_matrix,
            view_matrix,
            name,
        )
    else:
        return TrimeshOpaqueRenderee(ctx, program, mesh, name=name)


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
