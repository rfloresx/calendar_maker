"""Reusable mixins for common wx panel behaviors.

This module factors shared methods across multiple GUI panels:
- Scrolled panel items access (`pages`)
- Artwork pages operations (add/load/to_json/clear)
- Deletion from a `ScrolledPanel`
- Image setting convenience
"""

try:
    import lib as __lib  # noqa: F401
except Exception:
    import sys
    from os.path import dirname
    sys.path.append(dirname(dirname(dirname(__file__))))

from typing import List, Tuple
from lib.filemanager import FilesManager
from lib.gui.util import ScrolledPanel


class ScrolledPanelItemsMixin:
    @property
    def pages(self):
        return self._scrolling_panel.Items()


class ArtworkPanelOpsMixin(ScrolledPanelItemsMixin):
    """Shared operations for calendar artwork panels.

    Expects `self._scrolling_panel` and a method
    `create_artwork_panel(id, image, img_size, desc)` implemented by subclasses.
    """

    def create_artwork_panel(self, id: int, image: str, img_size: Tuple[int, int], desc: str):
        raise NotImplementedError()

    def add_artwork(self, id: int, image: str, desc: str, img_size: Tuple[int, int]) -> None:
        if image is not None:
            image = FilesManager.instance().add_file(image)
        panel = self.create_artwork_panel(id, image, img_size, desc)
        self._scrolling_panel.Add(panel)

    def load(self, data: dict) -> None:
        pages = data["pages"]
        items = self._scrolling_panel.Items()
        for i in range(len(pages)):
            items[i].load(pages[i])

    def to_json(self) -> dict:
        data = {"pages": []}
        for page in self._scrolling_panel.Items():
            data["pages"].append(page.to_json())
        return data

    def clear(self) -> None:
        pages = self._scrolling_panel.Items()
        if not pages:
            return
        pages[0].set_description("Cover Page")
        pages[0].set_image(None)
        for i in range(1, len(pages)):
            pages[i].set_description(f"Month {i}")
            pages[i].set_image(None)


class DeleteFromScrolledPanelMixin:
    def on_delete(self, event):
        if self.Parent and isinstance(self.Parent, ScrolledPanel):
            panel: ScrolledPanel = self.Parent
            panel.Remove(self)
            self.Destroy()
            panel.Refresh()


class ImageSetterMixin:
    def set_image(self, filename):
        self._image_ctrl.set_image(filename)
