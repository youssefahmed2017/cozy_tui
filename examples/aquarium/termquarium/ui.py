"""Small reusable UI pieces for TermQuarium."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from cozy_tui import Style
from cozy_tui.widgets import Box, Button, Label

from .save import format_relative_time

MAX_CARDS_SHOWN = 4  # keeps the menu on one screen; no scrolling yet


def build_save_menu(
    app, cards: list[tuple[Path, dict]], on_load: Callable[[Path], None]
) -> Box:
    """Render the save list from metadata, not simulation widgets -- cheap
    to draw since it never touches a save's full fish/decoration data. Each
    card shows exactly what the user asked for: enough at a glance to know
    which aquarium to load without opening any of them."""
    muted = Style(fg="bright_black")
    box = Box(0, 0, "460x360", title="Load Aquarium", border="rounded", style=app.style)
    if not cards:
        box.add(Label(2, 2, "No saves yet. Press P to create one.", muted))
    y = 2
    for path, meta in cards[:MAX_CARDS_SHOWN]:
        box.add(Label(2, y, str(meta.get("name", path.stem)), Style(styles=["bold"])))
        box.add(
            Button(34, y, "Load").on_click(lambda _widget, path=path: on_load(path))
        )
        y += 1
        box.add(Label(2, y, "─" * 24, muted))
        y += 1
        box.add(Label(2, y, f"🐠 {meta.get('fish', 0)} Fish"))
        y += 1
        box.add(Label(2, y, f"💰 ${meta.get('money', 0)}"))
        y += 1
        box.add(Label(2, y, f"🍽️ {meta.get('food', 0)} Food"))
        y += 1
        box.add(Label(2, y, f"📅 Day {meta.get('day', 0)}"))
        y += 1
        played = format_relative_time(meta.get("last_played", ""))
        box.add(Label(2, y, f"🕒 Played {played}", muted))
        y += 2
    box.add(Button(2, y, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box


def build_help_menu(app) -> Box:
    """A compact in-game controls reference, reachable from the start menu."""
    muted = Style(fg="bright_black")
    box = Box(0, 0, "500x270", title="How to Play", border="rounded", style=app.style)
    lines = [
        "Click open water to drop food for your fish.",
        "Click a fish or decoration to inspect it.",
        "S  Shop       G  Settings       P  Save       L  Load",
        "Fish grow, make friends or rivals, and may have babies.",
        "Keep food stocked: starving fish lose health over time.",
        "Daily visitors and maintenance grants keep the aquarium going.",
    ]
    for row, line in enumerate(lines, start=2):
        box.add(Label(2, row, line, muted if row not in (2, 4) else None))
    box.add(Button(2, 10, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box


def build_start_menu(
    app,
    on_new: Callable[[], None],
    on_load: Callable[[], None],
    on_settings: Callable[[], None],
    on_help: Callable[[], None],
) -> Box:
    """The first screen shown for every session."""
    box = Box(0, 0, "360x260", title="TermQuarium", border="rounded", style=app.style)
    box.add(
        Label(
            2,
            2,
            "A cozy aquarium, one fish at a time.",
            Style(fg="bright_cyan", styles=["bold"]),
        )
    )
    box.add(Button(2, 5, "New Aquarium").on_click(lambda _w: on_new()))
    box.add(Button(2, 7, "Load Save").on_click(lambda _w: on_load()))
    box.add(Button(2, 9, "Settings").on_click(lambda _w: on_settings()))
    box.add(Button(2, 11, "Help").on_click(lambda _w: on_help()))
    box.add(Button(2, 14, "Quit").on_click(lambda _w: app.quit()))
    return box
