import pyperclip as _pyperclip

from cozy_tui.widget import Widget
from cozy_tui.style import Style
from cozy_tui.events import Key

# ── Clipboard ─────────────────────────────────────────────────────────────────

def _clipboard_get() -> str:
    try:
        return _pyperclip.paste() or ""
    except Exception:
        return ""


def _clipboard_set(text: str) -> None:
    if not text:
        return
    try:
        _pyperclip.copy(text)
    except Exception:
        pass


# ── Input widget ──────────────────────────────────────────────────────────────

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
        masked=False,
        masked_symbol="*",
    ):
        super().__init__(x, y, style)
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
        self._sel_anchor: int | None = None  # None = no selection
        self._undo_stack: list = []
        self._redo_stack: list = []
        self._last_action: str | None = None

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

    # ── undo / redo history ──────────────────────────────────────────────────

    _COALESCE = {"type", "backspace", "delete"}
    _MAX_HISTORY = 200

    def _save_history(self, action: str) -> None:
        """Push (value, cursor_pos) onto the undo stack before an edit.
        Consecutive actions of the same coalescing type share one undo point."""
        if action in self._COALESCE and action == self._last_action:
            return
        self._undo_stack.append((self.value, self.cursor_pos))
        if len(self._undo_stack) > self._MAX_HISTORY:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._last_action = action

    def _do_undo(self) -> None:
        if not self._undo_stack:
            return
        self._redo_stack.append((self.value, self.cursor_pos))
        self.value, self.cursor_pos = self._undo_stack.pop()
        self._sel_anchor = None
        self._last_action = None

    def _do_redo(self) -> None:
        if not self._redo_stack:
            return
        self._undo_stack.append((self.value, self.cursor_pos))
        self.value, self.cursor_pos = self._redo_stack.pop()
        self._sel_anchor = None
        self._last_action = None

    # ── word-boundary helpers ────────────────────────────────────────────────

    def _word_right(self, pos: int) -> int:
        """Return the position after jumping one word to the right (VS Code style)."""
        v = self.value
        n = len(v)
        # Skip punctuation/whitespace, then skip the word body
        while pos < n and not (v[pos].isalnum() or v[pos] == "_"):
            pos += 1
        while pos < n and (v[pos].isalnum() or v[pos] == "_"):
            pos += 1
        return pos

    def _word_left(self, pos: int) -> int:
        """Return the position after jumping one word to the left (VS Code style)."""
        v = self.value
        pos -= 1
        # Skip punctuation/whitespace backwards
        while pos > 0 and not (v[pos].isalnum() or v[pos] == "_"):
            pos -= 1
        # Skip word body backwards
        while pos > 0 and (v[pos - 1].isalnum() or v[pos - 1] == "_"):
            pos -= 1
        return max(0, pos)

    # ── position helpers (multi-line) ────────────────────────────────────────

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
        raw_bg = self.style.bg.replace("_bg", "") if self.style.bg else None
        return Style(fg=self.style.fg, bg=raw_bg, styles=["dim"])

    def _cursor_style_obj(self, char_at_cursor, content_style: Style):
        fg = content_style.fg
        bg = content_style.bg
        raw_bg = bg.replace("_bg", "") if bg else None

        if self.cursor_style == "block":
            return Style(fg=raw_bg or "black", bg=fg or "white"), char_at_cursor
        else:  # vertical / underline — underline so it's always visible
            return Style(fg=fg, bg=raw_bg, styles=["underline"]), char_at_cursor

    # ── mouse click ──────────────────────────────────────────────────────────

    def on_mouse_click(self, col=None, row=None):
        self._clear_sel()
        if col is not None and row is not None:
            self._set_cursor_from_mouse(col, row)
        self._fire_click()

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
                chunks_count = max(1, (len(logical_line) + w - 1) // w) if logical_line else 1
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

    # ── key handling ─────────────────────────────────────────────────────────

    # Keys that should break typing coalescing even if cursor doesn't move.
    _NAV_KEYS = {
        Key.LEFT, Key.RIGHT, Key.UP, Key.DOWN,
        Key.HOME, Key.END,
        Key.SHIFT_LEFT, Key.SHIFT_RIGHT, Key.SHIFT_UP, Key.SHIFT_DOWN,
        Key.SHIFT_HOME, Key.SHIFT_END,
        Key.CTRL_LEFT, Key.CTRL_RIGHT,
        Key.CTRL_SHIFT_LEFT, Key.CTRL_SHIFT_RIGHT,
        Key.CTRL_A,
    }

    def on_key(self, key):
        _prev_value = self.value

        if key == Key.LEFT:
            r = self._sel_range()
            if r is not None:
                self.cursor_pos = r[0]
                self._clear_sel()
            else:
                self.cursor_pos = max(0, self.cursor_pos - 1)

        elif key == Key.RIGHT:
            r = self._sel_range()
            if r is not None:
                self.cursor_pos = r[1]
                self._clear_sel()
            else:
                self.cursor_pos = min(len(self.value), self.cursor_pos + 1)

        elif key == Key.HOME:
            self._clear_sel()
            if self.multiline:
                line, _ = self._cursor_to_line_col()
                self.cursor_pos = self._line_col_to_pos(line, 0)
            else:
                self.cursor_pos = 0

        elif key == Key.END:
            self._clear_sel()
            if self.multiline:
                line, _ = self._cursor_to_line_col()
                lines = self.value.split("\n")
                self.cursor_pos = self._line_col_to_pos(line, len(lines[line]))
            else:
                self.cursor_pos = len(self.value)

        elif key == Key.UP and self.multiline:
            self._clear_sel()
            line, col = self._cursor_to_line_col()
            if line > 0:
                lines = self.value.split("\n")
                self.cursor_pos = self._line_col_to_pos(
                    line - 1, min(col, len(lines[line - 1]))
                )

        elif key == Key.DOWN and self.multiline:
            self._clear_sel()
            line, col = self._cursor_to_line_col()
            lines = self.value.split("\n")
            if line < len(lines) - 1:
                self.cursor_pos = self._line_col_to_pos(
                    line + 1, min(col, len(lines[line + 1]))
                )

        # ── Shift navigation ─────────────────────────────────────────────────

        elif key == Key.SHIFT_LEFT:
            self._shift_move(self.cursor_pos - 1)

        elif key == Key.SHIFT_RIGHT:
            self._shift_move(self.cursor_pos + 1)

        elif key == Key.SHIFT_HOME:
            if self.multiline:
                line, _ = self._cursor_to_line_col()
                self._shift_move(self._line_col_to_pos(line, 0))
            else:
                self._shift_move(0)

        elif key == Key.SHIFT_END:
            if self.multiline:
                line, _ = self._cursor_to_line_col()
                lines = self.value.split("\n")
                self._shift_move(self._line_col_to_pos(line, len(lines[line])))
            else:
                self._shift_move(len(self.value))

        elif key == Key.SHIFT_UP and self.multiline:
            line, col = self._cursor_to_line_col()
            if line > 0:
                lines = self.value.split("\n")
                self._shift_move(self._line_col_to_pos(line - 1, min(col, len(lines[line - 1]))))

        elif key == Key.SHIFT_DOWN and self.multiline:
            line, col = self._cursor_to_line_col()
            lines = self.value.split("\n")
            if line < len(lines) - 1:
                self._shift_move(self._line_col_to_pos(line + 1, min(col, len(lines[line + 1]))))

        # ── word navigation ──────────────────────────────────────────────────

        elif key == Key.CTRL_RIGHT:
            self._clear_sel()
            self.cursor_pos = self._word_right(self.cursor_pos)

        elif key == Key.CTRL_LEFT:
            self._clear_sel()
            self.cursor_pos = self._word_left(self.cursor_pos)

        elif key == Key.CTRL_SHIFT_RIGHT:
            self._shift_move(self._word_right(self.cursor_pos))

        elif key == Key.CTRL_SHIFT_LEFT:
            self._shift_move(self._word_left(self.cursor_pos))

        # ── edit operations ──────────────────────────────────────────────────

        elif key == Key.BACKSPACE:
            if self._sel_anchor is not None:
                self._save_history("edit")
                self._delete_sel()
            elif self.cursor_pos > 0:
                self._save_history("backspace")
                self.value = self.value[: self.cursor_pos - 1] + self.value[self.cursor_pos :]
                self.cursor_pos -= 1

        elif key == Key.DELETE:
            if self._sel_anchor is not None:
                self._save_history("edit")
                self._delete_sel()
            elif self.cursor_pos < len(self.value):
                self._save_history("delete")
                self.value = self.value[: self.cursor_pos] + self.value[self.cursor_pos + 1 :]

        elif key in (Key.ENTER, Key.SHIFT_ENTER) and self.multiline:
            self._save_history("edit")
            if self._sel_anchor is not None:
                self._delete_sel()
            self.value = self.value[: self.cursor_pos] + "\n" + self.value[self.cursor_pos :]
            self.cursor_pos += 1

        # ── clipboard / select-all ────────────────────────────────────────────

        elif key == Key.CTRL_A:
            if self.value:
                self._sel_anchor = 0
                self.cursor_pos = len(self.value)

        elif key == Key.CTRL_C:
            text = self._sel_text()
            if text:
                _clipboard_set(text)

        elif key == Key.CTRL_X:
            text = self._sel_text()
            if text:
                self._save_history("edit")
                _clipboard_set(text)
                self._delete_sel()

        elif key == Key.CTRL_V:
            pasted = _clipboard_get()
            if pasted:
                self._save_history("edit")
                if self._sel_anchor is not None:
                    self._delete_sel()
                if not self.multiline:
                    pasted = pasted.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
                else:
                    pasted = pasted.replace("\r\n", "\n").replace("\r", "\n")
                self.value = self.value[: self.cursor_pos] + pasted + self.value[self.cursor_pos :]
                self.cursor_pos += len(pasted)

        # ── undo / redo ───────────────────────────────────────────────────────

        elif key == Key.CTRL_Z:
            self._do_undo()

        elif key in (Key.CTRL_SHIFT_Z, Key.CTRL_Y):
            self._do_redo()

        elif (
            key not in (Key.ESC, Key.ENTER, Key.TAB, Key.UP, Key.DOWN)
            and len(key) == 1
            and key.isprintable()
        ):
            self._save_history("type")
            if self._sel_anchor is not None:
                self._delete_sel()
            self.value = self.value[: self.cursor_pos] + key + self.value[self.cursor_pos :]
            self.cursor_pos += 1

        # Navigation (or select-all) breaks type coalescing so the next
        # edit starts a fresh undo point.
        if key in self._NAV_KEYS and self.value is _prev_value:
            self._last_action = None

    @property
    def _display_value(self):
        if not self.masked:
            return self.value
        return "".join(self.masked_symbol if c != "\n" else "\n" for c in self.value)

    # ── drawing ──────────────────────────────────────────────────────────────

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

            self._write_span(canvas, self.abs_x, self.abs_y, visible, self._scroll_off, cs, sel, sel_s)
            fill = w - len(visible)
            if fill > 0:
                canvas.write(self.abs_x + len(visible), self.abs_y, " " * fill, cs)

            cursor_visible = canvas._cursor_on if self.cursor else False
            if (
                self.cursor
                and is_focused
                and cursor_visible
                and self.cursor_style != "vertical"
                and 0 <= cursor_col < w
            ):
                char_at = visible[cursor_col] if cursor_col < len(visible) else " "
                cur_style, cur_char = self._cursor_style_obj(char_at, cs)
                canvas.write(self.abs_x + cursor_col, self.abs_y, cur_char, cur_style)
        else:
            canvas.write(
                self.abs_x,
                self.abs_y,
                self.placeholder[:w].ljust(w),
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
                self._write_span(canvas, self.abs_x, self.abs_y + i, line, i * w, cs, sel, sel_s)
                fill = w - len(line)
                if fill > 0:
                    canvas.write(self.abs_x + len(line), self.abs_y + i, " " * fill, cs)

            cursor_visible = canvas._cursor_on if self.flash else True
            if (
                self.cursor
                and is_focused
                and cursor_visible
                and self.cursor_style != "vertical"
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
                self.placeholder[:w].ljust(w),
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
            and self.cursor_style != "vertical"
            and (canvas._cursor_on if self.flash else True)
        )
        cur_line, cur_col = self._cursor_to_line_col()

        if not self.value:
            canvas.write(
                self.abs_x,
                self.abs_y,
                self.placeholder[:w].ljust(w),
                self._placeholder_style(is_focused),
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

                self._write_span(canvas, self.abs_x, vy, chunk, chunk_flat_start, cs, sel, sel_s)
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

    def get(self):
        return self.value
