from cozy_tui._width import text_width
from cozy_tui.widget import Widget


class Label(Widget):
    def __init__(self, x, y, text, style=None):
        super().__init__(x, y, style)
        self.text = text
        self.laps = True

    def natural_width(self, scale):
        return text_width(self.text)

    def natural_height(self, scale):
        if self._clip_width and self.text:
            return max(1, (len(self.text) + self._clip_width - 1) // self._clip_width)
        return 1

    def draw(self, canvas):
        if self._clip_width:
            w = self._clip_width
            for i in range(0, max(1, len(self.text)), w):
                canvas.write(
                    self.abs_x, self.abs_y + i // w, self.text[i : i + w], self.style
                )
        else:
            canvas.write(self.abs_x, self.abs_y, self.text, self.style)
