"""Reusable image upload component with preview."""

from typing import Callable, Optional
from nicegui import ui, events

from lib.web.storage import save_uploaded_image, get_image_absolute_path
from lib.web.config import PROJECTS_DIR


class ImageUpload:
    """Image upload widget with thumbnail preview.

    Provides a drag-and-drop upload area that saves the image to the project
    file store and displays a thumbnail preview.
    """

    def __init__(
        self,
        project_id: str,
        current_image: Optional[str] = None,
        on_change: Optional[Callable[[str], None]] = None,
        max_size: int = 10 * 1024 * 1024,  # 10MB
        label: str = "Upload Image",
    ):
        self.project_id = project_id
        self.current_image = current_image
        self.on_change = on_change
        self.max_size = max_size

        with ui.column().classes("items-center gap-2"):
            self._preview = ui.image().classes("w-48 h-36 object-cover rounded border")
            if current_image:
                self._set_preview(current_image)
            else:
                self._preview.set_source("")
                self._preview.set_visibility(False)

            self._upload = ui.upload(
                label=label,
                auto_upload=True,
                on_upload=self._handle_upload,
                max_file_size=max_size,
            ).props('accept="image/*"').classes("w-48")

    def _handle_upload(self, e: events.UploadEventArguments):
        """Handle file upload event."""
        content = e.content.read()
        filename = e.name

        # Save to project store
        relative_path = save_uploaded_image(self.project_id, filename, content)
        self.current_image = relative_path
        self._set_preview(relative_path)

        if self.on_change:
            self.on_change(relative_path)

    def _set_preview(self, relative_path: str):
        """Update the preview image."""
        if relative_path:
            # Construct URL to serve the image
            url = f"/project-files/{self.project_id}/{relative_path}"
            self._preview.set_source(url)
            self._preview.set_visibility(True)
        else:
            self._preview.set_source("")
            self._preview.set_visibility(False)

    def set_image(self, relative_path: Optional[str]):
        """Programmatically set the current image."""
        self.current_image = relative_path
        self._set_preview(relative_path)
