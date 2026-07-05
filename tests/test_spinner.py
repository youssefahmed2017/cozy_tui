"""Spinner: frame timing and rendering."""

from cozy_tui import App, Style
from cozy_tui.widgets import Spinner


def make_app():
    return App(full=False, size="800x300", style=Style(fg="white", bg="black"))


def test_frame_index_advances_and_wraps(monkeypatch):
    import cozy_tui.widgets.display.spinner as spmod

    sp = Spinner(0, 0, frames="ABC", speed=0.1)
    clock = [100.0]
    monkeypatch.setattr(spmod.time, "monotonic", lambda: clock[0])
    sp._start = 100.0

    assert sp.frame_index() == 0
    clock[0] = 100.05
    assert sp.frame_index() == 0
    clock[0] = 100.11  # just past 1 * speed
    assert sp.frame_index() == 1
    clock[0] = 100.21  # just past 2 * speed
    assert sp.frame_index() == 2
    clock[0] = 100.31  # just past 3 * speed -> wraps back to 0
    assert sp.frame_index() == 0


def test_draw_shows_current_frame_and_label():
    app = make_app()
    sp = Spinner(0, 0, frames="AB", speed=0.1, label="Loading")
    app.add(sp)
    snap = app.snapshot()
    assert ("A Loading" in snap) or ("B Loading" in snap)


def test_presets_are_nonempty():
    for preset in (Spinner.DOTS, Spinner.LINE, Spinner.BAR, Spinner.MOON, Spinner.ARROW):
        assert len(preset) >= 2


def test_draw_requests_a_frame_to_keep_animating():
    app = make_app()
    sp = Spinner(0, 0, speed=0.05)
    app.add(sp)
    app._anim_interval = None
    app._compose()
    assert app._anim_interval == 0.05  # asked the loop to redraw at its cadence
