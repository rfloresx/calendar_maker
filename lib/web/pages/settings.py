"""Settings page — manage API keys and application configuration."""

from nicegui import ui

from lib.web.database import get_db, set_config, get_config, AppConfig
from lib.web.config import DATA_PATH, CACHE_DIR


@ui.page("/settings")
def settings_page():
    """Application settings and configuration page."""
    with ui.header().classes("items-center justify-between bg-blue-800"):
        with ui.row().classes("items-center gap-2"):
            ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props("flat color=white round")
            ui.label("🗓️ Calendar Maker").classes("text-xl font-bold text-white")
        ui.label("Settings").classes("text-white text-lg")
        ui.element("div")  # spacer

    with ui.column().classes("w-full max-w-3xl mx-auto p-6"):
        ui.label("Application Settings").classes("text-2xl font-bold mb-6")

        # --- API Keys ---
        ui.label("API Keys").classes("text-xl font-medium mb-2")
        ui.label("API keys are stored in the database. Environment variables take priority if set.").classes("text-sm text-gray-500 mb-4")

        db = get_db()
        try:
            google_key = get_config(db, "GOOGLE_API_KEY")
        finally:
            db.close()

        google_input = ui.input(
            "Google Maps API Key",
            value=google_key,
            password=True,
            password_toggle_button=True,
        ).classes("w-full mb-2")

        def save_google_key():
            db = get_db()
            try:
                set_config(db, "GOOGLE_API_KEY", google_input.value, "Google Maps Places API key for location lookup")
            finally:
                db.close()
            ui.notify("API key saved", type="positive")

        ui.button("Save API Key", icon="save", on_click=save_google_key).props("color=primary").classes("mb-6")

        ui.separator()

        # --- Data Information ---
        ui.label("Data Storage").classes("text-xl font-medium mt-6 mb-2")

        with ui.card().classes("w-full"):
            ui.label(f"Data Path: {DATA_PATH}").classes("text-sm font-mono")
            ui.label(f"Cache Path: {CACHE_DIR}").classes("text-sm font-mono")

            # Count projects
            db = get_db()
            try:
                from lib.web.database import Project
                project_count = db.query(Project).count()
            finally:
                db.close()
            ui.label(f"Projects: {project_count}").classes("text-sm")

        ui.separator().classes("my-6")

        # --- Cache Management ---
        ui.label("Cache Management").classes("text-xl font-medium mb-2")

        def clear_cache():
            cache_file = CACHE_DIR / "geoutil_cache.json"
            if cache_file.exists():
                cache_file.unlink()
                ui.notify("Geo cache cleared", type="positive")
            else:
                ui.notify("No cache file found", type="info")

        ui.button("Clear Geo Cache", icon="delete_sweep", on_click=clear_cache).props("outline color=warning")

        ui.separator().classes("my-6")

        # --- About ---
        ui.label("About").classes("text-xl font-medium mb-2")
        ui.label("Calendar Maker — Web GUI").classes("text-sm")
        ui.label("A web-based calendar editor and exporter for creating printable wall and desk calendars.").classes("text-sm text-gray-500")
