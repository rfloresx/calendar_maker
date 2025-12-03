"""Unified font utilities for the print subpackage.

This module centralizes font discovery and factory behaviour previously
implemented separately in draw.py and print.py. It exposes a Fonts class
with an _Font factory, an open() helper that tries repository and resource
font locations, and a MAP of common font name mappings.
"""

import os
import PIL.ImageFont
from typing import Iterable

MODULE_DIR = os.path.dirname(os.path.realpath(__file__))
# Candidate font directories (search in order)
CANDIDATE_FONTS_DIRS = [
    os.path.join(MODULE_DIR, 'resources', 'fonts'),  # lib/print/resources/fonts
    os.path.join(MODULE_DIR, 'fonts'),              # lib/print/fonts (EB_Garamond bundle)
    os.path.join(os.path.dirname(MODULE_DIR), 'resources', 'fonts'),  # lib/resources/fonts
]


def _find_font_path(fontname: str) -> str | None:
    """Return a filesystem path to the font if it exists in any known folder."""
    for d in CANDIDATE_FONTS_DIRS:
        path = os.path.join(d, fontname)
        if os.path.exists(path):
            return path
    return None


class Fonts:
    """Factory providing access to bundled font files.

    API mirrors the previous implementations used in draw.py and print.py:
    - Fonts.open(fontname, size)
    - nested class _Font callable that returns a PIL FreeTypeFont
    - Fonts.MAP mapping common names to _Font instances
    - Fonts.fonts() generator
    """

    @staticmethod
    def open(fontname, size=10) -> PIL.ImageFont.FreeTypeFont:
        # Try known font directories first
        path = _find_font_path(fontname)
        if path:
            return PIL.ImageFont.truetype(path, size=size)
        # Fallback to loading by name (system font)
        return PIL.ImageFont.truetype(fontname, size=size)

    class _Font:
        def __init__(self, name) -> None:
            # Accept either a filename (with .ttf) or a base name. If a path
            # or extension is provided, use it as-is; otherwise append .ttf.
            self._name = name
            if name.endswith('.ttf') or os.path.sep in name:
                self._filename = name
            else:
                self._filename = f"{name}.ttf"

        @property
        def name(self) -> str:
            return self._name

        def __call__(self, size=10) -> PIL.ImageFont.FreeTypeFont:
            # This factory does not convert size units; callers should pass
            # device pixels (points) as appropriate for their DPI.
            return Fonts.open(self._filename, size=size)

        def __str__(self) -> str:
            return self._name

        def __repr__(self) -> str:
            return f'{self.__class__.__name__}({self._name})'

    @classmethod
    def fonts(cls) -> Iterable['_Font']:
        for val in cls.__dict__.values():
            if isinstance(val, Fonts._Font):
                yield val


# # Start with empty legacy variables to populate later
# Arial = Arial_Bold = Helvetica = Helvetica_Bold = Verdana = Verdana_Bold = Courier_New = None

# # Scan the bundled fonts/ tree and register any .ttf/.otf files. For each
# # discovered file we add two MAP entries: the relative path within
# # fonts/ (so Fonts.open can locate it via _find_font_path) and the base
# # filename without extension (a convenient lookup key).
# def _scan_bundle_fonts():
#     fonts_root = os.path.join(MODULE_DIR, 'fonts')
#     discovered = {}
#     if not os.path.isdir(fonts_root):
#         return discovered
#     for root, dirs, files in os.walk(fonts_root):
#         for fname in files:
#             if not fname.lower().endswith(('.ttf', '.otf')):
#                 continue
#             abs_path = os.path.join(root, fname)
#             # path relative to fonts/ directory (used by Fonts._Font)
#             rel = os.path.relpath(abs_path, fonts_root)
#             # Normalize to use os.path.join style separators (keeping platform behavior)
#             rel_key = rel
#             fobj = Fonts._Font(rel_key)
#             # register by relative path
#             if rel_key not in discovered:
#                 discovered[rel_key] = fobj
#             # register by base filename (no extension)
#             base = os.path.splitext(fname)[0]
#             if base not in discovered:
#                 discovered[base] = fobj
#     return discovered

# _discovered_fonts = _scan_bundle_fonts()
# Merge discovered fonts into the existing MAP
# MAP = {}
# MAP.update(_discovered_fonts)

# If EB Garamond was found, prefer it for legacy serif/sans/mono slots that
# historically mapped to Arial/Helvetica/Verdana/Courier_New in this project.
EBGaramond = None
EBGaramond_Bold = None
try:
    Arimo = Fonts._Font(os.path.join('Arimo', 'static', 'Arimo-Regular.ttf'))
    Arimo_Bold = Fonts._Font(os.path.join('Arimo', 'static', 'Arimo-Bold.ttf'))

    EBGaramond = Fonts._Font(os.path.join('EB_Garamond', 'static', 'EBGaramond-Regular.ttf'))
    EBGaramond_Bold = Fonts._Font(os.path.join('EB_Garamond', 'static', 'EBGaramond-Bold.ttf'))

    Roboto = Fonts._Font(os.path.join('Roboto', 'static', 'Roboto-Regular.ttf'))
    Roboto_Bold = Fonts._Font(os.path.join('Roboto', 'static', 'Roboto-Bold.ttf'))
except Exception:
    EBGaramond = None
    EBGaramond_Bold = None


MAP = {
    'Arimo': Arimo,
    'Arimo_Bold': Arimo_Bold,
    'EBGaramond': EBGaramond,
    'EBGaramond_Bold': EBGaramond_Bold,
    'Roboto': Roboto,
    'Roboto_Bold': Roboto_Bold,
}

