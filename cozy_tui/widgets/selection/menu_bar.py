from cozy_tui._width import text_width
from cozy_tui.events import Key
from cozy_tui.style import selection_style
from cozy_tui.widget import Widget
from cozy_tui.widgets.selection.context_menu import RightClickMenu


class MenuBar(Widget):
    """A horizontal row of top-level labels ("File", "Edit", ...), each
    opening a dropdown menu built from the same ``MenuItem``/``MenuSeparator``
    building blocks as :class:`RightClickMenu` (submenus, icons, shortcuts,
    and disabled items all work the same way, since a click/Down/Enter simply
    opens a ``RightClickMenu`` positioned right below the label).

    ``menus`` is a list of ``(label, items)`` pairs, where *items* is
    whatever :class:`RightClickMenu` accepts::

        bar = MenuBar(0, 0, [
            ("File", [MenuItem("New", on_select=new), MenuItem("Quit", on_select=app.quit)]),
            ("Edit", [MenuItem("Copy", shortcut="Ctrl+C", on_select=copy)]),
        ])
        app.dock(bar, "top")

    Left/Right move between top-level labels; Down/Enter/Space open the
    highlighted one. Once open, Esc or a click outside closes it -- matching
    every other dropdown/menu in this library, a click that lands on a
    *different* label while one is already open just closes the first (a
    second click opens the new one).
    """

    focusable = True

    def __init__(self, x, y, menus, *, style=None, gap=2):
        super().__init__(x, y, style, name="Menu Bar")
        self.menus = [(label, list(items)) for label, items in menus]
        self.gap = gap
        self._index = 0
        self._open_menu = None  # the RightClickMenu overlay, while one is open
        self._app = None  # set each draw(), used to open/close overlays
        self._bar_width = 0
        self._label_bounds = []  # [(start_col, end_col), ...] per menu, set each draw()

    # ── internals ─────────────────────────────────────────────────────────────

    def _label_text(self, label) -> str:
        return f" {label} "

    def _content_width(self) -> int:
        if not self.menus:
            return 0
        widths = [text_width(self._label_text(label)) for label, _items in self.menus]
        return sum(widths) + self.gap * (len(widths) - 1)

    def _open_at(self, index) -> None:
        if self._app is None or not self.menus or self._open_menu is not None:
            return
        self._index = index
        _label, items = self.menus[index]
        start, _end = self._label_bounds[index]
        menu = RightClickMenu(items, style=self.style)
        self._open_menu = menu
        menu.open_at(self._app, start, self.abs_y + 1, on_close=self._on_menu_close)

    def _on_menu_close(self, _widget) -> None:
        self._open_menu = None

    # ── Widget interface ──────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        return self._content_width()

    def natural_height(self, scale) -> int:
        return 1

    def dock_resize(self, w, h, scale) -> None:
        self._bar_width = w

    def contains(self, col: int, row: int) -> bool:
        w = self._bar_width or self._content_width()
        return self.abs_x <= col < self.abs_x + w and row == self.abs_y

    def on_key(self, key) -> None:
        if not self.menus:
            return
        if key == Key.LEFT:
            self._index = (self._index - 1) % len(self.menus)
        elif key == Key.RIGHT:
            self._index = (self._index + 1) % len(self.menus)
        elif key in (Key.DOWN, Key.ENTER, " "):
            self._open_at(self._index)

    def on_mouse_click(self, col=None, row=None) -> None:
        if col is None or not self._label_bounds:
            return
        for i, (start, end) in enumerate(self._label_bounds):
            if start <= col < end:
                self._index = i
                self._open_at(i)
                return

    def draw(self, canvas) -> None:
        self._app = canvas
        w = self._bar_width or self._content_width()
        canvas.write(self.abs_x, self.abs_y, " " * w, self.style)

        is_focused = canvas.focused is self
        col = self.abs_x
        self._label_bounds = []
        for i, (label, _items) in enumerate(self.menus):
            text = self._label_text(label)
            lw = text_width(text)
            self._label_bounds.append((col, col + lw))
            highlighted = i == self._index and (
                self._open_menu is not None or is_focused
            )
            style = selection_style() if highlighted else self.style
            canvas.write(col, self.abs_y, text, style)
            col += lw + self.gap
