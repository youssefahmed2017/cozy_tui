from typing import Any

from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widget import Widget


class CheckItem:
    """A list entry with a checked state, display text, and optional return value."""

    def __init__(self, text: str, value=None, checked: bool = False):
        self.text = text
        self.value = value if value is not None else text
        self.checked = checked

    def __repr__(self):
        return f"CheckItem({self.text!r}, checked={self.checked})"


class CheckList(Widget):
    """A scrollable list where each item can be individually checked/unchecked.

    Navigation (Up/Down/Home/End) moves the cursor. Enter or Space toggles the
    checked state of the highlighted item. Mouse click moves the cursor and
    toggles in one step.
    """

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
        super().__init__(x, y, style, mouse_moves=True)  # hover-to-highlight
        self._items: list[CheckItem] = []
        self._index: int = 0
        self._scroll_off: int = 0
        self.width = width
        self.height = height
        self._toggle_handler = None
        self._label_width_cache: int | None = None

        if items:
            for item in items:
                self._coerce_append(item)

    # ── coercion ──────────────────────────────────────────────────────────────

    def _coerce(self, item) -> CheckItem:
        return item if isinstance(item, CheckItem) else CheckItem(str(item))

    def _coerce_append(self, item) -> None:
        ci = self._coerce(item)
        self._items.append(ci)
        w = len(ci.text)
        if self._label_width_cache is None or w > self._label_width_cache:
            self._label_width_cache = w

    # ── item list API ─────────────────────────────────────────────────────────

    @property
    def selected(self):
        """Value of the currently highlighted item."""
        return self._items[self._index].value if self._items else None

    @property
    def selected_index(self) -> int | None:
        return self._index if self._items else None

    @property
    def checked_values(self) -> list:
        """Values of all checked items."""
        return [item.value for item in self._items if item.checked]

    def get(self):
        return self.selected

    def append(self, item) -> None:
        self._coerce_append(item)

    def insert(self, index: int, item) -> None:
        ci = self._coerce(item)
        self._items.insert(index, ci)
        if index <= self._index:
            self._index = min(self._index + 1, len(self._items) - 1)
        w = len(ci.text)
        if self._label_width_cache is None or w > self._label_width_cache:
            self._label_width_cache = w

    def remove(self, item) -> None:
        try:
            idx = self._items.index(item)
            ci = self._items.pop(idx)
            self._index = min(self._index, max(0, len(self._items) - 1))
            if (
                self._label_width_cache is not None
                and len(ci.text) >= self._label_width_cache
            ):
                self._label_width_cache = None
        except ValueError:
            pass

    def clear(self) -> None:
        self._items.clear()
        self._index = 0
        self._scroll_off = 0
        self._label_width_cache = None

    def set_checked(self, value, checked: bool) -> None:
        """Set the checked state of the first item whose value equals *value*."""
        for item in self._items:
            if item.value == value:
                item.checked = checked
                return

    def check_all(self) -> None:
        for item in self._items:
            item.checked = True

    def uncheck_all(self) -> None:
        for item in self._items:
            item.checked = False

    def toggle_all(self) -> None:
        for item in self._items:
            item.checked = not item.checked

    @property
    def checked_items(self) -> list:
        """CheckItem objects whose checked state is True."""
        return [item for item in self._items if item.checked]

    # ── callbacks ─────────────────────────────────────────────────────────────

    def on_change(self, func):
        """Register a callback called with the selected value when the cursor moves."""
        self._change_handler = func
        return self

    def on_toggle(self, func):
        """Register a callback called with (value, checked) when an item is toggled."""
        self._toggle_handler = func
        return self

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
        self._fire_change(self.selected)

    def _toggle_current(self) -> None:
        if not self._items:
            return
        self._fire_click()  # on_click(widget): fires on Enter/Space or click
        item = self._items[self._index]
        item.checked = not item.checked
        if self._toggle_handler:
            self._toggle_handler(item.value, item.checked)

    # ── Widget interface ──────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        if self.width:
            return self.width
        if not self._items:
            return 8
        if self._label_width_cache is None:
            self._label_width_cache = max(len(item.text) for item in self._items)
        return self._label_width_cache + 6  # "> [✔] " = 6 chars

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
            self._toggle_current()

    def on_mouse_click(self, col=None, row=None) -> None:
        if row is not None and self._items:
            idx = self._scroll_off + (row - self.abs_y)
            if 0 <= idx < len(self._items):
                if self._index != idx:
                    self._index = idx
                    self._clamp_scroll()
                    self._fire_change(self.selected)
                self._toggle_current()

    def on_mouse_move(self, col=None, row=None) -> None:
        # Hover highlights the item under the cursor (like arrow-key movement),
        # without toggling it. (This widget opts into mouse_moves itself.)
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
        raw_bg = self.style.raw_bg

        for row in range(vis):
            idx = self._scroll_off + row
            vy = self.abs_y + row

            if idx >= n:
                canvas.write(self.abs_x, vy, " " * w, self.style)
                continue

            item = self._items[idx]
            is_sel = idx == self._index
            mark = "✔" if item.checked else " "
            prefix = "> " if is_sel else "  "
            text = f"{prefix}[{mark}] {item.text}".ljust(w)[:w]

            if is_focused and is_sel:
                style = Style(fg="black", bg="white", styles=["bold"])
            elif is_sel:
                style = Style(fg="white", styles=["bold"])
            elif item.checked:
                style = Style(fg=self.style.fg, bg=raw_bg, styles=["dim"])
            else:
                style = self.style

            canvas.write(self.abs_x, vy, text, style)
