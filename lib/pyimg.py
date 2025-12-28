from pathlib import Path
from lib.gui.util import get_image_metadata, ImageInfo, TextTemplate, build_text_context

from typing import Dict, Any, List


def _process_photo_template(image_path: Path, template: str, selected_place_index: int, overrides: Dict[str, Any]) -> str:
    """Process a photo label template using TextTemplate with built context."""
    try:
        metadata = get_image_metadata(str(image_path))
        info = ImageInfo(filename=str(image_path), metadata=metadata)
        # overrides are stored with string keys in JSON; accept both
        ov = None
        if isinstance(overrides, dict):
            ov = overrides.get(str(selected_place_index)) or overrides.get(selected_place_index)
        ctx = build_text_context(
            info, selected_place_index=selected_place_index, overrides=ov, year=None)
        return TextTemplate(template or "").render(ctx)
    except Exception:
        return template or ""


class BaseArt:
    def __init__(self, image: str = None, description: str = ""):
        self._image = image
        self._description = description

    @staticmethod
    def new(data: dict, project_root: Path) -> "BaseArt":
        rel_image = data.get('image')
        template = data.get('template')
        spi = int(data.get('selected_place_index', 0))
        overrides = data.get('place_overrides', {})

        if rel_image:
            abs_image = Path(project_root, rel_image)
            description = _process_photo_template(abs_image, template, spi, overrides)
        else:
            abs_image = None
            description = template or ""
        return BaseArt(image=rel_image, description=description)

    @property
    def image(self) -> str:
        return self._image

    @property
    def description(self) -> str:
        return self._description
