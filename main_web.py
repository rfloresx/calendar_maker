"""Entry point for the NiceGUI web-based calendar editor.

This runs alongside (not instead of) the wxPython desktop GUI.
Start with: .venv/bin/python main_web.py [--port PORT]
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

from nicegui import ui
from lib.webgui.app import create_app

create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calendar Editor Web GUI")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    ui.run(
        title="Calendar Editor",
        port=args.port,
        host=args.host,
        reload=False,
        show=not args.no_open,
    )
