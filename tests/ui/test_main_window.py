from unittest.mock import patch, Mock

import pytest
from PySide6.QtCore import Qt
from trimesh.creation import box

from meshsee.ui.main_window import MainWindow


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
def mock_moderngl_widget(mock_gl_widget_adapter):
    with patch("meshsee.ui.moderngl_widget.ModernglWidget") as MockModernglWidget:
        yield MockModernglWidget(mock_gl_widget_adapter)


@pytest.fixture
def main_window(mock_controller, mock_moderngl_widget, monkeypatch, qtbot):
    window = MainWindow(
        "Test", (800, 600), mock_controller, mock_moderngl_widget, add_gl_widget=False
    )
    monkeypatch.setattr(
        "meshsee.ui.main_window.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: ("tests/data/test_mesh.py", "Python Files (*.py)"),
    )

    qtbot.addWidget(window)
    window.show()
    return window


@pytest.fixture
def controlller_failing_load():
    with patch("meshsee.ui.main_window.Controller") as MockController:
        mock_controller = MockController()
        mock_controller.load_mesh.side_effect = Exception("Load failed")
        yield mock_controller


@pytest.fixture
def main_window_failing_load(
    controlller_failing_load, mock_moderngl_widget, monkeypatch, qtbot
):
    window = MainWindow(
        "Test",
        (800, 600),
        controlller_failing_load,
        mock_moderngl_widget,
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
    assert main_window._toggle_camera_btn.isEnabled()
    assert main_window._toggle_grid_btn.isEnabled()
    assert main_window._toggle_gnomon_btn.isEnabled()


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
    qtbot.waitSignal(
        main_window._mesh_handler._mesh_loading_worker.signals.load_successful,
        timeout=100,
    )
    main_window._controller.load_mesh.assert_called_once_with("tests/data/test_mesh.py")
    assert main_window._reload_file_btn.isEnabled()
    assert main_window._reload_action.isEnabled()
    assert not main_window._export_btn.isEnabled()
    assert not main_window._export_action.isEnabled()
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
    qtbot.waitSignal(
        main_window_failing_load._mesh_handler._mesh_loading_worker.signals.error,
        timeout=00,
    )
    main_window_failing_load._controller.load_mesh.assert_called_once_with(
        "tests/data/test_mesh.py"
    )
    assert main_window_failing_load._reload_file_btn.isEnabled()
    assert main_window_failing_load._reload_action.isEnabled()
    assert not main_window_failing_load._export_btn.isEnabled()
    assert not main_window_failing_load._export_action.isEnabled()


def test_reload_button_calls_load_mesh(main_window, qtbot):
    load_file_btn = main_window._load_file_btn
    reload_file_btn = main_window._reload_file_btn

    # Mock load mesh on load button click to enable reload button
    with patch.object(main_window, "_load_mesh") as mock_load_mesh:
        qtbot.mouseClick(load_file_btn, Qt.MouseButton.LeftButton)
        mock_load_mesh.assert_called_once_with("tests/data/test_mesh.py")

    qtbot.mouseClick(load_file_btn, Qt.MouseButton.LeftButton)
    qtbot.waitSignal(
        main_window._mesh_handler._mesh_loading_worker.signals.load_successful,
        timeout=400,
    )
    assert reload_file_btn.isEnabled()
    assert main_window._reload_action.isEnabled()
    qtbot.waitUntil(
        lambda: main_window._export_action.isEnabled()
        and main_window._export_btn.isEnabled(),
        timeout=400,
    )

    # Now test reload button
    with patch.object(main_window, "_load_mesh") as mock_load_mesh:
        qtbot.mouseClick(reload_file_btn, Qt.MouseButton.LeftButton)
        mock_load_mesh.assert_called_once_with(None)

    qtbot.mouseClick(reload_file_btn, Qt.MouseButton.LeftButton)
    qtbot.waitSignal(
        main_window._mesh_handler._mesh_loading_worker.signals.load_successful,
        timeout=200,
    )
    assert main_window._controller.load_mesh.call_count == 2
    main_window._controller.load_mesh.assert_called_with(None)
    assert reload_file_btn.isEnabled()
    assert main_window._reload_action.isEnabled()
    assert not main_window._export_btn.isEnabled()
    assert not main_window._export_action.isEnabled()
    qtbot.waitUntil(
        lambda: main_window._export_action.isEnabled()
        and main_window._export_btn.isEnabled(),
        timeout=100,
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
