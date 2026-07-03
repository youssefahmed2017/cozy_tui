"""Dock layout demo — header, sidebar, status bar, and a filled main area.

Each dock consumes a band from the remaining screen rectangle, in the order
the docks are added; `"fill"` claims whatever is left. Resize your terminal
and the whole layout re-flows.

    +----------------------------------+
    | Header                           |
    +------+---------------------------+
    | Side | Main (fill)               |
    | Bar  |                           |
    +------+---------------------------+
    | Status                           |
    +----------------------------------+
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style
from cozy_tui.widgets import Box, Label, ListItem, ListView
from cozy_tui.events import Key

app = App(full=True, style=Style(fg="white", bg="black"))

# Sizes below are starting hints. Docking overrides the stretched axis:
#   top/bottom  -> full remaining width, keep own height
#   left/right  -> full remaining height, keep own width
#   fill        -> the entire leftover rectangle
header = Box(
    0,
    0,
    "10x10",
    title="Header",
    border="rounded",
    style=Style(fg="bright_white", bg="black"),
    focusable=True,
)
header.add(Label(1, 1, "cozy_tui — dock layout demo   (Tab to move, Esc to quit)"))

status = Box(
    0,
    0,
    "10x10",
    title="Status",
    border="rounded",
    style=Style(fg="bright_black", bg="black"),
    focusable=True,
)
status_label = Label(1, 1, "Ready.")
status.add(status_label)

sidebar = Box(
    0,
    0,
    "180x10",
    title="Menu",
    border="rounded",
    style=Style(fg="white", bg="black"),
    focusable=True,
)
menu = ListView(
    1,
    1,
    [
        ListItem("Dashboard", "dashboard"),
        ListItem("Reports", "reports"),
        ListItem("Settings", "settings"),
        ListItem("About", "about"),
    ],
)
menu.on_change(lambda v: setattr(status_label, "text", f"Hovering: {v}"))
menu.on_select(lambda v: setattr(status_label, "text", f"Opened: {v}"))
sidebar.add(menu)

main = Box(
    0,
    0,
    "10x10",
    title="Main",
    border="rounded",
    style=Style(fg="white", bg="black"),
    focusable=True,
)
main.add(Label(1, 1, 'This box is docked "fill" — it takes whatever'))
main.add(Label(1, 2, "space the other docks leave behind, and grows"))
main.add(Label(1, 3, "or shrinks as you resize the terminal."))

# Order matters: header/status carve off top and bottom first, so the sidebar's
# left band spans only the space between them, and main fills the rest.
app.dock(header, "top")
app.dock(status, "bottom")
app.dock(sidebar, "left")
app.dock(main, "fill")

app.focus(menu)
app.on_key(Key.ESC, lambda: "quit")
app.run()
