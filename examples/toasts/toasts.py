"""Toasts & Spinner — transient notifications and an activity indicator.

The bottom row of buttons raises info / success / warning / error toasts (they
stack in the corner and auto-dismiss). "Load data" shows a Spinner while a
background ``run_worker`` runs, then fires a success toast when it finishes —
the idiomatic async-feedback loop.

    python examples/toasts/toasts.py

Tab moves focus, Enter/Space activates, Esc quits.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.widgets import Box, Button, Label, Spinner

ACCENT = Style(fg="bright_cyan")
MUTED = Style(fg="bright_black")


def main():
    app = App(full=True, style=Style(fg="white", bg="rgb(24,26,32)"), title="Toasts")

    box = Box(2, 1, "620x180", title="Toasts & Spinner", border="rounded",
              style=Style(fg="white", bg="rgb(24,26,32)"))
    box.add(Label(2, 1, "Raise a notification — they stack and fade on a timer:", ACCENT))

    box.add(Button(2, 3, "Info").on_click(
        lambda b: app.toast("Heads up — just so you know.", level="info")))
    box.add(Button(11, 3, "Success").on_click(
        lambda b: app.toast("Saved successfully.", level="success")))
    box.add(Button(23, 3, "Warning").on_click(
        lambda b: app.toast("Low disk space.", level="warning")))
    box.add(Button(35, 3, "Error").on_click(
        lambda b: app.toast("Upload failed.", level="error")))

    box.add(Label(2, 6, "Background work with a spinner:", ACCENT))
    spinner = Spinner(2, 8, label="Loading data…")
    state = {"busy": False}

    def load(_b):
        if state["busy"]:
            return
        state["busy"] = True
        box.add(spinner)  # appears and animates while the worker runs

        def work():
            time.sleep(1.5)  # pretend to fetch something
            return 42

        def done(result):
            state["busy"] = False
            if spinner in box.children:
                box.children.remove(spinner)
            app.toast(f"Loaded {result} rows.", level="success")

        app.run_worker(work, on_result=done)

    box.add(Button(2, 10, "Load data").on_click(load))

    app.add(box)
    app.focus(box)
    app.on_key(Key.ESC, lambda: "quit")
    app.run()


if __name__ == "__main__":
    main()
