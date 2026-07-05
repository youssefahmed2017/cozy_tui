"""Markdown widget: renders Rich Markdown text into the canvas."""

from __future__ import annotations

from rich.color import ColorType
from rich.console import Console
from rich.markdown import Markdown as _RichMarkdown

from cozy_tui.style import Style
from cozy_tui.widget import Widget

# ── Rich → cozy_tui colour mapping ───────────────────────────────────────────

_ANSI16 = [
    "black",
    "red",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "white",
    "bright_black",
    "bright_red",
    "bright_green",
    "bright_yellow",
    "bright_blue",
    "bright_magenta",
    "bright_cyan",
    "bright_white",
]

_ANSI16_RGB = [
    (0, 0, 0),
    (170, 0, 0),
    (0, 170, 0),
    (170, 170, 0),
    (0, 0, 170),
    (170, 0, 170),
    (0, 170, 170),
    (170, 170, 170),
    (85, 85, 85),
    (255, 85, 85),
    (85, 255, 85),
    (255, 255, 85),
    (85, 85, 255),
    (255, 85, 255),
    (85, 255, 255),
    (255, 255, 255),
]


def _eight_bit_to_rgb(n: int) -> tuple:
    if n < 16:
        return _ANSI16_RGB[n]
    if n < 232:
        n -= 16
        r, g, b = n // 36, (n // 6) % 6, n % 6

        def _v(x):
            return 0 if x == 0 else 55 + x * 40

        return _v(r), _v(g), _v(b)
    v = 8 + (n - 232) * 10
    return v, v, v


def _nearest_ansi16(r: int, g: int, b: int) -> str:
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
    if not rich_style:
        return base
    fg = _cozy_color(rich_style.color) if rich_style.color is not None else base.fg
    bg = _cozy_color(rich_style.bgcolor) if rich_style.bgcolor is not None else base.bg
    st = list(base.styles)
    for attr, name in (
        ("bold", "bold"),
        ("italic", "italic"),
        ("underline", "underline"),
        ("dim", "dim"),
    ):
        if getattr(rich_style, attr, False) and name not in st:
            st.append(name)
    return Style(fg=fg, bg=bg, styles=st)


def _emit(lines: list, text: str, style: Style) -> None:
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


class Markdown(Widget):
    """Renders a Markdown string as styled Rich text.

    Focused state is irrelevant — this widget is not interactive.
    Requires ``rich`` (``pip install rich``); falls back to plain text if absent.
    """

    def __init__(self, x, y, width, value="", *, placeholder="", style=None):
        super().__init__(x, y, style)
        self.width = width
        self.value = value
        self.placeholder = placeholder
        self._md_cache_key: tuple | None = None
        self._md_lines: list | None = None
        self.laps = True

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
        con = Console(width=w, color_system="truecolor", highlight=False, markup=False)
        lines: list[list[tuple[str, Style]]] = [[]]
        for seg in con.render(_RichMarkdown(text)):
            if not seg.text:
                continue
            _emit(lines, seg.text, _to_cozy_style(seg.style, self.style))
        return lines

    # ── placeholder style (overridden by Input's version in MarkdownInput) ───

    def _placeholder_style(self, focused: bool = False) -> Style:
        raw_bg = self.style.raw_bg
        return Style(fg=self.style.fg, bg=raw_bg, styles=["dim"])

    # ── draw ──────────────────────────────────────────────────────────────────

    def _draw_markdown(self, canvas) -> None:
        w = self._clip_width or self.width
        if not self.value:
            if self.placeholder:
                ph_style = self._placeholder_style(False)
                for row_i, ph_line in enumerate(self.placeholder.split("\n")):
                    canvas.write(
                        self.abs_x,
                        self.abs_y + row_i,
                        ph_line[:w].ljust(w),
                        ph_style,
                    )
            else:
                canvas.write(self.abs_x, self.abs_y, " " * w, self.style)
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

    def draw(self, canvas) -> None:
        self._draw_markdown(canvas)

    # ── layout ────────────────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        return self.width

    def natural_height(self, scale) -> int:
        if self.value:
            w = self._clip_width or self.width
            return max(1, len(self._rendered_lines(w)))
        return 1

    def contains(self, col: int, row: int) -> bool:
        w = self._clip_width or self.width
        h = self.natural_height(1)
        return self.abs_x <= col < self.abs_x + w and self.abs_y <= row < self.abs_y + h
