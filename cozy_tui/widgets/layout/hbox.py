from cozy_tui.widgets.layout.layout import Layout


class HBox(Layout):
    """Stack children horizontally, left to right."""

    def __init__(self, x, y, gap=0, style=None):
        super().__init__(x, y, style, name="Horizontal Box")
        self.gap = gap

    def _arrange(self):
        cx = 0
        max_h = 0
        for child in self.children:
            child.x = cx
            child.y = 0
            child._layout_y = 0
            w = child.natural_width(1)
            h = child.natural_height(1)
            if h > max_h:
                max_h = h
            cx += w + self.gap
        self._computed_width = max(0, cx - self.gap) if self.children else 0
        self._computed_height = max_h
