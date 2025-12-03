"""Low-level drawing utilities and resolution helpers.

This module provides a small abstraction over PIL for working with printable
units (in, mm, px), bounding boxes and drawing primitives. Public types
include Resolution (unit conversion), BBox, Fonts, Font, Image, Draw and
DrawDecoder which is used by higher-level print modules to register
rendering functions for application objects.
"""

import os
import re

import PIL.FontFile
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
from typing import Iterable, List, Tuple, Union, Any

PRINT_DPI = 300


class Units:
    IN = "in"
    MM = "mm"
    CM = "cm"
    PX = "px"
    NONE = "none"


class _Resolution:
    """Conversion utility between measurement units and printer points.

    The Resolution instance exposes to_pt/pt_to helpers and allows selecting
    a default unit (Resolution.unit) and a DPI to perform conversions that
    are consistent across the drawing code.
    """
    NUMBER = r"[-+]?[0-9]*\.?[0-9]+"
    FMT_EXP = re.compile(f"({NUMBER})([a-z]*)")

    def __init__(self):
        self._dpi = PRINT_DPI
        self._unit = Units.NONE
        self._default = self.none_to_pt
        self._revert = self.none_to_pt

    @property
    def dpi(self) -> int:
        """Return the configured DPI used for conversions."""
        return self._dpi

    @property
    def unit(self) -> str:
        """Return the current default unit (one of Units)."""
        return self._unit

    @unit.setter
    def unit(self, unit: str) -> None:
        """Set the default unit used by to_pt/pt_to conversions.

        The setter locates the corresponding conversion functions and uses
        them for subsequent calls to Resolution.to_pt and Resolution.pt_to.
        """
        if unit:
            fn = getattr(self, f"{unit}_to_pt")
            fn2 = getattr(self, f"pt_to_{unit}")
            self._default = fn
            self._revert = fn2
            self._unit = unit

    @dpi.setter
    def dpi(self, value) -> None:
        """Set the DPI value used for unit conversions."""
        self._dpi = int(value)

    def none_to_pt(self, val: float) -> int:
        """Identity conversion when no unit is set."""
        return int(val)

    def mm_to_in(self, mm: float) -> float:
        return mm / 25.4

    def font_to_pt(self, font_size: int) -> int:
        """Convert font size in points to device pixels using current DPI."""
        return int((font_size/72)*self._dpi)

    def in_to_pt(self, inches: float) -> int:
        """Convert inches to printer points (pixels) using DPI."""
        return int(inches*self._dpi)
    
    def pt_to_in(self, pt: int) -> float:
        return float(pt/self._dpi)

    def mm_to_pt(self, mm: float) -> int:
        return self.in_to_pt(self.mm_to_in(mm))

    def cm_to_pt(self, cm: float) -> int:
        return self.mm_to_pt(cm*10)

    def px_to_pt(self, px: float) -> int:
        return self.in_to_pt(px*96)

    def pt_to_pt(self, val: float) -> int:
        return int(val)

    def _to_pt(self, val: float) -> int:
        return self._default(val)

    def _pt_to(self, val: int) -> float:
        return self._revert(val)

    def to_pt(self, *value: str) -> int:
        """Convert the provided value(s) to points using the configured unit.

        Accepts numeric values, tuple/list of values, or strings with units
        (e.g. '12.5in', '20mm'). Returns an int or a tuple/list of ints
        matching the input shape.
        """
        if len(value) == 1:
            value = value[0]
        if isinstance(value, (float, int)):
            return self._to_pt(value)
        elif isinstance(value, (tuple, list)):
            val = []
            for v in value:
                val.append(self.to_pt(v))
            t = type(value)
            return t(val)
        m = Resolution.FMT_EXP.match(value)
        if m:
            fn = getattr(self, f"{m.group(2)}_to_pt")
            return fn(float(m.group(1)))
        return 0

    def pt_to(self, *value: str) -> int:
        """Convert points back to the configured unit or to a numeric value.

        Mirrors to_pt but performs the inverse conversion using the selected
        unit.
        """
        if len(value) == 1:
            value = value[0]
        if isinstance(value, (float, int)):
            return self._pt_to(value)
        elif isinstance(value, (tuple, list)):
            val = []
            for v in value:
                val.append(self.pt_to(v))
            t = type(value)
            return t(val)
        m = Resolution.FMT_EXP.match(value)
        if m:
            fn = getattr(self, f"pt_to_{m.group(2)}")
            return fn(float(m.group(1)))
        return 0

Resolution = _Resolution()


class BBox(tuple):
    """Tuple-like bounding box with convenience accessors.

    BBox instances store (left, top, right, bottom) coordinates and expose
    properties for width/height/center and simple geometry helpers move()
    and shrink().
    """
    @staticmethod
    def new(x, y, w, h) -> 'BBox':
        return BBox(x, y, x + w, y + h)

    def __new__(self, *args):
        if len(args) == 1:
            args = args[0]
        if len(args) != 4:
            raise TypeError(f"Failed to create bbox from {args}")
        return tuple.__new__(BBox, args)
    @property
    def left(self) -> int:
        return self[0]

    @property
    def top(self) -> int:
        return self[1]

    @property
    def right(self) -> int:
        return self[2]

    @property
    def bottom(self) -> int:
        return self[3]

    @property
    def x(self) -> int:
        return self[0]

    @property
    def y(self) -> int:
        return self[1]

    @property
    def width(self) -> int:
        return self[2] - self[0]

    @property
    def height(self) -> int:
        return self[3] - self[1]

    @property
    def center(self):
        if len(self) == 4:
            left = self[0]
            top = self[1]
            right = self[2]
            bot = self[3]

            w = right - left
            h = bot - top

            x = left + w/2
            y = top + h/2
            return (x, y)
        return self

    def move(self, *pos) -> "BBox":
        if len(pos) == 1:
            pos = pos[0]
        x = pos[0]
        y = pos[1]

        return BBox(self[0]+x, self[1]+y, self[2]+x, self[3]+y)

    def shrink(self, val) -> "BBox":
        return BBox(self[0] + val, self[1] + val, self[2] - val, self[3] - val)


class Fonts:
    """Convenience font factory mapping logical names to font files.

    Fonts._Font instances are callable to produce PIL FreeType fonts at the
    configured resolution via Resolution.font_to_pt().
    """
    RES_DIR: str = os.path.dirname(os.path.realpath(__file__))
    FONTS_DIR: str = os.path.join(RES_DIR, 'fonts')

    @staticmethod
    def open(fontname, size=10) -> PIL.ImageFont.FreeTypeFont:
        return PIL.ImageFont.truetype(os.path.join(Fonts.FONTS_DIR, fontname), size=size)

    class _Font:
        def __init__(self, name) -> None:
            self._name = name
            self._filename = f"{name}.ttf"

        @property
        def name(self) -> str:
            return self._name

        def __call__(self, size=12) -> PIL.ImageFont.FreeTypeFont:
            return Fonts.open(self._filename, Resolution.font_to_pt(size))

        def __str__(self) -> str:
            return self._name

        def __repr__(self) -> str:
            return f'{self.__class__.__name__}({self._name})'

    Arial_Bold_Italic = _Font('Arial_Bold_Italic')
    Arial_Bold = _Font('Arial_Bold')
    Arial_Italic = _Font('Arial_Italic')
    Arial = _Font('Arial')
    Courier_New = _Font('Courier_New')
    Verdana_Bold_Italic = _Font('Verdana_Bold_Italic')
    Verdana_Bold = _Font('Verdana_Bold')
    Verdana_Italic = _Font('Verdana_Italic')
    Verdana = _Font('Verdana')
    EBGaramond = _Font('EBGaramond')
    EBGaramond_Bold = _Font('EBGaramond_Bold')
    Helvetica = _Font('Helvetica')
    Helvetica_Bold = _Font('Helvetica_Bold')

    MAP = {
        Arial_Bold_Italic.name: Arial_Bold_Italic,
        Arial_Bold.name: Arial_Bold,
        Arial_Italic.name: Arial_Italic,
        Arial.name: Arial,
        Courier_New.name: Courier_New,
        Verdana_Bold_Italic.name: Verdana_Bold_Italic,
        Verdana_Bold.name: Verdana_Bold,
        Verdana_Italic.name: Verdana_Italic,
        Verdana.name: Verdana
    }

    @classmethod
    def fonts(cls) -> Iterable['Fonts._Font']:
        for val in cls.__dict__.values():
            if isinstance(val, Fonts._Font):
                yield val


class Font:
    """Lightweight wrapper around a PIL font instance.

    The Font class accepts either a Fonts._Font or a string name and returns
    a callable object that can provide PIL FreeTypeFont objects adjusted to
    the configured Resolution.
    """
    def __init__(self, font: Union[Fonts, str], size: int):
        if isinstance(font, str):
            font = Fonts.MAP.get(font, Fonts.Arial)
        elif isinstance(font, Fonts._Font):
            font = font
        self._font = font(size)

    @property
    def font(self) -> PIL.ImageFont.FreeTypeFont:
        return self._font

    def getbbox(self, text, anchor=None):
        bbox = Resolution.pt_to(self._font.getbbox(text=text, anchor=anchor))
        return BBox(bbox)

        # return Resolution._revert

    def ToImage(self, text, fill) -> PIL.Image.Image:
        bbox = self._font.getbbox(text)
        img = PIL.Image.new('RGBA', (bbox[2], bbox[3]), color=(0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(img)
        draw.text((0, 0), text, fill=fill, font=self._font)
        return img

    def Draw(self,
             target: PIL.Image.Image,
             text: str, xy,
             fill=None,
             anchor=None,
             spacing=4,
             align="left",
             direction=None,
             features=None,
             language=None,
             stroke_width=0,
             stroke_fill=None,
             embedded_color=False) -> None:
        draw = PIL.ImageDraw.Draw(target)
        draw.text(xy, text, fill, self._font, anchor, spacing, align, direction,
                  features, language, stroke_width, stroke_fill, embedded_color)


def _resize_to_cover(image: PIL.Image.Image, bbox: Tuple):
    if len(bbox) == 2:
        bbox = (0, 0, bbox[0], bbox[1])
    # Bounding box: (left, upper, right, lower)
        left, upper, right, lower = bbox
    bbox_width = right - left
    bbox_height = lower - upper

    # Get the image size
    img_width, img_height = image.size

    # Calculate aspect ratios
    img_aspect_ratio = img_width / img_height
    bbox_aspect_ratio = bbox_width / bbox_height

    # Resize image to cover the bbox area (like object-fit: cover in CSS)
    if img_aspect_ratio > bbox_aspect_ratio:
        # Image is wider than the bounding box
        new_height = bbox_height
        new_width = int(new_height * img_aspect_ratio)
    else:
        # Image is taller than the bounding box
        new_width = bbox_width
        new_height = int(new_width / img_aspect_ratio)

    # Resize the image
    resized_image = image.resize(
        (new_width, new_height), PIL.Image.Resampling.LANCZOS)

    # Calculate the position to crop the image to fit inside the bbox
    left_offset = (new_width - bbox_width) // 2
    top_offset = (new_height - bbox_height) // 2

    # Crop the image to fit the bounding box
    cropped_image = resized_image.crop(
        (left_offset, top_offset, left_offset + bbox_width, top_offset + bbox_height))

    return cropped_image


def _resize_cover(image: PIL.Image.Image, size: tuple) -> PIL.Image.Image:
    """Resize an image to cover the target size, maintaining aspect ratio."""
    width, height = image.size
    orig_ratio = width / height

    target_width, target_height = size

    # Determine which dimension to scale
    if orig_ratio > 1:
        new_width = target_width
        new_height = int(target_width/orig_ratio)
    else:
        new_height = target_height
        new_width = int(target_height * orig_ratio)

    # Resize and crop
    resized_image = image.resize(
        (new_width, new_height), PIL.Image.Resampling.LANCZOS)
    x_offset = (new_width - target_width) // 2
    y_offset = (new_height - target_height) // 2
    cropped_image = resized_image.crop(
        (x_offset, y_offset, x_offset + target_width, y_offset + target_height))

    return cropped_image


class Image:
    @staticmethod
    def new(size: Tuple, color=(0, 0, 0, 0)) -> 'Image':
        size = Resolution.to_pt(size)
        img = PIL.Image.new('RGB', size, color=color)
        return Image(image=img)

    def __init__(self, image: str = None):
        if isinstance(image, str):
            self._image: PIL.Image.Image = PIL.Image.open(image)
        elif isinstance(image, PIL.Image.Image):
            self._image = image
        else:
            raise TypeError(f"Invalid type {type(image)}")

    @property
    def image(self) -> PIL.Image.Image:
        return self._image

    def convert(self, mode) -> None:
        self._image = self._image.convert(mode=mode)

    def resize(self, size: Tuple) -> None:
        size = Resolution.to_pt(size)
        self._image = _resize_to_cover(self._image, size)

    def crop(self, box: Tuple) -> None:
        val = Resolution.to_pt(box)

        if len(val) == 2:
            box = (0, 0, val[0], val[1])
        else:
            box = val
        self._image = self._image.crop(box)

    def ToImage(self) -> PIL.Image.Image:
        return self._image

    def Draw(self, image: PIL.Image.Image, box: Tuple) -> None:
        box = Resolution.to_pt(box)
        image.paste(self._image, box)


class Draw:
    def __init__(self, image: PIL.Image.Image):
        if isinstance(image, Image):
            image = image.image
        self._image = image

        self._draw = PIL.ImageDraw.Draw(self._image, mode='RGBA')

    def rectangle(self, bbox: Tuple, fill=None, outline=None, width: int = 1) -> None:
        bbox = Resolution.to_pt(bbox)
        width = Resolution.to_pt(width)
        bbox = (bbox[0], bbox[1], bbox[2], bbox[3])
        self._draw.rectangle(bbox, fill, outline, width)

    def paste(self, im: PIL.Image.Image, box: tuple, mask: Any = None):
        if isinstance(im, Image):
            im = im.image
        if isinstance(mask, Image):
            mask = mask.image
        box = Resolution.to_pt(box)
        self._image.paste(im, box, mask)

    def text(self,
             text: str,
             xy,
             font,
             fill=None,
             anchor=None,
             spacing='4pt',
             align="left",
             direction=None,
             features=None,
             language=None,
             stroke_width=0,
             stroke_fill=None,
             embedded_color=False) -> None:
        xy = Resolution.to_pt(xy)
        spacing = Resolution.to_pt(spacing)
        if isinstance(font, Font):
            font = font.font
        self._draw.text(xy, text, fill, font, anchor, spacing, align, direction,
                        features, language, stroke_width, stroke_fill, embedded_color)

    def textbbox(self, text, xy, font=None, anchor=None, spacing="4pt", align='left', direction=None, features=None, language=None, stroke_width=0, embedded_color=False):
        xy = Resolution.to_pt(xy)
        spacing = Resolution.to_pt(spacing)
        if isinstance(font, Font):
            font = font.font

        bbox = self._draw.multiline_textbbox(xy, text, font, anchor, spacing, align, direction, features, language, stroke_width, embedded_color)
        bbox = Resolution.pt_to(bbox)
        return BBox(bbox)

    def get_multiline_text(self, text : str, width : int, font) -> str:
        tokens = text.split(" ")
        
        result = ""
        for token in tokens:
            # print(token)
            bbox = self.textbbox(f"{result} {token}", (0,0), font)
            if bbox.width > width:
                result += "\n"+token
            else:
                result = f"{result} {token}"
        return result

class DrawDecoder:
    def __init__(self):
        self._handlers = {}

    def draw(self, obj) -> PIL.Image.Image:
        type_ = type(obj)
        ret = None
        if type_ in self._handlers:
            ret = self._handlers[type_](obj)
        elif hasattr(obj, '__draw__'):
            ret = obj.__draw__()
        else:
            raise ValueError(f"Unsuported Type {type_}")
        return ret

    def override(self, _type: type):
        def handler(func):
            self._handlers[_type] = func
            return func
        return handler

    @property
    def dpi(self) -> int:
        return Resolution.dpi

    @dpi.setter
    def dpi(self, value) -> None:
        Resolution.dpi = value

if __name__ == "__main__":
    # font = Font(Fonts.Arial, 8)
    # img = font.ToImage("Hello World", 'red')
    # img.show()
    # h = ['l', 'm', 'r']
    # v = ['a', 'm', 'd']
    # for a in h:
    #     for b in v:
    #         font.Draw("Hello World", direction='ttb', anchor=f'{a}{b}')

    print(Resolution.to_pt(("12.5in", 12, "12.2px")))
    print(Resolution.to_pt("12.5mm"))
    print(Resolution.to_pt("12.5cm"))
    print(Resolution.to_pt("12.5px"))
    print(Resolution.to_pt("12.512"))
