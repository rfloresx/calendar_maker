"""Utility GUI components and helpers used by the editor.

This module provides small helper controls (ImageButton, Text, NumberText,
ScrolledPanel), file chooser helpers and image metadata extraction used
throughout the GUI.
"""

import wx
import wx.lib.scrolledpanel as scrolled

from typing import List, Tuple, Any, Optional

try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

from lib.filemanager import FilesManager
import lib.gui.geoutil as geoutil
import PIL.Image
import lib.pycal as libpycal
import piexif
import datetime


def get_image_metadata(image: str) -> dict:
    """Extract basic EXIF metadata (DateTimeOriginal, GPS) from an image file.

    Returns a dictionary with any discovered keys. Best-effort: failures
    return an empty dict instead of raising.
    """

    result = {}
    try:
        # Fast path: let piexif parse the file directly when possible (e.g., JPEG)
        try:
            exif_dict = piexif.load(image)
            exif = exif_dict.get('Exif', {})

            dto = exif.get(piexif.ExifIFD.DateTimeOriginal, None)
            if isinstance(dto, bytes):
                try:
                    dto = dto.decode('utf-8')
                except Exception:
                    dto = str(dto)
            if dto is not None:
                result["DateTimeOriginal"] = dto

            lat, lon, alt = gps_from_exif(exif_dict)
            if lat is not None and lon is not None:
                result["GPSLatitude"] = lat
                result["GPSLongitude"] = lon
            if alt is not None:
                result["GPSAltitude"] = alt
            return result
        except Exception:
            pass

        # Fallback: open with PIL and extract embedded EXIF bytes
        with PIL.Image.open(image) as im:
            exif_bytes = im.info.get("exif")
            if not exif_bytes:
                return result

            exif_dict = piexif.load(exif_bytes)
            exif = exif_dict.get('Exif', {})

            dto = exif.get(piexif.ExifIFD.DateTimeOriginal, None)
            if isinstance(dto, bytes):
                try:
                    dto = dto.decode('utf-8')
                except Exception:
                    dto = str(dto)
            if dto is not None:
                result["DateTimeOriginal"] = dto

            lat, lon, alt = gps_from_exif(exif_dict)
            if lat is not None and lon is not None:
                result["GPSLatitude"] = lat
                result["GPSLongitude"] = lon
            if alt is not None:
                result["GPSAltitude"] = alt
    except Exception:
        # Failed to open image or parse EXIF; return whatever we have so far
        pass

    return result


def _rat2float(r):
    try:
        n, d = r
        return float(n) / float(d) if d else 0.0
    except Exception:
        return float(r) if isinstance(r, (int, float)) else 0.0


def _dms_to_deg(dms):
    deg = _rat2float(dms[0])
    minutes = _rat2float(dms[1])
    seconds = _rat2float(dms[2]) if len(dms) > 2 else 0.0
    return deg + minutes / 60.0 + seconds / 3600.0


def gps_from_exif(exif_dict) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    gps = exif_dict.get("GPS", {}) or {}
    # normalize keys to ints
    norm = {}
    for k, v in gps.items():
        ik = int(k) if isinstance(k, str) and k.isdigit() else k
        norm[ik] = v

    def decode_ref(x: Any):
        if isinstance(x, bytes):
            return x.decode(errors="ignore")
        if isinstance(x, (tuple, list)) and len(x) == 1 and isinstance(x[0], bytes):
            return x[0].decode(errors="ignore")
        return x

    lat = lon = alt = None
    lat_ref = decode_ref(norm.get(piexif.GPSIFD.GPSLatitudeRef) or norm.get(1))
    lon_ref = decode_ref(
        norm.get(piexif.GPSIFD.GPSLongitudeRef) or norm.get(3))
    lat_val = norm.get(piexif.GPSIFD.GPSLatitude) or norm.get(2)
    lon_val = norm.get(piexif.GPSIFD.GPSLongitude) or norm.get(4)
    if lat_val and lat_ref and lon_val and lon_ref:
        lat = _dms_to_deg(lat_val)
        lon = _dms_to_deg(lon_val)
        if str(lat_ref).upper().startswith("S"):
            lat = -abs(lat)
        if str(lon_ref).upper().startswith("W"):
            lon = -abs(lon)
    alt_val = norm.get(piexif.GPSIFD.GPSAltitude) or norm.get(6)
    if alt_val is not None:
        alt = _rat2float(alt_val)
    return lat, lon, alt


class ImageInfo():
    """Simple container for image filename and metadata dictionary."""

    def __init__(self, filename: str = None, metadata: dict = None):
        self.filename = filename
        self.metadata = metadata if metadata is not None else {}

    @property
    def datetime_original(self) -> Optional[datetime.datetime]:
        """Return the DateTimeOriginal datetime from metadata or None."""
        dto = self.metadata.get("DateTimeOriginal", None)
        if dto is not None and isinstance(dto, bytes):
            try:
                dto = dto.decode('utf-8')
            except Exception:
                dto = str(dto)
        if dto:
            try:
                return datetime.datetime.strptime(dto, '%Y:%m:%d %H:%M:%S')
            except (ValueError, TypeError):
                return None
        return None

    @property
    def places(self) -> List[geoutil.PlaceInfo]:
        """Return a list of places associated with the image metadata."""
        geo_util = geoutil.get_singleton_geo_util()
        lat = self.metadata.get("GPSLatitude", None)
        lon = self.metadata.get("GPSLongitude", None)
        if lat is not None and lon is not None:
            places = geo_util.get_nearby_places(lat=lat, lng=lon)
            if places:
                return places
        return []

    def __str__(self):
        return f"ImageInfo(filename={self.filename}, metadata={self.metadata})"


class ImageButton(wx.Button):
    """Button control that displays an image and allows changing it.

    The ImageButton stores the image filename and extracted metadata and
    will copy selected images into the project via FilesManager.
    """

    def __init__(self, image: str = None, *args, **kw):
        super().__init__(*args, **kw)
        self._size: Tuple[int, int] = kw.get('size')
        if self._size is None:
            self._size = (100, 100)
        # Initialize filename and metadata defaults
        self._filename: str = None
        self._metadata: dict = {}

        if image:
            self._filename = FilesManager.instance().add_file(image)
            self._metadata = get_image_metadata(self._filename)
            img = wx.Image(self._filename, wx.BITMAP_TYPE_ANY)
            img = img.Scale(*self._size)
            bmp = wx.Bitmap(img)
        else:
            bmp = wx.Bitmap(*self._size)

        self.SetBitmap(bmp)
        self.Bind(wx.EVT_BUTTON, self.on_set_image)

    def on_set_image(self, event) -> None:
        """Open a file chooser to select a new image and set it."""
        path = OpenDialog.ChoseFile(self, "Choose Image", OpenDialog.IMAGES)
        if path:
            self.set_image(path)

    def set_image(self, filename: str) -> None:
        """Set the control's image, copy it into the project and extract metadata."""
        if filename is None:
            self.ResetBitmap()
            self._filename = None
            self._metadata = {}
            return
        self._filename = FilesManager.instance().add_file(filename)
        self._metadata = get_image_metadata(self._filename)

        img = wx.Image(self._filename, wx.BITMAP_TYPE_ANY)
        img = img.Scale(*self._size)
        bmp = wx.Bitmap(img)
        self.SetBitmap(bmp)
        # Ensure the control and its parent are redrawn/laid out so bitmap and metadata are visible
        try:
            self.Refresh()
            self.Update()
            parent: wx.Window = self.GetParent()
            if parent is not None:
                if hasattr(parent, 'on_image_changed'):
                    parent.on_image_changed(filename)
                parent.Layout()
        except Exception:
            pass

    @property
    def image_info(self) -> ImageInfo:
        """Return an ImageInfo object with the current filename and metadata."""
        return ImageInfo(filename=self._filename, metadata=self._metadata)

    @property
    def metadata(self) -> dict:
        """Return metadata dictionary extracted from the image (may be empty)."""
        return self._metadata

    @property
    def filename(self) -> str:
        """Return current image filename (project path) or None."""
        return self._filename

    def ResetBitmap(self) -> None:
        """Reset the button to an empty bitmap of the configured size."""
        bmp = wx.Bitmap(*self._size)
        self.SetBitmap(bmp)


class Text(wx.TextCtrl):
    """Small Text control that optionally limits the number of lines.

    When attached inside a ScrolledPanel the mouse wheel will be propagated
    to the parent scrolling container to enable expected scroll behavior.
    """

    def __init__(self, value: str = None, lines: int = None, *args, **kw):
        if 'style' not in kw:
            kw['style'] = wx.TE_MULTILINE | wx.TE_NO_VSCROLL
        super().__init__(*args, **kw)
        if value:
            self.SetValue(value)
        self.Bind(wx.EVT_TEXT, self._validate)
        self._lines: int = lines
        self._scroll_panel: wx.Window = self.GetParent()
        while self._scroll_panel is not None and not self._scroll_panel.CanScroll(wx.VERTICAL):
            self._scroll_panel = self._scroll_panel.GetParent()
        if self._scroll_panel is not None:
            self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)

    def on_mouse_wheel(self, event: wx.CommandEvent) -> None:
        event.ResumePropagation(wx.EVENT_PROPAGATE_MAX)
        event.Skip()
        event.SetEventObject(self._scroll_panel)

    def _validate(self, event: wx.CommandEvent) -> None:
        if self._lines is None:
            return
        lines: int = self.GetNumberOfLines()
        if lines > self._lines:
            # Get the content of the TextCtrl up to the third line
            value: str = self.GetValue()
            content: List[str] = value.splitlines()[:self._lines]
            self.SetValue("\n".join(content))
            self.SetInsertionPointEnd()  # Move cursor to the end


class NumberText(Text):
    """Text control that restricts input to a single integer and calls a callback."""

    def __init__(self, value: int = 0, on_change=None, *args, **kw):
        super().__init__(str(value), lines=1, *args, **kw)
        self._on_change = on_change
        self._last_value = value

    def _validate(self, event: wx.CommandEvent) -> None:
        val = self.GetValue()
        value_str = val.strip()
        if not value_str:
            value_str = ""

        try:
            if value_str:
                value = int(value_str)
            else:
                value = 0
            if self._on_change:
                self._on_change(value)
            self._last_value = value
        except:
            value_str = str(self._last_value)

        if value_str != val:
            self.SetValue(value_str)
        super()._validate(event)

class ScrolledPanel(scrolled.ScrolledPanel):
    """Thin wrapper that makes adding/removing child widgets simpler.

    Exposes Items(), Add(), Insert(), Sort(), Remove() and clear() helpers
    operating on the underlying vertical sizer.
    """

    def __init__(self, parent, *args, **kargs):
        super().__init__(parent, *args, **kargs)
        self.SetAutoLayout(1)
        self.SetupScrolling()
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._sizer)

    def Items(self) -> List[wx.Window]:
        """Return the list of child window objects currently in the sizer."""
        return [item.GetWindow() for item in self._sizer.GetChildren()]

    def Insert(self, items: List[wx.Window]) -> None:
        """Insert one or more windows into the sizer."""
        for item in items:
            self._sizer.Add(item)
        self.Refresh()

    def Add(self, item: wx.Window) -> None:
        """Add a single window to the sizer and refresh the panel."""
        self._sizer.Add(item)
        self.Refresh()

    def Refresh(self, eraseBackground: bool = True, rect: Any = None):
        self.Layout()
        super().Refresh(eraseBackground, rect)
        self.SetupScrolling()

    def clear(self) -> None:
        """Remove and destroy all child widgets from the sizer."""
        self._sizer.Clear(True)
        self.Refresh()

    def Sort(self, key) -> None:
        """Sort child widgets in the sizer using the provided key function."""
        children: List[wx.SizerItem] = self._sizer.GetChildren()
        items = []
        for child in children:
            widget = child.GetWindow()
            items.append(widget)
            self._sizer.Detach(widget)

        sortedItems = sorted([it for it in items], key=key)
        for item in sortedItems:
            self._sizer.Add(item)
        self.Refresh()

    def Remove(self, item: wx.Window):
        """Detach a child widget from the sizer without destroying it."""
        val = self._sizer.Detach(item)


class OpenDialog:
    IMAGES = "Image files (*.png;*.jpg;*.jpeg;*.bmp)|*.png;*.jpg;*.jpeg;*.bmp"
    JSON = "Project files (*.json)|*.json"
    ICS = "ICS files (*.ics)|*.ics"

    def __init__(self):
        pass

    @staticmethod
    def ChoseFile(parent, title, wildcard="", style=wx.FD_OPEN) -> str:
        """Open a file chooser and return the selected path or None."""
        fileDialog: wx.FileDialog = None
        with wx.FileDialog(parent, title, wildcard=wildcard, style=style) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_OK:
                return fileDialog.GetPath()
        return None

    @staticmethod
    def ChoseFiles(parent, title, wildcard="", style=wx.FD_OPEN | wx.FD_MULTIPLE) -> List[str]:
        """Open a multi-file chooser and return the selected paths or None."""
        fileDialog: wx.FileDialog = None
        with wx.FileDialog(parent, title, wildcard=wildcard, style=style) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_OK:
                return fileDialog.GetPaths()
        return None

    @staticmethod
    def ChoseDir(parent, title, wildcard="", style=wx.DD_DEFAULT_STYLE) -> str:
        """Open a directory chooser and return the selected path or None."""
        dirDialog: wx.DirDialog = None
        with wx.DirDialog(parent, title, wildcard=wildcard, style=style) as dirDialog:
            if dirDialog.ShowModal() == wx.ID_OK:
                return dirDialog.GetPath()
        return None


class MainFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

    def get_wall_calendar(self) -> libpycal.Calendar:
        return None

    def get_desk_calendar(self) -> libpycal.Calendar:
        return None

class TextTemplate:
    def __init__(self, template: str = ""):
        self.template = template

    def render(self, context: dict) -> str:
        """Render the template using a generic key/value context mapping.

        Placeholders support optional format specifiers: {key} or {key:fmt}.
        When a format is provided and the value is a datetime, strftime(fmt)
        is applied. Otherwise the value is converted to string.
        Missing keys render as empty strings.
        """
        import re
        text = self.template or ""
        if not text:
            return text

        pattern = r"\{([A-Za-z0-9_.]+)(?::([^}]+))?\}"

        def replace(m: re.Match) -> str:
            key = m.group(1)
            fmt = m.group(2)
            value = context.get(key, "")
            # Normalize NaN floats
            try:
                if isinstance(value, float) and value != value:
                    value = ""
            except Exception:
                pass
            if fmt and isinstance(value, datetime.datetime):
                try:
                    return value.strftime(fmt)
                except Exception:
                    return ""
            return "" if value is None else str(value)

        return re.sub(pattern, replace, text)


def extract_place_info(image_info: ImageInfo, selected_place_index: int = 0, overrides: dict = None) -> dict:
    """Extract place-related variables from `image_info` with optional overrides.

    Returns a dictionary suitable for template substitution, including keys:
    - "place.name", "place.city", "place.state", "place.country",
      "place.address", "place.rating"
    - "img.date" (formatted as YYYY-MM-DD when available, else empty)

    Args:
        image_info: ImageInfo with metadata and places.
        selected_place_index: Index of the place to use from metadata.
        overrides: Optional dict providing manual values for place fields.

    Returns:
        dict mapping placeholder keys to string values.
    """
    ctx = {
        "place.name": "",
        "place.city": "",
        "place.state": "",
        "place.country": "",
        "place.address": "",
        "place.rating": "",
        "img.date": "",
    }

    # Date (ISO-style default)
    dt = getattr(image_info, "datetime_original", None)
    if dt is not None:
        try:
            ctx["img.date"] = dt.strftime("%Y-%m-%d")
        except Exception:
            ctx["img.date"] = ""

    # Place info
    if overrides and isinstance(overrides, dict) and any(v is not None and v != "" for v in overrides.values()):
        # Use provided overrides
        ctx["place.name"] = str(overrides.get("name", "") or "")
        ctx["place.city"] = str(overrides.get("city", "") or "")
        ctx["place.state"] = str(overrides.get("state", "") or "")
        ctx["place.country"] = str(overrides.get("country", "") or "")
        ctx["place.address"] = str(overrides.get("address", "") or "")
        rating = overrides.get("rating", "")
        try:
            ctx["place.rating"] = "" if (isinstance(rating, float) and rating != rating) else str(rating or "")
        except Exception:
            ctx["place.rating"] = str(rating or "")
        return ctx

    # Fallback to metadata places
    places = getattr(image_info, "places", [])
    if places:
        try:
            idx = max(0, min(int(selected_place_index), len(places) - 1))
        except Exception:
            idx = 0
        place = places[idx]
        try:
            ctx["place.name"] = str(getattr(place, "name", "") or "")
            ctx["place.city"] = str(getattr(place, "city", "") or "")
            ctx["place.state"] = str(getattr(place, "state", "") or "")
            ctx["place.country"] = str(getattr(place, "country", "") or "")
            ctx["place.address"] = str(getattr(place, "address", "") or "")
            rating = getattr(place, "rating", "")
            ctx["place.rating"] = "" if (isinstance(rating, float) and rating != rating) else str(rating or "")
        except Exception:
            pass
    # If no places, leave placeholders empty strings
    return ctx


def build_text_context(image_info: ImageInfo, selected_place_index: int = 0, overrides: dict = None, year: int = None) -> dict:
    """Build a full context dictionary for TextTemplate rendering.

    Includes place.* keys, a raw datetime under "date", a default formatted
    string under "img.date" (YYYY-MM-DD), and the optional "year" value.
    """
    ctx = extract_place_info(image_info, selected_place_index, overrides)
    # raw datetime for {date:%...}
    ctx["date"] = getattr(image_info, "datetime_original", None)
    if year is not None:
        ctx["year"] = year
    return ctx
    

