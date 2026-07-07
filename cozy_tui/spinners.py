"""Live showcase of every built-in Spinner preset — run it with
``python -m cozy_tui.spinners``.

Lists every name in ``cozy_tui._spinners.SPINNERS``, each animating with its
own frames and speed inside a scrollable viewport (mouse wheel / ↑ / ↓ /
PageUp / PageDown). Esc quits.
"""

from cozy_tui import App, Style
from cozy_tui._spinners import SPINNERS
from cozy_tui.events import Key
from cozy_tui.widgets import Label, ScrollView, Spinner

ACCENT = Style(fg="bright_cyan")
MUTED = Style(fg="bright_black")


def main() -> None:
    app = App(
        full=True,
        style=Style(fg="white", bg="black"),
        title="Cozy TUI — Spinners",
    )

    header = Label(
        2, 0, "Cozy TUI spinner presets  —  ↑/↓ or wheel to scroll, Esc to quit", ACCENT
    )
    app.dock(header, "top")

    view = ScrollView(2, 1, "10x10", autoscroll=False)  # size replaced by dock below
    for i, name in enumerate(sorted(SPINNERS)):
        frames, speed = SPINNERS[name]
        label = f"  {name}  ({speed:.3g}s/frame, {len(frames)} frames)"
        view.add(Spinner(0, i, spinner=name, label=label))
    app.dock(view, "fill")

    app.focus(view)
    app.on_key(Key.ESC, lambda: "quit")
    app.run()


if __name__ == "__main__":
    main()
