from cozy_tui.widgets.layout.layout import Layout


class VBox(Layout):
    """Stack children vertically, top to bottom."""

    def __init__(self, x, y, gap=0, style=None):
        super().__init__(x, y, style, name="Vertical Box")
        self.gap = gap

    def _arrange(self):
        natural = [(c.natural_width(1), c.natural_height(1)) for c in self.children]
        max_w = max((w for w, _h in natural), default=0)
        extras = self._flex_extras([h for _w, h in natural], self._target_h, self.gap)

        cy = 0
        for i, child in enumerate(self.children):
            w, h = natural[i]
            final_h = h + extras[i]
            if extras[i]:
                child.dock_resize(w, final_h, 1)
            child.x = 0
            child.y = cy
            child._layout_y = 0
            cy += final_h + self.gap
        self._computed_width = max_w
        self._computed_height = max(0, cy - self.gap) if self.children else 0
