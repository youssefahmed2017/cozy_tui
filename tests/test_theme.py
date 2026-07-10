import pytest

from cozy_tui import App, Style, Theme, get_theme, set_theme
from cozy_tui.events import Key
from cozy_tui.style import selection_style
from cozy_tui.widgets import ThemePalette
from cozy_tui.widgets.display.toast import Toast


@pytest.fixture(autouse=True)
def _restore_default_theme():
    # Theme is process-wide global state; every test starts and ends on the
    # default theme so switching it in one test can't leak into another.
    original = get_theme()
    yield
    set_theme(original)


def test_default_theme_matches_the_librarys_historical_hardcoded_colors():
    theme = Theme()
    assert theme.mode == "default"
    assert theme.selection_fg == "black" and theme.selection_bg == "white"
    assert theme.accent == "bright_cyan"
    assert theme.success == "bright_green"
    assert theme.warning == "bright_yellow"
    assert theme.error == "bright_red"


def test_mode_is_case_insensitive():
    assert Theme(mode="Monochromatic").mode == "monochromatic"
    assert Theme(mode="DEFAULT").mode == "default"


def test_invalid_mode_raises():
    with pytest.raises(ValueError):
        Theme(mode="nonexistent")


def test_style_override_keeps_the_rest_of_the_preset():
    custom = Style(fg="white", bg="#1a1a2e")
    theme = Theme(style=custom)
    assert theme.style is custom
    assert theme.accent == "bright_cyan"  # untouched: still the default preset


def test_individual_role_override():
    theme = Theme(accent="bright_green", error="white")
    assert theme.accent == "bright_green"
    assert theme.error == "white"
    assert theme.success == "bright_green"  # untouched: still the default preset
    assert theme.warning == "bright_yellow"  # untouched: still the default preset


def test_monochromatic_preset_differs_from_default():
    default = Theme(mode="default")
    mono = Theme(mode="monochromatic")
    assert mono.accent != default.accent
    assert mono.success != default.success


def test_theme_selection_style_solid_and_dim():
    theme = Theme(selection_fg="green", selection_bg="magenta")
    solid = theme.selection_style()
    assert solid.fg == "green" and solid.bg == "magenta_bg" and "bold" in solid.styles
    dim = theme.selection_style(dim=True)
    assert dim.fg == "magenta" and dim.bg is None and "bold" in dim.styles


def test_get_theme_defaults_and_set_theme_switches_it():
    assert get_theme().mode == "default"
    custom = Theme(mode="monochromatic")
    set_theme(custom)
    assert get_theme() is custom


def test_activate_sets_and_returns_self():
    custom = Theme(mode="monochromatic")
    result = custom.activate()
    assert result is custom
    assert get_theme() is custom


def test_selection_style_function_reads_the_active_theme():
    default_solid = selection_style()
    assert default_solid.fg == "black" and default_solid.bg == "white_bg"

    Theme(selection_fg="red", selection_bg="blue").activate()
    switched = selection_style()
    assert switched.fg == "red" and switched.bg == "blue_bg"


def test_app_with_no_explicit_style_uses_the_active_theme():
    Theme(style=Style(fg="green", bg="magenta")).activate()
    app = App(full=False, size="100x50")
    assert app.style.fg == "green" and app.style.bg == "magenta_bg"


def test_app_style_instances_are_independent_across_apps():
    app1 = App(full=False, size="100x50")
    app2 = App(full=False, size="100x50")
    assert app1.style is not app2.style
    app1.style.fg = "red"
    assert app2.style.fg != "red"


def test_explicit_app_style_overrides_the_active_theme():
    Theme(style=Style(fg="green", bg="magenta")).activate()
    app = App(full=False, size="100x50", style=Style(fg="yellow", bg="black"))
    assert app.style.fg == "yellow" and app.style.bg == "black_bg"


def test_toast_color_follows_the_active_theme():
    default_toast = Toast("hi", level="warning")
    assert default_toast.color == "bright_yellow"

    Theme(mode="monochromatic").activate()
    mono_toast = Toast("hi", level="warning")
    assert mono_toast.color == "bright_white"


def test_toast_unknown_level_falls_back_to_info():
    toast = Toast("hi", level="bogus")
    assert toast.level == "info"
    assert toast.color == get_theme().info


def test_toast_icon_still_defaults_per_level_and_can_be_overridden():
    assert Toast("hi", level="success").icon == "✓"
    assert Toast("hi", level="success", icon="★").icon == "★"


# ── App.cycle_theme() (no longer bound by default) ──────────────────────────


def test_cycle_theme_advances_through_every_mode_and_wraps():
    set_theme(Theme(mode=Theme.MODES[0]))
    app = App(full=False, size="100x50")
    seen = [get_theme().mode]
    for _ in range(len(Theme.MODES)):
        app.cycle_theme()
        seen.append(get_theme().mode)
    assert seen == list(Theme.MODES) + [Theme.MODES[0]]  # wraps back to the start


def test_cycle_theme_mutates_app_style_in_place():
    set_theme(Theme(mode="default"))
    app = App(full=False, size="100x50")
    style_obj = app.style
    app.cycle_theme()
    assert app.style is style_obj  # same object, not replaced
    next_theme = get_theme()
    assert app.style.fg == next_theme.style.fg
    assert app.style.bg == next_theme.style.bg


def test_cycle_theme_forces_a_full_render():
    # _full_render_pending starts True (every app's first frame is a full
    # render) and is only cleared by render() -- which writes real escape
    # codes to stdout, so drive it directly rather than calling render().
    app = App(full=False, size="100x50", style=Style(fg="white", bg="black"))
    app._full_render_pending = False
    app.cycle_theme()
    assert app._full_render_pending is True


# ── Ctrl+T / App.open_theme_palette() ────────────────────────────────────────


def test_ctrl_t_is_bound_and_labeled():
    app = App(full=False, size="100x50")
    assert Key.CTRL_T in app._key_handlers
    assert app._key_handlers[Key.CTRL_T] == app.open_theme_palette
    assert app._bindings[Key.CTRL_T] == ("Change theme", "App")
    assert Key.CTRL_T == Key.ctrl("t")
    assert Key.label(Key.CTRL_T) == "Ctrl+T"


def test_ctrl_t_opens_a_theme_palette_and_focuses_it():
    app = App(full=False, size="100x50", style=Style(fg="white", bg="black"))
    app.snapshot()
    app._dispatch_input(Key.CTRL_T)
    app.snapshot()
    assert len(app._overlays) == 1
    palette = app._overlays[-1].widget
    assert isinstance(palette, ThemePalette)
    assert app.focused is palette


def test_esc_cancels_the_palette_without_changing_the_theme():
    set_theme(Theme(mode="default"))
    app = App(full=False, size="100x50", style=Style(fg="white", bg="black"))
    app.snapshot()
    app._dispatch_input(Key.CTRL_T)
    app.snapshot()
    app._dispatch_input(Key.ESC)
    app.snapshot()
    assert app._overlays == []
    assert get_theme().mode == "default"


def test_typing_filters_and_enter_picks_the_match():
    set_theme(Theme(mode="default"))
    app = App(full=False, size="100x50", style=Style(fg="white", bg="black"))
    app.snapshot()
    app._dispatch_input(Key.CTRL_T)
    app.snapshot()
    for ch in "ocea":
        app._dispatch_input(ch)
    app.snapshot()
    assert app._overlays[-1].widget._matches == ["ocean"]

    app._dispatch_input(Key.ENTER)
    app.snapshot()
    assert get_theme().mode == "ocean"
    assert app._overlays == []
    assert app.style.fg == get_theme().style.fg
    assert app.style.bg == get_theme().style.bg


def test_backspace_widens_the_filter_again():
    app = App(full=False, size="100x50", style=Style(fg="white", bg="black"))
    app.snapshot()
    app._dispatch_input(Key.CTRL_T)
    app.snapshot()
    palette = app._overlays[-1].widget
    for ch in "zzz":  # matches nothing
        app._dispatch_input(ch)
    app.snapshot()
    assert palette._matches == []
    for _ in range(3):
        app._dispatch_input(Key.BACKSPACE)
    app.snapshot()
    assert palette.query == ""
    assert palette._matches == list(Theme.MODES)


def test_click_on_a_row_picks_it_immediately():
    set_theme(Theme(mode="default"))
    app = App(full=False, size="100x50", style=Style(fg="white", bg="black"))
    app.snapshot()
    app._dispatch_input(Key.CTRL_T)
    app.snapshot()
    palette = app._overlays[-1].widget
    row_y = palette.abs_y + 2 + 2  # 3rd row (index 2) = Theme.MODES[2]
    from cozy_tui.events import MouseClick

    app._dispatch_input(MouseClick(palette.abs_x + 3, row_y, 0))
    app.snapshot()
    assert get_theme().mode == Theme.MODES[2]
    assert app._overlays == []


def test_ctrl_t_can_be_overridden_by_the_users_own_binding():
    app = App(full=False, size="100x50")
    calls = []
    app.on_key(Key.CTRL_T, lambda: calls.append("mine"), description="My thing")
    app._dispatch_input(Key.CTRL_T)
    assert calls == ["mine"]
    assert app._bindings[Key.CTRL_T] == ("My thing", None)


# ── ThemePalette (direct, no App) ────────────────────────────────────────────


def test_palette_starts_positioned_on_the_current_theme():
    p = ThemePalette(Theme.MODES, current=Theme.MODES[3])
    assert p._index == 3


def test_palette_unknown_current_falls_back_to_the_first_match():
    p = ThemePalette(Theme.MODES, current="not-a-real-mode")
    assert p._index == 0


def test_palette_up_down_clamp_without_wrapping():
    p = ThemePalette(Theme.MODES)
    p.on_key(Key.UP)  # already at 0, stays put
    assert p._index == 0
    for _ in range(len(Theme.MODES) + 5):
        p.on_key(Key.DOWN)
    assert p._index == len(Theme.MODES) - 1  # clamped, not wrapped


def test_palette_home_end():
    p = ThemePalette(Theme.MODES)
    p.on_key(Key.DOWN)
    p.on_key(Key.END)
    assert p._index == len(Theme.MODES) - 1
    p.on_key(Key.HOME)
    assert p._index == 0


def test_palette_on_select_fires_with_the_highlighted_match():
    picked = []
    p = ThemePalette(Theme.MODES, on_select=picked.append)
    p.on_key(Key.DOWN)
    p.on_key(Key.ENTER)
    assert picked == [Theme.MODES[1]]


def test_palette_empty_matches_do_not_crash_navigation_or_enter():
    picked = []
    p = ThemePalette(Theme.MODES, on_select=picked.append)
    for ch in "not a real theme name at all":
        p.on_key(ch)
    assert p._matches == []
    p.on_key(Key.UP)
    p.on_key(Key.DOWN)
    p.on_key(Key.ENTER)  # no-op: nothing to pick
    assert picked == []
