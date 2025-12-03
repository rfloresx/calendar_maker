import wx
import wx.lib.scrolledpanel as scrolled

from typing import List, Tuple, Any

try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

from lib.filemanager import FilesManager
import PIL.Image
import lib.pycal as libpycal


def get_image_metadata(image: str) -> dict:
    import json
    import piexif

    result = {}
    try:
        with PIL.Image.open(image) as im:
            exif_bytes = im.info.get("exif")
            if not exif_bytes:
                return result

            exif_dict = piexif.load(exif_bytes)
            exif = exif_dict.get('Exif', {})

            # DateTimeOriginal (may be bytes)
            dto = exif.get(piexif.ExifIFD.DateTimeOriginal, None)
            if isinstance(dto, bytes):
                try:
                    dto = dto.decode('utf-8')
                except Exception:
                    dto = str(dto)
            result["DateTimeOriginal"] = dto

            gps = exif_dict.get('GPS', {})
            result["GPSInfo"] = gps

            # Helper to convert rationals to float
            def _rat2float(rat):
                try:
                    return float(rat[0]) / float(rat[1]) if rat[1] != 0 else 0.0
                except Exception:
                    return 0.0

            def _dms_to_deg(dms):
                # dms is a tuple of 3 rationals: (deg, min, sec)
                deg = _rat2float(dms[0])
                minutes = _rat2float(dms[1])
                seconds = _rat2float(dms[2])
                return deg + minutes / 60.0 + seconds / 3600.0

            # Parse latitude and longitude if present
            try:
                lat_tuple = gps.get(piexif.GPSIFD.GPSLatitude)
                lat_ref = gps.get(piexif.GPSIFD.GPSLatitudeRef)
                lon_tuple = gps.get(piexif.GPSIFD.GPSLongitude)
                lon_ref = gps.get(piexif.GPSIFD.GPSLongitudeRef)

                latitude = None
                longitude = None
                if lat_tuple and lat_ref and lon_tuple and lon_ref:
                    latitude = _dms_to_deg(lat_tuple)
                    if isinstance(lat_ref, bytes):
                        lat_ref = lat_ref.decode('utf-8', errors='ignore')
                    if lat_ref and lat_ref.upper() == 'S':
                        latitude = -abs(latitude)

                    longitude = _dms_to_deg(lon_tuple)
                    if isinstance(lon_ref, bytes):
                        lon_ref = lon_ref.decode('utf-8', errors='ignore')
                    if lon_ref and lon_ref.upper() == 'W':
                        longitude = -abs(longitude)

                    result['latitude'] = latitude
                    result['longitude'] = longitude

                # Altitude (optional)
                alt = gps.get(piexif.GPSIFD.GPSAltitude)
                if alt is not None:
                    try:
                        result['altitude'] = _rat2float(alt)
                    except Exception:
                        pass
            except Exception:
                # keep best-effort behavior; don't raise on malformed GPS
                print("Failed to parse GPS info")
                pass

            # debug print if needed
            # print(json.dumps(exif_dict, indent=4, default=str))
    except Exception:
        # Failed to open image or parse EXIF; return whatever we have so far
        pass

    return result


class ImageButton(wx.Button):
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
        path = OpenDialog.ChoseFile(self, "Choose Image", OpenDialog.IMAGES)
        if path:
            self.set_image(path)

    def set_image(self, filename: str) -> None:
        print(f"Setting image: {filename}") 
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
            parent : wx.Window = self.GetParent()
            if parent is not None:
                if hasattr(parent, 'on_image_changed'):
                    parent.on_image_changed(filename)
                parent.Layout()
        except Exception:
            pass

    @property
    def metadata(self) -> dict:
        return self._metadata

    @property
    def filename(self) -> str:
        return self._filename

    def ResetBitmap(self) -> None:
        bmp = wx.Bitmap(*self._size)
        self.SetBitmap(bmp)


# class NumberText(wx.TextCtrl):
#     def __init__(self, value: int = None, on_change=None, *args, **kw):
#         super().__init__(*args, **kw)
#         self._on_change = on_change
#         if value:
#             self.SetValue(str(value))
#         self.Bind(wx.EVT_TEXT, self._validate)
    
#     def _validate(self, event: wx.CommandEvent) -> None:
#         if self._lines is None:
#             return
#         lines: int = self.GetNumberOfLines()
#         if lines > self._lines:
#             # Get the content of the TextCtrl up to the third line
#             value: str = self.GetValue()
#             content: List[str] = value.splitlines()[:self._lines]
#             self.SetValue("\n".join(content))
#             self.SetInsertionPointEnd()  # Move cursor to the end

class Text(wx.TextCtrl):
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
    def __init__(self, value :int = 0, on_change=None, *args, **kw):
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
    def __init__(self, parent, *args, **kargs):
        super().__init__(parent, *args, **kargs)
        self.SetAutoLayout(1)
        self.SetupScrolling()
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self._sizer)

    def Items(self) -> List[wx.Window]:
        return [item.GetWindow() for item in self._sizer.GetChildren()]

    def Insert(self, items: List[wx.Window]) -> None:
        for item in items:
            self._sizer.Add(item)
        self.Refresh()

    def Add(self, item: wx.Window) -> None:
        self._sizer.Add(item)
        self.Refresh()

    def Refresh(self, eraseBackground: bool = True, rect: Any = None):
        self.Layout()
        super().Refresh(eraseBackground, rect)
        self.SetupScrolling()

    def clear(self) -> None:
        self._sizer.Clear(True)
        self.Refresh()

    def Sort(self, key) -> None:
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
        val = self._sizer.Detach(item)


class OpenDialog:
    IMAGES = "Image files (*.png;*.jpg;*.jpeg;*.bmp)|*.png;*.jpg;*.jpeg;*.bmp"
    JSON = "Project files (*.json)|*.json"
    ICS = "ICS files (*.ics)|*.ics"

    def __init__(self):
        pass

    @staticmethod
    def ChoseFile(parent, title, wildcard="", style=wx.FD_OPEN) -> str:
        fileDialog: wx.FileDialog = None
        with wx.FileDialog(parent, title, wildcard=wildcard, style=style) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_OK:
                return fileDialog.GetPath()
        return None

    @staticmethod
    def ChoseFiles(parent, title, wildcard="", style=wx.FD_OPEN | wx.FD_MULTIPLE) -> List[str]:
        fileDialog: wx.FileDialog = None
        with wx.FileDialog(parent, title, wildcard=wildcard, style=style) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_OK:
                return fileDialog.GetPaths()
        return None

    @staticmethod
    def ChoseDir(parent, title, wildcard="", style=wx.DD_DEFAULT_STYLE) -> str:
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
