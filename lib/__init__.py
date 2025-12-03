"""lib package

This package exposes a small collection of calendar-related modules used by
the application. The top-level imports provided here are convenience aliases
so callers can do `import lib` and access common submodules.
"""

import lib.calendar.holidays_ext as holidays_ext
import lib.calendar.moon_calendar as moon_calendar
import lib.pycal as pycal
import lib.gui.editor as editor
