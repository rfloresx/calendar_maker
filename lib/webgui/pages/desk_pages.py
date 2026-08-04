"""Desk calendar pages editor — web GUI."""

from nicegui import ui

from lib.webgui.state import ProjectState
from lib.webgui.components.artwork_card import ArtworkCard


def desk_pages_content(state: ProjectState) -> None:
    """Render the desk calendar artwork editor page."""
    cards: list[ArtworkCard] = []

    def on_change():
        """Persist card changes back to project state."""
        pages = [card.to_dict() for card in cards]
        state.desk_pages = {"pages": pages}

    ui.label("Desk Calendar Pages").classes("text-2xl font-bold mb-4")
    ui.separator()

    pages_data = state.desk_pages.get("pages", [])
    # Ensure we have 13 pages (cover + 12 months)
    while len(pages_data) < 13:
        pages_data.append(ProjectState._default_page(len(pages_data)))

    for i in range(13):
        card = ArtworkCard(
            index=i,
            page_data=pages_data[i],
            section="desk_pages",
            year=state.year,
            on_change=on_change,
        )
        cards.append(card)
