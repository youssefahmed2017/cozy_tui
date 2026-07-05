from collections import deque

from cozy_tui.style import Style
from cozy_tui.widget import Widget
from cozy_tui.widgets.input._input_draw import _DrawMixin
from cozy_tui.widgets.input._input_history import _HistoryMixin
from cozy_tui.widgets.input._input_keys import _KeysMixin


class Input(_HistoryMixin, _DrawMixin, _KeysMixin, Widget):
    focusable = True

    def __init__(
        self,
        x,
        y,
        width,
        placeholder="",
        style=None,
        cursor=True,
        cursor_style="vertical",
        flash=True,
        multiline=False,
        masked=False,
        masked_symbol="*",
    ):
        super().__init__(x, y, style)
        self.laps = True
        self.width = width
        self.placeholder = placeholder
        self.value = ""
        self.cursor_pos = 0
        self._scroll_off = 0
        self.cursor = cursor
        self.cursor_style = cursor_style
        self.flash = flash
        self.multiline = multiline
        self.masked = masked
        self.masked_symbol = masked_symbol
        self._overwrite = False
        self._sel_anchor: int | None = None
        self._masked_cache_key: str | None = None  # identity-cached masked display
        self._masked_cache_val: str = ""
        self._undo_stack = deque(maxlen=_HistoryMixin._MAX_HISTORY)
        self._redo_stack: list = []
        self._last_action: str | None = None
        self.laps = True

    def natural_width(self, scale):
        return self.width

    # ── selection helpers ────────────────────────────────────────────────────

    def _sel_range(self) -> tuple[int, int] | None:
        """Return (start, end) selection range, or None when nothing is selected."""
        if self._sel_anchor is None or self._sel_anchor == self.cursor_pos:
            return None
        a, b = self._sel_anchor, self.cursor_pos
        return (a, b) if a < b else (b, a)

    def _sel_text(self) -> str:
        r = self._sel_range()
        return self.value[r[0] : r[1]] if r else ""

    def _clear_sel(self) -> None:
        self._sel_anchor = None

    def _delete_sel(self) -> None:
        r = self._sel_range()
        if r is None:
            return
        a, b = r
        self.value = self.value[:a] + self.value[b:]
        self.cursor_pos = a
        self._sel_anchor = None

    def _shift_move(self, new_pos: int) -> None:
        """Move cursor to new_pos while extending/creating a selection."""
        new_pos = max(0, min(new_pos, len(self.value)))
        if self._sel_anchor is None:
            self._sel_anchor = self.cursor_pos
        self.cursor_pos = new_pos
        if self.cursor_pos == self._sel_anchor:
            self._sel_anchor = None

    def _sel_style(self) -> Style:
        return Style(fg="white", bg="blue")

    # ── word-boundary helpers ────────────────────────────────────────────────

    def _word_right(self, pos: int) -> int:
        v = self.value
        n = len(v)
        while pos < n and not (v[pos].isalnum() or v[pos] == "_"):
            pos += 1
        while pos < n and (v[pos].isalnum() or v[pos] == "_"):
            pos += 1
        return pos

    def _word_left(self, pos: int) -> int:
        v = self.value
        pos -= 1
        while pos > 0 and not (v[pos].isalnum() or v[pos] == "_"):
            pos -= 1
        while pos > 0 and (v[pos - 1].isalnum() or v[pos - 1] == "_"):
            pos -= 1
        return max(0, pos)

    # ── position helpers ─────────────────────────────────────────────────────

    def _cursor_to_line_col(self):
        """Return (line_index, col) for cursor_pos within value.split('\\n')."""
        before = self.value[: self.cursor_pos]
        parts = before.split("\n")
        return len(parts) - 1, len(parts[-1])

    def _line_col_to_pos(self, line: int, col: int) -> int:
        """Convert (line, col) to a flat cursor_pos."""
        lines = self.value.split("\n")
        pos = sum(len(lines[i]) + 1 for i in range(line))
        return pos + min(col, len(lines[line]) if line < len(lines) else 0)

    def _get_cursor_screen_pos(self, scroll_y: int):
        """Return (col, row) screen coordinates for the cursor, or None."""
        w = self._clip_width or self.width

        if self.multiline:
            cur_line, cur_col = self._cursor_to_line_col()
            display_row = 0
            for li, logical_line in enumerate((self.value or "").split("\n")):
                chunks_count = (
                    max(1, (len(logical_line) + w - 1) // w) if logical_line else 1
                )
                if li == cur_line:
                    chunk_row = cur_col // w
                    return (
                        self.abs_x + (cur_col % w),
                        self.abs_y + display_row + chunk_row - scroll_y,
                    )
                display_row += chunks_count
            return None

        elif self._clip_width:
            cline = self.cursor_pos // w
            ccol = self.cursor_pos % w
            return self.abs_x + ccol, self.abs_y + cline - scroll_y

        else:
            ccol = self.cursor_pos - self._scroll_off
            if 0 <= ccol < w:
                return self.abs_x + ccol, self.abs_y - scroll_y
            return None

    def natural_height(self, scale):
        w = self._clip_width or self.width
        return self._row_count(w)

    def _row_count(self, w: int) -> int:
        if self.multiline:
            logical = self.value.split("\n") if self.value else [""]
            return sum(max(1, (len(l) + w - 1) // w) for l in logical)
        return max(1, (len(self.value) + w - 1) // w) if self.value else 1

    # ── hit-testing ──────────────────────────────────────────────────────────

    def contains(self, col: int, row: int) -> bool:
        w = self._clip_width or self.width
        if self.multiline and self.value:
            h = self._row_count(w)
        elif self._clip_width and self.value:
            h = self._row_count(self._clip_width)
        else:
            h = 1
        return self.abs_x <= col < self.abs_x + w and self.abs_y <= row < self.abs_y + h

    # ── styles ───────────────────────────────────────────────────────────────

    def _normal_style(self):
        return self.style

    def _focused_style(self):
        return Style(fg="black", bg="white")

    def _placeholder_style(self, focused: bool = False):
        if focused:
            return Style(fg="bright_black", bg="white", styles=["dim"])
        raw_bg = self.style.raw_bg
        return Style(fg=self.style.fg, bg=raw_bg, styles=["dim"])

    def _cursor_style_obj(self, char_at_cursor, content_style: Style):
        fg = content_style.fg
        bg = content_style.bg
        raw_bg = bg.replace("_bg", "") if bg else None

        if self.cursor_style == "block":
            return Style(fg=raw_bg or "black", bg=fg or "white"), char_at_cursor
        else:
            return Style(fg=fg, bg=raw_bg, styles=["underline"]), char_at_cursor

    # ── mouse ────────────────────────────────────────────────────────────────

    def on_mouse_click(self, col=None, row=None):
        self._clear_sel()
        if col is not None and row is not None:
            self._set_cursor_from_mouse(col, row)
            self._sel_anchor = self.cursor_pos  # anchor for potential drag
        self._fire_click()

    def on_mouse_drag(self, col: int, row: int) -> None:
        self._set_cursor_from_mouse(col, row)

    def _set_cursor_from_mouse(self, col: int, row: int) -> None:
        """Position cursor_pos from a terminal click at (col, row)."""
        w = self._clip_width or self.width
        if self.multiline:
            target_row = row - self.abs_y
            display_row = 0
            flat_pos = 0
            value_lines = self.value.split("\n")
            for li, logical_line in enumerate(self._display_value.split("\n")):
                vline_len = len(value_lines[li]) if li < len(value_lines) else 0
                chunks_count = (
                    max(1, (len(logical_line) + w - 1) // w) if logical_line else 1
                )
                if display_row + chunks_count > target_row:
                    chunk_idx = target_row - display_row
                    col_in_chunk = max(0, col - self.abs_x)
                    pos = flat_pos + chunk_idx * w + col_in_chunk
                    self.cursor_pos = max(0, min(pos, flat_pos + vline_len))
                    return
                display_row += chunks_count
                flat_pos += vline_len + 1
            self.cursor_pos = len(self.value)
        elif self._clip_width:
            line = max(0, row - self.abs_y)
            pos = line * w + max(0, col - self.abs_x)
            self.cursor_pos = max(0, min(pos, len(self.value)))
        else:
            pos = self._scroll_off + max(0, col - self.abs_x)
            self.cursor_pos = max(0, min(pos, len(self.value)))

    def get(self):
        return self.value
