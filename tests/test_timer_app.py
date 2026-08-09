"""Regression tests for the timer example (examples/timer_app/timer.py)."""

import importlib.util
import pathlib

from cozy_tui import App, Style

_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "examples" / "timer_app" / "timer.py"
)
_spec = importlib.util.spec_from_file_location("timer_app", _PATH)
t = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(t)


def make_app():
    return App(full=False, size="600x200", style=Style(fg="white", bg="black"))


def test_running_timer_keeps_the_render_loop_ticking():
    # Regression: draw() updated self.remaining via _tick() but never called
    # canvas.request_frame(), so once the loop went idle (the normal,
    # zero-CPU-at-rest state -- see CLAUDE.md's Animation section) a running
    # timer's countdown would visually freeze until some unrelated event (a
    # keypress, mouse move, resize) happened to trigger another draw.
    app = make_app()
    countdown = t.CountdownTimer(0, 0, width=20)
    countdown.set_minutes(5)
    countdown.toggle()  # running = True
    app.add(countdown)
    app.snapshot()  # runs the real draw() pass
    assert app._anim_interval is not None


def test_idle_timer_does_not_request_frames():
    app = make_app()
    countdown = t.CountdownTimer(0, 0, width=20)
    countdown.set_minutes(5)  # not started
    app.add(countdown)
    app.snapshot()
    assert app._anim_interval is None
