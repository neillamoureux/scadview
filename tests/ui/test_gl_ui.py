import pytest

from meshsee.controller import Controller
from meshsee.render.camera import Camera
from meshsee.render.gl_widget_adapter import GlWidgetAdapter
from meshsee.render.renderer import RendererFactory
from meshsee.ui.gl_ui import GlUi


@pytest.fixture(scope="session")
def main_ui():
    ui = GlUi.instance()
    if ui is None:
        renderer_factory = RendererFactory(Camera())
        gl_widget_adapter = GlWidgetAdapter(renderer_factory)
        controller = Controller()
        ui = GlUi(controller, gl_widget_adapter)
    yield ui


def test_ui_instance(main_ui):
    assert main_ui is GlUi.instance()


def test_ui_instance_singleton(main_ui):
    renderer_factory = RendererFactory(Camera())
    gl_widget_adapter = GlWidgetAdapter(renderer_factory)
    controller = Controller()
    with pytest.raises(RuntimeError):
        GlUi(controller, gl_widget_adapter)


# def test_main(mocker):
#     app = mocker.patch("meshsee.app.QApplication")
#     window = mocker.patch("meshsee.app.MainWindow")
#     app.main()
#     assert application.called
#     assert application().exec.called
#     assert window.called
#     assert window().show.called


def test_main_window_title(main_ui):
    assert main_ui._main_window.windowTitle() == GlUi.MAIN_WINDOW_TITLE


def test_main_window_size(main_ui):
    assert main_ui._main_window.size().width() == GlUi.MAIN_WINDOW_SIZE[0]
    assert main_ui._main_window.size().height() == GlUi.MAIN_WINDOW_SIZE[1]
