from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widget import Widget


class MenuItem:
    """One entry in a :class:`RightClickMenu`.

    Args:
        text: The label shown in the menu.
        on_select: Called with this ``MenuItem`` when the entry is chosen.
        value: Optional payload (defaults to *text*).
        enabled: A disabled item is dimmed and skipped by cursor navigation.
    """

    separator = False

    def __init__(self, text, on_select=None, *, value=None, enabled=True):
        self.text = text
        self.on_select = on_select
        self.value = value if value is not None else text
        self.enabled = enabled

    def __repr__(self):
        return f"MenuItem({self.text!r}, enabled={self.enabled})"


class MenuSeparator(MenuItem):
    """A non-selectable horizontal divider between groups of items."""

    separator = True

    def __init__(self):
        super().__init__("", enabled=False)


class RightClickMenu(Widget):
    """A floating context menu, opened at the cursor by a right-click.

    Pair it with :meth:`App.on_right_click`::

        menu = RightClickMenu([
            MenuItem("Copy",  on_select=lambda i: do_copy()),
            MenuItem("Paste", on_select=lambda i: do_paste()),
            MenuSeparator(),
            MenuItem("Delete", on_select=lambda i: do_delete(), enabled=can_delete),
        ])
        app.on_right_click(lambda col, row, w: menu.open_at(app, col, row))

    Up/Down move the cursor (skipping separators and disabled items), Enter or
    a click selects, and Esc or a click outside dismisses it. Selecting an item
    closes the menu and calls its ``on_select``.
    """

    focusable = True
    _CORNERS = "╭╮╰╯"
    _H = "─"
    _V = "│"

    def __init__(self, items, *, style=None):
        super().__init__(0, 0, style, mouse_moves=True)  # hover-to-highlight
        self._items: list[MenuItem] = [self._coerce(it) for it in (items or [])]
        self._index: int = self._first_selectable(0, 1)
        self._app = None  # set by open_at, used to close on selection

    # ── construction ──────────────────────────────────────────────────────────

    def _coerce(self, item) -> MenuItem:
        return item if isinstance(item, MenuItem) else MenuItem(str(item))

    def add(self, item) -> None:
        self._items.append(self._coerce(item))
        if self._index < 0:
            self._index = self._first_selectable(0, 1)

    # ── selectability / navigation ─────────────────────────────────────────────

    def _selectable(self, i: int) -> bool:
        return (
            0 <= i < len(self._items)
            and not self._items[i].separator
            and self._items[i].enabled
        )

    def _first_selectable(self, start: int, step: int) -> int:
        i = start
        while 0 <= i < len(self._items):
            if self._selectable(i):
                return i
            i += step
        return -1

    def _move(self, step: int) -> None:
        i = self._index + step
        while 0 <= i < len(self._items):
            if self._selectable(i):
                self._index = i
                return
            i += step

    @property
    def selected_index(self) -> int:
        return self._index

    # ── opening / activating ────────────────────────────────────────────────────

    def open_at(self, app, col: int, row: int):
        """Open the menu as a modal overlay with its top-left at (col, row),
        flipping left/up when it would overflow the screen edge. Returns self."""
        self._app = app
        w = self.natural_width(app.SCALE)
        h = self.natural_height(app.SCALE)
        x = col if col + w <= app.cols else max(0, col - w)
        y = row if row + h <= app.rows else max(0, row - h)
        self.x, self.y = x, y
        app.open_overlay(
            self, modal=True, dim=False, center=False, close_on_click_outside=True
        )
        return self

    def _activate(self) -> None:
        if not self._selectable(self._index):
            return
        item = self._items[self._index]
        if self._app is not None:
            self._app.close_overlay(self)
        if item.on_select is not None:
            item.on_select(item)

    # ── Widget interface ────────────────────────────────────────────────────────

    def _content_width(self) -> int:
        widths = [len(it.text) for it in self._items if not it.separator]
        return (max(widths) if widths else 4) + 2  # one space of padding each side

    def natural_width(self, scale) -> int:
        return self._content_width() + 2  # + left/right border

    def natural_height(self, scale) -> int:
        return len(self._items) + 2  # + top/bottom border

    def contains(self, col: int, row: int) -> bool:
        w = self.natural_width(1)
        h = self.natural_height(1)
        return self.abs_x <= col < self.abs_x + w and self.abs_y <= row < self.abs_y + h

    def _item_at_row(self, row: int) -> int | None:
        idx = row - self.abs_y - 1  # -1 for the top border
        return idx if 0 <= idx < len(self._items) else None

    def on_key(self, key) -> None:
        if key == Key.UP:
            self._move(-1)
        elif key == Key.DOWN:
            self._move(1)
        elif key == Key.HOME:
            self._index = self._first_selectable(0, 1)
        elif key == Key.END:
            self._index = self._first_selectable(len(self._items) - 1, -1)
        elif key in (Key.ENTER, " "):
            self._activate()

    def on_mouse_click(self, col=None, row=None) -> None:
        if row is None:
            return
        idx = self._item_at_row(row)
        if idx is not None and self._selectable(idx):
            self._index = idx
            self._activate()

    def on_mouse_move(self, col=None, row=None) -> None:
        if row is not None:
            idx = self._item_at_row(row)
            if idx is not None and self._selectable(idx) and idx != self._index:
                self._index = idx
        self._fire_hover(col, row)

    def draw(self, canvas) -> None:
        w = self.natural_width(canvas.SCALE)
        inner = w - 2
        x, y = self.abs_x, self.abs_y
        tl, tr, bl, br = self._CORNERS
        border = self.style
        raw_bg = self.style.bg.replace("_bg", "") if self.style.bg else None

        canvas.write(x, y, tl + self._H * inner + tr, border)

        for row, item in enumerate(self._items):
            vy = y + 1 + row
            if item.separator:
                canvas.write(x, vy, "├" + self._H * inner + "┤", border)
                continue

            label = (" " + item.text).ljust(inner)[:inner]
            if row == self._index:
                st = Style(fg="black", bg="white", styles=["bold"])
            elif not item.enabled:
                st = Style(fg="bright_black", bg=raw_bg)
            else:
                st = self.style

            canvas.write(x, vy, self._V, border)
            canvas.write(x + 1, vy, label, st)
            canvas.write(x + inner + 1, vy, self._V, border)

        canvas.write(x, y + 1 + len(self._items), bl + self._H * inner + br, border)
