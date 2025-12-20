import logging

import wx

from meshsee.controller import Controller
from meshsee.render.gl_widget_adapter import GlWidgetAdapter
from meshsee.ui.wx.main_frame import MainFrame

logger = logging.getLogger(__name__)


def bring_to_front_mac(frame: wx.Frame):
    # Activate the application at the OS level
    frame.Raise()
    frame.SetFocus()
    frame.SetFocusFromKbd()
    frame.Restore()
    frame.Centre()

    try:
        from AppKit import NSApplication  # type: ignore[reportAttributeAccessIssue]

        logger.warning("Bringing app to front on Mac")

        app = NSApplication.sharedApplication()  # type: ignore[reportUnknownVariableType]
        app.activateIgnoringOtherApps_(True)
    except Exception:
        logger.exception("Failed to bring app to front on Mac")
        # If PyObjC isn't available, fall back to wx-only behavior
        pass


class GlUi:
    def __init__(self, controller: Controller, gl_widget_adapter: GlWidgetAdapter):
        self.app = wx.App(False)
        self.frame = MainFrame(controller, gl_widget_adapter)

    def run(self):
        self.frame.Show()
        # self.frame.Raise()
        wx.CallAfter(self.frame.Raise)
        wx.CallAfter(self.frame.SetFocus)
        wx.CallAfter(self.frame.SetFocusFromKbd)
        wx.CallAfter(self.frame.Restore)
        wx.CallAfter(self.frame.Centre)
        wx.CallAfter(bring_to_front_mac, self.frame)

        # if wx.Platform == "__WXMAC__":
        #     wx.CallAfter(self.app.SetActive, True)
        self.app.MainLoop()
