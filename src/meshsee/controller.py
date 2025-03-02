from trimesh import Trimesh

from meshsee.gl_widget_adapter import GlWidgetAdapter
from meshsee.module_loader import ModuleLoader


class Controller:
    CREATE_MESH_FUNCTION_NAME = "create_mesh"

    def __init__(self, gl_widget_adapter: GlWidgetAdapter):
        self._module_loader = ModuleLoader(self.CREATE_MESH_FUNCTION_NAME)
        self._gl_widget_adapter = gl_widget_adapter

    @property
    def gl_widget_adapter(self):
        return self._gl_widget_adapter

    def load_mesh(self, module_path: str | None = None) -> Trimesh:
        for mesh in self._module_loader.run_function(module_path):
            yield mesh
