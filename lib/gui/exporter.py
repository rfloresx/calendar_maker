try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))


import wx

import PIL.Image

import lib.print.wall_cal as libwallcal
import lib.print.desk_cal as libdeskcal

from lib.gui.settings import Settings
from lib.filemanager import FilesManager
from lib.gui.util import MainFrame
from typing import List

class ExporterPanel(wx.Panel):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self._sizer: wx.BoxSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self._sizer)

        export_wall_button = wx.Button(self, label="Create Wall Callendar")
        export_wall_button.Bind(wx.EVT_BUTTON, self.on_export_wall_callendar)

        export_desk_button = wx.Button(self, label="Create Desk Callendar")
        export_desk_button.Bind(wx.EVT_BUTTON, self.on_export_desk_callendar)
        
        self._sizer.Add(export_wall_button, 1, wx.ALL, 10)
        self._sizer.Add(export_desk_button, 1, wx.ALL, 10)


    def get_main_frame(self) -> 'MainFrame':
        parent: wx.Window = self.GetParent()
        while parent is not None and not isinstance(parent, MainFrame):
            parent = parent.GetParent()
        return parent

    def on_export_wall_callendar(self, event: wx.Event):
        libwallcal.ImageDrawer.dpi = Settings.dpi
        main_frame = self.get_main_frame()
        if main_frame:
            cal = main_frame.get_wall_calendar()

            with wx.ProgressDialog("Creating Wall Calendar", "Please wait...", maximum=25, style=wx.PD_SMOOTH | wx.PD_AUTO_HIDE) as progress_dialog:
                imgs : List[PIL.Image.Image] = libwallcal.ImageDrawer.draw(cal)
                for i, img in enumerate(imgs):
                    progress_dialog.Update(i+1)
                    fout = FilesManager.instance().get_file_path(f"WallCal/Page_{i}.png")
                    img.save(str(fout))


    def on_export_desk_callendar(self, event: wx.Event):
        libdeskcal.ImageDrawer.dpi = Settings.dpi
        main_frame = self.get_main_frame()
        if main_frame:
            cal = main_frame.get_desk_calendar()

            with wx.ProgressDialog("Creating Wall Calendar", "Please wait...", maximum=13, style=wx.PD_SMOOTH | wx.PD_AUTO_HIDE) as progress_dialog:
                imgs : List[PIL.Image.Image] = libdeskcal.ImageDrawer.draw(cal)
                for i, img in enumerate(imgs):
                    progress_dialog.Update(i+1)
                    fout = FilesManager.instance().get_file_path(f"DeskCal/Page_{i}.png")
                    img.save(str(fout))

