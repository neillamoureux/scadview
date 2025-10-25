import logging
from enum import Enum, auto
from importlib.resources import as_file, files
from typing import Any

import moderngl
from moderngl import Uniform

import meshsee.resources.shaders
from meshsee.observable import Observable

logger = logging.getLogger(__name__)


class ShaderVar(Enum):
    MODEL_MATRIX = auto()
    VIEW_MATRIX = auto()
    PROJECTION_MATRIX = auto()
    MESH_COLOR = auto()
    SHOW_GRID = auto()
    SHOW_EDGES = auto()
    GNOMON_VIEW_MATRIX = auto()
    GNOMON_PROJECTION_MATRIX = auto()


class ShaderProgram:
    BOOLEAN = 0x8B56

    def __init__(
        self,
        ctx: moderngl.Context,
        vertex_shader_loc: str,
        fragment_shader_loc: str,
        register: dict[ShaderVar, str],
    ):
        self._ctx = ctx
        self._current_values: dict[ShaderVar, Any] = {}
        self.register = register
        vertex_shader_source = files(meshsee.resources.shaders).joinpath(
            vertex_shader_loc
        )
        fragment_shader_source = files(meshsee.resources.shaders).joinpath(
            fragment_shader_loc
        )
        with (
            as_file(vertex_shader_source) as vs_f,
            as_file(fragment_shader_source) as fs_f,
        ):
            try:
                self.program = self._ctx.program(
                    vertex_shader=vs_f.read_text(),
                    fragment_shader=fs_f.read_text(),
                )
            except Exception as e:
                logger.exception(f"Error creating shader program: {e}")

    def update_program_var(self, var: ShaderVar, value: Any):
        self._current_values[var] = value
        if var not in self.register:
            return
        var_name = self.register[var]
        uniform = self.program[var_name]
        if not isinstance(uniform, Uniform):
            raise TypeError(f"{var_name!r} is not a uniform")
        if uniform.gl_type == self.BOOLEAN:  # type: ignore[attr-defined]
            uniform.value = value
        else:
            uniform.write(value)

    def update_all_program_vars(self):
        for var, value in self._current_values.items():
            self.update_program_var(var, value)

    def subscribe_to_updates(self, updates: Observable):
        updates.subscribe(self.update_program_var)
