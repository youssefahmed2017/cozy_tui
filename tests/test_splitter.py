import pytest

from cozy_tui import App, Style
from cozy_tui.events import Key, MouseClick, MouseDrag
from cozy_tui.widgets import Box, Button, Label, Splitter


def make_app(size="400x100"):
    return App(full=False, size=size, style=Style(fg="white", bg="black"))


def make_panes():
    return Label(0, 0, "left"), Label(0, 0, "right")


def test_children_and_parent_wiring():
    first, second = make_panes()
    sp = Splitter(0, 0, "400x100", first, second)
    assert sp.children == [first, second]
    assert first.parent is sp and second.parent is sp


def test_invalid_orientation_raises():
    first, second = make_panes()
    with pytest.raises(ValueError):
        Splitter(0, 0, "400x100", first, second, orientation="diagonal")


def test_natural_size_and_dock_resize():
    first, second = make_panes()
    sp = Splitter(0, 0, "400x100", first, second)
    assert sp.natural_width(10) == 40 and sp.natural_height(10) == 10
    sp.dock_resize(20, 5, 10)
    assert sp.width == 200 and sp.height == 50


def test_default_ratio_centers_the_bar():
    app = make_app()
    first, second = make_panes()
    sp = Splitter(0, 0, "400x100", first, second)
    app.add(sp)
    app.snapshot()
    assert sp._span == 40
    assert sp._divider_at == 20  # ratio 0.5 of a 40-cell span


def test_contains_matches_only_the_bar_cells():
    app = make_app()
    first, second = make_panes()
    sp = Splitter(0, 0, "400x100", first, second)
    app.add(sp)
    app.snapshot()
    bar_col = sp.abs_x + sp._divider_at
    assert sp.contains(bar_col, sp.abs_y)
    assert sp.contains(bar_col, sp.abs_y + sp._vh - 1)
    assert not sp.contains(bar_col - 1, sp.abs_y)
    assert not sp.contains(bar_col + 1, sp.abs_y)
    assert not sp.contains(bar_col, sp.abs_y + sp._vh)  # one row below the pane


def test_keyboard_resize_horizontal():
    app = make_app()
    first, second = make_panes()
    sp = Splitter(0, 0, "400x100", first, second, step=2)
    app.add(sp)
    app.snapshot()
    start = sp._divider_at
    sp.on_key(Key.RIGHT)
    app.snapshot()
    assert sp._divider_at == start + 2
    sp.on_key(Key.LEFT)
    sp.on_key(Key.LEFT)
    app.snapshot()
    assert sp._divider_at == start - 2


def test_keyboard_resize_vertical_uses_up_down():
    app = make_app()
    first, second = make_panes()
    sp = Splitter(0, 0, "400x100", first, second, orientation="vertical", step=1)
    app.add(sp)
    app.snapshot()
    start = sp._divider_at
    sp.on_key(Key.DOWN)
    app.snapshot()
    assert sp._divider_at == start + 1
    # left/right must not affect a vertical splitter
    sp.on_key(Key.RIGHT)
    app.snapshot()
    assert sp._divider_at == start + 1


def test_home_end_snap_to_min_size_extents():
    app = make_app()
    first, second = make_panes()
    sp = Splitter(0, 0, "400x100", first, second, min_size=5)
    app.add(sp)
    app.snapshot()
    sp.on_key(Key.HOME)
    app.snapshot()
    assert sp._divider_at == 5
    sp.on_key(Key.END)
    app.snapshot()
    assert sp._divider_at == sp._span - 1 - 5


def test_min_size_clamps_resize_and_drag():
    app = make_app()
    first, second = make_panes()
    sp = Splitter(0, 0, "400x100", first, second, min_size=5)
    app.add(sp)
    app.snapshot()
    sp._set_from_coord(sp.abs_x)  # drag all the way to the left edge
    app.snapshot()
    assert sp._divider_at == 5
    sp._set_from_coord(sp.abs_x + 1000)  # drag past the right edge
    app.snapshot()
    assert sp._divider_at == sp._span - 1 - 5


def test_mouse_click_and_drag_move_the_bar():
    app = make_app()
    first, second = make_panes()
    sp = Splitter(0, 0, "400x100", first, second)
    app.add(sp)
    app.snapshot()
    bar_col = sp.abs_x + sp._divider_at

    sp.on_mouse_click(bar_col, sp.abs_y)
    assert sp._dragging is True
    sp.on_mouse_drag(bar_col + 10, sp.abs_y)
    app.snapshot()
    assert sp._divider_at == sp._divider_at  # sanity: still an int in range
    assert 0 <= sp._divider_at < sp._span

    sp.on_mouse_release(bar_col + 10, sp.abs_y)
    assert sp._dragging is False


def test_click_on_bar_steals_focus_even_with_focusable_panes():
    # A container normally defers focus to its first focusable descendant on
    # click (matching Tab) -- Splitter overrides that specifically for a
    # click that lands on the bar itself, so the drag that follows (which
    # App always routes to self.focused) reaches the Splitter, not the button.
    app = make_app()
    left_box = Box(0, 0, "150x100", title="Left")
    btn = Button(1, 1, "Click")
    left_box.add(btn)
    right_box = Box(0, 0, "150x100", title="Right")

    sp = Splitter(0, 0, "400x100", left_box, right_box)
    app.add(sp)
    app.focus(btn)
    app.snapshot()

    bar_col = sp.abs_x + sp._divider_at
    app._dispatch_input(MouseClick(bar_col, sp.abs_y, 0))
    assert app.focused is sp

    app._dispatch_input(MouseDrag(bar_col + 8, sp.abs_y, 0))
    app.snapshot()
    assert sp._divider_at == sp._divider_at  # drag reached the splitter, not the button
    assert app.focused is sp


def test_clicking_inside_a_pane_still_focuses_its_descendant():
    app = make_app()
    left_box = Box(0, 0, "150x100", title="Left")
    btn = Button(1, 1, "Click")
    left_box.add(btn)
    right_box = Box(0, 0, "150x100", title="Right")
    sp = Splitter(0, 0, "400x100", left_box, right_box)
    app.add(sp)
    app.snapshot()

    app._dispatch_input(MouseClick(btn.abs_x, btn.abs_y, 0))
    assert app.focused is btn


def test_bar_is_a_tab_stop_when_no_pane_has_focusable_content():
    app = make_app()
    first, second = make_panes()
    sp = Splitter(0, 0, "400x100", first, second)
    app.add(sp)
    app.snapshot()
    assert app._focusables_in(sp) == [sp]


def test_snapshot_renders_the_bar_character():
    app = make_app()
    first, second = make_panes()
    sp = Splitter(0, 0, "400x100", first, second)
    app.add(sp)
    snap = app.snapshot()
    assert "┃" in snap


def test_vertical_snapshot_renders_horizontal_bar():
    app = make_app()
    first, second = make_panes()
    sp = Splitter(0, 0, "400x100", first, second, orientation="vertical")
    app.add(sp)
    snap = app.snapshot()
    assert "━" in snap


def test_get_and_set_ratio():
    first, second = make_panes()
    sp = Splitter(0, 0, "400x100", first, second)
    assert sp.get_ratio() == 0.5
    sp.set_ratio(0.25)
    assert sp.get_ratio() == 0.25
    sp.set_ratio(-1)  # clamped
    assert sp.get_ratio() == 0.0
    sp.set_ratio(5)  # clamped
    assert sp.get_ratio() == 1.0


def test_panes_are_clipped_to_their_slice():
    # A pane wider than the slice Splitter assigns it (e.g. a long Label,
    # which ignores dock_resize) must not bleed past the bar into the
    # other pane.
    app = make_app()
    first = Label(0, 0, "X" * 100)
    second = Label(0, 0, "second")
    sp = Splitter(0, 0, "400x100", first, second, ratio=0.5)
    app.add(sp)
    snap = app.snapshot().split("\n")[0]
    bar_col = sp.abs_x + sp._divider_at
    assert snap[bar_col] == "┃"
    assert "second" in snap
