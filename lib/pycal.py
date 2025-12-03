"""pycal — lightweight calendar model used by the application.

This module provides a small object model representing calendars, months,
days, events, moon phases and related helpers used by the GUI and export
logic. Public classes include EventsManager, Calendar, Month, Day and
supporting types such as FrontPage and CalendarArt.
"""

import sys
import calendar
import holidays
import datetime
from xml.etree import ElementTree as ET
from typing import List, Generator, Tuple
import pathlib

try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(__file__)))

import lib.calendar.moon_calendar as _moon_calendar
import lib.calendar.holidays_ext as _holidays_ext
import lib.calendar.ics_loader as libics


class EventsManager:
    """Manage events for a specific year.

    The EventsManager aggregates holidays, moon phases and birthday events
    and exposes a simple generator interface `get(date)` that yields
    zero-or-more Event instances for a given date.
    """
    class Event:
        """Base event object containing a date and a name (summary)."""
        def __init__(self, date: datetime.date, name: str):
            self._name: datetime.date = name
            self._date: str = date

        @property
        def date(self) -> datetime.date:
            """The date of the event as a datetime.date."""
            return self._date

        @property
        def name(self) -> str:
            """A short textual summary or name for the event."""
            return self._name

    class MoonPhase(Event):
        """Event representing a moon phase on a given date."""
        pass

    class Birthday(Event):
        """Event representing a birthday with an optional image.

        The Birthday event stores an image path in addition to the base
        Event attributes.
        """
        def __init__(self, image: str, *args, **kargs):
            self._image = image
            super().__init__(*args, **kargs)

        @property
        def image(self) -> str:
            """Path to an image associated with the birthday (may be None)."""
            return self._image

    def __init__(self, year, birthdays: libics.VCalendar={}):
        """Create an EventsManager for `year`.

        Args:
            year: target year used to generate moon phases and evaluate
                recurring events.
            birthdays: optional VCalendar instance containing birthday events.
        """
        self._us_holidays = _holidays_ext.US(categories=(
            holidays.PUBLIC, holidays.UNOFFICIAL, holidays.CHRISTIAN))
        self._moon_phases = _moon_calendar._MoonCalendar(years=(year))
        self._birthdays = birthdays

    def get(self, key: datetime.date) -> Generator['EventsManager.Event', None, None]:
        """Yield Event objects that occur on `key`.

        The generator yields holiday, moon-phase and birthday events when
        present for the given date.
        """
        holiday = self._us_holidays.get(key)
        if holiday:
            yield EventsManager.Event(key, str(holiday))

        moon_phase = self._moon_phases.get(key)
        if moon_phase:
            yield EventsManager.MoonPhase(key, str(moon_phase))

        birthdays = self._birthdays.get(key)
        if birthdays:
            for birthday in birthdays:
                summary = birthday.summary
                images = birthday.image
                yield EventsManager.Birthday(images, key, summary)


class FrontPage:
    """Simple model for the front (cover) page of a calendar."""
    def __init__(self, image: str = None, title: str = None):
        if not image:
            image = 'images/PXL_COVER.jpg'
        if not title:
            title = 'Calendar\n2025'
        self._image = image
        self._title = title

    @property
    def image(self) -> str:
        """Path to the cover image."""
        return self._image

    @image.setter
    def image(self, value) -> None:
        """Set the cover image path."""
        self._image = value

    @property
    def title(self) -> str:
        """Cover page title text."""
        return self._title

    @title.setter
    def title(self, value) -> None:
        """Set the cover title text."""
        self._title = value


class CalendarArt:
    """Model for additional full-page artwork used in the calendar."""
    def __init__(self, image: str = None, title: str = None):
        if not image:
            image = 'images/PXL_COVER.jpg'
        if not title:
            title = 'This is a sample\nCalendar Art, Austin, TX'
        self._image = image
        self._title = title

    @property
    def image(self) -> str:
        """Image path for the artwork."""
        return self._image

    @image.setter
    def image(self, value) -> None:
        """Set the artwork image path."""
        self._image = value

    @property
    def title(self) -> str:
        """Artwork title/description."""
        return self._title

    @title.setter
    def title(self, value) -> None:
        """Set the artwork title/description."""
        self._title = value


class MoonPhase:
    """Small wrapper storing a moon phase name."""
    def __init__(self, phase: str):
        self._phase = phase

    @property
    def phase(self) -> str:
        """Name of the moon phase (e.g. 'Full Moon')."""
        return self._phase


class Day:
    """Represents a single day cell in a month table.

    Attributes:
        day: integer day-of-month or None for empty cell.
        photo: optional image associated with the day.
        text: textual notes or event summaries for the day.
        moon_phase: MoonPhase instance or None.
    """
    def __init__(self, day: int = None, photo: str = None, text: str = None, moon_phase: str = None):
        self._day = day
        self._photo = photo
        self._text = text
        self._moon_phase = MoonPhase(moon_phase)

    @property
    def day(self) -> int:
        """Day of the month (1..31) or None for an empty cell."""
        return self._day

    @property
    def photo(self) -> str:
        """Optional image path associated with the day."""
        return self._photo

    @property
    def text(self) -> str:
        """Textual notes or event summaries for the day."""
        return self._text

    @property
    def moon_phase(self) -> MoonPhase:
        """MoonPhase object for the day (may wrap None)."""
        return self._moon_phase


class Month:
    """Simple month model that constructs a 6x7 table of Day cells.

    The Month class generates week rows for the given year and month and
    populates Day objects with events from an optional EventsManager.
    """
    def __init__(self, year: int = 2025, month: int = 1, events: EventsManager = None):
        self._year = year
        self._month = month
        calendar.setfirstweekday(calendar.SUNDAY)
        cal = calendar.monthcalendar(self._year, self._month)
        self._cells: List[List[Day]] = []
        for row in cal:
            week: List[Day] = []
            for day in row:
                day = day if day else None
                photo = None
                lines = []
                moon_phase = None
                if day and events:
                    for event in events.get(datetime.date(self._year, self._month, day)):
                        if isinstance(event, EventsManager.MoonPhase):
                            moon_phase = event.name
                        elif isinstance(event, EventsManager.Birthday):
                            photo = event.image
                            lines.append(event.name)
                        elif isinstance(event, EventsManager.Event):
                            lines.append(event.name)
                text = None
                if lines:
                    text = ';\n'.join(lines)

                week.append(Day(day=day, photo=photo,
                            text=text, moon_phase=moon_phase))
            self._cells.append(week)
        if len(self._cells) < 6:
            self._cells.append([Day() for i in range(7)])
        self._days = ["Sunday", "Monday", "Tuesday",
                      "Wednesday", "Thursday", "Friday", "Saturday"]

        self._photo = None
        self._text = None
        self._name = calendar.month_name[self._month]

    @property
    def year(self) -> int:
        """Year of the month."""
        return self._year

    @property
    def month(self) -> int:
        """Numeric month (1..12)."""
        return self._month

    @property
    def name(self):
        """Localized month name (e.g. 'January')."""
        return self._name

    @property
    def table(self) -> Tuple[List[str], List[List[Day]]]:
        """Return a tuple (weekdays, cells) where cells is a 2D list of Day."""
        return [self._days, self._cells]


class Calendar:
    """High-level calendar composed of months and front-page/artwork.

    The Calendar class builds MonthInfo objects for each month of the
    requested year and exposes convenience accessors for pages, arts,
    and front page data used by the UI and exporters.
    """
    class MonthInfo:
        """Container for a Month and its associated CalendarArt."""
        def __init__(self, year: int, month: int, events: EventsManager):
            self._month = Month(year, month, events)
            self._art = CalendarArt()

        @property
        def month(self) -> Month:
            """The Month instance for this entry."""
            return self._month

        @property
        def art(self) -> CalendarArt:
            """Associated CalendarArt for this entry."""
            return self._art

    def __init__(self, year: int = 2025, events: EventsManager = None):
        """Create a Calendar for `year` optionally populated with events."""
        self._year: int = year
        self._front_page: FrontPage = FrontPage()
        self._months: List[Calendar.MonthInfo] = []
        for i in range(1, 13):
            self._months.append(Calendar.MonthInfo(self._year, i, events))

    @property
    def year(self) -> int:
        """Year for this calendar."""
        return self._year

    @property
    def front_page(self) -> FrontPage:
        """FrontPage object containing cover image and title."""
        return self._front_page

    @property
    def months(self) -> List[Month]:
        """List of Month objects representing each month in the calendar."""
        return [mi.month for mi in self._months]

    @property
    def arts(self) -> List[CalendarArt]:
        """List of CalendarArt objects used for full-page artworks."""
        return [mi.art for mi in self._months]

    @property
    def pages(self) -> List['Calendar.MonthInfo']:
        """List of MonthInfo objects for building page-based exports."""
        return self._months
