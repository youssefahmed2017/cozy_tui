from typing import Any

from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widget import Widget


class RadioItem:
    """A radio entry with display text and an optional return value."""

    def __init__(self, text: str, value=None):
        self.text = text
        self.value = value if value is not None else text

    def __repr__(self):
        return f"RadioItem({self.text!r})"


class RadioSet(Widget):
    """A single-select list of options — exactly one is chosen at a time.

    Navigation (Up/Down/Home/End) moves the cursor; Enter or Space selects the
    highlighted option. Mouse click moves the cursor and selects in one step.
    The chosen option is marked ``(•)``; the cursor is marked with a ``>``.

    ``on_change`` fires with the newly selected value whenever the selection
    changes (not on mere cursor movement).
    """

    focusable = True

    def __init__(
        self,
        x,
        y,
        items: list[Any] | None = None,
        *,
        selected: int = 0,
        width=None,
        height=None,
        style=None,
    ):
        super().__init__(x, y, style, mouse_moves=True)  # hover-to-highlight
        self._items: list[RadioItem] = []
        self._index: int = 0  # cursor position
        self._selected: int | None = None  # chosen option, or None
        self._scroll_off: int = 0
        self.width = width
        self.height = height
        self._label_width_cache: int | None = None

        if items:
            for item in items:
                self._coerce_append(item)
        if self._items:
            self._selected = max(0, min(selected, len(self._items) - 1))
            self._index = self._selected

    # ── coercion ──────────────────────────────────────────────────────────────

    def _coerce(self, item) -> RadioItem:
        return item if isinstance(item, RadioItem) else RadioItem(str(item))

    def _coerce_append(self, item) -> None:
        ri = self._coerce(item)
        self._items.append(ri)
        w = len(ri.text)
        if self._label_width_cache is None or w > self._label_width_cache:
            self._label_width_cache = w

    # ── selection API ───────────────────────────────────────────────────────────

    @property
    def selected(self):
        """Value of the currently selected option (or None if there are none)."""
        if self._selected is None:
            return None
        return self._items[self._selected].value

    @property
    def selected_index(self) -> int | None:
        return self._selected

    @property
    def selected_item(self) -> RadioItem | None:
        if self._selected is None:
            return None
        return self._items[self._selected]

    def get(self):
        return self.selected

    def select(self, value) -> None:
        """Select the first option whose value equals *value*."""
        for i, item in enumerate(self._items):
            if item.value == value:
                self.select_index(i)
                return

    def select_index(self, index: int) -> None:
        if not (0 <= index < len(self._items)):
            return
        self._index = index
        self._clamp_scroll()
        if index != self._selected:
            self._selected = index
            self._fire_change(self.selected)

    # ── item list API ─────────────────────────────────────────────────────────

    def append(self, item) -> None:
        self._coerce_append(item)
        if self._selected is None:  # first option added becomes selected
            self._selected = 0
            self._index = 0

    def clear(self) -> None:
        self._items.clear()
        self._index = 0
        self._selected = None
        self._scroll_off = 0
        self._label_width_cache = None

    # ── internals ─────────────────────────────────────────────────────────────

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

    def _select_current(self) -> None:
        if not self._items:
            return
        if self._index != self._selected:
            self._selected = self._index
            self._fire_change(self.selected)

    # ── Widget interface ──────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        if self.width:
            return self.width
        if not self._items:
            return 8
        if self._label_width_cache is None:
            self._label_width_cache = max(len(item.text) for item in self._items)
        return self._label_width_cache + 6  # "> (•) " = 6 chars

    def natural_height(self, scale) -> int:
        return self.height or max(1, len(self._items))

    def on_key(self, key) -> None:
        if key == Key.UP:
            self._move(self._index - 1)
        elif key == Key.DOWN:
            self._move(self._index + 1)
        elif key == Key.HOME:
            self._move(0)
        elif key == Key.END:
            self._move(len(self._items) - 1)
        elif key in (Key.ENTER, " "):
            self._select_current()

    def on_mouse_click(self, col=None, row=None) -> None:
        if row is not None and self._items:
            idx = self._scroll_off + (row - self.abs_y)
            if 0 <= idx < len(self._items):
                self._index = idx
                self._clamp_scroll()
                self._select_current()

    def on_mouse_move(self, col=None, row=None) -> None:
        # Hover highlights the option under the cursor (like arrow-key movement),
        # without selecting it. (This widget opts into mouse_moves itself.)
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

            item = self._items[idx]
            is_cursor = idx == self._index
            mark = "•" if idx == self._selected else " "
            prefix = "> " if is_cursor else "  "
            text = f"{prefix}({mark}) {item.text}".ljust(w)[:w]

            if is_focused and is_cursor:
                style = Style(fg="black", bg="white", styles=["bold"])
            elif is_cursor:
                style = Style(fg="white", styles=["bold"])
            else:
                style = self.style

            canvas.write(self.abs_x, vy, text, style)
