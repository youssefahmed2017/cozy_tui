"""MarkdownInput: Input with live Rich Markdown preview when not focused."""

from __future__ import annotations

from cozy_tui.widgets.input import Input
from cozy_tui.style import Style

try:
    from rich.console import Console
    from rich.markdown import Markdown as _RichMarkdown
    from rich.color import ColorType
    _RICH_OK = True
except ImportError:
    _RICH_OK = False

# ── Rich → cozy_tui colour mapping ───────────────────────────────────────────

_ANSI16 = [
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "bright_black", "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
]

# Canonical RGB values for each of the 16 ANSI colours (used for nearest-match)
_ANSI16_RGB = [
    (0,   0,   0),    # black
    (170, 0,   0),    # red
    (0,   170, 0),    # green
    (170, 170, 0),    # yellow
    (0,   0,   170),  # blue
    (170, 0,   170),  # magenta
    (0,   170, 170),  # cyan
    (170, 170, 170),  # white
    (85,  85,  85),   # bright_black
    (255, 85,  85),   # bright_red
    (85,  255, 85),   # bright_green
    (255, 255, 85),   # bright_yellow
    (85,  85,  255),  # bright_blue
    (255, 85,  255),  # bright_magenta
    (85,  255, 255),  # bright_cyan
    (255, 255, 255),  # bright_white
]


def _eight_bit_to_rgb(n: int) -> tuple:
    """Convert a 256-colour palette index to (R, G, B)."""
    if n < 16:
        return _ANSI16_RGB[n]
    if n < 232:
        n -= 16
        r, g, b = n // 36, (n // 6) % 6, n % 6
        def _v(x): return 0 if x == 0 else 55 + x * 40
        return _v(r), _v(g), _v(b)
    v = 8 + (n - 232) * 10   # grayscale ramp
    return v, v, v


def _nearest_ansi16(r: int, g: int, b: int) -> str:
    """Return the closest ANSI-16 colour name for an arbitrary RGB value."""
    return _ANSI16[
        min(
            range(16),
            key=lambda i: (
                (r - _ANSI16_RGB[i][0]) ** 2
                + (g - _ANSI16_RGB[i][1]) ** 2
                + (b - _ANSI16_RGB[i][2]) ** 2
            ),
        )
    ]


def _cozy_color(rich_color) -> str | None:
    """Map any Rich Color to a cozy_tui colour name, or None to inherit."""
    if rich_color is None or rich_color.type == ColorType.DEFAULT:
        return None
    if rich_color.type == ColorType.STANDARD:
        n = rich_color.number
        return _ANSI16[n] if n is not None and 0 <= n < 16 else None
    if rich_color.type == ColorType.EIGHT_BIT:
        n = rich_color.number
        if n is None:
            return None
        return _ANSI16[n] if n < 16 else _nearest_ansi16(*_eight_bit_to_rgb(n))
    if rich_color.type == ColorType.TRUECOLOR:
        t = rich_color.triplet
        return _nearest_ansi16(t.red, t.green, t.blue) if t else None
    return None


def _to_cozy_style(rich_style, base: Style) -> Style:
    """Convert a Rich Segment Style to a cozy_tui Style, inheriting from base."""
    if not rich_style:
        return base
    fg = _cozy_color(rich_style.color)   if rich_style.color   is not None else base.fg
    bg = _cozy_color(rich_style.bgcolor) if rich_style.bgcolor is not None else base.bg
    st = list(base.styles)
    for attr, name in (
        ("bold", "bold"), ("italic", "italic"),
        ("underline", "underline"), ("dim", "dim"),
    ):
        if getattr(rich_style, attr, False) and name not in st:
            st.append(name)
    return Style(fg=fg, bg=bg, styles=st)


def _emit(lines: list, text: str, style: Style) -> None:
    """Append text to lines, creating a new line entry on each '\\n'."""
    if "\n" in text:
        parts = text.split("\n")
        for i, part in enumerate(parts):
            if part:
                lines[-1].append((part, style))
            if i < len(parts) - 1:
                lines.append([])
    elif text:
        lines[-1].append((text, style))


# ── widget ────────────────────────────────────────────────────────────────────

class MarkdownInput(Input):
    """Input widget that renders content as a live Markdown preview when unfocused.

    All editing behaviour (cursor, typing, backspace, home/end, multiline,
    wrapping, masking) is inherited unchanged from Input.  Only draw() is
    overridden:

    - focused   → raw text with cursor  (standard Input rendering)
    - unfocused → Rich Markdown preview

    Rendering pipeline::

        self.value
            ↓
        Console.render()       # yields Segment(text, rich_style)
            ↓
        _to_cozy_style()       # STANDARD/EIGHT_BIT/TRUECOLOR → nearest ANSI-16 name
            ↓
        canvas.write()

    No ANSI is emitted or parsed.  Rich's Segment objects already carry
    typed colour/style info, so the conversion goes Style → Style directly.

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
        # color_system="truecolor" ensures style.color / style.bgcolor are always
        # populated on segments so _cozy_color() can map them to ANSI-16 names.
        con = Console(width=w, color_system="truecolor", highlight=False, markup=False)
        lines: list[list[tuple[str, Style]]] = [[]]
        for seg in con.render(_RichMarkdown(text)):
            if not seg.text:
                continue
            _emit(lines, seg.text, _to_cozy_style(seg.style, self.style))
        return lines

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
