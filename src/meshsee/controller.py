from typing import Generator
from time import time

from trimesh.exchange import export
from trimesh import Trimesh

from meshsee.gl_widget_adapter import GlWidgetAdapter
from meshsee.module_loader import ModuleLoader


def export_formats() -> list[str]:
    return list(export._mesh_exporters.keys())


class Controller:
    CREATE_MESH_FUNCTION_NAME = "create_mesh"

    def __init__(self, gl_widget_adapter: GlWidgetAdapter):
        self._module_loader = ModuleLoader(self.CREATE_MESH_FUNCTION_NAME)
        self._gl_widget_adapter = gl_widget_adapter
        self.current_mesh = None

    @property
    def gl_widget_adapter(self):
        return self._gl_widget_adapter

    @property
    def current_mesh(self):
        return self._current_mesh

    @current_mesh.setter
    def current_mesh(self, mesh):
        self._current_mesh = mesh

    def load_mesh(
        self, module_path: str | None = None
    ) -> Generator[Trimesh, None, None]:
        t0 = time()
        for mesh in self._module_loader.run_function(module_path):
            self.current_mesh = mesh
            yield mesh
        t1 = time()
        print(f"Took {(t1 - t0) * 1000:.1f}ms")

    def export(self, file_path: str):
        if not self.current_mesh:
            print("No mesh to export")
            return
        if isinstance(self.current_mesh, list):
            export_mesh = self.current_mesh[-1]
        else:
            export_mesh = self.current_mesh
        export_mesh.export(file_path)
