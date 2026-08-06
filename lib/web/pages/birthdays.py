"""Birthdays page — manage birthday entries with ICS import and per-entry images."""

import datetime
from nicegui import ui, events

from lib.web.database import get_db, Birthday
from lib.web.components.layout import project_layout
from lib.web.storage import save_uploaded_image


def _load_birthdays(project_id: str):
    db = get_db()
    try:
        return db.query(Birthday).filter_by(project_id=project_id).order_by(Birthday.sort_order, Birthday.id).all()
    finally:
        db.close()


def _add_birthday(project_id: str, title: str = "", date: str = "", image_path: str = None):
    db = get_db()
    try:
        max_order = db.query(Birthday.sort_order).filter_by(project_id=project_id).order_by(Birthday.sort_order.desc()).first()
        next_order = (max_order[0] + 1) if max_order else 0
        bday = Birthday(project_id=project_id, title=title, date=date, image_path=image_path, sort_order=next_order)
        db.add(bday)
        db.commit()
        return bday.id
    finally:
        db.close()


def _update_birthday(birthday_id: int, field: str, value):
    db = get_db()
    try:
        bday = db.query(Birthday).filter_by(id=birthday_id).first()
        if bday:
            setattr(bday, field, value)
            db.commit()
    finally:
        db.close()


def _delete_birthday(birthday_id: int):
    db = get_db()
    try:
        bday = db.query(Birthday).filter_by(id=birthday_id).first()
        if bday:
            db.delete(bday)
            db.commit()
    finally:
        db.close()


def _sort_birthdays(project_id: str):
    db = get_db()
    try:
        birthdays = db.query(Birthday).filter_by(project_id=project_id).all()

        def sort_key(b):
            if b.date:
                try:
                    dt = datetime.datetime.strptime(b.date, "%d/%m/%Y")
                    return (dt.month, dt.day)
                except ValueError:
                    pass
            return (13, 0)

        birthdays.sort(key=sort_key)
        for i, bday in enumerate(birthdays):
            bday.sort_order = i
        db.commit()
    finally:
        db.close()


def _import_ics(project_id: str, content: bytes) -> int:
    import sys, tempfile, os
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from lib.calendar.ics_loader import VCalendar

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".ics", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        vcal = VCalendar(tmp_path)
        count = 0
        for ve in vcal.events:
            date = ve.date
            date_str = f"{date.day:02d}/{date.month:02d}/{datetime.datetime.now().year:04d}"
            _add_birthday(project_id, title=ve.summary, date=date_str)
            count += 1
        return count
    finally:
        os.unlink(tmp_path)


def _render_birthday_list(project_id: str, container):
    container.clear()
    birthdays = _load_birthdays(project_id)

    with container:
        if not birthdays:
            ui.label("No birthdays added yet.").classes("text-gray-500")
            return

        for bday in birthdays:
            with ui.card().classes("w-full mb-2"):
                with ui.row().classes("w-full items-center gap-4"):
                    # Image upload per entry
                    with ui.column().classes("items-center w-20"):
                        if bday.image_path:
                            ui.image(f"/project-files/{project_id}/{bday.image_path}").classes("w-16 h-12 object-cover rounded")

                        def make_img_handler(bid):
                            def handler(e: events.UploadEventArguments):
                                content = e.content.read()
                                path = save_uploaded_image(project_id, e.name, content)
                                _update_birthday(bid, "image_path", path)
                                _render_birthday_list(project_id, container)
                            return handler

                        ui.upload(
                            label="📷",
                            auto_upload=True,
                            on_upload=make_img_handler(bday.id),
                            max_file_size=10 * 1024 * 1024,
                        ).props('accept="image/*" flat dense').classes("w-16")

                    # Title
                    title_input = ui.input("Title", value=bday.title or "").classes("flex-1")
                    title_input.on("blur", lambda e, bid=bday.id, ti=title_input: _update_birthday(bid, "title", ti.value))

                    # Date
                    date_input = ui.input("Date (DD/MM/YYYY)", value=bday.date or "", placeholder="25/12/2026").classes("w-36")
                    date_input.on("blur", lambda e, bid=bday.id, di=date_input: _update_birthday(bid, "date", di.value))

                    # Delete
                    ui.button(icon="delete", on_click=lambda bid=bday.id: (_delete_birthday(bid), _render_birthday_list(project_id, container))).props("flat color=negative round size=sm")


@ui.page("/project/{project_id}/birthdays")
def birthdays_page(project_id: str):
    project_layout(project_id, active="birthdays")

    with ui.column().classes("w-full p-6"):
        ui.label("Birthdays").classes("text-2xl font-bold mb-4")
        list_container = ui.column().classes("w-full")

        with ui.row().classes("gap-2 mb-4"):
            ui.button("Add Birthday", icon="add", on_click=lambda: (_add_birthday(project_id), _render_birthday_list(project_id, list_container))).props("color=primary")
            ui.button("Sort by Date", icon="sort", on_click=lambda: (_sort_birthdays(project_id), _render_birthday_list(project_id, list_container))).props("outline")

            def handle_ics_upload(e: events.UploadEventArguments):
                content = e.content.read()
                count = _import_ics(project_id, content)
                ui.notify(f"Imported {count} birthday(s)", type="positive")
                _render_birthday_list(project_id, list_container)

            ui.upload(label="Import .ics", auto_upload=True, on_upload=handle_ics_upload).props('accept=".ics"').classes("w-auto")

        _render_birthday_list(project_id, list_container)
