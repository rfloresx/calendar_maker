"""Birthday card component for the web GUI.

Displays a single birthday entry with image upload, title, date picker,
and delete button.
"""

import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from nicegui import app as nicegui_app, events, ui

from lib.filemanager import FilesManager


class BirthdayCard:
    """UI card for a single birthday entry.

    Parameters:
        data: Dict with keys image, title, date (DD/MM/YYYY string).
        on_change: Callback when data changes.
        on_delete: Callback to remove this entry (receives the card instance).
    """

    def __init__(
        self,
        data: Dict[str, Any],
        on_change: Optional[Callable[[], None]] = None,
        on_delete: Optional[Callable[["BirthdayCard"], None]] = None,
    ):
        self._on_change = on_change
        self._on_delete = on_delete

        self._image: Optional[str] = data.get("image")
        self._title: str = data.get("title", "")
        self._date_str: str = data.get("date", datetime.datetime.now().strftime("%d/%m/%Y"))

        self._container = None
        self._build_ui()

    def _build_ui(self):
        self._container = ui.card().classes("w-full")
        with self._container:
            with ui.row().classes("w-full items-center gap-4"):
                # Image
                with ui.column().classes("items-center"):
                    self._image_display = ui.image(
                        self._get_image_src()
                    ).classes("w-32 h-24 object-cover rounded border")
                    ui.upload(
                        label="Image",
                        auto_upload=True,
                        on_upload=self._handle_upload,
                    ).props("accept='.png,.jpg,.jpeg,.bmp' dense").classes("w-32")

                # Title + Date
                with ui.column().classes("flex-grow gap-2"):
                    self._title_input = ui.input(
                        label="Name",
                        value=self._title,
                        on_change=self._on_title_change,
                    ).classes("w-full")

                    self._date_input = ui.input(
                        label="Date (DD/MM/YYYY)",
                        value=self._date_str,
                        on_change=self._on_date_change,
                    ).classes("w-full")

                # Delete button
                ui.button(
                    icon="delete",
                    on_click=self._on_delete_click,
                ).props("flat color=red")

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _handle_upload(self, e: events.UploadEventArguments):
        fm = FilesManager.instance()
        content = e.content.read()
        target = fm.get_target_path(e.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            f.write(content)
        self._image = fm.get_relative_path(str(target))
        self._image_display.set_source(self._get_image_src())
        self._notify_change()

    def _on_title_change(self, e):
        self._title = e.value or ""
        self._notify_change()

    def _on_date_change(self, e):
        self._date_str = e.value or ""
        self._notify_change()

    def _on_delete_click(self):
        if self._on_delete:
            self._on_delete(self)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_image_src(self) -> str:
        if not self._image:
            return "https://via.placeholder.com/128x96?text=No+Image"
        fm = FilesManager.instance()
        abs_path = str(fm.get_file_path(self._image))
        if Path(abs_path).exists():
            return nicegui_app.add_static_file(local_file=abs_path)
        return "https://via.placeholder.com/128x96?text=Not+Found"

    def _notify_change(self):
        if self._on_change:
            self._on_change()

    def remove_from_ui(self):
        """Remove this card's UI element."""
        if self._container:
            self._container.delete()

    def to_dict(self) -> Dict[str, Any]:
        """Export state matching Project.json birthday format."""
        return {
            "image": self._image,
            "title": self._title,
            "date": self._date_str,
        }
