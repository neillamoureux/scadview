import logging
from abc import ABC, abstractmethod

import moderngl
import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class Renderee(ABC):
    def __init__(self, ctx: moderngl.Context, program: moderngl.Program):
        self._ctx = ctx
        self._program = program

    @abstractmethod
    def render(self) -> None:
        """Render the object."""
        ...


class GnomonRenderee(Renderee):
    def __init__(self, ctx: moderngl.Context, program: moderngl.Program):
        super().__init__(ctx, program)
        self._vao = self._create_vao()

    def _vertices(self) -> NDArray:
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
        width, height = self._ctx.screen.size
        self._ctx.viewport = (0, 0, int(width * 0.2), int(height * 0.2))
        self._vao.render()
