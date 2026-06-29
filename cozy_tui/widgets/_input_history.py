class _HistoryMixin:
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
