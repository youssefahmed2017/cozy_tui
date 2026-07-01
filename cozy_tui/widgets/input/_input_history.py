class _HistoryMixin:
    _COALESCE = {"type", "backspace", "delete"}
    _MAX_HISTORY = 200

    def _save_history(self, action: str) -> None:
        """Push (value, cursor_pos) onto the undo stack before an edit.
        Consecutive actions of the same coalescing type share one undo point."""
        if action in self._COALESCE and action == self._last_action:
            return
        self._undo_stack.append((self.value, self.cursor_pos))
        self._redo_stack.clear()
        self._last_action = action

    def _step(self, src, dst) -> None:
        if not src:
            return
        dst.append((self.value, self.cursor_pos))
        self.value, self.cursor_pos = src.pop()
        self._sel_anchor = self._last_action = None

    def _do_undo(self) -> None:
        self._step(self._undo_stack, self._redo_stack)

    def _do_redo(self) -> None:
        self._step(self._redo_stack, self._undo_stack)
