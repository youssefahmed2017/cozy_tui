"""The Fish Shop overlay and its purchase wiring."""

from cozy_tui import Style
from cozy_tui.widgets import Box, Button, Label, ScrollView

from .constants import (
    DECORATION_SHOP_ITEMS,
    FOOD_PACK_PRICE,
    FOOD_PACK_SIZE,
    FOREST_UNLOCK_PRICE,
    SHOP_ITEMS,
    TREAT_SHOP_ITEMS,
)


def build_shop(
    app, state, buy_fish, buy_food, buy_decoration, buy_treat, unlock_forest
) -> Box:
    box = Box(0, 0, "480x440", title="Fish Shop", border="rounded", style=app.style)
    money_label = Label(2, 1, "", Style(fg="bright_white", styles=["bold"]))
    box.add(money_label)
    treat_labels = {}  # kind -> Label, so refresh() can update stock counts too

    def refresh():
        money_label.text = f"Money: ${state['money']}"
        stock = state.get("treats", {})
        for kind, label in treat_labels.items():
            label.text = f"(have {stock.get(kind, 0)})"

    def purchase(price, callback):
        if state["money"] < price:
            app.toast("Not enough money!", level="error")
            return
        state["money"] -= price
        callback()
        refresh()

    row = 3
    box.add(
        Label(
            2,
            row,
            f"{'Fish Food':<10} x{FOOD_PACK_SIZE:<6} ${FOOD_PACK_PRICE}",
            Style(fg="yellow"),
        )
    )
    box.add(
        Button(32, row, "Buy").on_click(lambda _w: purchase(FOOD_PACK_PRICE, buy_food))
    )
    row += 2
    out_of_stock = state.get("shop_out_of_stock", [])
    # More Fish (updates.md): the species roster grew past what a fixed-
    # height Box can show all at once -- species get their own scrollable
    # region (mouse wheel / arrows / PageUp-Down while focused, same as
    # Log's use of ScrollView) instead of pushing every row below them
    # (decorations, treats, Forest unlock, Close) off the visible panel.
    species_view_rows = 6  # visible at once, matching roughly what fit before
    species_view = ScrollView(
        2, row, f"440x{species_view_rows * 10}", autoscroll=False, style=app.style
    )
    box.add(species_view)
    srow = 0
    for species in SHOP_ITEMS:
        if species.name in out_of_stock:
            # Shop update (updates.md): "Today's Stock" rotates daily
            # (see aquarium.py's _refresh_shop_stock()) -- no Buy button at
            # all while sold out, rather than a disabled one, so there's
            # nothing to click and immediately bounce off of.
            species_view.add(
                Label(
                    0,
                    srow,
                    f"{species.name:<10} Out of Stock",
                    Style(fg="bright_black"),
                )
            )
            srow += 2
            continue
        tag = " (predator!)" if species.predator else ""
        species_view.add(
            Label(
                0,
                srow,
                f"{species.name:<10} {species.right}   ${species.price} "
                f"({species.rarity}){tag}",
                Style(fg=species.color),
            )
        )
        species_view.add(
            Button(34, srow, "Buy").on_click(
                lambda _w, species=species: purchase(
                    species.price, lambda: buy_fish(species)
                )
            )
        )
        srow += 2
    row += species_view_rows + 1
    for item in DECORATION_SHOP_ITEMS:
        box.add(
            Label(
                2,
                row,
                f"{item.kind:<10} (decoration)   ${item.price}",
                Style(fg="white"),
            )
        )
        box.add(
            Button(32, row, "Buy").on_click(
                lambda _w, item=item: purchase(item.price, lambda: buy_decoration(item))
            )
        )
        row += 2
    for item in TREAT_SHOP_ITEMS:
        box.add(
            Label(
                2,
                row,
                f"{item.emoji} {item.kind:<14} x{item.pack_size:<3} ${item.price}",
                Style(fg="white"),
            )
        )
        stock_label = Label(32, row, "", Style(fg="bright_black"))
        box.add(stock_label)
        treat_labels[item.kind] = stock_label
        box.add(
            Button(44, row, "Buy").on_click(
                lambda _w, item=item: purchase(item.price, lambda: buy_treat(item))
            )
        )
        row += 2
    if not state.get("forest_unlocked"):
        # A one-time, whole-tank unlock (Exploration Update Slice 1) --
        # this row simply disappears once bought, since there's nothing
        # left to buy here again. Uses the exact same purchase() gate as
        # everything else in this Shop.
        box.add(Label(2, row, "Unlock Forest (one-time)", Style(fg="bright_green")))
        box.add(
            Button(32, row, "Buy").on_click(
                lambda _w: purchase(FOREST_UNLOCK_PRICE, unlock_forest)
            )
        )
        row += 2
    box.add(Button(2, row, "Close").on_click(lambda _w: app.close_overlay(box)))
    refresh()
    return box
