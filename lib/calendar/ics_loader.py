from typing import List, Tuple, Dict, Any
import json
import datetime


class IcsParser:
    class Lines:
        def __init__(self, lines: List[str]):
            self._lines = lines
            self._index = 0

        def next(self) -> str:
            if self._index >= len(self._lines):
                return None
            val = self._lines[self._index]
            self._index += 1
            return val

    @staticmethod
    def loads(filename: str) -> dict:
        lines = IcsParser.Lines([])
        with open(filename, 'r') as file:
            lines = IcsParser.Lines(file.readlines())
        return IcsParser.parse_obj(lines)

    @staticmethod
    def parse_line(line: str) -> Tuple[str, str]:
        return line.split(':')

    @staticmethod
    def parse_obj(lines: 'IcsParser.Lines') -> dict:
        obj: Dict[str, List] = {}
        while True:
            line = lines.next()
            if line is None:
                return obj
            key, val = IcsParser.parse_line(line)
            key = key.strip()
            val = val.strip()
            if key == "BEGIN":
                key = val
                val = IcsParser.parse_obj(lines)
            elif key == "END":
                return obj
            if key not in obj:
                obj[key] = []
            obj[key].append(val)


class VCalendar:
    SUMMARY_KEY = "SUMMARY"
    DATE_KEY = "DTSTART;VALUE=DATE"
    IMAGES_KEY = "IMAGES"

    class VEvent:
        def __init__(self, data: dict):
            self._data = data

        @property
        def summary(self) -> str:
            return self._data.get(VCalendar.SUMMARY_KEY, [""])[0]

        @property
        def date(self) -> datetime.date:
            val = self._data.get(VCalendar.DATE_KEY, [""])[0]
            if isinstance(val, (datetime.date, datetime.datetime)):
                return val
            if val:
                return datetime.datetime.strptime(val, "%Y%m%d").date()
            return None

        @property
        def image(self) -> str:
            return self._data.get(VCalendar.IMAGES_KEY, [None])[0]

        def add(self, key: str, data: Any) -> None:
            _data = self._data.get(key, False)
            if not _data:
                _data = []
                self._data[key] = _data
            _data.append(data)

        def get(self, key) -> List[Any]:
            return self._data.get(key, [None])

        def __repr__(self):
            return str({"sumary": self.summary, "date": self.date})

    class EventMap:
        def __init__(self):
            self._data: Dict[int, Dict[int, List['VCalendar.VEvent']]] = {}

        def add_event(self, event: 'VCalendar.VEvent') -> None:
            date = event.date
            month = self._data.get(date.month, False)
            if not month:
                month = {}
                self._data[date.month] = month

            day = month.get(date.day, False)
            if not day:
                day = []
                month[date.day] = day
            day.append(event)

        def get_events(self, month: int = None, day: int = None) -> list['VCalendar.VEvent']:
            if month is not None:
                days = self._data.get(month, {})
                if day is not None:
                    if day in days:
                        return days[day].copy()
                    return []
                else:
                    events = []
                    for _, evs in days.items():
                        events.extend(evs)
                    return events
            else:
                events = []
                for _, days in self._data.items():
                    for _, evs in days.items():
                        events.extend(evs)
                return events

    def __init__(self, filename: str = None):
        self._events: VCalendar.EventMap = VCalendar.EventMap()
        if filename:
            root = IcsParser.loads(filename)
            vevents: List[dict] = root.get("VCALENDAR", [{}])[
                0].get("VEVENT", [])

            for event in vevents:
                self._events.add_event(VCalendar.VEvent(event))

    def add_event(self, date: datetime.date, summary: str) -> None:
        self._events.add_event(VCalendar.VEvent({
            VCalendar.SUMMARY_KEY: [summary],
            VCalendar.DATE_KEY: [date]
        }))

    @property
    def events(self) -> List['VCalendar.VEvent']:
        return self.get_events()

    def get_events(self, month: int = None, day: int = None) -> List['VCalendar.VEvent']:
        return self._events.get_events(month, day)

    def get(self, date: datetime.date) -> List['VCalendar.VEvent']:
        return self.get_events(date.month, date.day)

    def add(self, event: 'VCalendar.VEvent') -> None:
        self._events.add_event(event)


def TestVCalendar():
    vcal = VCalendar()
    dates = [(datetime.date(2025, 1, 1), "A"),
             (datetime.date(2025, 2, 1), "B"),
             (datetime.date(2025, 2, 2), "B1"),
             (datetime.date(2025, 2, 3), "B2"),
             (datetime.date(2025, 3, 1), "C"),
             (datetime.date(2025, 4, 1), "D")]
    for date in dates:
        vcal.add_event(date[0], date[1])
    return vcal


def main():
    vcal = VCalendar()
    dates = [(datetime.date(2025, 1, 1), "A"),
             (datetime.date(2025, 2, 1), "B"),
             (datetime.date(2025, 2, 2), "B1"),
             (datetime.date(2025, 2, 3), "B2"),
             (datetime.date(2025, 3, 1), "C"),
             (datetime.date(2025, 4, 1), "D")]
    for date in dates:
        vcal.add_event(date[0], date[1])

    # obj = IcsParser.loads("Birthdays.ics")
    print(json.dumps(vcal._events.__dict__,
          indent="    ", default=lambda obj: str(obj)))
    print(json.dumps(vcal.events, indent="    ", default=lambda obj: str(obj)))
    print(json.dumps(vcal.get_events(2), indent="    ", default=lambda obj: str(obj)))


if __name__ == "__main__":
    main()
