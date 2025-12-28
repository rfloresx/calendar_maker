"""Photo labeling panel UI components.

Provides wx based panels used to import photos, optionally sort them,
and edit a label template per photo via a popup dialog. Labels support
the same templating used in the calendar artwork views.
"""

try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

import wx
import re
import datetime

from typing import List, Optional

from lib.filemanager import FilesManager
from lib.gui.util import ImageButton, OpenDialog, ScrolledPanel
from lib.gui.panel_mixins import DeleteFromScrolledPanelMixin, ImageSetterMixin


DEFAULT_LABEL_TEMPLATE = "{place.name}\n{place.city}, {place.state}. {date:%b %d}"


class PhotoLabelInfoPanel(wx.Panel, DeleteFromScrolledPanelMixin, ImageSetterMixin):
    """Panel representing a single photo entry with image, place selection,
    metadata preview, and an Edit Label button to modify the label template.

    Public properties:
        image: path to the selected image.
        template: raw label template text.
        label: processed label string after applying template replacements.
        datetime_original: datetime derived from image metadata (for sorting).
    """

    def __init__(self, image: Optional[str] = None, template: Optional[str] = None, *args, **kw):
        super().__init__(*args, **kw)

        self._selected_place_index = 0
        self._place_overrides = {}
        self._template: str = template or DEFAULT_LABEL_TEMPLATE

        # Main vertical sizer to allow a top button bar
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._sizer)

        row_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Left column: Image selector + formatted description (2 lines)
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        self._image_ctrl: ImageButton = ImageButton(
            image, size=(200, 150), parent=self, style=wx.BORDER_NONE
        )

        # Readonly label preview (formatted description under the image)
        self._label_preview: wx.TextCtrl = wx.TextCtrl(
            parent=self,
            style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_NO_VSCROLL,
            size=(200, 40),
        )
        left_sizer.Add(self._image_ctrl, 0, wx.ALL, 10)
        left_sizer.Add(self._label_preview, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Right column: action bar, places combo and editable place fields (like calendar pages)
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        # Action bar placed to the right of the image
        action_bar = wx.BoxSizer(wx.HORIZONTAL)
        action_bar.AddStretchSpacer(1)
        self._edit_button = wx.Button(self, label="Edit Label")
        self._edit_button.Bind(wx.EVT_BUTTON, self._on_edit_label)
        self._del_button = wx.Button(self, label="Delete")
        self._del_button.Bind(wx.EVT_BUTTON, self.on_delete)
        action_bar.Add(self._edit_button, 0, wx.ALL, 5)
        action_bar.Add(self._del_button, 0, wx.ALL, 5)
        right_sizer.Add(action_bar, 0, wx.EXPAND | wx.ALL, 5)

        # Places combo and metadata preview
        self._places: wx.ComboBox = wx.ComboBox(
            parent=self, style=wx.CB_DROPDOWN | wx.CB_READONLY, value="", choices=[]
        )
        self._places.Bind(wx.EVT_COMBOBOX, self._on_place_selected)
        # right_sizer.Add(wx.StaticText(self, label="Places:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        right_sizer.Add(self._places, 0, wx.EXPAND | wx.ALL, 5)

        # Editable place fields (Name, City, State)
        place_edit_sizer = wx.BoxSizer(wx.VERTICAL)

        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_sizer.Add(wx.StaticText(self, label="Name:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self._place_name_ctrl = wx.TextCtrl(self, size=(-1, -1))
        self._place_name_ctrl.Bind(wx.EVT_TEXT, self._on_place_field_changed)
        name_sizer.Add(self._place_name_ctrl, 1, wx.EXPAND)
        place_edit_sizer.Add(name_sizer, 0, wx.EXPAND | wx.BOTTOM, 5)

        city_state_sizer = wx.BoxSizer(wx.HORIZONTAL)
        city_state_sizer.Add(wx.StaticText(self, label="City:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self._place_city_ctrl = wx.TextCtrl(self, size=(-1, -1))
        self._place_city_ctrl.Bind(wx.EVT_TEXT, self._on_place_field_changed)
        city_state_sizer.Add(self._place_city_ctrl, 1, wx.EXPAND | wx.RIGHT, 10)

        city_state_sizer.Add(wx.StaticText(self, label="State:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self._place_state_ctrl = wx.TextCtrl(self, size=(-1, -1))
        self._place_state_ctrl.Bind(wx.EVT_TEXT, self._on_place_field_changed)
        city_state_sizer.Add(self._place_state_ctrl, 1, wx.EXPAND)
        place_edit_sizer.Add(city_state_sizer, 0, wx.EXPAND)

        right_sizer.Add(place_edit_sizer, 0, wx.EXPAND | wx.ALL, 5)

        row_sizer.Add(left_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        row_sizer.Add(right_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        self._sizer.Add(row_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # Populate metadata/places after initialization
        self.update_metadata()
        self._update_label_preview()

    def _on_place_selected(self, event):
        self._selected_place_index = self._places.GetSelection()
        self._populate_place_fields()
        self._update_label_preview()

    def _on_edit_label(self, event):
        """Open a dialog to edit the label template text."""
        dlg = wx.Dialog(self, title="Edit Photo Label", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        dlg_sizer = wx.BoxSizer(wx.VERTICAL)
        dlg.SetSizer(dlg_sizer)

        info_text = wx.StaticText(
            dlg,
            label=(
                "Use placeholders like {place.name}, {place.city}, {place.state}, "
                "and {img.date:%b %d}."
            ),
        )
        template_ctrl = wx.TextCtrl(
            dlg,
            value=self._template or DEFAULT_LABEL_TEMPLATE,
            style=wx.TE_MULTILINE | wx.TE_NO_VSCROLL,
            size=(500, 120),
        )

        btn_sizer = wx.StdDialogButtonSizer()
        btn_ok = wx.Button(dlg, wx.ID_OK)
        btn_cancel = wx.Button(dlg, wx.ID_CANCEL)
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()

        dlg_sizer.Add(info_text, 0, wx.ALL, 10)
        dlg_sizer.Add(template_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        dlg_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        if dlg.ShowModal() == wx.ID_OK:
            self._template = template_ctrl.GetValue()
            self._update_label_preview()
        dlg.Destroy()

    # on_delete from DeleteFromScrolledPanelMixin

    def update_metadata(self):
        """Refresh places combo from the image control."""
        image_info = self._image_ctrl.image_info
        places = image_info.places
        self._places.Clear()
        if places:
            display = [f"{p.name}, {p.city}, {p.state}" for p in places]
            self._places.AppendItems(display)
            if self._selected_place_index < len(display):
                self._places.SetSelection(self._selected_place_index)
            else:
                self._selected_place_index = 0
                self._places.SetSelection(0)
        # Populate editable fields
        self._populate_place_fields()
        self._update_label_preview()

    def on_image_changed(self, _filename):
        self.update_metadata()
        self._update_label_preview()

    @property
    def image(self) -> Optional[str]:
        return self._image_ctrl.filename

    @property
    def datetime_original(self) -> Optional[datetime.datetime]:
        return self._image_ctrl.image_info.datetime_original

    @property
    def template(self) -> str:
        return self._template

    @property
    def label(self) -> str:
        return self._process_template(self._template or DEFAULT_LABEL_TEMPLATE)

    # set_image from ImageSetterMixin

    def set_template(self, value: str) -> None:
        self._template = value or DEFAULT_LABEL_TEMPLATE
        self._update_label_preview()

    def load(self, data: dict) -> None:
        self.set_image(data.get("image"))
        self._selected_place_index = data.get("selected_place_index", 0)
        self.set_template(data.get("template", DEFAULT_LABEL_TEMPLATE))
        # Load place overrides if present
        if "place_overrides" in data:
            self._place_overrides = {int(k): v for k, v in data["place_overrides"].items()}
        self.update_metadata()
        self._update_label_preview()

    def to_json(self) -> dict:
        return {
            "image": FilesManager.instance().get_relative_path(self.image),
            "template": self._template,
            "selected_place_index": self._selected_place_index,
            "place_overrides": {str(k): v for k, v in self._place_overrides.items()},
        }

    def _process_template(self, template: str) -> str:
        """Process template string using TextTemplate and built context."""
        from lib.gui.util import TextTemplate, build_text_context
        image_info = self._image_ctrl.image_info
        overrides = self._place_overrides.get(self._selected_place_index)
        ctx = build_text_context(
            image_info=image_info,
            selected_place_index=self._selected_place_index,
            overrides=overrides,
        )
        return TextTemplate(template or "").render(ctx)

    def _update_label_preview(self) -> None:
        """Update the readonly label preview with the processed description."""
        try:
            text = self.label or ""
            # Limit to two lines
            lines = text.splitlines()
            self._label_preview.SetValue("\n".join(lines[:2]))
        except Exception:
            pass

    def _populate_place_fields(self):
        """Populate place edit fields using overrides or metadata places."""
        image_info = self._image_ctrl.image_info
        places = image_info.places

        if self._selected_place_index in self._place_overrides:
            ov = self._place_overrides[self._selected_place_index]
            self._place_name_ctrl.ChangeValue(ov.get('name', ''))
            self._place_city_ctrl.ChangeValue(ov.get('city', ''))
            self._place_state_ctrl.ChangeValue(ov.get('state', ''))
        elif places and self._selected_place_index < len(places):
            place = places[self._selected_place_index]
            self._place_name_ctrl.ChangeValue(place.name or '')
            self._place_city_ctrl.ChangeValue(place.city or '')
            self._place_state_ctrl.ChangeValue(place.state or '')
        else:
            self._place_name_ctrl.ChangeValue('')
            self._place_city_ctrl.ChangeValue('')
            self._place_state_ctrl.ChangeValue('')

    def _on_place_field_changed(self, event):
        # Store overrides for the current place index
        if self._selected_place_index >= 0:
            self._place_overrides[self._selected_place_index] = {
                'name': self._place_name_ctrl.GetValue(),
                'city': self._place_city_ctrl.GetValue(),
                'state': self._place_state_ctrl.GetValue(),
            }
        self._update_label_preview()


class PhotoLabelsPanel(wx.Panel):
    """Panel that contains and manages multiple PhotoLabelInfoPanel entries.

    Provides import (multi-image), add, sort and serialization helpers.
    """

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

        self._scrolling_panel: ScrolledPanel = ScrolledPanel(self)
        self._sizer: wx.BoxSizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._sizer)

        # Top controls similar to Birthday view
        inputs: wx.BoxSizer = wx.BoxSizer(wx.HORIZONTAL)
        import_button = wx.Button(self, label="Import Photos")
        import_button.Bind(wx.EVT_BUTTON, self.on_import_photos)

        add_button = wx.Button(self, label="Add Photo")
        add_button.Bind(wx.EVT_BUTTON, self.on_add_photo)

        sort_button = wx.Button(self, label="Sort")
        sort_button.Bind(wx.EVT_BUTTON, self.on_sort_photos)

        inputs.Add(import_button, 1, wx.EXPAND | wx.ALL, 1)
        inputs.Add(add_button, 1, wx.EXPAND | wx.ALL, 1)
        inputs.Add(sort_button, 1, wx.EXPAND | wx.ALL, 1)

        self._sizer.Add(inputs, 0, wx.EXPAND | wx.ALL, 5)
        self._sizer.Add(self._scrolling_panel, 1, wx.EXPAND, 10)

    def _is_duplicate_target_path(self, target_path: str) -> bool:
        """Return True if any current row already uses the given project image path."""
        for item in self._scrolling_panel.Items():
            if getattr(item, 'image', None) == target_path:
                return True
        return False

    def add_photo(self, image: Optional[str] = None, template: Optional[str] = None) -> bool:
        """Add a photo row unless it would duplicate an existing project's image path.

        Returns True when added, False when skipped as duplicate.
        """
        # Avoid pre-copying the file here; ImageButton handles copying once.
        if image:
            try:
                # Compute the would-be destination path inside the project
                target = FilesManager.instance().get_target_path(image)
                if self._is_duplicate_target_path(str(target)):
                    return False
            except Exception:
                pass

        panel = PhotoLabelInfoPanel(parent=self._scrolling_panel, image=image, template=template)
        self._scrolling_panel.Add(panel)
        self.Layout()
        self.Refresh()
        return True

    def on_import_photos(self, event: wx.Event) -> None:
        files = OpenDialog.ChoseFiles(self, "Select Photos", OpenDialog.IMAGES)
        if files:
            skipped = []
            added = 0
            for f in files:
                ok = self.add_photo(f, DEFAULT_LABEL_TEMPLATE)
                if ok:
                    added += 1
                else:
                    skipped.append(f)
            self.sort()
            if skipped:
                try:
                    msg = f"Added {added} photo(s). Skipped {len(skipped)} duplicate(s)."
                    wx.MessageBox(msg, "Import Photos", wx.OK | wx.ICON_INFORMATION, parent=self)
                except Exception:
                    pass

    def on_add_photo(self, event: wx.Event) -> None:
        self.add_photo(image=None, template=DEFAULT_LABEL_TEMPLATE)

    def on_sort_photos(self, event: wx.Event) -> None:
        self.sort()

    def load(self, data: dict) -> None:
        for item in data.get("photos", []):
            panel = PhotoLabelInfoPanel(parent=self._scrolling_panel)
            panel.load(item)
            self._scrolling_panel.Add(panel)
        self.Layout()
        self.Refresh()

    def to_json(self) -> dict:
        photos = []
        for item in self._scrolling_panel.Items():
            photos.append(item.to_json())
        return {"photos": photos}

    def sort(self) -> None:
        def key(item: PhotoLabelInfoPanel):
            dt = item.datetime_original
            # Sort None dates last
            return (dt is None, dt or datetime.datetime.min)

        self._scrolling_panel.Sort(key=key)

    def clear(self) -> None:
        self._scrolling_panel.clear()
