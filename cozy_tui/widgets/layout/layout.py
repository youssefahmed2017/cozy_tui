from cozy_tui.widget import Widget


class Layout(Widget):
    """Base class for auto-positioning containers (VBox, HBox, Grid).

    Subclasses implement _arrange(), which sets child.x / child.y and
    updates self._computed_width / self._computed_height before drawing.
    """

    def __init__(self, x, y, style=None):
        super().__init__(x, y, style)
        self.children = []
        self._computed_width = 0
        self._computed_height = 0
        self._dirty = True

    def add(self, widget):
        widget.parent = self
        widget._layout_y = 0
        self.children.append(widget)
        self._dirty = True
        return self

    def natural_width(self, scale):
        if self._dirty:
            self._arrange()
            self._dirty = False
        return self._computed_width

    def natural_height(self, scale):
        if self._dirty:
            self._arrange()
            self._dirty = False
        return self._computed_height

    def contains(self, col: int, row: int) -> bool:
        return (
            self.abs_x <= col < self.abs_x + self._computed_width
            and self.abs_y <= row < self.abs_y + self._computed_height
        )

    def _arrange(self):
        raise NotImplementedError

    def draw(self, canvas):
        if self._dirty:
            self._arrange()
        self._dirty = True  # re-dirty so next frame's natural_width/height recomputes
        for child in self.children:
            child.draw(canvas)
