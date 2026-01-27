import importlib
import logging
import os
import sys
from types import GeneratorType
from typing import Any, Generator

logger = logging.getLogger(__name__)


def yield_if_return(result: Any) -> Generator[Any, None, None]:
    """
    # If the result is a generator (i.e. the function yielded values),
    # yield from it so you process each yielded value.
    """
    if isinstance(result, GeneratorType):
        yield from result
    else:
        # Otherwise, treat the result
        # as a single value.
        yield result


class ModuleLoader:
    def __init__(self, function_name: str):
        self._function_name = function_name

    def run_function(self, file_path: str) -> Generator[Any, None, None]:
        # Reload or import the module
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        module_path = os.path.dirname(file_path)

        # Ensure the module path is at the front of sys.path
        # so that if a previously loaded module from a different location,
        # it doesn't interfere.
        if module_path in sys.path:
            sys.path.remove(module_path)
        sys.path.insert(0, module_path)

        module = sys.modules.get(module_name)
        if module:
            importlib.reload(module)
        else:
            module = importlib.import_module(module_name)

        # Get the function from the module
        if not hasattr(module, self._function_name):
            raise AttributeError(
                f"Function '{self._function_name}' not found in '{file_path}'"
            )
        func = getattr(module, self._function_name)
        try:
            yield from yield_if_return(func())
        except Exception as e:
            logger.exception(
                f"Error while running {self._function_name} in {file_path}: {e}"
            )
            raise e
