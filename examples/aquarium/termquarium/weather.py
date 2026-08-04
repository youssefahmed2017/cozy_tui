"""A brief lightning flash while a storm is live -- purely decorative,
mirroring bubbles.py/leaves.py's own ambient-particle shape (randomized
timing, freezes while paused) but for a single transient shape instead of
many continuously-moving ones."""

import random
import time

from cozy_tui.widget import Widget

from .constants import (
    LIGHTNING_ART,
    LIGHTNING_FLASH_DURATION,
    LIGHTNING_FLASH_INTERVAL_RANGE,
)
from .styles import LIGHTNING_STYLE


class LightningField(Widget):
    """Flashes LIGHTNING_ART at a random x within `bounds` every so often
    while `environment["storm"]` is True, same shared-mutable-dict read
    BubbleField/Fish already do for `paused`/`environment`. Nothing shows
    at all outside a live storm -- the countdown to the next flash only
    starts once one begins, so a flash never fires right as a storm ends
    or lingers from a storm that just started."""

    def __init__(self, bounds, environment, paused=lambda: False):
        super().__init__(0, 0, LIGHTNING_STYLE)
        self.bounds = bounds
        self._environment = environment
        self._paused = paused
        self._last = time.monotonic()
        self._next_flash = random.uniform(*LIGHTNING_FLASH_INTERVAL_RANGE)
        self._flash_until = None
        self._flash_x = 0.0

    def draw(self, canvas) -> None:
        now = time.monotonic()
        dt = now - self._last
        self._last = now

        if not self._environment.get("storm"):
            self._flash_until = None
            self._next_flash = random.uniform(*LIGHTNING_FLASH_INTERVAL_RANGE)
            return
        if self._paused():
            if self._flash_until is not None and now < self._flash_until:
                self._draw_bolt(canvas)
            return

        if self._flash_until is not None:
            if now < self._flash_until:
                self._draw_bolt(canvas)
            else:
                self._flash_until = None
            return

        self._next_flash -= dt
        if self._next_flash <= 0.0:
            x0, _, x1, _ = self.bounds
            bolt_width = max(len(line) for line in LIGHTNING_ART)
            self._flash_x = random.uniform(x0, max(x0, x1 - bolt_width))
            self._flash_until = now + LIGHTNING_FLASH_DURATION
            self._next_flash = random.uniform(*LIGHTNING_FLASH_INTERVAL_RANGE)
            self._draw_bolt(canvas)

    def _draw_bolt(self, canvas) -> None:
        _, y0, _, y1 = self.bounds
        x = round(self._flash_x)
        for i, line in enumerate(LIGHTNING_ART):
            y = round(y0) + i
            if y > y1:
                break
            canvas.write(x, y, line, self.style)
