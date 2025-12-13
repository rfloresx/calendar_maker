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

from lib.filemanager import FilesManager

_libdraw.Resolution.unit = _libdraw.Units.IN
# _libdraw.Resolution.dpi = 300

ImageDrawer = _libdraw.DrawDecoder()


class WallCalPage:
    """Base layout class describing a printable wall calendar page.

    Subclasses define padding and provide helper methods to compute bounding
    boxes for main content areas (image, title, calendar grid, etc.).
    """
    WIDTH = 10.5
    HEIGHT = 7.5
    BIND_PADDING = 0.0
    PADDING = (0, 0, 0, 0)

    def __init__(self, color='white'):
        self._page = _libdraw.Image.new(
            size=(self.width, self.height), color=color)

    @property
    def left_padding(self) -> float:
        """Left page padding in inches."""
        return self.PADDING[0]

    @property
    def top_padding(self) -> float:
        """Top page padding in inches."""
        return self.PADDING[1]

    @property
    def right_padding(self) -> float:
        """Right page padding in inches."""
        return self.PADDING[2]

    @property
    def bot_padding(self) -> float:
        """Bottom page padding in inches."""
        return self.PADDING[3]

    @property
    def width(self) -> float:
        """Page width in inches."""
        return self.WIDTH

    @property
    def height(self) -> float:
        """Page height in inches."""
        return self.HEIGHT

    @property
    def page(self) -> _libdraw.Image:
        """Return the underlying drawing surface (lib.print.draw.Image)."""
        return self._page

    def main_bbox(self) -> _libdraw.BBox:
        """Return the main content BBox for this page."""
        left = self.left_padding
        top = self.top_padding
        right = self.width - self.right_padding
        bot = self.height - self.bot_padding
        return _libdraw.BBox(left, top, right, bot)

    def draw_image(self, image: str, bbox: _libdraw.BBox) -> None:
        """Helper to place and resize an image into a page bbox.

        Args:
            image: path to the image file.
            bbox: lib.print.draw.BBox describing the target area.
        """
        img_w = bbox.width
        img_h = bbox.height

        img = _libdraw.Image(str(image))

        img.resize((img_w, img_h))
        draw = _libdraw.Draw(self.page)
        draw.paste(img, (bbox.x, bbox.y))


class FrontPageLayout(WallCalPage):
    """Layout for the calendar front (cover) page."""
    PADDING = (0, 0, 0, 0)
    TOP_BAR = 0.0
    IMAGE_WIDTH = WallCalPage.WIDTH
    IMAGE_HEIGHT = 6.0

    TITLE_WIDTH = WallCalPage.WIDTH
    TITLE_HEIGHT = 1.5

    def topbar_bbox(self) -> _libdraw.BBox:
        """Return the top bar bounding box for the front page."""
        return _libdraw.BBox.new(0, self.top_padding, self.WIDTH, self.TOP_BAR)

    def image_bbox(self) -> _libdraw.BBox:
        """Return the image bounding box where the cover image should be drawn."""
        return _libdraw.BBox.new(0, self.top_padding + self.TOP_BAR, self.IMAGE_WIDTH, self.IMAGE_HEIGHT)

    def title_bbox(self) -> _libdraw.BBox:
        """Return the bounding box for the cover title text."""
        return _libdraw.BBox.new(0, self.top_padding + self.TOP_BAR + self.IMAGE_HEIGHT, self.TITLE_WIDTH, self.TITLE_HEIGHT)


class ArtPageLayout(WallCalPage):
    """Layout used for full-page artwork pages in the wall calendar."""
    PADDING = (0, 0, 0, 0)

    IMG_LEFT_BORDER = 0.0
    IMG_RIGHT_BORDER = 0.0
    IMG_BOT_BORDER = .55
    IMG_TOP_BORDER = 0.0

    IMAGE_WIDTH = WallCalPage.WIDTH
    IMAGE_HEIGHT = WallCalPage.HEIGHT - IMG_BOT_BORDER

    INFO_WIDTH = IMAGE_WIDTH
    INFO_HEIGHT = IMG_BOT_BORDER

    def image_bbox(self) -> _libdraw.BBox:
        """Return bounding box for artwork image placement."""
        return _libdraw.BBox.new(self.IMG_LEFT_BORDER, self.IMG_TOP_BORDER, self.IMAGE_WIDTH, self.IMAGE_HEIGHT)

    def info_bbox(self) -> _libdraw.BBox:
        """Return bounding box for the artwork description area."""
        return _libdraw.BBox.new(self.IMG_LEFT_BORDER, self.HEIGHT - self.PADDING[3] - self.INFO_HEIGHT, self.INFO_WIDTH, self.INFO_HEIGHT)


class CalendarPageLayout(WallCalPage):
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


    def title_bbox(self) -> _libdraw.BBox:
        """Return bounding box for the calendar title area."""
        return _libdraw.BBox.new(self.CAL_BORDER, self.top_padding, self.CALL_WIDTH, self.TITLE_HEIGHT)
    
    def header_bbox(self, index:int) -> _libdraw.BBox:
        """Return bounding box for a day-of-week header cell at column index."""
        x_pos = self.CAL_BORDER + (self.HEADER_WIDTH*index)        
        y_pos = self.top_padding + self.TITLE_HEIGHT
        return _libdraw.BBox.new(x_pos, y_pos, self.HEADER_WIDTH, self.HEADER_HEIGHT)

    def cel_bbox(self, x:int, y:int) -> _libdraw.BBox:
        """Return bounding box for a calendar day cell at column x and row y."""
        x_pos = self.CAL_BORDER + (self.CELL_WIDTH * x)
        y_pos = self.top_padding + self.TITLE_HEIGHT + self.HEADER_HEIGHT + (self.CELL_HEIGHT * y)
        return _libdraw.BBox.new(x_pos, y_pos, self.CELL_WIDTH, self.CELL_HEIGHT)

    def cal_bbox(self) -> _libdraw.BBox:
        """Return the overall calendar bounding box covering the grid area."""
        begin = self.cel_bbox(0,0)
        end = self.cel_bbox(6, 5)
        return _libdraw.BBox(begin.left, begin.top, end.right, end.bottom)

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

    page = ArtPageLayout(color='white')
    draw = _libdraw.Draw(page.page)

    draw.rectangle(page.main_bbox(), fill='white', width=0)

    page.draw_image(image_path, page.image_bbox())

    pos = page.info_bbox()

    spacing = .05
    draw.text(self.title, (pos.x+.5, pos.y + spacing), font, fill='black', spacing=spacing)

    return page.page.image

class MoonPhaseImages:
    """Helper class to load moon phase images for calendar rendering."""
    BASE_DIR: str = os.path.dirname(os.path.realpath(__file__))
    MOON_PHASES: str = os.path.join(BASE_DIR, 'moon-phases')
    NEW_MOON_PATH = os.path.join(MOON_PHASES,"new-moon.png")
    FIRST_QUARTER_PATH = os.path.join(MOON_PHASES,"first-quarter.png")
    FULL_MOON_PATH = os.path.join(MOON_PHASES,"full-moon.png")
    THIRD_QUARTER_PATH = os.path.join(MOON_PHASES,"third-quarter.png")

    @staticmethod
    def image(phase) -> _libdraw.Image:
        """Return the image corresponding to a moon phase."""
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
    
def DrawCell(page : CalendarPageLayout, day: _libcal.Day, pos : _libdraw.BBox) -> None:
    """Render a single calendar day cell."""
    padding = .05
    img_size = pos.shrink(.01)
    draw = _libdraw.Draw(page.page)

    # draw.rectangle(img_size, outline='green', width='1pt')
    has_photo = False
    if day.photo:
        photo = _libdraw.Image(day.photo)
        photo.resize((img_size.width, img_size.height))
        draw.paste(photo, (img_size.x, img_size.y))
        has_photo = True
    if day.day:
        day_pos = _libdraw.BBox.new(padding, padding, .2, .2).move(img_size.x, img_size.y)
        font = _libdraw.Font(_libdraw.fonts.Roboto, 14)
        draw.text(f"{day.day}", day_pos, font, fill='black')
    
    
    if day.moon_phase:
        moon = MoonPhaseImages.image(day.moon_phase.phase)
        if moon:
            moon_size = .2
            moon_pos = _libdraw.BBox.new(img_size.width - moon_size - padding, padding, moon_size, moon_size).move(img_size.x, img_size.y)
            moon.resize((moon_pos.width, moon_pos.height))
            draw.paste(moon, (moon_pos.x, moon_pos.y), moon)


    # day._text = "Hello\nWorld"
    if has_photo:
        if day.text:
            font = _libdraw.Font(_libdraw.fonts.Roboto, 10)

            mtext = draw.get_multiline_text(day.text, pos.width, font)
            # mtext = 
            x_pos = pos.center[0]
            y_pos = pos.bottom 

            bbox = draw.textbbox(mtext, (x_pos, y_pos), font, anchor='md', align='center')
            offset = abs(y_pos-bbox.bottom) + .01
            background = (pos.left, bbox.top-offset, pos.right, pos.bottom)
            draw.rectangle(background, fill=(0,0,0,100))

            draw.text(mtext, (x_pos, y_pos), font, fill='white', anchor='md', align='center')
    else:
        if day.text:
            font = _libdraw.Font(_libdraw.fonts.Roboto, 10)

            mtext = draw.get_multiline_text(day.text, pos.width, font)

            x_pos = pos.center[0]
            y_pos = pos.bottom - .1


            draw.text(mtext, (x_pos, y_pos), font, fill='black', anchor='md', align='center')


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
    img = ImageDrawer.draw(self.front_page)
    yield img
    for page in self.pages:
        yield ImageDrawer.draw(page.art)
        # yield ImageDrawer.draw(page.month)
        # calpage = DeskCalendarPage(img)
        # calpage.set_calendar(cal)
    #     images.append(img) 
    #     images.append(cal)
    # return images

if __name__ == "__main__":
    fm = FilesManager("resources")
    test_image = "images/PXL_COVER.jpg"

    front_page = _libcal.FrontPage(test_image, "Calendar\n2025")
    img = ImageDrawer.draw(front_page)
    # img.show()

    art = _libcal.CalendarArt(test_image, "Some Where in a places\nAustin, TX. Mar 20")
    img = ImageDrawer.draw(art)
    # img.show()

    month = _libcal.Month(2025, 5)
    img = ImageDrawer.draw(month)
    # img.show()

    cal = _libcal.Calendar(2025, _libcal.EventsManager(2025))
    imgs: List[PIL.Image.Image] = ImageDrawer.draw(cal)
    for i, img in enumerate(imgs):
        fout = fm.get_file_path(f"out/wall_page_{i}.png")
        img.save(str(fout))
