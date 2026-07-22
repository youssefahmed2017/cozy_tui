"""The F12 Cozy DevTools panel: Elements (the old F3 inspector), Console (see
also test_debug.py), Performance, Coordinates, and Tree -- unified behind one
key instead of three (F3/F12/Ctrl+Shift+D), and (unlike the first version of
this panel) a real docked Splitter pane rather than a floating overlay -- see
`App.toggle_devtools`/`cozy_tui._devtools._AppContentPane`."""

from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.testing import Harness
from cozy_tui.widgets import Button, Label, Splitter, VBox


def make_ui(**kw):
    """A Harness over a debug-enabled app. These tests assert on DevTools'
    own internals (`app._selected_widget`, `app.widgets`, ...), so they reach
    through `ui.app` for state and use the harness for interaction."""
    app = App(
        full=False,
        size="1000x400",
        style=Style(fg="white", bg="black"),
        debug=True,
        **kw,
    )
    return Harness(app)


def _click_tab(ui, name):
    """Simulate a real mouse click on a DevTools tab label by name, reading
    the tab bar's own hit-test segments (same technique test_command_palette.py
    /test_splitter.py already use for coordinate-based clicks)."""
    bar = ui.app._devtools_tabs.bar
    index = ui.app._devtools_tabs._titles.index(name)
    start, _end, _idx = next(s for s in bar._segments if s[2] == index)
    ui.click((bar.abs_x + start, bar.abs_y))


def test_devtools_is_a_noop_without_debug():
    app = App(full=False, size="1000x400")  # debug=False
    app.toggle_devtools()
    assert app._devtools_active is False


def test_f3_and_ctrl_shift_d_do_nothing_anymore():
    ui = make_ui()
    app = ui.app
    ui.press(Key.F3)
    assert app._devtools_active is False
    ui.press(Key.CTRL_SHIFT_D)
    assert app._devtools_active is False


# ── F12 wraps the app in a real Splitter, not an overlay ─────────────────────


def test_f12_wraps_the_app_in_a_splitter_and_opens_on_elements():
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    ui.compose()

    ui.press(Key.F12)
    assert app._devtools_active is True
    assert app._devtools_tabs.selected_title == "Elements"
    assert len(app.widgets) == 1
    splitter = app.widgets[0]
    assert isinstance(splitter, Splitter)
    assert splitter.first is app._devtools_content_pane
    assert splitter.second is app._devtools_panel
    assert btn in app._devtools_content_pane.children


def test_f12_again_closes_and_restores_the_original_widgets():
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    ui.compose()

    ui.press(Key.F12)
    ui.press(Key.F12)
    assert app._devtools_active is False
    assert app._devtools_panel is None
    assert app._devtools_content_pane is None
    assert app.widgets == [btn]
    assert btn.parent is None  # unwrapped, not left pointing at the pane


def test_opening_devtools_does_not_steal_focus_but_clicking_it_does():
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app.focus(btn)
    ui.compose()

    ui.press(Key.F12)
    assert app.focused is btn  # opening alone must not steal focus

    ui.compose()
    _click_tab(ui, "Console")
    bar = app._devtools_tabs.bar
    assert app.focused is bar  # a deliberate click on it does, via normal dispatch


def test_closing_devtools_restores_the_focus_from_before_it_opened():
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app.focus(btn)
    ui.compose()

    ui.press(Key.F12)
    ui.compose()
    _click_tab(ui, "Console")  # focus moves onto DevTools' own tab bar
    ui.press(Key.F12)  # close
    assert app.focused is btn


def test_adding_a_widget_while_devtools_is_open_lands_in_the_app_pane():
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    ui.compose()
    ui.press(Key.F12)

    label = Label(0, 5, "mid-session")
    app.add(label)
    assert label in app._devtools_content_pane.children
    assert label not in app.widgets  # not an orphaned second top-level item

    ui.press(Key.F12)  # close: the addition must survive the unwrap
    assert label in app.widgets


def test_dragging_the_divider_resizes_both_panes():
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    ui.compose()
    ui.press(Key.F12)
    ui.compose()  # establishes splitter._divider_at

    splitter = app.widgets[0]
    before = splitter.get_ratio()
    divider_col = splitter.abs_x + splitter._divider_at
    ui.click((divider_col, splitter.abs_y))
    ui.drag((divider_col - 15, splitter.abs_y))
    ui.release((divider_col - 15, splitter.abs_y))
    assert splitter.get_ratio() != before


# ── Elements: hover / click-freeze / Esc (the old F3 behavior) ───────────────


def test_hover_targets_any_widget_not_just_focusable():
    ui = make_ui()
    app = ui.app
    box = VBox(0, 0)
    btn = Button(0, 0, "Go", width=10)
    box.add(btn)
    app.add(box)
    ui.compose()

    ui.press(Key.F12)
    ui.compose()
    ui.hover((btn.abs_x, btn.abs_y))
    assert app._selected_widget is btn


def test_click_freezes_without_activating_the_widget():
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    ui.compose()
    clicked = []
    btn.on_click(lambda w: clicked.append(w))

    ui.press(Key.F12)
    ui.compose()
    ui.hover((btn.abs_x, btn.abs_y))
    ui.click((btn.abs_x, btn.abs_y))

    assert app._selection_frozen is True
    assert app._selected_widget is btn
    assert clicked == []  # the click must not reach the real widget


def test_esc_unfreezes_but_does_not_close_devtools():
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    ui.compose()

    ui.press(Key.F12)
    ui.compose()
    ui.click((btn.abs_x, btn.abs_y))
    assert app._selection_frozen is True

    ui.press(Key.ESC)
    assert app._selection_frozen is False
    assert app._devtools_active is True  # still open -- only F12 closes it


def test_elements_panel_snapshot_shows_widget_fields():
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    ui.compose()

    ui.press(Key.F12)
    ui.compose()
    ui.hover((btn.abs_x, btn.abs_y))
    ui.compose()
    snap = ui.screen
    assert "Widget: Button" in snap
    assert "Focused" in snap and "Parent" in snap and "Style" in snap


# ── clicking a different DevTools tab while on Elements switches, doesn't select ──


def test_clicking_a_different_tab_switches_instead_of_selecting():
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    ui.compose()  # establishes DevTools panel + tab bar segments

    ui.press(Key.F12)
    ui.compose()
    _click_tab(ui, "Console")

    assert app._devtools_tabs.selected_title == "Console"
    assert app._selected_widget is None  # never treated as an inspection click


# ── Console / Performance content ────────────────────────────────────────────


def test_console_tab_shows_the_debug_log():
    ui = make_ui()
    app = ui.app
    app.debug("hello from the log")
    ui.press(Key.F12)
    app._devtools_tabs.select(app._devtools_tabs._titles.index("Console"))
    ui.advance(1)  # let the tab-switch glide finish
    assert "hello from the log" in ui.screen


def test_performance_tab_shows_expected_fields():
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    ui.press(Key.F12)
    app._devtools_tabs.select(app._devtools_tabs._titles.index("Performance"))
    ui.advance(1)  # let the tab-switch glide finish
    snap = ui.screen
    for field in (
        "FPS",
        "Widgets",
        "Focused",
        "Hovered",
        "Mouse",
        "Frame",
        "Render",
        "Layout",
    ):
        assert field in snap, snap


# ── Coordinates: live readout + click-to-copy ────────────────────────────────


def _select_coords_tab(ui):
    tabs = ui.app._devtools_tabs
    tabs.select(tabs._titles.index("Coordinates"))
    ui.advance(1)  # let the tab-switch glide finish


def test_coordinates_tab_shows_live_position():
    ui = make_ui()
    app = ui.app
    app.add(Button(0, 0, "Go", width=10))
    ui.compose()
    ui.press(Key.F12)
    _select_coords_tab(ui)
    ui.hover((12, 7))
    ui.compose()
    snap = ui.screen
    assert "x: 12" in snap
    assert "y: 7" in snap


def test_clicking_while_on_coordinates_copies_to_clipboard(monkeypatch):
    import cozy_tui.clipboard as clipboard_mod

    copied = []
    monkeypatch.setattr(clipboard_mod, "copy", lambda text: copied.append(text))

    ui = make_ui()
    app = ui.app
    ui.compose()
    ui.press(Key.F12)
    ui.compose()
    _select_coords_tab(ui)

    ui.click((9, 4))
    assert copied == ["x=9, y=4"]


def test_clicking_while_on_coordinates_does_not_activate_the_real_widget():
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    clicked = []
    btn.on_click(lambda w: clicked.append(w))
    app.add(btn)
    ui.compose()
    ui.press(Key.F12)
    ui.compose()
    _select_coords_tab(ui)

    ui.click((btn.abs_x, btn.abs_y))
    assert clicked == []


def test_clicking_a_different_tab_while_on_coordinates_switches_not_copies(monkeypatch):
    import cozy_tui.clipboard as clipboard_mod

    copied = []
    monkeypatch.setattr(clipboard_mod, "copy", lambda text: copied.append(text))

    ui = make_ui()
    app = ui.app
    ui.compose()
    ui.press(Key.F12)
    ui.compose()
    _select_coords_tab(ui)

    _click_tab(ui, "Console")
    assert app._devtools_tabs.selected_title == "Console"
    assert copied == []


def test_dragging_the_divider_while_on_coordinates_still_resizes():
    ui = make_ui()
    app = ui.app
    app.add(Button(0, 0, "Go", width=10))
    ui.compose()
    ui.press(Key.F12)
    ui.compose()
    _select_coords_tab(ui)

    splitter = app.widgets[0]
    before = splitter.get_ratio()
    divider_col = splitter.abs_x + splitter._divider_at
    ui.click((divider_col, splitter.abs_y))
    ui.drag((divider_col - 15, splitter.abs_y))
    ui.release((divider_col - 15, splitter.abs_y))
    assert splitter.get_ratio() != before


def test_hover_still_works_normally_while_on_coordinates_tab():
    # Unlike Elements, Coordinates doesn't take over hover -- a widget's own
    # mouse_moves-based hover (on_enter/on_leave) keeps firing normally.
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    entered = []
    btn.on_enter(lambda w: entered.append(w))
    app.add(btn)
    ui.compose()
    ui.press(Key.F12)
    ui.compose()
    _select_coords_tab(ui)

    ui.hover((btn.abs_x, btn.abs_y))
    assert entered == [btn]


# ── Tree: lazy build, click selects without leaving the tab ──────────────────


def test_tree_tab_builds_lazily_on_first_switch():
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    ui.press(Key.F12)
    assert app._devtools_panel._tree_built is False

    app._devtools_tabs.select(app._devtools_tabs._titles.index("Tree"))
    assert app._devtools_panel._tree_built is True


def test_tree_shows_app_root_and_widget_hierarchy():
    ui = make_ui()
    app = ui.app
    box = VBox(0, 0)
    box.add(Button(0, 0, "Go", width=10))
    app.add(box)
    ui.press(Key.F12)
    app._devtools_tabs.select(app._devtools_tabs._titles.index("Tree"))
    ui.advance(1)  # let the tab-switch glide finish
    snap = ui.screen
    assert "App" in snap
    assert "VBox" in snap
    assert "Button" in snap


def test_tree_does_not_show_devtools_own_chrome():
    # _build_widget_tree reads app._devtools_content_pane.children, not
    # app.widgets (which is just [the Splitter] while DevTools is open) --
    # showing DevTools' own internals here would be circular and useless.
    ui = make_ui()
    app = ui.app
    app.add(Button(0, 0, "Go", width=10))
    ui.press(Key.F12)
    app._devtools_tabs.select(app._devtools_tabs._titles.index("Tree"))
    ui.advance(1)  # let the tab-switch glide finish
    snap = ui.screen
    assert "Splitter" not in snap
    assert "DevToolsPanel" not in snap


def test_clicking_a_tree_node_selects_without_leaving_the_tree_tab():
    # Deliberately does NOT jump to Elements -- that made it impossible to
    # click through several nodes in a row without being bounced away.
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    ui.press(Key.F12)
    app._devtools_tabs.select(app._devtools_tabs._titles.index("Tree"))
    ui.advance(1)  # let the tab-switch glide finish

    tree = app._devtools_panel._tree_panel.children[0]
    # visible[0] = synthetic "App" root, visible[1] = the Button (the only
    # top-level widget) -- select it via Enter, the same path a click takes
    # (Tree.on_key(ENTER)/on_mouse_click both toggle + fire on_select(node)).
    tree._index = 1
    tree.on_key(Key.ENTER)

    assert app._selected_widget is btn
    assert app._selection_frozen is True
    assert app._devtools_tabs.selected_title == "Tree"


# ── status bar ────────────────────────────────────────────────────────────────


def test_status_bar_shows_fps_widgets_focus_theme():
    ui = make_ui()
    app = ui.app
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app.focus(btn)
    ui.press(Key.F12)
    ui.compose()
    snap = ui.screen
    assert "FPS:" in snap
    assert "Widgets:" in snap
    assert "Focus: Button" in snap
    assert "Theme:" in snap
