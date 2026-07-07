"""App(catch_errors=...): show an unhandled crash as a full-screen TracebackView
instead of propagating a bare exception out of run() — on by default, matching
Textual; pass catch_errors=False to get a plain propagating exception back."""

import pytest

from cozy_tui import App, Style


def make_app(**kw):
    return App(full=False, size="400x100", style=Style(fg="white", bg="black"), **kw)


def test_catch_errors_defaults_to_true():
    assert make_app().catch_errors is True


def test_catch_errors_false_propagates_the_exception(monkeypatch):
    app = make_app(catch_errors=False)

    def boom(self):
        raise ValueError("boom")

    monkeypatch.setattr(App, "_compose", boom)
    with pytest.raises(ValueError, match="boom"):
        app.run()
    assert app._running is False  # terminal state still cleaned up before re-raising


def test_catch_errors_true_shows_crash_screen_instead_of_raising(monkeypatch):
    app = make_app()  # catch_errors defaults to True

    def boom(self):
        raise ValueError("boom")

    monkeypatch.setattr(App, "_compose", boom)

    calls = []
    monkeypatch.setattr(
        "cozy_tui.crash_screen.show_traceback", lambda exc: calls.append(exc)
    )

    app.run()  # must not raise

    assert app._running is False
    assert len(calls) == 1
    assert isinstance(calls[0], ValueError)
    assert str(calls[0]) == "boom"


def test_catch_errors_true_still_lets_keyboard_interrupt_through(monkeypatch):
    app = make_app()  # catch_errors defaults to True

    def interrupt(self):
        raise KeyboardInterrupt

    monkeypatch.setattr(App, "_compose", interrupt)
    calls = []
    monkeypatch.setattr(
        "cozy_tui.crash_screen.show_traceback", lambda exc: calls.append(exc)
    )

    app.run()  # KeyboardInterrupt is swallowed on its own, not routed to the crash screen

    assert calls == []


def test_crash_screen_itself_never_recurses_on_its_own_crash(monkeypatch):
    # show_traceback's own App must use catch_errors=False: if IT crashes (a
    # bug in the crash screen, or — as here — some App-wide fault that also
    # breaks the crash screen's render), it must fail loudly instead of
    # calling show_traceback on itself and recursing without end.
    import cozy_tui.crash_screen as crash_screen

    def boom(self):
        raise ValueError("boom")

    monkeypatch.setattr(App, "_compose", boom)
    with pytest.raises(ValueError, match="boom"):
        crash_screen.show_traceback(ValueError("outer"))
