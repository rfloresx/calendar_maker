"""Photo Labels page — manage labeled photos with place detection and live preview."""

import json
import datetime
from nicegui import ui, events

from lib.web.database import get_db, PhotoLabel
from lib.web.components.layout import project_layout
from lib.web.storage import save_uploaded_image
from lib.web.config import get_project_dir


DEFAULT_TEMPLATE = "{place.name}\n{place.city}, {place.state}. {date:%b %d}"


def _load_photos(project_id: str):
    db = get_db()
    try:
        return db.query(PhotoLabel).filter_by(project_id=project_id).order_by(PhotoLabel.sort_order, PhotoLabel.id).all()
    finally:
        db.close()


def _add_photo(project_id: str, image_path: str = None, template: str = None):
    db = get_db()
    try:
        max_order = db.query(PhotoLabel.sort_order).filter_by(project_id=project_id).order_by(PhotoLabel.sort_order.desc()).first()
        next_order = (max_order[0] + 1) if max_order else 0
        photo = PhotoLabel(project_id=project_id, image_path=image_path, template=template or DEFAULT_TEMPLATE, sort_order=next_order)
        db.add(photo)
        db.commit()
        return photo.id
    finally:
        db.close()


def _update_photo(photo_id: int, field: str, value):
    db = get_db()
    try:
        photo = db.query(PhotoLabel).filter_by(id=photo_id).first()
        if photo:
            setattr(photo, field, value)
            db.commit()
    finally:
        db.close()


def _delete_photo(photo_id: int):
    db = get_db()
    try:
        photo = db.query(PhotoLabel).filter_by(id=photo_id).first()
        if photo:
            db.delete(photo)
            db.commit()
    finally:
        db.close()


def _sort_photos(project_id: str):
    """Sort photos by EXIF date."""
    from lib.image_utils import get_image_metadata
    db = get_db()
    try:
        photos = db.query(PhotoLabel).filter_by(project_id=project_id).all()
        project_dir = get_project_dir(project_id)

        def sort_key(p):
            if p.image_path:
                try:
                    metadata = get_image_metadata(str(project_dir / p.image_path))
                    dto = metadata.get("DateTimeOriginal", "")
                    if dto:
                        return (False, datetime.datetime.strptime(dto, '%Y:%m:%d %H:%M:%S'))
                except Exception:
                    pass
            return (True, datetime.datetime.min)

        photos.sort(key=sort_key)
        for i, photo in enumerate(photos):
            photo.sort_order = i
        db.commit()
    finally:
        db.close()


def _is_duplicate(project_id: str, filename: str) -> bool:
    db = get_db()
    try:
        existing = db.query(PhotoLabel).filter_by(project_id=project_id).all()
        for p in existing:
            if p.image_path and filename in p.image_path:
                return True
        return False
    finally:
        db.close()


class PhotoLabelEditor:
    """Editor for a single photo label entry with live preview and place detection."""

    def __init__(self, project_id: str, photo_id: int, image_path: str, template: str, place_data: dict):
        self.project_id = project_id
        self.photo_id = photo_id
        self.image_path = image_path
        self.template = template or DEFAULT_TEMPLATE
        self.place_name = place_data.get("name", "")
        self.place_city = place_data.get("city", "")
        self.place_state = place_data.get("state", "")
        self._exif_date = None
        self._detected_places = []

    def _render_preview(self):
        from lib.image_utils import TextTemplate
        ctx = {
            "place.name": self.place_name,
            "place.city": self.place_city,
            "place.state": self.place_state,
            "date": self._exif_date,
        }
        rendered = TextTemplate(self.template).render(ctx)
        if hasattr(self, '_preview_label'):
            self._preview_label.text = rendered or "(empty)"

    def _save_place(self):
        data = json.dumps({"name": self.place_name, "city": self.place_city, "state": self.place_state})
        _update_photo(self.photo_id, "place_data", data)

    def on_template_change(self, e):
        self.template = e.value
        _update_photo(self.photo_id, "template", e.value)
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

    def _on_place_selected(self, e):
        if self._detected_places and hasattr(self, '_places_select'):
            idx = self._places_select.options.index(e.value) if e.value in self._places_select.options else 0
            if idx < len(self._detected_places):
                place = self._detected_places[idx]
                self.place_name = place.name or ""
                self.place_city = place.city or ""
                self.place_state = place.state or ""
                self._save_place()
                self._name_input.value = self.place_name
                self._city_input.value = self.place_city
                self._state_input.value = self.place_state
                self._render_preview()

    def _auto_detect_place(self):
        """Detect places from image EXIF GPS."""
        if not self.image_path:
            return
        try:
            from lib.image_utils import get_image_metadata, ImageInfo
            project_dir = get_project_dir(self.project_id)
            abs_path = str(project_dir / self.image_path)
            metadata = get_image_metadata(abs_path)

            dto = metadata.get("DateTimeOriginal")
            if dto:
                try:
                    self._exif_date = datetime.datetime.strptime(dto, '%Y:%m:%d %H:%M:%S')
                except Exception:
                    pass

            info = ImageInfo(filename=abs_path, metadata=metadata)
            places = info.places
            if places:
                self._detected_places = places
                if hasattr(self, '_places_select'):
                    options = [f"{p.name} — {p.city}, {p.state}" for p in places]
                    self._places_select.options = options
                    self._places_select.set_visibility(True)
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
                    self._save_place()
                    if hasattr(self, '_name_input'):
                        self._name_input.value = self.place_name
                        self._city_input.value = self.place_city
                        self._state_input.value = self.place_state
                    if hasattr(self, '_places_select') and self._places_select.options:
                        self._places_select.value = self._places_select.options[0]
        except Exception:
            pass
        self._render_preview()

    def render(self, container, list_container):
        """Render a single photo label card."""
        with container:
            with ui.card().classes("w-full mb-3"):
                with ui.row().classes("w-full items-start gap-4"):
                    # Image
                    if self.image_path:
                        ui.image(f"/project-files/{self.project_id}/{self.image_path}").classes("w-32 h-24 object-cover rounded")
                    else:
                        ui.icon("photo_camera").classes("text-5xl text-gray-300")

                    with ui.column().classes("flex-1"):
                        # Template editor
                        ui.textarea(
                            label="Label Template",
                            value=self.template,
                            on_change=self.on_template_change,
                        ).classes("w-full").props("rows=2 dense")

                        # Live preview
                        ui.label("Preview:").classes("text-xs text-gray-400 mt-1")
                        self._preview_label = ui.label("").classes("text-xs text-blue-600 italic bg-gray-50 p-1 rounded w-full")

                        # Places dropdown
                        self._places_select = ui.select(
                            options=[],
                            label="Detected Places",
                            on_change=self._on_place_selected,
                        ).classes("w-full mt-2").props("dense")
                        self._places_select.set_visibility(False)

                        # Place fields
                        with ui.row().classes("w-full gap-2 mt-2"):
                            self._name_input = ui.input("Name", value=self.place_name, on_change=self.on_name_change).props("dense").classes("flex-1")
                            self._city_input = ui.input("City", value=self.place_city, on_change=self.on_city_change).props("dense").classes("flex-1")
                            self._state_input = ui.input("State", value=self.place_state, on_change=self.on_state_change).props("dense").classes("w-24")

                    # Delete
                    ui.button(
                        icon="delete",
                        on_click=lambda: (_delete_photo(self.photo_id), _render_all_photos(self.project_id, list_container)),
                    ).props("flat color=negative round size=sm")

        # Detect places and render initial preview
        self._auto_detect_place()
        self._render_preview()


def _render_all_photos(project_id: str, container):
    """Render all photo label entries."""
    container.clear()
    photos = _load_photos(project_id)

    with container:
        if not photos:
            ui.label("No photos added yet.").classes("text-gray-500")
            return

        for photo in photos:
            place_data = {}
            if photo.place_data:
                try:
                    place_data = json.loads(photo.place_data)
                except (json.JSONDecodeError, TypeError):
                    pass

            editor = PhotoLabelEditor(
                project_id=project_id,
                photo_id=photo.id,
                image_path=photo.image_path,
                template=photo.template,
                place_data=place_data,
            )
            card_container = ui.column().classes("w-full")
            editor.render(card_container, container)


@ui.page("/project/{project_id}/photos")
def photo_labels_page(project_id: str):
    project_layout(project_id, active="photos")

    with ui.column().classes("w-full p-6"):
        ui.label("Photo Labels").classes("text-2xl font-bold mb-4")
        list_container = ui.column().classes("w-full")

        with ui.row().classes("gap-2 mb-4"):
            ui.button("Add Photo", icon="add", on_click=lambda: (
                _add_photo(project_id),
                _render_all_photos(project_id, list_container),
            )).props("color=primary")

            ui.button("Sort by Date", icon="sort_by_alpha", on_click=lambda: (
                _sort_photos(project_id),
                _render_all_photos(project_id, list_container),
                ui.notify("Sorted by EXIF date", type="positive"),
            )).props("outline")

            def handle_photo_upload(e: events.UploadEventArguments):
                content = e.content.read()
                filename = e.name
                if _is_duplicate(project_id, filename):
                    ui.notify(f"Duplicate skipped: {filename}", type="warning")
                    return
                relative_path = save_uploaded_image(project_id, filename, content)
                _add_photo(project_id, image_path=relative_path)
                _render_all_photos(project_id, list_container)
                ui.notify(f"Added: {filename}", type="positive")

            ui.upload(
                label="Import Photos",
                auto_upload=True,
                on_upload=handle_photo_upload,
                multiple=True,
            ).props('accept="image/*"').classes("w-auto")

        _render_all_photos(project_id, list_container)
