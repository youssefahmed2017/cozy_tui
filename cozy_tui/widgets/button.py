import time
from cozy_tui.widget import Widget
from cozy_tui.style import Style
from cozy_tui.events import Key

_PRESS_DURATION = 0.3


class Button(Widget):
    focusable = True

    def __init__(self, x, y, text, width=None, style=None):
        super().__init__(x, y, style)
        self.text = text
        self.width = width
        self._pressed = False
        self._press_time = 0.0

    def _width(self):
        return max(self.width or 0, len(self.text) + 4, 8)

    def natural_width(self, scale):
        return self._width()

    def contains(self, col: int, row: int) -> bool:
        return self.abs_x <= col < self.abs_x + self._width() and self.abs_y == row

    def _activate(self):
        self._pressed = True
        self._press_time = time.monotonic()
        self._fire_click()

    def on_key(self, key):
        if key in (Key.ENTER, " "):
            self._activate()

    def on_mouse_click(self, col=None, row=None):
        self._activate()

    def draw(self, canvas):
        if self._pressed and time.monotonic() - self._press_time >= _PRESS_DURATION:
            self._pressed = False

        is_focused = canvas.focused is self
        w = self._width()
        raw_bg = self.style.bg.replace("_bg", "") if self.style.bg else None
        fg = self.style.fg or "white"

        label = self.text.center(w)

        if self._pressed:
            style = Style(fg=fg, bg=raw_bg, styles=["dim"])
        elif is_focused:
            style = Style(fg=raw_bg or "black", bg=fg, styles=["bold"])
        else:
            style = Style(fg=fg, bg=raw_bg)

        canvas.write(self.abs_x, self.abs_y, label, style)
