"""Core export API and base classes.

This module defines the foundational classes for the export system:
- BaseExporter: Abstract base class that all exporters must implement
- ExporterRegistry: Central registry for managing and instantiating exporters
- ExportFormat: Enumeration of supported export formats
- DataType: Enumeration for export data types (wall calendar, desk calendar, photos, birthdays)
- ExportContext: Data class containing all export parameters
- ExportResult: Data class containing export operation results

The architecture uses a registry pattern to allow dynamic registration of
new exporters without modifying core code.
"""

try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Type, Any, Callable
from pathlib import Path
import datetime

import lib.pycal as libcal


class ExportFormat(Enum):
    """Enumeration of supported export formats.
    
    Each format represents a different output type for calendar exports.
    New formats can be added as needed.
    """
    PNG = "png"           # PNG image files
    HTML = "html"         # HTML documents
    PDF = "pdf"           # PDF documents
    SVG = "svg"           # SVG vector graphics
    ICS = "ics"           # iCalendar format
    JSON = "json"         # JSON data export
    
    def __str__(self) -> str:
        return self.value


class DataType(Enum):
    """Enumeration of export data types.

    - WALL: Wall calendar (large format, monthly pages)
    - DESK: Desk calendar (compact format, tent-fold style)
    - PHOTOS: Photo labels data
    - BIRTHDAYS: Birthdays data
    """
    WALL = "wall"
    DESK = "desk"
    PHOTOS = "photos"
    BIRTHDAYS = "birthdays"

    def __str__(self) -> str:
        return self.value


@dataclass
class ExportContext:
    """Context object containing all parameters for an export operation.
    
    The ExportContext encapsulates all the information needed to perform
    an export, including the calendar data, output settings, and format
    preferences. This allows exporters to be stateless and testable.
    
    Attributes:
        source: The source object to export (e.g., Calendar for wall/desk, list for photos/birthdays)
        data_type: The DataType describing the source
        format: Desired export format
        output_dir: Directory where exported files should be saved
        project_root: Optional project root for relative path resolution
        options: Additional format-specific options (e.g., generate_expanded, embed_images)
        progress_callback: Optional callback for progress updates
    """
    source: Any
    data_type: DataType
    format: ExportFormat
    output_dir: Path
    project_root: Optional[Path] = None
    options: Dict[str, Any] = field(default_factory=dict)
    progress_callback: Optional[Callable[[int, int, str], None]] = None
    
    def __post_init__(self):
        """Validate and normalize context fields after initialization."""
        # Ensure output_dir is a Path object
        if not isinstance(self.output_dir, Path):
            self.output_dir = Path(self.output_dir)
        
        # Ensure project_root is a Path object if provided
        if self.project_root and not isinstance(self.project_root, Path):
            self.project_root = Path(self.project_root)
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def year(self) -> int:
        """Return the year from the calendar when available, else current year."""
        try:
            return getattr(self.source, 'year')
        except Exception:
            return datetime.datetime.now().year
    
    def report_progress(self, current: int, total: int, message: str = ""):
        """Report progress if a callback is registered.
        
        Args:
            current: Current progress value (e.g., page number)
            total: Total items to process
            message: Optional status message
        """
        if self.progress_callback:
            self.progress_callback(current, total, message)


@dataclass
class ExportResult:
    """Result object returned by export operations.
    
    Contains information about the export operation including success status,
    generated files, and any errors encountered.
    
    Attributes:
        success: Whether the export completed successfully
        files: List of file paths that were generated
        format: Export format that was used
        calendar_type: Calendar type that was exported
        errors: List of error messages if any occurred
        metadata: Additional format-specific metadata
        duration: Time taken for the export operation
    """
    success: bool
    files: List[Path]
    format: ExportFormat
    data_type: DataType
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration: Optional[float] = None
    
    @property
    def file_count(self) -> int:
        """Return the number of files generated."""
        return len(self.files)
    
    def add_error(self, error: str):
        """Add an error message to the result.
        
        Args:
            error: Error message to add
        """
        self.errors.append(error)
        self.success = False


class BaseExporter(ABC):
    """Abstract base class for all calendar exporters.
    
    All exporters must inherit from this class and implement the export()
    method. Exporters should be stateless - all export parameters should
    be passed via the ExportContext.
    
    Class attributes:
        FORMAT: The ExportFormat this exporter handles
        DATA_TYPE: The DataType this exporter handles
        NAME: Unique identifier for this exporter variant (e.g., "standard", "compact", "v2")
        DESCRIPTION: Human-readable description of this exporter
    """
    
    FORMAT: ExportFormat = None
    DATA_TYPE: DataType = None
    NAME: str = "default"  # Unique name for this exporter variant
    DESCRIPTION: str = ""
    OPTIONS_SCHEMA: Dict[str, Any] = {}  # Optional schema for context options validation

    @abstractmethod
    def export(self, context: ExportContext) -> ExportResult:
        """Perform the export operation.
        
        This method must be implemented by all exporters. It should:
        1. Validate the context
        2. Generate the output files
        3. Return an ExportResult with status and file list
        
        Args:
            context: ExportContext containing all export parameters
            
        Returns:
            ExportResult with success status and generated files
            
        Raises:
            ValueError: If context is invalid for this exporter
            IOError: If file operations fail
        """
        pass
    
    def validate_context(self, context: ExportContext) -> bool:
        """Validate that the context is appropriate for this exporter.
        
        Args:
            context: ExportContext to validate
            
        Returns:
            True if context is valid
            
        Raises:
            ValueError: If context is invalid with explanation
        """
        if context.format != self.FORMAT:
            raise ValueError(
                f"{self.__class__.__name__} expects format {self.FORMAT}, "
                f"got {context.format}"
            )
        
        if context.data_type != self.DATA_TYPE:
            raise ValueError(
                f"{self.__class__.__name__} expects data type {self.DATA_TYPE}, "
                f"got {context.data_type}"
            )
        
        if context.source is None:
            raise ValueError("ExportContext must have a source")
        
        return True
    
    @classmethod
    def get_info(cls) -> Dict[str, str]:
        """Get information about this exporter.
        
        Returns:
            Dictionary with format, data_type, name, and description
        """
        return {
            'format': str(cls.FORMAT) if cls.FORMAT else 'unknown',
            'data_type': str(cls.DATA_TYPE) if cls.DATA_TYPE else 'unknown',
            'name': cls.NAME,
            'description': cls.DESCRIPTION,
            'class': cls.__name__,
        }

class ExporterRegistry:
    """Central registry for managing calendar exporters.
    
    The ExporterRegistry provides a factory pattern for creating exporters
    and maintains a mapping of (format, data_type, name) -> exporter class.
    Multiple exporters can be registered for the same format+data_type by
    using different names.
    
    Usage:
        # Register exporters
        ExporterRegistry.register(StandardPngWallExporter)  # name="default"
        ExporterRegistry.register(CompactPngWallExporter)   # name="compact"
        
        # Get default exporter
        exporter = ExporterRegistry.get_exporter(ExportFormat.PNG, CalendarType.WALL)
        
        # Get specific named exporter
        exporter = ExporterRegistry.get_exporter(ExportFormat.PNG, CalendarType.WALL, "compact")
        
        # List all registered exporters
        exporters = ExporterRegistry.list_exporters()
    """
    
    _registry: Dict[tuple, Type[BaseExporter]] = {}  # (format, data_type, name) -> class
    
    @classmethod
    def register(cls, exporter_class: Type[BaseExporter]) -> None:
        """Register an exporter class.
        
        Args:
            exporter_class: Class inheriting from BaseExporter
            
        Raises:
            ValueError: If exporter is missing required attributes
            TypeError: If exporter_class is not a BaseExporter subclass
        """
        if not issubclass(exporter_class, BaseExporter):
            raise TypeError(
                f"{exporter_class.__name__} must inherit from BaseExporter"
            )
        
        if exporter_class.FORMAT is None:
            raise ValueError(
                f"{exporter_class.__name__} must define FORMAT class attribute"
            )
        
        if getattr(exporter_class, 'DATA_TYPE', None) is None:
            raise ValueError(
                f"{exporter_class.__name__} must define DATA_TYPE class attribute"
            )
        
        if not exporter_class.NAME:
            raise ValueError(
                f"{exporter_class.__name__} must define NAME class attribute"
            )
        
        key = (exporter_class.FORMAT, exporter_class.DATA_TYPE, exporter_class.NAME)
        
        if key in cls._registry:
            existing = cls._registry[key]
            print(
                f"Warning: Replacing exporter for {key}: "
                f"{existing.__name__} -> {exporter_class.__name__}"
            )
        
        cls._registry[key] = exporter_class
    
    @classmethod
    def get_exporter(
        cls,
        format: ExportFormat,
        data_type: DataType,
        name: str = "default"
    ) -> BaseExporter:
        """Get an exporter instance for the specified format, calendar type, and name.
        
        Args:
            format: Desired export format
            data_type: Type of data to export
            name: Name of the specific exporter variant (default: "default")
            
        Returns:
            Instance of the appropriate exporter
            
        Raises:
            KeyError: If no exporter is registered for the given combination
        """
        key = (format, data_type, name)
        
        if key not in cls._registry:
            # Try to provide helpful error message
            available = cls.get_exporters_for(format, data_type)
            if available:
                available_names = [exp['name'] for exp in available]
                raise KeyError(
                    f"No exporter registered for {format} + {data_type} + '{name}'. "
                    f"Available names: {available_names}"
                )
            else:
                raise KeyError(
                    f"No exporter registered for {format} + {data_type}. "
                    f"Available: {cls.list_exporters()}"
                )
        
        exporter_class = cls._registry[key]
        return exporter_class()
    
    @classmethod
    def has_exporter(
        cls,
        format: ExportFormat,
        data_type: DataType,
        name: str = "default"
    ) -> bool:
        """Check if an exporter exists for the given format, calendar type, and name.
        
        Args:
            format: Export format to check
            calendar_type: Calendar type to check
            name: Exporter name to check (default: "default")
            
        Returns:
            True if an exporter is registered
        """
        return (format, data_type, name) in cls._registry
    
    @classmethod
    def list_exporters(cls) -> List[Dict[str, str]]:
        """List all registered exporters with their information.
        
        Returns:
            List of dictionaries containing exporter information
        """
        return [
            exporter_class.get_info()
            for exporter_class in cls._registry.values()
        ]
    
    @classmethod
    def get_exporters_for(
        cls,
        format: ExportFormat = None,
        data_type: DataType = None
    ) -> List[Dict[str, str]]:
        """Get all exporters registered for a specific format and calendar type.
        
        Args:
            format: Export format to query
            calendar_type: Calendar type to query
            
        Returns:
            List of exporter info dictionaries for the given format+calendar_type
        """
        matching = [
            exporter_class.get_info()
            for (fmt, cal_type, name), exporter_class in cls._registry.items()
            if (format is None or fmt == format) and (data_type is None or cal_type == data_type)
        ]
        return sorted(matching, key=lambda e: e['name'])
    
    @classmethod
    def get_formats_for_data_type(cls, data_type: DataType) -> List[ExportFormat]:
        """Get all available export formats for a given calendar type.
        
        Args:
            data_type: Data type to query
            
        Returns:
            List of ExportFormats available for this calendar type (unique)
        """
        formats = set(
            fmt for fmt, cal_type, name in cls._registry.keys()
            if cal_type == data_type
        )
        return sorted(formats, key=lambda f: f.value)
    
    @classmethod
    def get_data_types_for_format(cls, format: ExportFormat) -> List[DataType]:
        """Get all available calendar types for a given export format.
        
        Args:
            format: Export format to query
            
        Returns:
            List of DataTypes available for this format (unique)
        """
        data_types = set(
            cal_type for fmt, cal_type, name in cls._registry.keys()
            if fmt == format
        )
        return sorted(data_types, key=lambda ct: ct.value)
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered exporters.
        
        This is primarily useful for testing.
        """
        cls._registry.clear()


# Convenience function for quick exports
def export_data(
    source: Any,
    format: ExportFormat,
    data_type: DataType,
    output_dir: str | Path,
    exporter_name: str = "default",
    **kwargs
) -> ExportResult:
    """Convenience function to export data in one call.

    Creates an ExportContext, retrieves the appropriate exporter, and performs the export.
    """
    context = ExportContext(
        source=source,
        data_type=data_type,
        format=format,
        output_dir=Path(output_dir),
        **kwargs
    )

    exporter = ExporterRegistry.get_exporter(format, data_type, exporter_name)
    return exporter.export(context)

