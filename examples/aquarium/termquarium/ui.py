"""Small reusable UI pieces for TermQuarium."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from cozy_tui import Style
from cozy_tui.widgets import Box, Button, Label

from .dreams import DreamAnimation
from .save import format_relative_time

MAX_CARDS_SHOWN = 4  # keeps the menu on one screen; no scrolling yet


def build_save_menu(
    app,
    cards: list[tuple[Path, dict]],
    on_load: Callable[[Path], None],
    on_rename: Callable[[Path, str, str], None],
    on_duplicate: Callable[[Path, str], None],
    on_delete: Callable[[Path, str], None],
) -> Box:
    """Render the save list from metadata, not simulation widgets -- cheap
    to draw since it never touches a save's full fish/decoration data. Each
    card shows exactly what the user asked for: enough at a glance to know
    which aquarium to load without opening any of them. Rename/Duplicate
    each open their own app.prompt() for a new name (same pattern as the
    Fish Inspector's Rename); Delete opens an app.confirm() first, same
    pattern as Sell -- all three call back into the caller (main()'s
    _open_load_menu()) only once confirmed/submitted, which does the actual
    save.py mutation and refreshes this menu."""
    muted = Style(fg="bright_black")
    box = Box(0, 0, "520x440", title="Load Aquarium", border="rounded", style=app.style)
    if not cards:
        box.add(Label(2, 2, "No saves yet. Press P to create one.", muted))
    y = 2
    for path, meta in cards[:MAX_CARDS_SHOWN]:
        name = str(meta.get("name", path.stem))
        box.add(Label(2, y, name, Style(styles=["bold"])))
        y += 1

        def _rename_prompt(_widget, path=path, name=name):
            app.prompt(
                f"Rename '{name}' to",
                initial=name,
                on_submit=lambda new_name: on_rename(path, name, new_name),
            )

        def _duplicate_prompt(_widget, path=path, name=name):
            app.prompt(
                f"Duplicate '{name}' as",
                initial=f"{name} copy",
                on_submit=lambda new_name: on_duplicate(path, new_name),
            )

        def _delete_confirm(_widget, path=path, name=name):
            app.confirm(
                f"Delete '{name}'? This can't be undone.",
                on_yes=lambda: on_delete(path, name),
            )

        box.add(Button(2, y, "Load").on_click(lambda _widget, path=path: on_load(path)))
        box.add(Button(11, y, "Rename").on_click(_rename_prompt))
        box.add(Button(22, y, "Duplicate").on_click(_duplicate_prompt))
        box.add(Button(36, y, "Delete").on_click(_delete_confirm))
        y += 1
        box.add(Label(2, y, "─" * 30, muted))
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


def build_restore_menu(
    app, cloud_saves: list[dict], on_download: Callable[[str], None]
) -> Box:
    """Cloud Saves' "Restore My Saves" list -- deliberately simpler than
    build_save_menu()'s cards (no rename/duplicate/delete: those already
    exist for local saves once a cloud save is downloaded and shows up in
    the normal Load menu). Each entry is `{"name": ..., "metadata": ...}`
    from cloud.list_cloud_saves(), the same metadata shape write_save()
    already produces locally."""
    muted = Style(fg="bright_black")
    box = Box(
        0, 0, "460x360", title="Restore My Saves", border="rounded", style=app.style
    )
    if not cloud_saves:
        box.add(Label(2, 2, "No cloud saves found for this key.", muted))
    y = 2
    for entry in cloud_saves[:MAX_CARDS_SHOWN]:
        name = entry.get("name", "Untitled Aquarium")
        meta = entry.get("metadata", {})
        box.add(Label(2, y, name, Style(styles=["bold"])))
        y += 1
        box.add(
            Button(2, y, "Download").on_click(lambda _w, name=name: on_download(name))
        )
        y += 1
        played = format_relative_time(meta.get("last_played", ""))
        box.add(
            Label(
                2,
                y,
                f"🐠 {meta.get('fish', 0)} Fish · Day {meta.get('day', 0)} · {played}",
                muted,
            )
        )
        y += 2
    box.add(Button(2, y, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box


def build_achievements_menu(app, achievements: list, unlocked: set[str]) -> Box:
    """A read-only list of every achievement, locked and unlocked alike --
    transparent rather than secret, so the list doubles as a light to-do
    menu of things worth trying. `unlocked` is the shared
    save.load_unlocked_achievements() set; achievements are account-wide,
    not tied to any one save (see save.py), so this looks the same no
    matter which aquarium is currently open."""
    muted = Style(fg="bright_black")
    box = Box(0, 0, "560x460", title="Achievements", border="rounded", style=app.style)
    box.add(
        Label(
            2,
            1,
            f"{len(unlocked)} / {len(achievements)} unlocked",
            Style(fg="bright_cyan", styles=["bold"]),
        )
    )
    y = 3
    for achievement in achievements:
        got = achievement.id in unlocked
        name_style = Style(fg="bright_yellow", styles=["bold"]) if got else muted
        suffix = " ✓" if got else ""
        box.add(
            Label(2, y, f"{achievement.icon} {achievement.name}{suffix}", name_style)
        )
        y += 1
        box.add(Label(4, y, achievement.description, muted))
        y += 2
    box.add(Button(2, y, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box


def build_dream_view(app, f, on_view_stats: Callable[[object], None]) -> Box:
    """The click-through destination for a dreaming fish's 💭 indicator (see
    aquarium.py's _open_dream(), which takes over "click the fish" while a
    dream is active, in place of the normal Fish Inspector) -- purely a
    "watch and smile" view, per the user's own framing: nothing inside the
    animation itself is clickable, it just loops (see dreams.DreamAnimation)
    for as long as this stays open. Below it, a plain-language caption
    (name/title/description) is a clue for a player who can't quite read the
    scene, not a replacement for it -- the animation is still the point.
    "View Stats" is the escape hatch back to the normal Inspector, since a
    dreaming fish would otherwise be unreachable there until it wakes."""
    dream = f.dream
    muted = Style(fg="bright_black")
    box = Box(
        0,
        0,
        "400x260",
        title=f"💭 {f.display_name}'s Dream",
        border="rounded",
        style=app.style,
    )
    anim = DreamAnimation(2, 2, dream, Style(fg="bright_cyan"))
    box.add(anim)
    y = 2 + anim.natural_height(1) + 1
    box.add(Label(2, y, f"{f.display_name} is dreaming about:", muted))
    y += 1
    box.add(Label(2, y, f"{dream.title},", muted))
    y += 1
    box.add(Label(2, y, dream.description, muted))
    y += 2
    box.add(
        Button(2, y, "View Stats").on_click(
            lambda _w: (app.close_overlay(box), on_view_stats(f))
        )
    )
    box.add(Button(16, y, "Close").on_click(lambda _w: app.close_overlay(box)))
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
    on_resume: Callable[[], None] | None = None,
    on_achievements: Callable[[], None] | None = None,
) -> Box:
    """The first screen shown for every session -- and, since Ctrl+C now
    reaches this same menu mid-session too (see aquarium.py's
    _return_to_main_menu()), optionally a way back out of it. `on_resume`
    is only ever passed in that mid-session case; boot's own call leaves
    it None, so there's nothing to resume to and no button appears --
    identical to before this existed."""
    box = Box(0, 0, "360x260", title="TermQuarium", border="rounded", style=app.style)
    box.add(
        Label(
            2,
            2,
            "A cozy aquarium, one fish at a time.",
            Style(fg="bright_cyan", styles=["bold"]),
        )
    )
    y = 5
    if on_resume is not None:
        box.add(Button(2, y, "Resume").on_click(lambda _w: on_resume()))
        y += 2
    box.add(Button(2, y, "New Aquarium").on_click(lambda _w: on_new()))
    box.add(Button(2, y + 2, "Load Save").on_click(lambda _w: on_load()))
    box.add(Button(2, y + 4, "Settings").on_click(lambda _w: on_settings()))
    box.add(Button(2, y + 6, "Help").on_click(lambda _w: on_help()))
    if on_achievements is not None:
        box.add(Button(2, y + 8, "Achievements").on_click(lambda _w: on_achievements()))
    box.add(Button(2, y + 11, "Quit").on_click(lambda _w: app.quit()))
    return box


def build_pause_menu(
    app,
    on_resume: Callable[[], None],
    on_save: Callable[[], None],
    on_settings: Callable[[], None],
    on_help: Callable[[], None],
    on_quit: Callable[[], None],
    on_achievements: Callable[[], None] | None = None,
) -> Box:
    """Esc opens this (see main()) instead of instantly quitting -- the
    game genuinely freezes while it's open (every Fish/BubbleField checks
    the same shared `paused` flag this menu flips), and Quit here asks for
    confirmation first instead of a single accidental keypress destroying
    an unsaved session."""
    box = Box(0, 0, "320x260", title="Paused", border="rounded", style=app.style)
    box.add(
        Label(
            2,
            2,
            "Game paused -- nothing is moving.",
            Style(fg="bright_cyan", styles=["bold"]),
        )
    )
    box.add(Button(2, 5, "Resume").on_click(lambda _w: on_resume()))
    box.add(Button(2, 7, "Save").on_click(lambda _w: on_save()))
    box.add(Button(2, 9, "Settings").on_click(lambda _w: on_settings()))
    box.add(Button(2, 11, "Help").on_click(lambda _w: on_help()))
    if on_achievements is not None:
        box.add(Button(2, 13, "Achievements").on_click(lambda _w: on_achievements()))
    box.add(Button(2, 16, "Quit").on_click(lambda _w: on_quit()))
    return box


_TREE_CANOPY_TOP = "   /\\   "  # 8-char tileable unit -- kept plain ASCII
_TREE_CANOPY_MID = "  /  \\  "  # (not emoji) so Style colors actually apply,
_TREE_TRUNK = "   ||   "  # same convention as PLANT_ART/ROCK_ART/CASTLE_ART.


def _tile(unit: str, width: int) -> str:
    reps = width // len(unit) + 2
    return (unit * reps)[:width]


def build_forest_scene(
    app, on_leave, paused=lambda: False
) -> tuple[list, Label, tuple[float, float, float, float]]:
    """The Forest biome's own full-screen scene (Exploration Update Slice 1)
    -- the *static* part only (title, a money-readout label, background
    scenery, the Leave button), built once at boot. The live Fish/Wood
    objects currently in this biome are appended/removed straight onto
    this same persistent list over time by aquarium.py's _check_foraging()
    (which fish/wood currently exist changes on its own timers, regardless
    of whether this scene happens to be the one currently shown -- see
    constants.py's Exploration Update comment), so nothing here needs
    rebuilding just to reflect that.

    Returns `(widgets, stats_label, bounds)` -- the caller keeps the label
    reference to refresh its money readout each time the scene is entered
    (nothing in the Forest changes it while shown, so a live per-tick
    refresh isn't needed the way the tank's own stats label has one).
    `bounds` (x0, y0, x1, y1) is where fish/wood should be positioned --
    sized from the *actual* terminal (app.cols/app.rows), the same way the
    tank's own `bounds` is derived in aquarium.py, rather than a fixed
    constant a small terminal could clip.

    This whole scene is meant to be swapped wholesale into `app.widgets`
    (see aquarium.py's `_enter_forest()`) -- deliberately NOT a modal/
    overlay. Clicking a fish here still opens the same Fish Inspector as
    in the tank (the Forest isn't read-only). A `LeafField` (ambient
    falling leaves, mirrors the tank's own `BubbleField`) is included in
    the static scenery -- `paused` is the same zero-arg-callable shared-
    mutable pattern the tank's Pause menu already uses."""
    from .constants import FOREST_HEIGHT, FOREST_WIDTH
    from .leaves import LeafField

    forest_w = min(FOREST_WIDTH, max(20, app.cols - 6))
    forest_h = min(FOREST_HEIGHT, max(10, app.rows - 8))

    stats_label = Label(2, 1, "", Style(fg="bright_white"))
    widgets: list = [
        Label(
            2,
            0,
            "The Forest -- click a fish to inspect it, or Leave to go back",
            Style(fg="bright_cyan", styles=["bold"]),
        ),
        stats_label,
    ]
    canopy_top_y, canopy_mid_y, trunk_y = 3, 4, 5
    ground_y = forest_h - 3
    leave_y = forest_h - 1
    widgets.append(
        Label(
            2, canopy_top_y, _tile(_TREE_CANOPY_TOP, forest_w), Style(fg="bright_green")
        )
    )
    widgets.append(
        Label(2, canopy_mid_y, _tile(_TREE_CANOPY_MID, forest_w), Style(fg="green"))
    )
    widgets.append(Label(2, trunk_y, _tile(_TREE_TRUNK, forest_w), Style(fg="yellow")))
    widgets.append(Label(2, ground_y, "_" * forest_w, Style(fg="green")))
    widgets.append(
        LeafField(
            (2.0, float(canopy_top_y), float(2 + forest_w), float(ground_y)), paused
        )
    )
    widgets.append(Button(2, leave_y, "Leave Forest").on_click(lambda _w: on_leave()))

    fy_low = float(trunk_y + 1)
    fy_high = max(fy_low + 1.0, float(ground_y - 1))
    bounds = (4.0, fy_low, forest_w - 4.0, fy_high)
    return widgets, stats_label, bounds
