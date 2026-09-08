import pytest

from scadview.module_loader import CreateMeshParameter, ModuleLoader, yield_if_return


def test_yield_if_return():
    def func_yields():
        yield 1

    def func_returns():
        return 2

    assert list(yield_if_return(func_yields())) == [1]
    assert list(yield_if_return(func_returns())) == [2]


def func_that_yields():
    yield 1
    yield 2


def func_that_returns():
    return 3


def func_that_yields_then_returns():
    yield 4
    return 5


def func_that_returns_then_yields():
    return 6
    yield 7


def test_run_function_that_yields():
    loader = ModuleLoader("func_that_yields")
    assert list(loader.run_function(__file__)) == [1, 2]


def test_run_function_that_returns():
    loader = ModuleLoader("func_that_returns")
    assert list(loader.run_function(__file__)) == [3]


def test_run_function_that_yields_then_returns():
    loader = ModuleLoader("func_that_yields_then_returns")
    print(list(func_that_yields_then_returns()))
    # Only provides the yielded value
    assert list(loader.run_function(__file__)) == [4]


def test_run_function_that_returns_then_yields():
    loader = ModuleLoader("func_that_returns_then_yields")
    print(list(func_that_returns_then_yields()))
    # Empty list
    assert list(loader.run_function(__file__)) == []


def test_run_function_tmp_file(tmp_path):
    file_path = tmp_path / "tmp_module.py"
    file_path.write_text(
        """
def func_that_returns():
    return 4
"""
    )
    loader = ModuleLoader("func_that_returns")
    assert list(loader.run_function(file_path)) == [4]


def test_run_function_tmp_file_missing_func(tmp_path):
    file_path = tmp_path / "tmp_module2.py"
    file_path.write_text(
        """
def func_that_is_spelled_wrong():
    return 5
"""
    )
    loader = ModuleLoader("func_that_returns")
    with pytest.raises(AttributeError):
        list(loader.run_function(file_path))


def test_load_two_files_with_same_module_name(tmp_path):
    file_path1 = tmp_path / "module.py"
    file_path1.write_text(
        """
def func_that_returns():
    return 10
"""
    )
    file_path2 = tmp_path / "subdir" / "module.py"
    file_path2.parent.mkdir()
    file_path2.write_text(
        """
def func_that_returns():
    return 20
"""
    )
    loader = ModuleLoader("func_that_returns")
    assert list(loader.run_function(file_path1)) == [10]
    assert list(loader.run_function(file_path2)) == [20]


def test_discovers_supported_defaulted_parameters_in_signature_order(tmp_path):
    file_path = tmp_path / "parameterized.py"
    file_path.write_text(
        """
def create_mesh(enabled=True, count=2, width=2.5, label="part", *, detail=3):
    return enabled, count, width, label, detail
"""
    )

    loader = ModuleLoader("create_mesh")

    assert loader.get_parameters(file_path) == [
        CreateMeshParameter("enabled", "bool", True),
        CreateMeshParameter("count", "int", 2),
        CreateMeshParameter("width", "float", 2.5),
        CreateMeshParameter("label", "str", "part"),
        CreateMeshParameter("detail", "int", 3),
    ]


def test_ignores_unsupported_parameter_kinds_and_defaults(tmp_path):
    file_path = tmp_path / "unsupported.py"
    file_path.write_text(
        """
class IntSubclass(int):
    pass

def create_mesh(positional_only=1, /, *values, required, optional=None,
                items=[], custom=IntSubclass(2), **keywords):
    return 1
"""
    )

    loader = ModuleLoader("create_mesh")

    assert loader.get_parameters(file_path) == []


def test_run_function_passes_keyword_parameter_values(tmp_path):
    file_path = tmp_path / "keyword_values.py"
    file_path.write_text(
        """
def create_mesh(width=2.5, *, label="part"):
    return width, label
"""
    )

    loader = ModuleLoader("create_mesh")

    assert list(loader.run_function(file_path, {"width": 3.75, "label": "lid"})) == [
        (3.75, "lid")
    ]


def test_run_function_drops_removed_and_renamed_parameter_values(monkeypatch):
    def create_mesh(depth=1.25):
        return depth

    loader = ModuleLoader("create_mesh")
    monkeypatch.setattr(loader, "_load_function", lambda _: create_mesh)

    assert list(loader.run_function("unused.py", {"width": 3.75})) == [1.25]


def test_run_function_uses_defaults_for_changed_parameter_types(monkeypatch):
    def create_mesh(width="new", count=4):
        return width, count

    loader = ModuleLoader("create_mesh")
    monkeypatch.setattr(loader, "_load_function", lambda _: create_mesh)

    assert list(loader.run_function("unused.py", {"width": 3.75})) == [("new", 4)]


def test_run_function_preserves_values_for_matching_parameter_types(monkeypatch):
    def create_mesh(width=9.0):
        return width

    loader = ModuleLoader("create_mesh")
    monkeypatch.setattr(loader, "_load_function", lambda _: create_mesh)

    assert list(loader.run_function("unused.py", {"width": 3.75})) == [3.75]
