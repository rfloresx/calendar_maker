"""Common HTML helpers shared by desk and wall calendar views.

Provides reusable fragments and utilities for rendering front pages and
moon phase overlays. This avoids duplication across deskcal_html and
wallcal_html while keeping module-specific encoders minimal.
"""

from typing import Optional
from xml.etree import ElementTree as ET

try:
    import lib as __lib
except Exception:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

import lib.pycal as _libcal
import lib.html.htmlutil as _libhtml
from lib.calendar.moon_calendar import _MoonCalendar


class MoonPhaseImages:
    """Provide file paths for moon-phase overlay images used in cells.

    The image() helper returns a relative path for the given moon phase
    constant defined by lib.calendar.moon_calendar._MoonCalendar.
    """
    NEW_MOON_PATH = "images/moon-phases/new-moon.png"
    FIRST_QUARTER_PATH = "images/moon-phases/first-quarter.png"
    FULL_MOON_PATH = "images/moon-phases/full-moon.png"
    THIRD_QUARTER_PATH = "images/moon-phases/third-quarter.png"

    @staticmethod
    def image(phase) -> Optional[str]:
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


def moon_phase_element(phase) -> Optional[ET.Element]:
    """Return an <img> HtmlTag for the moon phase or None.

    The element uses CSS class 'cell-moon-overlay' consistent with both
    desk and wall calendar layouts.
    """
    img = MoonPhaseImages.image(phase)
    if img:
        return _libhtml.HtmlTag('img', attrib={'class': 'cell-moon-overlay', 'src': img})
    return None


def front_page_element(front_page: _libcal.FrontPage) -> ET.Element:
    """Build the shared front page fragment used by both views.

    Structure:
        <div class="page-letter-landscape">
          <div class="front-page">
            <img class="front-page-img" src="..." />
            <div class="front-page-title"><p>...</p></div>
          </div>
          <div class="page-break"></div>
        </div>
    """
    page = _libhtml.HtmlTag('div', attrib={'class': 'page-letter-landscape'})
    fp = page.add('div', attrib={'class': 'front-page'})
    if getattr(front_page, 'image', None):
        fp.add('img', attrib={'class': 'front-page-img', 'src': front_page.image})
    if getattr(front_page, 'title', None):
        title = fp.add('div', attrib={'class': 'front-page-title'})
        title.add('p', text=front_page.title)
    page.add('div', attrib={'class': 'page-break'})
    return page
