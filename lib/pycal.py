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
    class Event:
        def __init__(self, date: datetime.date, name: str):
            self._name: datetime.date = name
            self._date: str = date

        @property
        def date(self) -> datetime.date:
            return self._date

        @property
        def name(self) -> str:
            return self._name

    class MoonPhase(Event):
        pass

    class Birthday(Event):
        def __init__(self, image: str, *args, **kargs):
            self._image = image
            super().__init__(*args, **kargs)

        @property
        def image(self) -> str:
            return self._image

    def __init__(self, year, birthdays: libics.VCalendar={}):
        self._us_holidays = _holidays_ext.US(categories=(
            holidays.PUBLIC, holidays.UNOFFICIAL, holidays.CHRISTIAN))
        self._moon_phases = _moon_calendar._MoonCalendar(years=(year))
        self._birthdays = birthdays

    def get(self, key: datetime.date) -> Generator['EventsManager.Event', None, None]:
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
    def __init__(self, image: str = None, title: str = None):
        if not image:
            image = 'images/PXL_COVER.jpg'
        if not title:
            title = 'Calendar\n2025'
        self._image = image
        self._title = title

    @property
    def image(self) -> str:
        return self._image

    @image.setter
    def image(self, value) -> None:
        self._image = value

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value) -> None:
        self._title = value


class CalendarArt:
    def __init__(self, image: str = None, title: str = None):
        if not image:
            image = 'images/PXL_COVER.jpg'
        if not title:
            title = 'This is a sample\nCalendar Art, Austin, TX'
        self._image = image
        self._title = title

    @property
    def image(self) -> str:
        return self._image

    @image.setter
    def image(self, value) -> None:
        self._image = value

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value) -> None:
        self._title = value


class MoonPhase:
    def __init__(self, phase: str):
        self._phase = phase

    @property
    def phase(self) -> str:
        return self._phase


class Day:
    def __init__(self, day: int = None, photo: str = None, text: str = None, moon_phase: str = None):
        self._day = day
        self._photo = photo
        self._text = text
        self._moon_phase = MoonPhase(moon_phase)

    @property
    def day(self) -> int:
        return self._day

    @property
    def photo(self) -> str:
        return self._photo

    @property
    def text(self) -> str:
        return self._text

    @property
    def moon_phase(self) -> MoonPhase:
        return self._moon_phase


class Month:
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
        return self._year

    @property
    def month(self) -> int:
        return self._month

    @property
    def name(self):
        return self._name

    @property
    def table(self) -> Tuple[List[str], List[List[Day]]]:
        return [self._days, self._cells]


class Calendar:
    class MonthInfo:
        def __init__(self, year: int, month: int, events: EventsManager):
            self._month = Month(year, month, events)
            self._art = CalendarArt()

        @property
        def month(self) -> Month:
            return self._month

        @property
        def art(self) -> CalendarArt:
            return self._art

    def __init__(self, year: int = 2025, events: EventsManager = None):
        self._year: int = year
        self._front_page: FrontPage = FrontPage()
        self._months: List[Calendar.MonthInfo] = []
        for i in range(1, 13):
            self._months.append(Calendar.MonthInfo(self._year, i, events))

    @property
    def year(self) -> int:
        return self._year

    @property
    def front_page(self) -> FrontPage:
        return self._front_page

    @property
    def months(self) -> List[Month]:
        return [mi.month for mi in self._months]

    @property
    def arts(self) -> List[CalendarArt]:
        return [mi.art for mi in self._months]

    @property
    def pages(self) -> List['Calendar.MonthInfo']:
        return self._months
