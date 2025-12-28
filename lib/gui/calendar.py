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
import re

from typing import List, Tuple
from lib.filemanager import FilesManager
from lib.gui.util import ImageButton, Text, ScrolledPanel
from lib.gui.settings import Settings
from lib.gui.panel_mixins import ArtworkPanelOpsMixin, ScrolledPanelItemsMixin

import datetime


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
        self._selected_place_index = 0  # Track selected place index
        self._place_overrides = {}  # Store user edits to place properties
        self._sizer: wx.BoxSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._sizer)

        if self._month == 0:
            artwork_name = "Cover Page"
        else:
            artwork_name = datetime.date(
                2000, month if month > 0 else 1, 1).strftime("%B")
        self._artwork_label: wx.StaticText = wx.StaticText(
            parent=self, label=f"{artwork_name}", size=(400, 25))

        # Image
        self._image_ctrl: ImageButton = ImageButton(
            image, size=img_size, parent=self, style=wx.BORDER_NONE)

        # Description
        self._description_ctrl: Text = Text(value=description, lines=2, parent=self, size=(
            400, 50))
        self._description_ctrl.Bind(wx.EVT_TEXT, self._on_description_changed)

        # Formatted description preview
        self._formatted_description: Text = Text(
            value="", parent=self, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_NO_VSCROLL, size=(400, 50))

        self._metadata: Text = Text(
            value="", parent=self, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_NO_VSCROLL, size=(400, 50))
        self._places: wx.ComboBox = wx.ComboBox(
            parent=self, style=wx.CB_DROPDOWN | wx.CB_READONLY, value="", choices=[])
        self._places.Bind(wx.EVT_COMBOBOX, self._on_place_selected)

        # Editable place fields
        place_edit_sizer = wx.BoxSizer(wx.VERTICAL)

        # Name field
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_sizer.Add(wx.StaticText(self, label="Name:"), 0,
                       wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self._place_name_ctrl = wx.TextCtrl(self, size=(-1, -1))
        self._place_name_ctrl.Bind(wx.EVT_TEXT, self._on_place_field_changed)
        name_sizer.Add(self._place_name_ctrl, 1, wx.EXPAND)
        place_edit_sizer.Add(name_sizer, 0, wx.EXPAND | wx.BOTTOM, 5)

        # City and State on same line
        city_state_sizer = wx.BoxSizer(wx.HORIZONTAL)
        city_state_sizer.Add(wx.StaticText(self, label="City:"),
                             0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self._place_city_ctrl = wx.TextCtrl(self, size=(-1, -1))
        self._place_city_ctrl.Bind(wx.EVT_TEXT, self._on_place_field_changed)
        city_state_sizer.Add(self._place_city_ctrl, 1,
                             wx.EXPAND | wx.RIGHT, 10)

        city_state_sizer.Add(wx.StaticText(
            self, label="State:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self._place_state_ctrl = wx.TextCtrl(self, size=(-1, -1))
        self._place_state_ctrl.Bind(wx.EVT_TEXT, self._on_place_field_changed)
        city_state_sizer.Add(self._place_state_ctrl, 1, wx.EXPAND)
        place_edit_sizer.Add(city_state_sizer, 0, wx.EXPAND)

        inputs_sizer = wx.BoxSizer(wx.VERTICAL)

        inputs_sizer.Add(self._description_ctrl, 0, wx.EXPAND | wx.ALL, 0)
        inputs_sizer.Add(self._formatted_description, 0, wx.EXPAND | wx.ALL, 0)
        inputs_sizer.Add(self._metadata, 0, wx.EXPAND | wx.ALL, 0)
        inputs_sizer.Add(self._places, 0, wx.EXPAND | wx.ALL, 0)
        inputs_sizer.Add(place_edit_sizer, 0, wx.EXPAND | wx.ALL, 5)

        call_sizer = wx.BoxSizer(wx.HORIZONTAL)
        call_sizer.Add(self._image_ctrl, 0, wx.LEFT | wx.RIGHT, 10)
        call_sizer.Add(inputs_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self._sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 5)
        self._sizer.Add(self._artwork_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._sizer.Add(call_sizer, 0, wx.EXPAND | wx.ALL, 0)
        self.update_metadata()

    @property
    def month(self) -> int:
        """Month number associated with this artwork (0 for cover)."""
        return self._month

    @property
    def image(self) -> str:
        """Path to the selected artwork image (may be None)."""
        return self._image_ctrl.filename

    def _on_place_selected(self, event):
        """Handle place selection change from combo box."""
        self._selected_place_index = self._places.GetSelection()
        self._populate_place_fields()
        self._update_formatted_description()

    def _on_description_changed(self, event):
        """Handle description text change to update formatted preview."""
        self._update_formatted_description()

    def _on_place_field_changed(self, event):
        """Handle changes to place edit fields."""
        # Store overrides for the current place index
        if self._selected_place_index >= 0:
            self._place_overrides[self._selected_place_index] = {
                'name': self._place_name_ctrl.GetValue(),
                'city': self._place_city_ctrl.GetValue(),
                'state': self._place_state_ctrl.GetValue()
            }
        self._update_formatted_description()

    def _populate_place_fields(self):
        """Populate place edit fields with current place data."""
        image_info = self._image_ctrl.image_info
        places = image_info.places

        # Check if we have overrides first (works even without metadata places)
        if self._selected_place_index in self._place_overrides:
            overrides = self._place_overrides[self._selected_place_index]
            self._place_name_ctrl.ChangeValue(overrides.get('name', ''))
            self._place_city_ctrl.ChangeValue(overrides.get('city', ''))
            self._place_state_ctrl.ChangeValue(overrides.get('state', ''))
        elif places and self._selected_place_index < len(places):
            # Use original place data if available
            place = places[self._selected_place_index]
            self._place_name_ctrl.ChangeValue(place.name or '')
            self._place_city_ctrl.ChangeValue(place.city or '')
            self._place_state_ctrl.ChangeValue(place.state or '')
        else:
            # No places and no overrides - clear fields but leave them editable
            self._place_name_ctrl.ChangeValue('')
            self._place_city_ctrl.ChangeValue('')
            self._place_state_ctrl.ChangeValue('')

    def _update_formatted_description(self):
        """Update the formatted description preview."""
        formatted = self._process_description_template(
            self._description_ctrl.GetValue())
        self._formatted_description.SetValue(formatted)

    @property
    def description(self) -> str:
        """Description text for the artwork with template replacements applied."""
        return self._process_description_template(self._description_ctrl.GetValue())

    def _process_description_template(self, template: str) -> str:
        """Process template using TextTemplate with context builder."""
        from lib.gui.util import TextTemplate, build_text_context
        if not template:
            return template
        image_info = self._image_ctrl.image_info
        overrides = self._place_overrides.get(self._selected_place_index)
        ctx = build_text_context(
            image_info=image_info,
            selected_place_index=self._selected_place_index,
            overrides=overrides,
            year=Settings().year,
        )
        return TextTemplate(template or "").render(ctx)

    def update_metadata(self):
        """Refresh the metadata text area from the image control."""
        image_info = self._image_ctrl.image_info
        places = image_info.places
        datetime_original = image_info.datetime_original

        info = {}
        if datetime_original is not None:
            info_str = datetime_original.strftime("%b-%d")
            info["Date"] = info_str

        if places:
            places_lst = []
            for place in places:
                places_lst.append(
                    f"{place.name}, {place.city}, {place.state}")

            self._places.Clear()
            self._places.AppendItems(places_lst)
            # Restore selected index, default to 0 if out of bounds
            if self._selected_place_index < len(places_lst):
                self._places.SetSelection(self._selected_place_index)
            else:
                self._selected_place_index = 0
                self._places.SetSelection(0)
        else:
            # No places in metadata - still allow manual entry
            self._places.Clear()
            self._selected_place_index = 0

        lines = []
        for key, value in info.items():
            lines.append(f"{key}: {value}\n")
        self._metadata.SetValue("".join(lines))

        # Populate place edit fields
        self._populate_place_fields()

        # Update formatted description when metadata changes
        self._update_formatted_description()

    def set_image(self, filename: str) -> None:
        """Set the artwork image and update metadata.

        Args:
            filename: path to the image file or None to clear.
        """
        self._image_ctrl.set_image(filename)
        self.update_metadata()

    def set_description(self, description: str) -> None:
        """Set the artwork description text."""
        self._description_ctrl.SetValue(description)

    def load(self, data: dict) -> None:
        """Load panel state from a dictionary as produced by to_json."""
        self.set_image(data["image"])
        self.set_description(data["description"])
        # Load selected place index if available
        if "selected_place_index" in data:
            self._selected_place_index = data["selected_place_index"]
            # Update combo box selection after image is loaded
            if self._places.GetCount() > self._selected_place_index:
                self._places.SetSelection(self._selected_place_index)
        # Load place overrides if available
        if "place_overrides" in data:
            # Convert string keys back to integers
            self._place_overrides = {
                int(k): v for k, v in data["place_overrides"].items()}
            self._populate_place_fields()
            self._update_formatted_description()

    def to_json(self) -> dict:
        """Serialize the panel to a JSON-serializable dictionary."""
        data = {}
        data["image"] = FilesManager.instance().get_relative_path(self.image)
        # Save raw template, not processed
        data["description"] = self._description_ctrl.GetValue()
        data["selected_place_index"] = self._selected_place_index
        # Save place overrides (convert int keys to strings for JSON)
        data["place_overrides"] = {
            str(k): v for k, v in self._place_overrides.items()}
        return data

    def on_image_changed(self, event):
        """Callback invoked when the underlying image control's image changes."""
        self.update_metadata()


class CalendarPagePanel(wx.Panel, ArtworkPanelOpsMixin):
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

    def create_artwork_panel(self, id, image, img_size, desc):
        return ArtWorkInfoPanel(month=id, image=image, img_size=img_size, description=desc, parent=self._scrolling_panel)


class DeskCalendarPanel(wx.Panel, ArtworkPanelOpsMixin):
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

    def create_artwork_panel(self, id, image, img_size, desc):
        return ArtWorkInfoPanel(month=id, image=image, img_size=img_size, description=desc, parent=self._scrolling_panel)
