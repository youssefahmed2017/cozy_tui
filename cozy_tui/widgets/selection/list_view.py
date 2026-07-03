from typing import Any

from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widget import Widget


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


class ListView(Widget):
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
    ):
        super().__init__(x, y, style)
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
        try:
            idx = self._items.index(item)
            self._items.pop(idx)
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
        except ValueError:
            pass

    def set_item(self, index: int, item) -> None:
        """Replace the item at *index* in place, keeping selection and scroll."""
        if 0 <= index < len(self._items):
            self._items[index] = item
            self._label_width_cache = None  # display width may have changed

    def clear(self) -> None:
        self._items.clear()
        self._index = 0
        self._scroll_off = 0
        self._label_width_cache = 0

    # ── callbacks ────────────────────────────────────────────────────────────

    def on_select(self, func):
        """Called with the selected value when Enter is pressed or an item is clicked."""
        self._select_handler = func
        return self

    # ── internals ────────────────────────────────────────────────────────────

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
        self._fire_change(self.selected)

    def _activate(self, from_click: bool = False) -> None:
        if not self._items:
            return
        if from_click and self._click_handler:
            self._click_handler(self.selected)
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

    def natural_height(self, scale) -> int:
        return self.height or max(1, len(self._items))

    def contains(self, col: int, row: int) -> bool:
        w = self.natural_width(1)
        h = self.natural_height(1)
        return self.abs_x <= col < self.abs_x + w and self.abs_y <= row < self.abs_y + h

    def on_key(self, key) -> None:
        if key == Key.UP:
            self._move(self._index - 1)
        elif key == Key.DOWN:
            self._move(self._index + 1)
        elif key == Key.HOME:
            self._move(0)
        elif key == Key.END:
            self._move(len(self._items) - 1)
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

    def on_mouse_move(self, col=None, row=None) -> None:
        # Hover highlights the item under the cursor (like arrow-key movement),
        # without activating it. Requires App(mouse_moves=True).
        if row is not None and self._items:
            idx = self._scroll_off + (row - self.abs_y)
            if 0 <= idx < len(self._items) and idx != self._index:
                self._move(idx)
        self._fire_hover(col, row)

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
                style = Style(fg="black", bg="white", styles=["bold"])
            elif is_sel:
                style = Style(fg="white", styles=["bold"])
            else:
                style = self.style

            canvas.write(self.abs_x, vy, text, style)
