from cozy_tui.widgets.layout.layout import Layout


class HBox(Layout):
    """Stack children horizontally, left to right."""

    def __init__(self, x, y, gap=0, style=None):
        super().__init__(x, y, style, name="Horizontal Box")
        self.gap = gap

    def _arrange(self):
        natural = [(c.natural_width(1), c.natural_height(1)) for c in self.children]
        max_h = max((h for _w, h in natural), default=0)
        extras = self._flex_extras([w for w, _h in natural], self._target_w, self.gap)

        cx = 0
        for i, child in enumerate(self.children):
            w, h = natural[i]
            final_w = w + extras[i]
            if extras[i]:
                child.dock_resize(final_w, h, 1)
            child.x = cx
            child.y = 0
            child._layout_y = 0
            cx += final_w + self.gap
        self._computed_width = max(0, cx - self.gap) if self.children else 0
        self._computed_height = max_h
