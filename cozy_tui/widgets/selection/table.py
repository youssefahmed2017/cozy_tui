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

    THUMB = "█"
    TRACK = "─"

    def __init__(
        self,
        x,
        y,
        *,
        width: int | None = None,
        height: int | None = None,
        show_header: bool = True,
        show_border: bool = False,
        style=None,
        accent="bright_cyan",
    ):
        super().__init__(x, y, style)
        self._columns: list[dict] = []
        self._rows: list[TableRow] = []
        self._index: int = 0
        self._col_index: int = 0
        self._scroll_off: int = 0
        self._col_scroll_off: int = 0
        self.width = width
        self.height = height
        self.show_header = show_header
        self.show_border = show_border
        self.accent = accent
        self._select_handler = None
        self._col_width_cache: list[int] | None = None
        self._h_bar_row: int | None = None
        self._dragging_h_bar: bool = False
        self._sort_col: int | None = None
        self._sort_reverse: bool = False

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
        self._col_scroll_off = 0
        self._col_width_cache = None
        self._sort_col = None
        self._sort_reverse = False

    # ── sort ─────────────────────────────────────────────────────────────────

    def sort(self, column: str | int, *, reverse: bool = False) -> None:
        """Sort rows by column name or index. Also reachable by clicking a
        column header (toggling `reverse` on a repeat click of the same
        column) -- both update the header's `▲`/`▼` indicator, since this
        is the single place that tracks it.

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
        self._sort_col = ci
        self._sort_reverse = reverse
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

    def _viewport_width(self) -> int:
        return self.width if self.width is not None else self._total_width()

    def _shows_h_bar(self) -> bool:
        return self.width is not None and self._total_width() > self.width

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
        self._clamp_col_scroll()

    def _clamp_col_scroll(self) -> None:
        viewport_w = self._viewport_width()
        total_w = self._total_width()
        max_off = max(0, total_w - viewport_w)
        if max_off <= 0 or not self._columns:
            self._col_scroll_off = 0
            return
        widths = self._col_widths()
        border_offset = 1 if self.show_border else 0
        start = border_offset + sum(widths[: self._col_index]) + self._col_index
        end = start + widths[self._col_index]
        if start < self._col_scroll_off:
            self._col_scroll_off = start
        elif end > self._col_scroll_off + viewport_w:
            self._col_scroll_off = end - viewport_w
        self._col_scroll_off = max(0, min(self._col_scroll_off, max_off))

    def _col_at(self, col: int) -> int | None:
        """Column index under absolute column `col` (header or data row --
        both share the same per-column x layout), or None outside any
        column."""
        widths = self._col_widths()
        cx = self.abs_x - self._col_scroll_off
        if self.show_border:
            cx += 1
        for ci, w in enumerate(widths):
            if cx <= col < cx + w:
                return ci
            cx += w
            if ci < len(widths) - 1:
                cx += 1  # separator
        return None

    def _sort_by_column(self, ci: int) -> None:
        # A repeat click on the already-sorted column toggles direction;
        # clicking a different column always starts ascending.
        reverse = not self._sort_reverse if self._sort_col == ci else False
        self.sort(ci, reverse=reverse)

    # ── Widget interface ──────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        return self._viewport_width()

    def natural_height(self, scale) -> int:
        header_rows = 2 if self.show_header else 0
        border_rows = 2 if self.show_border else 0
        bar_rows = 1 if self._shows_h_bar() else 0
        return header_rows + self._visible_rows() + border_rows + bar_rows

    def contains(self, col: int, row: int) -> bool:
        w = self._viewport_width()
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

    def _bar_scroll_to(self, col: int) -> None:
        viewport_w = self._viewport_width()
        max_off = max(0, self._total_width() - viewport_w)
        if max_off <= 0:
            return
        rel = col - self.abs_x
        frac = rel / max(1, viewport_w - 1)
        self._col_scroll_off = max(0, min(max_off, round(frac * max_off)))

    def on_mouse_click(self, col=None, row=None) -> None:
        if row is not None and self._h_bar_row is not None and row == self._h_bar_row:
            self._dragging_h_bar = True
            if col is not None:
                self._bar_scroll_to(col)
            return
        self._dragging_h_bar = False
        if row is None:
            return
        if self.show_header and col is not None:
            header_y = self.abs_y + (1 if self.show_border else 0)
            if row == header_y:
                ci = self._col_at(col)
                if ci is not None:
                    self._sort_by_column(ci)
                return
        if not self._rows:
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

    def on_mouse_drag(self, col=None, row=None) -> None:
        if self._dragging_h_bar and col is not None:
            self._bar_scroll_to(col)

    def on_mouse_release(self, col=None, row=None) -> None:
        self._dragging_h_bar = False

    def _draw_h_scrollbar(self, canvas, x, row, viewport_w, total_w) -> None:
        raw_bg = self.style.raw_bg
        thumb = max(1, min(viewport_w, round(viewport_w * viewport_w / total_w)))
        span = viewport_w - thumb
        max_off = max(1, total_w - viewport_w)
        pos = round(span * (self._col_scroll_off / max_off)) if max_off else 0
        thumb_style = Style(fg=self.accent, bg=raw_bg)
        track_style = Style(fg="bright_black", bg=raw_bg)
        for c in range(viewport_w):
            on_thumb = pos <= c < pos + thumb
            canvas.write(
                x + c,
                row,
                self.THUMB if on_thumb else self.TRACK,
                thumb_style if on_thumb else track_style,
            )

    def draw(self, canvas) -> None:
        is_focused = canvas.focused is self
        widths = self._col_widths()
        if not widths:
            return

        n_cols = len(widths)
        total_w = self._total_width()
        vis = self._visible_rows()
        viewport_w = self._viewport_width()
        show_h_bar = self._shows_h_bar()
        x = self.abs_x
        y = self.abs_y
        ox = x - self._col_scroll_off
        table_raw_bg = self.style.raw_bg

        canvas.push_clip(x, y, x + viewport_w, y + self.natural_height(1))

        def write_row(row_y, cells, base_style, highlight_col: int | None = None):
            cx = ox
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
            canvas.write(ox, y, hline, self.style)
            y += 1

        # Header
        if self.show_header:
            header_style = Style(fg=self.style.fg, bg=table_raw_bg, styles=["bold"])
            write_row(y, [col["title"] for col in self._columns], header_style)
            if self._sort_col is not None and self._sort_col < n_cols:
                # Overlay the arrow on the sorted column's own trailing padding
                # space (_format_cell always wraps content in " ... ", so the
                # cell's last character is guaranteed blank) rather than
                # appending to the title text -- that would need every
                # auto-sized column widened to make room, reflowing the whole
                # table just because it got sorted.
                arrow = "▼" if self._sort_reverse else "▲"
                arrow_style = Style(fg=self.accent, bg=table_raw_bg, styles=["bold"])
                cx = ox + (1 if self.show_border else 0)
                for ci, w in enumerate(widths):
                    if ci == self._sort_col:
                        canvas.write(cx + w - 1, y, arrow, arrow_style)
                        break
                    cx += w + (1 if ci < n_cols - 1 else 0)
            y += 1
            if self.show_border:
                sep = "├" + "─" * widths[0]
                for w in widths[1:]:
                    sep += "┼" + "─" * w
                sep += "┤"
            else:
                sep = "─" * total_w
            canvas.write(ox, y, sep, self.style)
            y += 1

        # Data rows
        for row_off in range(vis):
            idx = self._scroll_off + row_off
            vy = y + row_off

            if idx >= len(self._rows):
                canvas.write(ox, vy, " " * total_w, self.style)
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
            canvas.write(ox, y + vis, hline, self.style)

        canvas.pop_clip()

        if show_h_bar:
            bar_y = y + vis + (1 if self.show_border else 0)
            self._h_bar_row = bar_y
            self._draw_h_scrollbar(canvas, x, bar_y, viewport_w, total_w)
        else:
            self._h_bar_row = None
