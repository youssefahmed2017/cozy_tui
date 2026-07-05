"""App scheduled-wake timers: after / every / cancel."""

import time

from cozy_tui import App, Style


def make_app():
    return App(full=False, size="800x300", style=Style(fg="white", bg="black"))


def test_after_fires_once_past_its_deadline():
    app = make_app()
    fired = []
    t = app.after(1.0, lambda: fired.append(1))

    app._drain_timers(t.deadline - 0.5)  # before the deadline
    assert fired == []
    app._drain_timers(t.deadline + 0.01)  # past it
    assert fired == [1]
    assert t not in app._timers  # one-shot is dropped after firing


def test_every_reschedules_on_its_interval():
    app = make_app()
    fired = []
    t = app.every(0.5, lambda: fired.append(1))

    app._drain_timers(t.deadline + 0.01)
    assert len(fired) == 1
    assert t.alive and t in app._timers  # still scheduled
    app._drain_timers(t.deadline + 0.01)
    assert len(fired) == 2


def test_cancel_prevents_firing():
    app = make_app()
    fired = []
    t = app.after(0.1, lambda: fired.append(1))
    app.cancel(t)
    app._drain_timers(t.deadline + 1.0)
    assert fired == []
    assert t not in app._timers


def test_next_deadline_reports_the_soonest():
    app = make_app()
    now = time.monotonic()
    app.after(2.0, lambda: None)
    app.after(0.5, lambda: None)
    d = app._next_timer_deadline(now)
    assert 0.3 < d <= 0.5
    assert make_app()._next_timer_deadline(now) is None  # none scheduled
