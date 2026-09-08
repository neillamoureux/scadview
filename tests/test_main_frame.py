from types import SimpleNamespace
from unittest.mock import Mock

import pytest

pytest.importorskip("wx")

from scadview.module_loader import CreateMeshParameter
from scadview.ui.wx import main_frame
from scadview.ui.wx.main_frame import MainFrame, convert_parameter_value


class FakeSizer:
    def __init__(self, *_args):
        self.items: list[object] = []

    def Add(self, item, *_args):
        self.items.append(item)


class FakeStaticText:
    def __init__(self, parent, *, label: str):
        self.parent = parent
        self.label = label


class FakeTextCtrl:
    def __init__(self, parent, *, value: str, style: int):
        self.parent = parent
        self.value = value
        self.style = style

    def Bind(self, *_args):
        return None


class FakeParameterBox:
    def __init__(self):
        self.visible: list[bool] = []

    def ShowItems(self, value: bool):
        self.visible.append(value)


def test_parameter_control_uses_parameter_name_and_current_value(monkeypatch):
    parameter = CreateMeshParameter("width", "float", 2.5)
    input_control = object()
    parameter_parent = object()
    monkeypatch.setattr(main_frame.wx, "BoxSizer", FakeSizer)
    monkeypatch.setattr(main_frame.wx, "StaticText", FakeStaticText)
    frame = SimpleNamespace(
        _button_panel=object(),
        _parameter_box=SimpleNamespace(
            GetStaticBox=lambda: parameter_parent,
        ),
        _controller=SimpleNamespace(parameter_values={"width": 3.5}),
        _create_parameter_input=lambda item, value: (
            input_control if (item, value) == (parameter, 3.5) else None
        ),
    )

    row = MainFrame._create_parameter_control(frame, parameter)

    assert row.items[0].label == "width:"
    assert row.items[0].parent is parameter_parent
    assert row.items[1] is input_control


def test_parameter_text_control_uses_parameters_static_box_parent(monkeypatch):
    parameter = CreateMeshParameter("width", "float", 2.5)
    parameter_parent = object()
    monkeypatch.setattr(main_frame.wx, "TextCtrl", FakeTextCtrl)
    frame = SimpleNamespace(
        _parameter_box=SimpleNamespace(
            GetStaticBox=lambda: parameter_parent,
        ),
    )

    control = MainFrame._create_parameter_input(frame, parameter, 2.5)

    assert control.parent is parameter_parent


@pytest.mark.parametrize(
    ("parameter", "value", "expected"),
    [
        (CreateMeshParameter("count", "int", 1), "2", 2),
        (CreateMeshParameter("width", "float", 2.5), "3.75", 3.75),
        (CreateMeshParameter("name", "str", "cube"), "base", "base"),
    ],
)
def test_convert_parameter_value_converts_text(parameter, value, expected):
    assert convert_parameter_value(parameter, value) == expected


def test_convert_parameter_value_requires_bool_value_for_boolean_parameter():
    parameter = CreateMeshParameter("enabled", "bool", True)

    assert convert_parameter_value(parameter, False) is False
    with pytest.raises(ValueError, match="boolean"):
        convert_parameter_value(parameter, "false")


def test_parameter_text_commit_retains_invalid_input_without_reloading(caplog):
    parameter = CreateMeshParameter("width", "float", 2.5)
    controller = Mock(parameters=[parameter])
    timer = Mock()
    gauge = Mock()
    control = Mock()
    control.GetValue.return_value = "not-a-number"
    event = Mock()
    event.GetEventObject.return_value = control
    frame = SimpleNamespace(
        _controller=controller,
        _loader_timer=timer,
        _load_progress_gauge=gauge,
        _set_parameter_value=lambda *_args: pytest.fail("invalid input was routed"),
    )

    with caplog.at_level("ERROR"):
        MainFrame._on_parameter_text_commit(frame, event, "width")

    controller.set_parameter_value.assert_not_called()
    timer.Start.assert_not_called()
    gauge.Pulse.assert_not_called()
    assert control.GetValue.called
    assert "Invalid value for parameter 'width'" in caplog.text


def test_parameter_text_commit_skips_event_before_control_replacement():
    parameter = CreateMeshParameter("width", "float", 2.5)
    order: list[str] = []
    controller = Mock(parameters=[parameter])
    controller.set_parameter_value.side_effect = lambda *_args: order.append(
        "replace-controls"
    )
    control = Mock()
    control.GetValue.return_value = "3.75"
    event = Mock()
    event.GetEventObject.return_value = control
    event.Skip.side_effect = lambda: order.append("skip-event")
    timer = Mock()
    gauge = Mock()
    frame = SimpleNamespace(
        _controller=controller,
        _loader_timer=timer,
        _load_progress_gauge=gauge,
    )
    frame._set_parameter_value = lambda name, value: MainFrame._set_parameter_value(
        frame, name, value
    )

    MainFrame._on_parameter_text_commit(frame, event, "width")

    assert order == ["skip-event", "replace-controls"]


def test_parameter_focus_loss_to_reset_button_does_not_commit():
    parameter = CreateMeshParameter("width", "float", 2.5)
    controller = Mock(parameters=[parameter])
    reset_button = object()
    control = Mock()
    control.GetValue.return_value = "3.75"
    event = Mock()
    event.GetEventObject.return_value = control
    event.GetWindow.return_value = reset_button
    frame = SimpleNamespace(
        _controller=controller,
        _reset_parameters_button=reset_button,
    )

    MainFrame._on_parameter_focus_loss(frame, event, "width")

    controller.set_parameter_value.assert_not_called()
    event.Skip.assert_called_once_with()


def test_repeated_focus_commit_does_not_restart_completed_load_timer():
    parameter = CreateMeshParameter("width", "float", 2.5)
    values = {"width": 2.5}

    class FakeController:
        parameters = [parameter]

        @property
        def parameter_values(self):
            return values.copy()

        def set_parameter_value(self, name, value):
            values[name] = value

    controller = FakeController()
    timer = Mock()
    gauge = Mock()
    frame = SimpleNamespace(
        _controller=controller,
        _loader_timer=timer,
        _load_progress_gauge=gauge,
    )
    frame._set_parameter_value = lambda name, value: MainFrame._set_parameter_value(
        frame, name, value
    )

    for _ in range(2):
        control = Mock()
        control.GetValue.return_value = "3.75"
        event = Mock()
        event.GetEventObject.return_value = control
        MainFrame._on_parameter_text_commit(frame, event, "width")

    timer.Start.assert_called_once_with(10)
    gauge.Pulse.assert_called_once()


def test_boolean_parameter_toggle_routes_actual_bool_and_starts_reload():
    controller = Mock()
    timer = Mock()
    gauge = Mock()
    event = Mock()
    event.IsChecked.return_value = True
    frame = SimpleNamespace(
        _controller=controller,
        _loader_timer=timer,
        _load_progress_gauge=gauge,
    )
    frame._set_parameter_value = lambda name, value: MainFrame._set_parameter_value(
        frame, name, value
    )

    MainFrame._on_parameter_toggle(frame, event, "enabled")

    controller.set_parameter_value.assert_called_once_with("enabled", True)
    timer.Start.assert_called_once()
    gauge.Pulse.assert_called_once()


def test_debug_toggle_does_not_poll_when_no_reload_is_queued():
    controller = Mock()
    controller.set_debug_features.return_value = False
    timer = Mock()
    gauge = Mock()
    event = Mock()
    event.IsChecked.return_value = True
    frame = SimpleNamespace(
        _controller=controller,
        _loader_timer=timer,
        _load_progress_gauge=gauge,
    )

    MainFrame._on_debug_features_toggle(frame, event)

    controller.set_debug_features.assert_called_once_with(True)
    timer.Start.assert_not_called()
    gauge.Pulse.assert_not_called()


def test_reset_parameters_routes_reload_and_starts_polling():
    controller = Mock()
    controller.reset_parameter_values.return_value = True
    timer = Mock()
    gauge = Mock()
    frame = SimpleNamespace(
        _controller=controller,
        _loader_timer=timer,
        _load_progress_gauge=gauge,
    )

    MainFrame._on_reset_parameters(frame, Mock())

    controller.reset_parameter_values.assert_called_once_with()
    timer.Start.assert_called_once_with(main_frame.LOAD_CHECK_INTERVAL_MS)
    gauge.Pulse.assert_called_once()


def test_reset_parameters_does_not_poll_when_controller_is_already_at_defaults():
    controller = Mock()
    controller.reset_parameter_values.return_value = False
    timer = Mock()
    gauge = Mock()
    frame = SimpleNamespace(
        _controller=controller,
        _loader_timer=timer,
        _load_progress_gauge=gauge,
    )

    MainFrame._on_reset_parameters(frame, Mock())

    controller.reset_parameter_values.assert_called_once_with()
    timer.Start.assert_not_called()
    gauge.Pulse.assert_not_called()


def test_parameter_controls_replace_when_error_result_publishes_new_metadata():
    parameter_sizer = Mock()
    parameter_box = FakeParameterBox()
    button_panel = Mock()
    sidebar = Mock()
    layout_calls: list[str] = []
    button_panel.Layout.side_effect = lambda: layout_calls.append("parent")
    sidebar.Layout.side_effect = lambda: layout_calls.append("sidebar")
    sidebar.FitInside.side_effect = lambda: layout_calls.append("fit")
    old_parameter = CreateMeshParameter("width", "float", 2.5)
    new_parameter = CreateMeshParameter("name", "str", "base")
    frame = SimpleNamespace(
        _parameter_sizer=parameter_sizer,
        _parameter_box=parameter_box,
        _button_panel=button_panel,
        _sidebar_scroll=sidebar,
        _layout_sidebar=lambda: MainFrame._layout_sidebar(frame),
        _create_parameter_control=lambda parameter: parameter,
    )

    MainFrame._update_parameter_controls(frame, [old_parameter])
    MainFrame._update_parameter_controls(frame, [new_parameter])

    assert parameter_sizer.Clear.call_count == 2
    assert parameter_sizer.Add.call_args.args[0] == new_parameter
    assert parameter_box.visible == [True, True]
    assert button_panel.Layout.call_count == 2
    assert sidebar.Layout.call_count == 2
    assert sidebar.FitInside.call_count == 2
    assert layout_calls == ["parent", "sidebar", "fit"] * 2


def test_stale_load_result_does_not_stop_current_timer_or_update_view():
    controller = SimpleNamespace(current_generation=2)
    timer = Mock()
    gauge = Mock()
    gl_widget = Mock()
    frame = SimpleNamespace(
        _controller=controller,
        _loader_timer=timer,
        _load_progress_gauge=gauge,
        _gl_widget=gl_widget,
        _loader_last_load_number=0,
        _loader_last_sequence_number=0,
    )
    from scadview.mesh_loader_process import LoadResult

    result = LoadResult(1, 1, None, None, complete=True, generation=1)

    MainFrame._handle_load_result(frame, result)

    timer.Stop.assert_not_called()
    gauge.SetValue.assert_not_called()
    gl_widget.load_mesh.assert_not_called()
