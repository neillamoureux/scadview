import pytest

from meshsee.module_loader import ModuleLoader, yield_if_return


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
