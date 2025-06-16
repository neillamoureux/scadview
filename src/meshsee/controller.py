import logging
from time import time
from typing import Generator

from trimesh import Trimesh
from trimesh.exchange import export

from meshsee.module_loader import ModuleLoader

logger = logging.getLogger(__name__)


def export_formats() -> list[str]:
    return list(export._mesh_exporters.keys())


class Controller:
    CREATE_MESH_FUNCTION_NAME = "create_mesh"

    def __init__(self):
        self._module_loader = ModuleLoader(self.CREATE_MESH_FUNCTION_NAME)
        self.current_mesh = None
        self._last_module_path = None

    @property
    def current_mesh(self) -> Trimesh | None:
        return self._current_mesh

    @current_mesh.setter
    def current_mesh(self, mesh: Trimesh | None):
        self._current_mesh = mesh

    def load_mesh(
        self, module_path: str | None = None
    ) -> Generator[Trimesh, None, None]:
        self.current_mesh = None
        if module_path is None:
            module_path = self._last_module_path
        if module_path is None:
            raise ValueError("No module path selected for load")
        self._last_module_path = module_path
        logger.info(f"Starting load of {module_path}")
        t0 = time()
        try:
            for i, mesh in enumerate(self._module_loader.run_function(module_path)):
                self.current_mesh = mesh
                logger.info(f"Loading mesh #{i + 1}")
                yield mesh
            t1 = time()
            logger.info(f"Load {module_path} took {(t1 - t0) * 1000:.1f}ms")
        except Exception as e:
            logger.exception(f"Error while loading {module_path}: {e}")
            raise e

    def export(self, file_path: str):
        if not self.current_mesh:
            logger.info("No mesh to export")
            return
        if isinstance(self.current_mesh, list):
            export_mesh = self.current_mesh[-1]
        else:
            export_mesh = self.current_mesh
        export_mesh.export(file_path)
