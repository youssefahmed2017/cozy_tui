from cozy_tui.widgets.layout.layout import Layout


class HBox(Layout):
    """Stack children horizontally, left to right.

    `align` (default "start") places each child across the vertical axis:
    "center"/"end" within the tallest sibling (or the docked height), "stretch"
    grows every child to that height. `justify` (default "start") distributes
    leftover horizontal space when this box is docked wider than its content --
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
        # See VBox._arrange: a hidden child measures as nothing and takes its
        # surrounding gap with it, so the row closes up rather than gapping.
        natural = [
            (c.natural_width(1), c.natural_height(1)) if c.visible else (0, 0)
            for c in self.children
        ]
        shown = [c for c in self.children if c.visible]
        max_h = max(
            (h for (_w, h), c in zip(natural, self.children) if c.visible), default=0
        )

        # Main axis (horizontal): flex distributes the docked width minus padding.
        inner_w = self._target_w - pl - pr if self._target_w is not None else None
        extras = self._flex_extras([w for w, _h in natural], inner_w, self.gap)
        widths = [natural[i][0] + extras[i] for i in range(len(self.children))]

        # Cross axis (vertical): align within the docked height (minus padding),
        # or the tallest child when undocked.
        cross = self._target_h - pt - pb if self._target_h is not None else max_h

        content_w = sum(widths[i] for i, c in enumerate(self.children) if c.visible)
        content_w += self.gap * max(0, len(shown) - 1)
        main_extent = inner_w if inner_w is not None else content_w
        offset, extra_gap = self._main_justify(main_extent, content_w, len(shown))

        cx = pl + offset
        for i, child in enumerate(self.children):
            w, h = natural[i]
            final_w = widths[i]
            final_h, cy = self._cross_place(h, cross, pt)
            child.x = cx
            child.y = cy
            child._layout_y = 0
            if not child.visible:
                continue
            if final_w != w or final_h != h:
                child.dock_resize(final_w, final_h, 1)
            cx += final_w + self.gap + extra_gap
        self._computed_width = (content_w + pl + pr) if shown else 0
        self._computed_height = (max_h + pt + pb) if shown else 0
