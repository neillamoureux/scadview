import wx

from meshsee.controller import Controller
from meshsee.render.gl_widget_adapter import GlWidgetAdapter
from meshsee.ui.wx.main_frame import MainFrame


class GlUi:
    def __init__(self, controller: Controller, gl_widget_adapter: GlWidgetAdapter):
        self.app = wx.App(False)
        self.frame = MainFrame()

    def run(self):
        self.frame.Show()
        self.app.MainLoop()


if __name__ == "__main__":
    app = wx.App(False)
    MainFrame().Show()
    app.MainLoop()
