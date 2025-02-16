import pytest

from meshsee.camera import Camera
from meshsee.gl_ui import GlUi
from meshsee.renderer import RendererFactory


@pytest.fixture(scope="session")
def main_ui():
    ui = GlUi.instance()
    if ui is None:
        ui = GlUi(RendererFactory(Camera()))
    yield ui


def test_ui_instance(main_ui):
    assert main_ui is GlUi.instance()


def test_ui_instance_singleton():
    with pytest.raises(RuntimeError):
        GlUi(RendererFactory(Camera()))


# def test_main(mocker):
#     application = mocker.patch("meshsee.app.QApplication")
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
