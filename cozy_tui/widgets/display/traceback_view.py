"""TracebackView widget: renders an exception's traceback via Rich, bridged
into cozy_tui's own cell grid instead of a stdout print — so it composes with
overlays, ScrollView, and the raw-mode/alt-screen renderer like any other
widget, rather than corrupting them the way a raw print would."""

import io
import traceback as _tb_module

from rich.console import Console
from rich.traceback import Traceback as _RichTraceback

from cozy_tui._rich_bridge import to_cozy_style
from cozy_tui.widget import Widget


def format_traceback(exc: BaseException) -> str:
    """Plain-text traceback for `exc` (no styling) — for logging, or for
    copying to the clipboard alongside a rendered :class:`TracebackView`."""
    return "".join(_tb_module.format_exception(type(exc), exc, exc.__traceback__))


class TracebackView(Widget):
    """Displays an exception's traceback with Rich's syntax highlighting and
    local-variable inspection. Non-focusable and non-interactive — wrap it in
    a :class:`~cozy_tui.widgets.ScrollView` for tracebacks taller than the
    screen (`show_locals` in particular can make these long).

    Example::

        try:
            risky()
        except Exception as exc:
            view = ScrollView(2, 1, "700x400")
            view.add(TracebackView(0, 0, 68, exc))
            app.add(view)

    For a ready-made full-screen crash view (Esc to quit, C to copy), use
    :func:`cozy_tui.crash_screen.show_traceback` instead.
    """

    def __init__(
        self, x, y, width: int, exc: BaseException, *, show_locals=True, style=None
    ):
        super().__init__(x, y, style, name="Cozy TUI Traceback")
        self.width = width
        self.exc = exc
        self.show_locals = show_locals
        self._cache_key = None
        self._rows: list | None = None

    def _rendered_rows(self, w: int) -> list:
        key = (self.exc, w, self.show_locals)
        if key != self._cache_key:
            self._cache_key = key
            self._rows = self._render(w)
        return self._rows

    def _render(self, w: int) -> list:
        console = Console(width=w, file=io.StringIO())
        tb = _RichTraceback.from_exception(
            type(self.exc),
            self.exc,
            self.exc.__traceback__,
            show_locals=self.show_locals,
            width=w,
        )
        options = console.options.update(width=w)
        lines = console.render_lines(tb, options)
        return [
            [(seg.text, to_cozy_style(seg.style, self.style)) for seg in line]
            for line in lines
        ]

    def natural_width(self, scale) -> int:
        return self.width

    def natural_height(self, scale) -> int:
        w = self._clip_width or self.width
        return max(1, len(self._rendered_rows(w)))

    def draw(self, canvas) -> None:
        w = self._clip_width or self.width
        for row, cells in enumerate(self._rendered_rows(w)):
            vy = self.abs_y + row
            if vy >= canvas.rows:
                break
            cx = self.abs_x
            for text, style in cells:
                canvas.write(cx, vy, text, style)
                cx += len(text)

    def contains(self, col: int, row: int) -> bool:
        w = self._clip_width or self.width
        h = self.natural_height(1)
        return self.abs_x <= col < self.abs_x + w and self.abs_y <= row < self.abs_y + h
