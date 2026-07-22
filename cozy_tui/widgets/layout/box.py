from cozy_tui._dock import SIDES, dock_layout
from cozy_tui.style import Style
from cozy_tui.widget import Widget


class Box(Widget):
    BORDERS = {
        "single": ("++++", "-", "|"),
        "double": ("╔╗╚╝", "═", "║"),
        "rounded": ("╭╮╰╯", "─", "│"),
        "bold": ("┏┓┗┛", "━", "┃"),
        "none": ("    ", " ", " "),
    }

    def __init__(
        self,
        x,
        y,
        size,
        text: str = "",
        border: str = "single",
        style=None,
        title="",
        focusable=False,
    ):
        super().__init__(x, y, style)
        self.bind("text", text)  # text/title may each be a State
        self.bind("title", title)
        # Non-focusable by default: Tab still dives into any focusable children,
        # but an empty/decorative box only becomes a Tab stop when focusable=True.
        self.focusable = focusable
        self.width, self.height = map(int, size.split("x"))
        # Stable floor for _layout()'s wrap-growth (never touched by
        # dock_resize(), unlike self.height): a "top"/"bottom"-docked box's
        # natural_height() is queried to reserve a dock band *before*
        # dock_resize() runs, so if that computation instead floored on the
        # live self.height, a one-time bad reservation (e.g. on the very
        # first frame, before self.width had converged to the terminal's
        # real width) would get baked into self.height by dock_resize(),
        # which _layout() would then use as *next* frame's floor too --
        # permanently inflating it instead of converging back down once the
        # real width was known. self.height keeps its normal job (the box's
        # actual current render size); this is only _layout()'s minimum.
        self._min_height = self.height
        self.border = self.BORDERS[border]
        self.children = []
        self._bounds = (0, 0, 0, 0)  # last drawn (x, y, w, h) in cells, for hit-testing

    def _focused_border_style(self) -> Style:
        """The bold-white border drawn while this box is focused. Built per
        draw rather than cached at construction: `self.style`'s background is
        re-colored in place when the active theme changes (see
        `App._sync_theme_style`), and a cached copy would keep the old one.
        `ansi.style_esc` memoizes the escape anyway, so this costs nothing."""
        return Style(fg="bright_white", bg=self.style.raw_bg, styles=["bold"])

    def _fill_docked(self) -> bool:
        # True only for side="fill" -- that's the one dock side whose
        # dock_resize() assigns self.width/height *directly* (see
        # dock_layout's fill branch), never derived from this box's own
        # natural_width/height() output, so it's safe to trust as a floor
        # here. Every other side's assigned size *is* derived from a
        # previous natural_width/height() call (via the dock band
        # reservation), so trusting it back would reopen the same feedback
        # loop _min_height exists to avoid -- see __init__ and _layout().
        dock = getattr(self, "_dock", None)
        return dock is not None and dock[0] == "fill"

    def natural_width(self, scale):
        # Runs the same layout pass draw() uses, so a Box whose content grows
        # it wider (a non-lapping child past its edge) or taller (a lapping
        # child wrapping) is measured correctly by anything sizing around it
        # -- notably the dock system, which reserves a "top"/"bottom"/"left"/
        # "right" band from natural_width/height() *before* dock_resize() is
        # called, so an unaware size here previously let wrapped content grow
        # right past whatever band had already been reserved for it.
        width, _height = self._layout(scale)
        if self._fill_docked():
            width = max(width, self.width // scale)
        return width + 2

    def natural_height(self, scale):
        _width, height = self._layout(scale)
        if self._fill_docked():
            height = max(height, self.height // scale)
        return height + 2

    def dock_resize(self, w, h, scale):
        # Grow to fill the assigned slice; the border eats 2 cells each way.
        self.width = max(0, w - 2) * scale
        self.height = max(0, h - 2) * scale

    def _box_chars(self, width, border=None):
        corners, h, v = border if border is not None else self.border
        tl, tr, bl, br = corners

        if self.title:
            title = f" {self.title} "
            remaining = max(0, width - len(title))
            top = tl + h + title + h * (remaining - 1) + tr
        else:
            top = tl + h * width + tr

        bottom = bl + h * width + br

        return top, bottom, v

    def _layout(self, scale):
        width = max(self.width // scale, len(self.text) + 3)
        # Always floors on the immutable _min_height, never the live
        # self.height -- self.height already *is* min_height + a previous
        # total_extra once this box has ever been "top"/"bottom"-docked (see
        # __init__), so flooring on it here would add that total_extra a
        # second time on top of itself, every single frame.
        height = self._min_height // scale

        # Reset layout state for all children
        for child in self.children:
            child._layout_y = 0
            child._clip_width = None

        # Expand width only for children that are neither Label nor Input
        for child in self.children:
            if not child.laps:
                child_right = child.x + child.natural_width(scale)
                if child_right > width:
                    width = child_right

        # Detect overflow for lapping children and compute extra lines each adds.
        # After _clip_width is set, every lapping widget's natural_height() is correct.
        overflow_extra = {}
        for child in self.children:
            if child.laps:
                child_right = child.x + child.natural_width(scale)
                if child_right > width:
                    child._clip_width = max(1, width - child.x)
                extra = child.natural_height(scale) - 1
                if extra > 0:
                    overflow_extra[id(child)] = extra

        # Push children down: accumulate shifts from wrapping children above each row.
        # Children at the same y all get the same shift (group by y).
        y_groups = {}
        for child in self.children:
            y_groups.setdefault(child.y, []).append(child)

        total_extra = 0
        for y in sorted(y_groups):
            group_extra = 0
            for child in y_groups[y]:
                child._layout_y = total_extra
                group_extra = max(group_extra, overflow_extra.get(id(child), 0))
            total_extra += group_extra
        height += total_extra

        # Grow height to fit every child's bottom edge -- symmetric to how
        # width already grows from non-lapping children's right edge above.
        # Without this, a box built at a placeholder size and sized entirely
        # by dock_resize() (e.g. a Splitter pane, which sets self.height but
        # never _min_height -- see __init__) collapses to _min_height's floor
        # whenever its children fit the (correctly grown) width without
        # needing to wrap: nothing else ever grows height for them, so a
        # child positioned below row 0 draws past the box's own bottom
        # border instead of being enclosed by it.
        for child in self.children:
            # -1: content rows are 1..height (row 0 is the border -- see
            # draw()'s own interior-fill loop, `abs_y + 1 + j` for
            # `j in range(height)`, i.e. rows abs_y+1..abs_y+height), so a
            # child's *last* occupied row is what must fit within `height`,
            # not one past it.
            child_bottom = child.y + child._layout_y + child.natural_height(scale) - 1
            if child_bottom > height:
                height = child_bottom

        return width, height

    def draw(self, canvas):
        self._apply_docks(canvas)
        width, height = self._layout(canvas.SCALE)
        if self._fill_docked():  # self.height is authoritative here, see _fill_docked()
            height = max(height, self.height // canvas.SCALE)
        self._bounds = (self.abs_x, self.abs_y, width + 2, height + 2)
        middle_height = (self.height // canvas.SCALE) // 2
        focused = self._has_focused(canvas)
        border_override = self.BORDERS["bold"] if focused else None
        top, bottom, v = self._box_chars(width, border_override)

        # Fill interior
        for j in range(height):
            content = (
                self.text.center(width)
                if j == middle_height and self.text
                else " " * width
            )
            canvas.write(self.abs_x + 1, self.abs_y + 1 + j, content, self.style)

        # Draw children over interior
        for child in self.children:
            if child.visible:
                child.draw(canvas)

        # Draw borders last; highlight when a descendant has focus
        bs = self._focused_border_style() if focused else self.style
        canvas.write(self.abs_x, self.abs_y, top, bs)
        for j in range(height):
            canvas.write(self.abs_x, self.abs_y + 1 + j, v, bs)
            canvas.write(self.abs_x + width + 1, self.abs_y + 1 + j, v, bs)
        canvas.write(self.abs_x, self.abs_y + height + 1, bottom, bs)

    def contains(self, col: int, row: int) -> bool:
        x, y, w, h = self._bounds
        return x <= col < x + w and y <= row < y + h

    def _has_focused(self, canvas) -> bool:
        # True when the box itself is focused, or any descendant is. Walk UP the
        # parent chain from the focused widget — O(depth) vs O(N widgets).
        w = canvas.focused
        while w is not None:
            if w is self:
                return True
            w = w.parent
        return False

    def add(self, widget):
        widget.parent = self
        self.children.append(widget)

    def dock(self, widget, side, margin=0):
        """Dock `widget` against an interior edge of this box.

        `side` is one of "left", "right", "top", "bottom", or "fill". Each dock
        consumes a band from the box's remaining interior (in call order) and
        the widget stretches across the other axis; "fill" takes whatever space
        is left. Docks are recomputed every frame, so they survive resizes and
        content changes. `margin` insets the widget from the consumed edge.
        Returns the widget for chaining.
        """
        if side not in SIDES:
            raise ValueError(f"dock side must be one of {SIDES}, got {side!r}")
        widget._dock = (side, margin)
        if widget not in self.children:
            self.add(widget)
        return widget

    def _apply_docks(self, canvas):
        items = [
            (c, c._dock[0], c._dock[1])
            for c in self.children
            if getattr(c, "_dock", None) is not None
        ]
        if not items:
            return
        scale = canvas.SCALE
        # Interior top-left cell (inside the border) is (1, 1).
        dock_layout(items, 1, 1, self.width // scale, self.height // scale, scale)
