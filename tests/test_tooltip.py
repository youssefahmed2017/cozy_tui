from cozy_tui import App, Style
from cozy_tui.events import MouseMove
from cozy_tui.testing import Harness
from cozy_tui.widgets import Button, Tooltip


def make_ui(size="400x100"):
    return Harness(App(full=False, size=size, style=Style(fg="white", bg="black")))


def _fire_pending_timers(app):
    for t in list(app._timers):
        if t.alive:
            t.callback()
            t.alive = False


# ── Tooltip (direct, no App) ──────────────────────────────────────────────


def test_natural_size_from_text():
    btn = Button(0, 0, "Save")
    tip = Tooltip(btn, "hello")
    assert tip.natural_width(1) == len("hello") + 2
    assert tip.natural_height(1) == 1


def test_not_focusable():
    btn = Button(0, 0, "Save")
    assert Tooltip(btn, "hi").focusable is False


def test_positions_below_the_anchor_by_default():
    ui = make_ui()
    app = ui.app
    btn = Button(3, 3, "Save")
    app.add(btn)
    ui.screen
    tip = Tooltip(btn, "hint")
    tip._position(app)
    assert tip.x == btn.abs_x
    assert tip.y == btn.abs_y + btn.natural_height(app.SCALE)


def test_flips_above_when_below_would_overflow():
    ui = make_ui(size="300x60")  # 30x6 cells
    app = ui.app
    btn = Button(2, 5, "X")  # last row
    app.add(btn)
    ui.screen
    tip = Tooltip(btn, "hint")
    tip._position(app)
    assert tip.y == btn.abs_y - 1


def test_clamps_left_when_right_would_overflow():
    ui = make_ui(size="300x60")  # 30 cols
    app = ui.app
    btn = Button(25, 0, "X")
    app.add(btn)
    ui.screen
    tip = Tooltip(btn, "a fairly long tooltip that overflows")
    tip._position(app)
    w = tip.natural_width(1)
    assert tip.x == max(0, app.cols - w)


def test_draw_writes_padded_text():
    ui = make_ui()
    app = ui.app
    btn = Button(2, 2, "Save")
    app.add(btn)
    tip = Tooltip(btn, "hi")
    app.open_overlay(tip, modal=False, dim=False, center=False, close_on_escape=False)
    snap = ui.screen
    # snapshot() rstrips each line, so the padded " hi " loses its trailing
    # space in the string form -- the leading pad is enough to confirm it.
    assert " hi" in snap


# ── App.set_tooltip() ────────────────────────────────────────────────────────


def test_hover_opts_widget_into_mouse_moves():
    ui = make_ui()
    app = ui.app
    btn = Button(2, 2, "Save")
    app.add(btn)
    assert btn.mouse_moves is False
    app.set_tooltip(btn, "Save the file")
    assert btn.mouse_moves is True


def test_hover_schedules_a_delayed_show_not_immediate():
    ui = make_ui()
    app = ui.app
    btn = Button(2, 2, "Save")
    app.add(btn)
    app.set_tooltip(btn, "Save the file")
    ui.screen

    ui.hover((btn.abs_x + 1, btn.abs_y))
    assert app._overlays == []  # not shown yet
    assert any(t.alive for t in app._timers)


def test_quick_pass_through_never_shows_the_tooltip():
    ui = make_ui()
    app = ui.app
    btn = Button(2, 2, "Save")
    app.add(btn)
    app.set_tooltip(btn, "Save the file")
    ui.screen

    ui.hover((btn.abs_x + 1, btn.abs_y))
    ui.hover((0, 50))  # leave before the delay fires
    ui.screen
    assert app._overlays == []
    assert not any(t.alive for t in app._timers)


def test_delay_elapsing_shows_the_tooltip():
    ui = make_ui()
    app = ui.app
    btn = Button(2, 2, "Save")
    app.add(btn)
    app.set_tooltip(btn, "Save the file")
    ui.screen

    ui.hover((btn.abs_x + 1, btn.abs_y))
    _fire_pending_timers(app)
    ui.screen
    assert len(app._overlays) == 1
    tip = app._overlays[-1].widget
    assert isinstance(tip, Tooltip)
    assert tip.text == "Save the file"
    assert tip.anchor is btn


def test_leaving_after_shown_hides_it():
    ui = make_ui()
    app = ui.app
    btn = Button(2, 2, "Save")
    app.add(btn)
    app.set_tooltip(btn, "Save the file")
    ui.screen

    ui.hover((btn.abs_x + 1, btn.abs_y))
    _fire_pending_timers(app)
    ui.screen
    assert len(app._overlays) == 1

    ui.hover((0, 50))
    ui.screen
    assert app._overlays == []


def test_tooltip_is_non_modal_and_does_not_steal_focus():
    ui = make_ui()
    app = ui.app
    btn = Button(2, 2, "Save")
    app.add(btn)
    other = Button(2, 5, "Other")
    app.add(other)
    app.set_tooltip(btn, "Save the file")
    app.focus(other)
    ui.screen

    ui.hover((btn.abs_x + 1, btn.abs_y))
    _fire_pending_timers(app)
    ui.screen
    assert app.focused is other  # unaffected by the tooltip showing
    assert app._overlays[-1].modal is False


def test_set_tooltip_replaces_any_existing_enter_leave_handlers():
    ui = make_ui()
    app = ui.app
    btn = Button(2, 2, "Save")
    app.add(btn)
    calls = []
    btn.on_enter(lambda w: calls.append("custom-enter"))
    app.set_tooltip(btn, "Save the file")
    ui.screen

    ui.hover((btn.abs_x + 1, btn.abs_y))
    assert calls == []  # the custom handler was replaced, not chained
