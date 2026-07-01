from cozy_tui.style import Style


class _DrawMixin:

    @property
    def _display_value(self):
        if not self.masked:
            return self.value
        # Re-build only when value is a different object (strings are immutable,
        # so any mutation produces a new string and breaks identity).
        if self.value is self._masked_cache_key:
            return self._masked_cache_val
        result = "".join(self.masked_symbol if c != "\n" else "\n" for c in self.value)
        self._masked_cache_key = self.value
        self._masked_cache_val = result
        return result

    def _write_span(
        self,
        canvas,
        x: int,
        y: int,
        text: str,
        start: int,
        style: Style,
        sel,
        sel_style: Style,
    ) -> None:
        """Write text at (x, y), highlighting characters within the sel range."""
        if not text:
            return
        if sel is None:
            canvas.write(x, y, text, style)
            return
        sel_a, sel_b = sel
        col = x
        i = 0
        n = len(text)
        while i < n:
            in_sel = sel_a <= (start + i) < sel_b
            cur_style = sel_style if in_sel else style
            j = i + 1
            while j < n and (sel_a <= (start + j) < sel_b) == in_sel:
                j += 1
            canvas.write(col, y, text[i:j], cur_style)
            col += j - i
            i = j

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
        sel = self._sel_range() if is_focused else None
        sel_s = self._sel_style()

        if self.value:
            if self.cursor_pos < self._scroll_off:
                self._scroll_off = self.cursor_pos
            elif self.cursor_pos >= self._scroll_off + w:
                self._scroll_off = self.cursor_pos - w + 1
            visible = self._display_value[self._scroll_off : self._scroll_off + w]
            cursor_col = self.cursor_pos - self._scroll_off

            self._write_span(
                canvas,
                self.abs_x,
                self.abs_y,
                visible,
                self._scroll_off,
                cs,
                sel,
                sel_s,
            )
            fill = w - len(visible)
            if fill > 0:
                canvas.write(self.abs_x + len(visible), self.abs_y, " " * fill, cs)

            cursor_visible = canvas._cursor_on if self.cursor else False
            if (
                self.cursor
                and is_focused
                and cursor_visible
                and self.cursor_style not in ("vertical", "block")
                and 0 <= cursor_col < w
            ):
                char_at = visible[cursor_col] if cursor_col < len(visible) else " "
                cur_style, cur_char = self._cursor_style_obj(char_at, cs)
                canvas.write(self.abs_x + cursor_col, self.abs_y, cur_char, cur_style)
        else:
            canvas.write(
                self.abs_x,
                self.abs_y,
                self.placeholder.replace("\n", " ")[:w].ljust(w),
                self._placeholder_style(is_focused),
            )

    def _draw_wrapped(self, canvas, is_focused):
        w = self._clip_width
        cs = self._focused_style() if is_focused else self._normal_style()
        sel = self._sel_range() if is_focused else None
        sel_s = self._sel_style()

        if self.value:
            lines = [
                self._display_value[i : i + w] for i in range(0, len(self.value), w)
            ]
            cursor_line = self.cursor_pos // w
            cursor_col = self.cursor_pos % w
            while len(lines) <= cursor_line:
                lines.append("")

            for i, line in enumerate(lines):
                self._write_span(
                    canvas, self.abs_x, self.abs_y + i, line, i * w, cs, sel, sel_s
                )
                fill = w - len(line)
                if fill > 0:
                    canvas.write(self.abs_x + len(line), self.abs_y + i, " " * fill, cs)

            cursor_visible = canvas._cursor_on if self.flash else True
            if (
                self.cursor
                and is_focused
                and cursor_visible
                and self.cursor_style not in ("vertical", "block")
            ):
                char_at = (
                    lines[cursor_line][cursor_col]
                    if cursor_col < len(lines[cursor_line])
                    else " "
                )
                cur_style, cur_char = self._cursor_style_obj(char_at, cs)
                canvas.write(
                    self.abs_x + cursor_col,
                    self.abs_y + cursor_line,
                    cur_char,
                    cur_style,
                )
        else:
            canvas.write(
                self.abs_x,
                self.abs_y,
                self.placeholder.replace("\n", " ")[:w].ljust(w),
                self._placeholder_style(is_focused),
            )

    def _draw_multiline(self, canvas, is_focused):
        w = self._clip_width or self.width
        cs = self._focused_style() if is_focused else self._normal_style()
        sel = self._sel_range() if is_focused else None
        sel_s = self._sel_style()
        cursor_visible = (
            is_focused
            and self.cursor
            and self.cursor_style not in ("vertical", "block")
            and (canvas._cursor_on if self.flash else True)
        )
        cur_line, cur_col = self._cursor_to_line_col()

        if not self.value:
            ph_style = self._placeholder_style(is_focused)
            for row_i, ph_line in enumerate(self.placeholder.split("\n")):
                canvas.write(
                    self.abs_x,
                    self.abs_y + row_i,
                    ph_line[:w].ljust(w),
                    ph_style,
                )
            return

        display_row = 0
        flat_pos = 0  # flat index into value at start of the current logical line
        value_lines = self.value.split("\n")

        for li, logical_line in enumerate(self._display_value.split("\n")):
            vline_len = len(value_lines[li]) if li < len(value_lines) else 0
            chunks = [
                logical_line[i : i + w] for i in range(0, max(1, len(logical_line)), w)
            ] or [""]

            for ci, chunk in enumerate(chunks):
                vy = self.abs_y + display_row
                chunk_flat_start = flat_pos + ci * w

                self._write_span(
                    canvas, self.abs_x, vy, chunk, chunk_flat_start, cs, sel, sel_s
                )
                fill = w - len(chunk)
                if fill > 0:
                    canvas.write(self.abs_x + len(chunk), vy, " " * fill, cs)

                if cursor_visible and li == cur_line:
                    chunk_start = ci * w
                    chunk_end = chunk_start + w
                    if chunk_start <= cur_col < chunk_end:
                        cc = cur_col - chunk_start
                        char_at = chunk[cc] if cc < len(chunk) else " "
                        cur_style, cur_char = self._cursor_style_obj(char_at, cs)
                        canvas.write(self.abs_x + cc, vy, cur_char, cur_style)
                    elif cur_col == len(logical_line) and ci == len(chunks) - 1:
                        cc = cur_col - chunk_start
                        if 0 <= cc <= w:
                            cur_style, cur_char = self._cursor_style_obj(" ", cs)
                            canvas.write(self.abs_x + cc, vy, cur_char, cur_style)

                display_row += 1

            flat_pos += vline_len + 1  # +1 for the \n between logical lines
