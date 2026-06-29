"""MarkdownInput: Input with live Rich Markdown preview when not focused."""

from __future__ import annotations

import re
from io import StringIO

from cozy_tui.widgets.input import Input
from cozy_tui.style import Style

try:
    from rich.console import Console
    from rich.markdown import Markdown as _RichMarkdown
    _RICH_OK = True
except ImportError:
    _RICH_OK = False

# ── ANSI parser ───────────────────────────────────────────────────────────────

_ANSI16 = [
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "bright_black", "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
]

_FG_CODES = {
    30: "black",        31: "red",          32: "green",        33: "yellow",
    34: "blue",         35: "magenta",      36: "cyan",         37: "white",
    90: "bright_black", 91: "bright_red",   92: "bright_green", 93: "bright_yellow",
    94: "bright_blue",  95: "bright_magenta", 96: "bright_cyan", 97: "bright_white",
}
_BG_CODES = {
    40: "black",         41: "red",           42: "green",         43: "yellow",
    44: "blue",          45: "magenta",        46: "cyan",          47: "white",
    100: "bright_black", 101: "bright_red",   102: "bright_green", 103: "bright_yellow",
    104: "bright_blue",  105: "bright_magenta", 106: "bright_cyan", 107: "bright_white",
}

_CSI_RE = re.compile(r"\x1b\[([0-9;]*)([A-Za-z])")
_OSC_RE = re.compile(r"\x1b\][^\x07]*\x07|\x1b\][^\x1b]*\x1b\\")


def _emit(lines: list, text: str, style: Style) -> None:
    """Append *text* to *lines*, splitting on newlines."""
    if not text:
        return
    if "\n" in text:
        parts = text.split("\n")
        for i, part in enumerate(parts):
            if part:
                lines[-1].append((part, style))
            if i < len(parts) - 1:
                lines.append([])
    else:
        lines[-1].append((text, style))


def _parse_ansi_lines(raw: str, base: Style) -> list:
    """Parse an ANSI-escaped string into ``list[list[(str, Style)]]``."""
    lines: list[list] = [[]]
    raw = _OSC_RE.sub("", raw)   # strip hyperlinks / OSC sequences

    fg, bg, st = base.fg, base.bg, list(base.styles)
    pos = 0

    while pos < len(raw):
        m = _CSI_RE.search(raw, pos)
        if not m:
            _emit(lines, raw[pos:], Style(fg=fg, bg=bg, styles=list(st)))
            break

        if m.start() > pos:
            _emit(lines, raw[pos:m.start()], Style(fg=fg, bg=bg, styles=list(st)))

        if m.group(2) == "m":   # SGR — only sequence type we care about
            params = (
                [int(x) for x in m.group(1).split(";") if x.isdigit()]
                if m.group(1) else [0]
            )
            i = 0
            while i < len(params):
                p = params[i]
                if p == 0:
                    fg, bg, st = base.fg, base.bg, list(base.styles)
                elif p == 1 and "bold"      not in st: st.append("bold")
                elif p == 2 and "dim"       not in st: st.append("dim")
                elif p == 3 and "italic"    not in st: st.append("italic")
                elif p == 4 and "underline" not in st: st.append("underline")
                elif p == 22: st = [s for s in st if s not in ("bold", "dim")]
                elif p == 23: st = [s for s in st if s != "italic"]
                elif p == 24: st = [s for s in st if s != "underline"]
                elif p in _FG_CODES: fg = _FG_CODES[p]
                elif p == 39:         fg = base.fg
                elif p in _BG_CODES: bg = _BG_CODES[p]
                elif p == 49:         bg = base.bg
                elif p == 38:
                    if i + 2 < len(params) and params[i + 1] == 5:
                        n = params[i + 2]
                        fg = _ANSI16[n] if n < 16 else fg
                        i += 2
                    elif i + 4 < len(params) and params[i + 1] == 2:
                        i += 4
                elif p == 48:
                    if i + 2 < len(params) and params[i + 1] == 5:
                        n = params[i + 2]
                        bg = _ANSI16[n] if n < 16 else bg
                        i += 2
                    elif i + 4 < len(params) and params[i + 1] == 2:
                        i += 4
                i += 1
        # All other CSI sequences (cursor movement, erase, etc.) are consumed silently

        pos = m.end()

    return lines


# ── Widget ────────────────────────────────────────────────────────────────────

class MarkdownInput(Input):
    """Input widget that renders content as a live Markdown preview when unfocused.

    All editing behaviour (cursor, typing, backspace, home/end, multiline,
    wrapping, masking) is inherited unchanged from Input.  Only draw() is
    overridden:

    - focused   → raw text with cursor  (standard Input rendering)
    - unfocused → Rich Markdown preview

    Requires ``rich`` (``pip install rich``).  Falls back to plain Input
    rendering if Rich is not installed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._md_cache_key: tuple | None = None
        self._md_lines: list | None = None   # list[list[(str, Style)]]

    # ── rendering cache ───────────────────────────────────────────────────────

    def _rendered_lines(self, w: int) -> list:
        key = (self.value, w)
        if key != self._md_cache_key:
            self._md_cache_key = key
            self._md_lines = self._render_md(self.value, w)
        return self._md_lines

    def _render_md(self, text: str, w: int) -> list:
        if not text:
            return []
        buf = StringIO()
        con = Console(
            file=buf,
            width=w,
            color_system="standard",
            highlight=False,
            force_terminal=True,
        )
        con.print(_RichMarkdown(text), end="")
        return _parse_ansi_lines(buf.getvalue(), self.style)

    # ── draw ──────────────────────────────────────────────────────────────────

    def draw(self, canvas):
        if canvas.focused is self or not _RICH_OK:
            super().draw(canvas)
        else:
            self._draw_markdown(canvas)

    def _draw_markdown(self, canvas):
        w = self._clip_width or self.width
        if not self.value:
            canvas.write(
                self.abs_x,
                self.abs_y,
                self.placeholder[:w].ljust(w),
                self._placeholder_style(False),
            )
            return

        lines = self._rendered_lines(w)
        for row, spans in enumerate(lines):
            vy = self.abs_y + row
            if vy >= canvas.rows:
                break
            col = self.abs_x
            for text, style in spans:
                canvas.write(col, vy, text, style)
                col += len(text)
            fill = self.abs_x + w - col
            if fill > 0:
                canvas.write(col, vy, " " * fill, self.style)

    # ── natural_height ─────────────────────────────────────────────────────────

    def natural_height(self, scale: int) -> int:
        if _RICH_OK and self.value:
            w = self._clip_width or self.width
            return max(1, len(self._rendered_lines(w)))
        return super().natural_height(scale)
