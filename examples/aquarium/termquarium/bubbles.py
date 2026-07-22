"""Ambient rising-bubble particles (Phase 6) -- purely decorative."""

import random
import time

from cozy_tui.widget import Widget

from .constants import (
    BUBBLE_GLYPHS,
    BUBBLE_MAX_COUNT,
    BUBBLE_SPAWN_INTERVAL,
    BUBBLE_SPEED_RANGE,
)
from .styles import BUBBLE_STYLE


def rise_bubble(y: float, speed: float, dt: float) -> float:
    """A bubble's new y after `dt` seconds -- pure so it's unit-testable
    without a Widget/canvas, same split as steer()."""
    return y - speed * dt


class _Bubble:
    __slots__ = ("x", "y", "speed", "glyph")

    def __init__(self, x: float, y: float, speed: float, glyph: str):
        self.x = x
        self.y = y
        self.speed = speed
        self.glyph = glyph


class BubbleField(Widget):
    """Ambient rising-bubble particles, purely decorative -- added before any
    Decoration (see main()'s add-order z-layering) so bubbles always drift
    behind the furniture and fish. Bubbles are plain `_Bubble` state in a
    list rather than their own Widget each: nothing about one benefits from
    Widget's own machinery (no input, no children, no independent styling
    beyond a shared glyph/color), so one field widget owning many of them
    is both simpler and lighter than 40 extra Widget instances would be.
    `enabled` is a zero-arg callable (not a plain bool) so Settings' toggle
    takes effect immediately without this widget needing to be rebuilt.
    `paused` (also a zero-arg callable, defaulting to "never paused") is
    main()'s Pause menu -- existing bubbles freeze in place and no new ones
    spawn while it's open, same freeze-not-hide treatment Fish gets."""

    def __init__(self, bounds, enabled, paused=lambda: False):
        x0, y0, x1, y1 = bounds
        super().__init__(0, 0, BUBBLE_STYLE)
        self.bounds = bounds
        self._enabled = enabled
        self._paused = paused
        self._bubbles: list[_Bubble] = []
        self._last = time.monotonic()
        self._next_spawn = random.uniform(*BUBBLE_SPAWN_INTERVAL)

    def draw(self, canvas) -> None:
        now = time.monotonic()
        dt = now - self._last
        self._last = now
        if not self._enabled():
            self._bubbles = []
            return
        if self._paused():
            for b in self._bubbles:
                canvas.write(round(b.x), round(b.y), b.glyph, self.style)
            return

        x0, y0, x1, y1 = self.bounds
        self._next_spawn -= dt
        if self._next_spawn <= 0.0 and len(self._bubbles) < BUBBLE_MAX_COUNT:
            self._bubbles.append(
                _Bubble(
                    random.uniform(x0, x1),
                    y1,
                    random.uniform(*BUBBLE_SPEED_RANGE),
                    random.choice(BUBBLE_GLYPHS),
                )
            )
            self._next_spawn = random.uniform(*BUBBLE_SPAWN_INTERVAL)

        alive = []
        for b in self._bubbles:
            b.y = rise_bubble(b.y, b.speed, dt)
            if b.y > y0:
                alive.append(b)
                canvas.write(round(b.x), round(b.y), b.glyph, self.style)
        self._bubbles = alive
