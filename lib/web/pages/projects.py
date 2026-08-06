"""Projects page — list, create, delete, edit, import calendar projects."""

import datetime
import json
from nicegui import ui, events

from lib.web.database import get_db, generate_id, Project, ExportSettings, WallPage, DeskPage, Birthday
from lib.web.storage import delete_project_files

PROJECT_TYPES = {
    "wall": {"label": "Wall Calendar", "icon": "photo_library"},
    "desk": {"label": "Desk Calendar", "icon": "table_chart"},
    "photos": {"label": "Photo Labels", "icon": "photo_camera"},
}


def _get_default_route(project):
    """Return the default page route for a project based on its type."""
    ptype = getattr(project, 'project_type', 'wall') or 'wall'
    if ptype == "photos":
        return f"/project/{project.id}/photos"
    elif ptype == "desk":
        return f"/project/{project.id}/desk"
    else:
        return f"/project/{project.id}/wall"


def create_project_cards(container):
    container.clear()
    db = get_db()
    try:
        projects = db.query(Project).order_by(Project.updated_at.desc()).all()
        if not projects:
            with container:
                ui.label("No projects yet. Create one to get started!").classes("text-lg text-gray-500")
        else:
            with container:
                with ui.element("div").classes("grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"):
                    for project in projects:
                        _render_project_card(project, container)
    finally:
        db.close()


def _render_project_card(project: Project, parent_container):
    ptype = getattr(project, 'project_type', 'wall') or 'wall'
    type_info = PROJECT_TYPES.get(ptype, PROJECT_TYPES["wall"])
    with ui.card().classes("w-full cursor-pointer hover:shadow-lg transition-shadow"):
        with ui.card_section():
            with ui.row().classes("items-center gap-2"):
                ui.icon(type_info["icon"]).classes("text-blue-600")
                ui.label(project.name).classes("text-lg font-bold")
            ui.label(f"{type_info['label']} • {project.year}").classes("text-sm text-gray-600")
            updated = project.updated_at.strftime("%b %d, %Y") if project.updated_at else "—"
            ui.label(f"Modified: {updated}").classes("text-xs text-gray-400")
        with ui.card_actions().classes("justify-end"):
            ui.button("Open", on_click=lambda p=project: ui.navigate.to(_get_default_route(p))).props("flat color=primary")
            ui.button("Edit", on_click=lambda p=project: _edit_project(p, parent_container)).props("flat color=secondary")
            ui.button("Delete", on_click=lambda p=project: _confirm_delete(p, parent_container)).props("flat color=negative")


async def _edit_project(project, parent_container):
    ptype = getattr(project, 'project_type', 'wall') or 'wall'
    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("Edit Project").classes("text-xl font-bold mb-4")
        name_input = ui.input("Name", value=project.name).classes("w-full")
        year_input = ui.number("Year", value=project.year, min=2000, max=2100).classes("w-full")
        type_select = ui.select(
            {k: v["label"] for k, v in PROJECT_TYPES.items()},
            value=ptype,
            label="Project Type",
        ).classes("w-full")
        with ui.row().classes("justify-end w-full mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")

            def save():
                db = get_db()
                try:
                    p = db.query(Project).filter_by(id=project.id).first()
                    if p:
                        p.name = name_input.value
                        p.year = int(year_input.value)
                        p.project_type = type_select.value
                        db.commit()
                finally:
                    db.close()
                dialog.close()
                create_project_cards(parent_container)
                ui.notify("Project updated", type="positive")

            ui.button("Save", on_click=save).props("color=primary")
    dialog.open()


async def _confirm_delete(project: Project, parent_container):
    with ui.dialog() as dialog, ui.card():
        ui.label(f'Delete project "{project.name}"?').classes("text-lg")
        ui.label("This cannot be undone.").classes("text-sm text-gray-500")
        with ui.row().classes("justify-end w-full mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Delete", on_click=lambda: _do_delete(project, dialog, parent_container)).props("flat color=negative")
    dialog.open()


def _do_delete(project, dialog, parent_container):
    db = get_db()
    try:
        proj = db.query(Project).filter_by(id=project.id).first()
        if proj:
            db.delete(proj)
            db.commit()
        delete_project_files(project.id)
    finally:
        db.close()
    dialog.close()
    create_project_cards(parent_container)
    ui.notify(f'Project "{project.name}" deleted', type="positive")


def _show_create_dialog(cards_container):
    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("New Project").classes("text-xl font-bold mb-4")
        name_input = ui.input("Project Name", placeholder="My Calendar 2026").classes("w-full")
        type_select = ui.select(
            {k: v["label"] for k, v in PROJECT_TYPES.items()},
            value="wall",
            label="Project Type",
        ).classes("w-full")
        year_input = ui.number("Year", value=datetime.datetime.now().year, min=2000, max=2100).classes("w-full")
        with ui.row().classes("justify-end w-full mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Create", on_click=lambda: _do_create(
                name_input.value, int(year_input.value), type_select.value, dialog, cards_container
            )).props("color=primary")
    dialog.open()


def _do_create(name: str, year: int, project_type: str, dialog, cards_container):
    if not name or not name.strip():
        ui.notify("Please enter a project name", type="warning")
        return
    db = get_db()
    try:
        project = Project(id=generate_id(), name=name.strip(), year=year, project_type=project_type)
        db.add(project)
        db.add(ExportSettings(project_id=project.id))
        # Only create pages relevant to the project type
        if project_type in ("wall", "desk"):
            for i in range(13):
                db.add(WallPage(project_id=project.id, page_index=i))
                db.add(DeskPage(project_id=project.id, page_index=i))
        db.commit()
    finally:
        db.close()
    dialog.close()
    create_project_cards(cards_container)
    ui.notify(f'Project "{name}" created', type="positive")


def _import_project_json(content: bytes, cards_container):
    """Import a Project.json from the wxPython GUI."""
    data = json.loads(content)
    year = data.get("settings", {}).get("year", datetime.datetime.now().year)
    name = f"Imported {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
    db = get_db()
    try:
        pid = generate_id()
        project = Project(id=pid, name=name, year=year, project_type="wall")
        db.add(project)
        db.add(ExportSettings(project_id=pid))
        for i in range(13):
            db.add(WallPage(project_id=pid, page_index=i))
            db.add(DeskPage(project_id=pid, page_index=i))
        db.commit()
        for i, art in enumerate(data.get("artworks", {}).get("pages", [])[:13]):
            page = db.query(WallPage).filter_by(project_id=pid, page_index=i).first()
            if page:
                page.description = art.get("description", "")
        for i, art in enumerate(data.get("desk_pages", {}).get("pages", [])[:13]):
            page = db.query(DeskPage).filter_by(project_id=pid, page_index=i).first()
            if page:
                page.description = art.get("description", "")
        for bday_data in data.get("birthdays", {}).get("birthdays", []):
            db.add(Birthday(project_id=pid, title=bday_data.get("title", ""), date=bday_data.get("date", "")))
        db.commit()
    finally:
        db.close()
    ui.notify(f"Imported project: {name}", type="positive")
    create_project_cards(cards_container)


@ui.page("/")
def projects_page():
    with ui.header().classes("items-center justify-between bg-blue-800"):
        ui.label("🗓️ Calendar Maker").classes("text-xl font-bold text-white")
        ui.button(icon="settings", on_click=lambda: ui.navigate.to("/settings")).props("flat color=white round")

    with ui.column().classes("w-full max-w-6xl mx-auto p-6"):
        with ui.row().classes("w-full justify-between items-center mb-6"):
            ui.label("Projects").classes("text-2xl font-bold")
            with ui.row().classes("gap-2"):
                ui.button("New Project", icon="add", on_click=lambda: _show_create_dialog(cards_container)).props("color=primary")

                def handle_import_upload(e: events.UploadEventArguments):
                    content = e.content.read()
                    try:
                        _import_project_json(content, cards_container)
                    except Exception as ex:
                        ui.notify(f"Import failed: {str(ex)}", type="negative")

                ui.upload(label="Import Project.json", auto_upload=True, on_upload=handle_import_upload).props('accept=".json"').classes("w-auto")

        cards_container = ui.element("div").classes("w-full")
        create_project_cards(cards_container)
