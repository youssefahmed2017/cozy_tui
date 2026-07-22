"""Widget lifecycle: remove(), visible, disabled, and focus/blur events.

These are the operations that change a UI *after* it's built, so nearly every
test here asserts on what the app does with focus and hit-testing afterwards —
that's where the interesting failures live, not in the attribute itself.
"""

import pytest

from cozy_tui import App, Style
from cozy_tui.testing import Harness
from cozy_tui.widgets import Box, Button, HBox, Label, ListView, ScrollView, VBox


def make_ui(*widgets, size="600x300"):
    app = App(full=False, size=size)
    for w in widgets:
        app.add(w)
    return Harness(app)


# ── remove ───────────────────────────────────────────────────────────────────


def test_remove_takes_a_top_level_widget_off_the_screen():
    label = Label(0, 0, "gone")
    ui = make_ui(label, Label(0, 1, "stays"))
    assert ui.app.remove(label) is label
    assert "gone" not in ui.screen
    assert "stays" in ui.screen


def test_remove_finds_a_widget_nested_in_a_container():
    inner = Label(2, 1, "inner")
    box = Box(0, 0, "300x100")
    box.add(inner)
    ui = make_ui(box)
    assert ui.app.remove(inner) is inner
    assert inner.parent is None
    assert inner not in box.children
    assert "inner" not in ui.screen


def test_remove_returns_none_for_a_widget_that_is_not_in_the_tree():
    ui = make_ui(Label(0, 0, "a"))
    assert ui.app.remove(Label(0, 0, "orphan")) is None


def test_removing_the_focused_widget_moves_focus_to_the_next_stop():
    # The whole reason App.remove exists: a removed widget that keeps focus
    # silently swallows every keystroke.
    first, second = Button(0, 0, "one"), Button(0, 2, "two")
    ui = make_ui(first, second)
    ui.app.focus(first)
    ui.app.remove(first)
    assert ui.focused is second


def test_removing_a_container_moves_focus_off_its_focused_descendant():
    button = Button(2, 1, "inside")
    box = Box(0, 0, "300x100")
    box.add(button)
    outside = Button(0, 12, "outside")
    ui = make_ui(box, outside)
    ui.app.focus(button)
    ui.app.remove(box)
    assert ui.focused is outside


def test_removing_the_last_focusable_leaves_nothing_focused():
    only = Button(0, 0, "only")
    ui = make_ui(only)
    ui.app.focus(only)
    ui.app.remove(only)
    assert ui.focused is None


def test_removing_an_unfocused_widget_leaves_focus_alone():
    keep, drop = Button(0, 0, "keep"), Button(0, 2, "drop")
    ui = make_ui(keep, drop)
    ui.app.focus(keep)
    ui.app.remove(drop)
    assert ui.focused is keep


def test_container_remove_and_clear_detach_their_children():
    a, b = Label(0, 0, "a"), Label(0, 1, "b")
    box = VBox(0, 0)
    box.add(a)
    box.add(b)
    assert box.remove(a) is a
    assert a.parent is None and box.children == [b]
    box.clear()
    assert box.children == [] and b.parent is None


def test_container_remove_ignores_a_widget_it_does_not_hold():
    box = VBox(0, 0)
    assert box.remove(Label(0, 0, "x")) is None


def test_a_layout_reflows_after_a_child_is_removed():
    stack = VBox(0, 0)
    for text in ("one", "two", "three"):
        stack.add(Label(0, 0, text))
    ui = make_ui(stack)
    ui.compose()
    stack.remove(stack.children[0])
    assert ui.line(0).startswith("two")
    assert ui.line(1).startswith("three")


def test_scrollview_clear_detaches_children_and_resets_the_scroll():
    view = ScrollView(0, 0, "400x30")
    child = Label(0, 5, "x")
    view.add(child)
    view.scroll_to(3)
    view.clear()
    assert view.children == [] and child.parent is None
    assert view._scroll == 0


# ── visible ──────────────────────────────────────────────────────────────────


def test_a_hidden_widget_is_not_drawn():
    label = Label(0, 0, "peekaboo")
    ui = make_ui(label)
    assert "peekaboo" in ui.screen
    label.visible = False
    assert "peekaboo" not in ui.screen
    label.visible = True
    assert "peekaboo" in ui.screen


def test_a_hidden_child_of_a_container_is_not_drawn():
    inner = Label(2, 1, "inner")
    box = Box(0, 0, "300x100")
    box.add(inner)
    ui = make_ui(box)
    inner.visible = False
    assert "inner" not in ui.screen


def test_a_hidden_widget_is_not_a_tab_stop():
    first, hidden, last = Button(0, 0, "a"), Button(0, 2, "b"), Button(0, 4, "c")
    ui = make_ui(first, hidden, last)
    hidden.visible = False
    ui.app.focus(first)
    ui.press("\t")
    assert ui.focused is last


def test_hiding_a_container_removes_its_whole_subtree_from_the_tab_order():
    inner = Button(2, 1, "inner")
    box = Box(0, 0, "300x100")
    box.add(inner)
    outside = Button(0, 12, "outside")
    ui = make_ui(box, outside)
    box.visible = False
    assert ui.app._collect_focusables() == [outside]


def test_a_click_passes_through_a_hidden_widget():
    under = Button(0, 0, "under", width=20)
    over = Button(0, 0, "over", width=20)
    ui = make_ui(under, over)
    over.visible = False
    ui.click((2, 0))
    assert ui.focused is under


def test_focus_refuses_to_land_on_a_hidden_widget():
    hidden = Button(0, 0, "hidden")
    ui = make_ui(hidden)
    hidden.visible = False
    ui.app.focus(hidden)
    assert ui.focused is None


def test_hiding_a_vbox_child_collapses_the_gap_around_it():
    stack = VBox(0, 0, gap=1)
    top, middle, bottom = Label(0, 0, "top"), Label(0, 0, "mid"), Label(0, 0, "bot")
    for w in (top, middle, bottom):
        stack.add(w)
    ui = make_ui(stack)
    ui.compose()
    assert ui.line(2).startswith("mid")
    middle.visible = False
    assert ui.line(2).startswith("bot")  # closed up, not a hole
    assert stack.natural_height(1) == 3  # two rows plus one gap


def test_hiding_an_hbox_child_collapses_the_gap_around_it():
    row = HBox(0, 0, gap=2)
    left, hidden, right = Label(0, 0, "L"), Label(0, 0, "H"), Label(0, 0, "R")
    for w in (left, hidden, right):
        row.add(w)
    ui = make_ui(row)
    ui.compose()
    hidden.visible = False
    ui.compose()
    assert ui.line(0).startswith("L  R")


def test_hiding_every_child_gives_a_layout_no_size():
    stack = VBox(0, 0, gap=1)
    for _ in range(3):
        stack.add(Label(0, 0, "x"))
    for child in stack.children:
        child.visible = False
    assert stack.natural_height(1) == 0
    assert stack.natural_width(1) == 0


# ── disabled ─────────────────────────────────────────────────────────────────


def test_a_disabled_widget_still_draws_but_dimmed():
    button = Button(0, 0, "Submit", style=Style(fg="white", styles=["bold"]))
    ui = make_ui(button)
    button.disabled = True
    assert "Submit" in ui.screen
    assert "dim" in button.style.styles
    assert "bold" not in button.style.styles  # bold would fight the dim
    button.disabled = False
    assert button.style.styles == ("bold",)


def test_the_dimmed_style_follows_a_change_to_the_base_style():
    # The cache keys on the style's colors, not its identity, because a theme
    # switch re-colors the App's Style object in place.
    label = Label(0, 0, "x", style=Style(fg="white"))
    label.disabled = True
    assert label.style.fg == "white"
    label._style.fg = "red"  # what App._sync_theme_style does
    assert label.style.fg == "red"


def test_a_disabled_widget_is_not_a_tab_stop():
    first, off, last = Button(0, 0, "a"), Button(0, 2, "b"), Button(0, 4, "c")
    ui = make_ui(first, off, last)
    off.disabled = True
    ui.app.focus(first)
    ui.press("\t")
    assert ui.focused is last


def test_a_disabled_widget_swallows_a_click_instead_of_passing_it_down():
    # It's still on screen and occupying the space, so a click on it must not
    # activate whatever happens to sit underneath.
    under = Button(0, 0, "under", width=20)
    over = Button(0, 0, "over", width=20)
    ui = make_ui(under, over)
    over.disabled = True
    ui.click((2, 0))
    assert ui.focused is None


def test_a_disabled_button_does_not_fire_its_click_handler():
    fired = []
    button = Button(0, 0, "Go", width=10).on_click(lambda _b: fired.append(1))
    ui = make_ui(button)
    button.disabled = True
    ui.click((2, 0))
    assert fired == []


def test_focus_refuses_to_land_on_a_disabled_widget():
    button = Button(0, 0, "nope")
    ui = make_ui(button)
    button.disabled = True
    ui.app.focus(button)
    assert ui.focused is None


def test_a_disabled_container_still_lets_tab_reach_its_children():
    # "Disabled" on a container means the container itself is inert, not that
    # its contents are — it isn't a Tab stop of its own to begin with.
    inner = Button(2, 1, "inner")
    box = Box(0, 0, "300x100", focusable=True)
    box.add(inner)
    ui = make_ui(box)
    box.disabled = True
    assert ui.app._collect_focusables() == [inner]


# ── focus / blur ─────────────────────────────────────────────────────────────


def test_focus_and_blur_fire_on_the_right_widgets():
    events = []
    a = Button(0, 0, "a").on_focus(lambda w: events.append("focus a"))
    a.on_blur(lambda w: events.append("blur a"))
    b = Button(0, 2, "b").on_focus(lambda w: events.append("focus b"))
    ui = make_ui(a, b)
    ui.app.focus(a)
    assert events == ["focus a"]
    ui.app.focus(b)
    assert events == ["focus a", "blur a", "focus b"]


def test_refocusing_the_same_widget_fires_nothing():
    events = []
    button = Button(0, 0, "a").on_focus(lambda w: events.append("focus"))
    button.on_blur(lambda w: events.append("blur"))
    ui = make_ui(button)
    ui.app.focus(button)
    ui.app.focus(button)
    assert events == ["focus"]


def test_blur_sees_the_new_focus_already_in_place():
    # Handlers run after the assignment, so one that inspects app.focused (a
    # validator that skips itself when focus moved to its own error label, say)
    # sees the final state rather than a half-applied one.
    seen = []
    a = Button(0, 0, "a")
    b = Button(0, 2, "b")
    ui = make_ui(a, b)
    a.on_blur(lambda w: seen.append(ui.app.focused))
    ui.app.focus(a)
    ui.app.focus(b)
    assert seen == [b]


def test_blur_fires_when_tabbing_away():
    events = []
    a = Button(0, 0, "a").on_blur(lambda w: events.append("blur"))
    ui = make_ui(a, Button(0, 2, "b"))
    ui.app.focus(a)
    ui.press("\t")
    assert events == ["blur"]


def test_blur_fires_when_the_focused_widget_is_removed():
    events = []
    a = Button(0, 0, "a").on_blur(lambda w: events.append("blur"))
    ui = make_ui(a, Button(0, 2, "b"))
    ui.app.focus(a)
    ui.app.remove(a)
    assert events == ["blur"]


def test_a_widget_with_no_handlers_is_unaffected():
    ui = make_ui(Button(0, 0, "a"), Button(0, 2, "b"))
    ui.app.focus(ui.app.widgets[0])
    ui.press("\t")
    assert ui.focused is ui.app.widgets[1]


def test_hiding_the_focused_widget_stops_it_receiving_keys():
    # visible/disabled are plain attributes, so nothing notices at the moment
    # they change; the key-routing path catches it instead.
    keys = []
    button = Button(0, 0, "a")
    button.on_key = lambda key: keys.append(key)
    ui = make_ui(button, Button(0, 2, "b"))
    ui.app.focus(button)
    button.visible = False
    ui.press("x")
    assert keys == []
    assert ui.focused is None


def test_disabling_the_focused_widget_stops_it_receiving_keys():
    keys = []
    button = Button(0, 0, "a")
    button.on_key = lambda key: keys.append(key)
    ui = make_ui(button, Button(0, 2, "b"))
    ui.app.focus(button)
    button.disabled = True
    ui.press("x")
    assert keys == []
    assert ui.focused is None


# ── Button height ────────────────────────────────────────────────────────────


def test_a_button_is_one_row_tall_by_default():
    button = Button(0, 0, "Go", width=8)
    assert button.natural_height(10) == 1
    assert button.contains(2, 0) and not button.contains(2, 1)


def test_a_tall_button_paints_a_solid_block_with_the_label_centred():
    button = Button(0, 0, "7", width=8, height=3, style=Style(fg="white", bg="blue"))
    ui = make_ui(button)
    ui.compose()
    assert [ui.cell(0, r).style.bg for r in range(3)] == ["blue_bg"] * 3
    assert ui.line(1).strip() == "7"  # middle row
    assert ui.line(0).strip() == "" and ui.line(2).strip() == ""


def test_a_tall_button_is_clickable_on_every_one_of_its_rows():
    fired = []
    button = Button(0, 0, "Go", width=10, height=3).on_click(lambda _b: fired.append(1))
    ui = make_ui(button)
    for row in range(3):
        ui.click((2, row))
    assert len(fired) == 3
    assert not button.contains(2, 3)


def test_a_layout_reserves_a_tall_buttons_full_height():
    stack = VBox(0, 0, gap=1)
    stack.add(Button(0, 0, "a", width=8, height=3))
    stack.add(Button(0, 0, "b", width=8, height=3))
    assert stack.natural_height(1) == 7  # 3 + gap + 3
    assert stack.children[1].y == 4


def test_button_height_is_clamped_to_at_least_one_row():
    assert Button(0, 0, "x", height=0).natural_height(10) == 1
