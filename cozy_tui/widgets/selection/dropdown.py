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
        # The inner ListView owns item storage, scrolling, and row rendering. When
        # open it is pushed onto the App's overlay layer so it floats above every
        # other widget instead of being drawn inline (which could be overpainted).
        self._lv = ListView(x, y + 1, items, width=None, height=height, style=style)
        self._lv.on_select(self._on_lv_select)
        self._explicit_width = width  # user-supplied fixed width; None = auto
        self._index: int = 0  # confirmed selection index
        self._open: bool = False
        self._change_handler = None
        self._select_handler = None
        self.placeholder = placeholder
        self._app = None  # set to the canvas (App) each draw, for opening overlays

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
        self._close()

    def on_select(self, func):
        self._select_handler = func
        return self

    # ── internals ─────────────────────────────────────────────────────────────

    def _open_popup(self) -> None:
        if self._open or not self._lv._items or self._app is None:
            return
        self._lv._index = self._index
        self._lv._clamp_scroll()
        self._position_popup(self._app)
        self._open = True
        # Modal so arrows/Enter go to the list; no dim (a dropdown isn't a dialog);
        # a click outside or Esc cancels. Popup is positioned, not centered.
        self._app.open_overlay(
            self._lv,
            modal=True,
            dim=False,
            center=False,
            close_on_escape=True,
            close_on_click_outside=True,
            on_close=self._on_popup_close,
        )

    def _position_popup(self, canvas) -> None:
        """Place the popup one row below the header, in screen coordinates."""
        scroll = getattr(canvas, "scroll_y", 0)
        self._lv.x = self.abs_x
        self._lv.y = self.abs_y - scroll + 1
        self._lv._layout_y = 0
        self._lv.width = self.natural_width(1)

    def _close(self) -> None:
        if self._open and self._app is not None:
            self._app.close_overlay(self._lv)  # fires _on_popup_close
        else:
            self._open = False

    def _on_popup_close(self, _widget) -> None:
        # Called by the overlay layer on Esc / click-outside / after a selection.
        self._open = False

    def _on_lv_select(self, _value) -> None:
        # Fired by the inner ListView on Enter or a row click.
        self._index = self._lv._index
        self._fire_change(self.selected)
        if self._select_handler:
            self._select_handler(self.selected)
        self._close()

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
        # The popup lives on the overlay layer now, so the header is always a
        # single row and never pushes surrounding widgets when opened.
        return 1

    def contains(self, col: int, row: int) -> bool:
        w = self.natural_width(1)
        return self.abs_x <= col < self.abs_x + w and row == self.abs_y

    def on_key(self, key) -> None:
        # While open, the modal overlay routes keys straight to the ListView, so
        # this only handles opening from the closed state.
        if not self._open and key in (Key.ENTER, Key.DOWN, Key.UP, " "):
            self._open_popup()

    def on_mouse_click(self, col=None, row=None) -> None:
        if not self._open:
            self._open_popup()

    def draw(self, canvas) -> None:
        self._app = canvas
        is_focused = canvas.focused is self
        w = self.natural_width(1)

        # Keep the (overlay) popup anchored under the header across resizes.
        if self._open:
            self._position_popup(canvas)

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
