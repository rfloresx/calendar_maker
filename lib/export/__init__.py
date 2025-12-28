"""Export module for calendar generation.

This module provides a flexible, extensible API for exporting calendars
in multiple formats (PNG, HTML, PDF, ICS, etc.). The core architecture
uses a registry pattern to allow easy addition of new export formats.

Key components:
    - BaseExporter: Abstract base class for all exporters
    - ExporterRegistry: Central registry and factory for exporters
    - ExportFormat: Enumeration of supported export formats
    - ExportContext: Data container with calendar, settings, and output info
    - DataType: Enumeration for export data types

Example usage:
    ```python
    from lib.export import ExporterRegistry, ExportFormat, ExportContext, DataType
    from lib.pycal import Calendar
    from lib.gui.settings import Settings
    
    # Create export context
    context = ExportContext(
        calendar=my_calendar,
        data_type=DataType.WALL,
        format=ExportFormat.PNG,
        output_dir="/path/to/output"
    )
    
    # Get and run exporter
    exporter = ExporterRegistry.get_exporter(ExportFormat.PNG, CalendarType.WALL)
    results = exporter.export(context)
    ```
"""

from lib.export.exporters import (
    BaseExporter,
    ExporterRegistry,
    ExportFormat,
    ExportContext,
    DataType,
    ExportResult,
)

# Import exporters to auto-register them
import lib.export.png_exporter  # noqa: F401
import lib.export.json_exporter  # noqa: F401

__all__ = [
    'BaseExporter',
    'ExporterRegistry',
    'ExportFormat',
    'ExportContext',
    'DataType',
    'ExportResult',
]
