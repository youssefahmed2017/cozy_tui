from cozy_tui.widgets.layout.layout import Layout


class VBox(Layout):
    """Stack children vertically, top to bottom.

    `align` (default "start") places each child across the horizontal axis:
    "center"/"end" within the widest sibling (or the docked width), "stretch"
    grows every child to that width. `justify` (default "start") distributes
    leftover vertical space when this box is docked taller than its content --
    "center"/"end"/"between"/"around"/"evenly", the counterpart to `flex` for
    when you want fixed-size children and the gaps to absorb the slack. See
    `Layout` for `padding`.
    """

    def __init__(
        self, x, y, gap=0, style=None, *, padding=0, align="start", justify="start"
    ):
        super().__init__(x, y, style, padding=padding, align=align, justify=justify)
        self.gap = gap

    def _arrange(self):
        pt, pr, pb, pl = self._padding
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

        # Main axis (vertical): flex distributes the docked height minus padding.
        inner_h = self._target_h - pt - pb if self._target_h is not None else None
        extras = self._flex_extras([h for _w, h in natural], inner_h, self.gap)
        heights = [natural[i][1] + extras[i] for i in range(len(self.children))]

        # Cross axis (horizontal): align within the docked width (minus padding),
        # or the widest child when undocked.
        cross = self._target_w - pl - pr if self._target_w is not None else max_w

        content_h = sum(heights[i] for i, c in enumerate(self.children) if c.visible)
        content_h += self.gap * max(0, len(shown) - 1)
        main_extent = inner_h if inner_h is not None else content_h
        offset, extra_gap = self._main_justify(main_extent, content_h, len(shown))

        cy = pt + offset
        for i, child in enumerate(self.children):
            w, h = natural[i]
            final_h = heights[i]
            final_w, cx = self._cross_place(w, cross, pl)
            child.x = cx
            child.y = cy
            child._layout_y = 0
            if not child.visible:
                continue
            if final_w != w or final_h != h:
                child.dock_resize(final_w, final_h, 1)
            cy += final_h + self.gap + extra_gap
        self._computed_width = (max_w + pl + pr) if shown else 0
        self._computed_height = (content_h + pt + pb) if shown else 0
