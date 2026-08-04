"""Settings page — web GUI."""

from nicegui import ui

from lib.webgui.state import ProjectState


def settings_content(state: ProjectState) -> None:
    """Render the global settings page."""
    ui.label("Settings").classes("text-2xl font-bold mb-4")
    ui.separator()

    with ui.column().classes("gap-4 w-96"):
        ui.number(
            label="Calendar Year",
            value=state.year,
            min=2000,
            max=2055,
            step=1,
            format="%.0f",
            on_change=lambda e: _set_year(state, int(e.value)),
        )

        ui.label(
            f"Project: {state.project_path or '(no project loaded)'}"
        ).classes("text-sm text-gray-600")


def _set_year(state: ProjectState, value: int):
    state.year = value
