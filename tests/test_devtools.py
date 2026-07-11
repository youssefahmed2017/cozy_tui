"""The F12 Cozy DevTools panel: Elements (the old F3 inspector), Console (see
also test_debug.py), Performance, Coordinates, and Tree -- unified behind one
key instead of three (F3/F12/Ctrl+Shift+D), and (unlike the first version of
this panel) a real docked Splitter pane rather than a floating overlay -- see
`App.toggle_devtools`/`cozy_tui._devtools._AppContentPane`."""

from cozy_tui import App, Style
from cozy_tui.events import Key, MouseClick, MouseDrag, MouseMove, MouseRelease
from cozy_tui.widgets import Button, Label, Splitter, VBox


def make_app(**kw):
    return App(
        full=False,
        size="1000x400",
        style=Style(fg="white", bg="black"),
        debug=True,
        **kw,
    )


def _click_tab(app, name):
    """Simulate a real mouse click on a DevTools tab label by name, reading
    the tab bar's own hit-test segments (same technique test_command_palette.py
    /test_splitter.py already use for coordinate-based clicks)."""
    bar = app._devtools_tabs.bar
    index = app._devtools_tabs._titles.index(name)
    start, _end, _idx = next(s for s in bar._segments if s[2] == index)
    app._dispatch_input(MouseClick(bar.abs_x + start, bar.abs_y, 0))


def test_devtools_is_a_noop_without_debug():
    app = App(full=False, size="1000x400")  # debug=False
    app.toggle_devtools()
    assert app._devtools_active is False


def test_f3_and_ctrl_shift_d_do_nothing_anymore():
    app = make_app()
    app._dispatch_input(Key.F3)
    assert app._devtools_active is False
    app._dispatch_input(Key.CTRL_SHIFT_D)
    assert app._devtools_active is False


# ── F12 wraps the app in a real Splitter, not an overlay ─────────────────────


def test_f12_wraps_the_app_in_a_splitter_and_opens_on_elements():
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app.render()

    app._dispatch_input(Key.F12)
    assert app._devtools_active is True
    assert app._devtools_tabs.selected_title == "Elements"
    assert len(app.widgets) == 1
    splitter = app.widgets[0]
    assert isinstance(splitter, Splitter)
    assert splitter.first is app._devtools_content_pane
    assert splitter.second is app._devtools_panel
    assert btn in app._devtools_content_pane.children


def test_f12_again_closes_and_restores_the_original_widgets():
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app.render()

    app._dispatch_input(Key.F12)
    app._dispatch_input(Key.F12)
    assert app._devtools_active is False
    assert app._devtools_panel is None
    assert app._devtools_content_pane is None
    assert app.widgets == [btn]
    assert btn.parent is None  # unwrapped, not left pointing at the pane


def test_opening_devtools_does_not_steal_focus_but_clicking_it_does():
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app.focus(btn)
    app.render()

    app._dispatch_input(Key.F12)
    assert app.focused is btn  # opening alone must not steal focus

    app.render()
    _click_tab(app, "Console")
    bar = app._devtools_tabs.bar
    assert app.focused is bar  # a deliberate click on it does, via normal dispatch


def test_closing_devtools_restores_the_focus_from_before_it_opened():
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app.focus(btn)
    app.render()

    app._dispatch_input(Key.F12)
    app.render()
    _click_tab(app, "Console")  # focus moves onto DevTools' own tab bar
    app._dispatch_input(Key.F12)  # close
    assert app.focused is btn


def test_adding_a_widget_while_devtools_is_open_lands_in_the_app_pane():
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app.render()
    app._dispatch_input(Key.F12)

    label = Label(0, 5, "mid-session")
    app.add(label)
    assert label in app._devtools_content_pane.children
    assert label not in app.widgets  # not an orphaned second top-level item

    app._dispatch_input(Key.F12)  # close: the addition must survive the unwrap
    assert label in app.widgets


def test_dragging_the_divider_resizes_both_panes():
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app.render()
    app._dispatch_input(Key.F12)
    app.render()  # establishes splitter._divider_at

    splitter = app.widgets[0]
    before = splitter.get_ratio()
    divider_col = splitter.abs_x + splitter._divider_at
    app._dispatch_input(MouseClick(divider_col, splitter.abs_y, 0))
    app._dispatch_input(MouseDrag(divider_col - 15, splitter.abs_y, 0))
    app._dispatch_input(MouseRelease(divider_col - 15, splitter.abs_y, 0))
    assert splitter.get_ratio() != before


# ── Elements: hover / click-freeze / Esc (the old F3 behavior) ───────────────


def test_hover_targets_any_widget_not_just_focusable():
    app = make_app()
    box = VBox(0, 0)
    btn = Button(0, 0, "Go", width=10)
    box.add(btn)
    app.add(box)
    app.render()

    app._dispatch_input(Key.F12)
    app.render()
    app._dispatch_input(MouseMove(btn.abs_x, btn.abs_y))
    assert app._selected_widget is btn


def test_click_freezes_without_activating_the_widget():
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app.render()
    clicked = []
    btn.on_click(lambda w: clicked.append(w))

    app._dispatch_input(Key.F12)
    app.render()
    app._dispatch_input(MouseMove(btn.abs_x, btn.abs_y))
    app._dispatch_input(MouseClick(btn.abs_x, btn.abs_y, 0))

    assert app._selection_frozen is True
    assert app._selected_widget is btn
    assert clicked == []  # the click must not reach the real widget


def test_esc_unfreezes_but_does_not_close_devtools():
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app.render()

    app._dispatch_input(Key.F12)
    app.render()
    app._dispatch_input(MouseClick(btn.abs_x, btn.abs_y, 0))
    assert app._selection_frozen is True

    app._dispatch_input(Key.ESC)
    assert app._selection_frozen is False
    assert app._devtools_active is True  # still open -- only F12 closes it


def test_elements_panel_snapshot_shows_widget_fields():
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app.render()

    app._dispatch_input(Key.F12)
    app.render()
    app._dispatch_input(MouseMove(btn.abs_x, btn.abs_y))
    app.render()
    snap = app.snapshot()
    assert "Widget: Button" in snap
    assert "Focused" in snap and "Parent" in snap and "Style" in snap


# ── clicking a different DevTools tab while on Elements switches, doesn't select ──


def test_clicking_a_different_tab_switches_instead_of_selecting():
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app.render()  # establishes DevTools panel + tab bar segments

    app._dispatch_input(Key.F12)
    app.render()
    _click_tab(app, "Console")

    assert app._devtools_tabs.selected_title == "Console"
    assert app._selected_widget is None  # never treated as an inspection click


# ── Console / Performance content ────────────────────────────────────────────


def test_console_tab_shows_the_debug_log():
    app = make_app()
    app.debug("hello from the log")
    app._dispatch_input(Key.F12)
    app._devtools_tabs.select(app._devtools_tabs._titles.index("Console"))
    app.render()
    assert "hello from the log" in app.snapshot()


def test_performance_tab_shows_expected_fields():
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app._dispatch_input(Key.F12)
    app._devtools_tabs.select(app._devtools_tabs._titles.index("Performance"))
    app.render()
    snap = app.snapshot()
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


def _select_coords_tab(app):
    app._devtools_tabs.select(app._devtools_tabs._titles.index("Coordinates"))


def test_coordinates_tab_shows_live_position():
    app = make_app()
    app.add(Button(0, 0, "Go", width=10))
    app.render()
    app._dispatch_input(Key.F12)
    _select_coords_tab(app)
    app._dispatch_input(MouseMove(12, 7))
    app.render()
    snap = app.snapshot()
    assert "x : 12" in snap
    assert "y : 7" in snap


def test_clicking_while_on_coordinates_copies_to_clipboard(monkeypatch):
    import cozy_tui.clipboard as clipboard_mod

    copied = []
    monkeypatch.setattr(clipboard_mod, "copy", lambda text: copied.append(text))

    app = make_app()
    app.render()
    app._dispatch_input(Key.F12)
    app.render()
    _select_coords_tab(app)

    app._dispatch_input(MouseClick(9, 4, 0))
    assert copied == ["x=9, y=4"]


def test_clicking_while_on_coordinates_does_not_activate_the_real_widget():
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    clicked = []
    btn.on_click(lambda w: clicked.append(w))
    app.add(btn)
    app.render()
    app._dispatch_input(Key.F12)
    app.render()
    _select_coords_tab(app)

    app._dispatch_input(MouseClick(btn.abs_x, btn.abs_y, 0))
    assert clicked == []


def test_clicking_a_different_tab_while_on_coordinates_switches_not_copies(monkeypatch):
    import cozy_tui.clipboard as clipboard_mod

    copied = []
    monkeypatch.setattr(clipboard_mod, "copy", lambda text: copied.append(text))

    app = make_app()
    app.render()
    app._dispatch_input(Key.F12)
    app.render()
    _select_coords_tab(app)

    _click_tab(app, "Console")
    assert app._devtools_tabs.selected_title == "Console"
    assert copied == []


def test_dragging_the_divider_while_on_coordinates_still_resizes():
    app = make_app()
    app.add(Button(0, 0, "Go", width=10))
    app.render()
    app._dispatch_input(Key.F12)
    app.render()
    _select_coords_tab(app)

    splitter = app.widgets[0]
    before = splitter.get_ratio()
    divider_col = splitter.abs_x + splitter._divider_at
    app._dispatch_input(MouseClick(divider_col, splitter.abs_y, 0))
    app._dispatch_input(MouseDrag(divider_col - 15, splitter.abs_y, 0))
    app._dispatch_input(MouseRelease(divider_col - 15, splitter.abs_y, 0))
    assert splitter.get_ratio() != before


def test_hover_still_works_normally_while_on_coordinates_tab():
    # Unlike Elements, Coordinates doesn't take over hover -- a widget's own
    # mouse_moves-based hover (on_enter/on_leave) keeps firing normally.
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    entered = []
    btn.on_enter(lambda w: entered.append(w))
    app.add(btn)
    app.render()
    app._dispatch_input(Key.F12)
    app.render()
    _select_coords_tab(app)

    app._dispatch_input(MouseMove(btn.abs_x, btn.abs_y))
    assert entered == [btn]


# ── Tree: lazy build, click selects without leaving the tab ──────────────────


def test_tree_tab_builds_lazily_on_first_switch():
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app._dispatch_input(Key.F12)
    assert app._devtools_panel._tree_built is False

    app._devtools_tabs.select(app._devtools_tabs._titles.index("Tree"))
    assert app._devtools_panel._tree_built is True


def test_tree_shows_app_root_and_widget_hierarchy():
    app = make_app()
    box = VBox(0, 0)
    box.add(Button(0, 0, "Go", width=10))
    app.add(box)
    app._dispatch_input(Key.F12)
    app._devtools_tabs.select(app._devtools_tabs._titles.index("Tree"))
    app.render()
    snap = app.snapshot()
    assert "App" in snap
    assert "VBox" in snap
    assert "Button" in snap


def test_tree_does_not_show_devtools_own_chrome():
    # _build_widget_tree reads app._devtools_content_pane.children, not
    # app.widgets (which is just [the Splitter] while DevTools is open) --
    # showing DevTools' own internals here would be circular and useless.
    app = make_app()
    app.add(Button(0, 0, "Go", width=10))
    app._dispatch_input(Key.F12)
    app._devtools_tabs.select(app._devtools_tabs._titles.index("Tree"))
    app.render()
    snap = app.snapshot()
    assert "Splitter" not in snap
    assert "DevToolsPanel" not in snap


def test_clicking_a_tree_node_selects_without_leaving_the_tree_tab():
    # Deliberately does NOT jump to Elements -- that made it impossible to
    # click through several nodes in a row without being bounced away.
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app._dispatch_input(Key.F12)
    app._devtools_tabs.select(app._devtools_tabs._titles.index("Tree"))
    app.render()

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
    app = make_app()
    btn = Button(0, 0, "Go", width=10)
    app.add(btn)
    app.focus(btn)
    app._dispatch_input(Key.F12)
    app.render()
    snap = app.snapshot()
    assert "FPS:" in snap
    assert "Widgets:" in snap
    assert "Focus: Button" in snap
    assert "Theme:" in snap
