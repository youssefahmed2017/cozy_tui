"""Overlay / modal demo.

Press Enter/Space on "Open dialog" to pop a centered modal over a dimmed
background. While it's open, Tab is confined to the dialog and Esc (or clicking
outside) dismisses it. The base screen keeps its own focus underneath.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style
from cozy_tui.widgets import Box, Button, Label
from cozy_tui.events import Key

app = App(full=True, style=Style(fg="white", bg="black"))

base = Box(2, 1, "600x300", title="Main screen", border="rounded")
base.add(Label(2, 1, "This is the base UI. It dims when a dialog opens."))


def open_dialog(_btn):
    dialog = Box(
        0,
        0,
        "520x180",
        title="Confirm",
        border="rounded",
        style=Style(fg="white", bg="black"),
    )
    dialog.add(Label(2, 1, "Delete everything? This cannot be undone."))
    dialog.add(Button(2, 4, "Cancel").on_click(lambda b: app.close_overlay(dialog)))
    dialog.add(
        Button(14, 4, "Delete", style=Style(fg="white", bg="red")).on_click(
            lambda b: app.close_overlay(dialog)
        )
    )
    # modal + dim + centered; Esc or a click outside also dismisses it.
    app.open_overlay(dialog, close_on_click_outside=True)


base.add(Button(2, 4, "Open dialog").on_click(open_dialog))
app.add(base)
app.focus(base.children[-1])  # the "Open dialog" button

app.on_key(Key.ESC, lambda: "quit")
app.run()
