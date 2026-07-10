from cozy_tui import App, Style
from cozy_tui.events import MouseMove
from cozy_tui.widgets import Button, Tooltip


def make_app(size="400x100"):
    return App(full=False, size=size, style=Style(fg="white", bg="black"))


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
    app = make_app()
    btn = Button(3, 3, "Save")
    app.add(btn)
    app.snapshot()
    tip = Tooltip(btn, "hint")
    tip._position(app)
    assert tip.x == btn.abs_x
    assert tip.y == btn.abs_y + btn.natural_height(app.SCALE)


def test_flips_above_when_below_would_overflow():
    app = make_app(size="300x60")  # 30x6 cells
    btn = Button(2, 5, "X")  # last row
    app.add(btn)
    app.snapshot()
    tip = Tooltip(btn, "hint")
    tip._position(app)
    assert tip.y == btn.abs_y - 1


def test_clamps_left_when_right_would_overflow():
    app = make_app(size="300x60")  # 30 cols
    btn = Button(25, 0, "X")
    app.add(btn)
    app.snapshot()
    tip = Tooltip(btn, "a fairly long tooltip that overflows")
    tip._position(app)
    w = tip.natural_width(1)
    assert tip.x == max(0, app.cols - w)


def test_draw_writes_padded_text():
    app = make_app()
    btn = Button(2, 2, "Save")
    app.add(btn)
    tip = Tooltip(btn, "hi")
    app.open_overlay(tip, modal=False, dim=False, center=False, close_on_escape=False)
    snap = app.snapshot()
    # snapshot() rstrips each line, so the padded " hi " loses its trailing
    # space in the string form -- the leading pad is enough to confirm it.
    assert " hi" in snap


# ── App.set_tooltip() ────────────────────────────────────────────────────────


def test_hover_opts_widget_into_mouse_moves():
    app = make_app()
    btn = Button(2, 2, "Save")
    app.add(btn)
    assert btn.mouse_moves is False
    app.set_tooltip(btn, "Save the file")
    assert btn.mouse_moves is True


def test_hover_schedules_a_delayed_show_not_immediate():
    app = make_app()
    btn = Button(2, 2, "Save")
    app.add(btn)
    app.set_tooltip(btn, "Save the file")
    app.snapshot()

    app._dispatch_input(MouseMove(btn.abs_x + 1, btn.abs_y))
    assert app._overlays == []  # not shown yet
    assert any(t.alive for t in app._timers)


def test_quick_pass_through_never_shows_the_tooltip():
    app = make_app()
    btn = Button(2, 2, "Save")
    app.add(btn)
    app.set_tooltip(btn, "Save the file")
    app.snapshot()

    app._dispatch_input(MouseMove(btn.abs_x + 1, btn.abs_y))
    app._dispatch_input(MouseMove(0, 50))  # leave before the delay fires
    app.snapshot()
    assert app._overlays == []
    assert not any(t.alive for t in app._timers)


def test_delay_elapsing_shows_the_tooltip():
    app = make_app()
    btn = Button(2, 2, "Save")
    app.add(btn)
    app.set_tooltip(btn, "Save the file")
    app.snapshot()

    app._dispatch_input(MouseMove(btn.abs_x + 1, btn.abs_y))
    _fire_pending_timers(app)
    app.snapshot()
    assert len(app._overlays) == 1
    tip = app._overlays[-1].widget
    assert isinstance(tip, Tooltip)
    assert tip.text == "Save the file"
    assert tip.anchor is btn


def test_leaving_after_shown_hides_it():
    app = make_app()
    btn = Button(2, 2, "Save")
    app.add(btn)
    app.set_tooltip(btn, "Save the file")
    app.snapshot()

    app._dispatch_input(MouseMove(btn.abs_x + 1, btn.abs_y))
    _fire_pending_timers(app)
    app.snapshot()
    assert len(app._overlays) == 1

    app._dispatch_input(MouseMove(0, 50))
    app.snapshot()
    assert app._overlays == []


def test_tooltip_is_non_modal_and_does_not_steal_focus():
    app = make_app()
    btn = Button(2, 2, "Save")
    app.add(btn)
    other = Button(2, 5, "Other")
    app.add(other)
    app.set_tooltip(btn, "Save the file")
    app.focus(other)
    app.snapshot()

    app._dispatch_input(MouseMove(btn.abs_x + 1, btn.abs_y))
    _fire_pending_timers(app)
    app.snapshot()
    assert app.focused is other  # unaffected by the tooltip showing
    assert app._overlays[-1].modal is False


def test_set_tooltip_replaces_any_existing_enter_leave_handlers():
    app = make_app()
    btn = Button(2, 2, "Save")
    app.add(btn)
    calls = []
    btn.on_enter(lambda w: calls.append("custom-enter"))
    app.set_tooltip(btn, "Save the file")
    app.snapshot()

    app._dispatch_input(MouseMove(btn.abs_x + 1, btn.abs_y))
    assert calls == []  # the custom handler was replaced, not chained
