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

    @property
    def raw_bg(self):
        """This style's background with the internal ``_bg`` suffix stripped, so
        it can be handed to a fresh ``Style(bg=...)`` (which re-applies the
        suffix). Returns ``None``/self-describing colors unchanged."""
        if self.bg and self.bg.endswith("_bg"):
            return self.bg[:-3]
        return self.bg


def selection_style(dim: bool = False) -> Style:
    """The focused-row highlight style shared by ListView, RadioSet, CheckList,
    Table, Tree, Dropdown, Checkbox, RightClickMenu, Slider, and MenuBar: a
    solid inverted block for the item under the cursor. `dim=True` gives the
    softer variant used for "selected but not the cursor row" (bold
    foreground, no background fill). Colors come from the active theme's
    `selection_fg`/`selection_bg` (see `cozy_tui.theme`) -- imported locally
    to avoid a circular import, since theme.py itself builds on Style."""
    from cozy_tui.theme import get_theme

    return get_theme().selection_style(dim)


class Cell:
    __slots__ = ("char", "style")

    def __init__(self, char: str, style: Style) -> None:
        self.char = char
        self.style = style
