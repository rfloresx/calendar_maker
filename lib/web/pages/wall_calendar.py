"""Wall Calendar page — manage 13 artwork pages (cover + 12 months)."""

import json
import calendar
import logging
from nicegui import ui

from lib.web.database import get_db, WallPage, Project
from lib.web.components.layout import project_layout
from lib.web.components.image_upload import ImageUpload
from lib.web.config import get_project_dir

logger = logging.getLogger(__name__)


PAGE_LABELS = ["Cover"] + [calendar.month_name[i] for i in range(1, 13)]


def _save_page(project_id: str, page_index: int, field: str, value):
    """Save a single field of a wall page to the database."""
    logger.info(f"[SAVE] project={project_id[:8]}... page_index={page_index} field={field} value={repr(value)[:100]}")
    db = get_db()
    try:
        page = db.query(WallPage).filter_by(project_id=project_id, page_index=page_index).first()
        if page:
            setattr(page, field, value)
            db.commit()
            logger.info(f"[SAVE] OK - saved {field} for page {page_index}")
        else:
            logger.warning(f"[SAVE] FAIL - no page found for project={project_id[:8]} page_index={page_index}")
    finally:
        db.close()


class PageEditor:
    """Encapsulates the state and handlers for a single wall calendar page editor."""

    def __init__(self, project_id: str, page_index: int):
        self.project_id = project_id
        self.page_index = page_index
        self._exif_date = None

        db = get_db()
        try:
            page = db.query(WallPage).filter_by(project_id=project_id, page_index=page_index).first()
            self.image_path = page.image_path if page else None
            self.description = page.description or ""
            place_data = page.place_dict if page else {}
        finally:
            db.close()

        self.place_name = place_data.get("name", "")
        self.place_city = place_data.get("city", "")
        self.place_state = place_data.get("state", "")
        self.place_country = place_data.get("country", "")

        logger.info(f"[RENDER] PageEditor created: page_index={page_index} image={self.image_path} place=({self.place_name}, {self.place_city}, {self.place_state})")

    def _render_preview(self):
        """Render the template with current place data and update preview label."""
        from lib.image_utils import TextTemplate
        db = get_db()
        try:
            project = db.query(Project).filter_by(id=self.project_id).first()
            year = project.year if project else 2026
        finally:
            db.close()
        ctx = {
            "place.name": self.place_name,
            "place.city": self.place_city,
            "place.state": self.place_state,
            "place.country": self.place_country,
            "year": year,
            "date": self._exif_date,
        }
        rendered = TextTemplate(self.description).render(ctx)
        if hasattr(self, '_preview_label'):
            self._preview_label.text = rendered or "(empty)"

    def on_image_change(self, path: str):
        logger.info(f"[EVENT] Image changed: page={self.page_index} path={path}")
        _save_page(self.project_id, self.page_index, "image_path", path)
        self._auto_detect_place(path)

    def on_desc_change(self, e):
        logger.info(f"[EVENT] Description changed: page={self.page_index} value={repr(e.value)[:50]}")
        self.description = e.value
        _save_page(self.project_id, self.page_index, "description", e.value)
        self._render_preview()

    def on_name_change(self, e):
        self.place_name = e.value or ""
        self._save_place()
        self._render_preview()

    def on_city_change(self, e):
        self.place_city = e.value or ""
        self._save_place()
        self._render_preview()

    def on_state_change(self, e):
        self.place_state = e.value or ""
        self._save_place()
        self._render_preview()

    def on_country_change(self, e):
        self.place_country = e.value or ""
        self._save_place()
        self._render_preview()

    def _save_place(self):
        place = {
            "name": self.place_name,
            "city": self.place_city,
            "state": self.place_state,
            "country": self.place_country,
        }
        _save_page(self.project_id, self.page_index, "place_data", json.dumps(place))

    def _auto_detect_place(self, relative_path: str):
        """Extract EXIF GPS from uploaded image and look up nearby places."""
        try:
            from lib.image_utils import get_image_metadata, ImageInfo
            project_dir = get_project_dir(self.project_id)
            abs_path = str(project_dir / relative_path)
            metadata = get_image_metadata(abs_path)
            logger.info(f"[PLACE_DETECT] EXIF metadata for page {self.page_index}: {metadata}")

            # Store EXIF date for preview
            dto = metadata.get("DateTimeOriginal")
            if dto:
                import datetime as dt_mod
                try:
                    self._exif_date = dt_mod.datetime.strptime(dto, '%Y:%m:%d %H:%M:%S')
                except Exception:
                    pass

            # Update EXIF label
            if hasattr(self, '_exif_label'):
                if self._exif_date:
                    self._exif_label.text = f"📅 {self._exif_date.strftime('%Y-%m-%d %H:%M')}"
                elif dto:
                    self._exif_label.text = f"📅 {dto}"
                else:
                    self._exif_label.text = ""

            info = ImageInfo(filename=abs_path, metadata=metadata)
            places = info.places
            if places:
                if hasattr(self, '_places_select'):
                    options = [f"{p.name} — {p.city}, {p.state}" for p in places]
                    self._places_select.options = options
                    self._places_select.set_visibility(True)
                    self._detected_places = places
                    # Only pre-select if the current name matches a detected place
                    matched = False
                    for i, p in enumerate(places):
                        if p.name == self.place_name:
                            self._places_select.value = options[i]
                            matched = True
                            break
                    if not matched:
                        # User has custom/manual place — don't select anything
                        self._places_select.value = None

                if not self.place_name:
                    place = places[0]
                    self.place_name = place.name or ""
                    self.place_city = place.city or ""
                    self.place_state = place.state or ""
                    self.place_country = place.country or ""
                    self._save_place()
                    if hasattr(self, '_name_input'):
                        self._name_input.value = self.place_name
                        self._city_input.value = self.place_city
                        self._state_input.value = self.place_state
                        self._country_input.value = self.place_country
                    # Now select the first option since we just filled it
                    if hasattr(self, '_places_select') and self._places_select.options:
                        self._places_select.value = self._places_select.options[0]

                logger.info(f"[PLACE_DETECT] Loaded {len(places)} places for page {self.page_index}")
            else:
                logger.info(f"[PLACE_DETECT] No places found for page {self.page_index}")

            self._render_preview()
        except Exception as e:
            logger.error(f"[PLACE_DETECT] Error: {type(e).__name__}: {e}")

    def _on_place_selected(self, e):
        """Handle selection from the places dropdown."""
        if hasattr(self, '_detected_places') and self._detected_places:
            idx = self._places_select.options.index(e.value) if e.value in self._places_select.options else 0
            if idx < len(self._detected_places):
                place = self._detected_places[idx]
                self.place_name = place.name or ""
                self.place_city = place.city or ""
                self.place_state = place.state or ""
                self.place_country = place.country or ""
                self._save_place()
                self._name_input.value = self.place_name
                self._city_input.value = self.place_city
                self._state_input.value = self.place_state
                self._country_input.value = self.place_country
                self._render_preview()

    def render(self, container):
        """Render the editor UI into the given container."""
        self._detected_places = []
        container.clear()
        with container:
            ui.label(PAGE_LABELS[self.page_index]).classes("text-xl font-bold mb-4")

            with ui.row().classes("w-full gap-8 flex-wrap"):
                with ui.column().classes("items-center"):
                    ui.label("Artwork Image").classes("text-sm font-medium mb-2")
                    ImageUpload(
                        project_id=self.project_id,
                        current_image=self.image_path,
                        on_change=self.on_image_change,
                        label="Upload artwork",
                    )
                    self._exif_label = ui.label("").classes("text-xs text-gray-400 mt-1")

                with ui.column().classes("flex-1 min-w-[300px]"):
                    ui.label("Description Template").classes("text-sm font-medium mb-1")
                    ui.label("Variables: {year}, {date:%b %d}, {place.name}, {place.city}, {place.state}").classes("text-xs text-gray-400 mb-2")

                    ui.textarea(
                        value=self.description,
                        placeholder="Enter description template...",
                        on_change=self.on_desc_change,
                    ).classes("w-full").props("rows=3")

                    ui.label("Preview:").classes("text-xs text-gray-400 mt-1")
                    self._preview_label = ui.label("").classes("text-sm text-blue-700 italic bg-gray-50 p-2 rounded w-full")

                    ui.separator().classes("my-4")
                    ui.label("Place Information").classes("text-sm font-medium mb-2")

                    self._places_select = ui.select(
                        options=[],
                        label="Detected Places (from photo GPS)",
                        on_change=self._on_place_selected,
                    ).classes("w-full mb-2")
                    self._places_select.set_visibility(False)

                    with ui.row().classes("w-full gap-4"):
                        self._name_input = ui.input("Name", value=self.place_name, on_change=self.on_name_change).classes("flex-1")
                        self._city_input = ui.input("City", value=self.place_city, on_change=self.on_city_change).classes("flex-1")

                    with ui.row().classes("w-full gap-4"):
                        self._state_input = ui.input("State", value=self.place_state, on_change=self.on_state_change).classes("flex-1")
                        self._country_input = ui.input("Country", value=self.place_country, on_change=self.on_country_change).classes("flex-1")

            if self.image_path:
                self._auto_detect_place(self.image_path)

            self._render_preview()


@ui.page("/project/{project_id}/wall")
def wall_calendar_page(project_id: str):
    """Wall calendar editor page."""
    project_layout(project_id, active="wall")

    with ui.column().classes("w-full p-6"):
        ui.label("Wall Calendar Pages").classes("text-2xl font-bold mb-4")

        with ui.tabs().classes("w-full") as tabs:
            tab_list = []
            for i, label in enumerate(PAGE_LABELS):
                tab_list.append(ui.tab(label))

        with ui.tab_panels(tabs, value=tab_list[0]).classes("w-full"):
            for i, tab in enumerate(tab_list):
                with ui.tab_panel(tab):
                    panel_container = ui.column().classes("w-full")
                    editor = PageEditor(project_id, i)
                    editor.render(panel_container)
