_FG = {
    "black":          "30",
    "red":            "31",
    "green":          "32",
    "yellow":         "33",
    "blue":           "34",
    "magenta":        "35",
    "cyan":           "36",
    "white":          "37",
    "bright_black":   "90",
    "bright_red":     "91",
    "bright_green":   "92",
    "bright_yellow":  "93",
    "bright_blue":    "94",
    "bright_magenta": "95",
    "bright_cyan":    "96",
    "bright_white":   "97",
}
_BG = {
    "black_bg":          "40",
    "red_bg":            "41",
    "green_bg":          "42",
    "yellow_bg":         "43",
    "blue_bg":           "44",
    "magenta_bg":        "45",
    "cyan_bg":           "46",
    "white_bg":          "47",
    "bright_black_bg":   "100",
    "bright_red_bg":     "101",
    "bright_green_bg":   "102",
    "bright_yellow_bg":  "103",
    "bright_blue_bg":    "104",
    "bright_magenta_bg": "105",
    "bright_cyan_bg":    "106",
    "bright_white_bg":   "107",
}
_ST = {"bold": "1", "dim": "2", "italic": "3", "underline": "4", "blink": "5"}

# Cache: (fg, bg, styles_tuple) → ANSI escape string
_ESC_CACHE: dict = {}


def style_esc(fg, bg, styles) -> str:
    """Return the ANSI SGR escape string for the given style triple.

    Results are cached permanently since the number of distinct styles in a
    typical TUI is small (< 100) and styles are reused every frame.
    """
    key = (fg, bg, styles)
    esc = _ESC_CACHE.get(key)
    if esc is not None:
        return esc
    codes = []
    if bg in _BG:
        codes.append(_BG[bg])
    if fg in _FG:
        codes.append(_FG[fg])
    for s in styles:
        if s in _ST:
            codes.append(_ST[s])
    esc = f"\033[0;{';'.join(codes)}m" if codes else "\033[0m"
    _ESC_CACHE[key] = esc
    return esc
