import importlib
import os
import sys


class ModuleLoader:
    def __init__(self, function_name: str):
        self._function_name = function_name
        self._file_path = None

    def run_function(self, file_path: str | None = None):
        if file_path is not None:
            self._file_path = file_path
        if not self._file_path:
            print("No file selected")
            raise ValueError("No file selected")
        try:
            # Reload or import the module
            module_name = os.path.splitext(os.path.basename(self._file_path))[0]
            module_path = os.path.dirname(self._file_path)
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
                    f"Function '{self._function_name}' not found in '{self._file_path}'"
                )

            func = getattr(module, self._function_name)

            try:
                return func()
            except Exception as e:
                print(f"Error while executing function: {e}")
        except Exception as e:
            print(f"Error while loading function: {e}")
