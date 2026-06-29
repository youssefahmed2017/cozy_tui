from cozy_tui.widget import Widget
from cozy_tui.style import Style
from cozy_tui.events import Key


class Checkbox(Widget):
    focusable = True

    def __init__(self, x, y, text, checked=False, style=None):
        super().__init__(x, y, style)
        self.text = text
        self.checked = checked

    def natural_width(self, scale):
        return len(self.text) + 4  # "[x] text"

    def contains(self, col: int, row: int) -> bool:
        return (
            self.abs_x <= col < self.abs_x + self.natural_width(1) and self.abs_y == row
        )

    def _toggle(self):
        self.checked = not self.checked
        self._fire_click()
        self._fire_change(self.checked)

    def on_key(self, key):
        if key in (Key.ENTER, " "):
            self._toggle()

    def on_mouse_click(self, col=None, row=None):
        self._toggle()

    def draw(self, canvas):
        is_focused = canvas.focused is self
        mark = "✔" if self.checked else " "
        label = f"[{mark}] {self.text}"

        raw_bg = self.style.bg.replace("_bg", "") if self.style.bg else None
        fg = self.style.fg or "white"

        if is_focused:
            style = Style(fg="black", bg="white", styles=["bold"])
        elif self.checked:
            style = Style(fg=fg, bg=raw_bg, styles=["bold"])
        else:
            style = Style(fg=fg, bg=raw_bg)

        canvas.write(self.abs_x, self.abs_y, label, style)
