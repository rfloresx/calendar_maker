"""File storage abstraction for project images and exports."""

import shutil
import uuid
from pathlib import Path
from typing import Optional

from lib.web.config import get_project_images_dir, get_project_exports_dir, get_project_dir


def save_uploaded_image(project_id: str, filename: str, content: bytes) -> str:
    """Save an uploaded image to the project's images directory.

    Returns the relative path (from project root) to the saved file.
    """
    images_dir = get_project_images_dir(project_id)
    # Avoid filename collisions by prepending a short UUID
    safe_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    dest = images_dir / safe_name
    dest.write_bytes(content)
    return f"images/{safe_name}"


def get_image_absolute_path(project_id: str, relative_path: str) -> Optional[Path]:
    """Resolve a relative image path to its absolute filesystem path."""
    if not relative_path:
        return None
    project_dir = get_project_dir(project_id)
    abs_path = project_dir / relative_path
    if abs_path.exists():
        return abs_path
    return None


def delete_project_files(project_id: str):
    """Delete all files for a project."""
    project_dir = get_project_dir(project_id)
    if project_dir.exists():
        shutil.rmtree(project_dir)


def delete_image(project_id: str, relative_path: str):
    """Delete a specific image from the project store."""
    if not relative_path:
        return
    abs_path = get_image_absolute_path(project_id, relative_path)
    if abs_path and abs_path.exists():
        abs_path.unlink()


def get_exports_dir(project_id: str) -> Path:
    """Return the exports directory for a project, creating it if needed."""
    return get_project_exports_dir(project_id)
