import sys

# Best-effort UTF-8 output. Guarded because sys.stdout may be None (pythonw.exe)
# or a stream without .reconfigure (already-wrapped / redirected), in which case
# importing cozy_tui must not crash.
_reconfigure = getattr(sys.stdout, "reconfigure", None)
if _reconfigure is not None:
    try:
        _reconfigure(encoding="utf-8")
    except (ValueError, OSError):
        pass


class Style:
    __slots__ = ("fg", "bg", "styles")

    # Color forms that are self-describing and must not get the named "_bg"
    # suffix (which only applies to the 16 bare color names).
    _NON_NAMED_BG = ("rgb(", "#", "color(")

    def __init__(self, fg=None, bg=None, styles=None):
        self.fg = fg
        if bg and not bg.startswith(self._NON_NAMED_BG):
            self.bg = f"{bg}_bg"
        else:
            self.bg = bg  # None, "rgb(R,G,B)", "#rrggbb", or "color(N)"
        self.styles = tuple(styles) if styles else ()


class Cell:
    __slots__ = ("char", "style")

    def __init__(self, char: str, style: Style) -> None:
        self.char = char
        self.style = style
