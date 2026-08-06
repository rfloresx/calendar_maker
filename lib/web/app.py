"""NiceGUI application entry point for Calendar Maker Web GUI."""

import argparse
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Ensure the project root is on sys.path so `lib` is importable
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from nicegui import app, ui

from lib.web.config import DATA_PATH, PROJECTS_DIR
from lib.web.database import init_db

# Import pages to register routes
import lib.web.pages.projects
import lib.web.pages.wall_calendar
import lib.web.pages.desk_calendar
import lib.web.pages.birthdays
import lib.web.pages.photo_labels
import lib.web.pages.export
import lib.web.pages.settings


def setup():
    """Initialize database and serve static files."""
    init_db()
    # Serve project images as static files
    app.add_static_files("/project-files", str(PROJECTS_DIR))
    logger.info(f"Calendar Maker Web GUI starting. DATA_PATH={DATA_PATH}, PROJECTS_DIR={PROJECTS_DIR}")


def main():
    """Main entry point for the web GUI server."""
    parser = argparse.ArgumentParser(description="Calendar Maker Web GUI")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    setup()

    ui.run(
        title="Calendar Maker",
        host=args.host,
        port=args.port,
        reload=args.reload,
        show=False,
        dark=None,
    )


if __name__ == "__main__":
    main()
