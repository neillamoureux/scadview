from enum import Enum, auto
from typing import Any

import moderngl
from moderngl import Program

from meshsee.observable import Observable


class ProgramValues(Enum):
    MODEL_MATRIX = auto()
    CAMERA_MATRIX = auto()
    PROJECTION_MATRIX = auto()
    SCALE_MATRIX = auto()
    MESH_COLOR = auto()
    SHOW_GRID = auto()


class ProgramUpdater:
    def __init__(
        self,
        program: Program,
        register: dict[ProgramValues, str],
    ):
        self.program = program
        self.register = register
        # self.on_change = Observable()

        # for item in register.items():
        #     self.on_change.subscribe(item, self.update_program)

    def update_program_vars(
        self, vars: list[ProgramValues], values: dict[ProgramValues, Any]
    ):
        for var in vars:
            if var in self.register:
                self.update_program_var(var, values[var])

    def update_program_var(self, var: ProgramValues, value: Any):
        if var not in self.register:
            return
        var_name = self.register[var]
        uniform = self.program[var_name]
        if uniform.gl_type == 0x8B56:
            uniform.value = value
        else:
            uniform.write(value)

    def subscribe_to_updates(self, updates: Observable):
        updates.subscribe(self.update_program_var)
