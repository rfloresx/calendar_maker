"""Wall calendar image layout and rendering helpers.

This module defines layouts and DrawDecoder handlers to render a lib.pycal.Calendar
into printable PIL Image pages suitable for a wall calendar export. It maps
pycal model objects (FrontPage, CalendarArt, Month, Calendar) to drawing
operations using lib.print.draw abstractions.
"""

import PIL.Image
import os
try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

import lib.pycal as _libcal
from typing import List
from lib.calendar.moon_calendar import _MoonCalendar

import lib.print.draw as _libdraw
from lib.print.wall_cal_base import (
    WallCalPageBase,
    FrontPageLayoutBase,
    ArtPageLayoutBase,
    CalendarPageLayoutBase,
    MoonPhaseImages,
    DrawCell as _DrawCell,
)

from lib.filemanager import FilesManager

_libdraw.Resolution.unit = _libdraw.Units.IN
# _libdraw.Resolution.dpi = 300

ImageDrawer = _libdraw.DrawDecoder()


class WallCalPage(WallCalPageBase):
    """Base layout class describing a printable wall calendar page.

    Subclasses define padding and provide helper methods to compute bounding
    boxes for main content areas (image, title, calendar grid, etc.).
    """
    WIDTH = 11
    HEIGHT = 8.5
    BIND_PADDING = 0.35
    PADDING = (0, 0, 0, 0)


class FrontPageLayout(FrontPageLayoutBase, WallCalPage):
    """Layout for the calendar front (cover) page."""
    PADDING = (0, WallCalPage.BIND_PADDING, 0, 0)
    TOP_BAR = .25
    IMAGE_WIDTH = WallCalPage.WIDTH
    IMAGE_HEIGHT = 6

    TITLE_WIDTH = WallCalPage.WIDTH
    TITLE_HEIGHT = 1.5

    # Methods inherited from FrontPageLayoutBase


class ArtPageLayout(ArtPageLayoutBase, WallCalPage):
    """Layout used for full-page artwork pages in the wall calendar."""
    PADDING = (0, 0, 0, WallCalPage.BIND_PADDING)

    IMG_LEFT_BORDER = .7
    IMG_RIGHT_BORDER = .7
    IMG_BOT_BORDER = .7
    IMG_TOP_BORDER = 1

    IMAGE_WIDTH = WallCalPage.WIDTH - (IMG_LEFT_BORDER + IMG_RIGHT_BORDER)
    IMAGE_HEIGHT = WallCalPage.HEIGHT - \
        (PADDING[3] + IMG_TOP_BORDER + IMG_BOT_BORDER)

    INFO_WIDTH = IMAGE_WIDTH
    INFO_HEIGHT = IMG_BOT_BORDER

    # Methods inherited from ArtPageLayoutBase


class CalendarPageLayout(CalendarPageLayoutBase, WallCalPage):
    """Layout used to draw a month calendar grid on a page."""
    PADDING = (0, WallCalPage.BIND_PADDING+.4, 0, 0)

    CAL_BORDER = .5

    CALL_WIDTH = 10
    CALL_HEIGHT = 6.25

    CELL_WIDTH = CALL_WIDTH/7
    CELL_HEIGHT = CALL_HEIGHT/6

    HEADER_WIDTH = CELL_WIDTH
    HEADER_HEIGHT = .3

    TITLE_HEIGHT = CALL_WIDTH
    TITLE_HEIGHT = .7


    # Methods inherited from CalendarPageLayoutBase

@ImageDrawer.override(_libcal.FrontPage)
def DrawFrontPage(self: _libcal.FrontPage) -> PIL.Image.Image:
    """Render a lib.pycal.FrontPage into a PIL Image using the FrontPageLayout."""
    image_path = FilesManager.instance().get_file_path(self.image)
    font = _libdraw.Font(_libdraw.fonts.EBGaramond_Bold, 48)

    page = FrontPageLayout(color="black")
    draw = _libdraw.Draw(page.page)

    draw.rectangle(page.main_bbox(), fill='black', width=0)

    page.draw_image(image_path, page.image_bbox())

    draw.text(self.title, page.title_bbox().center, font,
              anchor='mm', fill='white', align='center')

    return page.page.image


@ImageDrawer.override(_libcal.CalendarArt)
def DrawCalendarArt(self: _libcal.CalendarArt) -> PIL.Image.Image:
    """Render a lib.pycal.CalendarArt into a PIL Image using ArtPageLayout."""
    image_path = FilesManager.instance().get_file_path(self.image)
    font = _libdraw.Font(_libdraw.fonts.Roboto, 14)

    page = ArtPageLayout(color='black')
    draw = _libdraw.Draw(page.page)

    draw.rectangle(page.main_bbox(), fill='black', width=0)

    page.draw_image(image_path, page.image_bbox())

    pos = page.info_bbox()

    spacing = .1
    draw.text(self.title, (pos.x, pos.y + spacing), font, fill='white', spacing=spacing)

    return page.page.image

DrawCell = _DrawCell


@ImageDrawer.override(_libcal.Month)
def DrawMonth(self: _libcal.Month) -> PIL.Image.Image:
    """Render a lib.pycal.Month into a PIL Image using CalendarPageLayout."""
    title_font = _libdraw.Font(_libdraw.fonts.Roboto, 58)
    header_font = _libdraw.Font(_libdraw.fonts.Roboto, 14)
    
    page = CalendarPageLayout()
    draw = _libdraw.Draw(page.page)
    
    title_pos = page.title_bbox()
    draw.text(f"{self.name.upper()} {self.year}", (title_pos.right, title_pos.top), title_font, fill='black', anchor='ra', align='right')

    (headers, weeks) = self.table
    for index,day_name in enumerate(headers):
        pos = page.header_bbox(index)
        center = pos.center
        draw.text(day_name, (center[0], pos.bottom), header_font, fill='black', anchor='md')
    
    cal_box = page.cal_bbox()
    cal_box = cal_box.shrink(.01)
    for y_index,week in enumerate(weeks):
        for x_index,day in enumerate(week):
            pos = page.cel_bbox(x_index, y_index)
            DrawCell(page, day, pos)
            draw.rectangle(pos, outline='black', width=.01)
    draw.rectangle(cal_box, outline='black', width=.01)
            
    return page.page.image

@ImageDrawer.override(_libcal.Calendar)
def DrawCalendar(self: _libcal.Calendar):
    """Render a lib.pycal.Calendar into a sequence of PIL Images."""
    # ImageDrawer.draw(self.art)
    yield from ImageDrawer.draw(self.front_page)
    for page in self.pages:
        yield from ImageDrawer.draw(page.art)
        yield from ImageDrawer.draw(page.month)

if __name__ == "__main__":
    fm = FilesManager("resources")
    test_image = "images/PXL_COVER.jpg"

    front_page = _libcal.FrontPage(test_image, "Calendar\n2025")
    img = next(ImageDrawer.draw(front_page))
    # img.show()

    art = _libcal.CalendarArt(test_image, "Some Where in a places\nAustin, TX. Mar 20")
    img = next(ImageDrawer.draw(art))
    # img.show()

    month = _libcal.Month(2025, 5)
    img = next(ImageDrawer.draw(month))
    # img.show()

    cal = _libcal.Calendar(2025, _libcal.EventsManager(2025))
    imgs = ImageDrawer.draw(cal)
    for i, img in enumerate(imgs):
        fout = fm.get_file_path(f"out/wall_page_{i}.png")
        img.save(str(fout))
