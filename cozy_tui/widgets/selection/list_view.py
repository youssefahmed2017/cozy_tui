from typing import Any

from cozy_tui.events import Key
from cozy_tui.style import selection_style
from cozy_tui.widget import Widget

from ._indexed_list import _IndexedListMixin


class ListItem:
    """A list entry with separate display text and return value."""

    def __init__(self, text: str, value=None):
        self.text = text
        self.value = value if value is not None else text

    def __repr__(self):
        return f"ListItem({self.text!r}, {self.value!r})"


def _display(item) -> str:
    return item.text if isinstance(item, ListItem) else str(item)


def _value(item):
    return item.value if isinstance(item, ListItem) else item


class ListView(_IndexedListMixin, Widget):
    focusable = True

    def __init__(
        self,
        x,
        y,
        items: list[Any] | None = None,
        *,
        width=None,
        height=None,
        style=None,
        mouse_moves: bool = False,
    ):
        super().__init__(
            x, y, style, mouse_moves=mouse_moves
        )  # hover-to-highlight opt-in
        self._items: list = list(items) if items is not None else []
        self._index: int = 0
        self._scroll_off: int = 0
        self.width = width  # None = auto-sized from items
        self.height = height  # None = show all items
        self._select_handler = None
        self._change_handler = None
        self._click_handler = None
        self._label_width_cache: int | None = None  # max _display() len across items

    # ── item list API ────────────────────────────────────────────────────────

    @property
    def selected(self):
        """Return the value of the selected item (ListItem.value or the item itself)."""
        return _value(self._items[self._index]) if self._items else None

    @property
    def selected_index(self) -> int | None:
        return self._index if self._items else None

    @selected_index.setter
    def selected_index(self, index: int) -> None:
        """Move the highlight to `index` (clamped). The public way to restore a
        position after rebuilding the list -- e.g. deleting a row and keeping
        the cursor where it was."""
        if not self._items:
            return
        self._index = max(0, min(int(index), len(self._items) - 1))
        self._clamp_scroll()

    def __len__(self) -> int:
        return len(self._items)

    def get(self):
        return self.selected

    def set(self, value) -> None:
        """Select the first item whose value equals *value*."""
        for i, item in enumerate(self._items):
            if _value(item) == value:
                self._index = i
                self._clamp_scroll()
                return

    def append(self, item: ListItem) -> None:
        self._items.append(item)
        dw = len(_display(item))
        if self._label_width_cache is None or dw > self._label_width_cache:
            self._label_width_cache = dw

    def insert(self, index: int, item) -> None:
        self._items.insert(index, item)
        if index <= self._index:
            self._index = min(self._index + 1, len(self._items) - 1)
        dw = len(_display(item))
        if self._label_width_cache is None or dw > self._label_width_cache:
            self._label_width_cache = dw

    def remove(self, item) -> None:
        """Remove the first item whose value equals *item*. For a list that may
        hold two equal-valued items (e.g. duplicate card names), removing the
        one currently at `selected_index` needs `remove_at` instead -- this
        method has no way to tell them apart."""
        try:
            idx = self._items.index(item)
        except ValueError:
            return
        self.remove_at(idx)

    def remove_at(self, index: int) -> None:
        """Remove the item at *index*, unambiguous even when two items share
        an equal value (unlike `remove`, which matches by value)."""
        if not (0 <= index < len(self._items)):
            return
        item = self._items.pop(index)
        if self._items:
            self._index = min(self._index, len(self._items) - 1)
        else:
            self._index = 0
        # If the removed item was the widest, the cache is stale.
        if (
            self._label_width_cache is not None
            and len(_display(item)) >= self._label_width_cache
        ):
            self._label_width_cache = None

    def set_item(self, index: int, item) -> None:
        """Replace the item at *index* in place, keeping selection and scroll."""
        if 0 <= index < len(self._items):
            self._items[index] = item
            self._label_width_cache = None  # display width may have changed

    def clear(self) -> "ListView":
        self._items.clear()
        self._index = 0
        self._scroll_off = 0
        self._label_width_cache = None
        return self

    # ── callbacks ────────────────────────────────────────────────────────────

    def on_select(self, func):
        """Called with the selected value when Enter is pressed or an item is clicked."""
        self._select_handler = func
        return self

    # ── internals ────────────────────────────────────────────────────────────

    def _activate(self, from_click: bool = False) -> None:
        if not self._items:
            return
        self._fire_click()  # on_click(widget): fires on Enter or click
        if self._select_handler:
            self._select_handler(self.selected)

    # ── Widget interface ─────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        if self.width:
            return self.width
        if not self._items:
            return 4
        if self._label_width_cache is None:
            self._label_width_cache = max(len(_display(item)) for item in self._items)
        return self._label_width_cache + 2  # room for "> "

    def on_key(self, key) -> None:
        if self._handle_nav_key(key):
            return
        elif key == Key.ENTER:
            self._activate(from_click=False)

    def on_mouse_click(self, col=None, row=None) -> None:
        if row is not None and self._items:
            idx = self._scroll_off + (row - self.abs_y)
            if 0 <= idx < len(self._items):
                old = self._index
                self._index = idx
                self._clamp_scroll()
                if idx != old:
                    self._fire_change(self.selected)
        self._activate(from_click=True)

    def draw(self, canvas) -> None:
        is_focused = canvas.focused is self
        w = self.natural_width(1)
        n = len(self._items)
        vis = self.height or n

        for row in range(vis):
            idx = self._scroll_off + row
            vy = self.abs_y + row

            if idx >= n:
                canvas.write(self.abs_x, vy, " " * w, self.style)
                continue

            is_sel = idx == self._index
            prefix = "> " if is_sel else "  "
            text = (prefix + _display(self._items[idx])).ljust(w)[:w]

            if is_focused and is_sel:
                style = selection_style()
            elif is_sel:
                style = selection_style(dim=True)
            else:
                style = self.style

            canvas.write(self.abs_x, vy, text, style)
