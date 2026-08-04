"""Birthdays page — web GUI.

Provides birthday management with add, import ICS, sort, and delete.
"""

import datetime
from typing import List

from nicegui import events, ui

from lib.webgui.state import ProjectState
from lib.webgui.components.birthday_card import BirthdayCard


def birthdays_content(state: ProjectState) -> None:
    """Render the birthdays management page."""
    cards: List[BirthdayCard] = []

    def on_change():
        """Persist card data back to state."""
        state.birthdays = {"birthdays": [c.to_dict() for c in cards]}

    def on_delete(card: BirthdayCard):
        """Remove a birthday card."""
        card.remove_from_ui()
        cards.remove(card)
        on_change()

    def add_birthday():
        """Add a new empty birthday entry."""
        data = {
            "image": None,
            "title": "",
            "date": datetime.datetime.now().strftime("%d/%m/%Y"),
        }
        with cards_container:
            card = BirthdayCard(data=data, on_change=on_change, on_delete=on_delete)
        cards.append(card)
        on_change()

    def handle_ics_upload(e: events.UploadEventArguments):
        """Import birthdays from an uploaded .ics file."""
        import tempfile
        import os
        from lib.calendar.ics_loader import VCalendar

        # Write uploaded content to a temp file
        content = e.content.read()
        tmp_path = os.path.join(tempfile.gettempdir(), "import_birthdays.ics")
        with open(tmp_path, "wb") as f:
            f.write(content)

        try:
            vcal = VCalendar(tmp_path)
            imported = 0
            for ve in vcal.events:
                date = ve.date
                if date is None:
                    continue
                date_str = datetime.datetime(
                    datetime.datetime.today().year, date.month, date.day
                ).strftime("%d/%m/%Y")
                data = {
                    "image": None,
                    "title": ve.summary or "",
                    "date": date_str,
                }
                with cards_container:
                    card = BirthdayCard(data=data, on_change=on_change, on_delete=on_delete)
                cards.append(card)
                imported += 1

            on_change()
            ui.notify(f"Imported {imported} birthday(s)", type="positive")
        except Exception as ex:
            ui.notify(f"Failed to import ICS: {ex}", type="negative")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def sort_birthdays():
        """Sort cards by date and rebuild UI."""
        def parse_date(card: BirthdayCard):
            try:
                d = card.to_dict()["date"]
                return datetime.datetime.strptime(d, "%d/%m/%Y")
            except (ValueError, TypeError):
                return datetime.datetime.max

        cards.sort(key=parse_date)
        on_change()
        # Rebuild UI
        cards_container.clear()
        current_data = [c.to_dict() for c in cards]
        cards.clear()
        for data in current_data:
            with cards_container:
                card = BirthdayCard(data=data, on_change=on_change, on_delete=on_delete)
            cards.append(card)

    # --- UI ---
    ui.label("Birthdays").classes("text-2xl font-bold mb-4")
    ui.separator()

    with ui.row().classes("gap-2 mb-4"):
        ui.button("Add Birthday", icon="add", on_click=add_birthday)
        ui.upload(
            label="Import ICS",
            auto_upload=True,
            on_upload=handle_ics_upload,
        ).props("accept='.ics' flat dense").classes("w-40")
        ui.button("Sort by Date", icon="sort", on_click=sort_birthdays)

    # Cards container
    cards_container = ui.column().classes("w-full gap-2")

    # Load existing birthdays
    existing = state.birthdays.get("birthdays", [])
    for bday_data in existing:
        with cards_container:
            card = BirthdayCard(data=bday_data, on_change=on_change, on_delete=on_delete)
        cards.append(card)
