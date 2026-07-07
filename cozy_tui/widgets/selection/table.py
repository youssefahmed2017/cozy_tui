from cozy_tui.events import Key
from cozy_tui.style import Style, selection_style
from cozy_tui.widget import Widget


class TableRow:
    """A table row with optional per-row styling and metadata.

    Values are stored as strings.  The row supports index and iteration so
    existing code that treats it like a tuple keeps working::

        row[0]          # first cell value
        name, ver, *_  = row
    """

    def __init__(self, *values, style=None, disabled: bool = False, metadata=None):
        self.values = tuple(str(v) for v in values)
        self.style = (
            style  # Style override for unselected state; None = use table style
        )
        self.disabled = disabled
        self.metadata = metadata

    def __getitem__(self, index):
        return self.values[index]

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)

    def __repr__(self):
        return f"TableRow{self.values!r}"


class Table(Widget):
    """A focusable, scrollable table with optional header and border.

    Example::

        table = Table(2, 2, show_border=True)
        table.add_column("Name")
        table.add_column("Version", align="center")
        table.add_column("Size", align="right")
        table.add_row("cozy-kit", "1.2.0", "50 KB")
        table.add_row("CozyTUI", "0.8.0", "120 KB")
        table.on_select(lambda row: print(row[0]))
    """

    focusable = True

    def __init__(
        self,
        x,
        y,
        *,
        height: int | None = None,
        show_header: bool = True,
        show_border: bool = False,
        style=None,
    ):
        super().__init__(x, y, style, name="Table")
        self._columns: list[dict] = []
        self._rows: list[TableRow] = []
        self._index: int = 0
        self._col_index: int = 0
        self._scroll_off: int = 0
        self.height = height
        self.show_header = show_header
        self.show_border = show_border
        self._select_handler = None
        self._col_width_cache: list[int] | None = None

    # ── column API ───────────────────────────────────────────────────────────

    def add_column(
        self, title: str, *, width: int | None = None, align: str = "left"
    ) -> None:
        self._columns.append({"title": title, "width": width, "align": align})
        self._col_width_cache = None

    # ── row mutation API ─────────────────────────────────────────────────────

    def add_row(
        self, *values, style=None, disabled: bool = False, metadata=None
    ) -> None:
        self._rows.append(
            TableRow(*values, style=style, disabled=disabled, metadata=metadata)
        )
        self._col_width_cache = None

    def insert_row(
        self, index: int, *values, style=None, disabled: bool = False, metadata=None
    ) -> None:
        self._rows.insert(
            index, TableRow(*values, style=style, disabled=disabled, metadata=metadata)
        )
        if index <= self._index:
            self._index = min(self._index + 1, len(self._rows) - 1)
        self._col_width_cache = None

    def remove_row(self, index: int) -> None:
        self._rows.pop(index)
        if self._rows:
            self._index = min(self._index, len(self._rows) - 1)
        else:
            self._index = 0
        self._scroll_off = min(self._scroll_off, max(0, len(self._rows) - 1))
        self._col_width_cache = None

    def set_cell(self, row_index: int, col_index: int, value) -> None:
        """Replace the value of a single cell."""
        row = self._rows[row_index]
        vals = list(row.values)
        vals[col_index] = str(value)
        row.values = tuple(vals)
        self._col_width_cache = None

    def update_row(self, index: int, *values) -> None:
        """Replace all cell values in a row, preserving its style and metadata."""
        row = self._rows[index]
        row.values = tuple(str(v) for v in values)
        self._col_width_cache = None

    def clear_rows(self) -> None:
        self._rows.clear()
        self._index = 0
        self._scroll_off = 0
        self._col_width_cache = None

    def clear(self) -> None:
        self._columns.clear()
        self._rows.clear()
        self._index = 0
        self._col_index = 0
        self._scroll_off = 0
        self._col_width_cache = None

    # ── sort ─────────────────────────────────────────────────────────────────

    def sort(self, column: str | int, *, reverse: bool = False) -> None:
        """Sort rows by column name or index.

        The current selection follows its row after sorting.
        """
        if isinstance(column, str):
            ci = next(
                (i for i, c in enumerate(self._columns) if c["title"] == column), None
            )
            if ci is None:
                raise ValueError(f"No column {column!r}")
        else:
            ci = column
        selected = self._rows[self._index] if self._rows else None
        self._rows.sort(
            key=lambda r: r.values[ci] if ci < len(r.values) else "",
            reverse=reverse,
        )
        if selected is not None:
            try:
                self._index = self._rows.index(selected)
            except ValueError:
                self._index = 0
        self._clamp_scroll()

    # ── selection API ────────────────────────────────────────────────────────

    @property
    def selected_row(self) -> TableRow | None:
        return self._rows[self._index] if self._rows else None

    @property
    def selected_index(self) -> int | None:
        return self._index if self._rows else None

    @property
    def selected_column(self) -> int:
        return self._col_index

    def on_select(self, func):
        """Called with the selected TableRow when Enter is pressed or a row is clicked."""
        self._select_handler = func
        return self

    # ── internals ────────────────────────────────────────────────────────────

    def _col_widths(self) -> list[int]:
        if self._col_width_cache is not None:
            return self._col_width_cache
        widths = []
        for ci, col in enumerate(self._columns):
            if col["width"] is not None:
                widths.append(col["width"])
            else:
                w = len(col["title"])
                for row in self._rows:
                    if ci < len(row.values):
                        w = max(w, len(row.values[ci]))
                widths.append(w + 2)  # 1-space padding on each side
        self._col_width_cache = widths
        return widths

    def _total_width(self) -> int:
        widths = self._col_widths()
        if not widths:
            return 0
        n = len(widths)
        if self.show_border:
            return sum(widths) + n + 1
        return sum(widths) + n - 1

    def _visible_rows(self) -> int:
        return self.height or len(self._rows)

    def _data_start_y(self) -> int:
        y = self.abs_y
        if self.show_border:
            y += 1
        if self.show_header:
            y += 2
        return y

    @staticmethod
    def _format_cell(text: str, col_width: int, align: str) -> str:
        inner = col_width - 2
        if align == "right":
            content = text[:inner].rjust(inner)
        elif align == "center":
            content = text[:inner].center(inner)
        else:
            content = text[:inner].ljust(inner)
        return f" {content} "

    def _clamp_scroll(self) -> None:
        vis = self._visible_rows()
        if vis <= 0:
            return
        if self._index < self._scroll_off:
            self._scroll_off = self._index
        elif self._index >= self._scroll_off + vis:
            self._scroll_off = self._index - vis + 1

    def _move_row(self, new_index: int) -> None:
        if not self._rows:
            return
        self._index = max(0, min(new_index, len(self._rows) - 1))
        self._clamp_scroll()
        self._fire_change(self.selected_row)

    def _move_col(self, delta: int) -> None:
        if not self._columns:
            return
        self._col_index = max(0, min(self._col_index + delta, len(self._columns) - 1))

    # ── Widget interface ──────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        return self._total_width()

    def natural_height(self, scale) -> int:
        header_rows = 2 if self.show_header else 0
        border_rows = 2 if self.show_border else 0
        return header_rows + self._visible_rows() + border_rows

    def contains(self, col: int, row: int) -> bool:
        w = self._total_width()
        h = self.natural_height(1)
        return self.abs_x <= col < self.abs_x + w and self.abs_y <= row < self.abs_y + h

    def on_key(self, key) -> None:
        if key == Key.UP:
            self._move_row(self._index - 1)
        elif key == Key.DOWN:
            self._move_row(self._index + 1)
        elif key == Key.LEFT:
            self._move_col(-1)
        elif key == Key.RIGHT:
            self._move_col(1)
        elif key == Key.HOME:
            self._move_row(0)
        elif key == Key.END:
            self._move_row(len(self._rows) - 1)
        elif key == Key.ENTER:
            if self._rows:
                self._fire_click()  # on_click(widget): fires on Enter or click
                if self._select_handler:
                    self._select_handler(self.selected_row)

    def on_mouse_click(self, col=None, row=None) -> None:
        if row is None or not self._rows:
            return
        clicked = self._scroll_off + (row - self._data_start_y())
        if 0 <= clicked < len(self._rows):
            old = self._index
            self._index = clicked
            self._clamp_scroll()
            if clicked != old:
                self._fire_change(self.selected_row)
            self._fire_click()  # on_click(widget): fires on Enter or click
            if self._select_handler:
                self._select_handler(self.selected_row)

    def draw(self, canvas) -> None:
        is_focused = canvas.focused is self
        widths = self._col_widths()
        if not widths:
            return

        n_cols = len(widths)
        total_w = self._total_width()
        vis = self._visible_rows()
        x = self.abs_x
        y = self.abs_y
        table_raw_bg = self.style.raw_bg

        def write_row(row_y, cells, base_style, highlight_col: int | None = None):
            cx = x
            if self.show_border:
                canvas.write(cx, row_y, "│", self.style)
                cx += 1
            for ci, w in enumerate(widths):
                align = self._columns[ci]["align"] if ci < n_cols else "left"
                cell_text = cells[ci] if ci < len(cells) else ""
                if highlight_col is not None and ci == highlight_col:
                    cell_bg = base_style.raw_bg
                    cell_style = Style(
                        fg=base_style.fg,
                        bg=cell_bg,
                        styles=list(base_style.styles) + ["underline"],
                    )
                else:
                    cell_style = base_style
                canvas.write(
                    cx, row_y, self._format_cell(cell_text, w, align), cell_style
                )
                cx += w
                if ci < n_cols - 1:
                    canvas.write(cx, row_y, "│", self.style)
                    cx += 1
            if self.show_border:
                canvas.write(cx, row_y, "│", self.style)

        # Top border
        if self.show_border:
            hline = "┌" + "─" * widths[0]
            for w in widths[1:]:
                hline += "┬" + "─" * w
            hline += "┐"
            canvas.write(x, y, hline, self.style)
            y += 1

        # Header
        if self.show_header:
            header_style = Style(fg=self.style.fg, bg=table_raw_bg, styles=["bold"])
            write_row(y, [col["title"] for col in self._columns], header_style)
            y += 1
            if self.show_border:
                sep = "├" + "─" * widths[0]
                for w in widths[1:]:
                    sep += "┼" + "─" * w
                sep += "┤"
            else:
                sep = "─" * total_w
            canvas.write(x, y, sep, self.style)
            y += 1

        # Data rows
        for row_off in range(vis):
            idx = self._scroll_off + row_off
            vy = y + row_off

            if idx >= len(self._rows):
                canvas.write(x, vy, " " * total_w, self.style)
                continue

            row = self._rows[idx]
            is_sel = idx == self._index

            if is_focused and is_sel:
                row_style = selection_style()
                highlight_col = self._col_index
            elif is_sel:
                row_style = selection_style(dim=True)
                highlight_col = None
            elif row.style is not None:
                row_style = row.style
                highlight_col = None
            else:
                row_style = self.style
                highlight_col = None

            write_row(vy, list(row.values), row_style, highlight_col)

        # Bottom border
        if self.show_border:
            hline = "└" + "─" * widths[0]
            for w in widths[1:]:
                hline += "┴" + "─" * w
            hline += "┘"
            canvas.write(x, y + vis, hline, self.style)
