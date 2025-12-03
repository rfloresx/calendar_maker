import holidays
import re
from holidays.countries import UnitedStates

from holidays.groups.christian import ChristianHolidays


class US(UnitedStates):
    supported_categories = (
        holidays.PUBLIC, holidays.UNOFFICIAL, holidays.CHRISTIAN)
    ignore_holidays = (
        "Carnival Monday",
        "Christmas Day 2",
        "Christmas Day 3",
        "Easter Monday",
        "Easter Tuesday",
    )

    def _populate_christian_holidays(self):
        exp = re.compile(r"Add (.+?) \(", flags=re.MULTILINE)
        exp2 = re.compile(r"Add (.+?)\.", flags=re.MULTILINE)
        for method in dir(ChristianHolidays):
            attr = getattr(ChristianHolidays, method)
            if callable(attr) and method.startswith('_add_'):
                m = exp.search(attr.__doc__)
                if not m:
                    m = exp2.search(attr.__doc__)
                if m:
                    name = m.group(1)
                    if name not in self.ignore_holidays:
                        attr(self, name)
                    # attr(self, name)
