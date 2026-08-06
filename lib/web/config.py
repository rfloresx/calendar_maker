"""Application configuration and data path resolution.

The DATA_PATH environment variable controls where all persistent data is stored.
If not set, defaults to the current working directory.
"""

import os
from pathlib import Path

DATA_PATH = Path(os.environ.get("DATA_PATH", ".")).resolve()
PROJECTS_DIR = DATA_PATH / "projects"
CACHE_DIR = DATA_PATH / "cache"
DATABASE_PATH = DATA_PATH / "calendar_maker.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Ensure base directories exist
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_project_dir(project_id: str) -> Path:
    """Return the filesystem directory for a given project, creating it if needed."""
    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


def get_project_images_dir(project_id: str) -> Path:
    """Return the images subdirectory for a project."""
    images_dir = get_project_dir(project_id) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    return images_dir


def get_project_exports_dir(project_id: str) -> Path:
    """Return the exports subdirectory for a project."""
    exports_dir = get_project_dir(project_id) / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    return exports_dir


def get_config_value(key: str, default: str = "") -> str:
    """Get a config value from environment or database.

    Priority: env var > database > default.
    """
    # Check environment first
    env_val = os.environ.get(key, "")
    if env_val:
        return env_val
    # Database lookup done at call site (avoids circular import)
    return default
