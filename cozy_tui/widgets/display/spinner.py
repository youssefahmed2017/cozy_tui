import time

from cozy_tui._spinners import SPINNERS
from cozy_tui._width import text_width
from cozy_tui.style import Style
from cozy_tui.widget import Widget


class Spinner(Widget):
    """A small animated activity indicator — the idiomatic "working…" companion
    to :meth:`App.run_worker`. Non-focusable; drop one next to a label while a
    background task runs and remove it in the worker's ``on_result``.

    The frame advances off a wall clock and the widget asks the event loop to
    redraw at its own cadence (via ``request_frame``), so it animates smoothly
    without the app setting ``tick_interval``.

    Example::

        spinner = Spinner(2, 2, label="Loading…")
        box.add(spinner)
        app.run_worker(fetch, on_result=lambda data: box.remove(spinner))

        Spinner(2, 2, spinner="material", label="Uploading…")  # a named preset

    ``spinner`` picks both frames and speed from the built-in catalog:
    ``dots`` (default), ``line``, ``normalDots``, ``growVertical``, ``bounce``,
    ``arrow``, ``bouncingBar``, ``bouncingBall``, ``clock``, ``material``,
    ``moon``, ``pong``, ``aesthetic``. Passing ``frames=``/``speed=`` overrides
    it for a fully custom animation. The original class attributes
    (``Spinner.DOTS``, ``LINE``, ``BAR``, ``MOON``, ``ARROW``) still work and
    are just the matching preset's frames.
    """

    DOTS = SPINNERS["dots"][0]
    LINE = SPINNERS["line"][0]
    BAR = SPINNERS["growVertical"][0]
    MOON = SPINNERS["moon"][0]
    ARROW = SPINNERS["arrow"][0]

    def __init__(
        self,
        x,
        y,
        *,
        frames=None,
        speed: float | None = None,
        spinner: str = "dots",
        label: str = "",
        style: Style | None = None,
    ):
        super().__init__(x, y, style)
        if frames is not None:
            self.frames = tuple(frames)
            self.speed = speed if speed is not None else 0.08
        else:
            if spinner not in SPINNERS:
                raise ValueError(
                    f"Unknown spinner preset {spinner!r}; choose from "
                    f"{', '.join(sorted(SPINNERS))}"
                )
            preset_frames, preset_speed = SPINNERS[spinner]
            self.frames = preset_frames
            self.speed = speed if speed is not None else preset_speed
        self.label = label
        self._start = time.monotonic()

    def frame_index(self):
        return int((time.monotonic() - self._start) / self.speed) % len(self.frames)

    def natural_width(self, scale):
        w = text_width(self.frames[0])
        return w + (1 + text_width(self.label) if self.label else 0)

    def natural_height(self, scale):
        return 1

    def draw(self, canvas):
        glyph = self.frames[self.frame_index()]
        text = f"{glyph} {self.label}" if self.label else glyph
        canvas.write(self.abs_x, self.abs_y, text, self.style)
        canvas.request_frame(self.speed)  # keep the loop redrawing us
