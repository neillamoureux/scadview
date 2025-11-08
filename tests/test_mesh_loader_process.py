from unittest.mock import patch

import numpy.testing as npt
import pytest
from trimesh.creation import box, icosphere

from meshsee.mesh_loader_process import (
    LoadResult,
    LoadStatus,
    LoadWorker,
    MpLoadQueue,
    MpQueue,
)


@pytest.fixture
def mock_queue():
    with patch("meshsee.mesh_loader_process.Queue") as mock_cls:
        yield mock_cls


@pytest.fixture
def mp_queue_int():
    yield MpQueue[int](maxsize=10, type_=int)


def test_mp_queue_init(mock_queue):
    MpQueue[int](maxsize=10, type_=int)
    mock_queue.assert_called_once_with(maxsize=10)


def test_mp_queue_put_correct_type(mock_queue, mp_queue_int):
    mp_queue_int.put(42)
    mock_queue.return_value.put.assert_called_with(42, block=True, timeout=None)


def test_mp_queue_put_wrong_type(mp_queue_int):
    with pytest.raises(ValueError):
        mp_queue_int.put(10.3)


def test_mp_queue_put_nowait(mock_queue, mp_queue_int):
    mp_queue_int.put_nowait(55)
    mock_queue.return_value.put.assert_called_once_with(55, block=False, timeout=None)


def test_mp_queue_put_nowait_wrong_type(mp_queue_int):
    with pytest.raises(ValueError):
        mp_queue_int = MpQueue[int](maxsize=10, type_=int)
        mp_queue_int.put_nowait(10.3)


def test_mp_queue_get_correct_type(mock_queue, mp_queue_int):
    q = mock_queue.return_value
    q.get.return_value = 43
    assert mp_queue_int.get() == 43


def test_mp_queue_get_wrong_type(mock_queue, mp_queue_int):
    q = mock_queue.return_value
    q.get.return_value = 43.3
    with pytest.raises(ValueError):
        mp_queue_int.get()


def test_mp_queue_get_nowait(mock_queue, mp_queue_int):
    q = mock_queue.return_value
    q.get.return_value = 43
    mp_queue_int.get_nowait()
    q.get.assert_called_once_with(block=False, timeout=None)


def test_mp_queue_get_nowait_wrong_type(mock_queue, mp_queue_int):
    q = mock_queue.return_value
    q.get.return_value = 43.3
    with pytest.raises(ValueError):
        mp_queue_int.get_nowait()


def test_mp_queue_close(mock_queue, mp_queue_int):
    mp_queue_int.close()
    mock_queue.return_value.close.assert_called_once_with()


def test_load_result_debug():
    mesh = box()
    lr = LoadResult(1, 2, [mesh], None)
    assert lr.debug
    lr = LoadResult(1, 2, mesh, None)
    assert not lr.debug


def test_load_result_status():
    mesh = box()
    lr = LoadResult(1, 2, mesh, Exception())
    assert lr.status == LoadStatus.ERROR
    lr = LoadResult(1, 2, [mesh], None)
    assert lr.status == LoadStatus.DEBUG
    lr = LoadResult(1, 2, [mesh], None, True)
    assert lr.status == LoadStatus.DEBUG
    lr = LoadResult(1, 2, mesh, None, True)
    assert lr.status == LoadStatus.COMPLETE
    lr = LoadResult(1, 2, mesh, None)
    assert lr.status == LoadStatus.START
    lr = LoadResult(1, 2, None, None)
    assert lr.status == LoadStatus.NONE


@pytest.fixture
def mesh(request):
    m = getattr(request, "param", box())
    return m


@pytest.fixture
def load_queue():
    yield MpLoadQueue(maxsize=10, type_=LoadResult)


@pytest.fixture
def load_worker(mesh, load_queue):
    with patch("meshsee.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value
        if isinstance(mesh, list):
            ml_instance.run_function.return_value = iter(mesh)
        else:
            ml_instance.run_function.return_value = iter([mesh])
        worker = LoadWorker("test/path", load_queue)
        yield worker


@pytest.fixture
def started_load_worker(load_worker):
    load_worker.start()
    yield load_worker
    load_worker.cancel()
    load_worker.join(timeout=1.0)
    assert not load_worker.is_alive()


def test_load_worker_init(load_worker):
    assert load_worker.load_number == 0


def test_load_worker_put_in_queue(mesh, load_queue, started_load_worker):
    result = load_queue.get(timeout=1.0)
    assert result.load_number == 1
    assert result.sequence_number == 1
    npt.assert_array_equal(result.mesh.vertices, mesh.vertices)
    npt.assert_array_equal(result.mesh.faces, mesh.faces)
    assert not result.error
    assert not result.complete  # Even though no more meshes, not set complete

    # On get after last mesh, returns the last mesh with same load result and seq
    # with complete is True

    result = load_queue.get(timeout=1.0)
    assert result.load_number == 1
    assert result.sequence_number == 1
    npt.assert_array_equal(result.mesh.vertices, mesh.vertices)
    npt.assert_array_equal(result.mesh.faces, mesh.faces)
    assert not result.error
    assert result.complete


@pytest.mark.parametrize(
    "mesh", [[box(), icosphere()]], indirect=True, ids=["box and sphere"]
)
def test_load_worker_put_in_queue_multi_mesh(mesh, load_queue, started_load_worker):
    result = load_queue.get(timeout=1.0)
    assert result.load_number == 1
    assert result.sequence_number == 1
    npt.assert_array_equal(result.mesh.vertices, mesh[0].vertices)
    npt.assert_array_equal(result.mesh.faces, mesh[0].faces)
    assert not result.error
    assert not result.complete

    result = load_queue.get(timeout=1.0)
    assert result.load_number == 1
    assert result.sequence_number == 2
    npt.assert_array_equal(result.mesh.vertices, mesh[1].vertices)
    npt.assert_array_equal(result.mesh.faces, mesh[1].faces)
    assert not result.error
    assert not result.complete  # Even though no more meshes, not set complete

    # On get after last mesh, returns the last mesh with same load result and seq
    # with complete is True

    result = load_queue.get(timeout=1.0)
    assert result.load_number == 1
    assert result.sequence_number == 2
    npt.assert_array_equal(result.mesh.vertices, mesh[1].vertices)
    npt.assert_array_equal(result.mesh.faces, mesh[1].faces)
    assert not result.error
    assert result.complete
