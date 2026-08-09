"""Shared plumbing for the three simple, always-fully-materialized item
lists -- ListView, RadioSet, CheckList. All three page a plain `self._items`
list through `self._index`/`self._scroll_off` identically: Up/Down/Home/End
move the cursor (scrolling to keep it in view), and hover (when
`mouse_moves` is enabled) retargets it the same way a keypress would. Only
what happens *once the cursor lands somewhere* differs per widget -- select
vs toggle vs "current item" is just returned -- so that part (on_key's final
branch, on_mouse_click, _activate/_select_current/_toggle_current) stays
with each subclass.
"""

from cozy_tui.events import Key


class _IndexedListMixin:
    """Mixed into a ``Widget`` subclass that owns ``self._items``,
    ``self._index``, ``self._scroll_off``, and ``self.height`` (max visible
    rows, or falsy to show every item)."""

    # RadioSet overrides this to False: there, cursor movement and
    # "selection changed" are different events (Up/Down only relocates the
    # cursor; the value doesn't actually change until Enter/Space/click).
    # ListView/CheckList have no such split -- the highlighted item *is*
    # the current value, so every move is a change.
    _fire_change_on_move = True

    def _clamp_scroll(self) -> None:
        vis = self.height or len(self._items)
        if vis <= 0:
            return
        if self._index < self._scroll_off:
            self._scroll_off = self._index
        elif self._index >= self._scroll_off + vis:
            self._scroll_off = self._index - vis + 1

    def _move(self, new_index: int) -> None:
        if not self._items:
            return
        self._index = max(0, min(new_index, len(self._items) - 1))
        self._clamp_scroll()
        if self._fire_change_on_move:
            self._fire_change(self.selected)

    def natural_height(self, scale) -> int:
        return self.height or max(1, len(self._items))

    def _handle_nav_key(self, key) -> bool:
        """Handles Up/Down/Home/End, returning True if `key` was one of
        them. A subclass's own on_key checks this first, then handles
        whatever activates the current item (Enter, Space, ...) itself."""
        if key == Key.UP:
            self._move(self._index - 1)
        elif key == Key.DOWN:
            self._move(self._index + 1)
        elif key == Key.HOME:
            self._move(0)
        elif key == Key.END:
            self._move(len(self._items) - 1)
        else:
            return False
        return True

    def on_mouse_move(self, col=None, row=None) -> None:
        # Hover highlights the item under the cursor (like arrow-key
        # movement) without activating/selecting/toggling it -- only fires
        # when mouse_moves is enabled on this widget.
        if row is not None and self._items:
            idx = self._scroll_off + (row - self.abs_y)
            if 0 <= idx < len(self._items) and idx != self._index:
                self._move(idx)
        self._fire_hover(col, row)
