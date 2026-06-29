import time
from cozy_tui.widget import Widget
from cozy_tui.style import Style
from cozy_tui.events import Key

_PRESS_DURATION = 1.0


class Button(Widget):
    focusable = True

    def __init__(self, x, y, text, style=None):
        super().__init__(x, y, style)
        self.text = text
        self._handler = None
        self._pressed = False
        self._press_time = 0.0

    def natural_width(self, scale):
        return len(self.text) + 4  # "[ text ]"

    def contains(self, col: int, row: int) -> bool:
        return self.abs_x <= col < self.abs_x + self.natural_width(1) and self.abs_y == row

    def on_click(self, func):
        """Register a handler called when the button is activated."""
        self._handler = func
        return self

    def _activate(self):
        self._pressed = True
        self._press_time = time.monotonic()
        if self._handler:
            self._handler()

    def on_key(self, key):
        if key in (Key.ENTER, " "):
            self._activate()

    def on_mouse_click(self):
        self._activate()

    def draw(self, canvas):
        if self._pressed and time.monotonic() - self._press_time >= _PRESS_DURATION:
            self._pressed = False

        is_focused = canvas.focused is self
        raw_bg = self.style.bg.replace("_bg", "") if self.style.bg else None

        if self._pressed:
            style = Style(fg="white", bg=raw_bg, styles=["dim"])
            label = f"[·{self.text}·]"
        elif is_focused:
            style = Style(fg="black", bg="white", styles=["bold"])
            label = f"[ {self.text} ]"
        else:
            style = Style(fg=self.style.fg, bg=raw_bg)
            label = f"[ {self.text} ]"

        canvas.write(self.abs_x, self.abs_y, label, style)
