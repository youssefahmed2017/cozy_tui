from math import floor

from cozy_tui.style import Style
from cozy_tui.widget import Widget


class ProgressBar(Widget):
    focusable = False

    def __init__(
        self,
        x,
        y,
        fill: str = "=",
        empty: str = " ",
        progress=0,
        *,
        width=20,
        minimum=0,
        maximum=100,
        style: Style | None = None,
    ):
        super().__init__(x, y, style)
        self.min = minimum
        self.max = maximum
        self.width = width
        self.fill = fill
        self.empty = empty
        # After min/max: the `progress` setter clamps against them. A State
        # here keeps the bar tracking it, clamped on every change. _value is
        # seeded to None so the setter below is the single place that ever
        # computes it (its _fire_change is a no-op this early — no handler can
        # have been registered on a widget still inside its constructor).
        self._value = None
        self.bind("progress", progress)

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def progress(self):
        """The current value, clamped to ``[minimum, maximum]``. Assigning is
        the same as :meth:`set` — it exists so the constructor's ``progress=``
        argument has a matching attribute, which is also what lets a
        :class:`~cozy_tui.state.State` bind to it."""
        return self._value

    @progress.setter
    def progress(self, value) -> None:
        self.set(value)

    def get(self):
        return self._value

    def set(self, value) -> None:
        old = self._value
        self._value = self._clamp(value)
        if self._value != old:
            self._fire_change(self._value)

    def increment(self, amount=1) -> None:
        self.set(self._value + amount)

    def decrement(self, amount=1) -> None:
        self.set(self._value - amount)

    # ── internals ─────────────────────────────────────────────────────────────

    def _clamp(self, v):
        lo, hi = self.min, self.max
        return max(lo, min(hi, v))

    # ── Widget interface ──────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        return self.width

    def natural_height(self, scale) -> int:
        return 1

    def contains(self, col: int, row: int) -> bool:
        return self.abs_x <= col < self.abs_x + self.width and row == self.abs_y

    def draw(self, canvas) -> None:
        w = self.width
        span = self.max - self.min
        ratio = (self._value - self.min) / span if span else 1.0

        # Layout: "[" + bar + "] NNN%"
        # overhead = 1 "[" + 1 "]" + 1 " " + 3 digits + 1 "%" = 7
        bar_w = max(0, w - 7)
        filled = floor(ratio * bar_w)
        empty = bar_w - filled

        pct = f"{floor(ratio * 100):3}%"
        bar = "[" + self.fill * filled + self.empty * empty + "] " + pct

        canvas.write(self.abs_x, self.abs_y, bar[:w].ljust(w), self.style)
