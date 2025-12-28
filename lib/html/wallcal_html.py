"""HTML encoders for wall-style calendar views.

Register HtmlEncoder handlers that convert lib.pycal calendar model objects
into ElementTree fragments for a wall-sized calendar HTML document.  This
parallels deskcal_html but targets a larger, printable layout used for
wall calendars.
"""

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
import lib.html.common as _common
from lib.calendar.moon_calendar import _MoonCalendar

HtmlEncoder = _libhtml.HtmlEncoder()

class CssResources:
    CSS_DIR = "css"
    CALENDAR_CSS = str(pathlib.Path(CSS_DIR, "calendar.css"))
    PRINT_CSS = str(pathlib.Path(CSS_DIR, "print.css"))


@HtmlEncoder.override(_libcal.FrontPage)
def FrontPageHtml(self: _libcal.FrontPage) -> ET.Element:
    return _common.front_page_element(self)


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


# Use shared moon-phase images helper from common


@HtmlEncoder.override(_libcal.MoonPhase)
def MoonPhaseHtml(self: _libcal.MoonPhase) -> ET.Element:
    """Render a moon phase as an <img> element when an image is available.

    Returns an HtmlTag (ET.Element) containing an <img> with a CSS class
    that positions the moon overlay inside a calendar cell, or None when
    no image is defined for the phase.
    """
    return _common.moon_phase_element(self.phase)


@HtmlEncoder.override(_libcal.Day)
def CellHtml(self: _libcal.Day) -> ET.Element:
    """Render a single calendar day cell for the wall layout.

    Includes optional photo, text overlay and moon-phase image when
    provided by the Day model.
    """
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
    """Compose a printable month page for the wall calendar.

    The element contains the month header, weekday headings and a grid of
    day cells sized for printing on a letter landscape page.
    """
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
    """Render the entire calendar as a sequence of wall-style pages.

    The root fragment includes the front page and a sequence of month
    pages with artwork. The result is intended to be embedded in a
    full HTML document produced by WallCalendar.__html__.
    """
    cal = _libhtml.HtmlTag('div', attrib={'class': 'calendar'})
    cal.append(HtmlEncoder.to_html(self.front_page))
    for mi in self.pages:
        cal.append(HtmlEncoder.to_html(mi.art))
        cal.append(HtmlEncoder.to_html(mi.month))
    return cal


class WallCalendar:
    """Generate a complete HTML document for a wall calendar instance.

    The object wraps a lib.pycal.Calendar and exposes __html__ returning
    an ElementTree for writing to disk. CSS file locations are provided
    by CssResources.
    """
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
