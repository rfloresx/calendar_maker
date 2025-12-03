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
    country = "Birthdays"
    observed_label = "%s (observed)"
    start_year = 1777

    def __init__(self, vcalendar:libics.VCalendar, observed_rule = None, observed_since = None, *args, **kwargs):
        self._vcalendar = vcalendar
        super().__init__(observed_rule, observed_since, *args, **kwargs)

    def _populate_public_holidays(self):
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
    