from cozy_tui.events import Key
from cozy_tui.style import Style, selection_style
from cozy_tui.widget import Widget


class Splitter(Widget):
    """Two panes divided by a 1-cell bar you can drag to resize them.

    ``orientation="horizontal"`` (the default) places the panes side by side
    with a vertical bar between them; ``"vertical"`` stacks them with a
    horizontal bar. Each pane is resized every frame via its own
    ``dock_resize(w, h, scale)``, so panes built from ``Box``/``ScrollView``/
    another ``Splitter`` grow to fill their share; fixed-size widgets keep
    their own size and are simply clipped to it.

    Click-drag the bar with the mouse to resize freely. Once the bar itself
    is focused, Left/Right (horizontal) or Up/Down (vertical) nudge it by
    ``step`` cells, Home/End snap it to the ``min_size`` extent on either
    side. Tab dives into whichever pane has focusable content first, matching
    every other container in this library — so if either pane holds
    something focusable, Tab never stops on the bar itself; click it directly
    to grab it. When neither pane has anything focusable, the bar becomes an
    ordinary Tab stop.
    """

    focusable = True

    def __init__(
        self,
        x,
        y,
        size,
        first,
        second,
        *,
        orientation="horizontal",
        ratio=0.5,
        min_size=1,
        step=1,
        style=None,
    ):
        super().__init__(x, y, style)
        if orientation not in ("horizontal", "vertical"):
            raise ValueError('orientation must be "horizontal" or "vertical"')
        self.orientation = orientation
        self.width, self.height = map(int, size.split("x"))
        self.first = first
        self.second = second
        first.parent = self
        second.parent = self
        self.min_size = max(1, min_size)
        self.step = step
        self._ratio = min(1.0, max(0.0, ratio))
        self._dragging = False
        self._app = None  # canvas from the last draw(), needed to steal focus back (see on_mouse_click)
        self._vw = self._vh = 0
        self._span = 0  # cells available along the split axis, set each draw()
        self._divider_at = 0  # bar's cell offset along the split axis, set each draw()

    @property
    def children(self):
        return [self.first, self.second]

    # ── public API ────────────────────────────────────────────────────────────

    def get_ratio(self):
        return self._ratio

    def set_ratio(self, ratio) -> None:
        self._ratio = min(1.0, max(0.0, ratio))

    # ── internals ─────────────────────────────────────────────────────────────

    def _clamp_pos(self, pos):
        usable = max(0, self._span - 1)
        lo = self.min_size
        hi = max(lo, usable - self.min_size)
        return max(lo, min(hi, pos))

    def _resize_by(self, delta) -> None:
        if self._span <= 1:
            return
        # Derived fresh from _ratio rather than read off the cached
        # _divider_at, which only updates on the next draw() -- otherwise two
        # key presses in the same frame would only register as one step.
        usable = max(1, self._span - 1)
        current = self._clamp_pos(round(self._ratio * usable))
        self._ratio = self._clamp_pos(current + delta) / usable

    def _set_from_coord(self, coord) -> None:
        if self._span <= 1:
            return
        usable = max(1, self._span - 1)
        origin = self.abs_x if self.orientation == "horizontal" else self.abs_y
        self._ratio = self._clamp_pos(coord - origin) / usable

    def _bar_style(self, canvas):
        return (
            selection_style()
            if canvas.focused is self
            else Style(fg="bright_black", bg=self.style.raw_bg)
        )

    # ── Widget interface ──────────────────────────────────────────────────────

    def natural_width(self, scale):
        return self.width // scale

    def natural_height(self, scale):
        return self.height // scale

    def dock_resize(self, w, h, scale):
        self.width = w * scale
        self.height = h * scale

    def contains(self, col, row):
        # Only the bar itself is Splitter's own hit box; the rest of its
        # bounding box belongs to a pane, so a descendant widget (or nothing)
        # catches clicks there instead.
        if self._span <= 1:
            return False
        if self.orientation == "horizontal":
            return (
                col == self.abs_x + self._divider_at
                and self.abs_y <= row < self.abs_y + self._vh
            )
        return (
            row == self.abs_y + self._divider_at
            and self.abs_x <= col < self.abs_x + self._vw
        )

    def on_key(self, key) -> None:
        dec, inc = (
            (Key.LEFT, Key.RIGHT)
            if self.orientation == "horizontal"
            else (Key.UP, Key.DOWN)
        )
        if key == dec:
            self._resize_by(-self.step)
        elif key == inc:
            self._resize_by(self.step)
        elif key == Key.HOME:
            self._resize_by(-self._span)
        elif key == Key.END:
            self._resize_by(self._span)

    def on_mouse_click(self, col=None, row=None) -> None:
        # A click that lands on the bar resolves to Splitter via contains(),
        # but App's focus-on-click logic dives past any container straight to
        # its first focusable descendant (matching Tab) -- so if either pane
        # holds something focusable, focus would land there instead of on the
        # bar. Reclaim it explicitly so the drag that follows (routed by App
        # to self.focused) actually reaches us.
        if self._app is not None:
            self._app.focus(self)
        self._dragging = True
        if col is not None and row is not None:
            self._set_from_coord(col if self.orientation == "horizontal" else row)

    def on_mouse_drag(self, col=None, row=None) -> None:
        if self._dragging and col is not None and row is not None:
            self._set_from_coord(col if self.orientation == "horizontal" else row)
        self._fire_drag(col, row)

    def on_mouse_release(self, col=None, row=None) -> None:
        self._dragging = False
        self._fire_release(col, row)

    def draw(self, canvas) -> None:
        self._app = canvas
        scale = canvas.SCALE
        self._vw = self.width // scale
        self._vh = self.height // scale
        self._span = self._vw if self.orientation == "horizontal" else self._vh
        usable = max(1, self._span - 1)
        self._divider_at = (
            self._clamp_pos(round(self._ratio * usable)) if self._span > 1 else 0
        )

        bar_style = self._bar_style(canvas)
        if self.orientation == "horizontal":
            first_w, second_w = self._divider_at, max(
                0, self._span - self._divider_at - 1
            )
            self.first.x, self.first.y = 0, 0
            self.second.x, self.second.y = self._divider_at + 1, 0
            self.first.dock_resize(first_w, self._vh, scale)
            self.second.dock_resize(second_w, self._vh, scale)
            for r in range(self._vh):
                canvas.write(
                    self.abs_x + self._divider_at, self.abs_y + r, "┃", bar_style
                )

            canvas.push_clip(
                self.abs_x, self.abs_y, self.abs_x + first_w, self.abs_y + self._vh
            )
            self.first.draw(canvas)
            canvas.pop_clip()
            canvas.push_clip(
                self.abs_x + self._divider_at + 1,
                self.abs_y,
                self.abs_x + self._span,
                self.abs_y + self._vh,
            )
            self.second.draw(canvas)
            canvas.pop_clip()
        else:
            first_h, second_h = self._divider_at, max(
                0, self._span - self._divider_at - 1
            )
            self.first.x, self.first.y = 0, 0
            self.second.x, self.second.y = 0, self._divider_at + 1
            self.first.dock_resize(self._vw, first_h, scale)
            self.second.dock_resize(self._vw, second_h, scale)
            for c in range(self._vw):
                canvas.write(
                    self.abs_x + c, self.abs_y + self._divider_at, "━", bar_style
                )

            canvas.push_clip(
                self.abs_x, self.abs_y, self.abs_x + self._vw, self.abs_y + first_h
            )
            self.first.draw(canvas)
            canvas.pop_clip()
            canvas.push_clip(
                self.abs_x,
                self.abs_y + self._divider_at + 1,
                self.abs_x + self._vw,
                self.abs_y + self._span,
            )
            self.second.draw(canvas)
            canvas.pop_clip()
