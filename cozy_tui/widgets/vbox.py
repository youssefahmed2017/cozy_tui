from cozy_tui.widgets.layout import Layout


class VBox(Layout):
    """Stack children vertically, top to bottom."""

    def __init__(self, x, y, gap=0, style=None):
        super().__init__(x, y, style)
        self.gap = gap

    def _arrange(self):
        cy = 0
        max_w = 0
        for child in self.children:
            child.x = 0
            child.y = cy
            child._layout_y = 0
            w = child.natural_width(1)
            h = child.natural_height(1)
            if w > max_w:
                max_w = w
            cy += h + self.gap
        self._computed_width = max_w
        self._computed_height = max(0, cy - self.gap) if self.children else 0
