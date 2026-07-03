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
        self.text = text
        self.title = title
        # Non-focusable by default: Tab still dives into any focusable children,
        # but an empty/decorative box only becomes a Tab stop when focusable=True.
        self.focusable = focusable
        self.width, self.height = map(int, size.split("x"))
        self.border = self.BORDERS[border]
        self.children = []
        self._bounds = (0, 0, 0, 0)  # last drawn (x, y, w, h) in cells, for hit-testing
        raw_bg = self.style.bg.replace("_bg", "") if self.style.bg else None
        self._focused_border_style_cache = Style(
            fg="bright_white", bg=raw_bg, styles=["bold"]
        )

    def natural_width(self, scale):
        return self.width // scale + 2

    def natural_height(self, scale):
        return self.height // scale + 2

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

    def _layout(self, canvas):
        scale = canvas.SCALE
        width = max(self.width // scale, len(self.text) + 3)
        height = self.height // scale

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

        return width, height + total_extra

    def draw(self, canvas):
        self._apply_docks(canvas)
        width, height = self._layout(canvas)
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
            child.draw(canvas)

        # Draw borders last; highlight when a descendant has focus
        bs = self._focused_border_style_cache if focused else self.style
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

    def _focus_border_style(self):
        raw_bg = self.style.bg.replace("_bg", "") if self.style.bg else None
        return Style(fg="bright_white", bg=raw_bg, styles=["bold"])

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
