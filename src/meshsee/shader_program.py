from enum import Enum, auto
from importlib.resources import as_file, files
from typing import Any

import moderngl

from meshsee.observable import Observable
import meshsee.shaders


class ShaderVar(Enum):
    MODEL_MATRIX = auto()
    VIEW_MATRIX = auto()
    PROJECTION_MATRIX = auto()
    MESH_COLOR = auto()
    SHOW_GRID = auto()


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
        self.register = register
        vertex_shader_source = files(meshsee.shaders).joinpath(vertex_shader_loc)
        fragment_shader_source = files(meshsee.shaders).joinpath(fragment_shader_loc)
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
                print(f"Error creating shader program: {e}")

    def update_program_var(self, var: ShaderVar, value: Any):
        if var not in self.register:
            return
        var_name = self.register[var]
        uniform = self.program[var_name]
        if uniform.gl_type == self.BOOLEAN:
            uniform.value = value
        else:
            uniform.write(value)

    def subscribe_to_updates(self, updates: Observable):
        updates.subscribe(self.update_program_var)
