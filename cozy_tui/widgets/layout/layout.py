import time

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
        # Set by dock_resize() when this layout is docked/filled -- an
        # explicit size to report and (for VBox/HBox) distribute flex-marked
        # children's extra space within, instead of the usual shrink-to-fit
        # size derived from children alone. None (the default) preserves
        # today's undocked behavior exactly.
        self._target_w: int | None = None
        self._target_h: int | None = None

    def add(self, widget, flex: int = 0):
        """Append widget. flex=0 (default) is today's fixed-natural-size
        behavior. flex=N>0 marks it to share, proportional to N against
        every other flex-marked sibling's own weight, whatever space is
        left over once this layout's target size (dock_resize()) and every
        fixed sibling's natural size are accounted for -- see VBox/HBox's
        own _arrange(). Ignored unless this layout is docked/filled."""
        widget.parent = self
        widget._layout_y = 0
        widget._flex = flex
        self.children.append(widget)
        self._dirty = True
        return self

    def _children_changed(self) -> None:
        # Widget.remove()/clear() call this; a Layout caches its arrangement.
        self._dirty = True

    def dock_resize(self, w, h, scale) -> None:
        """Grow to fill the assigned slice (App.dock()/Box.dock()) -- unlike
        the default shrink-to-fit-children size, a docked/filled layout
        reports exactly this size from then on, and (VBox/HBox only, see
        their own `_arrange()`) redistributes any space beyond what its
        children naturally need to whichever children were added with
        `flex=`."""
        self._target_w = w
        self._target_h = h
        self._dirty = True

    @property
    def _display_width(self) -> int:
        return self._target_w if self._target_w is not None else self._computed_width

    @property
    def _display_height(self) -> int:
        return self._target_h if self._target_h is not None else self._computed_height

    def natural_width(self, scale):
        if self._dirty:
            self._arrange()
            self._dirty = False
        return self._display_width

    def natural_height(self, scale):
        if self._dirty:
            self._arrange()
            self._dirty = False
        return self._display_height

    def contains(self, col: int, row: int) -> bool:
        return (
            self.abs_x <= col < self.abs_x + self._display_width
            and self.abs_y <= row < self.abs_y + self._display_height
        )

    def _arrange(self):
        raise NotImplementedError

    def _flex_extras(self, sizes, target, gap):
        """Shared by VBox/HBox's own _arrange(): how much extra size (beyond
        its own entry in `sizes`, one per child in self.children, same
        order) to hand each child along the main axis, proportional to its
        `_flex` weight, from whatever's left of `target` (the axis's target
        size -- _target_h for VBox, _target_w for HBox) after every child's
        natural size and the `gap`s between them are accounted for. All
        zero unless `target` is not None and at least one child has
        flex > 0; never shrinks a child below its natural size even if the
        pool would be negative (children already need more than `target`)."""
        n = len(self.children)
        extras = [0] * n
        sum_flex = sum(c._flex for c in self.children)
        if target is None or sum_flex == 0:
            return extras
        total_gap = gap * (n - 1) if n else 0
        pool = max(0, target - total_gap - sum(sizes))
        if pool <= 0:
            return extras
        flex_indices = [i for i, c in enumerate(self.children) if c._flex > 0]
        distributed = 0
        for j, i in enumerate(flex_indices):
            if j == len(flex_indices) - 1:
                share = (
                    pool - distributed
                )  # remainder to the last, so the pool is fully consumed
            else:
                share = pool * self.children[i]._flex // sum_flex
                distributed += share
            extras[i] = share
        return extras

    def draw(self, canvas):
        if self._dirty:
            # Timed only when App(debug=True) (canvas._debug_log is then a
            # deque, never None) -- one attribute check for every other app,
            # no perf_counter() calls at all. Feeds the DevTools Performance
            # tab's "Layout" figure (see _devtools.py); accumulated rather
            # than overwritten since multiple Layout containers may
            # _arrange() within the same frame.
            if getattr(canvas, "_debug_log", None) is not None:
                start = time.perf_counter()
                self._arrange()
                canvas._debug_layout_ms += (time.perf_counter() - start) * 1000
            else:
                self._arrange()
        self._dirty = True  # re-dirty so next frame's natural_width/height recomputes
        for child in self.children:
            if child.visible:
                child.draw(canvas)
