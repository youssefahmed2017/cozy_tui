from cozy_tui.events import Key
from cozy_tui.style import Style, selection_style
from cozy_tui.widget import Widget


class Slider(Widget):
    """A draggable numeric control — the interactive counterpart to
    ``ProgressBar``. Left/Right (or Up/Down) step the value by ``step``;
    Home/End jump to ``min``/``max``; PageUp/PageDown move by ``page_step``.
    Click or drag anywhere on the track jumps the handle straight to that
    position. ``on_change`` fires with the new value whenever it actually
    changes (not on a clamp that leaves it unchanged).
    """

    focusable = True

    def __init__(
        self,
        x,
        y,
        minimum=0,
        maximum=100,
        value=None,
        step=1,
        *,
        width=20,
        page_step=None,
        show_value=True,
        style=None,
    ):
        super().__init__(x, y, style)
        if minimum > maximum:
            raise ValueError(f"minimum ({minimum!r}) must be <= maximum ({maximum!r})")
        self.min = minimum
        self.max = maximum
        self.step = step
        page = (maximum - minimum) // 10
        if page < step:
            page = step
        self.page_step = page if page_step is None else page_step
        self.width = width
        self.show_value = show_value
        # A fixed decimal count (the most precision any of min/max/step
        # implies) makes every formatted value's width fully determined by
        # its integer part -- which is always widest at one of the two
        # endpoints. Without this, e.g. minimum=0/maximum=1/step=0.01 would
        # reserve room for "0"/"1" (1 char) while a live value like 0.44 (via
        # the default %g formatting) needs 4, overflowing past the reserved
        # column into whatever's drawn to the right of the slider.
        self._decimals = max(
            self._decimal_places(minimum),
            self._decimal_places(maximum),
            self._decimal_places(step),
        )
        # Reserved from min/max (not the current value) so the bar's width —
        # and therefore the handle's pixel position — stays fixed as the
        # value changes; sizing off the live value would make the bar jitter
        # by a column or two while dragging near a width boundary (e.g. "9"
        # -> "10").
        min_w, max_w = len(self._fmt(minimum)), len(self._fmt(maximum))
        self._label_w = min_w if min_w > max_w else max_w
        self._value = self._clamp(minimum if value is None else value)

    # ── public API ────────────────────────────────────────────────────────────

    def get(self):
        return self._value

    def set(self, value) -> None:
        old = self._value
        self._value = self._clamp(value)
        if self._value != old:
            self._fire_change(self._value)

    def increment(self, amount=None) -> None:
        self.set(self._value + (self.step if amount is None else amount))

    def decrement(self, amount=None) -> None:
        self.set(self._value - (self.step if amount is None else amount))

    # ── internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _decimal_places(x) -> int:
        """How many fractional digits `x` needs to round-trip exactly (0 for
        an int, or a float with no fractional part)."""
        if isinstance(x, int):
            return 0
        s = repr(float(x))
        if "e" in s or "E" in s:  # scientific notation: rare for slider ranges
            return 6
        frac = s.split(".", 1)[1].rstrip("0")
        return len(frac)

    def _fmt(self, v) -> str:
        if self._decimals:
            return f"{float(v):.{self._decimals}f}"
        return str(v) if isinstance(v, int) else str(round(v))

    def _clamp(self, v):
        return max(self.min, min(self.max, v))

    def _bar_width(self) -> int:
        if not self.show_value:
            return self.width
        return max(1, self.width - self._label_w - 1)

    def _handle_pos(self, bar_w) -> int:
        span = self.max - self.min
        ratio = (self._value - self.min) / span if span else 0.0
        return round(ratio * (bar_w - 1)) if bar_w > 1 else 0

    def _set_from_col(self, col) -> None:
        bar_w = self._bar_width()
        if bar_w <= 1:
            return
        ratio = max(0.0, min(1.0, (col - self.abs_x) / (bar_w - 1)))
        raw = self.min + ratio * (self.max - self.min)
        if self.step:
            raw = round(raw / self.step) * self.step
        self.set(raw)

    # ── Widget interface ──────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        return self.width

    def natural_height(self, scale) -> int:
        return 1

    def contains(self, col: int, row: int) -> bool:
        return self.abs_x <= col < self.abs_x + self.width and row == self.abs_y

    def on_key(self, key) -> None:
        if key in (Key.LEFT, Key.DOWN):
            self.decrement()
        elif key in (Key.RIGHT, Key.UP):
            self.increment()
        elif key == Key.PAGE_DOWN:
            self.decrement(self.page_step)
        elif key == Key.PAGE_UP:
            self.increment(self.page_step)
        elif key == Key.HOME:
            self.set(self.min)
        elif key == Key.END:
            self.set(self.max)

    def on_mouse_click(self, col=None, row=None) -> None:
        if col is not None:
            self._set_from_col(col)

    def on_mouse_drag(self, col=None, row=None) -> None:
        if col is not None:
            self._set_from_col(col)
        self._fire_drag(col, row)

    def draw(self, canvas) -> None:
        is_focused = canvas.focused is self
        bar_w = self._bar_width()
        handle = self._handle_pos(bar_w)

        fg = self.style.fg or "white"
        raw_bg = self.style.raw_bg
        track_style = Style(fg=fg, bg=raw_bg)
        handle_style = (
            selection_style()
            if is_focused
            else Style(fg=fg, bg=raw_bg, styles=["bold"])
        )

        bar = ("━" * handle) + "●" + ("─" * (bar_w - handle - 1))
        canvas.write(self.abs_x, self.abs_y, bar, track_style)
        canvas.write(self.abs_x + handle, self.abs_y, "●", handle_style)

        if self.show_value:
            text = self._fmt(self._value).rjust(self._label_w)
            canvas.write(self.abs_x + bar_w + 1, self.abs_y, text, self.style)
