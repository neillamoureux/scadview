import logging
import os
from time import time
from typing import Generator

from trimesh import Trimesh
from trimesh.exchange import export

from meshsee.module_loader import ModuleLoader

logger = logging.getLogger(__name__)


def export_formats() -> list[str]:
    return [fmt for fmt in export._mesh_exporters.keys()]


class Controller:
    CREATE_MESH_FUNCTION_NAME = "create_mesh"

    def __init__(self):
        self._module_loader = ModuleLoader(self.CREATE_MESH_FUNCTION_NAME)
        self._current_mesh: Trimesh | None = None
        self._last_module_path = None
        self._last_export_path = None

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
        if module_path != self._last_module_path:
            self._last_export_path = (
                None  # Reset last export path if loading a new module
            )
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
            export_mesh = (  # pyright: ignore[reportUnknownVariableType]
                self.current_mesh[-1]
            )
        else:
            export_mesh = self.current_mesh
        self._last_export_path = file_path
        export_mesh.export(file_path)  # pyright: ignore[reportUnknownVariableType]

    def default_export_path(self) -> str:
        if self._last_export_path is not None:
            return self._last_export_path
        if self._last_module_path is not None:
            return os.path.join(
                os.path.dirname(self._last_module_path),
                os.path.splitext(os.path.basename(self._last_module_path))[0],
            )
        raise ValueError("No module loaded")
