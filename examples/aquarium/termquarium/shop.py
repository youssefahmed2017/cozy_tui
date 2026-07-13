"""The Fish Shop overlay and its purchase wiring."""

from cozy_tui import Style
from cozy_tui.widgets import Box, Button, Label

from .constants import (
    DECORATION_SHOP_ITEMS,
    FOOD_PACK_PRICE,
    FOOD_PACK_SIZE,
    SHOP_ITEMS,
)


def build_shop(app, state, buy_fish, buy_food, buy_decoration) -> Box:
    box = Box(0, 0, "480x340", title="Fish Shop", border="rounded", style=app.style)
    money_label = Label(2, 1, "", Style(fg="bright_white", styles=["bold"]))
    box.add(money_label)

    def refresh():
        money_label.text = f"Money: ${state['money']}"

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
    for species in SHOP_ITEMS:
        tag = " (predator!)" if species.predator else ""
        box.add(
            Label(
                2,
                row,
                f"{species.name:<10} {species.right}   ${species.price}{tag}",
                Style(fg=species.color),
            )
        )
        box.add(
            Button(32, row, "Buy").on_click(
                lambda _w, species=species: purchase(
                    species.price, lambda: buy_fish(species)
                )
            )
        )
        row += 2
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
    box.add(Button(2, row, "Close").on_click(lambda _w: app.close_overlay(box)))
    refresh()
    return box
