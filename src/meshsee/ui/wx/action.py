from typing import Any, Callable, TypeVar, Generic

import wx

from meshsee.observable import Observable


class Action:
    """The represents an action to be executed, and controls to trigger it.


    An Action represents a single action to be taken,
    execute by calling the `callback` argument in the constructor.
    Controls can be created from a class instance that execute the action.

    """

    def __init__(
        self,
        label: str,
        callback: Callable[[wx.Event], None],
        accelerator: str | None = None,
        checkable: bool = False,
    ):
        """Create an action.

        Args:
            label: Label to be displayed in controls created from this class
            callback: The function to call to execute the action
            accelerator: The accelerator key to press to execute the action.
                This is only set up if `menu_item` is called.
            checkable: If you are planning to include this Action
              in the CheckableAction class, you need to ensure this is set to True.

        """

        self._label = label
        self._callback = callback
        self._accelerator = accelerator
        self._checkable = checkable
        self._id: int = wx.NewIdRef()

    def button(self, parent: wx.Window) -> wx.Button:
        btn = wx.Button(parent, label=self._label, id=self._id)
        btn.Bind(wx.EVT_BUTTON, self._callback)
        return btn

    def menu_item(self, menu: wx.Menu) -> wx.MenuItem:
        label = self._menu_item_label()
        if self._checkable:
            item = menu.AppendCheckItem(self._id, label)
        else:
            item = menu.Append(self._id, label)
        menu.Bind(wx.EVT_MENU, self._callback, item)
        return item

    def _menu_item_label(self):
        return (
            f"{self._label}\tCtrl+{self._accelerator}"
            if self._accelerator
            else self._label
        )


T = TypeVar("T")


class CheckableAction(Action, Generic[T]):
    """Adds checkboxes and checkable menu items, binding to an Observable for updates

    Args:
        action: The action to add checkability to
        initial_value: The initial value this represents.
        check_func: Callled on the represented value, must return True of False to set whether the control is checked.
            If the value is already True or False, set this as `check_func=lambda x: x`
        on_value_change: Sets up feedback from the application to update the state of the controel (checked or not).
            An Observable must be created in the app that is triggered when the state changes,
            and passed in as this arg.
    """

    def __init__(
        self,
        action: Action,
        initial_value: T,
        check_func: Callable[[T], bool],
        on_value_change: Observable,
    ):
        self._action = action
        self._initial_value = initial_value
        self._check_func = check_func
        self._on_value_change: Observable = on_value_change
        self._check_refs = (
            []
        )  # keep refs to _check functions so that they are not deleted by Observable

    def menu_item(self, menu: wx.Menu) -> wx.MenuItem:
        item = self._action.menu_item(menu)
        item.Check(self._check_func(self._initial_value))

        def _check(value: T):
            item.Check(self._check_func(value))
            return True

        self._on_value_change.subscribe(_check)
        self._check_refs.append(_check)
        return item

    def checkbox(self, parent: wx.Window) -> wx.CheckBox:
        chk = wx.CheckBox(parent, label=self._action._label, id=self._action._id)
        chk.Bind(wx.EVT_CHECKBOX, self._action._callback)
        chk.SetValue(self._check_func(self._initial_value))

        def _check(value: T):
            chk.SetValue(self._check_func(value))
            return True

        self._on_value_change.subscribe(_check)
        self._check_refs.append(_check)
        return chk


class EnableableAction(Action, Generic[T]):
    def __init__(
        self,
        action: Action,
        initial_value: T,
        on_value_change: Observable,
        enable_func: Callable[[T], bool],
    ):
        """Adds the ability to enable/disable the controls associated with an Action

        Args:
            action: The action to which you are adding a value-backed enable/disable
            initial_value: The intial value upon which the control decides if it is enabled or not.
            on_value_change: Sets up feedback from the application to update the value behing the control.
                An Observable must be created in the app that ixs triggered when the state changes,
            enable_func: When notified by on_value_change when the new value, returns True or False to enable / disable
        """
        self._action = action
        self._initial_value = initial_value
        self._enable_func = enable_func
        self._on_value_change: Observable = on_value_change
        self._enable_refs = (
            []
        )  # keep refs to _check functions so that they are not deleted by Observable

    def button(self, parent: wx.Window) -> wx.Button:
        btn = self._action.button(parent)

        def _enable(value: T):
            btn.Enable() if self._enable_func(value) else btn.Disable()

        _enable(self._initial_value)
        self._on_value_change.subscribe(_enable)
        self._enable_refs.append(_enable)
        return btn

    def menu_item(self, menu: wx.Menu) -> wx.MenuItem:
        item = self._action.menu_item(menu)

        def _enable(value: T):
            item.Enable(self._enable_func(value))

        _enable(self._initial_value)
        self._on_value_change.subscribe(_enable)
        self._enable_refs.append(_enable)
        return item


class ChoiceAction:
    """Create an action that can choose one of many values."""

    def __init__(
        self,
        labels: list[str],
        values: list[str],
        callback: Callable[[wx.CommandEvent, str], None],
        initial_value: str,
        on_value_change: Observable,
    ):
        """Constructor

        Args:
            labels: A label for each choice.
            values: The value to be set associated with each label.
            callback: The function to call to execute the action.  It passes the value selected.
            initial_value: The initial value from the app.
            on_value_change: Sets up feedback from the application to update which item is shows as selected.
               An Observable must be created in the app that is triggered when the state changes,
               and passed in as this arg.
        """

        on_value_change.subscribe(self._on_value_change)
        self._labels = labels
        self._values = values
        self._callback = callback
        self._initial_value = initial_value
        self._id: int = wx.NewIdRef()
        self._radio_buttons: list[wx.RadioButton] = []
        self._menu_items: list[wx.MenuItem] = []

    def _on_value_change(self, value: str):
        for rb, v in zip(self._radio_buttons, self._values):
            rb.SetValue(v == value)
        for item, v in zip(self._menu_items, self._values):
            item.Check(v == value)

    def menu_items(self, menu: wx.Menu) -> list[wx.MenuItem]:
        for label, value in zip(self._labels, self._values):
            item = menu.AppendRadioItem(id=wx.ID_ANY, item=label)
            item.Check(self._initial_value == value)
            menu.Bind(wx.EVT_MENU, self._update_value_from_menu, item)
            self._menu_items.append(item)
        return self._menu_items

    def radio_buttons(self, parent: wx.Window) -> list[wx.RadioButton]:
        self._radio_buttons: list[wx.RadioButton] = []
        first = True
        for label, value in zip(self._labels, self._values):
            if first:
                rb = wx.RadioButton(parent, label=label, style=wx.RB_GROUP)
            else:
                rb = wx.RadioButton(parent, label=label)
            rb.SetValue(value == self._initial_value)
            rb.Bind(
                wx.EVT_RADIOBUTTON,
                self._update_value_from_radio_button,
            )
            self._radio_buttons.append(rb)
        return self._radio_buttons

    def _update_value_from_radio_button(self, e: wx.CommandEvent):
        for label, value in zip(self._labels, self._values):
            label_func = getattr(e.GetEventObject(), "GetLabel", None)
            if callable(label_func) and label == label_func():
                self._callback(e, value)

    def _update_value_from_menu(self, e: wx.CommandEvent):
        event_item_id = e.GetId()
        for item, value in zip(self._menu_items, self._values):
            item_id = item.GetId()
            if e.IsChecked() and event_item_id == item_id:
                self._callback(e, value)
