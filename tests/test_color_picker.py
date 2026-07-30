from cozy_tui.events import Key
from cozy_tui.widgets import ColorPicker
from cozy_tui.widgets.selection import color_picker as color_picker_mod


def make(**kw):
    kw.setdefault("color", (10, 100, 200))
    kw.setdefault("width", 16)
    kw.setdefault("step", 1)
    kw.setdefault("page_step", 16)
    return ColorPicker(0, 0, **kw)


def test_initial_rgb_and_hex():
    cp = make()
    assert cp.rgb == (10, 100, 200)
    assert cp.hex == "#0a64c8"


def test_accepts_hex_string_and_named_color():
    from cozy_tui.ansi import resolve_rgb

    assert ColorPicker(0, 0, "#ff8800").rgb == (255, 136, 0)
    assert ColorPicker(0, 0, "red").rgb == resolve_rgb("red")


def test_rejects_unrecognized_color_string():
    import pytest

    with pytest.raises(ValueError):
        ColorPicker(0, 0, "not-a-color")


def test_left_right_step_the_active_channel_only():
    cp = make()
    cp.on_key(Key.RIGHT)
    assert cp.rgb == (11, 100, 200)  # R is the default active channel
    cp.on_key(Key.LEFT)
    cp.on_key(Key.LEFT)
    assert cp.rgb == (9, 100, 200)


def test_up_down_move_the_active_channel_clamped_not_wrapped():
    cp = make()
    cp.on_key(Key.UP)  # already at R (0) -- clamped, not wrapped to B
    cp.on_key(Key.RIGHT)
    assert cp.rgb == (11, 100, 200)

    cp.on_key(Key.DOWN)
    cp.on_key(Key.DOWN)
    cp.on_key(Key.DOWN)  # already at B (2) -- clamped
    cp.on_key(Key.RIGHT)
    assert cp.rgb == (11, 100, 201)


def test_page_up_down_use_the_larger_step_on_the_active_channel():
    cp = make()
    cp.on_key(Key.DOWN)  # -> G
    cp.on_key(Key.PAGE_UP)
    assert cp.rgb == (10, 116, 200)
    cp.on_key(Key.PAGE_DOWN)
    cp.on_key(Key.PAGE_DOWN)
    assert cp.rgb == (10, 84, 200)


def test_home_end_jump_the_active_channel_to_bounds():
    cp = make()
    cp.on_key(Key.DOWN)
    cp.on_key(Key.DOWN)  # -> B
    cp.on_key(Key.END)
    assert cp.rgb == (10, 100, 255)
    cp.on_key(Key.HOME)
    assert cp.rgb == (10, 100, 0)


def test_on_change_fires_with_full_rgb_only_on_real_change():
    cp = make()
    changes = []
    cp.on_change(changes.append)
    cp.on_key(Key.UP)  # channel switch only, no value change -> no fire
    assert changes == []
    cp.on_key(Key.RIGHT)
    assert changes == [(11, 100, 200)]


def test_set_rgb_updates_all_channels():
    cp = make()
    cp.set_rgb((1, 2, 3))
    assert cp.rgb == (1, 2, 3)
    assert cp.hex == "#010203"


def test_click_on_a_row_jumps_that_channel_and_makes_it_active():
    cp = make(color=(0, 0, 0), width=12)
    bar_w = cp._sliders[2]._bar_width()
    cp.on_mouse_click(
        col=cp.abs_x + 2 + bar_w - 1, row=cp.abs_y + 2
    )  # B row, far right
    assert cp._channel == 2
    assert cp.rgb == (0, 0, 255)


def test_drag_continues_on_the_channel_selected_by_the_preceding_click():
    cp = make(color=(0, 0, 0), width=12)
    bar_w = cp._sliders[1]._bar_width()
    cp.on_mouse_click(col=cp.abs_x + 2, row=cp.abs_y + 1)  # select G
    cp.on_mouse_drag(col=cp.abs_x + 2 + bar_w - 1, row=cp.abs_y + 1)
    assert cp.rgb == (0, 255, 0)


def test_drag_fires_the_registered_drag_handler():
    cp = make()
    drags = []
    cp.on_drag(lambda w, col, row: drags.append((col, row)))
    cp.on_mouse_drag(col=cp.abs_x + 5, row=cp.abs_y)
    assert drags == [(cp.abs_x + 5, cp.abs_y)]


def test_ctrl_e_copies_hex_and_fires_on_copy(monkeypatch):
    cp = make()
    copied = []
    monkeypatch.setattr(color_picker_mod, "_copy_to_clipboard", copied.append)
    fired = []
    cp.on_copy(lambda kind, text: fired.append((kind, text)))

    cp.on_key(Key.ctrl("e"))

    assert copied == ["#0a64c8"]
    assert fired == [("hex", "#0a64c8")]


def test_ctrl_r_copies_rgb_and_fires_on_copy(monkeypatch):
    cp = make()
    copied = []
    monkeypatch.setattr(color_picker_mod, "_copy_to_clipboard", copied.append)
    fired = []
    cp.on_copy(lambda kind, text: fired.append((kind, text)))

    cp.on_key(Key.ctrl("r"))

    assert copied == ["10, 100, 200"]
    assert fired == [("rgb", "10, 100, 200")]


def test_contains_bounding_box():
    cp = make(width=10)
    assert cp.contains(cp.abs_x, cp.abs_y)
    assert cp.contains(cp.abs_x, cp.abs_y + cp.natural_height(1) - 1)
    assert not cp.contains(cp.abs_x, cp.abs_y + cp.natural_height(1))
    assert not cp.contains(cp.abs_x + cp.natural_width(1), cp.abs_y)


def test_is_a_single_focusable_widget_and_wants_page_keys_routed_to_it():
    cp = make()
    assert cp.focusable is True
    # PageUp/PageDown are otherwise intercepted by App._dispatch_input to
    # scroll the base UI unless the focused widget opts in -- see app.py's
    # `getattr(self.focused, "scrollable", False)` check.
    assert cp.scrollable is True


def test_renders_channels_hex_rgb_and_hint_in_snapshot():
    from cozy_tui import App, Style

    app = App(full=False, size="400x200", style=Style(fg="white", bg="black"))
    app.add(ColorPicker(0, 0, (10, 100, 200), width=16))
    lines = app.snapshot().split("\n")

    assert lines[0].startswith("R ")
    assert lines[1].startswith("G ")
    assert lines[2].startswith("B ")
    assert "HEX: #0a64c8" in lines[4]
    assert "RGB: (10, 100, 200)" in lines[5]
    assert "Ctrl+E" in lines[6] and "Ctrl+R" in lines[6]


def test_hex_and_rgb_lines_are_colored_with_the_current_color():
    from cozy_tui import App

    app = App(full=False, size="400x200")
    cp = ColorPicker(0, 0, (255, 0, 0), width=16)
    app.add(cp)
    app._compose()

    hex_line = "".join(c.char for c in app.buffer[4])
    col = hex_line.index("#")
    assert app.buffer[4][col].style.fg == "rgb(255,0,0)"
    assert app.buffer[5][0].style.fg == "rgb(255,0,0)"

    cp.set_rgb((0, 255, 0))
    app._compose()
    assert app.buffer[4][col].style.fg == "rgb(0,255,0)"
