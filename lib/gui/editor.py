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
    def project_new(self, event: wx.Event) -> None:
        dirDialog: wx.DirDialog = None
        with wx.DirDialog(self, "New Project", "", wx.DD_DEFAULT_STYLE) as dirDialog:
            if dirDialog.ShowModal() == wx.ID_OK:
                directory = dirDialog.GetPath()
                self.init_project(directory)

    def project_open(self, event: wx.Event) -> None:
        path = OpenDialog.ChoseFile(self, "Open Project", OpenDialog.JSON)
        if path:
            with open(path) as fp:
                obj = json.load(fp)
                obj['project'] = str(pathlib.Path(path).parent)
                self.load(obj)

    def project_save(self, event: wx.Event) -> None:
        with self._files_manager.open("Project.json", "w+") as file:
            obj = self.to_json()
            file.write(json.dumps(obj, indent="    "))

    def menu_handler(self, event: wx.Event) -> None:
        eid = event.GetId()
        if eid == wx.ID_OPEN:
            self.project_open(event)
        elif eid == wx.ID_SAVE:
            self.project_save(event)
        elif eid == wx.ID_NEW:
            self.project_new(event)

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self._files_manager: FilesManager = FilesManager("tmp")

        self.SetTitle("Calendar Editor")
        self.SetSize(800, 600)

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
        
        sizer.Add(self.notebook, 1, flag=wx.EXPAND)

        try:
            with self._files_manager.open("Project.json", "r+") as file:
                obj = json.load(file)
                obj["project"] = str(self._files_manager.root)
                self.load(obj)
        except:
            pass

    def load(self, data: dict):
        self._files_manager = FilesManager(data["project"])
        self._wall_pages_view.load(data.get("artworks", {}))
        self._desk_pages_view.load(data.get("desk_pages", {}))
        self._birthday_view.load(data.get("birthdays", {}))
        self._settings_view.load(data.get("settings", {}))

    def to_json(self) -> dict:
        data = {}
        data["project"] = str(self._files_manager.root)
        data["artworks"] = self._wall_pages_view.to_json()
        data["desk_pages"] = self._desk_pages_view.to_json()
        data["birthdays"] = self._birthday_view.to_json()
        data["settings"] = self._settings_view.to_json()

        return data

    def init_project(self, project: str) -> None:
        self._files_manager = FilesManager(project)
        self._project_name.SetValue(str(self._files_manager.root))
        self._wall_pages_view.clear()
        self._desk_pages_view.clear()
        self._birthday_view.clear()
        self._settings_view.clear()

    def get_vcalendar(self) -> libics.VCalendar:
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

class MyApp(wx.App):
    def OnInit(self):
        self.frame = CalendarInfoFrame(None, title="Calendar Editor")
        self.frame.Show()
        return True


if __name__ == "__main__":
    app = MyApp(False)
    app.MainLoop()
