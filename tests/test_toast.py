"""Toast notifications: creation, stacking, rendering, and auto-dismiss."""

import time

from cozy_tui import App, Style
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
