"""Birthday panel UI components.

Provides wx based panels used to view and edit birthday entries. Public
classes include BirthdayInfoPanel (single entry editor) and BirthdayPanel
(collection of birthdays with import/sort helpers).
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

import lib.calendar.ics_loader as libics


from lib.filemanager import FilesManager
from lib.gui.util import ImageButton, OpenDialog, ScrolledPanel
from typing import List


class AspectRations:
    """Simple constants describing aspect ratios used by the UI."""
    # CELL=(14:10)
    CELL = (14, 10)
    CELL_SCALE = 15/10
    # FRONT_PAGE=(11:6)
    FRONT_PAGE = (11, 6)
    FRONT_PAGE_SCALE = 11/6
    # ART_PAGE=(15:10) 960/648
    ART_PAGE = (15, 10)
    ART_PAGE_SCALE = 15/10


class BirthdayInfoPanel(wx.Panel):
    """Panel representing a single birthday entry with image, title and date.

    Public properties:
        image: path to the selected image.
        title: birthday title/summary.
        date: selected date as datetime.datetime.
    """
    def __init__(self, image: str = None, title: str = None, date: datetime.datetime = None, *args, **kw):
        super().__init__(*args, **kw)

        self._sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self._sizer)

        # Display Image
        self._image_ctrl = ImageButton(image, size=(
            140, 100), parent=self, style=wx.BORDER_NONE)

        # Title
        self._title_ctrl = wx.TextCtrl(self, size=(200, 25))
        if title:
            self._title_ctrl.SetValue(title)

        # Set time
        self._date_ctrl = wx.adv.DatePickerCtrl(
            self, size=(200, 25), style=wx.adv.DP_DROPDOWN)
        if date:
            dt = wx.DateTime.FromDMY(date.day, date.month-1, date.year)
            self._date_ctrl.SetValue(dt)

        self._del_button = wx.Button(self, label="Delete")
        self._del_button.Bind(wx.EVT_BUTTON, self.on_delete)

        inputs_sizer = wx.BoxSizer(wx.VERTICAL)
        inputs_sizer.Add(self._title_ctrl, 0, wx.EXPAND | wx.ALL, 5)
        inputs_sizer.Add(self._date_ctrl, 0, wx.EXPAND | wx.ALL, 5)
        inputs_sizer.Add(self._del_button, 0, wx.EXPAND | wx.ALL, 5)

        self._sizer.Add(self._image_ctrl, 0, wx.ALL, 10)
        self._sizer.Add(inputs_sizer, 0, wx.EXPAND | wx.ALL, 10)

    def on_delete(self, event: wx.Event):
        """Handle deletion of this panel from its parent ScrolledPanel."""
        if self.Parent and isinstance(self.Parent, ScrolledPanel):
            panel: ScrolledPanel = self.Parent
            panel.Remove(self)
            self.Destroy()
            panel.Refresh()

    @property
    def image(self) -> str:
        """Return the path of the currently selected image (may be None)."""
        return self._image_ctrl.filename

    @property
    def title(self) -> str:
        """Return the title/summary text for the birthday."""
        return self._title_ctrl.GetValue()

    @property
    def date(self) -> datetime.datetime:
        """Return the selected date as a datetime.datetime instance."""
        wx_dt: wx.DateTime = self._date_ctrl.GetValue()
        return datetime.datetime(wx_dt.GetYear(), wx_dt.GetMonth() + 1, wx_dt.GetDay(),
                                 wx_dt.GetHour(), wx_dt.GetMinute(), wx_dt.GetSecond())

    def set_image(self, filename: str) -> None:
        """Set the displayed image for this birthday entry."""
        self._image_ctrl.set_image(filename)

    def set_title(self, value: str) -> None:
        """Set the title text for this birthday entry."""
        self._title_ctrl.SetValue(value)

    def set_date(self, date: str) -> None:
        """Set the date control from a string in DD/MM/YYYY format."""
        date: datetime.datetime = datetime.datetime.strptime(date, "%d/%m/%Y")

        wdt = wx.DateTime(year=date.year, month=date.month-1, day=date.day)
        self._date_ctrl.SetValue(wdt)

    def load(self, data: dict) -> None:
        """Load state from a dictionary produced by to_json."""
        self.set_image(data["image"])
        self.set_title(data["title"])
        self.set_date(data["date"])

    def to_json(self) -> dict:
        """Return a JSON-serializable representation of this entry."""
        return {
            "image": FilesManager.instance().get_relative_path(self.image),
            "title": self.title,
            "date": self.date.strftime("%d/%m/%Y")
        }


class BirthdayPanel(wx.Panel):
    """Panel that contains and manages multiple BirthdayInfoPanel entries.

    Provides import from ICS, add, sort and serialization helpers.
    """
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self._scrolling_panel: ScrolledPanel = ScrolledPanel(self)

        self._sizer: wx.BoxSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._sizer)

        inputs: wx.BoxSizer = wx.BoxSizer(wx.HORIZONTAL)
        import_button = wx.Button(self, label="Import Ics")
        import_button.Bind(wx.EVT_BUTTON, self.on_import_ics)

        load_button = wx.Button(self, label="Add birthday")
        load_button.Bind(wx.EVT_BUTTON, self.on_add_birthday)

        sort_button = wx.Button(self, label="Sort")
        sort_button.Bind(wx.EVT_BUTTON, self.on_sort_birthday)
        inputs.Add(import_button, 1, wx.EXPAND | wx.ALL, 1)
        inputs.Add(load_button, 1, wx.EXPAND | wx.ALL, 1)
        inputs.Add(sort_button, 1, wx.EXPAND | wx.ALL, 1)

        self._sizer.Add(inputs, 0, wx.EXPAND | wx.ALL, 5)
        self._sizer.Add(self._scrolling_panel, 1, wx.EXPAND, 10)

    def add_birthday(self, image: str, title: str = None, date: datetime = None) -> None:
        """Append a new BirthdayInfoPanel to the scrolling list.

        If an image path is provided it will be added to the project via
        FilesManager and the returned project path will be used.
        """
        if image is not None:
            image = FilesManager.instance().add_file(image)
        panel = BirthdayInfoPanel(
            parent=self._scrolling_panel, image=image, title=title, date=date)
        self._scrolling_panel.Add(panel)
        self.Layout()
        self.Refresh()

    def on_import_ics(self, event: wx.Event) -> None:
        """Import birthdays from an .ics file and add them to the panel."""
        file = OpenDialog.ChoseFile(self, "Select File", OpenDialog.ICS)
        if file:
            vcal = libics.VCalendar(file)
            for ve in vcal.events:
                date = ve.date
                date = datetime.datetime(
                    datetime.datetime.today().year, date.month, date.day)
                self.add_birthday(None, ve.summary, date)
            self.sort()

    def on_add_birthday(self, event: wx.Event) -> None:
        """Handler invoked when the Add button is pressed; creates an empty entry."""
        self.add_birthday(image=None)

    def on_sort_birthday(self, event) -> None:
        """Handler to trigger sorting of birthdays."""
        self.sort()

    def load(self, data: dict) -> None:
        """Load birthdays from a dict produced by to_json."""
        # self._scrolling_panel.clear()
        for item in data["birthdays"]:
            panel = BirthdayInfoPanel(parent=self._scrolling_panel, image=None)
            panel.load(item)
            self._scrolling_panel.Add(panel)
        # self._scrolling_panel.Refresh()
        self.Layout()
        self.Refresh()

    def to_json(self) -> dict:
        """Serialize the contained birthdays to a dict suitable for JSON."""
        birthdays = []
        for item in self._scrolling_panel.Items():
            birthdays.append(item.to_json())
        return {"birthdays": birthdays}

    def sort(self) -> None:
        """Sort the contained BirthdayInfoPanel instances by date."""
        self._scrolling_panel.Sort(key=lambda item: item.date)

    def clear(self) -> None:
        """Remove all birthday entries from the panel."""
        self._scrolling_panel.clear()

    def get_birthdays(self) -> List[BirthdayInfoPanel]:
        """Return the list of BirthdayInfoPanel instances currently present."""
        return self._scrolling_panel.Items()
