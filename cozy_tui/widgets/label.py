from cozy_tui.widget import Widget


class Label(Widget):
    def __init__(self, text, x, y, style=None):
        super().__init__(x, y, style)
        self.text = text

    def natural_width(self, scale):
        return len(self.text)

    def draw(self, canvas):
        if self._clip_width:
            w = self._clip_width
            for i in range(0, max(1, len(self.text)), w):
                canvas.write(
                    self.abs_x, self.abs_y + i // w, self.text[i : i + w], self.style
                )
        else:
            canvas.write(self.abs_x, self.abs_y, self.text, self.style)
