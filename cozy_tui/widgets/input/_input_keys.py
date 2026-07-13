from cozy_tui.events import Key, Paste
from cozy_tui.widgets.input._input_clipboard import _clipboard_get, _clipboard_set


class _KeysMixin:

    # Keys that should break typing coalescing even if cursor doesn't move.
    _NAV_KEYS = {
        Key.LEFT,
        Key.RIGHT,
        Key.UP,
        Key.DOWN,
        Key.HOME,
        Key.END,
        Key.SHIFT_LEFT,
        Key.SHIFT_RIGHT,
        Key.SHIFT_UP,
        Key.SHIFT_DOWN,
        Key.SHIFT_HOME,
        Key.SHIFT_END,
        Key.CTRL_LEFT,
        Key.CTRL_RIGHT,
        Key.CTRL_SHIFT_LEFT,
        Key.CTRL_SHIFT_RIGHT,
        Key.CTRL_A,
    }

    def _filter_type_text(self, text: str) -> str:
        """Restrict `text` (about to be inserted at `cursor_pos`) to what the
        current `type` allows -- e.g. `type="number"` drops anything but
        digits, at most one leading "-", and at most one ".". A no-op for
        `type="text"` (the default)."""
        if self.type != "number":
            return text
        has_dot = "." in self.value
        has_minus = "-" in self.value
        out = []
        for i, ch in enumerate(text):
            if ch.isdigit():
                out.append(ch)
            elif ch == "-" and not has_minus and self.cursor_pos == 0 and i == 0:
                out.append(ch)
                has_minus = True
            elif ch == "." and not has_dot:
                out.append(ch)
                has_dot = True
        return "".join(out)

    def _do_paste(self, text: str) -> None:
        if self.mask is not None:
            self._mask_paste(text)
            self._touched = True
            return
        self._save_history("edit")
        if self._sel_anchor is not None:
            self._delete_sel()
        if not self.multiline:
            text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
        else:
            text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = self._filter_type_text(text)
        self.value = (
            self.value[: self.cursor_pos] + text + self.value[self.cursor_pos :]
        )
        self.cursor_pos += len(text)
        self._sel_anchor = None
        self._touched = True

    def on_key(self, key):
        _prev_value = self.value

        if isinstance(key, Paste):
            self._do_paste(key.text)
            return

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
                self._shift_move(
                    self._line_col_to_pos(line - 1, min(col, len(lines[line - 1])))
                )

        elif key == Key.SHIFT_DOWN and self.multiline:
            line, col = self._cursor_to_line_col()
            lines = self.value.split("\n")
            if line < len(lines) - 1:
                self._shift_move(
                    self._line_col_to_pos(line + 1, min(col, len(lines[line + 1])))
                )

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
            if self.mask is not None:
                self._mask_backspace()
            elif self._sel_anchor is not None:
                self._save_history("edit")
                self._delete_sel()
            elif self.cursor_pos > 0:
                self._save_history("backspace")
                self.value = (
                    self.value[: self.cursor_pos - 1] + self.value[self.cursor_pos :]
                )
                self.cursor_pos -= 1

        elif key == Key.DELETE:
            if self.mask is not None:
                self._mask_delete()
            elif self._sel_anchor is not None:
                self._save_history("edit")
                self._delete_sel()
            elif self.cursor_pos < len(self.value):
                self._save_history("delete")
                self.value = (
                    self.value[: self.cursor_pos] + self.value[self.cursor_pos + 1 :]
                )

        elif key in (Key.ENTER, Key.SHIFT_ENTER) and self.multiline:
            self._save_history("edit")
            if self._sel_anchor is not None:
                self._delete_sel()
            self.value = (
                self.value[: self.cursor_pos] + "\n" + self.value[self.cursor_pos :]
            )
            self.cursor_pos += 1

        # ── clipboard / select-all ────────────────────────────────────────────

        elif key == Key.CTRL_A:
            if self.value:
                self._sel_anchor = 0
                self.cursor_pos = len(self.value)

        elif key == Key.CTRL_C:
            if self.masked and not self._reveal_masked:
                return  # never leak the real value while it's still hidden
            text = self._sel_text()
            if text:
                _clipboard_set(text)

        elif key == Key.CTRL_X:
            if self.masked and not self._reveal_masked:
                return  # cutting both removes and copies -- same guard as Ctrl+C
            text = self._sel_text()
            if text:
                self._save_history("edit")
                _clipboard_set(text)
                self._delete_sel()

        elif key == Key.CTRL_V:
            pasted = _clipboard_get()
            if pasted:
                self._do_paste(pasted)

        # ── insert / overwrite mode ───────────────────────────────────────────

        elif key == Key.INSERT:
            self._overwrite = not self._overwrite
            self.cursor_style = "block" if self._overwrite else "vertical"

        # ── reveal masked value ────────────────────────────────────────────────

        elif key == Key.CTRL_R and self.masked:
            self._reveal_masked = not self._reveal_masked

        # ── undo / redo ───────────────────────────────────────────────────────

        elif key == Key.CTRL_U:
            self._do_undo()

        elif key == Key.CTRL_Y:
            self._do_redo()

        elif (
            key not in (Key.ESC, Key.ENTER, Key.TAB, Key.UP, Key.DOWN)
            and len(key) == 1
            and key.isprintable()
        ):
            if self.mask is not None:
                self._mask_insert_digit(key)
                self._touched = True
                return
            filtered = self._filter_type_text(key)
            if not filtered:
                return  # disallowed by `type` (e.g. a letter in a "number" field)
            self._save_history("type")
            if self._sel_anchor is not None:
                self._delete_sel()
            elif self._overwrite and self.cursor_pos < len(self.value):
                self.value = (
                    self.value[: self.cursor_pos]
                    + filtered
                    + self.value[self.cursor_pos + 1 :]
                )
                self.cursor_pos += len(filtered)
                self._touched = True
                return
            self.value = (
                self.value[: self.cursor_pos] + filtered + self.value[self.cursor_pos :]
            )
            self.cursor_pos += len(filtered)

        # Strings are immutable, so any real edit produced a new object --
        # this is what "touched" (see Input.error) means: the value actually
        # changed at least once, not just that a key was pressed.
        if self.value is not _prev_value:
            self._touched = True

        # Navigation breaks type coalescing so the next edit starts a fresh undo point.
        if key in self._NAV_KEYS and self.value is _prev_value:
            self._last_action = None
