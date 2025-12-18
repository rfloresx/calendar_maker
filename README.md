# calendar_maker

Lightweight calendar editor and exporter (GUI) for creating printable wall and desk calendars, importing birthdays from ICS files and exporting images/HTML. This repository contains the editor UI, calendar model, renderers for image/HTML output and supporting resources (fonts, images, CSS).

![GUI Screenshot](docs/gui.png)

Key features
- GUI editor (wx) for artworks, birthdays and settings
- Import birthdays from .ics files
- Render desk and wall calendar pages to images and HTML
- Moon phase and holiday integration
- **Template-based descriptions** with variable replacements:
  - `{year}` - Current calendar year
  - `{date:%b %d}` - Photo date with custom formatting
  - `{place.name}`, `{place.city}`, `{place.state}`, `{place.country}` - Place information
- **Editable place metadata** - Edit or add location details manually, even for photos without GPS data
- **Image metadata integration** - Automatically extracts date and location from photo EXIF data
- **Unsaved changes warning** - Alerts when closing with unsaved work
- **Responsive UI** - Dynamic window resizing with proper layout adaptation

Quick start (macOS)
1. Install Python 3.11+ (3.12 recommended)
2. Create and activate a virtual environment:
   python -m venv .venv
   source .venv/bin/activate
3. Install required packages:
   python -m pip install -r requirements.txt

Run
- Start the editor UI:
  python main.py

Project layout (important folders)
- lib/ — application code (gui, calendar logic, renderers, print)
- lib/resources/ — CSS, fonts and images used by renderers
- tmp/ — temporary project data and example Project.json
- docs/ — documentation and screenshots

Development notes
- Fonts and image assets are included under lib/print/fonts and lib/resources; ensure licenses (OFL for EB Garamond) are respected when redistributing.
- For debugging GUI use a Python interpreter with a display (macOS GUI).
- The editor supports template variables in artwork descriptions for dynamic content generation.
- Place overrides are saved per-image and persist across sessions.

