"""Moon phases as a holiday-style calendar provider.

This module implements _MoonCalendar, a small ObservedHolidayBase subclass
that exposes moon phases (new, first quarter, full, last quarter) as
holiday-like entries for a given year. The class is used by EventsManager
in lib.pycal to include moon-phase events in the generated calendar.
"""

import ephem
import datetime
from holidays.observed_holiday_base import (
    ObservedHolidayBase
)

class _MoonCalendar(ObservedHolidayBase):
    """ObservedHolidayBase subclass that adds moon phase dates as holidays.

    The class computes the sequential moon phases starting from January 1st
    of the target year and continues adding phases until the next year is
    reached.
    """
    country = "MOON"
    observed_label = "%s (observed)"
    start_year = 1777
    NEW_MOON="New Moon"
    FIRST_QUARTER="First Quarter"
    FULL_MOON="Full Moon"
    THIRD_QUARTER="Third Quarter"
    def _populate_public_holidays(self):
        date = datetime.date(self._year, 1, 1)
        phases = [
            (ephem.next_new_moon(date), _MoonCalendar.NEW_MOON),
            (ephem.next_first_quarter_moon(date), _MoonCalendar.FIRST_QUARTER),
            (ephem.next_full_moon(date), _MoonCalendar.FULL_MOON),
            (ephem.next_last_quarter_moon(date), _MoonCalendar.THIRD_QUARTER),
        ]
        phases = sorted(phases, key =lambda k:k[0])
        last_date = None
        last_phase = None
        for k,v in phases:
            last_date = k.datetime()
            last_phase = v
            self._add_holiday(v, last_date)
        next_year = datetime.datetime(self._year+1, 1, 1)
        while (last_date != None):
            if last_phase == _MoonCalendar.NEW_MOON:
                last_phase = _MoonCalendar.FIRST_QUARTER
                last_date = ephem.next_first_quarter_moon(last_date).datetime()
            elif last_phase == _MoonCalendar.FIRST_QUARTER:
                last_phase = _MoonCalendar.FULL_MOON
                last_date = ephem.next_full_moon(last_date).datetime()
            elif last_phase == _MoonCalendar.FULL_MOON:
                last_phase = _MoonCalendar.THIRD_QUARTER
                last_date = ephem.next_last_quarter_moon(last_date).datetime()
            elif last_phase ==  _MoonCalendar.THIRD_QUARTER:
                last_phase = _MoonCalendar.NEW_MOON
                last_date = ephem.next_new_moon(last_date).datetime()
            if last_date < next_year:
                self._add_holiday(last_phase, last_date)
            else:
                last_date = None
                last_phase = None

if __name__ == "__main__":
    moon = _MoonCalendar(years=(2025))
    for k,v in moon.items():
        print(k, v)
