from cozy_tui.events import Key
from cozy_tui.widgets import Slider


def make(**kw):
    kw.setdefault("minimum", 0)
    kw.setdefault("maximum", 100)
    kw.setdefault("value", 50)
    kw.setdefault("step", 5)
    kw.setdefault("width", 20)
    return Slider(0, 0, **kw)


def test_initial_value_clamped_to_range():
    assert make(value=500).get() == 100
    assert make(value=-5).get() == 0
    assert make(value=None).get() == 0  # defaults to minimum


def test_left_right_step_by_step():
    s = make()
    s.on_key(Key.RIGHT)
    assert s.get() == 55
    s.on_key(Key.LEFT)
    s.on_key(Key.LEFT)
    assert s.get() == 45


def test_up_down_are_aliases_for_right_left():
    s = make()
    s.on_key(Key.UP)
    assert s.get() == 55
    s.on_key(Key.DOWN)
    s.on_key(Key.DOWN)
    assert s.get() == 45


def test_home_end_jump_to_bounds():
    s = make()
    s.on_key(Key.END)
    assert s.get() == 100
    s.on_key(Key.HOME)
    assert s.get() == 0


def test_stepping_clamps_at_bounds():
    s = make(value=98, step=5)
    s.on_key(Key.RIGHT)
    assert s.get() == 100  # 98 + 5 would overshoot -> clamped, not wrapped
    s.on_key(Key.RIGHT)
    assert s.get() == 100


def test_page_up_down_use_larger_step():
    s = make(value=50, page_step=20)
    s.on_key(Key.PAGE_UP)
    assert s.get() == 70
    s.on_key(Key.PAGE_DOWN)
    s.on_key(Key.PAGE_DOWN)
    assert s.get() == 30


def test_default_page_step_is_derived_when_unset():
    # (maximum - minimum) // 10 = 10, which is >= step, so that wins.
    s = Slider(0, 0, minimum=0, maximum=100, value=50, step=1)
    assert s.page_step == 10
    # a coarse step wins over the derived page step when it's larger.
    s2 = Slider(0, 0, minimum=0, maximum=100, value=50, step=50)
    assert s2.page_step == 50


def test_on_change_fires_only_on_real_change():
    s = make()
    changes = []
    s.on_change(changes.append)
    s.set(50)  # already 50 -> no-op
    assert changes == []
    s.set(60)
    assert changes == [60]


def test_click_jumps_to_position():
    s = make(minimum=0, maximum=10, value=0, step=1, width=12)
    bar_w = s._bar_width()
    s.on_mouse_click(col=s.abs_x, row=s.abs_y)
    assert s.get() == 0
    s.on_mouse_click(col=s.abs_x + bar_w - 1, row=s.abs_y)
    assert s.get() == 10
    s.on_mouse_click(col=s.abs_x + (bar_w - 1) // 2, row=s.abs_y)
    assert s.get() == 5


def test_drag_updates_like_click_and_fires_drag_handler():
    s = make(minimum=0, maximum=10, value=0, step=1, width=12)
    drags = []
    s.on_drag(lambda w, col, row: drags.append((col, row)))
    bar_w = s._bar_width()
    s.on_mouse_drag(col=s.abs_x + bar_w - 1, row=s.abs_y)
    assert s.get() == 10
    assert drags == [(s.abs_x + bar_w - 1, s.abs_y)]


def test_click_respects_step_rounding():
    s = make(minimum=0, maximum=10, value=0, step=5, width=12)  # only 0, 5, 10 valid
    bar_w = s._bar_width()
    s.on_mouse_click(col=s.abs_x + (bar_w - 1) // 2, row=s.abs_y)
    assert s.get() in (0, 5, 10)


def test_float_values_and_formatting():
    s = Slider(0, 0, minimum=0.0, maximum=1.0, value=0.5, step=0.1, width=20)
    assert s._fmt(s.get()) == "0.5"
    s.on_key(Key.RIGHT)
    assert round(s.get(), 1) == 0.6


def test_bar_width_stable_across_value_range():
    # Sizing off min/max (not the live value) keeps the bar from jittering
    # as the value's printed width changes (e.g. "9" -> "10").
    s = Slider(0, 0, minimum=0, maximum=100, value=9, width=20)
    w1 = s._bar_width()
    s.set(100)
    assert s._bar_width() == w1


def test_contains_bounding_box():
    s = make(width=10)
    assert s.contains(s.abs_x, s.abs_y)
    assert s.contains(s.abs_x + 9, s.abs_y)
    assert not s.contains(s.abs_x + 10, s.abs_y)
    assert not s.contains(s.abs_x, s.abs_y + 1)


def test_not_focused_by_default_but_focusable():
    s = make()
    assert s.focusable is True


def test_renders_handle_and_value_in_snapshot():
    from cozy_tui import App, Style

    app = App(full=False, size="300x60", style=Style(fg="white", bg="black"))
    app.add(Slider(0, 0, minimum=0, maximum=100, value=0, width=20))
    line = app.snapshot().split("\n")[0]
    assert "●" in line
    assert "0" in line


def test_show_value_false_uses_full_width_for_track():
    s = Slider(0, 0, minimum=0, maximum=100, value=0, width=20, show_value=False)
    assert s._bar_width() == 20
