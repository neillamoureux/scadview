from typing import Callable

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
    ):
        """Create an action.

        Args:
            label: Label to be displayed in controls created from this class
            callback: The function to call to execute the action
            accelerator: The accelerator key to press to execute the action.
                This is only set up if `menu_item` is called.

        """

        self._label = label
        self._callback = callback
        self._accelerator = accelerator
        self._id: int = wx.NewIdRef()

    def button(self, parent: wx.Window) -> wx.Button:
        btn = wx.Button(parent, label=self._label, id=self._id)
        btn.Bind(wx.EVT_BUTTON, self._callback)
        return btn

    def menu_item(self, menu: wx.Menu) -> wx.MenuItem:
        label = self._menu_item_label()
        item = menu.Append(self._id, label)
        menu.Bind(wx.EVT_MENU, self._callback, item)
        return item

    def _menu_item_label(self):
        return (
            f"{self._label}\tCtrl+{self._accelerator}"
            if self._accelerator
            else self._label
        )


class CheckableAction(Action):
    """Create an action that changes a binary state, and can be represented by a "checked" control like a checkbox"""

    def __init__(
        self,
        label: str,
        callback: Callable[[wx.Event], None],
        initial_state: bool,
        on_state_change: Observable,
        accelerator: str | None = None,
    ):
        """Constructor

        Args:
            label: Label to be displayed in controls created from this class
            callback: The function to call to execute the action
            initial_state: True to show as checked, False as not checked.
            on_state_change: Sets up feedback from the application to update the state of the controel (checked or not).
               An Observable must be created in the app that is triggered when the state changes,
               and passed in as this arg.
            accelerator: The accelerator key to press to execute the action.
                This is only set up if `menu_item` is called.
        """
        super().__init__(label, callback, accelerator)
        on_state_change.subscribe(self._on_state_change)
        self._initial_state = initial_state
        self._menu_items: list[wx.MenuItem] = []
        self._checkboxes: list[wx.CheckBox] = []

    def menu_item(self, menu: wx.Menu):
        label = self._menu_item_label()
        item = menu.AppendCheckItem(self._id, label)
        item.Check(self._initial_state)
        menu.Bind(wx.EVT_MENU, self._update_state, item)
        self._menu_items.append(item)
        return item

    def checkbox(self, parent: wx.Window) -> wx.CheckBox:
        chk = wx.CheckBox(parent, label=self._label, id=self._id)
        chk.Bind(wx.EVT_CHECKBOX, self._update_state)
        chk.SetValue(self._initial_state)
        self._checkboxes.append(chk)
        return chk

    def _update_state(self, event: wx.Event):
        self._callback(event)

    def _on_state_change(self, state: bool):
        for item in self._menu_items:
            item.Check(state)
        for chk in self._checkboxes:
            chk.SetValue(state)


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
