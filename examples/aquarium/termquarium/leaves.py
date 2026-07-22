"""Ambient falling-leaf particles for the Forest scene -- purely decorative,
directly mirroring bubbles.py's BubbleField/_Bubble (capped count,
randomized spawn interval, freezes while paused), just falling instead of
rising."""

import random
import time

from cozy_tui.widget import Widget

from .constants import (
    FOREST_LEAF_DRIFT_RANGE,
    FOREST_LEAF_FALL_SPEED_RANGE,
    FOREST_LEAF_GLYPHS,
    FOREST_LEAF_MAX_COUNT,
    FOREST_LEAF_SPAWN_INTERVAL,
)
from .styles import FOREST_LEAF_STYLES


def fall_leaf(y: float, speed: float, dt: float) -> float:
    """A leaf's new y after `dt` seconds -- pure so it's unit-testable
    without a Widget/canvas, same split as bubbles.py's rise_bubble()."""
    return y + speed * dt


class _Leaf:
    __slots__ = ("x", "y", "fall_speed", "drift", "glyph", "style")

    def __init__(
        self, x: float, y: float, fall_speed: float, drift: float, glyph: str, style
    ):
        self.x = x
        self.y = y
        self.fall_speed = fall_speed
        self.drift = drift
        self.glyph = glyph
        self.style = style


class LeafField(Widget):
    """Ambient falling leaves, purely decorative -- appended after the
    Forest's canopy/trunk/ground scenery (see ui.py's build_forest_scene())
    so leaves draw over the ground line but under any fish/wood appended
    later. `paused` is the same zero-arg-callable shared-mutable pattern
    BubbleField already uses -- existing leaves freeze in place and no new
    ones spawn while the game is paused."""

    def __init__(self, bounds, paused=lambda: False):
        x0, y0, x1, y1 = bounds
        super().__init__(0, 0, FOREST_LEAF_STYLES[0])
        self.bounds = bounds
        self._paused = paused
        self._leaves: list[_Leaf] = []
        self._last = time.monotonic()
        self._next_spawn = random.uniform(*FOREST_LEAF_SPAWN_INTERVAL)

    def draw(self, canvas) -> None:
        now = time.monotonic()
        dt = now - self._last
        self._last = now
        if self._paused():
            for leaf in self._leaves:
                canvas.write(round(leaf.x), round(leaf.y), leaf.glyph, leaf.style)
            return

        x0, y0, x1, y1 = self.bounds
        self._next_spawn -= dt
        if self._next_spawn <= 0.0 and len(self._leaves) < FOREST_LEAF_MAX_COUNT:
            self._leaves.append(
                _Leaf(
                    random.uniform(x0, x1),
                    y0,
                    random.uniform(*FOREST_LEAF_FALL_SPEED_RANGE),
                    random.uniform(*FOREST_LEAF_DRIFT_RANGE),
                    random.choice(FOREST_LEAF_GLYPHS),
                    random.choice(FOREST_LEAF_STYLES),
                )
            )
            self._next_spawn = random.uniform(*FOREST_LEAF_SPAWN_INTERVAL)

        alive = []
        for leaf in self._leaves:
            leaf.y = fall_leaf(leaf.y, leaf.fall_speed, dt)
            leaf.x += leaf.drift * dt
            if leaf.y < y1:
                alive.append(leaf)
                canvas.write(round(leaf.x), round(leaf.y), leaf.glyph, leaf.style)
        self._leaves = alive
