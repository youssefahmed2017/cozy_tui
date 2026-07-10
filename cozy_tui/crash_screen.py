"""Convenience: a ready-made full-screen crash view for an exception.

    try:
        risky()
    except Exception as exc:
        show_traceback(exc)

Esc quits, C copies the plain-text traceback to the clipboard, arrows /
PageUp / PageDown / Home / End scroll. For finer control (embedding in your
own layout, different key bindings, etc.) build your own screen from
:class:`~cozy_tui.widgets.TracebackView` directly.

Run this module for a demo: `python -m cozy_tui.crash_screen`
"""

from cozy_tui.app import App
from cozy_tui.clipboard import copy
from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widgets import Label, ScrollView
from cozy_tui.widgets.display.traceback_view import TracebackView, format_traceback

__all__ = ["show_traceback"]


def show_traceback(exc: BaseException, *, title: str = "Cozy TUI — Error") -> None:
    """Run a blocking, full-screen crash view for `exc`."""
    # catch_errors=False is deliberate: if the crash screen itself blows up, it
    # must fail loudly (a plain traceback) rather than call show_traceback on
    # itself — App's own default is True precisely so *user* apps get this
    # screen automatically, but that must never apply recursively to it.
    app = App(
        full=True, style=Style(fg="white", bg="black"), title=title, catch_errors=False
    )

    hint = Label(
        2,
        0,
        "[C] Copy Traceback     [↑/↓] Scroll     [Esc] Quit",
        Style(fg="bright_black"),
    )
    app.dock(hint, "top")

    # Reserve the ScrollView's left inset + scrollbar column so wrapped lines
    # fit the viewport they'll actually be shown in.
    width = max(20, app.cols - 4)
    view = ScrollView(
        2, 1, f"{width * App.SCALE}x{(app.rows - 4) * App.SCALE}", autoscroll=False
    )
    view.add(TracebackView(0, 0, width, exc))
    app.dock(view, "fill")

    def copy_traceback():
        copy(format_traceback(exc))
        hint.text = "Copied to clipboard!     [Esc] Quit"

    app.focus(view)
    app.on_key(Key.ESC, lambda: "quit")
    app.on_key("c", copy_traceback)
    app.run()


if __name__ == "__main__":

    def _inner():
        data = {"a": 1}
        return data["b"]  # KeyError, raised a couple frames deep

    def _outer():
        _inner()

    try:
        _outer()
    except Exception as exc:
        show_traceback(exc)
