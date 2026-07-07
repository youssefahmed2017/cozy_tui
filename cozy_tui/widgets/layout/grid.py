from cozy_tui.widgets.layout.layout import Layout


class Grid(Layout):
    """Arrange children in a fixed number of columns, left to right, top to bottom.

    Column widths and row heights are sized to fit the widest/tallest child
    in each column/row respectively.
    """

    def __init__(self, x, y, cols, gap_x=1, gap_y=0, style=None):
        super().__init__(x, y, style, name="Grid")
        self.cols = cols
        self.gap_x = gap_x
        self.gap_y = gap_y

    def _arrange(self):
        if not self.children:
            self._computed_width = 0
            self._computed_height = 0
            return

        rows = (len(self.children) + self.cols - 1) // self.cols

        col_widths = [0] * self.cols
        row_heights = [0] * rows

        for i, child in enumerate(self.children):
            col = i % self.cols
            row = i // self.cols
            col_widths[col] = max(col_widths[col], child.natural_width(1))
            row_heights[row] = max(row_heights[row], child.natural_height(1))

        col_x = []
        cx = 0
        for w in col_widths:
            col_x.append(cx)
            cx += w + self.gap_x

        row_y = []
        cy = 0
        for h in row_heights:
            row_y.append(cy)
            cy += h + self.gap_y

        for i, child in enumerate(self.children):
            child.x = col_x[i % self.cols]
            child.y = row_y[i // self.cols]
            child._layout_y = 0

        self._computed_width = cx - self.gap_x
        self._computed_height = cy - self.gap_y
