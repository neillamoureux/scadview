from abc import ABC, abstractmethod

import moderngl


class Renderee(ABC):
    def __init__(self, ctx: moderngl.Context, program: moderngl.Program):
        self._ctx = ctx
        self._program = program

    @abstractmethod
    def render(self) -> None:
        """Render   he object."""
        pass
