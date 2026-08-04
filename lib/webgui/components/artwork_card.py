"""Artwork card component for wall/desk calendar pages.

Displays a single month's artwork with image upload, description editing,
template preview, and place metadata editing.
"""

import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from nicegui import events, ui

from lib.filemanager import FilesManager


def _month_name(index: int) -> str:
    """Return human-readable name for artwork page index (0=Cover, 1-12=months)."""
    if index == 0:
        return "Cover Page"
    return datetime.date(2000, index, 1).strftime("%B")


def _get_image_metadata(filepath: str) -> Dict[str, Any]:
    """Extract EXIF metadata from an image file. Returns empty dict on failure."""
    try:
        from lib.template import get_image_metadata
        return get_image_metadata(filepath)
    except Exception:
        return {}


def _get_places(metadata: Dict[str, Any]):
    """Return list of PlaceInfo objects from metadata GPS coordinates."""
    try:
        from lib.template import ImageInfo
        info = ImageInfo(metadata=metadata)
        return info.places
    except Exception:
        return []


def _render_template(template: str, metadata: Dict[str, Any], place_index: int,
                     overrides: Optional[Dict[str, Any]], year: int) -> str:
    """Render a description template with place/date context."""
    try:
        from lib.template import TextTemplate, ImageInfo, build_text_context
        image_info = ImageInfo(metadata=metadata)
        ctx = build_text_context(
            image_info=image_info,
            selected_place_index=place_index,
            overrides=overrides,
            year=year,
        )
        return TextTemplate(template or "").render(ctx)
    except Exception:
        return template or ""


class ArtworkCard:
    """A UI card component for editing a single artwork page.

    Parameters:
        index: Page index (0 = cover, 1-12 = months).
        page_data: Dict with keys image, description, selected_place_index, place_overrides.
        section: 'artworks' or 'desk_pages' — used to route saves.
        year: Calendar year for template rendering.
        on_change: Callback invoked when the page data changes.
    """

    def __init__(
        self,
        index: int,
        page_data: Dict[str, Any],
        section: str,
        year: int,
        on_change: Optional[Callable[[], None]] = None,
    ):
        self._index = index
        self._section = section
        self._year = year
        self._on_change = on_change

        # Local working copy of the page data
        self._image: Optional[str] = page_data.get("image")
        self._description: str = page_data.get("description", "")
        self._selected_place_index: int = page_data.get("selected_place_index", 0)
        self._place_overrides: Dict[int, Dict[str, str]] = {
            int(k): v for k, v in (page_data.get("place_overrides") or {}).items()
        }

        # Metadata extracted from image
        self._metadata: Dict[str, Any] = {}
        self._places: list = []
        if self._image:
            self._resolve_image_metadata()

        self._build_ui()

    def _resolve_image_metadata(self):
        """Load metadata and places from the current image path."""
        if not self._image:
            self._metadata = {}
            self._places = []
            return
        # Resolve relative path using FilesManager
        fm = FilesManager.instance()
        abs_path = str(fm.get_file_path(self._image))
        if Path(abs_path).exists():
            self._metadata = _get_image_metadata(abs_path)
            self._places = _get_places(self._metadata)
        else:
            self._metadata = {}
            self._places = []

    def _build_ui(self):
        """Construct the NiceGUI elements for this card."""
        with ui.card().classes("w-full"):
            # Header
            ui.label(_month_name(self._index)).classes("text-lg font-semibold")

            with ui.row().classes("w-full items-start gap-4"):
                # Left column: image
                with ui.column().classes("items-center"):
                    self._image_display = ui.image(
                        self._get_image_src()
                    ).classes("w-48 h-36 object-cover rounded border")

                    self._upload = ui.upload(
                        label="Choose image",
                        auto_upload=True,
                        on_upload=self._handle_upload,
                    ).props("accept='.png,.jpg,.jpeg,.bmp'").classes("w-48")

                # Right column: description + place
                with ui.column().classes("flex-grow gap-2"):
                    # Description template
                    self._desc_input = ui.textarea(
                        label="Description (template)",
                        value=self._description,
                        on_change=self._on_description_change,
                    ).classes("w-full")

                    # Rendered preview
                    self._preview_label = ui.label(
                        self._rendered_description()
                    ).classes("text-sm italic text-gray-600")

                    # Metadata info
                    self._meta_label = ui.label(
                        self._metadata_summary()
                    ).classes("text-xs text-gray-500")

                    # Place selector
                    if self._places:
                        place_options = {
                            i: f"{p.name}, {p.city}, {p.state}"
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
    # Event handlers
    # ------------------------------------------------------------------

    def _handle_upload(self, e: events.UploadEventArguments):
        """Handle image file upload."""
        fm = FilesManager.instance()
        # Save uploaded file to a temp location, then add to project
        content = e.content.read()
        filename = e.name

        # Write to project images dir
        target = fm.get_target_path(filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            f.write(content)

        # Store relative path
        self._image = fm.get_relative_path(str(target))
        self._resolve_image_metadata()

        # Update UI
        self._image_display.set_source(self._get_image_src())
        self._meta_label.set_text(self._metadata_summary())
        self._preview_label.set_text(self._rendered_description())
        self._notify_change()

    def _on_description_change(self, e):
        """Handle description text change."""
        self._description = e.value or ""
        self._preview_label.set_text(self._rendered_description())
        self._notify_change()

    def _on_place_select(self, e):
        """Handle place dropdown selection."""
        self._selected_place_index = e.value
        overrides = self._place_overrides.get(self._selected_place_index, {})
        self._name_input.set_value(overrides.get("name", self._place_field("name")))
        self._city_input.set_value(overrides.get("city", self._place_field("city")))
        self._state_input.set_value(overrides.get("state", self._place_field("state")))
        self._preview_label.set_text(self._rendered_description())
        self._notify_change()

    def _on_place_field_change(self, e):
        """Handle editable place field changes."""
        self._place_overrides[self._selected_place_index] = {
            "name": self._name_input.value or "",
            "city": self._city_input.value or "",
            "state": self._state_input.value or "",
        }
        self._preview_label.set_text(self._rendered_description())
        self._notify_change()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_image_src(self) -> str:
        """Return a URL-safe source for the image display."""
        if not self._image:
            return "https://via.placeholder.com/192x144?text=No+Image"
        fm = FilesManager.instance()
        abs_path = str(fm.get_file_path(self._image))
        if Path(abs_path).exists():
            # Serve via NiceGUI's local file mechanism
            from nicegui import app as nicegui_app
            return nicegui_app.add_static_file(local_file=abs_path)
        return "https://via.placeholder.com/192x144?text=Not+Found"

    def _rendered_description(self) -> str:
        """Return the rendered template text."""
        overrides = self._place_overrides.get(self._selected_place_index)
        return _render_template(
            self._description, self._metadata, self._selected_place_index,
            overrides, self._year,
        )

    def _metadata_summary(self) -> str:
        """Return a short text summary of image metadata."""
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
        """Get a place field value from metadata places (not overrides)."""
        if self._places and self._selected_place_index < len(self._places):
            return getattr(self._places[self._selected_place_index], field, "") or ""
        return ""

    def _notify_change(self):
        """Notify parent that data changed."""
        if self._on_change:
            self._on_change()

    def to_dict(self) -> Dict[str, Any]:
        """Export this card's state as a dict matching Project.json format."""
        return {
            "image": self._image,
            "description": self._description,
            "selected_place_index": self._selected_place_index,
            "place_overrides": {str(k): v for k, v in self._place_overrides.items()},
        }
