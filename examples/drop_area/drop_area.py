"""Drop Area — drag a file onto the terminal to file it away.

A `DropFilesArea` copies whatever you drop (or paste the path of) into a
``dropped/`` folder next to this script. A terminal delivers a drag-and-drop as
the file's *path text*, so this works for files on the same machine as the
terminal; a path dropped over SSH points at the terminal's filesystem, not this
process's, and shows up as a friendly "not found here".

    python examples/drop_area/drop_area.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.widgets import DropFilesArea, Label

ACCENT = Style(fg="bright_cyan")
MUTED = Style(fg="bright_black")

STORE = Path(__file__).resolve().parent / "dropped"


def main():
    app = App(full=True, style=Style(fg="white", bg="rgb(24,26,32)"), title="Drop Area")

    app.add(Label(2, 0, "Drag a file onto the terminal (or paste its path) · Esc quits",
                  MUTED))

    stored = Label(2, 15, f"Files land in: {STORE}", MUTED)

    drop = DropFilesArea(2, 2, STORE, "720x300", hint="Drop a file here")
    drop.on_drop(lambda paths: setattr(
        stored, "text", f"Stored {len(paths)} file(s) in {STORE}"))

    app.add(drop)
    app.add(stored)
    app.focus(drop)
    app.on_key(Key.ESC, lambda: "quit")
    app.run()


if __name__ == "__main__":
    main()
