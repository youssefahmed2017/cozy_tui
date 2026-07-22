"""Inline style markup: ``"[bold red]Error[/] connecting"``.

Opt in per widget with ``markup=True`` (:class:`~cozy_tui.widgets.Label`,
:class:`~cozy_tui.widgets.Text`, :class:`~cozy_tui.widgets.AnimatedLabel`,
:class:`~cozy_tui.widgets.Log`); without it the text is drawn verbatim, so
nothing that already works can change meaning by accident.

A tag names any combination of the attributes and colors :class:`Style` already
understands — there is no separate markup color table::

    [red]            [bold]            [bold red]
    [#ff8800]        [rgb(255,136,0)]  [color(33)]
    [on blue]        [white on red]    [dim italic bright_black]

``[/]`` closes the most recent tag; ``[/red]`` does the same and reads better
when tags are nested. Tags nest, and an unclosed one simply runs to the end of
the string.

**Unrecognized tags are left alone.** ``"list[0]"``, ``"[INFO] ready"``, and
``"[a-z]+"`` render as themselves rather than raising or vanishing — the parser
only consumes a bracket group when every word inside it is a real style or
color. That matters most for :class:`~cozy_tui.widgets.Log`, whose input is
usually not written by the person who enabled markup. Use :func:`escape` (or a
backslash: ``"\\[red]"``) when you need a literal bracket that *would* have
parsed.
"""

from __future__ import annotations

import re

from cozy_tui.ansi import _FG, _ST
from cozy_tui.style import Style

__all__ = ["render", "plain", "escape", "runs_width"]

# A bracket group with no newline or nested bracket inside. Whether it is
# actually a tag is decided by _parse_tag, not by this pattern -- see the
# module docstring's "unrecognized tags are left alone" rule.
_TAG = re.compile(r"\\?\[([^\[\]\n]*)\]")

_COLOR_FUNC = re.compile(r"(?:rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)|color\(\s*\d+\s*\))")
_HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")


def _is_color(word: str) -> bool:
    return (
        word in _FG
        or bool(_HEX.fullmatch(word))
        or bool(_COLOR_FUNC.fullmatch(word.replace(" ", "")))
    )


def _parse_tag(body: str, top: Style) -> Style | None:
    """Resolve a tag body ("bold red on blue") against the enclosing style.

    Returns the style to push, or ``None`` if this isn't a tag at all — in
    which case the caller emits the original ``[...]`` as literal text.
    """
    # "rgb(255, 0, 0)" contains spaces that aren't token separators; collapse
    # them so the split below sees one word.
    body = _COLOR_FUNC.sub(lambda m: m.group(0).replace(" ", ""), body)
    words = body.split()
    if not words:
        return None

    fg, bg = top.fg, top.raw_bg
    styles = list(top.styles)
    expect_bg = False
    for word in words:
        if word == "on":
            if expect_bg:  # "on on"
                return None
            expect_bg = True
        elif expect_bg:
            if not _is_color(word):
                return None
            bg, expect_bg = word, False
        elif word in _ST:
            if word not in styles:
                styles.append(word)
        elif _is_color(word):
            fg = word
        else:
            return None
    if expect_bg:  # trailing "on" with nothing after it
        return None
    return Style(fg=fg, bg=bg, styles=styles)


def render(markup: str, base: Style | None = None) -> list[tuple[str, Style]]:
    """Parse *markup* into ``(text, style)`` runs, each styled relative to
    *base*. Newlines are kept inside the runs; callers that care about lines
    split on them.

    Adjacent runs are never merged — a caller measuring width should sum
    :func:`runs_width` rather than assume one run per visual span.
    """
    base = base if base is not None else Style()
    stack: list[Style] = [base]
    runs: list[tuple[str, Style]] = []
    pos = 0

    def emit(text: str) -> None:
        if text:
            runs.append((text, stack[-1]))

    for match in _TAG.finditer(markup):
        raw = match.group(0)
        if raw.startswith("\\"):  # escaped: literal bracket, not a tag
            emit(markup[pos : match.start()] + raw[1:])
            pos = match.end()
            continue

        body = match.group(1)
        if body.startswith("/"):
            # A closing tag pops regardless of what it names: [/] and [/red]
            # both close the innermost open tag. Names are for the reader.
            if len(stack) == 1:  # nothing open -- not ours, leave it be
                continue
            emit(markup[pos : match.start()])
            stack.pop()
            pos = match.end()
            continue

        pushed = _parse_tag(body, stack[-1])
        if pushed is None:
            continue  # not a tag; falls through as literal text
        emit(markup[pos : match.start()])
        stack.append(pushed)
        pos = match.end()

    emit(markup[pos:])
    return runs


def plain(markup: str) -> str:
    """*markup* with every tag removed — what the text measures and wraps as."""
    return "".join(text for text, _style in render(markup))


def escape(text: str) -> str:
    """Backslash-escape ``[`` so *text* survives a markup-enabled widget
    unchanged. Use when interpolating data you don't control."""
    return text.replace("[", "\\[")


def runs_width(runs) -> int:
    """Display width of a run list, wide glyphs included."""
    from cozy_tui._width import text_width

    return sum(text_width(text) for text, _style in runs)


def write_runs(canvas, x: int, y: int, runs) -> int:
    """Paint *runs* left to right starting at ``(x, y)``; returns the total
    width written. Advances by display width, so a run following a wide glyph
    still lands on the right cell."""
    from cozy_tui._width import text_width

    dx = 0
    for text, style in runs:
        if text:
            canvas.write(x + dx, y, text, style)
            dx += text_width(text)
    return dx


def split_lines(runs) -> list[list[tuple[str, Style]]]:
    """Split a run list on newlines into one run list per line. A run spanning
    a newline is divided, so no returned run contains one."""
    lines: list[list[tuple[str, Style]]] = [[]]
    for text, style in runs:
        parts = text.split("\n")
        for i, part in enumerate(parts):
            if i:
                lines.append([])
            if part:
                lines[-1].append((part, style))
    return lines


def slice_runs(runs, start: int, end: int) -> list[tuple[str, Style]]:
    """The runs covering character positions ``[start, end)``.

    Indices count *characters* of the plain text, matching how the wrapping and
    clipping code that calls this already thinks; a wide glyph is one index but
    two cells, so slice on boundaries you got from the plain text itself.
    """
    out: list[tuple[str, Style]] = []
    pos = 0
    for text, style in runs:
        run_end = pos + len(text)
        if run_end > start and pos < end:
            out.append((text[max(0, start - pos) : end - pos], style))
        pos = run_end
        if pos >= end:
            break
    return out
