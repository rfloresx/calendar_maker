# calendar_maker

Lightweight calendar editor and exporter (GUI) for creating printable wall and desk calendars, importing birthdays from ICS files and exporting images/HTML. This repository contains the editor UI, calendar model, renderers for image/HTML output and supporting resources (fonts, images, CSS).

Key features
- GUI editor (wx) for artworks, birthdays and settings
- Import birthdays from .ics files
- Render desk and wall calendar pages to images and HTML
- Moon phase and holiday integration

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

Development notes
- Fonts and image assets are included under lib/print/fonts and lib/resources; ensure licenses (OFL for EB Garamond) are respected when redistributing.
- For debugging GUI use a Python interpreter with a display (macOS GUI).

