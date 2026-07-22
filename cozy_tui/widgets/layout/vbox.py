from cozy_tui.widgets.layout.layout import Layout


class VBox(Layout):
    """Stack children vertically, top to bottom."""

    def __init__(self, x, y, gap=0, style=None):
        super().__init__(x, y, style)
        self.gap = gap

    def _arrange(self):
        # A hidden child measures as nothing and doesn't advance the cursor, so
        # the gap that would have surrounded it collapses too -- hiding a row
        # closes the stack up instead of leaving a hole in it.
        natural = [
            (c.natural_width(1), c.natural_height(1)) if c.visible else (0, 0)
            for c in self.children
        ]
        shown = [c for c in self.children if c.visible]
        max_w = max(
            (w for (w, _h), c in zip(natural, self.children) if c.visible), default=0
        )
        extras = self._flex_extras([h for _w, h in natural], self._target_h, self.gap)

        cy = 0
        for i, child in enumerate(self.children):
            w, h = natural[i]
            final_h = h + extras[i]
            child.x = 0
            child.y = cy
            child._layout_y = 0
            if not child.visible:
                continue
            if extras[i]:
                child.dock_resize(w, final_h, 1)
            cy += final_h + self.gap
        self._computed_width = max_w
        self._computed_height = max(0, cy - self.gap) if shown else 0
