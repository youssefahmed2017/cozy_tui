"""Cozy Arcade — four screens, and the state that survives moving between them.

A screen is a named set of top-level widgets. This app has four (menu,
settings, game, over) and the whole of its navigation is `app.show(...)`.

What the example is really about is the two things screens give you that
rebuilding a UI on every switch would not:

  • **Widgets keep their state.** Start a game, leave mid-round to change a
    setting, come back — the score, the clock, and the focused widget are all
    exactly where you left them. Nothing is rebuilt, because a screen owns its
    widget list rather than a function that recreates one.

  • **`on_show` / `on_hide` are where the *rest* of the state goes.** Widgets
    take care of themselves; a running timer doesn't. The game screen cancels
    its tick in `on_hide` and restarts it in `on_show`, so wandering off to the
    settings screen pauses the round instead of letting it run out while you
    aren't looking. That pairing is the whole trick: anything the widgets can't
    hold for you, hang off these two.

Notice also that the "over" screen is built once and *refilled* before each
show (`show_over`), not rebuilt — a screen is an ordinary widget list, so
updating one is just assigning to a label.

Run it:

    python examples/screens/screens.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Key, State, Style
from cozy_tui.widgets import Box, Button, Checkbox, Input, Label, VBox

app = App(full=True, title="Cozy Arcade")

ROUND_SECONDS = 15
TICK = 0.1

TITLE = Style(fg="bright_cyan", styles=["bold"])
DIM = Style(fg="bright_black")


# ── shared state ─────────────────────────────────────────────────────────────
# Plain States, so the same value can be read from more than one screen without
# either screen knowing about the other.

score = State(0)
clock = State(float(ROUND_SECONDS))
player = State("player one")

timer = None


def footer_for(screen_name: str, hint: str) -> Label:
    """Every screen gets the same footer shape. `app.current_screen` is printed
    so it's obvious which one you're on while clicking around."""
    return Label(0, 0, f"[{screen_name}]  {hint}", style=DIM)


# ── menu ─────────────────────────────────────────────────────────────────────
# The first screen created adopts whatever the app already holds (nothing here)
# and starts out showing, so no initial app.show() is needed.

menu = app.screen("menu")
menu.dock(Label(0, 0, "COZY ARCADE", style=TITLE), "top", margin=1)
menu.dock(footer_for("menu", "Enter/click a button · Esc quits"), "bottom", margin=1)

menu_buttons = VBox(4, 3, gap=1)
menu_buttons.add(Button(0, 0, "Play", width=14).on_click(lambda _b: start_round()))
menu_buttons.add(
    Button(0, 0, "Settings", width=14).on_click(lambda _b: app.show("settings"))
)
menu_buttons.add(Button(0, 0, "Quit", width=14).on_click(lambda _b: app.quit()))
menu.add(menu_buttons)
menu.focus(menu_buttons.children[0])


# ── settings ─────────────────────────────────────────────────────────────────
# Reachable from the menu *and* mid-game. Its Input keeps whatever you typed
# either way, because the widget itself is never thrown away.

settings = app.screen("settings")
settings.dock(Label(0, 0, "SETTINGS", style=TITLE), "top", margin=1)
settings.dock(
    footer_for("settings", "Esc/Back returns where you came from"), "bottom", margin=1
)

form = Box(2, 2, "440x70", title="Player", border="rounded")
form.add(Label(2, 1, "Name:"))
name_field = Input(9, 1, 22)
name_field.value = player.value
name_field.on_change(lambda text: player.set(text.strip() or "player one"))
form.add(name_field)
form.add(Checkbox(2, 3, "Sound (does nothing, honestly)"))
form.add(Button(2, 5, "Back", width=10).on_click(lambda _b: go_back()))
settings.add(form)
settings.focus(name_field)

# Where "Back" returns to. Set on the way *in*, so settings can be opened from
# the menu or from a paused game and still return to the right place.
_return_to = "menu"


def open_settings() -> None:
    global _return_to
    _return_to = app.current_screen.name
    app.show("settings")


def go_back() -> None:
    app.show(_return_to)


# ── game ─────────────────────────────────────────────────────────────────────

game = app.screen("game")
game.dock(Label(0, 0, "TAP SPACE", style=TITLE), "top", margin=1)
game.dock(
    footer_for("game", "Space scores · S = settings (pauses) · Esc = menu"),
    "bottom",
    margin=1,
)

score_label = Label(4, 2, "")
clock_label = Label(4, 4, "")
player_label = Label(4, 6, "", style=DIM)
for label in (score_label, clock_label, player_label):
    game.add(label)


def refresh(*_args) -> None:
    score_label.text = f"Score: {score.value}"
    clock_label.text = f"Time:  {clock.value:4.1f}s"
    player_label.text = f"playing as {player.value}"


# Both states feed the same redraw, and neither knows about the labels.
score.subscribe(refresh)
clock.subscribe(refresh)
player.subscribe(refresh)


def tick() -> None:
    clock.value = max(0.0, clock.value - TICK)
    if clock.value <= 0:
        show_over()


def start_round() -> None:
    score.value = 0
    clock.value = float(ROUND_SECONDS)
    app.show("game")


def resume(_screen=None) -> None:
    """on_show: restart the clock. Also runs for the first show of a round, so
    there's only one place the timer is ever started."""
    global timer
    refresh()
    if timer is None and clock.value > 0:
        timer = app.every(TICK, tick)


def pause(_screen=None) -> None:
    """on_hide: stop the clock. Without this, wandering into settings would
    quietly run the round out while you weren't looking at it."""
    global timer
    if timer is not None:
        app.cancel(timer)
        timer = None


game.on_show(resume)
game.on_hide(pause)


# ── game over ────────────────────────────────────────────────────────────────
# Built once here and *refilled* before each show — a screen is an ordinary
# widget list, so "updating" one is assigning to a label.

over = app.screen("over")
over.dock(Label(0, 0, "ROUND OVER", style=TITLE), "top", margin=1)
over.dock(footer_for("over", "Enter/click · Esc = menu"), "bottom", margin=1)

result = Label(4, 2, "")
over.add(result)
over_buttons = VBox(4, 4, gap=1)
over_buttons.add(
    Button(0, 0, "Play again", width=14).on_click(lambda _b: start_round())
)
over_buttons.add(Button(0, 0, "Menu", width=14).on_click(lambda _b: app.show("menu")))
over.add(over_buttons)
over.focus(over_buttons.children[0])


def show_over() -> None:
    result.text = f"{player.value} scored {score.value}"
    app.show("over")


# ── keys ─────────────────────────────────────────────────────────────────────


def on_space() -> None:
    # Only means anything on the game screen; every screen shares one key map,
    # so a global handler checks where it is rather than being re-registered.
    if app.current_screen is game and clock.value > 0:
        score.update(lambda n: n + 1)


def on_escape() -> None:
    current = app.current_screen
    if current is menu:
        app.quit()
    elif current is settings:
        go_back()
    else:
        app.show("menu")


app.on_key(Key.SPACE, on_space, description="Score a point", section="Game")
app.on_key("s", lambda: open_settings(), description="Settings", section="Game")
app.on_key(Key.ESC, on_escape, description="Back / quit", section="Actions")

refresh()
app.run()
