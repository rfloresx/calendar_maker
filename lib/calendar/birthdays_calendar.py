"""
birthdays_calendar.py

Adapter that converts a lib.calendar.ics_loader.VCalendar of events (birthdays)
into the ObservedHolidayBase interface used by the project.

Each VCalendar event is expected to provide:
 - date: a datetime.date instance (only month and day are used to map into a target year)
 - summary: a short string used as the holiday name

The BirthdaysCalendar will create one holiday per event for the configured year(s).
This module contains a small example usage in the module's __main__ section.
"""

import datetime
from holidays.observed_holiday_base import (
    ObservedHolidayBase
)

try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

import lib.calendar.ics_loader as libics

class BirthdaysCalendar(ObservedHolidayBase):
    """Expose birthday events from a VCalendar as a holiday calendar.

    This class adapts events from a lib.calendar.ics_loader.VCalendar into the
    ObservedHolidayBase interface so they can be treated like public holidays
    by the rest of the codebase.

    Important:
      - The provided VCalendar must have an 'events' iterable. Each event must
        expose a `date` attribute (datetime.date) and a `summary` attribute (str).
      - Only the month and day from each event's date are used; the target year
        is provided by the ObservedHolidayBase (typically via the `years` or
        `year` arguments passed to the base class).

    Example:
        vcal = lib.calendar.ics_loader.VCalendar()
        vcal.add_event(datetime.date(2025, 1, 1), "Alice")
        cal = BirthdaysCalendar(vcalendar=vcal, years=(2025,))
        for d, name in cal.items():
            print(d, name)
    """
    country = "Birthdays"
    observed_label = "%s (observed)"
    start_year = 1777

    def __init__(self, vcalendar:libics.VCalendar, observed_rule = None, observed_since = None, *args, **kwargs):
        """Create a BirthdaysCalendar.

        Args:
            vcalendar (lib.calendar.ics_loader.VCalendar): source of events to
                convert to holidays.
            observed_rule: optional rule object forwarded to ObservedHolidayBase
                that controls how observed holidays are handled.
            observed_since: optional year (int) forwarded to ObservedHolidayBase
                indicating when observed rules start to apply.
            *args, **kwargs: additional arguments forwarded to ObservedHolidayBase
                (for example `years` or `year`).
        """
        self._vcalendar = vcalendar
        super().__init__(observed_rule, observed_since, *args, **kwargs)

    def _populate_public_holidays(self):
        """Populate the holiday dictionary from the VCalendar events.

        Iterates the events available on the provided VCalendar and registers
        a holiday for each event using the event's summary as the name and
        the event's month/day placed into the active year.
        """
        for event in self._vcalendar.events:
            date = event.date
            summary = event.summary
            self._add_holiday(summary, datetime.date(self._year, date.month, date.day))

if __name__ == "__main__":
    vcal = libics.VCalendar()
    dates = [(datetime.date(2025, 1, 1), "A"),
     (datetime.date(2025, 2, 1), "B"),
     (datetime.date(2025, 3, 1), "C"),
     (datetime.date(2025, 4, 1), "D")]
    for date in dates:
        vcal.add_event(date[0], date[1])
    
    birthdays = BirthdaysCalendar(vcalendar=vcal, years=(2025, 2026))
    for k,v in birthdays.items():
        print(k, v)
