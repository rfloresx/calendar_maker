"""Shared base utilities for wall calendar layouts and rendering.

Provides base classes with common methods for page layout helpers and
shared drawing helpers reused across different wall calendar variants.
"""

import os
import PIL.Image

try:
    import lib as __lib  # noqa: F401
except Exception:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

import lib.print.draw as _libdraw
from lib.calendar.moon_calendar import _MoonCalendar
import lib.pycal as _libcal


class WallCalPageBase:
    """Base page class with common helpers.

    Subclasses must define WIDTH, HEIGHT, BIND_PADDING, and PADDING.
    """

    WIDTH = 0.0
    HEIGHT = 0.0
    BIND_PADDING = 0.0
    PADDING = (0.0, 0.0, 0.0, 0.0)

    def __init__(self, color: str = "white"):
        self._page = _libdraw.Image.new(size=(self.width, self.height), color=color)

    @property
    def left_padding(self) -> float:
        return self.PADDING[0]

    @property
    def top_padding(self) -> float:
        return self.PADDING[1]

    @property
    def right_padding(self) -> float:
        return self.PADDING[2]

    @property
    def bot_padding(self) -> float:
        return self.PADDING[3]

    @property
    def width(self) -> float:
        return self.WIDTH

    @property
    def height(self) -> float:
        return self.HEIGHT

    @property
    def page(self) -> _libdraw.Image:
        return self._page

    def main_bbox(self) -> _libdraw.BBox:
        left = self.left_padding
        top = self.top_padding
        right = self.width - self.right_padding
        bot = self.height - self.bot_padding
        return _libdraw.BBox(left, top, right, bot)

    def draw_image(self, image: str, bbox: _libdraw.BBox) -> None:
        img_w = bbox.width
        img_h = bbox.height
        img = _libdraw.Image(str(image))
        img.resize((img_w, img_h))
        draw = _libdraw.Draw(self.page)
        draw.paste(img, (bbox.x, bbox.y))


class FrontPageLayoutBase(WallCalPageBase):
    """Common methods for front page layout."""

    TOP_BAR = 0.0
    IMAGE_WIDTH = 0.0
    IMAGE_HEIGHT = 0.0
    TITLE_WIDTH = 0.0
    TITLE_HEIGHT = 0.0

    def __init__(self, color: str = "white"):
        super().__init__(color)

    def topbar_bbox(self) -> _libdraw.BBox:
        return _libdraw.BBox.new(0, self.top_padding, self.WIDTH, self.TOP_BAR)

    def image_bbox(self) -> _libdraw.BBox:
        return _libdraw.BBox.new(0, self.top_padding + self.TOP_BAR, self.IMAGE_WIDTH, self.IMAGE_HEIGHT)

    def title_bbox(self) -> _libdraw.BBox:
        return _libdraw.BBox.new(0, self.top_padding + self.TOP_BAR + self.IMAGE_HEIGHT, self.TITLE_WIDTH, self.TITLE_HEIGHT)


class ArtPageLayoutBase(WallCalPageBase):
    """Common methods for artwork page layout."""

    IMG_LEFT_BORDER = 0.0
    IMG_RIGHT_BORDER = 0.0
    IMG_BOT_BORDER = 0.0
    IMG_TOP_BORDER = 0.0
    IMAGE_WIDTH = 0.0
    IMAGE_HEIGHT = 0.0
    INFO_WIDTH = 0.0
    INFO_HEIGHT = 0.0

    def image_bbox(self) -> _libdraw.BBox:
        return _libdraw.BBox.new(self.IMG_LEFT_BORDER, self.IMG_TOP_BORDER, self.IMAGE_WIDTH, self.IMAGE_HEIGHT)

    def info_bbox(self) -> _libdraw.BBox:
        return _libdraw.BBox.new(self.IMG_LEFT_BORDER, self.HEIGHT - self.PADDING[3] - self.INFO_HEIGHT, self.INFO_WIDTH, self.INFO_HEIGHT)


class CalendarPageLayoutBase(WallCalPageBase):
    """Common methods for calendar grid page layout."""

    CAL_BORDER = 0.5
    CALL_WIDTH = 10.0
    CALL_HEIGHT = 6.25
    CELL_WIDTH = CALL_WIDTH / 7.0
    CELL_HEIGHT = CALL_HEIGHT / 6.0
    HEADER_WIDTH = CELL_WIDTH
    HEADER_HEIGHT = 0.3
    TITLE_HEIGHT = 0.7

    def title_bbox(self) -> _libdraw.BBox:
        return _libdraw.BBox.new(self.CAL_BORDER, self.top_padding, self.CALL_WIDTH, self.TITLE_HEIGHT)

    def header_bbox(self, index: int) -> _libdraw.BBox:
        x_pos = self.CAL_BORDER + (self.HEADER_WIDTH * index)
        y_pos = self.top_padding + self.TITLE_HEIGHT
        return _libdraw.BBox.new(x_pos, y_pos, self.HEADER_WIDTH, self.HEADER_HEIGHT)

    def cel_bbox(self, x: int, y: int) -> _libdraw.BBox:
        x_pos = self.CAL_BORDER + (self.CELL_WIDTH * x)
        y_pos = self.top_padding + self.TITLE_HEIGHT + self.HEADER_HEIGHT + (self.CELL_HEIGHT * y)
        return _libdraw.BBox.new(x_pos, y_pos, self.CELL_WIDTH, self.CELL_HEIGHT)

    def cal_bbox(self) -> _libdraw.BBox:
        begin = self.cel_bbox(0, 0)
        end = self.cel_bbox(6, 5)
        return _libdraw.BBox(begin.left, begin.top, end.right, end.bottom)


class MoonPhaseImages:
    """Shared moon phase images loader."""
    BASE_DIR: str = os.path.dirname(os.path.realpath(__file__))
    MOON_PHASES: str = os.path.join(BASE_DIR, 'moon-phases')
    NEW_MOON_PATH = os.path.join(MOON_PHASES, "new-moon.png")
    FIRST_QUARTER_PATH = os.path.join(MOON_PHASES, "first-quarter.png")
    FULL_MOON_PATH = os.path.join(MOON_PHASES, "full-moon.png")
    THIRD_QUARTER_PATH = os.path.join(MOON_PHASES, "third-quarter.png")

    @staticmethod
    def image(phase) -> _libdraw.Image:
        moon_path = None
        if phase == _MoonCalendar.NEW_MOON:
            moon_path = MoonPhaseImages.NEW_MOON_PATH
        elif phase == _MoonCalendar.FIRST_QUARTER:
            moon_path = MoonPhaseImages.FIRST_QUARTER_PATH
        elif phase == _MoonCalendar.FULL_MOON:
            moon_path = MoonPhaseImages.FULL_MOON_PATH
        elif phase == _MoonCalendar.THIRD_QUARTER:
            moon_path = MoonPhaseImages.THIRD_QUARTER_PATH
        if moon_path:
            return _libdraw.Image(moon_path)
        return moon_path


def DrawCell(page: CalendarPageLayoutBase, day: _libcal.Day, pos: _libdraw.BBox) -> None:
    padding = 0.05
    img_size = pos.shrink(0.01)
    draw = _libdraw.Draw(page.page)

    has_photo = False
    if day.photo:
        photo = _libdraw.Image(day.photo)
        photo.resize((img_size.width, img_size.height))
        draw.paste(photo, (img_size.x, img_size.y))
        has_photo = True
    if day.day:
        day_pos = _libdraw.BBox.new(padding, padding, 0.2, 0.2).move(img_size.x, img_size.y)
        font = _libdraw.Font(_libdraw.fonts.Roboto, 14)
        draw.text(f"{day.day}", day_pos, font, fill='black')

    if day.moon_phase:
        moon = MoonPhaseImages.image(day.moon_phase.phase)
        if moon:
            moon_size = 0.2
            moon_pos = _libdraw.BBox.new(img_size.width - moon_size - padding, padding, moon_size, moon_size).move(img_size.x, img_size.y)
            moon.resize((moon_pos.width, moon_pos.height))
            draw.paste(moon, (moon_pos.x, moon_pos.y), moon)

    if has_photo:
        if day.text:
            font = _libdraw.Font(_libdraw.fonts.Roboto, 10)
            mtext = draw.get_multiline_text(day.text, pos.width, font)
            x_pos = pos.center[0]
            y_pos = pos.bottom
            bbox = draw.textbbox(mtext, (x_pos, y_pos), font, anchor='md', align='center')
            offset = abs(y_pos - bbox.bottom) + 0.01
            background = (pos.left, bbox.top - offset, pos.right, pos.bottom)
            draw.rectangle(background, fill=(0, 0, 0, 100))
            draw.text(mtext, (x_pos, y_pos), font, fill='white', anchor='md', align='center')
    else:
        if day.text:
            font = _libdraw.Font(_libdraw.fonts.Roboto, 10)
            mtext = draw.get_multiline_text(day.text, pos.width, font)
            x_pos = pos.center[0]
            y_pos = pos.bottom - 0.1
            draw.text(mtext, (x_pos, y_pos), font, fill='black', anchor='md', align='center')
