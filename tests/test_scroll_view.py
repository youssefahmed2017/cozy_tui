"""ScrollView: clipping, scrollbar, autoscroll, and keyboard/mouse scrolling."""

from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.widgets import Label, ScrollView


def make_app():
    return App(full=False, size="800x300", style=Style(fg="white", bg="black"))


def make_sv(app, *, autoscroll=True, n=30):
    sv = ScrollView(0, 0, "260x80", autoscroll=autoscroll)  # 26 x 8 cells
    for i in range(n):
        sv.add(Label(0, i, f"row{i:02d}"))
    app.add(sv)
    app.focus(sv)
    return sv


def test_add_returns_widget_and_children_exposes_content():
    sv = ScrollView(0, 0, "100x100")
    w = Label(0, 0, "a")
    assert sv.add(w) is w
    assert sv.children == [w]
    assert w.parent is sv


def test_content_height_is_the_lowest_child_bottom():
    sv = ScrollView(0, 0, "100x100")
    sv.add(Label(0, 0, "a"))
    sv.add(Label(0, 9, "b"))  # bottom = 9 + 1
    assert sv.content_height(10) == 10


def test_only_the_visible_slice_renders():
    app = make_app()
    sv = make_sv(app, autoscroll=False)
    sv.scroll_to_top()
    snap = app.snapshot()
    assert "row00" in snap and "row07" in snap  # 8 rows tall
    assert "row08" not in snap and "row20" not in snap


def test_autoscroll_pins_to_bottom():
    app = make_app()
    sv = make_sv(app, autoscroll=True)
    app.snapshot()  # a draw pins to the bottom
    assert sv._scroll == sv._max_scroll
    snap = app.snapshot()
    assert "row29" in snap and "row00" not in snap


def test_no_autoscroll_starts_at_top():
    app = make_app()
    sv = make_sv(app, autoscroll=False)
    snap = app.snapshot()
    assert "row00" in snap and "row29" not in snap


def test_scroll_clamps_and_pin_toggles():
    app = make_app()
    sv = make_sv(app)
    app.snapshot()
    assert sv._pin_bottom  # started pinned

    sv.scroll_by(-3)
    assert not sv._pin_bottom  # scrolling up unpins
    sv.scroll_to(999)
    assert sv._scroll == sv._max_scroll and sv._pin_bottom  # back at bottom re-pins
    sv.scroll_to(-10)
    assert sv._scroll == 0


def test_keyboard_scrolling():
    app = make_app()
    sv = make_sv(app)
    app.snapshot()  # establishes viewport height / max scroll
    sv.scroll_to_top()

    sv.on_key(Key.DOWN)
    assert sv._scroll == 1
    sv.on_key(Key.PAGE_DOWN)
    assert sv._scroll == 1 + max(1, sv._vh - 1)
    sv.on_key(Key.END)
    assert sv._scroll == sv._max_scroll
    sv.on_key(Key.HOME)
    assert sv._scroll == 0


def test_scrollbar_only_shows_when_content_overflows():
    app = make_app()
    over = make_sv(app)  # 30 rows in an 8-row viewport
    app.snapshot()
    assert ScrollView.THUMB in app.snapshot()
    assert over._bar_col is not None

    app2 = make_app()
    fits = make_sv(app2, n=3)  # fits within the viewport
    snap = app2.snapshot()
    assert ScrollView.THUMB not in snap and fits._bar_col is None


def test_dragging_the_scrollbar_thumb_scrolls():
    app = make_app()
    sv = make_sv(app)
    app.snapshot()
    col = sv._bar_col

    sv.on_mouse_click(col, sv.abs_y)  # press at the top of the bar
    assert sv._scroll == 0
    sv.on_mouse_drag(col, sv.abs_y + sv._vh - 1)  # drag to the bottom
    assert sv._scroll == sv._max_scroll


def test_is_scrollable_for_wheel_routing():
    assert ScrollView.scrollable is True


def test_dock_resize_sets_cell_size():
    sv = ScrollView(0, 0, "100x100")
    sv.dock_resize(50, 20, 10)
    assert sv.natural_width(10) == 50 and sv.natural_height(10) == 20


def test_smooth_scroll_eases_toward_target(monkeypatch):
    import cozy_tui.motion as motion

    app = make_app()
    sv = make_sv(app, autoscroll=False)  # starts at top; first layout snaps _disp=0
    app.snapshot()
    clock = [100.0]
    monkeypatch.setattr(motion.time, "monotonic", lambda: clock[0])

    sv.scroll_to(20)  # target jumps immediately, display eases
    app.snapshot()  # a draw at t=0: tween just started
    assert sv._scroll == 20
    assert sv._disp < 20  # hasn't jumped to the target yet

    clock[0] = 100.2  # past the 0.12s ease
    app.snapshot()
    assert round(sv._disp) == 20  # settled on the target


def test_smooth_false_snaps_instantly():
    app = make_app()
    sv = ScrollView(0, 0, "260x80", autoscroll=False, smooth=False)
    for i in range(30):
        sv.add(Label(0, i, f"row{i:02d}"))
    app.add(sv)
    app.snapshot()
    sv.scroll_to(10)
    app.snapshot()
    assert sv._disp == 10  # no easing when smooth=False
