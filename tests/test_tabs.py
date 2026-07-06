"""The Tabs container: focus order, switching, and rendering."""

from cozy_tui import App, Style
from cozy_tui.widgets import Button, Input, Label, Tabs


def make_app():
    return App(full=False, size="800x300", style=Style(fg="white", bg="black"))


def test_add_tab_returns_panel_and_holds_widgets():
    tabs = Tabs(0, 0, "600x200")
    panel = tabs.add_tab("One", Label(1, 1, "hello"))
    assert tabs.selected_title == "One"
    assert tabs.panel(0) is panel
    assert len(panel.children) == 1


def test_children_expose_only_the_active_panel():
    tabs = Tabs(0, 0, "600x200")
    p0 = tabs.add_tab("One")
    p1 = tabs.add_tab("Two")
    assert tabs.children == [tabs._bar, p0]
    tabs.select(1)
    assert tabs.children == [tabs._bar, p1]


def test_focus_order_is_bar_then_active_panel_controls():
    app = make_app()
    tabs = Tabs(0, 0, "600x200")
    a = tabs.add_tab("One", Button(1, 1, "A")).children[0]
    tabs.add_tab("Two", Button(1, 1, "B"), Input(1, 3, 10))
    app.add(tabs)

    focusables = app._collect_focusables()
    assert focusables[0] is tabs._bar  # Tab lands on the strip first
    assert focusables[1] is a          # then dives into the active panel
    assert len(focusables) == 2        # tab Two's controls are not reachable yet

    tabs.select(1)
    focusables = app._collect_focusables()
    assert focusables[0] is tabs._bar
    assert len(focusables) == 3  # bar + Button B + Input


def test_select_clamps_and_fires_on_change():
    tabs = Tabs(0, 0, "600x200")
    tabs.add_tab("One")
    tabs.add_tab("Two")
    tabs.add_tab("Three")
    seen = []
    tabs.on_change(seen.append)

    tabs.select(2)
    tabs.select(99)  # clamped to 2 -> no change, no fire
    tabs.select(-5)  # clamped to 0
    assert tabs.active == 0
    assert seen == [2, 0]


def test_bar_arrow_keys_switch_tabs():
    from cozy_tui.events import Key

    tabs = Tabs(0, 0, "600x200")
    tabs.add_tab("One")
    tabs.add_tab("Two")
    tabs.add_tab("Three")
    tabs._bar.on_key(Key.RIGHT)
    assert tabs.active == 1
    tabs._bar.on_key(Key.END)
    assert tabs.active == 2
    tabs._bar.on_key(Key.LEFT)
    assert tabs.active == 1
    tabs._bar.on_key(Key.HOME)
    assert tabs.active == 0


def test_click_on_a_tab_title_selects_it():
    app = make_app()
    tabs = Tabs(0, 0, "600x200")
    tabs.add_tab("Alpha")
    tabs.add_tab("Bravo")
    app.add(tabs)
    app.snapshot()  # populate the bar's click segments via a draw pass

    # Second segment (" Bravo ") — click inside its local x-range.
    start, end, index = tabs._bar._segments[1]
    tabs._bar.on_mouse_click(tabs._bar.abs_x + start + 1, tabs._bar.abs_y)
    assert tabs.active == 1


def test_only_active_panel_content_renders():
    app = make_app()
    tabs = Tabs(0, 0, "800x200", animate=False)  # instant swap for a clean assert
    tabs.add_tab("One", Label(1, 1, "PANEL_ONE"))
    tabs.add_tab("Two", Label(1, 1, "PANEL_TWO"))
    app.add(tabs)

    snap = app.snapshot()
    assert "One" in snap and "Two" in snap  # both titles show in the strip
    assert "PANEL_ONE" in snap and "PANEL_TWO" not in snap  # only active content

    tabs.select(1)
    snap = app.snapshot()
    assert "PANEL_TWO" in snap and "PANEL_ONE" not in snap


def test_dock_resize_sets_cell_size():
    tabs = Tabs(0, 0, "100x100")
    tabs.dock_resize(50, 20, 10)  # 50x20 cells at scale 10
    assert tabs.natural_width(10) == 50
    assert tabs.natural_height(10) == 20


# ── switch animation ─────────────────────────────────────────────────────────


def _built_tabs(app, **kw):
    tabs = Tabs(0, 0, "800x200", **kw)
    tabs.add_tab("One", Label(1, 1, "PANEL_ONE"))
    tabs.add_tab("Two", Label(1, 1, "PANEL_TWO"))
    tabs.add_tab("Three", Label(1, 1, "PANEL_THREE"))
    app.add(tabs)
    app.snapshot()  # first draw so _wc is known (a switch only animates after that)
    return tabs


def test_animate_false_switches_instantly():
    app = make_app()
    tabs = _built_tabs(app, animate=False)
    tabs.select(1)
    assert not tabs._transitioning
    snap = app.snapshot()
    assert "PANEL_TWO" in snap and "PANEL_ONE" not in snap


def test_select_starts_a_transition():
    app = make_app()
    tabs = _built_tabs(app)  # animate defaults on
    tabs.select(2)
    assert tabs._transitioning and tabs._from == 0 and tabs._to == 2


def test_content_hidden_until_transition_finishes(monkeypatch):
    import cozy_tui.widgets.layout.tabs as tabsmod

    app = make_app()
    tabs = _built_tabs(app, anim_duration=0.2)
    clock = [100.0]
    monkeypatch.setattr(tabsmod.time, "monotonic", lambda: clock[0])

    tabs.select(1)  # _anim_start = 100.0
    clock[0] = 100.05  # mid-transition: no panel content is shown yet
    snap = app.snapshot()
    assert "PANEL_ONE" not in snap and "PANEL_TWO" not in snap
    assert "One" in snap and "Two" in snap  # the tab strip stays visible

    clock[0] = 100.3  # finished: the new panel is revealed
    snap = app.snapshot()
    assert "PANEL_TWO" in snap and "PANEL_ONE" not in snap


def test_transition_settles_after_duration(monkeypatch):
    import cozy_tui.widgets.layout.tabs as tabsmod

    app = make_app()
    tabs = _built_tabs(app, anim_duration=0.2)
    clock = [100.0]
    monkeypatch.setattr(tabsmod.time, "monotonic", lambda: clock[0])

    tabs.select(1)
    clock[0] = 100.3  # past the duration
    snap = app.snapshot()
    assert not tabs._transitioning
    assert "PANEL_TWO" in snap and "PANEL_ONE" not in snap
