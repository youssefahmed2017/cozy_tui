from cozy_tui._width import text_width
from cozy_tui.events import Key
from cozy_tui.style import Style, selection_style
from cozy_tui.widget import Widget


class MenuItem:
    """One entry in a :class:`RightClickMenu`.

    Args:
        text: The label shown in the menu.
        on_select: Called with this ``MenuItem`` when the entry is chosen. Ignored
            when the item has a *submenu* (choosing it opens the submenu instead).
        value: Optional payload (defaults to *text*).
        enabled: A disabled item is dimmed and skipped by cursor navigation.
        icon: Optional glyph shown before the label, e.g. ``"📋"``. Equivalent to
            embedding it in *text* yourself — ``MenuItem("Copy", icon="📋")`` and
            ``MenuItem("📋 Copy")`` render the same.
        shortcut: Optional accelerator label shown right-aligned, e.g. ``"Ctrl+C"``.
            Display only — it's a hint; wire the real key binding with
            ``app.on_key(...)`` yourself.
        submenu: Optional list of ``MenuItem`` shown as a nested menu. The item is
            marked with ``▶``; Right/Enter/click opens it, Left/Esc closes it.
    """

    separator = False

    def __init__(
        self,
        text,
        on_select=None,
        *,
        value=None,
        enabled=True,
        icon=None,
        shortcut=None,
        submenu=None,
    ):
        self.text = text
        self.on_select = on_select
        self.value = value if value is not None else text
        self.enabled = enabled
        self.icon = icon
        self.shortcut = shortcut
        self.submenu = list(submenu) if submenu else None

    @property
    def has_submenu(self) -> bool:
        return bool(self.submenu)

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
            MenuItem("Copy",  icon="📋", shortcut="Ctrl+C", on_select=do_copy),
            MenuItem("Paste", icon="📄", shortcut="Ctrl+V", on_select=do_paste),
            MenuSeparator(),
            MenuItem("Theme", submenu=[MenuItem("Dark"), MenuItem("Light")]),
            MenuItem("Delete", icon="🗑", shortcut="Del", on_select=do_delete),
        ])
        app.on_right_click(lambda col, row, w: menu.open_at(app, col, row))

    Up/Down move the cursor (skipping separators and disabled items); Enter, a
    click, or Right selects. Selecting a leaf closes the whole menu chain and
    calls its ``on_select``; selecting an item with a ``submenu`` opens the
    submenu to the side. Left/Esc closes the current (sub)menu; a click outside
    dismisses it.
    """

    focusable = True
    _CORNERS = "╭╮╰╯"
    _H = "─"
    _V = "│"
    _SUBMENU_ARROW = "▶"
    GAP = 2  # minimum columns between the label and its shortcut/arrow column

    def __init__(self, items, *, style=None, mouse_moves: bool = False):
        super().__init__(
            0, 0, style, mouse_moves=mouse_moves, name="Right Click Menu"
        )  # hover-to-highlight opt-in
        self._items: list[MenuItem] = [self._coerce(it) for it in (items or [])]
        self._index: int = self._first_selectable(0, 1)
        self._app = None  # set by open_at, used to close on selection
        self._parent_menu = None  # set when opened as a submenu
        self._open_sub = None  # currently-open child submenu, if any

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

    def open_at(self, app, col: int, row: int, *, on_close=None):
        """Open the menu as a modal overlay with its top-left at (col, row),
        flipping left/up when it would overflow the screen edge. `on_close`
        (optional) is called when the menu is dismissed, however that
        happens -- Esc, a click outside, or a selection. Returns self."""
        self._app = app
        w = self.natural_width(app.SCALE)
        h = self.natural_height(app.SCALE)
        x = col if col + w <= app.cols else max(0, col - w)
        y = row if row + h <= app.rows else max(0, row - h)
        self.x, self.y = x, y
        app.open_overlay(
            self,
            modal=True,
            dim=False,
            center=False,
            close_on_click_outside=True,
            on_close=on_close,
        )
        return self

    def _open_submenu(self, item: MenuItem) -> None:
        if self._app is None or not item.has_submenu:
            return
        sub = RightClickMenu(item.submenu, style=self.style)
        sub._parent_menu = self
        self._open_sub = sub
        width = self.natural_width(self._app.SCALE)
        # Place the submenu just right of this item, its first row aligned with
        # the parent item (top border sits one row above).
        sub.open_at(self._app, self.x + width, self.abs_y + self._index)

    def _close_chain(self) -> None:
        """Close this menu and every ancestor, unwinding the whole chain."""
        menu = self
        while menu is not None:
            parent = menu._parent_menu
            if menu._app is not None:
                menu._app.close_overlay(menu)
            menu = parent

    def _activate(self) -> None:
        if not self._selectable(self._index):
            return
        item = self._items[self._index]
        if item.has_submenu:
            self._open_submenu(item)
            return
        self._close_chain()
        if item.on_select is not None:
            item.on_select(item)

    # ── Widget interface ────────────────────────────────────────────────────────

    def _left_text(self, item: MenuItem) -> str:
        return f"{item.icon} {item.text}" if item.icon else item.text

    def _right_text(self, item: MenuItem) -> str:
        if item.has_submenu:
            return self._SUBMENU_ARROW
        return item.shortcut or ""

    def _content_width(self) -> int:
        entries = [it for it in self._items if not it.separator]
        left_w = max((text_width(self._left_text(it)) for it in entries), default=4)
        right_w = max((text_width(self._right_text(it)) for it in entries), default=0)
        gap = self.GAP if right_w else 0
        return 1 + left_w + gap + right_w + 1  # 1 leading + 1 trailing pad

    def natural_width(self, scale) -> int:
        return self._content_width() + 2  # + left/right border

    def natural_height(self, scale) -> int:
        return len(self._items) + 2  # + top/bottom border

    def _item_at_row(self, row: int) -> int | None:
        idx = row - self.abs_y - 1  # -1 for the top border
        return idx if 0 <= idx < len(self._items) else None

    def _row_text(self, item: MenuItem, inner: int) -> str:
        left = self._left_text(item)
        right = self._right_text(item)
        gap = max(1, inner - 2 - text_width(left) - text_width(right))
        return " " + left + " " * gap + right + " "

    def on_key(self, key) -> None:
        if key == Key.UP:
            self._move(-1)
        elif key == Key.DOWN:
            self._move(1)
        elif key == Key.HOME:
            self._index = self._first_selectable(0, 1)
        elif key == Key.END:
            self._index = self._first_selectable(len(self._items) - 1, -1)
        elif key in (Key.ENTER, " ", Key.RIGHT):
            # Right only acts on submenu items; Enter/Space activate anything.
            if key != Key.RIGHT or (
                self._selectable(self._index) and self._items[self._index].has_submenu
            ):
                self._activate()
        elif key == Key.LEFT and self._parent_menu is not None:
            if self._app is not None:
                self._app.close_overlay(self)  # step back to the parent menu

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
        raw_bg = self.style.raw_bg

        canvas.write(x, y, tl + self._H * inner + tr, border)

        for row, item in enumerate(self._items):
            vy = y + 1 + row
            if item.separator:
                canvas.write(x, vy, "├" + self._H * inner + "┤", border)
                continue

            if row == self._index:
                st = selection_style()
            elif not item.enabled:
                st = Style(fg="bright_black", bg=raw_bg)
            else:
                st = self.style

            canvas.write(x, vy, self._V, border)
            canvas.write(x + 1, vy, self._row_text(item, inner), st)
            canvas.write(x + inner + 1, vy, self._V, border)

        canvas.write(x, y + 1 + len(self._items), bl + self._H * inner + br, border)
