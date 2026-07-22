"""Diff widget: a line-level, colorized text diff (`difflib`-backed, no new
dependency) with optional syntax highlighting via Rich's `Syntax` (backed by
Pygments, already a transitive dependency of `rich` -- no new dependency
either) -- see `TracebackView` for the sibling pattern this follows (a
non-focusable, non-interactive block of formatted read-only text, sized to
fit its content, cached on its own inputs)."""

import difflib
import io

from cozy_tui._rich_bridge import to_cozy_style
from cozy_tui._width import text_width
from cozy_tui.ansi import tint
from cozy_tui.style import Style
from cozy_tui.widget import Widget

_TINT_AMOUNT = 0.25  # how strongly a changed row's background leans toward
# its tag color -- a full-strength fill would fight with the syntax-
# highlighted code text sitting on top of it.
_MARKERS = {"equal": " ", "delete": "-", "insert": "+"}
_SYNTAX_THEME = "monokai"


def _diff_rows_with_index(old_text: str, new_text: str):
    """Shared core for `diff_lines()` and `Diff`'s syntax-highlighting
    lookup: yields (tag, source_index, line) -- `source_index` is the
    line's position in `old_text.splitlines()` (for "equal"/"delete") or
    `new_text.splitlines()` (for "insert"), used to fetch that exact line's
    pre-highlighted segments without re-highlighting per row."""
    old, new = old_text.splitlines(), new_text.splitlines()
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("equal", "delete", "replace"):
            deleted_tag = "delete" if tag == "replace" else tag
            for idx in range(i1, i2):
                yield deleted_tag, idx, old[idx]
        if tag in ("insert", "replace"):
            for idx in range(j1, j2):
                yield "insert", idx, new[idx]


def diff_lines(old_text: str, new_text: str) -> list[tuple[str, str]]:
    """Return ``[(tag, line), ...]`` in display order -- ``tag`` is
    ``"equal"``/``"delete"``/``"insert"``. A changed span shows its old
    lines (deleted) before its new lines (inserted), like a unified diff
    but with no hunk headers -- what `Diff` renders."""
    return [
        (tag, line) for tag, _idx, line in _diff_rows_with_index(old_text, new_text)
    ]


def _highlight_lines(text: str, lexer: str, base_fg) -> list[list[tuple[str, Style]]]:
    """One row of Rich-highlighted (text, Style) segments per line of
    `text` (via `rich.syntax.Syntax`, bridged through `to_cozy_style` the
    same way `Markdown`/`TracebackView` already do). Rebuilt from
    ``"\\n".join(text.splitlines())`` rather than `text` itself -- Rich's
    own line-splitting (unlike `str.splitlines()`) counts a trailing
    newline as one more, empty, line, which would misalign every index
    after it against `_diff_rows_with_index`'s `str.splitlines()`-based
    positions."""
    lines = text.splitlines()
    if not lines:
        return []
    from rich.console import Console
    from rich.syntax import Syntax

    width = max((text_width(line) for line in lines), default=1) or 1
    syntax = Syntax(
        "\n".join(lines),
        lexer,
        theme=_SYNTAX_THEME,
        line_numbers=False,
        word_wrap=False,
        background_color="default",
    )
    console = Console(file=io.StringIO(), width=width, color_system="truecolor")
    options = console.options.update(width=width)
    base = Style(fg=base_fg)
    return [
        [(seg.text, to_cozy_style(seg.style, base)) for seg in line]
        for line in console.render_lines(syntax, options, pad=False)
    ]


class Diff(Widget):
    """Renders a colorized, line-level diff of two strings: a line-number
    gutter (a single running counter down the rendered rows, not separate
    old-file/new-file counters) followed by a `"+"`/`"-"`/blank marker,
    then the line itself, syntax-highlighted via Rich's `Syntax` (set
    `lexer=None` for plain, unhighlighted text). Changed rows get their
    whole width tinted toward red (removed) or green (added), like
    GitHub's diff view -- the syntax colors sit on top of that tint rather
    than the widget's own text color. Uses the standard library's
    `difflib` for the diffing itself (see `diff_lines`) and Rich's
    Pygments-backed highlighter for the syntax colors -- both already
    dependencies of this library, so nothing new to install.

    Non-focusable and non-interactive, like `TracebackView`: it sizes
    itself to fit the whole diff and does not wrap or truncate long lines
    (naive character-wrapping would break code mid-token) -- wrap it in a
    :class:`~cozy_tui.widgets.ScrollView` if the diff is taller than the
    screen. Word-level highlighting *within* a changed line (vs. this
    version's whole-line diff granularity) is a separate, larger follow-up.

    Example::

        box.add(Diff(2, 2, old_source, new_source))
        box.add(Diff(2, 2, old_json, new_json, lexer="json"))
    """

    def __init__(
        self,
        x,
        y,
        old_text: str,
        new_text: str,
        *,
        lexer: str | None = "python",
        style=None,
    ):
        super().__init__(x, y, style)
        self.old_text = old_text
        self.new_text = new_text
        self.lexer = lexer
        self._cache_key = None
        self._rows: list[list[tuple[str, Style]]] | None = None

    def _rendered_rows(self) -> list[list[tuple[str, Style]]]:
        key = (self.old_text, self.new_text, self.lexer)
        if key != self._cache_key:
            self._cache_key = key
            self._rows = self._render()
        return self._rows

    def _render(self) -> list[list[tuple[str, Style]]]:
        from cozy_tui.theme import get_theme  # local: theme.py builds on Style

        rows_data = list(_diff_rows_with_index(self.old_text, self.new_text))
        if not rows_data:
            return []

        theme = get_theme()
        base_bg = self.style.raw_bg or "black"
        tag_fg = {
            "equal": self.style.fg,
            "delete": theme.error,
            "insert": theme.success,
        }
        tag_bg = {
            "equal": base_bg,
            "delete": tint(base_bg, theme.error, _TINT_AMOUNT),
            "insert": tint(base_bg, theme.success, _TINT_AMOUNT),
        }
        gutter_w = len(str(len(rows_data)))
        code_w = max(text_width(line) for _tag, _idx, line in rows_data)

        old_hl = new_hl = None
        if self.lexer is not None:
            old_hl = _highlight_lines(self.old_text, self.lexer, self.style.fg)
            new_hl = _highlight_lines(self.new_text, self.lexer, self.style.fg)

        rows = []
        for i, (tag, idx, line) in enumerate(rows_data, start=1):
            bg = tag_bg[tag]
            gutter_style = Style(
                fg=tag_fg[tag], bg=bg, styles=["bold"] if tag != "equal" else []
            )
            gutter_text = f"{i:>{gutter_w}} {_MARKERS[tag]} "

            if old_hl is not None:
                source = new_hl if tag == "insert" else old_hl
                code_segments = [
                    (text, Style(fg=style.fg, bg=bg, styles=style.styles))
                    for text, style in source[idx]
                ]
            else:
                code_segments = [(line, Style(fg=self.style.fg, bg=bg))]

            rendered_w = sum(text_width(t) for t, _ in code_segments)
            if rendered_w < code_w:
                code_segments.append(
                    (" " * (code_w - rendered_w), Style(fg=self.style.fg, bg=bg))
                )

            rows.append([(gutter_text, gutter_style), *code_segments])
        return rows

    def natural_width(self, scale) -> int:
        return max(
            (sum(text_width(t) for t, _ in row) for row in self._rendered_rows()),
            default=0,
        )

    def natural_height(self, scale) -> int:
        return max(1, len(self._rendered_rows()))

    def draw(self, canvas) -> None:
        for row, segments in enumerate(self._rendered_rows()):
            cx = self.abs_x
            for text, style in segments:
                canvas.write(cx, self.abs_y + row, text, style)
                cx += text_width(text)
