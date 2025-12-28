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
import lib.print.wall_cal_v2 as libwallcalv2

import lib.print.desk_cal as libdeskcal
import lib.print.draw as libdraw
import lib.print.photo_info as libphotoinfo
import lib.pyimg as libpyimg

from lib.export.exporters import (
    BaseExporter,
    ExportContext,
    ExportResult,
    ExportFormat,
    DataType,
    ExporterRegistry,
)


class PngWallCalendarExporterBase(BaseExporter):
    _WAL_CAL = None  # To be defined in subclasses
    """Export wall calendars to PNG image files.
    
    Generates a series of PNG files (one per page) for a wall calendar.
    Each file is named Page_0.png, Page_1.png, etc., where:
    - Page 0: Front cover page
    - Page 1+: Alternating art and month pages
    
    The exporter uses lib.print.wall_cal.ImageDrawer to render pages at
    the configured DPI.
    """
    
    FORMAT = ExportFormat.PNG
    DATA_TYPE = DataType.WALL
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
        self._WAL_CAL.ImageDrawer.dpi = dpi
        
        result = ExportResult(
            success=True,
            files=[],
            format=self.FORMAT,
            data_type=self.DATA_TYPE,
        )
        
        try:
            # Generate images using existing wall_cal renderer
            # Process as generator to avoid loading all images into memory
            imgs = self._WAL_CAL.ImageDrawer.draw(context.source)
            
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
            result.metadata['page_size'] = f"{self._WAL_CAL.WallCalPage.WIDTH}x{self._WAL_CAL.WallCalPage.HEIGHT} in"
            result.metadata['skip_months'] = skip_months
            
        except Exception as e:
            result.add_error(f"Export failed: {str(e)}")
        
        result.duration = time.time() - start_time
        return result

class PngWallCalendarExporter(PngWallCalendarExporterBase):
    """PNG exporter for wall calendars using lib.print.wall_cal."""
    _WAL_CAL = libwallcal
    NAME = "wall_cal_v1"

class PngWallCalendarExporterV2(PngWallCalendarExporterBase):
    """PNG exporter for wall calendars using lib.print.wall_cal_v2."""
    _WAL_CAL = libwallcalv2
    NAME = "wall_cal_v2"


class PngDeskCalendarExporterBase(BaseExporter):
    """Base class for desk calendar PNG exporters.

    Subclasses define the output subdirectory and the image transform
    (standard page vs. legal-sized expanded page).
    """

    FORMAT = ExportFormat.PNG
    DATA_TYPE = DataType.DESK

    OPTIONS_SCHEMA = {
        'dpi': {
            'type': 'enum',
            'default': 300,
            'choices': [32, 64, 96, 150, 300, 600, 1200],
            'description': 'Dots per inch for rendering the PNG images',
        },
    }

    def get_output_subdir_name(self) -> str:
        """Return the subdirectory name where pages are saved."""
        raise NotImplementedError()

    def transform_image(self, img: PIL.Image.Image) -> PIL.Image.Image:
        """Return the image to save (may be transformed)."""
        return img

    def page_size_str(self) -> str:
        """Human-readable page size string for metadata."""
        raise NotImplementedError()

    def export(self, context: ExportContext) -> ExportResult:
        """Export desk calendar pages to PNG files."""
        start_time = time.time()

        # Validate context
        self.validate_context(context)

        # Get options
        dpi = int(context.options.get('dpi', 300))

        # Configure DPI for drawing
        libdraw.Resolution.dpi = dpi
        libdeskcal.ImageDrawer.dpi = dpi

        result = ExportResult(
            success=True,
            files=[],
            format=self.FORMAT,
            data_type=self.DATA_TYPE,
        )

        try:
            # Create output subdirectory
            out_dir = context.output_dir / self.get_output_subdir_name()
            out_dir.mkdir(parents=True, exist_ok=True)

            # Generate images using existing desk_cal renderer
            imgs_generator = libdeskcal.ImageDrawer.draw(context.source)

            # Estimate total: 1 cover + 12 months = 13 pages
            estimated_total = 13
            total_pages = 0

            for i, img in enumerate(imgs_generator):
                context.report_progress(i + 1, estimated_total, f"Saving page {i}")

                if img is None:
                    result.add_error(f"Page {i} returned None from renderer")
                    continue

                # Get PIL.Image from wrapper if needed
                pil_img = img.image if hasattr(img, 'image') else img

                # Transform (e.g., expand to legal) and save with DPI metadata
                final_img = self.transform_image(pil_img)
                out_path = out_dir / f"Page_{i}.png"
                final_img.save(str(out_path), dpi=(dpi, dpi))
                result.files.append(out_path)

                total_pages = i + 1

            # Add metadata
            result.metadata['dpi'] = dpi
            result.metadata['total_pages'] = total_pages
            result.metadata['page_size'] = self.page_size_str()

        except Exception as e:
            result.add_error(f"Export failed: {str(e)}")

        result.duration = time.time() - start_time
        return result

class PngDeskCalendarExporterStandard(PngDeskCalendarExporterBase):
    """Export standard desk calendar pages to PNG (7x4.25 inches)."""
    NAME = "desk_cal_standard"
    DESCRIPTION = "Export standard desk calendar PNG images"

    def get_output_subdir_name(self) -> str:
        return "DeskCal"

    def page_size_str(self) -> str:
        return f"{libdeskcal.DeskCalSize.WIDTH}x{libdeskcal.DeskCalSize.HEIGHT} in"

class PngDeskCalendarExporterLegal(PngDeskCalendarExporterBase):
    """Export legal-sized expanded desk calendar pages to PNG (14x8.5 inches).

    Uses a 2x2 tiled layout with bottom row rotated for tent-fold printing.
    """
    NAME = "desk_cal_legal"
    DESCRIPTION = "Export legal-sized expanded desk calendar PNG images (2x2 tiled)"

    def get_output_subdir_name(self) -> str:
        return "DeskCalExt"

    def transform_image(self, img: PIL.Image.Image) -> PIL.Image.Image:
        return libdeskcal.expan_to_legal(img)

    def page_size_str(self) -> str:
        return "14x8.5 in (legal landscape)"


# Auto-register exporters when module is imported
ExporterRegistry.register(PngWallCalendarExporter)
ExporterRegistry.register(PngWallCalendarExporterV2)
ExporterRegistry.register(PngDeskCalendarExporterStandard)
ExporterRegistry.register(PngDeskCalendarExporterLegal)

# --- Photos PNG Exporter ---

class PngPhotoExporter(BaseExporter):
    """Export labeled photos as PNG images.

    Uses `lib.print.photo_info.ImageDrawer` to render each photo with its
    description at the bottom-left over a semi-transparent black background.
    Saves output files under a `Photos/` subdirectory.
    """

    FORMAT = ExportFormat.PNG
    DATA_TYPE = DataType.PHOTOS
    NAME = "default"
    DESCRIPTION = "Export labeled photos as PNG images"
    OPTIONS_SCHEMA = {
        'dpi': {
            'type': 'enum',
            'default': 300,
            'choices': [32, 64, 96, 150, 300, 600, 1200],
            'description': 'Dots per inch for rendering the PNG images',
        },
        'aspect_ratio': {
            'type': 'enum',
            'default': 'original',
            'choices': ['original', '1:1', '3:2', '4:3', '5:4', '16:9'],
            'description': 'Aspect ratio for exported photos',
        },
        'portrait': {
            'type': 'boolean',
            'default': False,
            'description': 'If True, use portrait orientation for exported photos',
        },
        'output_subdir': {
            'type': 'string',
            'default': 'Photos',
            'description': 'Subdirectory name for exported photo images',
        },
        'use_original_names': {
            'type': 'boolean',
            'default': True,
            'description': 'If True, use original image stem as filename; otherwise use sequential names',
        },
    }

    def export(self, context: ExportContext) -> ExportResult:
        """Export photos with labels to PNG files."""
        import time
        from pathlib import Path
        from lib.filemanager import FilesManager

        start_time = time.time()
        self.validate_context(context)

        # Options
        dpi = int(context.options.get('dpi', 300))
        out_subdir = context.options.get('output_subdir', 'Photos')
        use_original = bool(context.options.get('use_original_names', True))
        portrait = bool(context.options.get('portrait', False))
        aspect_ratio_option = context.options.get('aspect_ratio', 'original')
        aspect_map = {
            'original': libphotoinfo.ImageDrawer.Aspect.AUTO,
            '1:1': libphotoinfo.ImageDrawer.Aspect.SQUARE,
            '3:2': libphotoinfo.ImageDrawer.Aspect.STANDARD,
            '4:3': libphotoinfo.ImageDrawer.Aspect.MICRO_FOUR_THIRDS,
            '5:4': libphotoinfo.ImageDrawer.Aspect.EIGHT_BY_TEN,
            '16:9': libphotoinfo.ImageDrawer.Aspect.WIDESCREEN,
        }
        aspect_ratio = aspect_map.get(aspect_ratio_option, libphotoinfo.ImageDrawer.Aspect.AUTO)
        libphotoinfo.ImageDrawer.aspect = aspect_ratio
        libphotoinfo.ImageDrawer.portrait = portrait
        libphotoinfo.ImageDrawer.dpi = dpi

        result = ExportResult(
            success=True,
            files=[],
            format=self.FORMAT,
            data_type=self.DATA_TYPE,
        )

        try:
            photos = context.source or []
            project_root = context.project_root or FilesManager.instance().root

            # Output directory
            out_dir = context.output_dir / out_subdir
            out_dir.mkdir(parents=True, exist_ok=True)

            total = len(photos) if hasattr(photos, '__len__') else 0

            for i, item in enumerate(photos):
                context.report_progress(i + 1, max(total, 1), f"Rendering photo {i}")

                # Build BaseArt and render
                base_art = libpyimg.BaseArt.new(item, project_root)
                imgs = libphotoinfo.ImageDrawer.draw(base_art)
                img = None
                for img in imgs:
                    break
                if img is None:
                    result.add_error(f"Photo {i} returned None from renderer")
                    continue

                pil_img = img.image if hasattr(img, 'image') else img

                # Determine filename
                stem = None
                if use_original and base_art.image:
                    try:
                        stem = Path(base_art.image).stem
                    except Exception:
                        stem = None
                if not stem:
                    stem = f"Photo_{i}"

                out_path = out_dir / f"{stem}.png"
                pil_img.save(str(out_path), dpi=(dpi, dpi))
                result.files.append(out_path)

            # Metadata
            result.metadata['dpi'] = dpi
            result.metadata['total_photos'] = len(result.files)
            result.metadata['output_subdir'] = out_subdir

        except Exception as e:
            result.add_error(f"Export failed: {str(e)}")

        result.duration = time.time() - start_time
        return result

# Register the photos PNG exporter
ExporterRegistry.register(PngPhotoExporter)
