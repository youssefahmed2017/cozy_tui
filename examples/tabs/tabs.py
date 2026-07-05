"""Tabs — a tabbed container demo.

A single `Tabs` widget with three panels. Tab into the strip, use ←/→ (or Home/
End) or click a title to switch, then Tab again to dive into the active panel's
controls. Each panel holds ordinary widgets.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.widgets import (Button, CheckItem, CheckList, Hyperlink, Input,
                              Label, ListItem, ListView, ProgressBar, Tabs)

ACCENT = Style(fg="bright_cyan")
MUTED = Style(fg="bright_black")


def main():
    app = App(full=True, style=Style(fg="white", bg="rgb(24,26,32)"), title="Tabs")

    app.add(Label(2, 0, "Tabs — ←/→ switch · Tab dives into a panel · Esc quits", MUTED))

    tabs = Tabs(2, 2, "760x360", accent="bright_cyan")

    # ── Files ────────────────────────────────────────────────────────────────
    status = Label(1, 6, "", Style(fg="bright_green"))
    files = tabs.add_tab("Files")
    files.add(Label(1, 1, "Pick a file:", ACCENT))
    files.add(
        ListView(1, 2, [ListItem("report.pdf"), ListItem("notes.md"),
                        ListItem("photo.png"), ListItem("archive.zip")], height=4)
        .on_select(lambda name: setattr(status, "text", f"Selected {name}"))
    )
    files.add(status)

    # ── Settings ─────────────────────────────────────────────────────────────
    settings = tabs.add_tab("Settings")
    settings.add(Label(1, 1, "Name:", ACCENT))
    settings.add(Input(7, 1, 24, placeholder="your name…"))
    settings.add(
        CheckList(1, 3, [CheckItem("Dark theme", checked=True),
                         CheckItem("Autosave"), CheckItem("Telemetry")], height=3)
    )

    # ── About ────────────────────────────────────────────────────────────────
    about = tabs.add_tab("About")
    about.add(Label(1, 1, "Cozy TUI — tabbed containers", ACCENT))
    about.add(Label(1, 3, "Only the active panel is drawn, focusable, and clickable."))
    about.add(ProgressBar(1, 5, width=40, progress=0.72))
    about.add(Hyperlink(1, 7, "GitHub", "https://github.com/youssefahmed2017/cozy_tui"))

    tabs.on_change(lambda i: setattr(status, "text", ""))
    app.add(tabs)
    app.focus(tabs.bar)
    app.on_key(Key.ESC, lambda: "quit")
    app.run()


if __name__ == "__main__":
    main()
