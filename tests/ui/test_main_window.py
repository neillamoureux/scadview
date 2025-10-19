from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from trimesh.creation import box

from meshsee.ui.main_window import MainWindow
from meshsee.ui.moderngl_widget import ModernglWidget


@pytest.fixture
def mock_controller():
    with patch("meshsee.ui.main_window.Controller") as MockController:
        mock_controller = MockController()
        mock_controller.load_mesh.return_value = iter([box()])
        yield mock_controller


@pytest.fixture
def mock_gl_widget_adapter():
    with patch("meshsee.ui.moderngl_widget.GlWidgetAdapter") as MockGlWidgetAdapter:
        yield MockGlWidgetAdapter()


@pytest.fixture
def main_window(mock_controller, mock_gl_widget_adapter, monkeypatch, qtbot):
    moderngl_widget = ModernglWidget(mock_gl_widget_adapter)
    window = MainWindow(
        "Test", (800, 600), mock_controller, moderngl_widget, add_gl_widget=False
    )
    monkeypatch.setattr(
        "meshsee.ui.main_window.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: ("tests/data/test_mesh.py", "Python Files (*.py)"),
    )

    qtbot.addWidget(window)
    window.show()
    return window


@pytest.fixture(autouse=True)
def cleanup_workers(main_window):
    yield
    if getattr(main_window, "_mesh_handler", None):
        main_window._mesh_handler.stop()


@pytest.fixture
def controlller_failing_load():
    with patch("meshsee.ui.main_window.Controller") as MockController:
        mock_controller = MockController()
        mock_controller.load_mesh.side_effect = Exception("Load failed")
        yield mock_controller


@pytest.fixture
def main_window_failing_load(
    controlller_failing_load,
    mock_gl_widget_adapter,
    monkeypatch,
    qtbot,
):
    moderngl_widget = ModernglWidget(mock_gl_widget_adapter)

    window = MainWindow(
        "Test",
        (800, 600),
        controlller_failing_load,
        moderngl_widget,
        add_gl_widget=False,
    )
    monkeypatch.setattr(
        "meshsee.ui.main_window.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: ("tests/data/test_mesh.py", "Python Files (*.py)"),
    )
    qtbot.addWidget(window)
    window.show()
    return window


def test_initial_button_states(main_window):
    assert main_window._load_file_btn.isEnabled()
    assert not main_window._reload_file_btn.isEnabled()
    assert not main_window._export_btn.isEnabled()
    assert main_window._frame_btn.isEnabled()
    assert main_window._view_from_xyz_btn.isEnabled
    assert main_window._view_from_x_btn.isEnabled()
    assert main_window._view_from_y_btn.isEnabled()
    assert main_window._view_from_z_btn.isEnabled()
    assert main_window._toggle_grid_cb.isEnabled()
    assert main_window._toggle_gnomon_cb.isEnabled()
    assert main_window._toggle_edges_cb.isEnabled()


def test_initial_action_states(main_window):
    assert main_window._load_action.isEnabled()
    assert not main_window._reload_action.isEnabled()
    assert not main_window._export_action.isEnabled()
    assert main_window._frame_action.isEnabled()
    assert main_window._view_from_xyz_action.isEnabled
    assert main_window._view_from_x_action.isEnabled()
    assert main_window._view_from_y_action.isEnabled()
    assert main_window._view_from_z_action.isEnabled()
    assert main_window._toggle_camera_action.isEnabled()
    assert main_window._toggle_grid_action.isEnabled()
    assert main_window._toggle_gnomon_action.isEnabled()
    assert main_window._show_font_action.isEnabled()


def test_load_button_calls_load_mesh(main_window, qtbot):
    load_file_btn = main_window._load_file_btn
    assert load_file_btn.isEnabled()
    assert main_window._load_action.isEnabled()

    with patch.object(main_window, "_load_mesh") as mock_load_mesh:
        qtbot.mouseClick(load_file_btn, Qt.MouseButton.LeftButton)
        mock_load_mesh.assert_called_once_with("tests/data/test_mesh.py")

    qtbot.mouseClick(load_file_btn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: getattr(main_window._mesh_handler, "_mesh_loading_worker", None)
        is not None,
        timeout=200,
    )
    spy = QSignalSpy(
        main_window._mesh_handler._mesh_loading_worker.signals.load_successful
    )
    qtbot.waitUntil(lambda: spy.count() >= 1, timeout=2000)

    main_window._controller.load_mesh.assert_called_once_with("tests/data/test_mesh.py")
    assert main_window._reload_file_btn.isEnabled()
    assert main_window._reload_action.isEnabled()
    qtbot.waitUntil(
        lambda: main_window._export_action.isEnabled()
        and main_window._export_btn.isEnabled(),
        timeout=100,
    )


def test_load_button_no_file_no_call_load_mesh(main_window, qtbot, monkeypatch):
    load_file_btn = main_window._load_file_btn
    assert load_file_btn.isEnabled()
    assert main_window._load_action.isEnabled()

    monkeypatch.setattr(
        "meshsee.ui.main_window.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: ("", "Python Files (*.py)"),
    )

    with patch.object(main_window, "_load_mesh") as mock_load_mesh:
        qtbot.mouseClick(load_file_btn, Qt.MouseButton.LeftButton)
        mock_load_mesh.assert_not_called()

    assert not main_window._reload_file_btn.isEnabled()
    assert not main_window._reload_action.isEnabled()
    assert not main_window._export_btn.isEnabled()
    assert not main_window._export_action.isEnabled()


def test_export_disabled_if_load_error(main_window_failing_load, qtbot):
    load_file_btn = main_window_failing_load._load_file_btn
    qtbot.mouseClick(load_file_btn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: getattr(
            main_window_failing_load._mesh_handler, "_mesh_loading_worker", None
        )
        is not None,
        timeout=200,
    )
    qtbot.waitSignal(
        main_window_failing_load._mesh_handler._mesh_loading_worker.signals.error,
        timeout=200,
    )
    assert main_window_failing_load._reload_file_btn.isEnabled()
    assert main_window_failing_load._reload_action.isEnabled()
    assert not main_window_failing_load._export_btn.isEnabled()
    assert not main_window_failing_load._export_action.isEnabled()


def test_reload_button_calls_load_mesh(main_window, qtbot):
    load_file_btn = main_window._load_file_btn
    reload_file_btn = main_window._reload_file_btn

    # Enable reload by simulating an initial load (don’t run the real loader)
    with patch.object(main_window, "_load_mesh") as mock_load_mesh:
        qtbot.mouseClick(load_file_btn, Qt.MouseButton.LeftButton)
        mock_load_mesh.assert_called_once_with("tests/data/test_mesh.py")

    # Do a real load and wait for completion
    qtbot.mouseClick(load_file_btn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: getattr(main_window._mesh_handler, "_mesh_loading_worker", None)
        is not None,
        timeout=200,
    )
    spy = QSignalSpy(
        main_window._mesh_handler._mesh_loading_worker.signals.load_successful
    )
    qtbot.waitUntil(lambda: spy.count() >= 1, timeout=2000)

    assert main_window._reload_action.isEnabled()
    assert main_window._export_action.isEnabled()
    assert main_window._export_btn.isEnabled()

    # First reload: just verify _load_mesh is invoked with None
    with patch.object(main_window, "_load_mesh") as mock_load_mesh:
        qtbot.mouseClick(reload_file_btn, Qt.MouseButton.LeftButton)
        mock_load_mesh.assert_called_once_with(None)

    # Second reload: run it for real and wait for the signal again
    qtbot.mouseClick(reload_file_btn, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: getattr(main_window._mesh_handler, "_mesh_loading_worker", None)
        is not None,
        timeout=200,
    )
    spy = QSignalSpy(
        main_window._mesh_handler._mesh_loading_worker.signals.load_successful
    )

    qtbot.waitUntil(lambda: spy.count() >= 1, timeout=200)

    # State immediately after a reload may temporarily disable export until ready
    assert reload_file_btn.isEnabled()
    assert main_window._reload_action.isEnabled()

    # If export toggles off during reload, allow it time to re-enable
    qtbot.waitUntil(
        lambda: main_window._export_action.isEnabled()
        and main_window._export_btn.isEnabled(),
        timeout=200,
    )


@patch("meshsee.ui.main_window.FontDialog")
def test_open_font_dialog(mock_FontDialog, main_window, qtbot):
    font_dialog = mock_FontDialog.return_value = Mock()
    patch.object(main_window, "font_dialog", None)
    main_window._open_font_dialog()
    assert mock_FontDialog.called
    assert font_dialog.show.called
    assert font_dialog.raise_.called
    assert font_dialog.activateWindow.called


def test_export_button_calls_export(main_window, qtbot, monkeypatch):
    load_file_btn = main_window._load_file_btn
    export_btn = main_window._export_btn

    qtbot.mouseClick(load_file_btn, Qt.MouseButton.LeftButton)
    qtbot.waitSignal(
        main_window._mesh_handler._mesh_loading_worker.signals.load_successful,
        timeout=400,
    )
    qtbot.waitUntil(
        lambda: main_window._export_action.isEnabled(),
        timeout=100,
    )

    # Now test export button
    with patch.object(main_window, "export") as mock_export:
        qtbot.mouseClick(export_btn, Qt.MouseButton.LeftButton)
        mock_export.assert_called_once()

    monkeypatch.setattr(
        "meshsee.ui.main_window.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: ("tests/data/test_export.stl", "Stl Files (*.stl)"),
    )

    qtbot.mouseClick(export_btn, Qt.MouseButton.LeftButton)
    qtbot.wait(100)
    assert main_window._controller.export.called
