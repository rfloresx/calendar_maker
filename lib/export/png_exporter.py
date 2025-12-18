"""PNG image exporters for wall and desk calendars.

This module provides PNG export implementations that wrap the existing
lib.print modules (wall_cal and desk_cal). The exporters generate high-
resolution PNG images suitable for printing.

Classes:
    PngWallCalendarExporter: Exports wall calendars as PNG images
    PngDeskCalendarExporter: Exports desk calendars as PNG images (with optional legal expansion)
"""

try:
    import lib as __lib
except:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

import time
from pathlib import Path
from typing import List, Generator
import PIL.Image

import lib.print.wall_cal as libwallcal
import lib.print.desk_cal as libdeskcal
import lib.print.draw as libdraw

from lib.export.exporters import (
    BaseExporter,
    ExportContext,
    ExportResult,
    ExportFormat,
    CalendarType,
    ExporterRegistry,
)


class PngWallCalendarExporter(BaseExporter):
    """Export wall calendars to PNG image files.
    
    Generates a series of PNG files (one per page) for a wall calendar.
    Each file is named Page_0.png, Page_1.png, etc., where:
    - Page 0: Front cover page
    - Page 1+: Alternating art and month pages
    
    The exporter uses lib.print.wall_cal.ImageDrawer to render pages at
    the configured DPI.
    """
    
    FORMAT = ExportFormat.PNG
    CALENDAR_TYPE = CalendarType.WALL
    NAME = "default"
    DESCRIPTION = "Export wall calendar as high-resolution PNG images"
    OPTIONS_SCHEMA = {
        'dpi': {
            'type': 'enum',
            'default': 300,
            'choices': [32, 64, 96, 150, 300, 600, 1200],
            'description': 'Dots per inch for rendering the PNG images',
        },
        'skip_months': {
            'type': 'boolean',
            'default': False,
            'description': 'If True, skip month pages (export cover + art pages only)',
        }
    }

    def export(self, context: ExportContext) -> ExportResult:
        """Export wall calendar to PNG files.
        
        Args:
            context: ExportContext with calendar and output settings.
                    Options:
                    - dpi (int): Dots per inch for rendering (default: 300)
                    - skip_months (bool): Skip month pages, export only cover and art (default: False)
            
        Returns:
            ExportResult with list of generated PNG files
        """
        start_time = time.time()
        
        # Validate context
        self.validate_context(context)
        
        # Get options
        dpi = int(context.options.get('dpi', 300))
        skip_months = context.options.get('skip_months', False)
        
        # Configure DPI for drawing
        libdraw.Resolution.dpi = dpi
        libwallcal.ImageDrawer.dpi = dpi
        
        result = ExportResult(
            success=True,
            files=[],
            format=self.FORMAT,
            calendar_type=self.CALENDAR_TYPE,
        )
        
        try:
            # Generate images using existing wall_cal renderer
            # Process as generator to avoid loading all images into memory
            imgs = libwallcal.ImageDrawer.draw(context.calendar)
            
            # Determine page indices to skip if skip_months is enabled
            # Page 0: Front cover (keep)
            # Pages 1+: Alternating art (odd) and month (even) pages
            # If skip_months, we want to skip even pages (2, 4, 6, ...)
            
            # Estimate total pages: 1 cover + 12 months + 12 art = 25
            estimated_total = 25
            page_index = 0  # Index in the generated stream
            output_index = 0  # Index for output filenames (sequential)
            
            for img in imgs:                
                # Determine if this is a month page (even index > 0)
                is_month_page = page_index > 0 and page_index % 2 == 0
                
                # Skip if it's a month page and skip_months is enabled
                if skip_months and is_month_page:
                    page_index += 1
                    continue
                
                context.report_progress(output_index + 1, estimated_total, f"Saving page {output_index}")
                
                if img is None:
                    result.add_error(f"Page {output_index} returned None from renderer")
                    page_index += 1
                    continue
                
                # Build output filename using sequential output_index
                output_path = context.output_dir / f"Page_{output_index}.png"
                
                # Save with DPI metadata
                img.save(str(output_path), dpi=(dpi, dpi))
                result.files.append(output_path)
                
                page_index += 1
                output_index += 1
            
            # Add metadata
            result.metadata['dpi'] = dpi
            result.metadata['total_pages'] = len(result.files)
            result.metadata['page_size'] = f"{libwallcal.WallCalPage.WIDTH}x{libwallcal.WallCalPage.HEIGHT} in"
            result.metadata['skip_months'] = skip_months
            
        except Exception as e:
            result.add_error(f"Export failed: {str(e)}")
        
        result.duration = time.time() - start_time
        return result


class PngDeskCalendarExporter(BaseExporter):
    """Export desk calendars to PNG image files.
    
    Generates PNG files for a desk calendar with two output modes:
    1. Standard: One PNG per page (7x4.25 inches)
    2. Expanded: Additional legal-sized PNGs (14x8.5 inches) with 2x2 tiled layout
    
    Output files are organized in subdirectories:
    - DeskCal/: Standard desk calendar pages
    - DeskCalExt/: Expanded legal-sized pages (if generate_expanded=True)
    
    The expanded format tiles the desk page in a 2x2 grid with the bottom
    row rotated 180 degrees for tent-fold style printing.
    
    Options (passed via context.options):
        generate_expanded (bool): If True, also generate legal-sized versions.
                                 Default: True
    """
    
    FORMAT = ExportFormat.PNG
    CALENDAR_TYPE = CalendarType.DESK
    NAME = "default"
    DESCRIPTION = "Export desk calendar as PNG images with optional legal expansion"
    OPTIONS_SCHEMA = {
        'dpi': {
            'type': 'enum',
            'default': 300,
            'choices': [32, 64, 96, 150, 300, 600, 1200],
            'description': 'Dots per inch for rendering the PNG images',
        },
        'generate_expanded': {
            'type': 'boolean',
            'default': True,
            'description': 'If True, generate legal-sized expanded versions',
        },
    }

    def export(self, context: ExportContext) -> ExportResult:
        """Export desk calendar to PNG files.
        
        Args:
            context: ExportContext with calendar and output settings.
                    Options:
                    - dpi (int): Dots per inch for rendering (default: 300)
                    - generate_expanded (bool): Generate legal-sized versions (default: True)
            
        Returns:
            ExportResult with list of generated PNG files
        """
        start_time = time.time()
        
        # Validate context
        self.validate_context(context)
        
        # Get options
        dpi = int(context.options.get('dpi', 300))
        generate_expanded = context.options.get('generate_expanded', True)
        
        # Configure DPI for drawing
        libdraw.Resolution.dpi = dpi
        libdeskcal.ImageDrawer.dpi = dpi
        
        result = ExportResult(
            success=True,
            files=[],
            format=self.FORMAT,
            calendar_type=self.CALENDAR_TYPE,
        )
        
        try:
            # Create subdirectories
            desk_dir = context.output_dir / "DeskCal"
            desk_dir.mkdir(parents=True, exist_ok=True)
            
            if generate_expanded:
                desk_ext_dir = context.output_dir / "DeskCalExt"
                desk_ext_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate images using existing desk_cal renderer
            # Process as generator to show progress during generation
            imgs_generator = libdeskcal.ImageDrawer.draw(context.calendar)
            
            # Estimate total: 1 cover + 12 months = 13 pages
            estimated_total = 13
            expanded_files = []

            # Now save the generated images
            total_pages = 0
            for i, img in enumerate(imgs_generator):
                context.report_progress(i + 1, estimated_total, f"Saving page {i}")
                
                if img is None:
                    result.add_error(f"Page {i} returned None from renderer")
                    continue
                
                # Get the actual PIL.Image from the wrapped object if needed
                if hasattr(img, 'image'):
                    pil_img = img.image
                else:
                    pil_img = img
                
                # Save standard desk calendar page
                desk_path = desk_dir / f"Page_{i}.png"
                pil_img.save(str(desk_path))
                result.files.append(desk_path)
                
                # Generate expanded legal-sized version if requested
                if generate_expanded:
                    img_ext = libdeskcal.expan_to_legal(pil_img)
                    desk_ext_path = desk_ext_dir / f"Page_{i}.png"
                    img_ext.save(str(desk_ext_path))
                    expanded_files.append(desk_ext_path)
                
                total_pages = i + 1
            # Add expanded files to result
            result.files.extend(expanded_files)
            
            # Add metadata
            result.metadata['dpi'] = dpi
            result.metadata['total_pages'] = total_pages
            result.metadata['standard_files'] = total_pages
            result.metadata['expanded_files'] = len(expanded_files)
            result.metadata['page_size_standard'] = f"{libdeskcal.DeskCalSize.WIDTH}x{libdeskcal.DeskCalSize.HEIGHT} in"
            result.metadata['page_size_expanded'] = "14x8.5 in (legal landscape)"
            result.metadata['generate_expanded'] = generate_expanded
            
        except Exception as e:
            result.add_error(f"Export failed: {str(e)}")
        
        result.duration = time.time() - start_time
        return result


# Auto-register exporters when module is imported
ExporterRegistry.register(PngWallCalendarExporter)
ExporterRegistry.register(PngDeskCalendarExporter)
