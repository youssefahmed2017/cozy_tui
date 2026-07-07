"""Shared Rich -> cozy_tui color/style bridging, used by every widget that
borrows Rich's rendering (`Markdown`, `TracebackView`) instead of
reimplementing syntax highlighting or markup parsing from scratch.

Colors are mapped down to the 16 named ANSI colors (not raw truecolor hex),
matching the rest of cozy_tui's `Style` system regardless of Rich's original
color space — the palette a name actually resolves to is then handled by
`ansi.py`'s own depth-aware truecolor/256/16 downgrading, same as any other
named color a user writes by hand.
"""

from rich.color import ColorType

from cozy_tui.style import Style

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


def cozy_color(rich_color) -> str | None:
    """Resolve a `rich.color.Color` (standard/8-bit/truecolor/default) to a
    cozy_tui named color, or `None` for "use the terminal default"."""
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


def to_cozy_style(rich_style, base: Style | None = None) -> Style:
    """Convert a resolved `rich.style.Style` (or `None`, for a plain/unstyled
    segment) into a cozy_tui `Style`, falling back to `base` for anything
    Rich didn't set."""
    base = base if base is not None else Style()
    if not rich_style:
        return base
    fg = cozy_color(rich_style.color) if rich_style.color is not None else base.fg
    bg = cozy_color(rich_style.bgcolor) if rich_style.bgcolor is not None else base.bg
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
