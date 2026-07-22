from collections import deque

from cozy_tui.widgets.display.label import Label
from cozy_tui.widgets.layout.scroll_view import ScrollView


class Log(ScrollView):
    """An append-only, auto-scrolling text log.

    Example::

        log = Log(2, 2, "600x160")
        app.add(log)
        log.log("Server started")

        errors = Log(2, 2, "600x160", markup=True)
        errors.log("[red]connection refused[/] — retrying")

    ``log()`` takes the same shape as ``print()`` (several values, joined by
    ``sep``) and splits embedded newlines into separate rows, so a formatted
    traceback or a block of output lands as one line each.

    Being a :class:`~cozy_tui.widgets.ScrollView`, it scrolls with the wheel and
    the arrow/page keys once focused, and stays pinned to the newest line until
    the user scrolls up. ``max_lines`` (default 1000) bounds how much history is
    kept — the oldest rows are dropped, which is what keeps a long-running app's
    memory flat. Rows are clipped, not wrapped; use :class:`Text` for prose.

    With ``markup=True`` each line is parsed for inline style tags (see
    :mod:`cozy_tui.markup`). Tags that aren't recognized are left as literal
    text, so a log line that merely happens to contain ``[`` — a level prefix,
    a list index — still reads correctly.
    """

    def __init__(
        self,
        x=0,
        y=0,
        size="600x200",
        *,
        markup: bool = False,
        max_lines: int = 1000,
        autoscroll: bool = True,
        scrollbar: bool = True,
        smooth: bool = True,
        style=None,
    ):
        super().__init__(
            x,
            y,
            size,
            autoscroll=autoscroll,
            scrollbar=scrollbar,
            smooth=smooth,
            style=style,
        )
        self.markup = markup
        self._lines: deque[str] = deque(maxlen=max_lines)

    # ── content ──────────────────────────────────────────────────────────────

    @property
    def lines(self) -> list[str]:
        """The retained lines, oldest first — as passed in, tags and all."""
        return list(self._lines)

    @property
    def max_lines(self) -> int:
        return self._lines.maxlen

    def log(self, *values, sep: str = " ") -> "Log":
        """Append one line per newline in ``sep.join(str(v) for v in values)``.
        Returns self, so calls chain."""
        text = sep.join(str(v) for v in values)
        for line in text.split("\n"):
            self._append(line)
        return self

    def _append(self, line: str) -> None:
        over = len(self._lines) == self._lines.maxlen
        self._lines.append(line)
        if over:
            # The deque dropped its oldest line; drop the matching row and
            # shift the rest up. Renumbering the whole list is O(max_lines)
            # per line once the cap is reached, but it keeps child `y` values
            # equal to their row index — which is what ScrollView measures
            # content height and scroll offsets against, so anything cleverer
            # would have to be undone before drawing anyway.
            self._children.pop(0)
            for child in self._children:
                child.y -= 1
        self.add(Label(0, len(self._children), line, self.style, markup=self.markup))

    def clear(self) -> None:
        super().clear()
        self._lines.clear()
