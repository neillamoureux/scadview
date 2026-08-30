from unittest.mock import patch

import manifold3d
import numpy.testing as npt
import pytest
from trimesh.creation import box, icosphere

from scadview.features import FeatureState, feature
from scadview.mesh_loader_process import (
    LoadMeshCommand,
    LoadResult,
    LoadStatus,
    LoadWorker,
    MpLoadQueue,
    MpQueue,
)


@pytest.fixture
def mock_queue():
    with patch("scadview.mesh_loader_process.Queue") as mock_cls:
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


def test_load_mesh_command_preserves_debug_features():
    command = LoadMeshCommand("test/path", debug_features=True)

    assert command.debug_features is True


@pytest.fixture
def mesh(request):
    m = getattr(request, "param", box())
    return m


@pytest.fixture
def load_queue():
    yield MpLoadQueue(maxsize=10, type_=LoadResult)


@pytest.fixture
def load_worker(mesh, load_queue):
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value
        if isinstance(mesh, list):
            ml_instance.run_function.return_value = iter(mesh)
        else:
            ml_instance.run_function.return_value = iter([mesh])
        worker = LoadWorker("test/path", load_queue)
        yield worker
        LoadWorker.load_number = 0  # reset


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


def test_load_worker_colors_mesh_list(load_queue):
    mesh_list = [box(), icosphere()]
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value
        ml_instance.run_function.return_value = iter([mesh_list])
        worker = LoadWorker("test/path", load_queue)
        LoadWorker.load_number = 0  # reset
        worker.start()
        worker.join(timeout=1.0)
        assert not worker.is_alive()
        worker.cancel()

    result = load_queue.get(timeout=1.0)
    assert isinstance(result.mesh, list)
    load_queue.get(timeout=1.0)  # Otherwise hangs on windows.
    for tm in result.mesh:
        assert "scadview" in tm.metadata
        assert tm.metadata["scadview"]["color"][3] == 0.5


def test_load_worker_debugs_feature_sources_for_every_yield(load_queue):
    first_source = box()
    second_source = icosphere()
    first_result = box()
    second_result = icosphere()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value

        def _run_function(_module_path):
            feature("support", first_source)
            yield first_result
            feature("support", second_source)
            yield second_result

        ml_instance.run_function.side_effect = _run_function
        worker = LoadWorker("test/path", load_queue, debug_features=True)
        LoadWorker.load_number = 0
        worker.load()

    first_load = load_queue.get(timeout=1.0)
    second_load = load_queue.get(timeout=1.0)
    final_load = load_queue.get(timeout=1.0)

    assert isinstance(first_load.mesh, list)
    assert isinstance(second_load.mesh, list)
    assert isinstance(final_load.mesh, list)
    npt.assert_array_equal(first_load.mesh[0].vertices, first_source.vertices)
    npt.assert_array_equal(second_load.mesh[0].vertices, first_source.vertices)
    npt.assert_array_equal(second_load.mesh[1].vertices, second_source.vertices)
    npt.assert_array_equal(final_load.mesh[0].vertices, first_source.vertices)
    npt.assert_array_equal(final_load.mesh[1].vertices, second_source.vertices)
    assert first_load.mesh[0].metadata["scadview"]["color"][3] == 0.5
    assert final_load.complete


def test_load_worker_debug_omits_disabled_feature_sources(load_queue):
    source = box()
    normal_mesh = icosphere()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value

        def _run_function(_module_path):
            feature("cutout", source)
            feature("guide", box())
            yield normal_mesh

        ml_instance.run_function.side_effect = _run_function
        worker = LoadWorker(
            "test/path",
            load_queue,
            feature_states={"cutout": False},
            debug_features=True,
        )
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)

    assert isinstance(result.mesh, list)
    assert len(result.mesh) == 1
    assert result.mesh[0].metadata["scadview"]["color"][3] == 0.5


def test_load_worker_debug_converts_manifold_feature_sources(load_queue):
    source = manifold3d.Manifold.cube()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value

        def _run_function(_module_path):
            feature("cutout", source)
            yield box()

        ml_instance.run_function.side_effect = _run_function
        worker = LoadWorker("test/path", load_queue, debug_features=True)
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)

    assert isinstance(result.mesh, list)
    assert len(result.mesh) == 1
    assert isinstance(result.mesh[0], type(box()))
    assert result.mesh[0].metadata["scadview"]["color"][3] == 0.5


def test_load_worker_debug_omits_unregistered_meshes_from_feature_entries(
    load_queue,
):
    base = box()
    unregistered = icosphere()
    source = box()
    normal_mesh = base.union(unregistered)
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value

        def _run_function(_module_path):
            feature("guide", source)
            yield normal_mesh

        ml_instance.run_function.side_effect = _run_function
        worker = LoadWorker("test/path", load_queue, debug_features=True)
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)

    assert isinstance(result.mesh, list)
    assert len(result.mesh) == 1
    npt.assert_array_equal(result.mesh[0].vertices, source.vertices)


def test_load_worker_debug_falls_back_to_normal_mesh_without_feature_sources(
    load_queue,
):
    normal_mesh = icosphere()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value
        ml_instance.run_function.return_value = iter([normal_mesh])
        worker = LoadWorker("test/path", load_queue, debug_features=True)
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)

    npt.assert_array_equal(result.mesh.vertices, normal_mesh.vertices)


def test_load_worker_preserves_normal_mesh_when_feature_debug_is_off(load_queue):
    source = box()
    normal_mesh = icosphere()
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value

        def _run_function(_module_path):
            feature("cutout", source)
            yield normal_mesh

        ml_instance.run_function.side_effect = _run_function
        worker = LoadWorker("test/path", load_queue, debug_features=False)
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)

    npt.assert_array_equal(result.mesh.vertices, normal_mesh.vertices)


def test_load_worker_tracks_feature_states_and_filters_disabled_features(load_queue):
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value

        def _run_function(_module_path):
            yield feature("cutout", box())

        ml_instance.run_function.side_effect = _run_function
        worker = LoadWorker(
            "test/path",
            load_queue,
            feature_states={"cutout": False},
        )
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)
    assert result.mesh is None
    assert result.features == [FeatureState("cutout", False)]
    result = load_queue.get(timeout=1.0)
    assert result.complete
    assert result.features == [FeatureState("cutout", False)]


def test_load_worker_errors_on_nan_vertices(load_queue):
    nan_mesh = box()
    nan_mesh.vertices[0] = [float("nan"), 0.0, 0.0]
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value
        ml_instance.run_function.return_value = iter([nan_mesh])
        worker = LoadWorker("test/path", load_queue)
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)
    assert result.error is not None
    assert isinstance(result.error, ValueError)
    assert result.status == LoadStatus.ERROR


def test_load_worker_errors_on_non_finite_manifold_vertices(load_queue):
    base_mesh = manifold3d.Manifold.cube().to_mesh()
    vertices = base_mesh.vert_properties.copy()
    vertices[0, 0] = float("inf")
    invalid_manifold = manifold3d.Manifold(
        manifold3d.Mesh(vertices.astype("f4"), base_mesh.tri_verts.copy())
    )
    with patch("scadview.mesh_loader_process.ModuleLoader") as mock_module_loader:
        ml_instance = mock_module_loader.return_value
        ml_instance.run_function.return_value = iter([invalid_manifold])
        worker = LoadWorker("test/path", load_queue)
        LoadWorker.load_number = 0
        worker.load()

    result = load_queue.get(timeout=1.0)
    assert result.error is not None
    assert isinstance(result.error, ValueError)
    assert result.status == LoadStatus.ERROR


@pytest.mark.skip  # Flakey
def test_load_worker_cancel(started_load_worker):
    assert started_load_worker.is_alive()
    started_load_worker.cancel()
    started_load_worker.join(timeout=1.0)
    assert not started_load_worker.is_alive()
