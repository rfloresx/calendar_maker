"""Settings UI and application-wide configuration singleton.

Provides a simple Settings singleton used to store DPI and year values and
SettingsPanel, a wx.Panel for editing those settings inside the editor.
"""

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
    """Application-wide settings singleton.

    Use Settings to access or modify global configuration such as DPI and
    target year. The module exports a pre-instantiated `Settings` object
    at the bottom of the file for convenience.
    """
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
        """Return the configured DPI (dots per inch)."""
        return int(self._settings.get("dpi", 300))
    
    @dpi.setter
    def dpi(self, value: int):
        """Set the configured DPI value."""
        self._settings["dpi"] = int(value)

    def set_dpi(self, value: int):
        """Convenience setter for DPI used by UI callbacks."""
        self.dpi = value
    
    @property
    def year(self) -> int:
        """Return the configured calendar year."""
        return self._settings.get("year", datetime.datetime.now().year)
        
    @year.setter
    def year(self, value: int):
        """Set the configured calendar year."""
        self._settings["year"] = int(value)

    def set_year(self, value: int):
        """Convenience setter for year used by UI callbacks."""
        self.year = value

    def to_json(self):
        """Serialize settings to a plain dict for saving."""
        return self._settings
    
    def load(self, obj):
        """Load settings from a dict (usually read from JSON)."""
        self._settings = obj

Settings = Settings()

class BaseSetting(wx.BoxSizer):
    """Helper base class for single-line setting rows in the settings panel."""
    def __init__(self, parent, label: str, value: str, choices: list):
        super().__init__(wx.HORIZONTAL)
        self._label = wx.StaticText(parent, label=label)
        self._ctrl = wx.ComboBox(parent, value=str(value), choices=choices, style=wx.CB_READONLY)
        self._ctrl.Bind(wx.EVT_COMBOBOX, self.update)

        self.Add(self._label, 0, wx.ALL, 10)
        self.Add(self._ctrl, 0, wx.ALL, 10)

    def update(self, event: wx.Event):
        """Update callback invoked when the control value changes. Subclasses must implement."""
        raise NotImplementedError("update method not implemented")

class DpiSettings(BaseSetting):
    """Row widget allowing the user to select a DPI from common choices."""
    DPIs = ["32", "64", "96", "150", "300", "600", "1200"]
    def __init__(self, parent):
        super().__init__(parent, label="DPI", value=str(Settings.dpi), choices=DpiSettings.DPIs)

    def update(self, event: wx.Event):
        """Handle user selection and update the Settings singleton."""
        value = self._ctrl.GetValue()
        Settings.set_dpi(int(value))

class YearSettings(BaseSetting):
    """Row widget allowing the user to select the target calendar year."""
    YEARs = [str(i) for i in range(2000, 2055)]
    def __init__(self, parent):
        super().__init__(parent, label="Year", value=str(Settings.year), choices=YearSettings.YEARs)

    def update(self, event: wx.Event):
        """Handle user selection and update the Settings singleton."""
        value = self._year_ctrl.GetValue()
        Settings.set_year(int(value))

class SettingsPanel(wx.Panel):
    """Panel exposing controls to edit application settings.

    The panel exposes load() and to_json() methods used by the editor to
    synchronize UI state with stored project settings.
    """
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
        """UI handler to apply the selected DPI to Settings."""
        value = self._dpi_ctrl.GetValue()
        Settings.set_dpi(int(value))

    def update_year(self, event: wx.CommandEvent):
        """UI handler to apply the selected year to Settings."""
        value = self._year_ctrl.GetValue()
        Settings.set_year(int(value))
    
    def load(self, data:dict):
        """Load settings from a dict into the UI controls."""
        Settings.load(data)
        self._year_ctrl.SetValue(str(Settings.year))
        self._dpi_ctrl.SetValue(str(Settings.dpi))

    def to_json(self):
        """Return the current settings as a dict for serialization."""
        return Settings.to_json()

if __name__ == "__main__":
    print(Settings().dpi)
    print(Settings.year)
