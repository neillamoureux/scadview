import tkinter as tk
from pathlib import Path
from time import sleep

import wx


from meshsee.controller import Controller
from meshsee.render.gl_widget_adapter import GlWidgetAdapter
from meshsee.ui.wx.main_frame import MainFrame
from meshsee.ui.splash import start_splash_process


class GlUi:
    def __init__(self, controller: Controller, gl_widget_adapter: GlWidgetAdapter):
        _, pipe_conn = start_splash_process()
        print("splash shown")
        self.app = wx.App(False)
        print("wx app created")
        print("splash closing")
        pipe_conn.send("CLOSE")
        print("splash closed")

        self.frame = MainFrame(controller, gl_widget_adapter)

    def run(self):
        self.frame.Show()
        self.frame.Raise()
        self.app.MainLoop()
