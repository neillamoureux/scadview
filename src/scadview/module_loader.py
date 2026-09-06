import importlib
import inspect
import logging
import os
import sys
from dataclasses import dataclass
from types import GeneratorType
from typing import Any, Generator, Literal

logger = logging.getLogger(__name__)

ScalarParameterType = Literal["bool", "int", "float", "str"]
ScalarParameterValue = bool | int | float | str


@dataclass(frozen=True)
class CreateMeshParameter:
    name: str
    type: ScalarParameterType
    default: ScalarParameterValue


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
    last_loaded_module_path: str = ""

    def __init__(self, function_name: str):
        self._function_name = function_name

    def get_parameters(self, file_path: str) -> list[CreateMeshParameter]:
        function = self._load_function(file_path)
        return self._discover_parameters(function)

    def run_function(
        self,
        file_path: str,
        parameter_values: dict[str, ScalarParameterValue] | None = None,
    ) -> Generator[Any, None, None]:
        function = self._load_function(file_path)
        values = parameter_values or {}
        try:
            yield from yield_if_return(function(**values))
        except Exception as error:
            logger.exception(
                "Error while running %s in %s: %s",
                self._function_name,
                file_path,
                error,
            )
            raise

    def _load_function(self, file_path: str) -> Any:
        # Reload or import the module
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        module_path = os.path.dirname(file_path)

        # Ensure the module path is at the front of sys.path
        # so that if a previously loaded module from a different location,
        # it doesn't interfere.
        # First, remove the last loaded module path if it exists
        if self.last_loaded_module_path and self.last_loaded_module_path in sys.path:
            sys.path.remove(self.last_loaded_module_path)

        self.last_loaded_module_path = module_path
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
        return getattr(module, self._function_name)

    def _discover_parameters(self, function: Any) -> list[CreateMeshParameter]:
        return [
            parameter
            for signature_parameter in inspect.signature(function).parameters.values()
            if (
                parameter := self._create_parameter_descriptor(signature_parameter)
            ) is not None
        ]

    def _create_parameter_descriptor(
        self, parameter: inspect.Parameter
    ) -> CreateMeshParameter | None:
        if parameter.kind not in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            return None
        if parameter.default is inspect.Parameter.empty:
            return None
        parameter_type = self._supported_parameter_type(parameter.default)
        if parameter_type is None:
            return None
        return CreateMeshParameter(parameter.name, parameter_type, parameter.default)

    def _supported_parameter_type(
        self, value: Any
    ) -> ScalarParameterType | None:
        value_type = type(value)
        if value_type is bool:
            return "bool"
        if value_type is int:
            return "int"
        if value_type is float:
            return "float"
        if value_type is str:
            return "str"
        return None
