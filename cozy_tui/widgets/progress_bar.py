from cozy_tui.widget import Widget
from cozy_tui.style import Style
from math import floor


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
        min=0,
        max=100,
        style: Style | None = None,
    ):
        super().__init__(x, y, style)
        self.min = min
        self.max = max
        self._value = self._clamp(progress)
        self.width = width
        self.fill = fill
        self.empty = empty

    # ── public API ────────────────────────────────────────────────────────────

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
