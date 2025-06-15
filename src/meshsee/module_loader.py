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
        try:
            # Reload or import the module
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            module_path = os.path.dirname(file_path)
            if module_path not in sys.path:
                sys.path.append(module_path)
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
                logger.error(f"Error while executing function: {e}")
        except Exception as e:
            logger.error(f"Error while loading function: {e}")
            raise e
