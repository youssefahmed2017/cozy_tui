"""Screens: named, swappable sets of top-level widgets (cozy_tui.screen)."""

import pytest

from cozy_tui import App, Key
from cozy_tui.screen import Screen
from cozy_tui.testing import Harness
from cozy_tui.widgets import Box, Button, Input, Label, Tabs


def make_ui(size="600x300"):
    return Harness(App(full=False, size=size))


# ── basics ───────────────────────────────────────────────────────────────────


def test_screens_swap_what_is_drawn():
    ui = make_ui()
    ui.app.screen("menu").add(Label(0, 0, "MENU"))
    ui.app.screen("game").add(Label(0, 0, "GAME"))

    ui.app.show("menu")
    assert "MENU" in ui.screen and "GAME" not in ui.screen
    ui.app.show("game")
    assert "GAME" in ui.screen and "MENU" not in ui.screen


def test_screen_returns_the_same_object_for_a_name():
    ui = make_ui()
    assert ui.app.screen("menu") is ui.app.screen("menu")


def test_the_first_screen_adopts_whatever_the_app_already_had():
    # So screens can be introduced to an existing app without blanking it or
    # reordering the setup code.
    ui = make_ui()
    ui.app.add(Label(0, 0, "already here"))
    home = ui.app.screen("home")
    assert "already here" in ui.screen
    assert ui.app.current_screen is home
    assert len(home.widgets) == 1


def test_app_add_lands_on_the_current_screen():
    ui = make_ui()
    menu = ui.app.screen("menu")
    other = ui.app.screen("other")
    ui.app.show(other)
    ui.app.add(Label(0, 0, "late"))
    assert other.widgets and not menu.widgets
    assert "late" in ui.screen


def test_showing_an_unknown_screen_raises():
    ui = make_ui()
    ui.app.screen("menu")
    with pytest.raises(KeyError, match="menu"):
        ui.app.show("nope")


def test_show_accepts_the_screen_object_too():
    ui = make_ui()
    ui.app.screen("a").add(Label(0, 0, "A"))
    b = ui.app.screen("b")
    b.add(Label(0, 0, "B"))
    assert ui.app.show(b) is b
    assert "B" in ui.screen


def test_showing_the_current_screen_is_a_no_op():
    ui = make_ui()
    seen = []
    menu = ui.app.screen("menu").on_show(lambda s: seen.append(s.name))
    ui.app.show(menu)
    ui.app.show(menu)
    assert seen == []  # it was already current from being created first


def test_an_app_with_no_screens_is_unchanged():
    ui = make_ui()
    ui.app.add(Label(0, 0, "plain"))
    assert ui.app.current_screen is None
    assert "plain" in ui.screen


# ── state is kept ────────────────────────────────────────────────────────────


def test_switching_away_and_back_keeps_the_widgets_and_their_state():
    ui = make_ui()
    form = ui.app.screen("form")
    field = Input(0, 0, 20)
    form.add(field)
    ui.app.screen("other").add(Label(0, 0, "other"))

    ui.app.show("form")
    ui.focus(field)
    ui.type("hello")
    ui.app.show("other")
    ui.app.show("form")
    assert field.value == "hello"  # not rebuilt
    assert "hello" in ui.screen


def test_a_screen_remembers_which_widget_was_focused():
    ui = make_ui()
    home = ui.app.screen("home")
    first, second = Button(0, 0, "one"), Button(0, 2, "two")
    home.add(first)
    home.add(second)
    ui.app.screen("away").add(Label(0, 0, "away"))

    ui.app.show(home)
    ui.app.focus(second)
    ui.app.show("away")
    ui.app.show(home)
    assert ui.focused is second


def test_a_screen_focuses_its_first_stop_when_it_has_no_memory():
    ui = make_ui()
    ui.app.screen("home").add(Label(0, 0, "home"))
    away = ui.app.screen("away")
    first = Button(0, 0, "first")
    away.add(first)
    away.add(Button(0, 2, "second"))
    ui.app.show(away)
    assert ui.focused is first


def test_screen_focus_before_the_screen_is_shown_applies_on_show():
    ui = make_ui()
    ui.app.screen("home").add(Label(0, 0, "home"))
    away = ui.app.screen("away")
    a, b = Button(0, 0, "a"), Button(0, 2, "b")
    away.add(a)
    away.add(b)
    away.focus(b)
    ui.app.show(away)
    assert ui.focused is b


def test_a_remembered_widget_that_was_removed_does_not_come_back():
    ui = make_ui()
    ui.app.screen("home").add(Label(0, 0, "home"))
    away = ui.app.screen("away")
    a, b = Button(0, 0, "a"), Button(0, 2, "b")
    away.add(a)
    away.add(b)
    ui.app.show(away)
    ui.app.focus(a)
    ui.app.show("home")
    away.remove(a)
    ui.app.show(away)
    assert ui.focused is b


# ── focus / tab confinement ──────────────────────────────────────────────────


def test_tab_only_cycles_the_showing_screen():
    ui = make_ui()
    home = ui.app.screen("home")
    a, b = Button(0, 0, "a"), Button(0, 2, "b")
    home.add(a)
    home.add(b)
    hidden = Button(0, 0, "hidden")
    ui.app.screen("away").add(hidden)

    ui.app.show(home)
    ui.app.focus(a)
    ui.press("\t")
    assert ui.focused is b
    ui.press("\t")
    assert ui.focused is a  # wrapped, never reaching the other screen


def test_blur_fires_when_a_screen_switch_takes_focus_away():
    ui = make_ui()
    events = []
    home = ui.app.screen("home")
    button = Button(0, 0, "a").on_blur(lambda w: events.append("blur"))
    home.add(button)
    ui.app.screen("away").add(Label(0, 0, "away"))
    ui.app.show(home)
    ui.app.focus(button)
    ui.app.show("away")
    assert events == ["blur"]


# ── docking ──────────────────────────────────────────────────────────────────


def test_each_screen_docks_independently():
    ui = make_ui()
    home = ui.app.screen("home")
    home.dock(Label(0, 0, "home footer"), "bottom")
    away = ui.app.screen("away")
    away.dock(Label(0, 0, "away header"), "top")

    ui.app.show(home)
    assert "home footer" in ui.lines[-1]
    ui.app.show(away)
    assert "away header" in ui.lines[0]
    assert "home footer" not in ui.screen


def test_screen_dock_rejects_an_unknown_side():
    ui = make_ui()
    with pytest.raises(ValueError, match="dock side"):
        ui.app.screen("home").dock(Label(0, 0, "x"), "sideways")


# ── lifecycle hooks ──────────────────────────────────────────────────────────


def test_on_show_and_on_hide_fire_in_order():
    ui = make_ui()
    events = []
    home = ui.app.screen("home").on_hide(lambda s: events.append(f"hide {s.name}"))
    home.on_show(lambda s: events.append("show home"))
    away = ui.app.screen("away").on_show(lambda s: events.append("show away"))
    away.on_hide(lambda s: events.append("hide away"))

    ui.app.show(away)
    ui.app.show(home)
    assert events == ["hide home", "show away", "hide away", "show home"]


def test_on_show_sees_the_screen_already_installed():
    ui = make_ui()
    seen = []
    ui.app.screen("home").add(Label(0, 0, "home"))
    away = ui.app.screen("away")
    away.add(Label(0, 0, "away"))
    away.on_show(lambda s: seen.append((s.is_current, "away" in ui.screen)))
    ui.app.show(away)
    assert seen == [(True, True)]


# ── screen.remove ────────────────────────────────────────────────────────────


def test_removing_from_the_showing_screen_moves_focus_like_app_remove():
    ui = make_ui()
    home = ui.app.screen("home")
    a, b = Button(0, 0, "a"), Button(0, 2, "b")
    home.add(a)
    home.add(b)
    ui.app.show(home)
    ui.app.focus(a)
    assert home.remove(a) is a
    assert ui.focused is b


def test_removing_from_a_background_screen_clears_its_remembered_focus():
    ui = make_ui()
    ui.app.screen("home").add(Label(0, 0, "home"))
    away = ui.app.screen("away")
    a = Button(0, 0, "a")
    away.add(a)
    away.focus(a)
    assert away.remove(a) is a
    assert away.focused is None


def test_removing_a_nested_widget_from_a_background_screen():
    ui = make_ui()
    ui.app.screen("home").add(Label(0, 0, "home"))
    away = ui.app.screen("away")
    box = Box(0, 0, "300x100")
    inner = Label(2, 1, "inner")
    box.add(inner)
    away.add(box)
    assert away.remove(inner) is inner
    assert inner not in box.children


def test_screen_repr_says_whether_it_is_showing():
    ui = make_ui()
    home = ui.app.screen("home")
    assert "showing" in repr(home)
    ui.app.screen("away")
    ui.app.show("away")
    assert "showing" not in repr(home)


# ── Tabs.remove_tab (container API consistency) ──────────────────────────────


def test_remove_tab_by_title_and_by_index():
    tabs = Tabs(0, 0, "400x100")
    for title in ("A", "B", "C"):
        tabs.add_tab(title, Label(0, 0, title))
    assert tabs.remove_tab("B") is not None
    assert tabs._titles == ["A", "C"]
    assert tabs.remove_tab(0) is not None
    assert tabs._titles == ["C"]


def test_remove_tab_ignores_something_that_is_not_a_tab():
    tabs = Tabs(0, 0, "400x100")
    tabs.add_tab("A", Label(0, 0, "A"))
    assert tabs.remove_tab("nope") is None
    assert tabs.remove_tab(7) is None
    assert tabs._titles == ["A"]


def test_removing_an_earlier_tab_keeps_you_on_the_same_one():
    tabs = Tabs(0, 0, "400x100")
    for title in ("A", "B", "C"):
        tabs.add_tab(title, Label(0, 0, title))
    tabs.select(2)
    tabs.remove_tab("A")
    assert tabs.selected_title == "C"


def test_removing_the_last_tab_clamps_the_selection():
    tabs = Tabs(0, 0, "400x100")
    for title in ("A", "B"):
        tabs.add_tab(title, Label(0, 0, title))
    tabs.select(1)
    tabs.remove_tab("B")
    assert tabs.selected_title == "A"


# ── per-screen key bindings ──────────────────────────────────────────────────


def two_screens():
    ui = make_ui()
    a = ui.app.screen("a")
    a.add(Label(0, 0, "A"))
    b = ui.app.screen("b")
    b.add(Label(0, 0, "B"))
    return ui, a, b


def test_a_screen_binding_only_fires_while_that_screen_shows():
    ui, a, b = two_screens()
    seen = []
    a.on_key("x", lambda: seen.append("a"))
    b.on_key("x", lambda: seen.append("b"))
    ui.press("x")
    ui.app.show(b)
    ui.press("x")
    assert seen == ["a", "b"]


def test_a_screen_binding_beats_the_app_wide_one_for_the_same_key():
    # The point: Esc can mean "back" on one screen and "quit" on another with
    # no dispatcher in the middle checking current_screen.
    ui, a, b = two_screens()
    seen = []
    ui.app.on_key(Key.ESC, lambda: seen.append("global"))
    a.on_key(Key.ESC, lambda: seen.append("a"))
    ui.press(Key.ESC)
    ui.app.show(b)  # b has no binding of its own
    ui.press(Key.ESC)
    assert seen == ["a", "global"]


def test_a_screen_binding_can_quit():
    ui, a, _b = two_screens()
    a.on_key("q", lambda: "quit")
    ui.press("q")
    assert ui.quit_requested


def test_a_described_screen_binding_reaches_the_bindings_legend():
    ui, a, _b = two_screens()
    a.on_key("s", lambda: None, description="Save", section="File")
    assert ui.app._bindings["s"] == ("Save", "File")


def test_screen_on_key_chains():
    ui, a, _b = two_screens()
    assert a.on_key("x", lambda: None).on_key("y", lambda: None) is a


# ── selected_index setter ────────────────────────────────────────────────────


def test_check_list_selected_index_can_be_restored():
    from cozy_tui.widgets import CheckItem, CheckList

    items = CheckList(0, 0)
    for text in ("a", "b", "c"):
        items.append(CheckItem(text))
    items.selected_index = 2
    assert items.selected_index == 2 and items.selected == "c"
    items.selected_index = 99  # clamped, not an error
    assert items.selected_index == 2


def test_list_view_selected_index_can_be_restored():
    from cozy_tui.widgets import ListView

    items = ListView(0, 0)
    for text in ("a", "b", "c"):
        items.append(text)
    items.selected_index = 1
    assert items.selected == "b"
    items.selected_index = -5
    assert items.selected_index == 0


def test_setting_selected_index_on_an_empty_list_is_a_no_op():
    from cozy_tui.widgets import ListView

    items = ListView(0, 0)
    items.selected_index = 3
    assert items.selected_index is None
