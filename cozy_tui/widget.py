from cozy_tui.style import Style


class Widget:
    focusable = False

    def __init__(self, x=0, y=0, style=None):
        self.x = x
        self.y = y
        self.parent = None
        self.style = style or Style()
        self._layout_y = 0
        self._clip_width = None

    @property
    def abs_x(self):
        if self.parent:
            return self.parent.abs_x + self.x
        return self.x

    @property
    def abs_y(self):
        if self.parent:
            return self.parent.abs_y + self.y + self._layout_y
        return self.y + self._layout_y

    def natural_width(self, scale):
        return 0

    def contains(self, col: int, row: int) -> bool:
        return False

    def draw(self, canvas):
        raise NotImplementedError

    def on_key(self, key):
        pass
