"""Project state management for the web GUI.

Provides a ProjectState class that holds the in-memory representation of
a calendar project. Serializes to/from the same Project.json format used
by the desktop GUI so projects are interchangeable.
"""

import copy
import json
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProjectState:
    """Holds the current project state in memory.

    Manages load/save of Project.json and tracks unsaved changes.
    """

    def __init__(self):
        self._project_path: Optional[Path] = None
        self._artworks: Dict[str, Any] = self._default_artworks()
        self._desk_pages: Dict[str, Any] = self._default_artworks()
        self._birthdays: Dict[str, Any] = {"birthdays": []}
        self._photo_labels: Dict[str, Any] = {"photos": []}
        self._settings: Dict[str, Any] = {
            "year": datetime.datetime.now().year,
            "export": {
                "calendar_type": "wall",
                "format": "png",
                "exporter_name": "default",
                "options": {},
            },
        }
        self._last_saved: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def project_path(self) -> Optional[Path]:
        return self._project_path

    @project_path.setter
    def project_path(self, value: Optional[Path]):
        self._project_path = Path(value) if value else None

    @property
    def year(self) -> int:
        return self._settings.get("year", datetime.datetime.now().year)

    @year.setter
    def year(self, value: int):
        self._settings["year"] = int(value)

    @property
    def artworks(self) -> Dict[str, Any]:
        return self._artworks

    @artworks.setter
    def artworks(self, value: Dict[str, Any]):
        self._artworks = value

    @property
    def desk_pages(self) -> Dict[str, Any]:
        return self._desk_pages

    @desk_pages.setter
    def desk_pages(self, value: Dict[str, Any]):
        self._desk_pages = value

    @property
    def birthdays(self) -> Dict[str, Any]:
        return self._birthdays

    @birthdays.setter
    def birthdays(self, value: Dict[str, Any]):
        self._birthdays = value

    @property
    def photo_labels(self) -> Dict[str, Any]:
        return self._photo_labels

    @photo_labels.setter
    def photo_labels(self, value: Dict[str, Any]):
        self._photo_labels = value

    @property
    def settings(self) -> Dict[str, Any]:
        return self._settings

    @settings.setter
    def settings(self, value: Dict[str, Any]):
        self._settings = value

    @property
    def has_unsaved_changes(self) -> bool:
        if self._last_saved is None:
            return False
        return self._last_saved != self.to_json()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_json(self) -> Dict[str, Any]:
        """Serialize the full project state to a dict (same format as desktop GUI)."""
        data: Dict[str, Any] = {}
        data["project"] = str(self._project_path) if self._project_path else ""
        data["artworks"] = self._artworks
        data["desk_pages"] = self._desk_pages
        data["birthdays"] = self._birthdays
        data["photo_labels"] = self._photo_labels
        data["settings"] = self._settings
        return data

    def from_json(self, data: Dict[str, Any]) -> None:
        """Load project state from a dict (same format as desktop GUI)."""
        self._project_path = Path(data["project"]) if data.get("project") else None
        self._artworks = data.get("artworks", self._default_artworks())
        self._desk_pages = data.get("desk_pages", self._default_artworks())
        self._birthdays = data.get("birthdays", {"birthdays": []})
        self._photo_labels = data.get("photo_labels", {"photos": []})
        self._settings = data.get("settings", {})
        # Ensure setting defaults
        self._settings.setdefault("year", datetime.datetime.now().year)
        export = self._settings.setdefault("export", {})
        export.setdefault("calendar_type", "wall")
        export.setdefault("format", "png")
        export.setdefault("exporter_name", "default")
        export.setdefault("options", {})
        self._last_saved = copy.deepcopy(self.to_json())

    def load(self, path: Path) -> None:
        """Load a Project.json from disk."""
        path = Path(path)
        with open(path, "r") as f:
            data = json.load(f)
        data["project"] = str(path.parent)
        self.from_json(data)

    def save(self) -> None:
        """Save the current state to Project.json inside project_path."""
        if not self._project_path:
            return
        self._project_path.mkdir(parents=True, exist_ok=True)
        out_path = self._project_path / "Project.json"
        data = self.to_json()
        with open(out_path, "w") as f:
            json.dump(data, f, indent=4)
        self._last_saved = copy.deepcopy(data)

    def new_project(self, path: Path) -> None:
        """Initialize a fresh project at the given directory."""
        self._project_path = Path(path)
        self._project_path.mkdir(parents=True, exist_ok=True)
        self._artworks = self._default_artworks()
        self._desk_pages = self._default_artworks()
        self._birthdays = {"birthdays": []}
        self._photo_labels = {"photos": []}
        self._settings = {
            "year": datetime.datetime.now().year,
            "export": {
                "calendar_type": "wall",
                "format": "png",
                "exporter_name": "default",
                "options": {},
            },
        }
        self._last_saved = None

    # ------------------------------------------------------------------
    # Artwork helpers
    # ------------------------------------------------------------------

    def get_artwork_page(self, section: str, index: int) -> Dict[str, Any]:
        """Get a single artwork page dict by section ('artworks' or 'desk_pages') and index."""
        source = self._artworks if section == "artworks" else self._desk_pages
        pages = source.get("pages", [])
        if 0 <= index < len(pages):
            return pages[index]
        return self._default_page(index)

    def set_artwork_page(self, section: str, index: int, data: Dict[str, Any]) -> None:
        """Update a single artwork page dict."""
        source = self._artworks if section == "artworks" else self._desk_pages
        pages = source.setdefault("pages", [])
        # Extend if needed
        while len(pages) <= index:
            pages.append(self._default_page(len(pages)))
        pages[index] = data

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_artworks() -> Dict[str, Any]:
        """Return default artworks structure with 13 empty pages."""
        pages: List[Dict[str, Any]] = []
        for i in range(13):
            pages.append(ProjectState._default_page(i))
        return {"pages": pages}

    @staticmethod
    def _default_page(index: int) -> Dict[str, Any]:
        if index == 0:
            desc = "Cover Page"
        else:
            desc = f"Month {index}"
        return {
            "image": None,
            "description": desc,
            "selected_place_index": 0,
            "place_overrides": {},
        }
