import pytest

from meshsee import app
from meshsee.app import App


@pytest.fixture
def main_app():
    main = App()
    yield main
    main._app.shutdown()


def test_main(mocker):
    application = mocker.patch("meshsee.app.QApplication")
    window = mocker.patch("meshsee.app.MainWindow")
    app.main()
    assert application.called
    assert application().exec.called
    assert window.called
    assert window().show.called


def test_main_window_title(main_app):
    assert main_app._main_window.windowTitle() == App.MAIN_WINDOW_TITLE


def test_main_window_size(main_app):
    assert main_app._main_window.size().width() == App.MAIN_WINDOW_SIZE[0]
    assert main_app._main_window.size().height() == App.MAIN_WINDOW_SIZE[1]
