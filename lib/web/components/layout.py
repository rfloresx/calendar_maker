"""Shared layout for project editor pages with sidebar navigation."""

from nicegui import ui

from lib.web.database import get_db, Project


def project_layout(project_id: str, active: str = "wall"):
    """Create the common layout for project editor pages.

    Args:
        project_id: The project UUID.
        active: The currently active section ('wall', 'desk', 'birthdays', 'photos', 'export').

    Returns:
        A content container element to place page content inside.
    """
    db = get_db()
    try:
        project = db.query(Project).filter_by(id=project_id).first()
        project_name = project.name if project else "Unknown"
        project_year = project.year if project else ""
    finally:
        db.close()

    # Header
    with ui.header().classes("items-center justify-between bg-blue-800"):
        with ui.row().classes("items-center gap-2"):
            ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/")).props("flat color=white round")
            ui.label("🗓️ Calendar Maker").classes("text-xl font-bold text-white")
        ui.label(f"{project_name} ({project_year})").classes("text-white text-lg")
        ui.button(icon="settings", on_click=lambda: ui.navigate.to("/settings")).props("flat color=white round")

    # Left drawer (sidebar)
    with ui.left_drawer(value=True).classes("bg-gray-50 p-4") as drawer:
        ui.label(project_name).classes("text-lg font-bold mb-2")
        ui.label(f"Year: {project_year}").classes("text-sm text-gray-500 mb-4")
        ui.separator()

        nav_items = [
            ("wall", "Wall Calendar", "photo_library", f"/project/{project_id}/wall"),
            ("desk", "Desk Calendar", "table_chart", f"/project/{project_id}/desk"),
            ("birthdays", "Birthdays", "cake", f"/project/{project_id}/birthdays"),
            ("photos", "Photo Labels", "photo_camera", f"/project/{project_id}/photos"),
            ("export", "Export", "file_download", f"/project/{project_id}/export"),
        ]

        for key, label, icon, path in nav_items:
            btn = ui.button(
                label,
                icon=icon,
                on_click=lambda p=path: ui.navigate.to(p),
            ).classes("w-full justify-start mb-1")
            if key == active:
                btn.props("color=primary")
            else:
                btn.props("flat color=dark")

        ui.separator().classes("my-4")
        ui.button("← Back to Projects", on_click=lambda: ui.navigate.to("/")).props("flat color=dark").classes("w-full justify-start")

    return drawer
