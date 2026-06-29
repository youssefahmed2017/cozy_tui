from cozy_tui.widget import Widget
from cozy_tui.style import Style
from cozy_tui.events import Key


class Input(Widget):
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
    ):
        super().__init__(x, y, style)
        self.width = width
        self.placeholder = placeholder
        self.value = ""
        self.cursor_pos = 0      # caret position (flat index into value)
        self._scroll_off = 0     # horizontal scroll offset (single-line mode)
        self.cursor = cursor
        self.cursor_style = cursor_style
        self.flash = flash
        self.multiline = multiline

    def natural_width(self, scale):
        return self.width

    # ── position helpers (multi-line) ────────────────────────────────────────

    def _cursor_to_line_col(self):
        """Return (line_index, col) for cursor_pos within value.split('\\n')."""
        before = self.value[: self.cursor_pos]
        parts = before.split("\n")
        return len(parts) - 1, len(parts[-1])

    def _line_col_to_pos(self, line: int, col: int) -> int:
        """Convert (line, col) to a flat cursor_pos."""
        lines = self.value.split("\n")
        pos = sum(len(lines[i]) + 1 for i in range(line))   # +1 for the \n
        return pos + min(col, len(lines[line]) if line < len(lines) else 0)

    def _get_cursor_screen_pos(self, scroll_y: int):
        """Return (col, row) screen coordinates for the cursor, or None."""
        w = self._clip_width or self.width

        if self.multiline:
            cur_line, cur_col = self._cursor_to_line_col()
            display_row = 0
            for li, logical_line in enumerate((self.value or "").split("\n")):
                chunks_count = max(1, (len(logical_line) + w - 1) // w) if logical_line else 1
                if li == cur_line:
                    chunk_row = cur_col // w
                    return (self.abs_x + (cur_col % w),
                            self.abs_y + display_row + chunk_row - scroll_y)
                display_row += chunks_count
            return None

        elif self._clip_width:
            cline = self.cursor_pos // w
            ccol  = self.cursor_pos % w
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
        """Total display rows needed for current value at display width w."""
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
        return Style(fg="black", bg="white")   # Style() adds _bg automatically

    def _placeholder_style(self, focused: bool = False):
        if focused:
            return Style(fg="bright_black", bg="white", styles=["dim"])
        raw_bg = self.style.bg.replace("_bg", "") if self.style.bg else None
        return Style(fg=self.style.fg, bg=raw_bg, styles=["dim"])

    def _cursor_style_obj(self, char_at_cursor, content_style: Style):
        fg = content_style.fg
        bg = content_style.bg                            # has _bg suffix or None
        raw_bg = bg.replace("_bg", "") if bg else None   # strip suffix for Style()

        if self.cursor_style == "block":
            return Style(fg=raw_bg or "black", bg=fg or "white"), char_at_cursor
        elif self.cursor_style == "underline":
            return Style(fg=fg, bg=raw_bg, styles=["underline"]), char_at_cursor
        else:   # vertical (default) — underline the char so it never disappears
            return Style(fg=fg, bg=raw_bg, styles=["underline"]), char_at_cursor

    # ── key handling ─────────────────────────────────────────────────────────

    def on_key(self, key):
        if key == Key.LEFT:
            self.cursor_pos = max(0, self.cursor_pos - 1)

        elif key == Key.RIGHT:
            self.cursor_pos = min(len(self.value), self.cursor_pos + 1)

        elif key == Key.HOME:
            if self.multiline:
                line, _ = self._cursor_to_line_col()
                self.cursor_pos = self._line_col_to_pos(line, 0)
            else:
                self.cursor_pos = 0

        elif key == Key.END:
            if self.multiline:
                line, _ = self._cursor_to_line_col()
                lines = self.value.split("\n")
                self.cursor_pos = self._line_col_to_pos(line, len(lines[line]))
            else:
                self.cursor_pos = len(self.value)

        elif key == Key.UP and self.multiline:
            line, col = self._cursor_to_line_col()
            if line > 0:
                lines = self.value.split("\n")
                self.cursor_pos = self._line_col_to_pos(line - 1, min(col, len(lines[line - 1])))

        elif key == Key.DOWN and self.multiline:
            line, col = self._cursor_to_line_col()
            lines = self.value.split("\n")
            if line < len(lines) - 1:
                self.cursor_pos = self._line_col_to_pos(line + 1, min(col, len(lines[line + 1])))

        elif key == Key.BACKSPACE:
            if self.cursor_pos > 0:
                self.value = self.value[: self.cursor_pos - 1] + self.value[self.cursor_pos :]
                self.cursor_pos -= 1

        elif key == Key.DELETE:
            if self.cursor_pos < len(self.value):
                self.value = self.value[: self.cursor_pos] + self.value[self.cursor_pos + 1 :]

        elif key == Key.SHIFT_ENTER and self.multiline:
            self.value = self.value[: self.cursor_pos] + "\n" + self.value[self.cursor_pos :]
            self.cursor_pos += 1

        elif (
            key not in (Key.ESC, Key.ENTER, Key.TAB, Key.UP, Key.DOWN)
            and len(key) == 1
            and key.isprintable()
        ):
            self.value = self.value[: self.cursor_pos] + key + self.value[self.cursor_pos :]
            self.cursor_pos += 1

    # ── drawing ──────────────────────────────────────────────────────────────

    def draw(self, canvas):
        is_focused = canvas.focused is self
        if self.multiline:
            self._draw_multiline(canvas, is_focused)
        elif self._clip_width:
            self._draw_wrapped(canvas, is_focused)
        else:
            self._draw_scrolling(canvas, is_focused)

    def _draw_scrolling(self, canvas, is_focused):
        w = self.width
        cs = self._focused_style() if is_focused else self._normal_style()

        if self.value:
            if self.cursor_pos < self._scroll_off:
                self._scroll_off = self.cursor_pos
            elif self.cursor_pos >= self._scroll_off + w:
                self._scroll_off = self.cursor_pos - w + 1
            visible = self.value[self._scroll_off : self._scroll_off + w].ljust(w)
            cursor_col = self.cursor_pos - self._scroll_off
            canvas.write(self.abs_x, self.abs_y, visible, cs)
            cursor_visible = canvas._cursor_on if self.cursor else False
            if (self.cursor and is_focused and cursor_visible
                    and self.cursor_style != "vertical"
                    and 0 <= cursor_col < w):
                char_at = visible[cursor_col] if cursor_col < len(visible) else " "
                cur_style, cur_char = self._cursor_style_obj(char_at, cs)
                canvas.write(self.abs_x + cursor_col, self.abs_y, cur_char, cur_style)
        else:
            canvas.write(self.abs_x, self.abs_y, self.placeholder[:w].ljust(w),
                         self._placeholder_style(is_focused))

    def _draw_wrapped(self, canvas, is_focused):
        w = self._clip_width
        cs = self._focused_style() if is_focused else self._normal_style()

        if self.value:
            lines = [self.value[i : i + w] for i in range(0, len(self.value), w)]
            cursor_line = self.cursor_pos // w
            cursor_col  = self.cursor_pos % w
            while len(lines) <= cursor_line:
                lines.append("")
            for i, line in enumerate(lines):
                canvas.write(self.abs_x, self.abs_y + i, line.ljust(w), cs)
            cursor_visible = canvas._cursor_on if self.flash else True
            if self.cursor and is_focused and cursor_visible and self.cursor_style != "vertical":
                char_at = lines[cursor_line][cursor_col] if cursor_col < len(lines[cursor_line]) else " "
                cur_style, cur_char = self._cursor_style_obj(char_at, cs)
                canvas.write(self.abs_x + cursor_col, self.abs_y + cursor_line, cur_char, cur_style)
        else:
            canvas.write(self.abs_x, self.abs_y, self.placeholder[:w].ljust(w),
                         self._placeholder_style(is_focused))

    def _draw_multiline(self, canvas, is_focused):
        w = self._clip_width or self.width
        cs = self._focused_style() if is_focused else self._normal_style()
        cursor_visible = (is_focused and self.cursor and self.cursor_style != "vertical"
                          and (canvas._cursor_on if self.flash else True))
        cur_line, cur_col = self._cursor_to_line_col()

        if not self.value:
            canvas.write(self.abs_x, self.abs_y, self.placeholder[:w].ljust(w),
                         self._placeholder_style(is_focused))
            return

        display_row = 0
        for li, logical_line in enumerate(self.value.split("\n")):
            # Each logical line may span multiple display rows if it overflows w
            chunks = [logical_line[i : i + w] for i in range(0, max(1, len(logical_line)), w)] or [""]
            for ci, chunk in enumerate(chunks):
                canvas.write(self.abs_x, self.abs_y + display_row, chunk.ljust(w), cs)

                if cursor_visible and li == cur_line:
                    chunk_start = ci * w
                    chunk_end   = chunk_start + w
                    if chunk_start <= cur_col < chunk_end:
                        cc = cur_col - chunk_start
                        char_at = chunk[cc] if cc < len(chunk) else " "
                        cur_style, cur_char = self._cursor_style_obj(char_at, cs)
                        canvas.write(self.abs_x + cc, self.abs_y + display_row, cur_char, cur_style)
                    elif cur_col == len(logical_line) and ci == len(chunks) - 1:
                        # Cursor at end of logical line
                        cc = cur_col - chunk_start
                        if 0 <= cc <= w:
                            cur_style, cur_char = self._cursor_style_obj(" ", cs)
                            canvas.write(self.abs_x + cc, self.abs_y + display_row, cur_char, cur_style)

                display_row += 1

    def get(self):
        return self.value
