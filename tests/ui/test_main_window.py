from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt

from meshsee.ui.main_window import MainWindow
from meshsee.ui.moderngl_widget import ModernglWidget
from trimesh.creation import box


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
def main_window(mock_controller, mock_moderngl_widget, qtbot):
    window = MainWindow(
        "Test", (800, 600), mock_controller, mock_moderngl_widget, add_gl_widget=False
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


def test_load_button_calls_load_mesh(main_window, qtbot, monkeypatch):
    load_file_btn = main_window._load_file_btn
    assert load_file_btn.isEnabled()
    assert main_window._load_action.isEnabled()

    monkeypatch.setattr(
        "meshsee.ui.main_window.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: ("tests/data/test_mesh.py", "Python Files (*.py)"),
    )
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
