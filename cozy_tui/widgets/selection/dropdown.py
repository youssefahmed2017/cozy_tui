from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widget import Widget
from cozy_tui.widgets.selection.list_view import ListView, _display, _value


class Dropdown(Widget):
    focusable = True

    def __init__(
        self, x, y, items=None, *, width=None, height=6, style=None, placeholder=None
    ):
        super().__init__(x, y, style)
        # The inner ListView owns item storage, scrolling, and row rendering.
        # Its x/y are kept in sync with the Dropdown's resolved position in _sync_lv().
        self._lv = ListView(x, y + 1, items, width=None, height=height, style=style)
        self._explicit_width = (
            width  # user-supplied fixed width; None = auto from items
        )
        self._index: int = 0  # confirmed selection index
        self._open: bool = False
        self._change_handler = None
        self._select_handler = None
        self.placeholder = placeholder

    # ── position sync ─────────────────────────────────────────────────────────

    def _sync_lv(self) -> None:
        """Keep the inner ListView's origin one row below this widget."""
        self._lv.x = self.abs_x
        self._lv.y = self.abs_y + 1
        self._lv._layout_y = 0
        # Force the popup rows to match the header width.
        self._lv.width = self.natural_width(1)

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def selected(self):
        items = self._lv._items
        return _value(items[self._index]) if items else None

    @property
    def selected_index(self) -> int | None:
        return self._index if self._lv._items else None

    def get(self):
        return self.selected

    def set(self, value) -> None:
        self._lv.set(value)
        self._index = self._lv._index

    def append(self, item) -> None:
        self._lv.append(item)

    def insert(self, index: int, item) -> None:
        self._lv.insert(index, item)
        if index <= self._index:
            self._index = min(self._index + 1, len(self._lv._items) - 1)

    def remove(self, item) -> None:
        self._lv.remove(item)
        self._index = max(0, min(self._index, len(self._lv._items) - 1))

    def clear(self) -> None:
        self._lv.clear()
        self._index = 0
        self._open = False

    def on_select(self, func):
        self._select_handler = func
        return self

    # ── internals ─────────────────────────────────────────────────────────────

    def _open_popup(self) -> None:
        if not self._lv._items:
            return
        self._lv._index = self._index
        self._lv._clamp_scroll()
        self._open = True

    def _confirm(self) -> None:
        self._index = self._lv._index
        self._open = False
        self._fire_change(self.selected)
        if self._select_handler:
            self._select_handler(self.selected)

    # ── Widget interface ──────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        if self._explicit_width:
            return self._explicit_width
        if not self._lv._items:
            hint = len(self.placeholder) if self.placeholder else 4
            return hint + 5
        # Header needs label + 5 ("[ " + " ▼]"); popup rows need label + 2 ("> ").
        # Always recompute from items so appended items are never clipped.
        return max(len(_display(item)) for item in self._lv._items) + 5

    def natural_height(self, scale) -> int:
        return 1 + (self._lv.natural_height(1) if self._open else 0)

    def contains(self, col: int, row: int) -> bool:
        w = self.natural_width(1)
        h = self.natural_height(1)
        return self.abs_x <= col < self.abs_x + w and self.abs_y <= row < self.abs_y + h

    def on_key(self, key) -> None:
        if not self._open:
            if key in (Key.ENTER, Key.DOWN, Key.UP, " "):
                self._open_popup()
            return

        if key == Key.ENTER:
            self._confirm()
        elif key in (Key.ESC, " "):
            self._open = False
        else:
            # UP / DOWN / HOME / END handled by ListView
            self._lv.on_key(key)

    def on_mouse_click(self, col=None, row=None) -> None:
        if row is None:
            return
        self._sync_lv()
        if row == self.abs_y:
            # Header click: toggle open/closed
            if self._open:
                self._open = False
            else:
                self._open_popup()
        elif self._open:
            # Popup row click: delegate to ListView then confirm
            self._lv.on_mouse_click(col, row)
            self._confirm()

    def draw(self, canvas) -> None:
        self._sync_lv()
        is_focused = canvas.focused is self
        w = self._lv.width  # already computed and stored by _sync_lv()

        # ── header ───────────────────────────────────────────────────────────
        items = self._lv._items
        label = _display(items[self._index]) if items else ""
        display = label or (self.placeholder or "")
        arrow = "▲" if self._open else "▼"
        inner = max(0, w - 5)  # "[ " + label + " " + arrow + "]" = 5 overhead
        header = "[ " + display[:inner].ljust(inner) + " " + arrow + "]"

        if is_focused:
            header_style = Style(fg="black", bg="white", styles=["bold"])
        elif not label and self.placeholder:
            header_style = Style(fg="bright_black", styles=["dim"])
        else:
            header_style = self.style
        canvas.write(self.abs_x, self.abs_y, header[:w], header_style)

        if not self._open:
            return

        # ── popup via ListView ────────────────────────────────────────────────
        # Temporarily focus the inner ListView so it uses its highlighted style.
        real_focused = canvas.focused
        canvas.focused = self._lv
        try:
            self._lv.draw(canvas)
        finally:
            canvas.focused = real_focused
