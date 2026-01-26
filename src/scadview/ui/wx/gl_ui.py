import logging

import wx

from scadview.controller import Controller
from scadview.render.gl_widget_adapter import GlWidgetAdapter
from scadview.ui.wx.main_frame import MainFrame

logger = logging.getLogger(__name__)


class GlUi:
    def __init__(self, controller: Controller, gl_widget_adapter: GlWidgetAdapter):
        self.app = wx.App(False)
        self.frame = MainFrame(controller, gl_widget_adapter)

    def run(self):
        self.frame.Show()
        wx.CallAfter(self._bring_to_front)
        self.app.MainLoop()

    def _bring_to_front(self):
        self.frame.Raise()
        self.frame.SetFocus()
        self.frame.SetFocusFromKbd()
        self.frame.Restore()

        if wx.Platform == "__WXMAC__":
            self._bring_to_front_mac()

    def _bring_to_front_mac(self):
        try:
            from AppKit import NSApplication  # type: ignore[reportAttributeAccessIssue]

            app = NSApplication.sharedApplication()  # type: ignore[reportUnknownVariableType]
            app.activateIgnoringOtherApps_(True)
        except Exception:
            pass
