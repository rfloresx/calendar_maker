from xml.etree import ElementTree as ET
import pathlib

try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

import lib.pycal as _libcal
import lib.html.htmlutil as _libhtml
from lib.calendar.moon_calendar import _MoonCalendar

HtmlEncoder = _libhtml.HtmlEncoder()

class CssResources:
    CSS_DIR = "css"
    CALENDAR_CSS = str(pathlib.Path(CSS_DIR, "calendar.css"))
    PRINT_CSS = str(pathlib.Path(CSS_DIR, "print.css"))


@HtmlEncoder.override(_libcal.FrontPage)
def FrontPageHtml(self: _libcal.FrontPage) -> ET.Element:
    """
    <div class="page-letter-landscape">
        <div class="front-page">
            <div class="front-page
    """
    page = _libhtml.HtmlTag('div', attrib={'class': 'page-letter-landscape'})
    fp = page.add('div', attrib={'class': 'front-page'})
    if self.image:
        fp.add('img', attrib={
            'class': 'front-page-img', 'src': self.image})

    if self.title:
        title = fp.add('div', attrib={'class': 'front-page-title'})
        title.add('p', text=self.title)
    page.add("div", attrib={'class': 'page-break'})
    return page


@HtmlEncoder.override(_libcal.CalendarArt)
def CalendarArtHtml(self: _libcal.CalendarArt) -> ET.Element:
    """
    <div class="page-letter-landscape">
        <div class="front-page">
            <div class="front-page
    """
    page = _libhtml.HtmlTag('div', attrib={'class': 'page-letter-landscape'})
    fp = page.add('div', attrib={'class': 'calendar-art-page'})
    if self.image:
        fp.add('img', attrib={
            'class': 'calendar-art-page-img', 'src': self.image})

    if self.title:
        title = fp.add('div', attrib={'class': 'calendar-art-page-title'})
        title.add('p', text=self.title)
    page.add("div", attrib={'class': 'page-break'})

    return page


class MoonPhaseImages:
    NEW_MOON_PATH = "images/moon-phases/new-moon.png"
    FIRST_QUARTER_PATH = "images/moon-phases/first-quarter.png"
    FULL_MOON_PATH = "images/moon-phases/full-moon.png"
    THIRD_QUARTER_PATH = "images/moon-phases/third-quarter.png"

    @staticmethod
    def image(phase) -> None:
        moon_path = None
        if phase == _MoonCalendar.NEW_MOON:
            moon_path = MoonPhaseImages.NEW_MOON_PATH
        elif phase == _MoonCalendar.FIRST_QUARTER:
            moon_path = MoonPhaseImages.FIRST_QUARTER_PATH
        elif phase == _MoonCalendar.FULL_MOON:
            moon_path = MoonPhaseImages.FULL_MOON_PATH
        elif phase == _MoonCalendar.THIRD_QUARTER:
            moon_path = MoonPhaseImages.THIRD_QUARTER_PATH
        return moon_path


@HtmlEncoder.override(_libcal.MoonPhase)
def MoonPhaseHtml(self: _libcal.MoonPhase) -> ET.Element:
    img = MoonPhaseImages.image(self.phase)
    if img:
        return _libhtml.HtmlTag('img', attrib={'class': 'cell-moon-overlay', 'src': img})
    return None


@HtmlEncoder.override(_libcal.Day)
def CellHtml(self: _libcal.Day) -> ET.Element:
    attrib = {'class': 'cell'}
    cell = _libhtml.HtmlTag('div', attrib=attrib)
    if self.photo:
        cell.add('img', attrib={'class': 'cell-photo-overlay',
                                'src': self._photo})
    if self.day:
        cell.add('div', text=str(self._day),
                 attrib={'class': 'cell-text-day'})
    if self.text:
        cell.add('div', text=str(self._text),
                 attrib={'class': 'cell-text-overlay'})
    if self.moon_phase:
        cell.append(HtmlEncoder.to_html(self.moon_phase))
    return cell


@HtmlEncoder.override(_libcal.Month)
def MonthHtml(self: _libcal.Month) -> ET.Element:
    page = _libhtml.HtmlTag('div', attrib={'class': 'page-letter-landscape'})
    cal = page.add('div', attrib={'class': 'month'})

    cal.add('div', text=f"{self.name} {self.year}".upper(),
            attrib={'class': 'month-header'})

    header = cal.add('div', attrib={'class': 'container'})
    _days, _cells = self.table
    for day in _days:
        header.add('div', text=day, attrib={'class': 'month-day-header'})

    grid = cal.add(
        'div', attrib={'class': 'container', 'style': 'border: 1px solid black;'})
    for row in _cells:
        for c in row:
            grid.append(HtmlEncoder.to_html(c))

    cal.add("div", attrib={'class': 'page-break'})
    return page


@HtmlEncoder.override(_libcal.Calendar)
def CalendarHtml(self: _libcal.Calendar) -> ET.Element:
    cal = _libhtml.HtmlTag('div', attrib={'class': 'calendar'})
    cal.append(HtmlEncoder.to_html(self.front_page))
    for mi in self.pages:
        cal.append(HtmlEncoder.to_html(mi.art))
        cal.append(HtmlEncoder.to_html(mi.month))
    return cal


class WallCalendar:
    def __init__(self, calendar: _libcal.Calendar):
        self._calendar = calendar

    def __html__(self) -> ET.ElementTree:
        root = _libhtml.HtmlTag("html")
        head = root.add("head")
        head.add('title', text='Calendar')
        head.add('link', attrib={'rel': "stylesheet",
                 'href': CssResources.CALENDAR_CSS})
        head.add('link', attrib={
            'rel': "stylesheet", 'type': 'text/css', 'media': 'print', 'href': CssResources.PRINT_CSS})

        body = root.add('body', attrib={'class': 'main'})

        body.append(HtmlEncoder.to_html(self._calendar))
        return ET.ElementTree(root)


if __name__ == "__main__":
    import lib.calendar.ics_loader as _libics
    import sys
    cal = _libcal.Calendar(year=2025, events=_libcal.EventsManager(
        2025, birthdays=_libics.TestVCalendar()))
    cal = WallCalendar(cal)
    root = HtmlEncoder.to_html(cal)

    root.write(sys.stdout, encoding='unicode',
               method='html')
