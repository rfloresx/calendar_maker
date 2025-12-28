"""Settings UI and application-wide configuration singleton.

Provides a simple Settings singleton used to store year values and
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

    Use Settings to access or modify global configuration such as the
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
        self._settings["year"] = datetime.datetime.now().year
        # Default export settings structure
        self._settings["export"] = {
            "calendar_type": "wall",   # 'wall' or 'desk'
            "format": "png",          # 'png', 'html', 'pdf', etc.
            "exporter_name": "default",
            "options": {}               # per-exporter options map: name -> dict
        }

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
        self._settings = obj or {}
        # Ensure defaults exist
        if "year" not in self._settings:
            self._settings["year"] = datetime.datetime.now().year
        export = self._settings.get("export")
        if not isinstance(export, dict):
            export = {}
        export.setdefault("calendar_type", "wall")
        export.setdefault("format", "png")
        export.setdefault("exporter_name", "default")
        export.setdefault("options", {})
        self._settings["export"] = export

    # ---- Export settings helpers ----
    def get_export_selection(self) -> dict:
        """Return current export selection (calendar_type, format, exporter_name)."""
        exp = self._settings.get("export", {})
        return {
            "calendar_type": exp.get("calendar_type", "wall"),
            "format": exp.get("format", "png"),
            "exporter_name": exp.get("exporter_name", "default")
        }

    def set_export_selection(self, calendar_type: str, format: str, exporter_name: str):
        """Update current export selection values."""
        exp = self._settings.setdefault("export", {})
        exp["calendar_type"] = calendar_type
        exp["format"] = format
        exp["exporter_name"] = exporter_name

    def get_export_options(self, exporter_name: str) -> dict:
        """Return saved option values for the given exporter name."""
        exp = self._settings.get("export", {})
        options = exp.get("options", {})
        return dict(options.get(exporter_name, {}))

    def set_export_options(self, exporter_name: str, opts: dict):
        """Persist option values for the given exporter name."""
        exp = self._settings.setdefault("export", {})
        options = exp.setdefault("options", {})
        options[exporter_name] = dict(opts or {})

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

class YearSettings(BaseSetting):
    """Row widget allowing the user to select the target calendar year."""
    YEARs = [str(i) for i in range(2000, 2055)]
    def __init__(self, parent):
        super().__init__(parent, label="Year", value=str(Settings.year), choices=YearSettings.YEARs)

    def update(self, event: wx.Event):
        """Handle user selection and update the Settings singleton."""
        value = self._ctrl.GetValue()
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

    def load(self, data:dict):
        """Load settings from a dict into the UI controls."""
        Settings.load(data)
    
    def clear(self):
        """Clear all settings controls."""
        pass

    def to_json(self):
        """Return the current settings as a dict for serialization."""
        return Settings.to_json()

if __name__ == "__main__":
    print(Settings().dpi)
    print(Settings.year)
