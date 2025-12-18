"""Exporter panel UI helpers.

Contains ExporterPanel which exposes controls to select and configure
calendar exporters with dynamically generated option controls based on
the selected exporter's OPTIONS_SCHEMA.
"""

try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))


import wx
from pathlib import Path
from typing import List, Dict, Any, Optional

from lib.gui.settings import Settings
from lib.filemanager import FilesManager
from lib.gui.util import MainFrame

from lib.export import (
    ExporterRegistry,
    ExportFormat,
    CalendarType,
    ExportContext,
    BaseExporter
)


class ExporterPanel(wx.Panel):
    """Panel providing export actions for wall and desk calendars.

    The ExporterPanel allows selection of calendar type, format, and specific
    exporter variant. It dynamically generates UI controls based on the selected
    exporter's OPTIONS_SCHEMA.
    """
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        
        self._option_controls: Dict[str, wx.Control] = {}
        self._current_exporter_class: Optional[type] = None
        
        self._main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._main_sizer)
        
        # Year selection
        year_sizer = wx.BoxSizer(wx.HORIZONTAL)
        year_label = wx.StaticText(self, label="Year:")
        self._year_ctrl = wx.ComboBox(
            self,
            value=str(Settings.year),
            choices=[str(i) for i in range(2000, 2055)],
            style=wx.CB_READONLY
        )
        self._year_ctrl.Bind(wx.EVT_COMBOBOX, self.on_year_changed)
        year_sizer.Add(year_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        year_sizer.Add(self._year_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        
        # Calendar type selection
        type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        type_label = wx.StaticText(self, label="Calendar Type:")
        self._calendar_type_ctrl = wx.ComboBox(
            self, 
            value="wall",
            choices=["wall", "desk"],
            style=wx.CB_READONLY
        )
        self._calendar_type_ctrl.Bind(wx.EVT_COMBOBOX, self.on_calendar_type_changed)
        type_sizer.Add(type_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        type_sizer.Add(self._calendar_type_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        
        # Format selection
        format_sizer = wx.BoxSizer(wx.HORIZONTAL)
        format_label = wx.StaticText(self, label="Export Format:")
        self._format_ctrl = wx.ComboBox(
            self,
            value="png",
            choices=["png", "html", "pdf"],
            style=wx.CB_READONLY
        )
        self._format_ctrl.Bind(wx.EVT_COMBOBOX, self.on_format_changed)
        format_sizer.Add(format_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        format_sizer.Add(self._format_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        
        # Exporter variant selection
        exporter_sizer = wx.BoxSizer(wx.HORIZONTAL)
        exporter_label = wx.StaticText(self, label="Exporter:")
        self._exporter_ctrl = wx.ComboBox(
            self,
            value="default",
            choices=["default"],
            style=wx.CB_READONLY
        )
        self._exporter_ctrl.Bind(wx.EVT_COMBOBOX, self.on_exporter_changed)
        exporter_sizer.Add(exporter_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        exporter_sizer.Add(self._exporter_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        
        # Options panel (dynamically populated)
        self._options_panel = wx.Panel(self)
        self._options_sizer = wx.BoxSizer(wx.VERTICAL)
        self._options_panel.SetSizer(self._options_sizer)
        
        # Export button
        self._export_button = wx.Button(self, label="Export Calendar")
        self._export_button.Bind(wx.EVT_BUTTON, self.on_export)
        
        # Layout
        self._main_sizer.Add(year_sizer, 0, wx.ALL | wx.EXPAND, 10)
        self._main_sizer.Add(wx.StaticLine(self), 0, wx.ALL | wx.EXPAND, 5)
        self._main_sizer.Add(type_sizer, 0, wx.ALL | wx.EXPAND, 10)
        self._main_sizer.Add(format_sizer, 0, wx.ALL | wx.EXPAND, 10)
        self._main_sizer.Add(exporter_sizer, 0, wx.ALL | wx.EXPAND, 10)
        self._main_sizer.Add(wx.StaticLine(self), 0, wx.ALL | wx.EXPAND, 5)
        self._main_sizer.Add(self._options_panel, 1, wx.ALL | wx.EXPAND, 10)
        self._main_sizer.Add(self._export_button, 0, wx.ALL | wx.EXPAND, 10)
        
        # Initialize with current selection
        self.update_exporter_list()
        self.update_options_ui()

    def get_main_frame(self) -> 'MainFrame':
        """Locate and return the parent MainFrame instance or None."""
        parent: wx.Window = self.GetParent()
        while parent is not None and not isinstance(parent, MainFrame):
            parent = parent.GetParent()
        return parent
    
    def get_selected_calendar_type(self) -> CalendarType:
        """Get the currently selected calendar type."""
        value = self._calendar_type_ctrl.GetValue()
        return CalendarType.WALL if value == "wall" else CalendarType.DESK
    
    def get_selected_format(self) -> ExportFormat:
        """Get the currently selected export format."""
        value = self._format_ctrl.GetValue()
        return ExportFormat(value)
    
    def get_selected_exporter_name(self) -> str:
        """Get the currently selected exporter name."""
        return self._exporter_ctrl.GetValue()
    
    def on_year_changed(self, event: wx.Event):
        """Handler when year selection changes."""
        value = self._year_ctrl.GetValue()
        Settings.set_year(int(value))
    
    def on_calendar_type_changed(self, event: wx.Event):
        """Handler when calendar type selection changes."""
        self.update_exporter_list()
        self.update_options_ui()
    
    def on_format_changed(self, event: wx.Event):
        """Handler when format selection changes."""
        self.update_exporter_list()
        self.update_options_ui()
    
    def on_exporter_changed(self, event: wx.Event):
        """Handler when exporter variant selection changes."""
        self.update_options_ui()
    
    def update_exporter_list(self):
        """Update the exporter variant choices based on current format and calendar type."""
        calendar_type = self.get_selected_calendar_type()
        format = self.get_selected_format()
        
        # Get all available exporters for this combination
        exporters = ExporterRegistry.get_exporters_for(format, calendar_type)
        
        if exporters:
            names = [exp['name'] for exp in exporters]
            self._exporter_ctrl.Clear()
            self._exporter_ctrl.AppendItems(names)
            self._exporter_ctrl.SetValue(names[0])
        else:
            self._exporter_ctrl.Clear()
            self._exporter_ctrl.SetValue("(none available)")
    
    def update_options_ui(self):
        """Dynamically generate option controls based on the selected exporter's OPTIONS_SCHEMA."""
        # Clear existing options
        self._options_sizer.Clear(True)
        self._option_controls.clear()
        
        # Get the selected exporter class
        try:
            calendar_type = self.get_selected_calendar_type()
            format = self.get_selected_format()
            exporter_name = self.get_selected_exporter_name()
            
            if not ExporterRegistry.has_exporter(format, calendar_type, exporter_name):
                return
            
            exporter = ExporterRegistry.get_exporter(format, calendar_type, exporter_name)
            self._current_exporter_class = exporter.__class__
            
            # Get OPTIONS_SCHEMA
            schema = getattr(self._current_exporter_class, 'OPTIONS_SCHEMA', {})
            
            if not schema:
                self._options_sizer.Add(
                    wx.StaticText(self._options_panel, label="No options available"),
                    0, wx.ALL, 5
                )
            else:
                for option_name, option_spec in schema.items():
                    self._add_option_control(option_name, option_spec)
            
            # Refresh layout
            self._options_panel.Layout()
            self.Layout()
            
        except (KeyError, ValueError) as e:
            # Exporter not available
            pass
    
    def _add_option_control(self, name: str, spec: Dict[str, Any]):
        """Add a UI control for a single option based on its spec."""
        option_type = spec.get('type', 'string')
        description = spec.get('description', '')
        default = spec.get('default')
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self._options_panel, label=f"{name}:")
        label.SetToolTip(description)
        sizer.Add(label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        control = None
        
        if option_type in ('integer', 'int'):
            # Integer input with optional min/max
            min_val = spec.get('min', -999999)
            max_val = spec.get('max', 999999)
            default_val = default if default is not None else min_val
            
            control = wx.SpinCtrl(
                self._options_panel,
                value=str(default_val),
                min=min_val,
                max=max_val,
                initial=default_val
            )
            
        elif option_type in ('boolean', 'bool'):
            # Checkbox
            default_val = bool(default) if default is not None else False
            control = wx.CheckBox(self._options_panel)
            control.SetValue(default_val)
            
        elif option_type in ('enum', 'choices'):
            # ComboBox with predefined choices
            choices = spec.get('choices', [])
            default_val = str(default) if default is not None else (choices[0] if choices else "")
            control = wx.ComboBox(
                self._options_panel,
                value=default_val,
                choices=[str(c) for c in choices],
                style=wx.CB_READONLY
            )
            
        else:  # string or text
            # Text input
            default_val = str(default) if default is not None else ""
            control = wx.TextCtrl(self._options_panel, value=default_val)
        
        if control:
            control.SetToolTip(description)
            sizer.Add(control, 1, wx.ALL | wx.EXPAND, 5)
            self._option_controls[name] = control
            self._options_sizer.Add(sizer, 0, wx.ALL | wx.EXPAND, 5)
    
    def get_options_from_ui(self) -> Dict[str, Any]:
        """Extract option values from UI controls."""
        options = {}
        
        if not self._current_exporter_class:
            return options
        
        schema = getattr(self._current_exporter_class, 'OPTIONS_SCHEMA', {})
        
        for name, control in self._option_controls.items():
            spec = schema.get(name, {})
            option_type = spec.get('type', 'string')
            
            if option_type in ('integer', 'int'):
                options[name] = control.GetValue()
            elif option_type in ('boolean', 'bool'):
                options[name] = control.GetValue()
            elif option_type == 'choices':
                options[name] = control.GetValue()
            else:  # string
                options[name] = control.GetValue()
        
        return options
    
    def on_export(self, event: wx.Event):
        """Handler to export the calendar using the selected exporter and options."""
        main_frame = self.get_main_frame()
        if not main_frame:
            return
        
        # Get calendar based on type
        calendar_type = self.get_selected_calendar_type()
        if calendar_type == CalendarType.WALL:
            calendar = main_frame.get_wall_calendar()
        else:
            calendar = main_frame.get_desk_calendar()
        
        # Get selected exporter
        format = self.get_selected_format()
        exporter_name = self.get_selected_exporter_name()
        
        try:
            exporter = ExporterRegistry.get_exporter(format, calendar_type, exporter_name)
        except KeyError as e:
            wx.MessageBox(str(e), "Exporter Not Found", wx.OK | wx.ICON_ERROR)
            return
        
        # Get options from UI
        options = self.get_options_from_ui()
        
        # Setup output directory
        output_base = f"{calendar_type.value.title()}Cal"
        output_dir = FilesManager.instance().get_file_path(output_base)
        
        # Create progress dialog
        progress_dialog = wx.ProgressDialog(
            f"Exporting {calendar_type.value.title()} Calendar",
            "Please wait...",
            maximum=100,
            style=wx.PD_SMOOTH | wx.PD_AUTO_HIDE | wx.PD_CAN_ABORT
        )
        
        def progress_callback(current: int, total: int, message: str):
            """Update progress dialog."""
            percent = int((current / total) * 100) if total > 0 else 0
            progress_dialog.Update(percent, message)
        
        # Create export context
        context = ExportContext(
            calendar=calendar,
            calendar_type=calendar_type,
            format=format,
            output_dir=Path(output_dir),
            project_root=FilesManager.instance().root,
            options=options,
            progress_callback=progress_callback
        )
        
        try:
            # Perform export
            result = exporter.export(context)
            
            progress_dialog.Destroy()
            
            # Show result
            if result.success:
                wx.MessageBox(
                    f"Successfully exported {result.file_count} files to:\n{output_dir}",
                    "Export Complete",
                    wx.OK | wx.ICON_INFORMATION
                )
            else:
                error_msg = "\n".join(result.errors)
                wx.MessageBox(
                    f"Export completed with errors:\n{error_msg}",
                    "Export Errors",
                    wx.OK | wx.ICON_WARNING
                )
        except Exception as e:
            progress_dialog.Destroy()
            wx.MessageBox(
                f"Export failed:\n{str(e)}",
                "Export Error",
                wx.OK | wx.ICON_ERROR
            )

