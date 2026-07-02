"""Command Palette — a VS Code / Spotlight style fuzzy command launcher.

Press `p` (or click the button) to open a modal palette. Type to fuzzy-filter,
Up/Down to move, Enter or click to run, Esc to dismiss. Shows off:
  * the overlay layer (a centered, dimmed modal),
  * a custom Widget that owns its own text buffer + filtered list,
  * background work via app.run_worker (the "Fetch data" command).
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from random import randint

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Box, Button, Label, Style
from cozy_tui.events import Key
from cozy_tui.widget import Widget

PANEL = Style(fg="white", bg="black")
BORDER = Style(fg="bright_cyan", bg="black", styles=["bold"])
SELECTED = Style(fg="black", bg="bright_cyan", styles=["bold"])
DIM = Style(fg="bright_black", bg="black")


def _fuzzy_score(text: str, query: str):
    """Return a score if every query char appears in order in text, else None.
    Lower is better; contiguous / early matches score best."""
    if not query:
        return 0
    ti = 0
    score = 0
    last = -1
    for qc in query:
        found = text.find(qc, ti)
        if found == -1:
            return None
        score += found - last - 1  # gaps between matched chars
        last = found
        ti = found + 1
    return score + last  # prefer matches that finish earlier


class Palette(Widget):
    """Self-contained: draws its own bordered panel, search line, and results."""

    focusable = True

    def __init__(self, commands, on_run, *, width=52, rows=8):
        super().__init__(0, 0, PANEL)
        self._commands = commands            # list of (label, action)
        self._on_run = on_run
        self.width = width
        self.rows = rows
        self.query = ""
        self.sel = 0
        self._filtered = list(commands)

    def _refilter(self):
        q = self.query.lower()
        if not q:
            self._filtered = list(self._commands)
        else:
            scored = []
            for label, action in self._commands:
                s = _fuzzy_score(label.lower(), q)
                if s is not None:
                    scored.append((s, len(label), label, action))
            scored.sort()
            self._filtered = [(lbl, act) for _, _, lbl, act in scored]
        self.sel = 0

    # ── Widget interface ──────────────────────────────────────────────────────

    def natural_width(self, scale):
        return self.width + 2

    def natural_height(self, scale):
        return self.rows + 4  # border(2) + search(1) + separator(1) + rows

    def contains(self, col, row):
        return (
            self.abs_x <= col < self.abs_x + self.natural_width(1)
            and self.abs_y <= row < self.abs_y + self.natural_height(1)
        )

    def on_key(self, key):
        if key == Key.UP:
            self.sel = max(0, self.sel - 1)
        elif key == Key.DOWN:
            self.sel = min(max(0, len(self._filtered) - 1), self.sel + 1)
        elif key == Key.ENTER:
            self._run()
        elif key == Key.BACKSPACE:
            self.query = self.query[:-1]
            self._refilter()
        elif isinstance(key, str) and len(key) == 1 and key.isprintable():
            self.query += key
            self._refilter()

    def on_mouse_click(self, col=None, row=None):
        if row is None:
            return
        idx = row - (self.abs_y + 3)  # first result row
        if 0 <= idx < len(self._filtered[: self.rows]):
            self.sel = idx
            self._run()

    def _run(self):
        if self._filtered:
            label, action = self._filtered[self.sel]
            self._on_run(label, action)

    def draw(self, canvas):
        x, y, w = self.abs_x, self.abs_y, self.width
        h = self.natural_height(1)
        canvas.write(x, y, "╭" + "─" * w + "╮", BORDER)
        canvas.write(x, y + h - 1, "╰" + "─" * w + "╯", BORDER)
        for i in range(h - 2):
            canvas.write(x, y + 1 + i, "│", BORDER)
            canvas.write(x + 1, y + 1 + i, " " * w, PANEL)
            canvas.write(x + w + 1, y + 1 + i, "│", BORDER)

        # search line
        prompt = "> " + self.query
        prompt = prompt[-(w - 2):] if len(prompt) > w - 2 else prompt
        canvas.write(x + 1, y + 1, (" " + prompt + "▏").ljust(w)[:w], PANEL)
        # separator
        canvas.write(x + 1, y + 2, " " + "─" * (w - 2) + " ", DIM)

        # results
        visible = self._filtered[: self.rows]
        if not visible:
            canvas.write(x + 1, y + 3, "   no matching commands".ljust(w)[:w], DIM)
            return
        for i, (label, _action) in enumerate(visible):
            selected = i == self.sel
            marker = " ❯ " if selected else "   "
            text = (marker + label).ljust(w)[:w]
            canvas.write(x + 1, y + 3 + i, text, SELECTED if selected else PANEL)


def main():
    app = App(full=True, style=Style(fg="white", bg="black"))

    title = Label(2, 1, "cozy_tui — Command Palette demo", Style(fg="bright_cyan", styles=["bold"]))
    hint = Label(2, 3, "Press  p  or click the button below. Then type to fuzzy-search.")
    status = Label(2, 7, "Ready.", Style(fg="bright_green"))
    open_btn = Button(2, 5, "Open palette")

    def set_status(msg, color="bright_green"):
        status.text = msg
        status.style = Style(fg=color)

    def fetch_data():
        time.sleep(1.5)  # pretend to hit the network — UI stays responsive
        return randint(100, 999)

    commands = [
        ("Say hello", lambda: set_status("Hello there! 👋")),
        ("Insert timestamp", lambda: set_status(datetime.now().strftime("%H:%M:%S"))),
        ("Roll a die", lambda: set_status(f"You rolled a {randint(1, 6)} 🎲", "bright_yellow")),
        ("Paint status red", lambda: set_status("Status is red now.", "bright_red")),
        ("Paint status cyan", lambda: set_status("Status is cyan now.", "bright_cyan")),
        ("Fetch data (background)", lambda: (
            set_status("Fetching… (UI stays responsive)", "bright_yellow"),
            app.run_worker(fetch_data, on_result=lambda n: set_status(f"Fetched value: {n}")),
        )),
        ("Clear status", lambda: set_status("")),
        ("Quit", app.quit),
    ]

    def open_palette(*_):
        palette = Palette(commands, run_command)
        app.open_overlay(palette, close_on_click_outside=True)

    def run_command(_label, action):
        app.close_overlay()  # dismiss the palette first
        action()

    open_btn.on_click(open_palette)
    for w in (title, hint, open_btn, status):
        app.add(w)
    app.focus(open_btn)
    app.on_key("p", open_palette)
    app.on_key(Key.ESC, lambda: "quit")
    app.run()


if __name__ == "__main__":
    main()
