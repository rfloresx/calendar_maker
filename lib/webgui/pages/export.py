"""Export page — web GUI.

Provides export controls with dynamic format/exporter/option selection,
progress feedback, and result notification.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from nicegui import ui

from lib.webgui.state import ProjectState


def export_content(state: ProjectState) -> None:
    """Render the export controls page."""

    # Lazy import to avoid loading heavy modules at startup
    from lib.export import (
        ExporterRegistry,
        ExportFormat,
        DataType,
        ExportContext,
    )
    from lib.filemanager import FilesManager

    # --- State ---
    export_state: Dict[str, Any] = {
        "calendar_type": "wall",
        "format": "png",
        "exporter_name": "default",
        "options": {},
    }

    # Load saved selection from project settings
    saved_export = state.settings.get("export", {})
    export_state["calendar_type"] = saved_export.get("calendar_type", "wall")
    export_state["format"] = saved_export.get("format", "png")
    export_state["exporter_name"] = saved_export.get("exporter_name", "default")

    # --- Helpers ---
    def get_data_type() -> DataType:
        mapping = {"wall": DataType.WALL, "desk": DataType.DESK, "photos": DataType.PHOTOS, "birthdays": DataType.BIRTHDAYS}
        return mapping.get(export_state["calendar_type"], DataType.WALL)

    def get_format() -> ExportFormat:
        try:
            return ExportFormat(export_state["format"])
        except ValueError:
            return ExportFormat.PNG

    def get_available_formats() -> List[str]:
        """Get formats available for the current data type."""
        data_type = get_data_type()
        formats = ExporterRegistry.get_formats_for_data_type(data_type)
        return [f.value for f in formats] if formats else ["png"]

    def get_available_exporters() -> List[str]:
        """Get exporter names for current format + data type."""
        exporters = ExporterRegistry.get_exporters_for(get_format(), get_data_type())
        return [e["name"] for e in exporters] if exporters else []

    def get_options_schema() -> Dict[str, Any]:
        """Get OPTIONS_SCHEMA for the current exporter."""
        try:
            fmt = get_format()
            dt = get_data_type()
            name = export_state["exporter_name"]
            if ExporterRegistry.has_exporter(fmt, dt, name):
                exporter = ExporterRegistry.get_exporter(fmt, dt, name)
                return getattr(exporter.__class__, "OPTIONS_SCHEMA", {})
        except Exception:
            pass
        return {}

    # --- UI ---
    ui.label("Export").classes("text-2xl font-bold mb-4")
    ui.separator()

    with ui.column().classes("w-full max-w-xl gap-4"):

        # Year
        ui.number(
            label="Year",
            value=state.year,
            min=2000,
            max=2055,
            step=1,
            format="%.0f",
            on_change=lambda e: _update_year(state, e.value),
        )

        # Calendar Type
        type_select = ui.select(
            label="Calendar Type",
            options=["wall", "desk", "photos", "birthdays"],
            value=export_state["calendar_type"],
            on_change=lambda e: _on_type_change(e.value),
        ).classes("w-full")

        # Format
        format_select = ui.select(
            label="Export Format",
            options=get_available_formats(),
            value=export_state["format"],
            on_change=lambda e: _on_format_change(e.value),
        ).classes("w-full")

        # Exporter variant
        available_exporters = get_available_exporters()
        if export_state["exporter_name"] not in available_exporters and available_exporters:
            export_state["exporter_name"] = available_exporters[0]

        exporter_select = ui.select(
            label="Exporter",
            options=available_exporters if available_exporters else ["(none available)"],
            value=export_state["exporter_name"] if available_exporters else "(none available)",
            on_change=lambda e: _on_exporter_change(e.value),
        ).classes("w-full")

        ui.separator()

        # Dynamic options container
        ui.label("Options").classes("text-lg font-semibold")
        options_container = ui.column().classes("w-full gap-2")
        option_controls: Dict[str, Any] = {}

        def rebuild_options():
            """Rebuild option controls from the current exporter's schema."""
            options_container.clear()
            option_controls.clear()
            schema = get_options_schema()

            # Load saved options for this exporter
            saved_opts = state.settings.get("export", {}).get("options", {}).get(
                export_state["exporter_name"], {}
            )

            if not schema:
                with options_container:
                    ui.label("No options available").classes("text-gray-500 italic")
                return

            with options_container:
                for opt_name, opt_spec in schema.items():
                    opt_type = opt_spec.get("type", "string")
                    description = opt_spec.get("description", "")
                    default = opt_spec.get("default")
                    # Use saved value if available
                    value = saved_opts.get(opt_name, default)

                    if opt_type in ("integer", "int"):
                        min_val = opt_spec.get("min", 0)
                        max_val = opt_spec.get("max", 999999)
                        ctrl = ui.number(
                            label=opt_name,
                            value=int(value) if value is not None else min_val,
                            min=min_val,
                            max=max_val,
                            step=1,
                            format="%.0f",
                        ).classes("w-full").tooltip(description)
                        option_controls[opt_name] = ("int", ctrl)

                    elif opt_type in ("boolean", "bool"):
                        ctrl = ui.switch(
                            text=opt_name,
                            value=bool(value) if value is not None else False,
                        ).tooltip(description)
                        option_controls[opt_name] = ("bool", ctrl)

                    elif opt_type in ("enum", "choices"):
                        choices = opt_spec.get("choices", [])
                        str_choices = [str(c) for c in choices]
                        ctrl = ui.select(
                            label=opt_name,
                            options=str_choices,
                            value=str(value) if value is not None else (str_choices[0] if str_choices else ""),
                        ).classes("w-full").tooltip(description)
                        option_controls[opt_name] = ("enum", ctrl)

                    else:  # string
                        ctrl = ui.input(
                            label=opt_name,
                            value=str(value) if value is not None else "",
                        ).classes("w-full").tooltip(description)
                        option_controls[opt_name] = ("string", ctrl)

        def get_options_values() -> Dict[str, Any]:
            """Extract current option values from UI controls."""
            values: Dict[str, Any] = {}
            schema = get_options_schema()
            for name, (typ, ctrl) in option_controls.items():
                if typ == "int":
                    values[name] = int(ctrl.value) if ctrl.value is not None else 0
                elif typ == "bool":
                    values[name] = bool(ctrl.value)
                elif typ == "enum":
                    # Try to match original type from schema
                    raw = ctrl.value
                    spec = schema.get(name, {})
                    choices = spec.get("choices", [])
                    # If choices are integers, convert back
                    if choices and isinstance(choices[0], int):
                        try:
                            raw = int(raw)
                        except (ValueError, TypeError):
                            pass
                    values[name] = raw
                else:
                    values[name] = ctrl.value or ""
            return values

        # Cascade handlers
        def _on_type_change(value: str):
            export_state["calendar_type"] = value
            # Update available formats
            new_formats = get_available_formats()
            format_select.options = new_formats
            if export_state["format"] not in new_formats:
                export_state["format"] = new_formats[0] if new_formats else "png"
            format_select.set_value(export_state["format"])
            _update_exporters()
            rebuild_options()

        def _on_format_change(value: str):
            export_state["format"] = value
            _update_exporters()
            rebuild_options()

        def _on_exporter_change(value: str):
            export_state["exporter_name"] = value
            rebuild_options()

        def _update_exporters():
            new_exporters = get_available_exporters()
            exporter_select.options = new_exporters if new_exporters else ["(none available)"]
            if export_state["exporter_name"] not in new_exporters:
                export_state["exporter_name"] = new_exporters[0] if new_exporters else "(none available)"
            exporter_select.set_value(export_state["exporter_name"])

        # Build initial options
        rebuild_options()

        ui.separator()

        # Progress bar (hidden initially)
        progress_bar = ui.linear_progress(value=0, show_value=False).classes("w-full")
        progress_bar.visible = False
        progress_label = ui.label("").classes("text-sm text-gray-600")
        progress_label.visible = False

        # Export button
        async def do_export():
            """Run the export."""
            if not state.project_path:
                ui.notify("No project loaded. Create or open a project first.", type="warning")
                return

            available = get_available_exporters()
            if not available or export_state["exporter_name"] == "(none available)":
                ui.notify("No exporter available for this combination.", type="warning")
                return

            fmt = get_format()
            data_type = get_data_type()
            exporter_name = export_state["exporter_name"]

            try:
                exporter = ExporterRegistry.get_exporter(fmt, data_type, exporter_name)
            except KeyError as ex:
                ui.notify(str(ex), type="negative")
                return

            # Collect options
            options = get_options_values()

            # Persist selection in settings
            export_settings = state.settings.setdefault("export", {})
            export_settings["calendar_type"] = export_state["calendar_type"]
            export_settings["format"] = export_state["format"]
            export_settings["exporter_name"] = exporter_name
            opts_store = export_settings.setdefault("options", {})
            opts_store[exporter_name] = options

            # Determine source
            source = _get_export_source(state, data_type)

            # Output directory
            fm = FilesManager.instance()
            if data_type in (DataType.WALL, DataType.DESK):
                output_base = f"{data_type.value.title()}Cal"
            elif data_type == DataType.PHOTOS:
                output_base = "Photos"
            else:
                output_base = "Birthdays"
            output_dir = Path(fm.get_file_path(output_base))

            # Progress
            progress_bar.visible = True
            progress_label.visible = True
            progress_bar.set_value(0)
            progress_label.set_text("Starting export...")

            def progress_cb(current: int, total: int, message: str):
                pct = current / total if total > 0 else 0
                progress_bar.set_value(pct)
                progress_label.set_text(message or f"{current}/{total}")

            context = ExportContext(
                source=source,
                data_type=data_type,
                format=fmt,
                output_dir=output_dir,
                project_root=fm.root,
                options=options,
                progress_callback=progress_cb,
            )

            try:
                result = exporter.export(context)
                progress_bar.set_value(1.0)

                if result.success:
                    progress_label.set_text(
                        f"Done — {result.file_count} file(s) exported to {output_dir}"
                    )
                    ui.notify(
                        f"Exported {result.file_count} file(s) to {output_dir}",
                        type="positive",
                    )
                else:
                    errors = "\n".join(result.errors)
                    progress_label.set_text(f"Completed with errors")
                    ui.notify(f"Export errors:\n{errors}", type="warning", multi_line=True)
            except Exception as ex:
                progress_bar.visible = False
                progress_label.set_text(f"Failed: {ex}")
                ui.notify(f"Export failed: {ex}", type="negative")

        ui.button("Export", icon="file_download", on_click=do_export).props("color=primary")


def _update_year(state: ProjectState, value):
    """Update year in state settings."""
    if value is not None:
        state.year = int(value)


def _get_export_source(state: ProjectState, data_type) -> Any:
    """Build the source object for export based on data type."""
    from lib.export import DataType

    if data_type == DataType.WALL:
        return _build_calendar(state, "artworks")
    elif data_type == DataType.DESK:
        return _build_calendar(state, "desk_pages")
    elif data_type == DataType.PHOTOS:
        return state.photo_labels.get("photos", [])
    else:  # BIRTHDAYS
        return state.birthdays.get("birthdays", [])


def _build_calendar(state: ProjectState, section: str):
    """Build a pycal.Calendar object from state data for wall/desk export."""
    import lib.pycal as libpycal
    import lib.calendar.ics_loader as libics
    from lib.filemanager import FilesManager

    # Build VCalendar from birthdays
    vcal = libics.VCalendar()
    for bday in state.birthdays.get("birthdays", []):
        import datetime
        try:
            date = datetime.datetime.strptime(bday.get("date", ""), "%d/%m/%Y")
            data = {
                libics.VCalendar.DATE_KEY: [date.date()],
                libics.VCalendar.SUMMARY_KEY: [bday.get("title", "")],
                libics.VCalendar.IMAGES_KEY: [bday.get("image")],
            }
            vcal.add(libics.VCalendar.VEvent(data))
        except (ValueError, TypeError):
            pass

    cal = libpycal.Calendar(state.year, libpycal.EventsManager(state.year, vcal))

    source = state.artworks if section == "artworks" else state.desk_pages
    pages = source.get("pages", [])

    # Resolve image paths via FilesManager if available
    try:
        fm = FilesManager.instance()
    except (TypeError, Exception):
        fm = None

    # Cover
    if pages:
        cover = pages[0]
        img = cover.get("image")
        if img and fm:
            img = str(fm.get_file_path(img))
        cal.front_page.image = img
        cal.front_page.title = cover.get("description", "")

    # Month arts
    arts = cal.arts
    for i in range(1, min(len(pages), 13)):
        page = pages[i]
        img = page.get("image")
        if img and fm:
            img = str(fm.get_file_path(img))
        arts[i - 1].image = img
        arts[i - 1].title = page.get("description", "")

    return cal
