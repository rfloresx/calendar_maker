"""JSON exporters for Photos and Birthdays.

Provides simple JSON output for photo labels and birthdays data.
"""

try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

from pathlib import Path
import json
from typing import Dict, Any, List

from lib.export.exporters import (
    BaseExporter,
    ExportFormat,
    DataType,
    ExportContext,
    ExportResult,
    ExporterRegistry,
)
import lib.pyimg as libpyimg

from lib.filemanager import FilesManager


class JsonPhotoLabelsExporter(BaseExporter):
    FORMAT = ExportFormat.JSON
    DATA_TYPE = DataType.PHOTOS
    NAME = "default"
    DESCRIPTION = "Export photo labels to Photos.json"
    OPTIONS_SCHEMA = {
        'filename': {
            'type': 'string',
            'description': 'Output JSON filename',
            'default': 'Photos.json',
        }
    }

    def export(self, context: ExportContext) -> ExportResult:
        self.validate_context(context)
        out_file = Path(context.output_dir, context.options.get(
            'filename', 'Photos.json'))

        photos: List[Dict[str, Any]] = context.source or []
        project_root: Path = context.project_root or FilesManager.instance().root

        result_items = []
        for item in photos:
            base_art = libpyimg.BaseArt.new(
                item, project_root)  # validate item

            result_items.append({
                'image': base_art.image,
                'label': base_art.description
            })

        out_file.write_text(json.dumps({'photos': result_items}, indent=2))
        return ExportResult(success=True, files=[out_file], format=self.FORMAT, data_type=self.DATA_TYPE)


class JsonBirthdaysExporter(BaseExporter):
    FORMAT = ExportFormat.JSON
    DATA_TYPE = DataType.BIRTHDAYS
    NAME = "default"
    DESCRIPTION = "Export birthdays to Birthdays.json"
    OPTIONS_SCHEMA = {
        'filename': {
            'type': 'string',
            'description': 'Output JSON filename',
            'default': 'Birthdays.json',
        }
    }

    def export(self, context: ExportContext) -> ExportResult:
        self.validate_context(context)
        out_file = Path(context.output_dir, context.options.get(
            'filename', 'Birthdays.json'))
        birthdays: List[Dict[str, Any]] = context.source or []

        out_file.write_text(json.dumps({'birthdays': birthdays}, indent=2))
        return ExportResult(success=True, files=[out_file], format=self.FORMAT, data_type=self.DATA_TYPE)


# Register exporters
ExporterRegistry.register(JsonPhotoLabelsExporter)
ExporterRegistry.register(JsonBirthdaysExporter)
