"""Photo labels page — web GUI.

Provides photo label management with add, multi-image import, sort, and delete.
"""

import datetime
from typing import List

from nicegui import events, ui

from lib.webgui.state import ProjectState
from lib.webgui.components.photo_card import PhotoCard, DEFAULT_LABEL_TEMPLATE


def photo_labels_content(state: ProjectState) -> None:
    """Render the photo labels management page."""
    cards: List[PhotoCard] = []

    def on_change():
        """Persist card data back to state."""
        state.photo_labels = {"photos": [c.to_dict() for c in cards]}

    def on_delete(card: PhotoCard):
        """Remove a photo card."""
        card.remove_from_ui()
        cards.remove(card)
        on_change()

    def add_photo():
        """Add a new empty photo entry."""
        data = {
            "image": None,
            "template": DEFAULT_LABEL_TEMPLATE,
            "selected_place_index": 0,
            "place_overrides": {},
        }
        with cards_container:
            card = PhotoCard(data=data, on_change=on_change, on_delete=on_delete)
        cards.append(card)
        on_change()

    def handle_photos_upload(e: events.UploadEventArguments):
        """Import a photo from upload."""
        from lib.filemanager import FilesManager

        fm = FilesManager.instance()
        content = e.content.read()
        target = fm.get_target_path(e.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            f.write(content)

        rel_path = fm.get_relative_path(str(target))
        data = {
            "image": rel_path,
            "template": DEFAULT_LABEL_TEMPLATE,
            "selected_place_index": 0,
            "place_overrides": {},
        }
        with cards_container:
            card = PhotoCard(data=data, on_change=on_change, on_delete=on_delete)
        cards.append(card)
        on_change()
        ui.notify(f"Added: {e.name}", type="positive")

    def sort_photos():
        """Sort cards by date and rebuild UI."""
        def sort_key(card: PhotoCard):
            dt = card.datetime_original
            return (dt is None, dt or datetime.datetime.min)

        cards.sort(key=sort_key)
        on_change()
        # Rebuild UI
        cards_container.clear()
        current_data = [c.to_dict() for c in cards]
        cards.clear()
        for data in current_data:
            with cards_container:
                card = PhotoCard(data=data, on_change=on_change, on_delete=on_delete)
            cards.append(card)

    # --- UI ---
    ui.label("Photo Labels").classes("text-2xl font-bold mb-4")
    ui.separator()

    with ui.row().classes("gap-2 mb-4"):
        ui.button("Add Photo", icon="add", on_click=add_photo)
        ui.upload(
            label="Import Photos",
            auto_upload=True,
            on_upload=handle_photos_upload,
            multiple=True,
        ).props("accept='.png,.jpg,.jpeg,.bmp' flat dense").classes("w-48")
        ui.button("Sort by Date", icon="sort", on_click=sort_photos)

    # Cards container
    cards_container = ui.column().classes("w-full gap-2")

    # Load existing photos
    existing = state.photo_labels.get("photos", [])
    for photo_data in existing:
        with cards_container:
            card = PhotoCard(data=photo_data, on_change=on_change, on_delete=on_delete)
        cards.append(card)
