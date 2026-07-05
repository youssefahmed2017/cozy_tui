import os

_FG = {
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "bright_black": "90",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}
_BG = {
    "black_bg": "40",
    "red_bg": "41",
    "green_bg": "42",
    "yellow_bg": "43",
    "blue_bg": "44",
    "magenta_bg": "45",
    "cyan_bg": "46",
    "white_bg": "47",
    "bright_black_bg": "100",
    "bright_red_bg": "101",
    "bright_green_bg": "102",
    "bright_yellow_bg": "103",
    "bright_blue_bg": "104",
    "bright_magenta_bg": "105",
    "bright_cyan_bg": "106",
    "bright_white_bg": "107",
}
_ST = {"bold": "1", "dim": "2", "italic": "3", "underline": "4", "blink": "5"}

# Cache: (fg, bg, styles_tuple) → ANSI escape string. Bounded so an app that
# animates through unbounded distinct truecolor values can't grow it forever;
# entries are cheap to recompute, so a full clear on overflow is fine.
_ESC_CACHE: dict = {}
_ESC_CACHE_MAX = 4096

# Output color depth. Truecolor/256 colors are downgraded to fit; "none"
# suppresses color entirely (text attributes like bold are still emitted).
_DEPTHS = ("none", "16", "256", "truecolor")

# Approximate RGB for the 16 named colors, paired with their fg SGR code
# (bg = code + 10). Used to snap truecolor/256 down to the nearest ANSI color.
_ANSI16_RGB = (
    (0, 0, 0, "30"),
    (128, 0, 0, "31"),
    (0, 128, 0, "32"),
    (128, 128, 0, "33"),
    (0, 0, 128, "34"),
    (128, 0, 128, "35"),
    (0, 128, 128, "36"),
    (192, 192, 192, "37"),
    (128, 128, 128, "90"),
    (255, 0, 0, "91"),
    (0, 255, 0, "92"),
    (255, 255, 0, "93"),
    (0, 0, 255, "94"),
    (255, 0, 255, "95"),
    (0, 255, 255, "96"),
    (255, 255, 255, "97"),
)


def _detect_depth() -> str:
    """Pick a color depth from the environment (honoring NO_COLOR / COLORTERM /
    TERM). Defaults to truecolor when the terminal doesn't advertise a level,
    since most modern terminals support it."""
    if os.environ.get("NO_COLOR") is not None:  # https://no-color.org
        return "none"
    if os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return "truecolor"
    if "256color" in os.environ.get("TERM", ""):
        return "256"
    return "truecolor"


_color_depth = _detect_depth()


def get_color_depth() -> str:
    """Return the active color depth: "none", "16", "256", or "truecolor"."""
    return _color_depth


def set_color_depth(depth: str) -> None:
    """Override the color depth ("none", "16", "256", or "truecolor"). "none"
    suppresses color (respecting NO_COLOR); the others downgrade truecolor and
    256-color values to fit. Clears the escape cache so the change takes effect."""
    global _color_depth
    if depth not in _DEPTHS:
        raise ValueError(f"depth must be one of {_DEPTHS}, got {depth!r}")
    _color_depth = depth
    _ESC_CACHE.clear()


def _hex_to_rgb(value: str):
    """Parse "#rrggbb" or shorthand "#rgb" into an (r, g, b) tuple."""
    h = value[1:]
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_256(r: int, g: int, b: int) -> int:
    """Nearest xterm-256 index for an RGB triple (grayscale ramp or 6×6×6 cube)."""
    if r == g == b:
        if r < 8:
            return 16
        if r > 248:
            return 231
        return 232 + round((r - 8) / 247 * 24)
    q = lambda v: round(v / 255 * 5)
    return 16 + 36 * q(r) + 6 * q(g) + q(b)


def _index256_to_rgb(n: int):
    """Approximate RGB for an xterm-256 palette index (inverse of the cube)."""
    if n < 16:
        return _ANSI16_RGB[n][:3]
    if n >= 232:
        v = 8 + (n - 232) * 10
        return (v, v, v)
    n -= 16
    conv = lambda x: 55 + x * 40 if x else 0
    return (conv(n // 36), conv((n % 36) // 6), conv(n % 6))


def _nearest16(r: int, g: int, b: int, is_bg: bool) -> str:
    """SGR code for the nearest of the 16 named colors to an RGB triple."""
    best = min(
        _ANSI16_RGB, key=lambda c: (c[0] - r) ** 2 + (c[1] - g) ** 2 + (c[2] - b) ** 2
    )
    return str(int(best[3]) + 10) if is_bg else best[3]


# fg SGR code → RGB, for resolving named colors back to a triple.
_CODE_RGB = {code: (r, g, b) for r, g, b, code in _ANSI16_RGB}


def resolve_rgb(color):
    """Resolve a color spec — a named color, "#rrggbb"/"#rgb", "rgb(R,G,B)", or
    "color(N)" — to an ``(r, g, b)`` tuple, or ``None`` if it can't be resolved
    (e.g. ``None`` or an unknown name)."""
    if not color:
        return None
    if color.startswith("#"):
        return _hex_to_rgb(color)
    if color.startswith("rgb("):
        return tuple(int(x) for x in color[4:-1].split(","))
    if color.startswith("color("):
        return _index256_to_rgb(int(color[6:-1].strip()))
    if color in _FG:
        return _CODE_RGB.get(_FG[color])
    return None


def tint(color, toward, amount: float):
    """Blend ``color`` toward ``toward`` by ``amount`` (0.0–1.0), returning an
    ``"rgb(R,G,B)"`` string. Mirrors Textual's ``tint:`` — overlaying ``toward``
    at ``amount`` opacity. If ``color`` can't be resolved it is returned as-is."""
    c = resolve_rgb(color)
    if c is None:
        return color
    t = resolve_rgb(toward) or (0, 0, 0)
    blended = tuple(round(a * (1 - amount) + b * amount) for a, b in zip(c, t))
    return f"rgb({blended[0]},{blended[1]},{blended[2]})"


def _truecolor_sgr(r: int, g: int, b: int, is_bg: bool) -> str:
    """Emit an RGB triple at the current depth (24-bit, 256, or nearest-16)."""
    if _color_depth == "truecolor":
        return f"{'48' if is_bg else '38'};2;{r};{g};{b}"
    if _color_depth == "256":
        return f"{'48' if is_bg else '38'};5;{_rgb_to_256(r, g, b)}"
    return _nearest16(r, g, b, is_bg)


def _index_sgr(n: int, is_bg: bool) -> str:
    """Emit a 256-palette index at the current depth (downgraded to 16 if needed)."""
    if _color_depth in ("256", "truecolor"):
        return f"{'48' if is_bg else '38'};5;{n}"
    return _nearest16(*_index256_to_rgb(n), is_bg)


def _color_codes(value: str, is_bg: bool) -> str:
    """SGR parameter(s) for one color at the active depth. Handles named colors,
    "rgb(R,G,B)" and "#rrggbb"/"#rgb" truecolor, and "color(N)" indexed-256."""
    table = _BG if is_bg else _FG
    if value in table:
        return table[value]
    if value.startswith("rgb("):
        r, g, b = (int(x) for x in value[4:-1].split(","))
        return _truecolor_sgr(r, g, b, is_bg)
    if value.startswith("#"):
        return _truecolor_sgr(*_hex_to_rgb(value), is_bg)
    if value.startswith("color("):
        return _index_sgr(int(value[6:-1].strip()), is_bg)
    return ""


def style_esc(fg, bg, styles) -> str:
    """Return the ANSI SGR escape string for the given style triple.

    Results are cached (keyed on the triple; the cache is cleared when the color
    depth changes). fg/bg accept named colors (e.g. "blue"), "rgb(R,G,B)" or
    "#rrggbb"/"#rgb" truecolor, or "color(N)" indexed-256 palette entries; they
    are downgraded to the active depth (see set_color_depth). At depth "none"
    color is suppressed but text attributes (bold/underline/…) still apply.
    """
    no_color = _color_depth == "none"
    key = (fg, bg, styles)
    esc = _ESC_CACHE.get(key)
    if esc is not None:
        return esc
    codes = []
    if bg and not no_color:
        code = _color_codes(bg, is_bg=True)
        if code:
            codes.append(code)
    if fg and not no_color:
        code = _color_codes(fg, is_bg=False)
        if code:
            codes.append(code)
    for s in styles:
        if s in _ST:
            codes.append(_ST[s])
    esc = f"\033[0;{';'.join(codes)}m" if codes else "\033[0m"
    if len(_ESC_CACHE) >= _ESC_CACHE_MAX:
        _ESC_CACHE.clear()
    _ESC_CACHE[key] = esc
    return esc
