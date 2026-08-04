"""NiceGUI application setup and routing.

Creates the web GUI app with navigation drawer, header, and page routing.
"""

from pathlib import Path
from typing import Optional

from nicegui import app, events, ui

from lib.webgui.state import ProjectState
from lib.webgui.pages.wall_pages import wall_pages_content
from lib.webgui.pages.desk_pages import desk_pages_content
from lib.webgui.pages.birthdays import birthdays_content
from lib.webgui.pages.photo_labels import photo_labels_content
from lib.webgui.pages.export import export_content
from lib.webgui.pages.settings import settings_content

# Module-level project state (single-user)
_state = ProjectState()


def _try_load_default_project():
    """Attempt to load Project.json from the default tmp/ directory."""
    from lib.filemanager import FilesManager
    try:
        fm = FilesManager.instance()
        project_file = fm.root / "Project.json"
        if project_file.exists():
            _state.load(project_file)
    except Exception:
        pass


def create_app() -> None:
    """Configure the NiceGUI application with all routes and shared layout."""

    _try_load_default_project()

    # Serve project images as static files so ui.image can display them
    _setup_static_files()

    @ui.page("/")
    def index():
        _page_layout(lambda: wall_pages_content(_state))

    @ui.page("/wall")
    def wall():
        _page_layout(lambda: wall_pages_content(_state))

    @ui.page("/desk")
    def desk():
        _page_layout(lambda: desk_pages_content(_state))

    @ui.page("/birthdays")
    def birthdays():
        _page_layout(lambda: birthdays_content(_state))

    @ui.page("/photos")
    def photos():
        _page_layout(lambda: photo_labels_content(_state))

    @ui.page("/export")
    def export_page():
        _page_layout(lambda: export_content(_state))

    @ui.page("/settings")
    def settings_page():
        _page_layout(lambda: settings_content(_state))


def _setup_static_files():
    """Register static file serving for project images."""
    # If project has a path, serve its images folder
    if _state.project_path and (_state.project_path / "images").exists():
        app.add_static_files("/project-images", str(_state.project_path / "images"))
    # Also serve from the default tmp directory
    from lib.filemanager import FilesManager
    try:
        fm = FilesManager.instance()
        images_dir = fm.root / "images"
        if images_dir.exists():
            app.add_static_files("/project-images", str(images_dir))
    except Exception:
        pass


def _page_layout(content_fn):
    """Shared page layout with header and navigation drawer."""

    # Header
    with ui.header().classes("bg-blue-800 text-white items-center"):
        ui.button(icon="menu", on_click=lambda: drawer.toggle()).props("flat color=white")
        title_text = "Calendar Editor"
        if _state.has_unsaved_changes:
            title_text += " *"
        ui.label(title_text).classes("text-xl font-bold")
        ui.space()
        # Project actions in header
        ui.button("New", icon="add", on_click=_on_new_project).props("flat color=white")
        ui.button("Open", icon="folder_open", on_click=_on_open_project).props("flat color=white")
        ui.button("Save", icon="save", on_click=_on_save_project).props("flat color=white")

    # Navigation drawer
    with ui.left_drawer(value=True).classes("bg-gray-100") as drawer:
        ui.label("Navigation").classes("text-lg font-semibold mb-2")
        ui.separator()
        _nav_item("Wall Pages", "/wall", "photo_library")
        _nav_item("Desk Calendar", "/desk", "calendar_today")
        _nav_item("Birthdays", "/birthdays", "cake")
        _nav_item("Photo Labels", "/photos", "photo")
        _nav_item("Export", "/export", "file_download")
        _nav_item("Settings", "/settings", "settings")

    # Main content area
    with ui.column().classes("w-full p-6 gap-4"):
        content_fn()


def _nav_item(label: str, target: str, icon: str):
    """Create a navigation link in the drawer."""
    with ui.link(target=target).classes("no-underline w-full"):
        with ui.row().classes("items-center gap-2 p-2 rounded hover:bg-gray-200 w-full"):
            ui.icon(icon).classes("text-gray-700")
            ui.label(label).classes("text-gray-800")


async def _on_new_project():
    """Handle new project action via a dialog."""
    with ui.dialog() as dialog, ui.card():
        ui.label("New Project").classes("text-lg font-bold")
        path_input = ui.input(
            label="Project directory",
            placeholder="/path/to/new/project",
        ).classes("w-96")

        with ui.row().classes("justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Create", on_click=lambda: _create_project(path_input.value, dialog))

    dialog.open()


def _create_project(path: str, dialog):
    """Create a new project at the given path."""
    if not path or not path.strip():
        ui.notify("Please enter a valid path", type="warning")
        return
    _state.new_project(Path(path.strip()))
    _setup_static_files()
    dialog.close()
    ui.notify(f"Project created at {path}", type="positive")
    ui.navigate.to("/wall")


async def _on_open_project():
    """Handle open project action via file upload dialog."""
    with ui.dialog() as dialog, ui.card():
        ui.label("Open Project").classes("text-lg font-bold")
        ui.label("Upload a Project.json file:").classes("text-sm text-gray-600")

        ui.upload(
            label="Select Project.json",
            auto_upload=True,
            on_upload=lambda e: _load_project_file(e, dialog),
        ).props("accept='.json'").classes("w-96")

        with ui.row().classes("justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")

    dialog.open()


def _load_project_file(e: events.UploadEventArguments, dialog):
    """Load project from uploaded JSON file."""
    import json
    try:
        content = e.content.read().decode("utf-8")
        data = json.loads(content)
        _state.from_json(data)
        _setup_static_files()
        dialog.close()
        ui.notify("Project loaded successfully", type="positive")
        ui.navigate.to("/wall")
    except Exception as ex:
        ui.notify(f"Failed to load project: {ex}", type="negative")


def _on_save_project():
    """Save the current project."""
    if not _state.project_path:
        ui.notify("No project loaded. Create or open a project first.", type="warning")
        return
    try:
        _state.save()
        ui.notify("Project saved", type="positive")
    except Exception as ex:
        ui.notify(f"Failed to save: {ex}", type="negative")
