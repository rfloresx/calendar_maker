"""Drawing routines for the desk-style printable calendar pages.

This module implements size constants and drawing helpers used to render a
small desk calendar. It registers image-drawing handlers (via ImageDrawer)
for the calendar model objects from lib.pycal so the calendar can be
rendered to PIL images for preview or saving.
"""

import PIL.Image

try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

import lib.pycal as _libcal
from typing import List

import lib.print.draw as _libdraw

from lib.filemanager import FilesManager

_libdraw.Resolution.unit = _libdraw.Units.IN
# _libdraw.Resolution.dpi = 300
# _libdraw.Resolution.dpi = 96


class DeskCalSize:
    """Geometry constants for the desk calendar layout.

    Values are expressed in drawing units (set by lib.print.draw.Resolution).
    The class provides convenience methods that return BBox instances for
    the image area, info area and calendar area used by the page layout.
    """
    WIDTH = 7
    HEIGHT = 4.25
    TOP_PADDING = 0.25

    IMAGE_WIDTH = 4
    IMAGE_HEIGHT = 4

    INFO_WIDTH = WIDTH - IMAGE_WIDTH
    INFO_HEIGHT = HEIGHT - TOP_PADDING

    CAL_WIDTH = 2.6
    CAL_HEIGHT = 2.6

    @staticmethod
    def info_bbox() -> _libdraw.BBox:
        return _libdraw.BBox.new(DeskCalSize.IMAGE_WIDTH, DeskCalSize.TOP_PADDING, DeskCalSize.INFO_WIDTH, DeskCalSize.INFO_HEIGHT)

    @staticmethod
    def image_bbox() -> _libdraw.BBox:
        return _libdraw.BBox.new(0, DeskCalSize.HEIGHT-DeskCalSize.IMAGE_HEIGHT, DeskCalSize.IMAGE_WIDTH, DeskCalSize.IMAGE_HEIGHT)

    @staticmethod
    def cal_bbox() -> _libdraw.BBox:
        """Return a BBox positioned inside the info region for the month grid.

        The method centers the calendar grid inside the info area and returns
        a moved BBox appropriate for pasting the calendar image.
        """
        info_box = DeskCalSize.info_bbox()
        # Add Padding
        # .2in left
        # .7in top
        left_padding = (DeskCalSize.INFO_WIDTH-DeskCalSize.CAL_WIDTH)/2
        top_padding = (DeskCalSize.INFO_HEIGHT-DeskCalSize.CAL_HEIGHT)/2

        info_box = info_box.move(left_padding, top_padding)
        bbox = _libdraw.BBox(0, 0, DeskCalSize.CAL_WIDTH,
                             DeskCalSize.CAL_HEIGHT)
        return bbox.move(info_box.x, info_box.y)


ImageDrawer = _libdraw.DrawDecoder()


class DeskCalendarPage:
    """Container for a single desk calendar page image.

    Provides helpers to paste the cover image and the calendar grid onto a
    page sized according to DeskCalSize. The underlying image object is an
    instance of lib.print.draw.Image and is exposed via the `page` property.
    """
    def __init__(self, page: PIL.Image.Image = None):
        self._width = DeskCalSize.WIDTH
        self._height = DeskCalSize.HEIGHT
        self._top_padding = DeskCalSize.TOP_PADDING

        if page is None:
            self._page = _libdraw.Image.new(
                size=(self._width, self._height), color="white")
        else:
            self._page = page

    @property
    def width(self) -> float:
        return self._width

    @property
    def height(self) -> float:
        return self._height

    @property
    def page(self) -> _libdraw.Image:
        return self._page

    def set_image(self, image: str) -> None:
        """Paste the provided image into the page's image area.

        The image path is resolved via FilesManager and the image is resized
        to exactly fill the configured image_bbox.
        """
        pos = DeskCalSize.image_bbox()

        img_w = pos.width
        img_h = pos.height

        img = _libdraw.Image(str(image))

        img.resize((img_w, img_h))
        draw = _libdraw.Draw(self._page)
        draw.paste(img, (pos.x, pos.y))

    def set_calendar(self, image: PIL.Image.Image) -> None:
        """Paste a small calendar image into the info area of the page.

        The provided image is resized to the calendar bbox and pasted onto the
        page so it aligns with the descriptive text and title areas.
        """
        if isinstance(image, _libdraw.Draw):
            image = image.image
        img_w = DeskCalSize.CAL_WIDTH
        img_h = DeskCalSize.CAL_HEIGHT

        img = _libdraw.Image(image)
        img.resize((img_w, img_h))

        draw = _libdraw.Draw(self._page)
        pos = DeskCalSize.cal_bbox()

        draw.paste(img, (pos.x, pos.y))


@ImageDrawer.override(_libcal.FrontPage)
def DrawFrontPage(self: _libcal.FrontPage) -> PIL.Image:
    """Draw the front (cover) page for the desk calendar.

    The cover places the configured image on the left and centers the title
    text in the info area on the right. Returns a PIL.Image instance ready
    for saving or preview.
    """
    image_path = FilesManager.instance().get_file_path(self.image)

    if True:
        page = DeskCalendarPage()
        page.set_image(image_path)
        draw = _libdraw.Draw(page.page)

        center = DeskCalSize.info_bbox().center
        font = _libdraw.Font(_libdraw.Fonts.EBGaramond_Bold, 48)
        draw.text(self.title, center, font, anchor='mm',
                  fill='black', align='center')

        # page.page.image.show()
        return page.page.image


@ImageDrawer.override(_libcal.CalendarArt)
def DrawArtPage(self: _libcal.CalendarArt) -> PIL.Image.Image:
    """Draw an artwork page used between the cover and month grids.

    The artwork fills the left side image area while a small title is drawn
    on the right info area. Returns a PIL.Image instance.
    """
    image_path = FilesManager.instance().get_file_path(self.image)
    if True:
        page = DeskCalendarPage()
        page.set_image(image_path)
        """
        info:
            width: 3
            height: 4

            padding: .25
            __________________________
            |   ______2.6_________   | 
            |.2|                  |  |
            |  |    Title         |  |
            |  |      Mar 2       |  |
            |  |__________________|  |
            _.2______________________|
        """
        draw = _libdraw.Draw(page.page)

        title_width = 2.6
        title_height = .5
        padding = .2

        right = page.width - padding
        bot = page.height - padding
        left = right - title_width
        top = bot - title_height
        bbox = _libdraw.BBox(left, top, right, bot)
        text_pos = bbox.center
        font = _libdraw.Font(_libdraw.Fonts.EBGaramond, 14)
        draw.text(self.title, text_pos, font, anchor='mm',
                  fill='black', align='center')
        # draw.rectangle(bbox, fill=None, outline='red', width="1pt")
        return page.page.image


@ImageDrawer.override(_libcal.Month)
def DrawMonth(self: _libcal.Month):
    """Render the month grid into an image sized for the desk layout.

    A new image is created for the month grid, the month name and weekday
    headings are drawn, then each day number is placed into the grid
    according to the Month.table provided by lib.pycal.
    """
    # 2.6x2.6
    pos = DeskCalSize.cal_bbox()

    img = _libdraw.Image.new((pos.width, pos.height), color='white')
    draw = _libdraw.Draw(img)

    # Calendar title
    # Width 2.6
    # Height .6
    title = _libdraw.BBox((0, 0, 2.6, .6))

    font = _libdraw.Font(_libdraw.Fonts.Helvetica_Bold, 24)
    draw.text(f"{self.name} {self.year}", title.center, font,
              fill='black', anchor='mm', align='center')

    font = _libdraw.Font(_libdraw.Fonts.Helvetica_Bold, 10)

    # Calendar Week days
    # Height .2
    # Width .37
    # 7 cells = .37*7 = 2.59
    header = _libdraw.BBox(0, .6, .37, .8)
    headers, weeks = self.table
    pos = header
    for c in headers:
        # draw.rectangle(pos, outline='red', width='1pt')
        draw.text(c[:3], pos.center, font, fill='black',
                  anchor='mm', align='center')
        pos = pos.move(0.37, 0)

    # Calendar Days
    # Day Height .3
    # Day Width .37
    font = _libdraw.Font(_libdraw.Fonts.Helvetica, 10)
    day_start = _libdraw.BBox(0, .8, .37, .8+.3)

    for week in weeks:
        day_pos = day_start
        for day in week:
            if day.day:
                draw.text(str(day.day), day_pos.center, font,
                          fill='black', anchor='mm', align='center')
            day_pos = day_pos.move(.37, 0)
        day_start = day_start.move(0, .3)
    return img.image


@ImageDrawer.override(_libcal.Calendar)
def DrawCalendar(self: _libcal.Calendar):
    """Generate the sequence of page images that make up the calendar.

    Yields PIL.Image objects: the cover page followed by each month page
    as a DeskCalendarPage instance with the month grid pasted into the
    artwork background.
    """
    images = []
    img = ImageDrawer.draw(self.front_page)
    yield img
    for page in self.pages:
        img = ImageDrawer.draw(page.art)
        cal = ImageDrawer.draw(page.month)
        calpage = DeskCalendarPage(img)
        calpage.set_calendar(cal)
        yield calpage.page


    # self.image
    # self.title
if __name__ == "__main__":
    fm = FilesManager("resources")
    # test_image = "images/PXL_COVER.jpg"

    # front_page = _libcal.FrontPage("images/PXL_COVER.jpg", "Calendar\n2025")
    # img = ImageDrawer.draw(front_page)
    # img.show()

    # art = _libcal.CalendarArt(test_image, "Some Where in a places\nMar 20")
    # img = ImageDrawer.draw(art)
    # img.show()

    # month = _libcal.Month(2025, 5)
    # img = ImageDrawer.draw(month)
    # img.show()

    cal = _libcal.Calendar(2025)
    imgs: List[PIL.Image.Image] = ImageDrawer.draw(cal)
    for i, img in enumerate(imgs):
        fout = fm.get_file_path(f"out/page_{i}.png")
        img.save(str(fout))
