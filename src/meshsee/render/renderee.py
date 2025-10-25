import logging
from abc import ABC, abstractmethod

import moderngl
import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class Renderee(ABC):
    def __init__(
        self, ctx: moderngl.Context, program: moderngl.Program, name: str = "Unnamed"
    ):
        self._ctx = ctx
        self._program = program
        self.name = name

    @abstractmethod
    def render(self) -> None:
        """Render the object."""
        ...


class GnomonRenderee(Renderee):
    WINDOW_DIM_FRAC = 0.2

    def __init__(
        self,
        ctx: moderngl.Context,
        program: moderngl.Program,
        window_size: tuple[int, int],
        name: str = "Uknown Gnomon",
    ):
        super().__init__(ctx, program, name)
        self._window_size = window_size
        self._vao = None

    @property
    def window_size(self) -> tuple[int, int]:
        return self._window_size

    @window_size.setter
    def window_size(self, value: tuple[int, int]):
        self._window_size = value

    def _vertices(self) -> NDArray[np.float32]:
        # fmt: off
        return np.array([ # 
            0, 0, 0, 1, 0, 0,  # Red X
            100, 0, 0, 1, 0, 0,

            0, 0, 0, 0, 1, 0,  # Green Y
            0, 100, 0, 0, 1, 0,

            0, 0, 0, 0, 0, 1,  # Blue Z
            0, 0, 100, 0, 0, 1,
        ], dtype='f4')
        # fmt: on

    def _create_vao(
        self,
    ) -> moderngl.VertexArray:
        try:
            vertices = self._ctx.buffer(data=self._vertices().tobytes())
            return self._ctx.vertex_array(
                self._program,
                [
                    (vertices, "3f4 3f4", "in_position", "in_color"),
                ],
                mode=moderngl.TRIANGLES,
            )
        except Exception as e:
            logger.exception(f"Error creating vertex array: {e}")
            raise e

    def render(self) -> None:
        self._ctx.viewport = (
            0,
            0,
            int(self._window_size[0] * self.WINDOW_DIM_FRAC),
            int(self._window_size[1] * self.WINDOW_DIM_FRAC),
        )
        if self._vao is None:
            self._vao = self._create_vao()
        self._vao.render(mode=moderngl.LINES)
        self._ctx.viewport = (
            0,
            0,
            int(self._window_size[0]),
            int(self._window_size[1]),
        )
