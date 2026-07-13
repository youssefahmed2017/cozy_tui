"""Fish/Decoration inspector panels, the Daily Summary, and Settings --
small Box-building functions with no shared state between them."""

from cozy_tui import Style
from cozy_tui.widgets import Box, Button, Checkbox, Label

from .fish import Fish
from .styles import HEART_STYLE, MUTED
from .tank_objects import Decoration


def _build_inspector(app, f: Fish, on_rename, on_sell) -> Box:
    """A read-only stat card for one Fish (name/species/age+growth/health/
    hunger/personality/favorite spot/sell value) with Rename and Sell
    buttons. A snapshot at open-time, not live-refreshing -- matching the
    Shop's own money label, which likewise only updates on explicit actions.
    Sell asks for confirmation first (app.confirm(), stacked on top of this
    modal exactly like Rename's prompt already does) since it's the one
    irreversible action here."""
    spot = (
        f.favorite_decoration.kind if f.favorite_decoration is not None else "none yet"
    )
    box = Box(0, 0, "360x300", title=f.display_name, border="rounded", style=app.style)
    box.add(Label(2, 1, f"Species: {f.species_name}"))
    box.add(Label(2, 2, f"Age: {f.age_days:.1f} days ({f.growth_stage})"))
    box.add(Label(2, 3, f"Health: {f.health:.0f}%"))
    box.add(Label(2, 4, f"Hunger: {f.hunger:.0f}%"))
    box.add(Label(2, 5, f"Personality: {f.personality}"))
    box.add(Label(2, 6, f"Favorite spot: {spot}"))
    if f.friend is not None:
        box.add(Label(2, 7, f"Friend: {f.friend.display_name} ❤", HEART_STYLE))
    if f.rival is not None:
        box.add(
            Label(
                2,
                8,
                f"Rival: {f.rival.display_name} \U0001f620",
                Style(fg="bright_red"),
            )
        )
    box.add(Label(2, 9, f"Sell value: ${f.sell_value}"))

    def _on_sell(_widget):
        app.confirm(
            f"Sell {f.display_name} for ${f.sell_value}?",
            on_yes=lambda: (on_sell(f), app.close_overlay(box)),
        )

    box.add(Button(2, 11, "Rename").on_click(lambda _w: on_rename(f)))
    box.add(Button(14, 11, "Sell").on_click(_on_sell))
    box.add(Button(24, 11, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box


def _build_decoration_inspector(app, d: Decoration, on_sell) -> Box:
    """Decorations are sellable too -- an emergency option (per the user's
    own framing: "instead of game over, I guess the castle has to go...")
    rather than just cosmetic. Sell asks for confirmation first, same
    pattern as the Fish Inspector's Sell button."""
    box = Box(0, 0, "300x160", title=d.kind, border="rounded", style=app.style)
    box.add(Label(2, 1, f"Sell value: ${d.sell_value}"))

    def _on_sell(_widget):
        app.confirm(
            f"Sell this {d.kind} for ${d.sell_value}?",
            on_yes=lambda: (on_sell(d), app.close_overlay(box)),
        )

    box.add(Button(2, 3, "Sell").on_click(_on_sell))
    box.add(Button(12, 3, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box


def _build_daily_summary(
    style,
    day: int,
    visitors: int,
    ticket_sales: int,
    donations: int,
    grant: int,
    food_expense: int,
    net: int,
) -> Box:
    """The end-of-day report -- non-modal and auto-dismissing (see main()),
    since it's a periodic ceremony, not something that should interrupt
    whatever the player's doing every couple of minutes."""
    green, red = Style(fg="bright_green"), Style(fg="bright_red")
    box = Box(0, 0, "380x220", title=f"Day {day}", border="rounded", style=style)
    box.add(Label(2, 1, f"Visitors: {visitors}"))
    box.add(Label(2, 2, f"Ticket Sales: +${ticket_sales}", green))
    box.add(Label(2, 3, f"Donations: +${donations}", green))
    box.add(Label(2, 4, f"Maintenance Grant: +${grant}", green))
    box.add(Label(2, 5, f"Food Expenses: -${food_expense}", red))
    sign = (
        "+" if net >= 0 else "-"
    )  # goes before the $, not net's own minus (avoids "$-20")
    box.add(
        Label(
            2,
            7,
            f"Net Profit: {sign}${abs(net)}",
            Style(fg=green.fg if net >= 0 else red.fg, styles=["bold"]),
        )
    )
    return box


def _build_settings(app, state) -> Box:
    """Gameplay (Emergency Aquarium Welfare) and Display (ambient bubbles)
    toggles. Checked state lives directly in `state`, the same dict
    everything else in this economy reads/writes."""
    box = Box(0, 0, "420x240", title="Settings", border="rounded", style=app.style)
    box.add(Label(2, 1, "Gameplay", Style(styles=["bold"])))

    welfare_cb = Checkbox(
        2, 3, "Emergency Aquarium Welfare", checked=state.get("welfare_enabled", True)
    )
    welfare_cb.on_change(lambda checked: state.update(welfare_enabled=checked))
    box.add(welfare_cb)

    box.add(Label(2, 5, "If enabled, a bankrupt tank (no money, no food,", MUTED))
    box.add(Label(2, 6, "no fish) gets a small fresh start instead of", MUTED))
    box.add(Label(2, 7, "staying empty forever. Turn it off for hardcore mode.", MUTED))

    box.add(Label(2, 9, "Display", Style(styles=["bold"])))

    bubbles_cb = Checkbox(
        2, 11, "Ambient Bubbles", checked=state.get("bubbles_enabled", True)
    )
    bubbles_cb.on_change(lambda checked: state.update(bubbles_enabled=checked))
    box.add(bubbles_cb)

    box.add(Label(2, 13, "Purely cosmetic rising bubbles. Turn off if you", MUTED))
    box.add(Label(2, 14, "find them distracting.", MUTED))

    box.add(Button(2, 16, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box
