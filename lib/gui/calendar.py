"""GUI panels for selecting and editing artwork pages.

This module exposes ArtWorkInfoPanel, CalendarPagePanel and DeskCalendarPanel
used by the editor to manage cover and month artwork selections.
"""

try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

import wx

from typing import List, Tuple
from lib.filemanager import FilesManager
from lib.gui.util import ImageButton, Text, ScrolledPanel


class ArtWorkInfoPanel(wx.Panel):
    """Panel that holds artwork image, description and simple metadata.

    Public properties:
        month: integer month index associated with this artwork.
        image: path of the artwork image.
        description: textual description for the artwork.
    """
    def __init__(self, month: int, image: str = None, img_size: Tuple[int, int] = (200, 200), description: str = None, *args, **kw):
        super().__init__(*args, **kw)
        self._month = month
        self._sizer: wx.BoxSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self._sizer)

        # Image
        self._image_ctrl: ImageButton = ImageButton(
            image, size=img_size, parent=self, style=wx.BORDER_NONE)

        # Description
        self._description_ctrl: Text = Text(value=description, lines=2, parent=self, size=(
            400, 50))
            
        self._metadata : Text = Text(value="", parent=self, style=wx.TE_READONLY|wx.TE_MULTILINE|wx.TE_NO_VSCROLL)
        
        inputs_sizer = wx.BoxSizer(wx.VERTICAL)

        inputs_sizer.Add(self._description_ctrl, 0, wx.EXPAND | wx.ALL, 0)
        inputs_sizer.Add(self._metadata, 0, wx.EXPAND | wx.ALL, 0)

        self._sizer.Add(self._image_ctrl, 0, wx.ALL, 10)
        self._sizer.Add(inputs_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.update_metadata()

    @property
    def month(self) -> int:
        """Month number associated with this artwork (0 for cover)."""
        return self._month

    @property
    def image(self) -> str:
        """Path to the selected artwork image (may be None)."""
        return self._image_ctrl.filename

    @property
    def description(self) -> str:
        """Description text for the artwork."""
        return self._description_ctrl.GetValue()

    def update_metadata(self):
        """Refresh the metadata text area from the image control."""
        info = self._image_ctrl.metadata
        lines = []
        for key, value in info.items():
            lines.append(f"{key}: {value}\n")
        self._metadata.SetValue("".join(lines))
                                
    def set_image(self, filename: str) -> None:
        """Set the artwork image and update metadata.

        Args:
            filename: path to the image file or None to clear.
        """
        self._image_ctrl.set_image(filename)
        self.update_metadata()
        print(f"Image set to: {filename}")

    def set_description(self, description: str) -> None:
        """Set the artwork description text."""
        self._description_ctrl.SetValue(description)

    def load(self, data: dict) -> None:
        """Load panel state from a dictionary as produced by to_json."""
        self.set_image(data["image"])
        self.set_description(data["description"])

    def to_json(self) -> dict:
        """Serialize the panel to a JSON-serializable dictionary."""
        data = {}
        data["image"] = FilesManager.instance().get_relative_path(self.image)
        data["description"] = self.description
        return data

    def on_image_changed(self, event):
        """Callback invoked when the underlying image control's image changes."""
        self.update_metadata()

class CalendarPagePanel(wx.Panel):
    """Panel containing the list of month artwork entries for a wall calendar."""
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self._scrolling_panel: ScrolledPanel = ScrolledPanel(self)

        self._sizer: wx.BoxSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._sizer)

        self._sizer.Add(self._scrolling_panel, 1, wx.EXPAND, 10)

        self.add_artwork(0, None, "Cover Page",
                         img_size=(300, int(300*(6/11))))
        for i in range(1, 13):
            self.add_artwork(i, None, f"Month {i}", img_size=(300, 200))

    def add_artwork(self, id, image: str, desc: str, img_size: Tuple[int, int]) -> None:
        """Add a new ArtWorkInfoPanel to the scrolling list."""
        if image is not None:
            image = FilesManager.instance().add_file(image)
        panel = ArtWorkInfoPanel(month=id,
                                 image=image, img_size=img_size, description=desc, parent=self._scrolling_panel)
        self._scrolling_panel.Add(panel)

    def load(self, data: dict) -> None:
        """Load pages from a previously saved dictionary."""
        pages = data["pages"]
        items = self._scrolling_panel.Items()

        for i in range(len(pages)):
            items[i].load(pages[i])

    def to_json(self) -> dict:
        """Serialize the panel state to a dictionary suitable for JSON."""
        data = {}
        data["pages"] = []
        for page in self._scrolling_panel.Items():
            data["pages"].append(page.to_json())
        return data

    def clear(self):
        """Reset all pages to default empty state (no images, default descriptions)."""
        pages: List[ArtWorkInfoPanel] = self._scrolling_panel.Items()
        pages[0].set_description("Cover Page")
        pages[0].set_image(None)
        for i in range(1, len(pages)):
            pages[i].set_description(f"Month {i}")
            pages[i].set_image(None)

    @property
    def pages(self) -> List[ArtWorkInfoPanel]:
        """Return the list of ArtWorkInfoPanel items in the panel."""
        return self._scrolling_panel.Items()


class DeskCalendarPanel(wx.Panel):
    """Panel containing artwork entries optimized for the desk calendar layout."""
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self._scrolling_panel: ScrolledPanel = ScrolledPanel(self)

        self._sizer: wx.BoxSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._sizer)

        self._sizer.Add(self._scrolling_panel, 1, wx.EXPAND, 10)

        self.add_artwork(0, None, "Cover Page", img_size=(300, int(300)))
        for i in range(1, 13):
            self.add_artwork(i, None, f"Month {i}", img_size=(300, 300))

    def add_artwork(self, id, image: str, desc: str, img_size: Tuple[int, int]) -> None:
        """Add a new ArtWorkInfoPanel to the scrolling list."""
        if image is not None:
            image = FilesManager.instance().add_file(image)
        panel = ArtWorkInfoPanel(month=id,
                                 image=image, img_size=img_size, description=desc, parent=self._scrolling_panel)
        self._scrolling_panel.Add(panel)

    def load(self, data: dict) -> None:
        """Load pages from a previously saved dictionary."""
        pages = data["pages"]
        items = self._scrolling_panel.Items()

        for i in range(len(pages)):
            items[i].load(pages[i])

    def to_json(self) -> dict:
        """Serialize the panel state to a dictionary suitable for JSON."""
        data = {}
        data["pages"] = []
        for page in self._scrolling_panel.Items():
            data["pages"].append(page.to_json())
        return data

    def clear(self):
        """Reset all pages to default empty state (no images, default descriptions)."""
        pages: List[ArtWorkInfoPanel] = self._scrolling_panel.Items()
        pages[0].set_description("Cover Page")
        pages[0].set_image(None)
        for i in range(1, len(pages)):
            pages[i].set_description(f"Month {i}")
            pages[i].set_image(None)

    @property
    def pages(self) -> List[ArtWorkInfoPanel]:
        """Return the list of ArtWorkInfoPanel items in the panel."""
        return self._scrolling_panel.Items()
