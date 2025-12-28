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
import lib.print.fonts as fonts
from lib.print.fonts import Fonts
from lib.print.decoder_base import DecoderBase

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

    def font_in_to_font(self, inches: float) -> int:
        """Convert a font height measured in inches to typographic points.

        Uses the standard 1in = 72pt conversion. This returns a point size
        that can be passed to font APIs expecting point units.
        """
        return int(round(inches * 72))

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


class Font:
    """Lightweight wrapper around a PIL font instance.

    The Font class accepts either a Fonts._Font or a string name and returns
    a callable object that can provide PIL FreeTypeFont objects adjusted to
    the configured Resolution.
    """
    def __init__(self, font: Union[Fonts, str], size: int):
        if isinstance(font, str):
            font = fonts.MAP.get(font, fonts.Arimo)
        elif isinstance(font, Fonts._Font):
            font = font
        # Fonts._Font in the unified fonts module expects device pixels; the
        # previous implementation converted point sizes via Resolution.font_to_pt
        # so preserve that behavior here.
        self._font = font(Resolution.font_to_pt(size))

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
    def new(size: Tuple, mode="RGB", color=(0, 0, 0, 0)) -> 'Image':
        size = Resolution.to_pt(size)
        img = PIL.Image.new(mode, size, color=color)
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


def _has_alpha(color: Union[Tuple[Any, ...], List[Any], int, str, None]) -> bool:
    try:
        return isinstance(color, (tuple, list)) and len(color) >= 4 and color[3] is not None and int(color[3]) < 255
    except Exception:
        return False


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

        # If semi-transparent fill or outline is provided, draw on an overlay and alpha-composite
        if _has_alpha(fill) or _has_alpha(outline):
            base = self._image
            if base.mode != 'RGBA':
                base = base.convert('RGBA')
                # Update draw context to RGBA but keep the same image reference
                self._image = base
                self._draw = PIL.ImageDraw.Draw(self._image, mode='RGBA')

            overlay = PIL.Image.new('RGBA', base.size, (0, 0, 0, 0))
            ov_draw = PIL.ImageDraw.Draw(overlay, mode='RGBA')
            ov_draw.rectangle(bbox, fill=fill, outline=outline, width=width)
            # Blend overlay onto the base without replacing the image object
            self._image.paste(overlay, (0, 0), overlay)
            return

        # Opaque colors: draw directly
        self._draw.rectangle(bbox, fill, outline, width)

    def rounded_rectangle(self, bbox: Tuple, radius: int, fill=None, outline=None, width: int = 1) -> None:
        """Draw a (possibly semi-transparent) rounded rectangle.

        Supports alpha blending by using an overlay when `fill` or `outline`
        include transparency (alpha < 255).
        """
        bbox_pt = Resolution.to_pt(bbox)
        width_pt = Resolution.to_pt(width)
        radius_pt = Resolution.to_pt(radius)
        bbox_pt = (bbox_pt[0], bbox_pt[1], bbox_pt[2], bbox_pt[3])

        if _has_alpha(fill) or _has_alpha(outline):
            base = self._image
            if base.mode != 'RGBA':
                base = base.convert('RGBA')
                self._image = base
                self._draw = PIL.ImageDraw.Draw(self._image, mode='RGBA')

            overlay = PIL.Image.new('RGBA', base.size, (0, 0, 0, 0))
            ov_draw = PIL.ImageDraw.Draw(overlay, mode='RGBA')
            try:
                ov_draw.rounded_rectangle(bbox_pt, radius=radius_pt, fill=fill, outline=outline, width=width_pt)
            except Exception:
                ov_draw.rectangle(bbox_pt, fill=fill, outline=outline, width=width_pt)
            self._image.paste(overlay, (0, 0), overlay)
            return

        # Opaque draw directly
        try:
            self._draw.rounded_rectangle(bbox_pt, radius=radius_pt, fill=fill, outline=outline, width=width_pt)
        except Exception:
            self._draw.rectangle(bbox_pt, fill=fill, outline=outline, width=width_pt)

    def rounded_rectangle_right(self, bbox: Tuple, radius: int, fill=None, outline=None, width: int = 1) -> None:
        """Draw a rectangle with only the right-side corners rounded.

        The left-side corners remain square so the shape looks like it
        enters from the left. Supports alpha blending via overlay.
        """
        bbox_pt = Resolution.to_pt(bbox)
        width_pt = Resolution.to_pt(width)
        radius_pt = Resolution.to_pt(radius)
        left, top, right, bottom = bbox_pt

        # Choose target draw surface (overlay if semi-transparent)
        use_overlay = _has_alpha(fill) or _has_alpha(outline)
        base = self._image
        if base.mode != 'RGBA':
            base = base.convert('RGBA')
            self._image = base
            self._draw = PIL.ImageDraw.Draw(self._image, mode='RGBA')

        target = self._image
        draw = self._draw
        overlay = None
        if use_overlay:
            overlay = PIL.Image.new('RGBA', base.size, (0, 0, 0, 0))
            draw = PIL.ImageDraw.Draw(overlay, mode='RGBA')

        # Build shape: left square body + right vertical body + two quarter circles
        # Left body (square corners)
        draw.rectangle((left, top, max(left, right - radius_pt), bottom), fill=fill, outline=outline, width=width_pt)
        # Right vertical middle body
        if bottom - top > 2 * radius_pt:
            draw.rectangle((max(left, right - radius_pt), top + radius_pt, right, bottom - radius_pt), fill=fill, outline=outline, width=width_pt)
        # Top-right quarter circle
        tr = (right - 2 * radius_pt, top, right, top + 2 * radius_pt)
        try:
            draw.pieslice(tr, start=270, end=360, fill=fill, outline=outline)
        except Exception:
            # Fallback: small rounded rectangle
            draw.ellipse(tr, fill=fill, outline=outline)
        # Bottom-right quarter circle
        br = (right - 2 * radius_pt, bottom - 2 * radius_pt, right, bottom)
        try:
            draw.pieslice(br, start=0, end=90, fill=fill, outline=outline)
        except Exception:
            draw.ellipse(br, fill=fill, outline=outline)

        # Composite overlay if used
        if overlay is not None:
            self._image.paste(overlay, (0, 0), overlay)

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

        lines = []
        current = ""
        for token in tokens:
            candidate = f"{current} {token}" if current else token
            bbox = self.textbbox(candidate, (0, 0), font)
            if bbox.width > width and current:
                lines.append(current)
                current = token
            else:
                current = candidate
        if current:
            lines.append(current)
        return "\n".join(lines)

class DrawDecoder(DecoderBase):
    def __init__(self):
        super().__init__()

    def draw(self, obj):
        """Draw an object and yield results.
        
        If the handler returns a generator, yield from it.
        Otherwise, yield the single result.
        """
        type_ = type(obj)
        handler = self.get_handler(type_)
        if handler is not None:
            ret = handler(obj)
        elif hasattr(obj, '__draw__'):
            ret = obj.__draw__()
        else:
            raise ValueError(f"Unsuported Type {type_}")
        
        # Check if ret is a generator/iterator
        if hasattr(ret, '__iter__') and not isinstance(ret, (str, bytes, PIL.Image.Image)):
            yield from ret
        else:
            yield ret


    @property
    def dpi(self) -> int:
        return Resolution.dpi

    @dpi.setter
    def dpi(self, value) -> None:
        Resolution.dpi = value

if __name__ == "__main__":
    print(Resolution.to_pt(("12.5in", 12, "12.2px")))
    print(Resolution.to_pt("12.5mm"))
    print(Resolution.to_pt("12.5cm"))
    print(Resolution.to_pt("12.5px"))
    print(Resolution.to_pt("12.512"))
