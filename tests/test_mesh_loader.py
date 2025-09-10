from unittest.mock import Mock

import pytest
from manifold3d import Manifold
from trimesh import Trimesh

from meshsee.mesh_loader import MeshLoader


@pytest.fixture
def mock_controller():
    class MockController:
        def load_mesh(self, file_path):
            yield "mock_mesh"

    return MockController()


@pytest.fixture
def load_start_callback():
    return Mock()


@pytest.fixture
def load_successful_callback():
    return Mock()


@pytest.fixture
def stopped_callback():
    return Mock()


@pytest.fixture
def error_callback():
    return Mock()


@pytest.fixture
def mesh_loader(
    mock_controller, load_start_callback, load_successful_callback, stopped_callback
):
    return MeshLoader(
        controller=mock_controller,
        file_path="test",
        load_start_callback=load_start_callback,
        mesh_update_callback=lambda: None,
        load_successful_callback=load_successful_callback,
        stopped_callback=stopped_callback,
        error_callback=lambda: None,
    )


def test_load_start_callback(mesh_loader, load_start_callback):
    mesh_loader.run()
    load_start_callback.assert_called_once()


def test_load_start_callback_no_file_path(mock_controller, load_start_callback):
    mesh_loader = MeshLoader(
        controller=mock_controller,
        file_path=None,
        load_start_callback=load_start_callback,
        mesh_update_callback=lambda: None,
        load_successful_callback=lambda: None,
        stopped_callback=lambda: None,
        error_callback=lambda: None,
    )
    mesh_loader.run()
    load_start_callback.assert_not_called()


def test_call_stop_before_run(mesh_loader, load_successful_callback, stopped_callback):
    mesh_loader.stop()
    mesh_loader.run()
    load_successful_callback.assert_not_called()
    stopped_callback.assert_called_once()


def test_stop_requested_during_run(
    mesh_loader, mock_controller, load_successful_callback, stopped_callback
):
    original_load_mesh = mock_controller.load_mesh

    def load_mesh_with_stop(file_path):
        for mesh in original_load_mesh(file_path):
            mesh_loader.stop()  # Request stop during loading
            yield mesh

    mock_controller.load_mesh = load_mesh_with_stop
    mesh_loader.run()
    load_successful_callback.assert_not_called()
    stopped_callback.assert_called_once()


def test_load_successfule_callback(mesh_loader, load_successful_callback):
    mesh_loader.run()
    load_successful_callback.assert_called_once()


def test_error_callback_called_on_error(mesh_loader, mock_controller, error_callback):
    def load_mesh_with_error(file_path):
        raise RuntimeError("Test error")

    mock_controller.load_mesh = Mock(side_effect=load_mesh_with_error)
    mesh_loader._error_callback = error_callback
    mesh_loader.run()
    error_callback.assert_called_once()


def test_put_mesh_in_queue(mesh_loader):
    mesh_loader.run()
    assert not mesh_loader.mesh_queue.empty()
    assert mesh_loader.mesh_queue.get() == "mock_mesh"


def test_no_mesh_in_queue_initially(mesh_loader):
    assert mesh_loader.mesh_queue.empty()


def test_multiple_meshes_in_queue(mock_controller, mesh_loader):
    mesh_1 = Trimesh()
    mesh_2 = Trimesh()
    mesh_3 = Trimesh()

    def load_mesh_multiple(file_path):
        yield mesh_1
        yield mesh_2
        yield mesh_3

    mock_controller.load_mesh = load_mesh_multiple
    mesh_loader.run()
    assert not mesh_loader.mesh_queue.empty()
    assert mesh_loader.mesh_queue.get() == mesh_3  # Only the last mesh should remain


def test_convert_manifold_to_trimesh(mock_controller, mesh_loader):
    def load_manifold(file_path):
        yield Manifold.cube([1, 1, 1], True)

    mock_controller.load_mesh = load_manifold
    mesh_loader.run()
    assert not mesh_loader.mesh_queue.empty()
    assert isinstance(mesh_loader.mesh_queue.get(), Trimesh)
