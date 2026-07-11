"""Toast notifications: creation, stacking, rendering, and auto-dismiss."""

import time

from cozy_tui import App, Style
from cozy_tui.events import MouseClick, MouseMove
from cozy_tui.widgets import Toast


def make_app():
    return App(full=False, size="800x300", style=Style(fg="white", bg="black"))


def test_toast_opens_a_nonmodal_overlay():
    app = make_app()
    t = app.toast("Saved", level="success")
    assert t in app._toasts
    entry = next(e for e in app._overlays if e.widget is t)
    assert entry.modal is False and entry.dim is False and entry.center is False


def test_toast_renders_message_and_icon():
    app = make_app()
    app.toast("File saved", level="success")
    snap = app.snapshot()
    assert "File saved" in snap and "✓" in snap


def test_level_maps_to_icon_and_falls_back_to_info():
    app = make_app()
    assert app.toast("a", level="error").icon == "✗"
    assert app.toast("b", level="warning").icon == "⚠"
    assert app.toast("c", level="bogus").level == "info"
    assert app.toast("d", icon="🎉").icon == "🎉"  # explicit icon wins


def test_multiple_toasts_stack_without_overlap():
    app = make_app()
    toasts = [app.toast(str(i)) for i in range(3)]
    w = toasts[0]._content_width(app.cols)
    tops = sorted(t._place(app, w)[1] for t in toasts)
    assert tops[1] - tops[0] >= Toast.HEIGHT
    assert tops[2] - tops[1] >= Toast.HEIGHT


def test_auto_dismiss_removes_toast_after_duration():
    app = make_app()
    t = app.toast("bye", duration=2.0)
    assert t in app._toasts

    app._drain_timers(time.monotonic() + 2.1)
    assert t not in app._toasts
    assert not any(e.widget is t for e in app._overlays)


def test_zero_duration_toast_is_sticky():
    app = make_app()
    t = app.toast("stays", duration=0)
    app._drain_timers(time.monotonic() + 100)
    assert t in app._toasts  # no dismiss timer scheduled


# ── actions ───────────────────────────────────────────────────────────────────


def _render_and_click(app, toast, index):
    """Render once (populates toast._bounds), then dispatch a real MouseClick
    at the given action button's location -- exercising the full
    App._hit_non_modal_overlay dispatch path, not just the widget directly."""
    app.render()
    left, top, w, _h = toast._bounds
    _text, _idx, start, _end = toast._button_row_spans(left, w)[index]
    app._dispatch_input(MouseClick(start + 1, top + 2, 0))


def test_actions_render_as_button_row():
    app = make_app()
    app.toast("Item deleted", actions=[("Undo", lambda: None), ("Dismiss", None)])
    snap = app.snapshot()
    assert "[ Undo ]" in snap
    assert "[ Dismiss ]" in snap


def test_plain_toast_has_no_button_row():
    app = make_app()
    app.toast("Saved")
    snap = app.snapshot()
    assert "[" not in snap


def test_clicking_an_action_fires_its_callback_and_dismisses_the_toast():
    app = make_app()
    calls = []
    t = app.toast(
        "Item deleted",
        actions=[("Undo", lambda: calls.append("undo")), ("Dismiss", None)],
        duration=0,
    )
    _render_and_click(app, t, 0)
    assert calls == ["undo"]
    assert t not in app._toasts


def test_dismiss_action_with_no_callback_just_closes():
    app = make_app()
    t = app.toast(
        "Item deleted", actions=[("Undo", None), ("Dismiss", None)], duration=0
    )
    _render_and_click(app, t, 1)
    assert t not in app._toasts


def test_clicking_a_toast_action_never_moves_focus():
    from cozy_tui.widgets import Button

    app = make_app()
    btn = Button(0, 0, "Go")
    app.add(btn)
    app.focus(btn)
    t = app.toast("Item deleted", actions=[("Undo", lambda: None)], duration=0)
    _render_and_click(app, t, 0)
    assert app.focused is btn  # untouched by the toast click


def test_clicking_the_message_row_does_nothing():
    app = make_app()
    calls = []
    t = app.toast(
        "Item deleted", actions=[("Undo", lambda: calls.append(1))], duration=0
    )
    app.render()
    left, top, _w, _h = t._bounds
    app._dispatch_input(MouseClick(left + 2, top + 1, 0))  # message row, not buttons
    assert calls == []
    assert t in app._toasts


def test_hover_pauses_and_leaving_restarts_the_dismiss_timer():
    app = make_app()
    t = app.toast("Item deleted", actions=[("Undo", None)], duration=2.0)
    app.render()
    left, top, _w, _h = t._bounds

    app._dispatch_input(MouseMove(left + 2, top + 1))
    assert app._hovered is t
    app._drain_timers(time.monotonic() + 2.1)
    assert t in app._toasts  # timer was cancelled by the hover

    app._dispatch_input(MouseMove(0, 0))  # move away -> leave -> re-arm
    assert app._hovered is None
    app._drain_timers(time.monotonic() + 2.1)
    assert t not in app._toasts  # the restarted timer fired


def test_plain_toast_ignores_hover_and_still_auto_dismisses_on_schedule():
    # No actions -> no on_enter/on_leave wiring at all; a click/hover over it
    # still shouldn't crash or do anything toast-specific.
    app = make_app()
    t = app.toast("Saved", duration=2.0)
    app.render()
    left, top, _w, _h = t._bounds
    app._dispatch_input(MouseMove(left + 2, top + 2))
    app._drain_timers(time.monotonic() + 2.1)
    assert t not in app._toasts


def test_clicking_a_plain_toast_is_swallowed_not_passed_through():
    # An overlay sits visually on top; a click on its own footprint should
    # never leak through to a base-UI widget sitting directly underneath it.
    from cozy_tui.widgets import Button

    app = make_app()
    clicked = []
    btn = Button(0, 0, "Go")
    btn.on_click(lambda b: clicked.append(1))
    app.add(btn)
    t = app.toast("Saved")
    app.render()  # establishes t._bounds

    left, top, _w, _h = t._bounds
    btn.x, btn.y = left, top + 2  # move the button directly under the toast
    app._dispatch_input(MouseClick(left + 2, top + 2, 0))
    assert clicked == []
