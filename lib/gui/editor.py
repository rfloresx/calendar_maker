"""GUI editor main window and application entrypoint.

This module provides CalendarInfoFrame, the main editor window used by the
application, and MyApp, the wx.App subclass that starts the GUI. Public
methods that are used by other modules (load, to_json, get_wall_calendar,
get_desk_calendar, etc.) receive explanatory docstrings.
"""

try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))


import wx
import wx.adv
import wx.lib.agw.flatnotebook as fnb
import datetime
import pathlib
import json
import copy

import lib.calendar.ics_loader as libics
import lib.pycal as libpycal


from lib.filemanager import FilesManager
from lib.gui.util import OpenDialog, MainFrame

from lib.gui.birthday import BirthdayPanel
from lib.gui.calendar import CalendarPagePanel, DeskCalendarPanel
from lib.gui.exporter import ExporterPanel
from lib.gui.settings import SettingsPanel
from lib.gui.settings import Settings

######################################################
# Editor Main
######################################################


class CalendarInfoFrame(MainFrame):
    """Main editor frame providing project menu, notebook pages and
    convenience helpers for loading/saving project state and building
    calendar objects used by exporters.
    """
    def project_new(self, event: wx.Event) -> None:
        """Prompt for a directory and initialize a new project there."""
        dirDialog: wx.DirDialog = None
        with wx.DirDialog(self, "New Project", "", wx.DD_DEFAULT_STYLE) as dirDialog:
            if dirDialog.ShowModal() == wx.ID_OK:
                directory = dirDialog.GetPath()
                self.init_project(directory)

    def project_open(self, event: wx.Event) -> None:
        """Open a saved project JSON file and load its data into the editor."""
        path = OpenDialog.ChoseFile(self, "Open Project", OpenDialog.JSON)
        if path:
            with open(path) as fp:
                obj = json.load(fp)
                obj['project'] = str(pathlib.Path(path).parent)
                self.load(obj)

    def project_save(self, event: wx.Event) -> None:
        """Save the current project to Project.json inside the project root."""
        with self._files_manager.open("Project.json", "w+") as file:
            obj = self.to_json()
            file.write(json.dumps(obj, indent="    "))
            self._last_saved_state = copy.deepcopy(obj)
            self._has_unsaved_changes = False
            self._update_title()

    def menu_handler(self, event: wx.Event) -> None:
        """Handle file menu actions (new/open/save)."""
        eid = event.GetId()
        if eid == wx.ID_OPEN:
            self.project_open(event)
        elif eid == wx.ID_SAVE:
            self.project_save(event)
        elif eid == wx.ID_NEW:
            self.project_new(event)

    def __init__(self, *args, **kw):
        """Create and initialize the editor GUI components."""
        super().__init__(*args, **kw)

        self._files_manager: FilesManager = FilesManager("tmp")
        self._has_unsaved_changes: bool = False
        self._last_saved_state: dict = None

        self.SetTitle("Calendar Editor")
        self.SetSize(800, 600)
        
        # Bind close event
        self.Bind(wx.EVT_CLOSE, self.on_close)

        # Menu bar
        menubar = wx.MenuBar()

        file_menu = wx.Menu()

        item = wx.MenuItem(file_menu, wx.ID_NEW,
                           text="&New", kind=wx.ITEM_NORMAL)
        file_menu.Append(item)

        item = wx.MenuItem(file_menu, wx.ID_OPEN,
                           text="&Open\tCtrl+O", kind=wx.ITEM_NORMAL)
        file_menu.Append(item)

        item = wx.MenuItem(file_menu, wx.ID_SAVE,
                           text="&Save\tCtrl+S", kind=wx.ITEM_NORMAL)
        file_menu.Append(item)

        file_menu.AppendSeparator()
        menubar.Append(file_menu, "&Project")
        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.menu_handler)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        # Add
        self._project_name: wx.TextCtrl = wx.TextCtrl(self, value=str(
            self._files_manager.root), size=(100, 25), style=wx.TE_READONLY)
        sizer.Add(self._project_name, 0, wx.EXPAND | wx.ALL, 5)

        # Create a notebook (tab container)
        self.notebook: fnb.FlatNotebook = fnb.FlatNotebook(
            self, agwStyle=fnb.FNB_NO_X_BUTTON | fnb.FNB_NO_NAV_BUTTONS)
        self.notebook.SetActiveTabColour(wx.Colour(0x0f, 0x0f, 0x0f))
        self._birthday_view: BirthdayPanel = BirthdayPanel(
            parent=self.notebook)

        self._wall_pages_view: CalendarPagePanel = CalendarPagePanel(
            parent=self.notebook)
        self._desk_pages_view: CalendarPagePanel = DeskCalendarPanel(
            parent=self.notebook)
        self._export_view: ExporterPanel = ExporterPanel(
            parent=self.notebook)
        
        self._settings_view: SettingsPanel = SettingsPanel(
            parent=self.notebook)

        self.notebook.AddPage(self._wall_pages_view, "Wall Pages")
        self.notebook.AddPage(self._desk_pages_view, "Desk Calendar")
        self.notebook.AddPage(self._birthday_view, "Birthdays")
        self.notebook.AddPage(self._export_view, "Export")
        self.notebook.AddPage(self._settings_view, "Settings")
        
        # Set up timer to periodically check for changes
        self._change_check_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._check_for_changes, self._change_check_timer)
        self._change_check_timer.Start(1000)  # Check every second
        
        sizer.Add(self.notebook, 1, flag=wx.EXPAND)

        try:
            with self._files_manager.open("Project.json", "r+") as file:
                obj = json.load(file)
                obj["project"] = str(self._files_manager.root)
                self.load(obj)
        except:
            pass

    def load(self, data: dict):
        """Load project data into the editor views.

        Args:
            data: dictionary with keys 'artworks', 'desk_pages', 'birthdays', 'settings'.
        """
        self._files_manager = FilesManager(data["project"])
        self._wall_pages_view.load(data.get("artworks", {}))
        self._desk_pages_view.load(data.get("desk_pages", {}))
        self._birthday_view.load(data.get("birthdays", {}))
        self._settings_view.load(data.get("settings", {}))
        self._last_saved_state = copy.deepcopy(data)
        self._has_unsaved_changes = False
        self._update_title()

    def to_json(self) -> dict:
        """Serialize the editor state into a JSON-serializable dict."""
        data = {}
        data["project"] = str(self._files_manager.root)
        data["artworks"] = self._wall_pages_view.to_json()
        data["desk_pages"] = self._desk_pages_view.to_json()
        data["birthdays"] = self._birthday_view.to_json()
        data["settings"] = self._settings_view.to_json()

        return data

    def init_project(self, project: str) -> None:
        """Initialize a new project directory and clear current views."""
        self._files_manager = FilesManager(project)
        self._project_name.SetValue(str(self._files_manager.root))
        self._wall_pages_view.clear()
        self._desk_pages_view.clear()
        self._birthday_view.clear()
        self._settings_view.clear()
        self._last_saved_state = None
        self._has_unsaved_changes = False
        self._update_title()

    def get_vcalendar(self) -> libics.VCalendar:
        """Collect birthdays from the UI and return a VCalendar instance."""
        birthdays = self._birthday_view.get_birthdays()
        vcal = libics.VCalendar()

        for birthday in birthdays:
            data = {
                libics.VCalendar.DATE_KEY: [birthday.date],
                libics.VCalendar.SUMMARY_KEY: [birthday.title],
                libics.VCalendar.IMAGES_KEY: [birthday.image]
            }
            vcal.add(libics.VCalendar.VEvent(data))
        return vcal

    def get_wall_calendar(self) -> libpycal.Calendar:
        """Build and return a Calendar object representing the wall calendar."""
        cal = libpycal.Calendar(Settings.year, libpycal.EventsManager(
            Settings.year, self.get_vcalendar()))
        pages = self._wall_pages_view.pages
        page = pages[0]
        cal.front_page.image = page.image
        cal.front_page.title = page.description

        arts = cal.arts
        for i in range(1, len(pages)):
            page = pages[i]
            arts[i-1].image = page.image
            arts[i-1].title = page.description
        return cal

    def get_desk_calendar(self) -> libpycal.Calendar:
        """Build and return a Calendar object representing the desk calendar."""
        cal = libpycal.Calendar(Settings.year, libpycal.EventsManager(
            Settings.year, self.get_vcalendar()))
        pages = self._desk_pages_view.pages
        page = pages[0]
        cal.front_page.image = page.image
        cal.front_page.title = page.description

        arts = cal.arts
        for i in range(1, len(pages)):
            page = pages[i]
            arts[i-1].image = page.image
            arts[i-1].title = page.description
        return cal

    def _check_for_changes(self, event=None):
        """Periodically check if current state differs from saved state."""
        if self._last_saved_state is not None:
            current_state = self.to_json()
            has_changes = self._last_saved_state != current_state
            if has_changes != self._has_unsaved_changes:
                self._has_unsaved_changes = has_changes
                self._update_title()

    def on_content_changed(self, event=None):
        """Mark that content has changed (unsaved changes)."""
        if event:
            event.Skip()
        current_state = self.to_json()
        if self._last_saved_state != current_state:
            self._has_unsaved_changes = True
            self._update_title()

    def _update_title(self):
        """Update window title to show unsaved changes indicator."""
        base_title = "Calendar Editor"
        if self._has_unsaved_changes:
            self.SetTitle(f"{base_title} *")
        else:
            self.SetTitle(base_title)

    def on_close(self, event):
        """Handle window close event and prompt if there are unsaved changes."""
        if self._has_unsaved_changes:
            dlg = wx.MessageDialog(
                self,
                "You have unsaved changes. Do you want to save before closing?",
                "Unsaved Changes",
                wx.YES_NO | wx.CANCEL | wx.ICON_WARNING
            )
            result = dlg.ShowModal()
            dlg.Destroy()
            
            if result == wx.ID_YES:
                self.project_save(None)
                event.Skip()  # Continue with close
            elif result == wx.ID_NO:
                event.Skip()  # Continue with close without saving
            else:  # wx.ID_CANCEL
                event.Veto()  # Cancel the close
        else:
            event.Skip()  # No unsaved changes, close normally

class MyApp(wx.App):
    """Simple wx.App subclass used to start the editor application."""
    def OnInit(self):
        """Initialize application and show the main editor frame."""
        self.frame = CalendarInfoFrame(None, title="Calendar Editor")
        self.frame.Show()
        return True


if __name__ == "__main__":
    app = MyApp(False)
    app.MainLoop()
