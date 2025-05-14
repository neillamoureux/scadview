from abc import ABC, abstractmethod
from math import pi

import moderngl
import numpy as np
from pyrr import Matrix44

from meshsee.camera import Camera
from meshsee.label_atlas import LabelAtlas


class Renderee(ABC):
    def __init__(self, ctx: moderngl.Context, program: moderngl.Program):
        self._ctx = ctx
        self._program = program

    @abstractmethod
    def render(self) -> None:
        """Render the object."""
        pass


AXIS_WIDTH = 0.01
NUMBER_HEIGHT = 1.0
NUMBER_WIDTH = 0.5


class LabelRenderee(Renderee):

    def __init__(
        self,
        ctx: moderngl.Context,
        prog: moderngl.Program,
        label_atlas: LabelAtlas,
        camera: Camera,
        label: str,
    ):
        self.ctx = ctx
        self.camera = camera
        self._number = float(label)
        self.char_width = NUMBER_WIDTH
        self.axis = 0
        self.shift_up = AXIS_WIDTH
        base_vertices = np.array(
            [
                [NUMBER_WIDTH, NUMBER_HEIGHT, 0.0],  # top left
                [NUMBER_WIDTH, 0.0, 0.0],  # bottom left
                [0.0, NUMBER_HEIGHT, 0.0],  # top right
                [0.0, 0.0, 0.0],  # bottom right
            ],
            dtype="f4",
        )

        vertices = np.empty(base_vertices.shape, dtype="f4")
        uvs = np.empty((0, 2), dtype="f4")
        center = len(label) * NUMBER_WIDTH / -2.0 + self._number
        for i, c in enumerate(label):
            offset = NUMBER_WIDTH * i + center
            vertices = np.concatenate(
                [
                    (base_vertices + np.array([offset, 0.0, 0.0], dtype="f4")),
                    vertices,
                ],
                axis=0,
                dtype="f4",
            )
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

        self.vertices = ctx.buffer(data=vertices.tobytes())
        self.uv = ctx.buffer(data=uvs.tobytes())
        self.sampler = label_atlas.sampler
        try:
            self.vao = self._create_vao(ctx, prog)
        except Exception as e:
            print(f"Error creating vertex array: {e}")

        prog["atlas"].value = 0
        self.sampler.use(location=0)
        self._prog = prog
        self._translate_to_origin = Matrix44.from_translation(
            [-self._number, 0.0, 0.0], dtype="f4"
        )
        self._translate_from_origin = Matrix44.from_translation(
            [self._number, 0.0, 0.0], dtype="f4"
        )

    def _create_vao(self, ctx: moderngl.Context, prog: moderngl.Program):
        vao = ctx.vertex_array(
            prog,
            [
                (self.vertices, "3f4", "in_position"),
                (self.uv, "2f4", "in_uv"),
            ],
            mode=moderngl.TRIANGLES,
        )
        return vao

    def render(self):
        m_mag = np.identity(4, dtype="f4")
        scale = self.char_width / NUMBER_WIDTH
        m_mag[0, 0] = scale
        m_mag[1, 1] = scale
        m_shift_up = Matrix44.from_translation([0.0, self.shift_up, 0.0], dtype="f4")
        # m_scale = (
        #     m_shift_up * self._translate_from_origin * m_mag * self._translate_to_origin
        # )
        # self._prog["m_scale"].write(m_scale)
        self.sampler.use(location=0)
        self.ctx.enable(moderngl.BLEND)
        # Use the standard alpha blend function
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        # x axis
        if self.axis == 0:
            m_scale = (
                m_shift_up
                * self._translate_from_origin
                * m_mag
                * self._translate_to_origin
            )
        if self.axis == 1:
            rotation = Matrix44.from_z_rotation(-pi / 2.0, dtype="f4")
            m_scale = (
                rotation
                * m_shift_up
                * self._translate_from_origin
                * m_mag
                * self._translate_to_origin
            )
        if self.axis == 2:
            rotation_z = Matrix44.from_z_rotation(
                pi, dtype="f4"
            ) * Matrix44.from_y_rotation(pi / 2.0, dtype="f4")
            m_scale = (
                rotation_z
                * m_shift_up
                * self._translate_from_origin
                * m_mag
                * self._translate_to_origin
            )

        self._prog["m_scale"].write(m_scale)
        self.vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.disable(moderngl.BLEND)
