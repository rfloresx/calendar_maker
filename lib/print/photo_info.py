import PIL.Image

try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))


import lib.print.draw as _libdraw
import lib.pyimg as _pyimg

from lib.filemanager import FilesManager
from typing import Tuple

# Ensure printable units use inches for consistent sizing
_libdraw.Resolution.unit = _libdraw.Units.IN

class PhotoDrawer(_libdraw.DrawDecoder):
    """
    1:1 (Square): Ideal for social media feeds (Instagram) or classic medium format cameras.
    3:2: Standard for most full-frame and APS-C digital cameras and 35mm film, matching classic 4x6 prints.
    4:3: Common for Micro Four Thirds cameras, slightly more squarish than 3:2.
    4:5: Basis for traditional 8x10 prints and popular for vertical Instagram posts.
    16:9: Widescreen format used for TVs, monitors, and online video.
    """
    class Aspect:
        AUTO = None
        SQUARE = (1, 1)
        STANDARD = (3, 2)
        MICRO_FOUR_THIRDS = (4, 3)
        EIGHT_BY_TEN = (5, 4)
        WIDESCREEN = (16, 9)

    def __init__(self):
        super().__init__()
        self._aspect = self.Aspect.STANDARD
        self._portrait = False

    @property
    def aspect(self) -> tuple:
        return self._aspect

    @aspect.setter
    def aspect(self, value: tuple) -> None:
        self._aspect = value

    @property
    def portrait(self) -> bool:
        return self._portrait

    @portrait.setter
    def portrait(self, value: bool) -> None:
        self._portrait = value

    @property
    def size(self) -> tuple:
        if self._aspect is None:
            return (0, 0)
        w, h = self._aspect
        if self._portrait:
            w, h = h, w
        return (w, h)

ImageDrawer = PhotoDrawer()

class ImageLayout:
    def __init__(self, image: PIL.Image.Image):
        self._size = ImageDrawer.size
        if ImageDrawer.aspect is ImageDrawer.Aspect.AUTO:
            """Auto aspect ratio based on image pixel dimensions converted to inches.

            Uses the configured print DPI to convert pixels to inches:
            inches = pixels / Resolution.dpi
            """
            px_w, px_h = image.size
            dpi = _libdraw.Resolution.dpi or 300
            img_w_in = px_w / dpi
            img_h_in = px_h / dpi
            # Ensure minimum non-zero dimensions to avoid degenerate layout
            img_w_in = max(img_w_in, 0.1)
            img_h_in = max(img_h_in, 0.1)
            self._size = (img_w_in, img_h_in)

        self._page: _libdraw.Image = _libdraw.Image.new(
            size=self._size,
            mode="RGBA"
        )
        
        img = _libdraw.Image(image=image)
        img.resize(self._size)

        draw = _libdraw.Draw(self._page)
        draw.paste(img, (0,0))

    @property
    def page(self) -> _libdraw.Image:
        return self._page

    @property
    def size(self) -> tuple:
        """Return the page size in inches (width, height)."""
        return self._size

    def font(self, size: float) -> _libdraw.Font:
        # size is a fraction of the page height (inches)
        inches = self._size[1] * size
        point_size = _libdraw.Resolution.font_in_to_font(inches)
        return _libdraw.Font(_libdraw.fonts.EBGaramond_Bold, point_size)

    def size_from_percentage(self, percent: Tuple[float, float]) -> tuple:
        """Get size as a percentage of the page size."""
        return (self._size[0] * percent[0], self._size[1] * percent[1])

    def value_from_percentage_w(self, percent: float) -> float:
        """Get width value as a percentage of the page width."""
        return self._size[0] * percent

    def value_from_percentage_h(self, percent: float) -> float:
        """Get height value as a percentage of the page height."""
        return self._size[1] * percent

@ImageDrawer.override(_pyimg.BaseArt)
def DrawImage(self: _pyimg.BaseArt) -> PIL.Image.Image:
    """Draw the photo image into the given box."""
    image_path = FilesManager.instance().get_file_path(self.image)
    image = ImageLayout(PIL.Image.open(image_path))

    # Choose a readable font size relative to image height
    font_size = 0.04  # 4% of image height
    font = image.font(font_size)
    draw = _libdraw.Draw(image.page)
    text = (self.description or "").strip()

    # If there's no description, just return the image
    if not text:
        return image.page.ToImage()

    # Wrap text to fit a portion of the image width (bottom-left area)
    # Use the actual rendered page size to support AUTO aspect
    page_w_in, page_h_in = image.size
    max_text_width_in = page_w_in * 0.6
    wrapped = draw.get_multiline_text(text, max_text_width_in, font)

    # Measure wrapped text bbox without relying on anchor (multiline)
    tmp_bbox = draw.textbbox(wrapped, (0, 0), font)

    # Layout: bottom-left with margin and padded background
    # Use fractions of page size to avoid negative positions under AUTO
    margin_x_in = font_size * 0.0
    margin_y_in = font_size * 1.0
    pad_x_in = font_size * 0.75
    pad_y_in = font_size * 0.75

    x_in = margin_x_in + pad_x_in
    # Position so that the background bottom is margin above page bottom
    desired_y = page_h_in - (margin_y_in + pad_y_in*2 + tmp_bbox.height)
    # Clamp to avoid negative values placing the box at the top-left
    y_in = max(margin_y_in + pad_y_in, desired_y)

    # Recompute bbox at final position to draw background precisely
    text_bbox = draw.textbbox(wrapped, (x_in, y_in), font)

    # Semi-transparent black background behind the text with equal padding
    bg_left = text_bbox.left - pad_x_in
    bg_top = text_bbox.top - pad_y_in
    bg_right = text_bbox.right + pad_x_in
    bg_bottom = text_bbox.bottom + pad_y_in

    # Use right-only rounded rectangle (left side remains square)
    corner_radius_in = min(pad_y_in, (bg_bottom - bg_top)/2)
    draw.rounded_rectangle_right((bg_left, bg_top, bg_right, bg_bottom), radius=corner_radius_in, fill=(0, 0, 0, 160))

    # Draw the white text over the background
    draw.text(wrapped, (x_in, y_in), font, fill=(255, 255, 255, 255), align="left")

    # Return the final composed image
    return image.page.ToImage()



