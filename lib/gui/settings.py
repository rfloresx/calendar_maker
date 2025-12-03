try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

import wx
import wx.adv

import datetime

import lib.gui.util as libutil

class Settings(object):
    __instance = None
    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance
    
    def __call__(self, *args, **kwds):
        return self
    
    def __init__(self):
        self._settings = {}
        self._settings["dpi"] = 300
        self._settings["year"] = datetime.datetime.now().year

    @property
    def dpi(self) -> int:
        return int(self._settings.get("dpi", 300))
    
    @dpi.setter
    def dpi(self, value: int):
        self._settings["dpi"] = int(value)

    def set_dpi(self, value: int):
        self.dpi = value
    
    @property
    def year(self) -> int:
        return self._settings.get("year", datetime.datetime.now().year)
        
    @year.setter
    def year(self, value: int):
        self._settings["year"] = int(value)

    def set_year(self, value: int):
        self.year = value

    def to_json(self):
        return self._settings
    
    def load(self, obj):
        self._settings = obj

Settings = Settings()

class BaseSetting(wx.BoxSizer):
    def __init__(self, parent, label: str, value: str, choices: list):
        super().__init__(wx.HORIZONTAL)
        self._label = wx.StaticText(parent, label=label)
        self._ctrl = wx.ComboBox(parent, value=str(value), choices=choices, style=wx.CB_READONLY)
        self._ctrl.Bind(wx.EVT_COMBOBOX, self.update)

        self.Add(self._label, 0, wx.ALL, 10)
        self.Add(self._ctrl, 0, wx.ALL, 10)

    def update(self, event: wx.Event):
        raise NotImplementedError("update method not implemented")

class DpiSettings(BaseSetting):
    DPIs = ["32", "64", "96", "150", "300", "600", "1200"]
    def __init__(self, parent):
        super().__init__(parent, label="DPI", value=str(Settings.dpi), choices=DpiSettings.DPIs)

    def update(self, event: wx.Event):
        value = self._ctrl.GetValue()
        Settings.set_dpi(int(value))

class YearSettings(BaseSetting):
    YEARs = [str(i) for i in range(2000, 2055)]
    def __init__(self, parent):
        super().__init__(parent, label="Year", value=str(Settings.year), choices=YearSettings.YEARs)

    def update(self, event: wx.Event):
        value = self._year_ctrl.GetValue()
        Settings.set_year(int(value))

class SettingsPanel(wx.Panel):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self._sizer: wx.BoxSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._sizer)

        dpi_line : wx.BoxSizer = wx.BoxSizer(wx.HORIZONTAL)
        dpi_label = wx.StaticText(self, label="DPI")
        self._dpi_ctrl = wx.ComboBox(self, value=str(Settings.dpi), choices=["32", "64", "96", "150", "300", "600", "1200"], style=wx.CB_READONLY)
        self._dpi_ctrl.Bind(wx.EVT_COMBOBOX, self.update_dpi)

        dpi_line.Add(dpi_label, 1, wx.ALL, 10)
        dpi_line.Add(self._dpi_ctrl, 1, wx.ALL, 10)

        
        year_line = wx.BoxSizer(wx.HORIZONTAL)
        year_label = wx.StaticText(self, label="Year")
        self._year_ctrl = wx.ComboBox(self, value=str(Settings.year), choices=[str(i) for i in range(2000, 2055)], style=wx.CB_READONLY)
        self._year_ctrl.Bind(wx.EVT_COMBOBOX, self.update_year)

        year_line.Add(year_label, 1, wx.EXPAND | wx.ALL, 10)
        year_line.Add(self._year_ctrl, 1, wx.EXPAND | wx.ALL, 10)
        
        self._sizer.Add(dpi_line, 0, wx.ALL, 10)
        self._sizer.Add(year_line, 0, wx.ALL, 10)

    def update_dpi(self, event: wx.CommandEvent):
        value = self._dpi_ctrl.GetValue()
        Settings.set_dpi(int(value))

    def update_year(self, event: wx.CommandEvent):
        value = self._year_ctrl.GetValue()
        Settings.set_year(int(value))
    
    def load(self, data:dict):
        Settings.load(data)
        self._year_ctrl.SetValue(str(Settings.year))
        self._dpi_ctrl.SetValue(str(Settings.dpi))

    def to_json(self):
        return Settings.to_json()

if __name__ == "__main__":
    print(Settings().dpi)
    print(Settings.year)
