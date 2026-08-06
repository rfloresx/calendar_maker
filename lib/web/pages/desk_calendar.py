"""Desk Calendar page — manage 13 artwork pages (cover + 12 months)."""

import json
import calendar
import logging
from nicegui import ui

from lib.web.database import get_db, DeskPage, Project
from lib.web.components.layout import project_layout
from lib.web.components.image_upload import ImageUpload
from lib.web.config import get_project_dir

logger = logging.getLogger(__name__)


PAGE_LABELS = ["Cover"] + [calendar.month_name[i] for i in range(1, 13)]


def _save_page(project_id: str, page_index: int, field: str, value):
    """Save a single field of a desk page to the database."""
    db = get_db()
    try:
        page = db.query(DeskPage).filter_by(project_id=project_id, page_index=page_index).first()
        if page:
            setattr(page, field, value)
            db.commit()
    finally:
        db.close()


class DeskPageEditor:
    """Encapsulates the state and handlers for a single desk calendar page editor."""

    def __init__(self, project_id: str, page_index: int):
        self.project_id = project_id
        self.page_index = page_index
        self._exif_date = None

        db = get_db()
        try:
            page = db.query(DeskPage).filter_by(project_id=project_id, page_index=page_index).first()
            self.image_path = page.image_path if page else None
            self.description = page.description or ""
            place_data = page.place_dict if page else {}
        finally:
            db.close()

        self.place_name = place_data.get("name", "")
        self.place_city = place_data.get("city", "")
        self.place_state = place_data.get("state", "")
        self.place_country = place_data.get("country", "")

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
        _save_page(self.project_id, self.page_index, "image_path", path)
        self._auto_detect_place(path)

    def on_desc_change(self, e):
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
        place = {"name": self.place_name, "city": self.place_city, "state": self.place_state, "country": self.place_country}
        _save_page(self.project_id, self.page_index, "place_data", json.dumps(place))

    def _auto_detect_place(self, relative_path: str):
        """Extract EXIF GPS from uploaded image and look up nearby places."""
        try:
            from lib.image_utils import get_image_metadata, ImageInfo
            project_dir = get_project_dir(self.project_id)
            abs_path = str(project_dir / relative_path)
            metadata = get_image_metadata(abs_path)

            dto = metadata.get("DateTimeOriginal")
            if dto:
                import datetime as dt_mod
                try:
                    self._exif_date = dt_mod.datetime.strptime(dto, '%Y:%m:%d %H:%M:%S')
                except Exception:
                    pass

            if hasattr(self, '_exif_label'):
                if self._exif_date:
                    self._exif_label.text = f"📅 {self._exif_date.strftime('%Y-%m-%d %H:%M')}"
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
                    matched = False
                    for i, p in enumerate(places):
                        if p.name == self.place_name:
                            self._places_select.value = options[i]
                            matched = True
                            break
                    if not matched:
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
                    if hasattr(self, '_places_select') and self._places_select.options:
                        self._places_select.value = self._places_select.options[0]

            self._render_preview()
        except Exception as e:
            logger.error(f"[DESK_PLACE_DETECT] Error: {type(e).__name__}: {e}")

    def _on_place_selected(self, e):
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
        self._detected_places = []
        container.clear()
        with container:
            ui.label(PAGE_LABELS[self.page_index]).classes("text-xl font-bold mb-4")

            with ui.row().classes("w-full gap-8 flex-wrap"):
                with ui.column().classes("items-center"):
                    ui.label("Artwork Image").classes("text-sm font-medium mb-2")
                    ImageUpload(project_id=self.project_id, current_image=self.image_path, on_change=self.on_image_change, label="Upload artwork")
                    self._exif_label = ui.label("").classes("text-xs text-gray-400 mt-1")

                with ui.column().classes("flex-1 min-w-[300px]"):
                    ui.label("Description Template").classes("text-sm font-medium mb-1")
                    ui.label("Variables: {year}, {date:%b %d}, {place.name}, {place.city}, {place.state}").classes("text-xs text-gray-400 mb-2")
                    ui.textarea(value=self.description, placeholder="Enter description template...", on_change=self.on_desc_change).classes("w-full").props("rows=3")

                    ui.label("Preview:").classes("text-xs text-gray-400 mt-1")
                    self._preview_label = ui.label("").classes("text-sm text-blue-700 italic bg-gray-50 p-2 rounded w-full")

                    ui.separator().classes("my-4")
                    ui.label("Place Information").classes("text-sm font-medium mb-2")
                    self._places_select = ui.select(options=[], label="Detected Places (from photo GPS)", on_change=self._on_place_selected).classes("w-full mb-2")
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


@ui.page("/project/{project_id}/desk")
def desk_calendar_page(project_id: str):
    project_layout(project_id, active="desk")
    with ui.column().classes("w-full p-6"):
        ui.label("Desk Calendar Pages").classes("text-2xl font-bold mb-4")
        with ui.tabs().classes("w-full") as tabs:
            tab_list = [ui.tab(label) for label in PAGE_LABELS]
        with ui.tab_panels(tabs, value=tab_list[0]).classes("w-full"):
            for i, tab in enumerate(tab_list):
                with ui.tab_panel(tab):
                    panel_container = ui.column().classes("w-full")
                    editor = DeskPageEditor(project_id, i)
                    editor.render(panel_container)
