from cozy_tui._presets import CATEGORIES, PRESETS
from cozy_tui.state import State
from cozy_tui.style import Style

# mode name -> preset role values. "style" is the base App canvas
# fg/bg; the rest are named colors the rest of this module's Theme reads
# individual widgets from (selection_style(), Toast's level colors, ...).


class Theme:
    """A named bundle of the colors this library's shared visual language
    draws from: the base app ``style`` (fg/bg), an ``accent`` color for
    emphasis, semantic ``success``/``warning``/``error``/``info`` colors
    (what :class:`~cozy_tui.widgets.Toast` picks its border/icon color from),
    a ``muted`` color for secondary text, and the ``selection_fg``/
    ``selection_bg`` pair the focused-row highlight is built from --
    :func:`~cozy_tui.style.selection_style` (shared by ListView, RadioSet,
    CheckList, Table, Tree, Dropdown, Checkbox, RightClickMenu, Slider, and
    MenuBar) reads it from the active theme, so switching themes re-colors
    every one of those widgets at once.

    Build from a built-in ``mode`` (one of ``Theme.MODES`` -- over 30 built-in
    presets, e.g. ``"default"``, ``"monochromatic"``, ``"ocean"``, ``"dracula"``,
    ``"cyberpunk"``, ..., case-insensitive) -- or override the base look directly with your own
    ``style=Style(...)``, and/or override any individual role -- anything you
    don't override falls back to the mode's preset::

        Theme(mode="monochromatic")
        Theme(style=Style(fg="white", bg="#1a1a2e"))       # keeps default's accents
        Theme(mode="monochromatic", accent="bright_green")  # one role overridden

    A theme does nothing on its own until it's made active: call
    ``theme.activate()`` (or the equivalent module function,
    ``set_theme(theme)``).

    **Switching is live.** An ``App()`` built with no explicit ``style=``
    re-colors its canvas on a later switch and forces a full repaint, and
    anything reading the theme at draw time -- ``selection_style()`` (every
    list/table/tree highlight), the modal scrim, `Toast` colors, `Bindings`,
    the dialogs' accent -- follows with it. What does *not* change is a color
    the app author chose explicitly: an ``App(style=Style(...))`` or a
    ``Widget(style=Style(...))`` keeps exactly what it was given, since a theme
    switch has no business discarding a deliberate choice. Register your own
    reaction with :func:`on_theme_change`.
    """

    MODES = tuple(PRESETS)
    # display category name -> mode names in it (e.g. "Nature" ->
    # ("ocean", "forest", ...)), for anything that wants to group the
    # ever-growing preset list instead of showing it as one flat list --
    # see cozy_tui.themes (`python -m cozy_tui.themes`).
    CATEGORIES = {name: tuple(modes) for name, modes in CATEGORIES.items()}

    def __init__(
        self,
        mode="default",
        *,
        style=None,
        accent=None,
        muted=None,
        info=None,
        success=None,
        warning=None,
        error=None,
        selection_fg=None,
        selection_bg=None,
    ):
        mode = mode.lower()
        if mode not in PRESETS:
            raise ValueError(f"mode must be one of {self.MODES}, got {mode!r}")
        preset = PRESETS[mode]
        self.mode = mode
        self.style = style if style is not None else preset["style"]
        self.accent = accent or preset["accent"]
        self.muted = muted or preset["muted"]
        self.info = info or preset["info"]
        self.success = success or preset["success"]
        self.warning = warning or preset["warning"]
        self.error = error or preset["error"]
        self.selection_fg = selection_fg or preset["selection_fg"]
        self.selection_bg = selection_bg or preset["selection_bg"]

    def selection_style(self, dim: bool = False) -> Style:
        """The focused-row highlight: a solid inverted block, or (``dim=True``)
        the softer bold-foreground-only variant for "selected but not the
        cursor row". Same styles :func:`~cozy_tui.style.selection_style`
        returns for the *active* theme -- call that instead unless you
        specifically need a non-active theme's colors."""
        if dim:
            return Style(fg=self.selection_bg, styles=["bold"])
        return Style(fg=self.selection_fg, bg=self.selection_bg, styles=["bold"])

    def activate(self) -> "Theme":
        """Make this the process-wide active theme. Returns self for chaining,
        e.g. ``app_theme = Theme(mode="monochromatic").activate()``."""
        set_theme(self)
        return self

    def __repr__(self):
        return f"Theme(mode={self.mode!r})"


#: The process-wide active theme, as an observable :class:`~cozy_tui.state.State`
#: so anything holding resolved colors can re-derive them on a switch (see
#: :func:`on_theme_change`). Read it through `get_theme()`/`set_theme()` rather
#: than touching it directly.
_active_theme = State(Theme())


def get_theme() -> Theme:
    """Return the process-wide active theme (``Theme()``, i.e. mode="default",
    until something calls :func:`set_theme`)."""
    return _active_theme.value


def set_theme(theme: Theme) -> None:
    """Make ``theme`` the process-wide active theme, and notify everything
    registered via :func:`on_theme_change` -- which is how a running `App`
    re-colors its canvas mid-session instead of keeping the old theme's
    background until it restarts."""
    _active_theme.set(theme)


def on_theme_change(callback, *, owner=None):
    """Call ``callback(theme)`` whenever the active theme changes. Returns the
    callback, for :func:`unsubscribe_theme`.

    ``owner`` makes the subscription weak in that object -- `App` passes itself,
    so a discarded app doesn't stay alive (and keep re-coloring) through this
    module-level state for the rest of the process.
    """
    return _active_theme.subscribe(callback, owner=owner)


def unsubscribe_theme(callback) -> None:
    """Remove a callback registered with :func:`on_theme_change`."""
    _active_theme.unsubscribe(callback)
