"""lib package

This package exposes a small collection of calendar-related modules used by
the application. The top-level imports provided here are convenience aliases
so callers can do `import lib` and access common submodules.

Note: wx-dependent modules (gui.editor) are imported conditionally so that
the web GUI can use other lib submodules without requiring wxPython.
"""

import lib.calendar.holidays_ext as holidays_ext
import lib.calendar.moon_calendar as moon_calendar
import lib.pycal as pycal

try:
    import lib.gui.editor as editor
except ImportError:
    # wxPython not available (e.g., running the web GUI only)
    editor = None
