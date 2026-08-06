"""Export page — select exporter, configure options, run export."""

import json
import time
import datetime
import zipfile
import io
from pathlib import Path
from typing import Dict, Any

from nicegui import ui

from lib.web.database import (
    get_db, Project, WallPage, DeskPage, Birthday, PhotoLabel,
    ExportSettings, get_or_create_export_settings,
)
from lib.web.config import get_project_dir, get_project_exports_dir
from lib.web.components.layout import project_layout

# Import export system
from lib.export import ExporterRegistry, ExportFormat, DataType, ExportContext
import lib.pycal as libpycal
import lib.calendar.ics_loader as libics


def _resolve_template(description: str, place_data_json: str, image_path: str, year: int) -> str:
    """Resolve a description template with place data and EXIF date."""
    from lib.image_utils import TextTemplate, get_image_metadata
    import datetime as dt_mod

    if not description:
        return ""

    place_data = {}
    if place_data_json:
        try:
            place_data = json.loads(place_data_json)
        except (json.JSONDecodeError, TypeError):
            pass

    # Try to get EXIF date from image
    exif_date = None
    if image_path:
        try:
            metadata = get_image_metadata(image_path)
            dto = metadata.get("DateTimeOriginal")
            if dto:
                exif_date = dt_mod.datetime.strptime(dto, '%Y:%m:%d %H:%M:%S')
        except Exception:
            pass

    ctx = {
        "place.name": place_data.get("name", ""),
        "place.city": place_data.get("city", ""),
        "place.state": place_data.get("state", ""),
        "place.country": place_data.get("country", ""),
        "year": year,
        "date": exif_date,
    }
    return TextTemplate(description).render(ctx)


def _build_wall_calendar(project_id: str) -> libpycal.Calendar:
    """Build a Calendar object from wall page database entries."""
    db = get_db()
    try:
        project = db.query(Project).filter_by(id=project_id).first()
        year = project.year if project else datetime.datetime.now().year
        pages = db.query(WallPage).filter_by(project_id=project_id).order_by(WallPage.page_index).all()
        birthdays_entries = db.query(Birthday).filter_by(project_id=project_id).all()
    finally:
        db.close()

    # Build VCalendar from birthdays
    vcal = libics.VCalendar()
    for bday in birthdays_entries:
        if bday.date:
            try:
                dt = datetime.datetime.strptime(bday.date, "%d/%m/%Y")
                data = {
                    libics.VCalendar.DATE_KEY: [dt],
                    libics.VCalendar.SUMMARY_KEY: [bday.title or ""],
                    libics.VCalendar.IMAGES_KEY: [bday.image_path or ""],
                }
                vcal.add(libics.VCalendar.VEvent(data))
            except ValueError:
                pass

    events = libpycal.EventsManager(year, vcal)
    cal = libpycal.Calendar(year, events)

    # Populate pages
    project_dir = get_project_dir(project_id)
    for page in pages:
        image = str(project_dir / page.image_path) if page.image_path else None
        title = _resolve_template(page.description, page.place_data, image, year)
        if page.page_index == 0:
            cal.front_page.image = image
            cal.front_page.title = title
        elif page.page_index <= 12:
            art = cal.arts[page.page_index - 1]
            art.image = image
            art.title = title

    return cal


def _build_desk_calendar(project_id: str) -> libpycal.Calendar:
    """Build a Calendar object from desk page database entries."""
    db = get_db()
    try:
        project = db.query(Project).filter_by(id=project_id).first()
        year = project.year if project else datetime.datetime.now().year
        pages = db.query(DeskPage).filter_by(project_id=project_id).order_by(DeskPage.page_index).all()
        birthdays_entries = db.query(Birthday).filter_by(project_id=project_id).all()
    finally:
        db.close()

    vcal = libics.VCalendar()
    for bday in birthdays_entries:
        if bday.date:
            try:
                dt = datetime.datetime.strptime(bday.date, "%d/%m/%Y")
                data = {
                    libics.VCalendar.DATE_KEY: [dt],
                    libics.VCalendar.SUMMARY_KEY: [bday.title or ""],
                    libics.VCalendar.IMAGES_KEY: [bday.image_path or ""],
                }
                vcal.add(libics.VCalendar.VEvent(data))
            except ValueError:
                pass

    events = libpycal.EventsManager(year, vcal)
    cal = libpycal.Calendar(year, events)

    project_dir = get_project_dir(project_id)
    for page in pages:
        image = str(project_dir / page.image_path) if page.image_path else None
        title = _resolve_template(page.description, page.place_data, image, year)
        if page.page_index == 0:
            cal.front_page.image = image
            cal.front_page.title = title
        elif page.page_index <= 12:
            art = cal.arts[page.page_index - 1]
            art.image = image
            art.title = title

    return cal


def _get_photo_labels_data(project_id: str) -> list:
    """Get photo labels as a list of dicts suitable for export."""
    db = get_db()
    try:
        photos = db.query(PhotoLabel).filter_by(project_id=project_id).order_by(PhotoLabel.sort_order).all()
    finally:
        db.close()

    project_dir = get_project_dir(project_id)
    result = []
    for photo in photos:
        entry = {
            "image": str(project_dir / photo.image_path) if photo.image_path else None,
            "template": photo.template or "",
        }
        if photo.place_data:
            try:
                entry["place_data"] = json.loads(photo.place_data)
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(entry)
    return result


def _get_birthdays_data(project_id: str) -> list:
    """Get birthdays as a list of dicts suitable for export."""
    db = get_db()
    try:
        birthdays = db.query(Birthday).filter_by(project_id=project_id).order_by(Birthday.sort_order).all()
    finally:
        db.close()

    project_dir = get_project_dir(project_id)
    result = []
    for bday in birthdays:
        result.append({
            "image": str(project_dir / bday.image_path) if bday.image_path else None,
            "title": bday.title or "",
            "date": bday.date or "",
        })
    return result


@ui.page("/project/{project_id}/export")
def export_page(project_id: str):
    """Export page with exporter selection and option configuration."""
    project_layout(project_id, active="export")

    # Load project info and settings
    db = get_db()
    try:
        project = db.query(Project).filter_by(id=project_id).first()
        settings = get_or_create_export_settings(db, project_id)
        current_type = settings.calendar_type or "wall"
        current_format = settings.format or "png"
        current_exporter = settings.exporter_name or "default"
        saved_options = settings.options_dict
    finally:
        db.close()

    with ui.column().classes("w-full p-6 max-w-3xl"):
        ui.label("Export").classes("text-2xl font-bold mb-4")

        # Calendar type selector
        data_types = ["wall", "desk", "photos", "birthdays"]
        type_select = ui.select(
            data_types,
            value=current_type,
            label="Calendar Type",
        ).classes("w-full mb-4")

        # Format selector
        format_select = ui.select(
            ["png", "html", "json"],
            value=current_format,
            label="Export Format",
        ).classes("w-full mb-4")

        # Exporter variant selector
        exporter_select = ui.select(
            [],
            value=None,
            label="Exporter Variant",
        ).classes("w-full mb-4")

        # Options container
        ui.label("Options").classes("text-lg font-medium mt-4 mb-2")
        options_container = ui.column().classes("w-full")

        # State for dynamic options
        option_controls: Dict[str, Any] = {}

        def update_exporters():
            """Update exporter choices based on type + format."""
            try:
                dt = DataType(type_select.value)
                fmt = ExportFormat(format_select.value)
                exporters = ExporterRegistry.get_exporters_for(fmt, dt)
                names = [e["name"] for e in exporters]
                exporter_select.options = names
                if names:
                    if current_exporter in names:
                        exporter_select.value = current_exporter
                    else:
                        exporter_select.value = names[0]
                else:
                    exporter_select.options = ["(none available)"]
                    exporter_select.value = "(none available)"
            except (ValueError, KeyError):
                exporter_select.options = ["(none available)"]
                exporter_select.value = "(none available)"
            exporter_select.update()
            update_options()

        def update_options():
            """Update options UI based on selected exporter."""
            options_container.clear()
            option_controls.clear()

            try:
                dt = DataType(type_select.value)
                fmt = ExportFormat(format_select.value)
                name = exporter_select.value
                if not ExporterRegistry.has_exporter(fmt, dt, name):
                    return
                exporter = ExporterRegistry.get_exporter(fmt, dt, name)
                schema = getattr(exporter.__class__, "OPTIONS_SCHEMA", {})
            except (ValueError, KeyError):
                return

            if not schema:
                with options_container:
                    ui.label("No configurable options.").classes("text-sm text-gray-500")
                return

            with options_container:
                for opt_name, spec in schema.items():
                    opt_type = spec.get("type", "string")
                    default = spec.get("default")
                    description = spec.get("description", "")
                    # Use saved value if available
                    saved_val = saved_options.get(opt_name, default)

                    if opt_type in ("integer", "int"):
                        min_val = spec.get("min", 0)
                        max_val = spec.get("max", 9999)
                        ctrl = ui.number(
                            opt_name,
                            value=int(saved_val) if saved_val is not None else min_val,
                            min=min_val,
                            max=max_val,
                        ).classes("w-full mb-2").tooltip(description)
                        option_controls[opt_name] = ctrl
                    elif opt_type in ("boolean", "bool"):
                        ctrl = ui.checkbox(
                            opt_name,
                            value=bool(saved_val) if saved_val is not None else False,
                        ).classes("mb-2").tooltip(description)
                        option_controls[opt_name] = ctrl
                    elif opt_type in ("enum", "choices"):
                        choices = spec.get("choices", [])
                        ctrl = ui.select(
                            [str(c) for c in choices],
                            value=str(saved_val) if saved_val is not None else (str(choices[0]) if choices else ""),
                            label=opt_name,
                        ).classes("w-full mb-2").tooltip(description)
                        option_controls[opt_name] = ctrl
                    else:
                        ctrl = ui.input(
                            opt_name,
                            value=str(saved_val) if saved_val is not None else "",
                        ).classes("w-full mb-2").tooltip(description)
                        option_controls[opt_name] = ctrl

        type_select.on("update:model-value", lambda e: update_exporters())
        format_select.on("update:model-value", lambda e: update_exporters())
        exporter_select.on("update:model-value", lambda e: update_options())

        # Initialize
        update_exporters()

        ui.separator().classes("my-4")

        # Progress and results area
        progress_bar = ui.linear_progress(value=0, show_value=False).classes("w-full")
        progress_bar.set_visibility(False)
        progress_label = ui.label("").classes("text-sm text-gray-500")
        results_container = ui.column().classes("w-full mt-4")

        async def do_export():
            """Run the export."""
            # Show spinner immediately
            results_container.clear()
            with results_container:
                spinner_row = ui.row().classes("items-center gap-2")
                with spinner_row:
                    ui.spinner("dots", size="lg", color="primary")
                    ui.label("Exporting... please wait").classes("text-sm text-gray-600")

            try:
                dt = DataType(type_select.value)
                fmt = ExportFormat(format_select.value)
                name = exporter_select.value

                if not ExporterRegistry.has_exporter(fmt, dt, name):
                    ui.notify("No exporter available for this combination", type="warning")
                    return

                exporter = ExporterRegistry.get_exporter(fmt, dt, name)

                # Gather options from controls
                options = {}
                schema = getattr(exporter.__class__, "OPTIONS_SCHEMA", {})
                for opt_name, ctrl in option_controls.items():
                    spec = schema.get(opt_name, {})
                    opt_type = spec.get("type", "string")
                    if opt_type in ("integer", "int"):
                        options[opt_name] = int(ctrl.value)
                    elif opt_type in ("boolean", "bool"):
                        options[opt_name] = bool(ctrl.value)
                    else:
                        options[opt_name] = ctrl.value

                # Save settings
                db = get_db()
                try:
                    s = get_or_create_export_settings(db, project_id)
                    s.calendar_type = type_select.value
                    s.format = format_select.value
                    s.exporter_name = name
                    s.options = json.dumps(options)
                    db.commit()
                finally:
                    db.close()

                # Build source data
                if dt == DataType.WALL:
                    source = _build_wall_calendar(project_id)
                elif dt == DataType.DESK:
                    source = _build_desk_calendar(project_id)
                elif dt == DataType.PHOTOS:
                    source = _get_photo_labels_data(project_id)
                else:
                    source = _get_birthdays_data(project_id)

                # Output directory
                output_dir = get_project_exports_dir(project_id) / f"{dt.value}_{fmt.value}"
                output_dir.mkdir(parents=True, exist_ok=True)

                # Initialize FilesManager for the exporters that need it
                from lib.filemanager import FilesManager
                FilesManager(str(get_project_dir(project_id)))

                # Progress callback
                progress_bar.set_visibility(True)
                progress_bar.value = 0

                def progress_cb(current, total, message):
                    if total > 0:
                        progress_bar.value = current / total
                    progress_label.text = message

                # Export
                context = ExportContext(
                    source=source,
                    data_type=dt,
                    format=fmt,
                    output_dir=output_dir,
                    project_root=get_project_dir(project_id),
                    options=options,
                    progress_callback=progress_cb,
                )

                start = time.time()
                result = exporter.export(context)
                duration = time.time() - start

                progress_bar.value = 1.0
                progress_bar.set_visibility(False)

                # Show results
                results_container.clear()
                with results_container:
                    if result.success:
                        ui.label(f"✅ Export complete! {result.file_count} file(s) in {duration:.1f}s").classes("text-green-600 font-medium")
                        if result.files:
                            # Create zip file for bulk download
                            project_dir = get_project_dir(project_id)
                            zip_name = f"{dt.value}_{fmt.value}_export.zip"
                            zip_path = output_dir / zip_name
                            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                                for f in result.files:
                                    zf.write(f, Path(f).name)

                            try:
                                rel_zip = zip_path.relative_to(project_dir)
                                zip_url = f"/project-files/{project_id}/{rel_zip}"
                                ui.link(
                                    f"📦 Download All ({result.file_count} files as ZIP)",
                                    zip_url,
                                    new_tab=True,
                                ).classes("text-sm text-blue-700 font-medium underline")
                            except ValueError:
                                pass

                            # Also show individual files
                            with ui.expansion("Individual files", icon="list").classes("w-full mt-2"):
                                for f in result.files[:50]:
                                    fname = Path(f).name
                                    try:
                                        rel_path = Path(f).relative_to(project_dir)
                                        download_url = f"/project-files/{project_id}/{rel_path}"
                                        ui.link(fname, download_url, new_tab=True).classes("text-xs text-blue-600 underline")
                                    except ValueError:
                                        ui.label(f"  • {fname}").classes("text-xs text-gray-600")
                                if len(result.files) > 50:
                                    ui.label(f"  ... and {len(result.files) - 50} more").classes("text-xs text-gray-400")
                    else:
                        ui.label("❌ Export failed").classes("text-red-600 font-medium")
                        for err in result.errors:
                            ui.label(f"  • {err}").classes("text-sm text-red-500")

                ui.notify(
                    f"Export {'complete' if result.success else 'failed'}: {result.file_count} file(s)",
                    type="positive" if result.success else "negative",
                )

            except Exception as e:
                progress_bar.set_visibility(False)
                ui.notify(f"Export error: {str(e)}", type="negative")
                results_container.clear()
                with results_container:
                    ui.label(f"❌ Error: {str(e)}").classes("text-red-600")

        ui.button("Export", icon="file_download", on_click=do_export).props("color=primary size=lg").classes("mt-4")
