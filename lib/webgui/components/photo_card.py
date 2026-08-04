"""Photo label card component for the web GUI.

Displays a single photo entry with image upload, label template editing,
rendered preview, place selection, and editable place fields.
"""

import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from nicegui import app as nicegui_app, events, ui

from lib.filemanager import FilesManager
from lib.template import (
    ImageInfo,
    TextTemplate,
    build_text_context,
    get_image_metadata,
)

DEFAULT_LABEL_TEMPLATE = "{place.name}\n{place.city}, {place.state}. {date:%b %d}"


class PhotoCard:
    """UI card for a single photo label entry.

    Parameters:
        data: Dict with keys image, template, selected_place_index, place_overrides.
        on_change: Callback when data changes.
        on_delete: Callback to remove this entry (receives the card instance).
    """

    def __init__(
        self,
        data: Dict[str, Any],
        on_change: Optional[Callable[[], None]] = None,
        on_delete: Optional[Callable[["PhotoCard"], None]] = None,
    ):
        self._on_change = on_change
        self._on_delete = on_delete

        self._image: Optional[str] = data.get("image")
        self._template: str = data.get("template", DEFAULT_LABEL_TEMPLATE)
        self._selected_place_index: int = data.get("selected_place_index", 0)
        self._place_overrides: Dict[int, Dict[str, str]] = {
            int(k): v for k, v in (data.get("place_overrides") or {}).items()
        }

        # Metadata
        self._metadata: Dict[str, Any] = {}
        self._places: list = []
        if self._image:
            self._resolve_metadata()

        self._container = None
        self._build_ui()

    def _resolve_metadata(self):
        if not self._image:
            self._metadata = {}
            self._places = []
            return
        fm = FilesManager.instance()
        abs_path = str(fm.get_file_path(self._image))
        if Path(abs_path).exists():
            self._metadata = get_image_metadata(abs_path)
            info = ImageInfo(metadata=self._metadata)
            self._places = info.places
        else:
            self._metadata = {}
            self._places = []

    def _build_ui(self):
        self._container = ui.card().classes("w-full")
        with self._container:
            with ui.row().classes("w-full items-start gap-4"):
                # Left: image + preview
                with ui.column().classes("items-center gap-1"):
                    self._image_display = ui.image(
                        self._get_image_src()
                    ).classes("w-48 h-36 object-cover rounded border")

                    ui.upload(
                        label="Choose photo",
                        auto_upload=True,
                        on_upload=self._handle_upload,
                    ).props("accept='.png,.jpg,.jpeg,.bmp' dense").classes("w-48")

                    # Label preview
                    self._preview_label = ui.label(
                        self._rendered_label()
                    ).classes("text-sm italic text-gray-600 w-48 break-words")

                # Right: template + place
                with ui.column().classes("flex-grow gap-2"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Label Template").classes("text-sm font-medium")
                        ui.button(
                            icon="delete",
                            on_click=self._on_delete_click,
                        ).props("flat color=red dense")

                    self._template_input = ui.textarea(
                        value=self._template,
                        on_change=self._on_template_change,
                    ).classes("w-full").props("rows=2")

                    # Metadata
                    self._meta_label = ui.label(
                        self._metadata_summary()
                    ).classes("text-xs text-gray-500")

                    # Place selector
                    if self._places:
                        place_options = {
                            i: f"{getattr(p, 'name', '')}, {getattr(p, 'city', '')}, {getattr(p, 'state', '')}"
                            for i, p in enumerate(self._places)
                        }
                        self._place_select = ui.select(
                            options=place_options,
                            value=self._selected_place_index,
                            label="Place",
                            on_change=self._on_place_select,
                        ).classes("w-full")

                    # Editable place fields
                    overrides = self._place_overrides.get(self._selected_place_index, {})
                    with ui.row().classes("w-full gap-2"):
                        self._name_input = ui.input(
                            label="Name",
                            value=overrides.get("name", self._place_field("name")),
                            on_change=self._on_place_field_change,
                        ).classes("flex-grow")
                        self._city_input = ui.input(
                            label="City",
                            value=overrides.get("city", self._place_field("city")),
                            on_change=self._on_place_field_change,
                        ).classes("flex-grow")
                        self._state_input = ui.input(
                            label="State",
                            value=overrides.get("state", self._place_field("state")),
                            on_change=self._on_place_field_change,
                        ).classes("flex-grow")

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
        self._resolve_metadata()
        self._image_display.set_source(self._get_image_src())
        self._meta_label.set_text(self._metadata_summary())
        self._preview_label.set_text(self._rendered_label())
        self._notify_change()

    def _on_template_change(self, e):
        self._template = e.value or DEFAULT_LABEL_TEMPLATE
        self._preview_label.set_text(self._rendered_label())
        self._notify_change()

    def _on_place_select(self, e):
        self._selected_place_index = e.value
        overrides = self._place_overrides.get(self._selected_place_index, {})
        self._name_input.set_value(overrides.get("name", self._place_field("name")))
        self._city_input.set_value(overrides.get("city", self._place_field("city")))
        self._state_input.set_value(overrides.get("state", self._place_field("state")))
        self._preview_label.set_text(self._rendered_label())
        self._notify_change()

    def _on_place_field_change(self, e):
        self._place_overrides[self._selected_place_index] = {
            "name": self._name_input.value or "",
            "city": self._city_input.value or "",
            "state": self._state_input.value or "",
        }
        self._preview_label.set_text(self._rendered_label())
        self._notify_change()

    def _on_delete_click(self):
        if self._on_delete:
            self._on_delete(self)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_image_src(self) -> str:
        if not self._image:
            return "https://via.placeholder.com/192x144?text=No+Image"
        fm = FilesManager.instance()
        abs_path = str(fm.get_file_path(self._image))
        if Path(abs_path).exists():
            return nicegui_app.add_static_file(local_file=abs_path)
        return "https://via.placeholder.com/192x144?text=Not+Found"

    def _rendered_label(self) -> str:
        overrides = self._place_overrides.get(self._selected_place_index)
        try:
            image_info = ImageInfo(metadata=self._metadata)
            ctx = build_text_context(
                image_info=image_info,
                selected_place_index=self._selected_place_index,
                overrides=overrides,
            )
            return TextTemplate(self._template).render(ctx)
        except Exception:
            return self._template

    def _metadata_summary(self) -> str:
        parts = []
        dto = self._metadata.get("DateTimeOriginal")
        if dto:
            parts.append(f"Date: {dto}")
        lat = self._metadata.get("GPSLatitude")
        lon = self._metadata.get("GPSLongitude")
        if lat is not None and lon is not None:
            parts.append(f"GPS: {lat:.4f}, {lon:.4f}")
        return " | ".join(parts) if parts else "No metadata"

    def _place_field(self, field: str) -> str:
        if self._places and self._selected_place_index < len(self._places):
            return getattr(self._places[self._selected_place_index], field, "") or ""
        return ""

    def _notify_change(self):
        if self._on_change:
            self._on_change()

    def remove_from_ui(self):
        """Remove this card from the UI."""
        if self._container:
            self._container.delete()

    @property
    def datetime_original(self) -> Optional[datetime.datetime]:
        """For sorting — returns the image's DateTimeOriginal or None."""
        dto = self._metadata.get("DateTimeOriginal")
        if dto:
            try:
                return datetime.datetime.strptime(dto, "%Y:%m:%d %H:%M:%S")
            except (ValueError, TypeError):
                pass
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Export state matching Project.json photo_labels format."""
        return {
            "image": self._image,
            "template": self._template,
            "selected_place_index": self._selected_place_index,
            "place_overrides": {str(k): v for k, v in self._place_overrides.items()},
        }
