"""Code widget: a syntax-highlighted source block, rendered through Rich's
``Syntax`` (and therefore Pygments' lexers) and bridged into cozy_tui's own
cell grid -- the same borrow-don't-reimplement approach `Markdown` and
`TracebackView` already take, for the same reason: a highlighter is a large
thing to hand-roll, and `rich` is already a required dependency.
"""

from __future__ import annotations

import io

from rich.console import Console
from rich.syntax import Syntax

from cozy_tui._rich_bridge import to_cozy_style
from cozy_tui.widget import Widget

#: Rich's own terminal-oriented theme, deliberately preferred over its default
#: ("monokai"): its colors *are* the 16 ANSI names, so they survive
#: `_rich_bridge`'s nearest-color mapping exactly instead of being approximated,
#: and they follow the user's terminal palette like the rest of this library.
DEFAULT_THEME = "ansi_dark"

#: Slack added when measuring an auto-sized block, so the gutter and Rich's own
#: right-hand padding have room before the real width is derived from the
#: rendered output.
_MEASURE_SLACK = 16


class Code(Widget):
    """A syntax-highlighted block of source code.

    ::

        from cozy_tui.widgets import Code

        code = Code('print("hello world")', lang="python")
        code_js = Code('console.log("hello")', lang="javascript")

        app.add(code)

    ``lang`` is a Pygments lexer name -- ``"python"``, ``"javascript"``,
    ``"java"``, ``"rust"``, ``"json"``, ``"sql"``, and several hundred more.
    An unrecognized one is **not** an error: Rich falls back to rendering the
    text unhighlighted, which is the right outcome for a viewer (a crash while
    drawing would be far worse than plain text).

    Unlike most widgets, position is keyword-only (``x=``/``y=``) so the code
    itself can come first, matching how a code block reads. Size is optional
    too: with no ``width`` the block measures its own rendered output and
    sizes to fit, so a short snippet needs nothing but the source and a lang.

    Non-focusable and non-interactive -- wrap it in a
    :class:`~cozy_tui.widgets.ScrollView` for anything taller than the screen.
    """

    def __init__(
        self,
        code: str = "",
        lang: str = "text",
        # Not a real parameter: a trap for the Widget(x, y, ...) call shape the
        # rest of the library uses, so that mistake gets named here instead of
        # failing later inside Pygments (or, for Code(2, 1, "src"), as a bare
        # arity error that doesn't hint at what's actually wrong).
        *_positional,
        x: int = 0,
        y: int = 0,
        width: int | None = None,
        line_numbers: bool = False,
        theme: str = DEFAULT_THEME,
        background: bool = True,
        tab_size: int = 4,
        style=None,
    ):
        if _positional or isinstance(code, int):
            raise TypeError(
                "Code takes the source first: Code('print(1)', lang='python', "
                "x=2, y=1) -- x/y are keyword-only here"
            )
        super().__init__(x, y, style)
        self.bind("code", code)  # code may be a State
        self.lang = lang
        self.width = width
        self.line_numbers = line_numbers
        self.theme = theme
        self.background = background
        self.tab_size = tab_size
        self._cache_key: tuple | None = None
        self._rows: list | None = None
        self._measured: int | None = None

    # ── rendering ────────────────────────────────────────────────────────────

    def _syntax(self) -> Syntax:
        return Syntax(
            self.code,
            self.lang,
            theme=self.theme,
            line_numbers=self.line_numbers,
            tab_size=self.tab_size,
            word_wrap=False,
            # "default" leaves the cell background alone, so the block sits on
            # whatever the app's own background is instead of painting a slab.
            background_color=None if self.background else "default",
        )

    def _render_rows(self, w: int) -> list:
        console = Console(width=w, file=io.StringIO())
        lines = console.render_lines(self._syntax(), console.options.update(width=w))
        return [
            [(seg.text, to_cozy_style(seg.style, self.style)) for seg in line]
            for line in lines
        ]

    def _measure(self) -> int:
        """Width of the block when no explicit ``width`` was given.

        Derived from Rich's *rendered* output rather than from the source text:
        the line-number gutter's exact width is Rich's business (and has
        changed shape between versions), so rendering once at a generous width
        and reading back how much was actually used is the one measurement
        that can't drift out of sync with it.
        """
        longest = max((len(line) for line in self.code.splitlines()), default=0)
        probe = max(1, longest + _MEASURE_SLACK)
        used = 0
        for row in self._render_rows(probe):
            used = max(used, len("".join(text for text, _style in row).rstrip()))
        return max(1, used)

    def _key(self) -> tuple:
        return (
            self.code,
            self.lang,
            self.width,
            self.line_numbers,
            self.theme,
            self.background,
            self.tab_size,
            self._clip_width,
        )

    def _sync(self) -> None:
        """Re-render if any input changed. Everything else here reads through
        this, so mutating ``code``/``lang``/... as a plain attribute is enough
        to update the widget -- no setter or explicit refresh call."""
        key = self._key()
        if key == self._cache_key:
            return
        self._cache_key = key
        self._measured = None
        w = self._clip_width or self.width
        if w is None:
            w = self._measure()
            self._measured = w
        self._rows = self._render_rows(w)

    # ── Widget interface ─────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        self._sync()
        return self._clip_width or self.width or self._measured or 1

    def natural_height(self, scale) -> int:
        self._sync()
        return max(1, len(self._rows or []))

    def contains(self, col: int, row: int) -> bool:
        w = self.natural_width(1)
        h = self.natural_height(1)
        return self.abs_x <= col < self.abs_x + w and self.abs_y <= row < self.abs_y + h

    def draw(self, canvas) -> None:
        self._sync()
        for row, cells in enumerate(self._rows or []):
            vy = self.abs_y + row
            if vy >= canvas.rows:
                break
            cx = self.abs_x
            for text, style in cells:
                canvas.write(cx, vy, text, style)
                cx += len(text)
