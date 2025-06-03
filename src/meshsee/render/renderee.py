from abc import ABC, abstractmethod
from math import pi

import moderngl
from manifold3d import Manifold, Mesh
import numpy as np
from pyrr import Matrix44
from trimesh import Trimesh
from trimesh.bounds import corners

from meshsee.camera import Camera
from meshsee.label_atlas import LabelAtlas
from meshsee.label_metrics import label_char_width, label_step, labels_to_show
from meshsee.renderer import ShaderVar


class Renderee(ABC):
    def __init__(self, ctx: moderngl.Context, program: moderngl.Program):
        self._ctx = ctx
        self._program = program

    @abstractmethod
    def render(self) -> None:
        """Render   he object."""
        pass


AXIS_WIDTH = 0.01


# Helper to convert a Manifold into a Trimesh
# From https://colab.research.google.com/drive/1VxrFYHPSHZgUbl9TeWzCeovlpXrPQ5J5?usp=sharing#scrollTo=xCHqkWeJXgmJ
#
def manifold_to_trimesh(manifold: Manifold) -> Trimesh:
    mesh = manifold.to_mesh()
    return manifold_mesh_to_trimesh(mesh)


def manifold_mesh_to_trimesh(mesh: Mesh) -> Trimesh:
    if mesh.vert_properties.shape[1] > 3:
        vertices = mesh.vert_properties[:, :3]
        colors = (mesh.vert_properties[:, 3:] * 255).astype(np.uint8)
    else:
        vertices = mesh.vert_properties
        colors = None

    return Trimesh(vertices=vertices, faces=mesh.tri_verts, vertex_colors=colors)


class TrimeshRenderee(Renderee):
    DEFAULT_COLOR = np.array([0.5, 0.5, 0.5, 1.0], "f4")

    def __init__(self, ctx: moderngl.Context, program: moderngl.Program, mesh: Trimesh):
        super().__init__(ctx, program)
        self._points = corners(mesh.bounds)
        self._vertices = ctx.buffer(data=mesh.triangles.astype("f4"))
        self._normals = ctx.buffer(
            data=np.array([[v] * 3 for v in mesh.triangles_cross])
            .astype("f4")
            .tobytes()
        )
        self._color = self.DEFAULT_COLOR
        if "meshsee" in mesh.metadata:
            if "color" in mesh.metadata["meshsee"]:
                self._color = np.array(mesh.metadata["meshsee"]["color"], "f4")
        try:
            self._vao = self._create_vao()
        except Exception as e:
            print(f"Error creating vertex array: {e}")

    @property
    def points(self) -> np.ndarray:
        return self._points

    def _create_vao(self) -> moderngl.VertexArray:
        return self._ctx.vertex_array(
            self._program,
            [
                (self._vertices, "3f4", "in_position"),
                (self._normals, "3f4", "in_normal"),
            ],
            mode=moderngl.TRIANGLES,
        )

    def render(self):
        self._program["color"] = self._color
        if self._color[3] < 1.0:
            self._ctx.blend_func = moderngl.DEFAULT_BLENDING
            self._ctx.disable(moderngl.DEPTH_TEST)
            self._ctx.enable(moderngl.BLEND)
        else:
            self._ctx.enable(moderngl.DEPTH_TEST)
            self._ctx.disable(moderngl.BLEND)
        self._vao.render()


class TrimeshListRenderee(Renderee):
    def __init__(
        self, ctx: moderngl.Context, program: moderngl.Program, meshes: list[Trimesh]
    ):
        super().__init__(ctx, program)
        self._renderees = [TrimeshRenderee(ctx, program, mesh) for mesh in meshes]

    @property
    def points(self) -> np.ndarray:
        return np.concatenate([r.points for r in self._renderees], axis=0)

    def render(self):
        for renderee in self._renderees:
            renderee.render()


class LabelRenderee(Renderee):
    ATLAS_SAMPLER_LOCATION = 0
    NUMBER_HEIGHT = 1.0
    NUMBER_WIDTH = 0.5

    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        label_atlas: LabelAtlas,
        camera: Camera,
        label: str,
    ):
        super().__init__(ctx, program)
        self._number = float(label)
        self.camera = camera
        self.char_width = self.NUMBER_WIDTH
        self.axis = 0
        self.shift_up = AXIS_WIDTH
        self._vertices = self._create_vertices(len(label))
        self._uv = self._create_uvs(label, label_atlas)
        self._sampler = label_atlas.sampler
        try:
            self._vao = self._create_vao()
        except Exception as e:
            print(f"Error creating vertex array: {e}")

        self._program["atlas"].value = self.ATLAS_SAMPLER_LOCATION
        self._translate_to_origin = Matrix44.from_translation(
            [-self._number, 0.0, 0.0], dtype="f4"
        )
        self._translate_from_origin = Matrix44.from_translation(
            [self._number, 0.0, 0.0], dtype="f4"
        )
        self._m_base_scale = np.identity(4, dtype="f4")

    def _create_vertices(self, label_len: int) -> moderngl.Buffer:
        base_vertices = np.array(
            [
                [self.NUMBER_WIDTH, self.NUMBER_HEIGHT, 0.0],  # top left
                [self.NUMBER_WIDTH, 0.0, 0.0],  # bottom left
                [0.0, self.NUMBER_HEIGHT, 0.0],  # top right
                [0.0, 0.0, 0.0],  # bottom right
            ],
            dtype="f4",
        )

        vertices = np.empty(base_vertices.shape, dtype="f4")
        center = label_len * self.NUMBER_WIDTH / -2.0 + self._number
        for i in range(label_len):
            offset = self.NUMBER_WIDTH * i + center
            vertices = np.concatenate(
                [
                    (base_vertices + np.array([offset, 0.0, 0.0], dtype="f4")),
                    vertices,
                ],
                axis=0,
                dtype="f4",
            )
        return self._ctx.buffer(data=vertices.tobytes())

    def _create_uvs(self, label: str, label_atlas: LabelAtlas) -> moderngl.Buffer:
        uvs = np.empty((0, 2), dtype="f4")
        for c in label:
            c_uvs = label_atlas.uv(c).astype("f4")

            uvs = np.concatenate(
                [
                    np.array(
                        [
                            [c_uvs[2], c_uvs[1]],  # top right
                            [c_uvs[2], c_uvs[3]],  # bottom right
                            [c_uvs[0], c_uvs[1]],  # top left
                            [c_uvs[0], c_uvs[3]],  # bottom left
                        ],
                        dtype="f4",
                    ),
                    uvs,
                ],
                axis=0,
                dtype="f4",
            )
        return self._ctx.buffer(data=uvs.tobytes())

    def _create_vao(self) -> moderngl.VertexArray:
        return self._ctx.vertex_array(
            self._program,
            [
                (self._vertices, "3f4", "in_position"),
                (self._uv, "2f4", "in_uv"),
            ],
            mode=moderngl.TRIANGLES,
        )

    def render(self):
        scale = self.char_width / self.NUMBER_WIDTH
        self._update_m_base_scale(scale)
        self._sampler.use(location=self.ATLAS_SAMPLER_LOCATION)
        self._ctx.enable(moderngl.BLEND)

        # Use the standard alpha blend function
        self._ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        m_base_scale_at_label = self._calc_base_scale_at_label_matrix()
        m_scale = self._calc_scale_matrix_for_axis(m_base_scale_at_label)
        self._program["m_scale"].write(m_scale)
        self._vao.render(moderngl.TRIANGLE_STRIP)
        self._ctx.disable(moderngl.BLEND)

    def _update_m_base_scale(self, scale: float):
        self._m_base_scale[0, 0] = scale
        self._m_base_scale[1, 1] = scale

    def _calc_base_scale_at_label_matrix(self) -> Matrix44:
        m_shift_up = Matrix44.from_translation([0.0, self.shift_up, 0.0], dtype="f4")
        m_base_scale_at_label = (
            self._translate_from_origin
            * m_shift_up
            * self._m_base_scale
            * self._translate_to_origin
        )
        return m_base_scale_at_label

    def _calc_scale_matrix_for_axis(self, m_base_scale_at_label: Matrix44) -> Matrix44:
        if self.axis == 0:
            return m_base_scale_at_label
        if self.axis == 1:
            rotation = Matrix44.from_z_rotation(-pi / 2.0, dtype="f4")
            return rotation * m_base_scale_at_label
        if self.axis == 2:
            rotation = Matrix44.from_z_rotation(
                pi, dtype="f4"
            ) * Matrix44.from_y_rotation(pi / 2.0, dtype="f4")
            return rotation * m_base_scale_at_label
        else:
            raise ValueError(f"Invalid axis value: {self.axis}. Must be 0, 1, or 2.")


class LabelSetRenderee(Renderee):
    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        label_atlas: LabelAtlas,
        max_labels_per_axis: int,
        max_label_frac_of_step: float,
        camera: Camera,
    ):
        super().__init__(ctx, program)
        self._label_atlas = label_atlas
        self.camera = camera
        self._max_labels_per_axis = max_labels_per_axis
        self._max_label_frac_of_step = max_label_frac_of_step
        self._label_renderees = {}

    def render(self):
        axis_ranges = [(i, self.camera.axis_visible_range(i)) for i in range(3)]
        visible_ranges = list(filter(lambda x: x[1] is not None, axis_ranges))
        if len(visible_ranges) == 0:
            return
        spans = [range[1][1] - range[1][0] for range in visible_ranges]
        max_span = max(spans)
        step = label_step(max_span, self._max_labels_per_axis)
        min_value = min([visible_range[1][0] for visible_range in visible_ranges])
        max_value = max([visible_range[1][1] for visible_range in visible_ranges])
        char_width = label_char_width(
            min_value, max_value, step, self._max_label_frac_of_step
        )
        for visible in visible_ranges:
            axis = visible[0]
            min_value = visible[1][0]
            max_value = visible[1][1]
            show = labels_to_show(min_value, max_value, step)
            for label in show:
                if label not in self._label_renderees.keys():
                    self._label_renderees[label] = LabelRenderee(
                        self._ctx,
                        self._program,
                        self._label_atlas,
                        self.camera,
                        label,
                    )
                l = self._label_renderees[label]
                l.char_width = char_width
                l.axis = axis
                l.render()
