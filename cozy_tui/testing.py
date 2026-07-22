"""Headless driving of an :class:`~cozy_tui.App` for tests.

::

    from cozy_tui import App
    from cozy_tui.testing import Harness
    from cozy_tui.widgets import Button, Label

    def test_clicking_saves():
        app = App(full=False, size="600x200")
        status = Label(0, 2, "Ready")
        button = Button(0, 0, "Save")
        button.on_click(lambda _b: setattr(status, "text", "Saved!"))
        app.add(button)
        app.add(status)

        with Harness(app) as ui:
            ui.click(button)
            assert "Saved!" in ui.screen

A ``Harness`` drives the app the way :meth:`App.run` would -- feeding events
through :meth:`App._dispatch_input` and re-composing after each one -- without
a terminal, a real event loop, or a single escape byte written to stdout. Every
action leaves the screen freshly composed, so an assertion right after it sees
what a user would see.

It renders via ``App._compose()`` rather than ``App.render()``: composing fills
the cell buffer without emitting to the terminal, so a test suite stays quiet
instead of interleaving thousands of escape sequences with pytest's output.
That also means the diff renderer isn't exercised here -- this harness is for
testing *your app*, not cozy_tui's renderer.

Time is virtual. Nothing sleeps: :meth:`Harness.advance` moves a private clock
offset forward and fires whatever ``app.after``/``app.every`` timers that
crosses, so a test for a 30-second timeout runs instantly. Background work
started with ``app.run_worker`` is real threading, so :meth:`Harness.settle`
waits for results and delivers their callbacks on this thread, exactly as the
event loop would.
"""

from __future__ import annotations

import importlib
import time

from cozy_tui.events import MouseClick, MouseDrag, MouseMove, MouseRelease, Paste

__all__ = ["Harness"]

#: How long :meth:`Harness.settle` waits for background workers, in seconds.
DEFAULT_SETTLE_TIMEOUT = 2.0
_SETTLE_POLL = 0.005


class _VirtualClock:
    """Stand-in for the `time` module that adds a test-controlled offset to
    `monotonic()` and passes everything else straight through."""

    offset = 0.0

    def monotonic(self) -> float:
        return time.monotonic() + self.offset

    def __getattr__(self, name):
        return getattr(time, name)


#: Modules whose animations are timed off a wall clock rather than off a timer
#: (`Tween`, the Tabs underline glide, Button's press flash, Spinner,
#: AnimatedLabel). `App` is deliberately absent: its own `monotonic()` calls are
#: frame timing and double-click detection, which virtual time has no business
#: shifting -- timers are advanced explicitly instead, via `_drain_timers`.
_CLOCK_MODULES = (
    "cozy_tui.motion",
    "cozy_tui.widgets.layout.tabs",
    "cozy_tui.widgets.selection.button",
    "cozy_tui.widgets.display.spinner",
    "cozy_tui.widgets.display.animated_label",
)

_CLOCK = _VirtualClock()
_clock_installed = False


def _install_clock() -> None:
    """Swap the virtual clock into the animating modules, once per process.

    It is never uninstalled, and doesn't need to be: with `offset` back at 0 it
    is indistinguishable from the real `time` module, and every Harness resets
    the offset on construction. That avoids any restore-ordering hazard between
    overlapping harnesses or a test that never closes one.
    """
    global _clock_installed
    if _clock_installed:
        return
    for name in _CLOCK_MODULES:
        importlib.import_module(name).time = _CLOCK
    _clock_installed = True


class Harness:
    """Drives ``app`` headlessly. Usable as a context manager or directly."""

    def __init__(self, app, *, size: str | None = None):
        # Headless regardless of how the app was built: `full=True` would size
        # the buffer from the real terminal (or 80x24 when there isn't one),
        # which makes a test's assertions depend on the machine running it.
        app.full = False
        if size is not None or not getattr(app, "buffer", None):
            app._init_size(size or "800x240")
        # Let exceptions out. The default (catch_errors=True) swallows them
        # into a full-screen crash view, which in a test means a hang on a
        # terminal that isn't there and a green run for broken code.
        app.catch_errors = False
        self.app = app
        _install_clock()
        _CLOCK.offset = 0.0
        self.compose()

    # ── context manager ──────────────────────────────────────────────────────

    def __enter__(self) -> "Harness":
        return self

    def __exit__(self, *_exc) -> None:
        self.app._should_quit = True

    # ── the screen ───────────────────────────────────────────────────────────

    def compose(self) -> "Harness":
        """Re-run the draw pass into the cell buffer. Called automatically after
        every action; call it directly after mutating a widget by hand."""
        self.app._compose()
        return self

    @property
    def screen(self) -> str:
        """The whole screen as text, one line per row, trailing blanks stripped."""
        return "\n".join(self.lines)

    @property
    def lines(self) -> list[str]:
        """Every screen row as text.

        Composes first, exactly as :meth:`App.snapshot` does -- so a read right
        after mutating a widget by hand sees the result, with no explicit
        :meth:`compose` call.
        """
        self.compose()
        return ["".join(cell.char for cell in row).rstrip() for row in self.app.buffer]

    def line(self, row: int) -> str:
        """One screen row as text."""
        return self.lines[row]

    def cell(self, col: int, row: int):
        """The raw :class:`~cozy_tui.app.Cell` at ``(col, row)`` -- for asserting
        on color/style, which :attr:`screen` throws away. Composes first, like
        :attr:`lines`."""
        self.compose()
        return self.app.buffer[row][col]

    def find(self, text: str) -> tuple[int, int] | None:
        """``(col, row)`` of the first occurrence of ``text`` on screen, or None."""
        for row, line in enumerate(self.lines):
            col = line.find(text)
            if col != -1:
                return col, row
        return None

    def __contains__(self, text: str) -> bool:
        """``"Saved!" in harness`` -- shorthand for the common assertion."""
        return text in self.screen

    # ── keyboard ─────────────────────────────────────────────────────────────

    def press(self, *keys) -> "Harness":
        """Send key events -- ``Key.*`` constants or single characters."""
        for key in keys:
            self.app._dispatch_input(key)
        return self.compose()

    def type(self, text: str) -> "Harness":
        """Type ``text`` one character at a time, as a person would.

        Not the same as a paste: this fires per-character handlers (validation,
        ``on_change``, undo coalescing) exactly like real typing. Use
        :meth:`paste` for a bracketed paste.
        """
        for char in text:
            self.app._dispatch_input(char)
        return self.compose()

    def paste(self, text: str) -> "Harness":
        """Deliver ``text`` as a single bracketed-paste event."""
        self.app._dispatch_input(Paste(text))
        return self.compose()

    # ── mouse ────────────────────────────────────────────────────────────────

    def _point(self, target) -> tuple[int, int]:
        """Resolve a widget or an explicit ``(col, row)`` to screen coordinates."""
        if isinstance(target, tuple):
            return target
        return target.abs_x, target.abs_y

    def click(self, target, *, button: int = 0) -> "Harness":
        """Click a widget (at its top-left cell) or an explicit ``(col, row)``."""
        col, row = self._point(target)
        self.app._dispatch_input(MouseClick(col, row, button))
        return self.compose()

    def right_click(self, target) -> "Harness":
        return self.click(target, button=2)

    def double_click(self, target) -> "Harness":
        """Two clicks close enough together to be treated as a double click."""
        col, row = self._point(target)
        self.app._dispatch_input(MouseClick(col, row, 0))
        self.app._dispatch_input(MouseClick(col, row, 0))
        return self.compose()

    def hover(self, target) -> "Harness":
        """Move the mouse over a widget or point (no button held)."""
        col, row = self._point(target)
        self.app._dispatch_input(MouseMove(col, row))
        return self.compose()

    def drag(self, target, *, button: int = 0) -> "Harness":
        """Mouse motion with a button held. Routed to the focused widget, which
        is how the app captures a drag started by :meth:`click`."""
        col, row = self._point(target)
        self.app._dispatch_input(MouseDrag(col, row, button))
        return self.compose()

    def release(self, target, *, button: int = 0) -> "Harness":
        col, row = self._point(target)
        self.app._dispatch_input(MouseRelease(col, row, button))
        return self.compose()

    def scroll(self, target, *, down: bool = True, amount: int = 1) -> "Harness":
        """Wheel scroll over a widget or point."""
        col, row = self._point(target)
        button = 5 if down else 4  # VT wheel buttons
        for _ in range(amount):
            self.app._dispatch_input(MouseClick(col, row, button))
        return self.compose()

    # ── focus ────────────────────────────────────────────────────────────────

    @property
    def focused(self):
        return self.app.focused

    def focus(self, widget) -> "Harness":
        self.app.focus(widget)
        return self.compose()

    # ── time & background work ───────────────────────────────────────────────

    def advance(self, seconds: float) -> "Harness":
        """Move the clock forward: fire any ``after``/``every`` timers that
        crosses, **and** carry wall-clock animations forward with it.

        Nothing sleeps -- a 30-second timeout is testable instantly. The offset
        accumulates, so repeated calls keep moving forward rather than each
        jumping from the real present.

        Animations matter here because several widgets deliberately hide
        content mid-transition -- a `Tabs` panel draws nothing while its
        underline glides -- so a test that switches tabs and reads the screen
        without letting time pass sees an empty panel, exactly as a user would
        in that same instant.
        """
        _CLOCK.offset += seconds
        self.app._drain_timers(time.monotonic() + _CLOCK.offset)
        return self.compose()

    def settle(self, timeout: float = DEFAULT_SETTLE_TIMEOUT) -> "Harness":
        """Wait for background workers and deliver their callbacks here.

        ``app.run_worker`` really does use a thread, so this really does wait --
        but only for as long as results keep arriving, and never past
        ``timeout``. Callbacks fire on *this* thread, the same guarantee the
        event loop gives.
        """
        deadline = time.monotonic() + timeout
        delivered = self.app._drain_workers()
        while not delivered and time.monotonic() < deadline:
            time.sleep(_SETTLE_POLL)
            delivered = self.app._drain_workers()
        # A callback may have queued more work; drain whatever is already in.
        while self.app._drain_workers():
            pass
        return self.compose()

    # ── misc ─────────────────────────────────────────────────────────────────

    def resize(self, size: str) -> "Harness":
        """Resize the screen, e.g. ``"400x120"`` (virtual pixels, as elsewhere).
        Docked and flex layouts reflow on the next compose, as on a real resize.
        """
        self.app._init_size(size)
        return self.compose()

    @property
    def cursor(self) -> tuple[int, int] | None:
        """``(col, row)`` of the terminal cursor, or None when it's hidden."""
        focused = self.app.focused
        if focused is None or not getattr(focused, "cursor", False):
            return None
        scroll = 0 if self.app._topmost_modal() else self.app.scroll_y
        return focused._get_cursor_screen_pos(scroll)

    @property
    def quit_requested(self) -> bool:
        """True once something called ``app.quit()`` -- what a real loop would
        act on, since there's no loop here to exit."""
        return self.app._should_quit
