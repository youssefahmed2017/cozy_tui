from cozy_tui.events import Key
from cozy_tui.style import Style, selection_style
from cozy_tui.widget import Widget
from cozy_tui.widgets.selection.list_view import ListView, _display, _value


class Collapsible(ListView):
    """A focusable container whose children are navigated like a ListView.

    Items may be Widget instances *or* plain strings / ListItems:
    - Widget items are drawn directly (Button, Checkbox, Label, ...).  The
      selected one renders as focused so it shows its active style.  Pressing
      Enter / Space forwards the key event to the widget.
    - Text items (str or ListItem) are drawn as ListView rows with a "> "
      selection prefix.  Pressing Enter fires on_select with the item value.

    All items are laid out sequentially (one row each) regardless of the
    widget's own y coordinate.

    Keys: Up/Down navigate items, Left collapse, Right expand,
    Enter/Space activate the selected item (or expand when collapsed).
    """

    focusable = True

    def __init__(self, x, y, *, title: str = "", expanded: bool = True, style=None):
        super().__init__(x, y, style=style, name="Collapsible")
        self.title = title
        self.expanded = expanded
        self._toggle_handler = None
        # _items (from ListView) stores Widget objects, ListItems, or plain strings.

    # -- children -------------------------------------------------------------

    @property
    def children(self):
        # Return [] so App never collects children as individually focusable.
        return []

    def add(self, item):
        """Add a Widget, ListItem, or plain string as the next row."""
        if isinstance(item, Widget):
            item.parent = self
            item._layout_y = 1  # refined each frame in draw()
        self._items.append(item)
        return self

    # ListView.append() would misuse _label_width_cache (it's a str-only concept
    # here); route it to add() so calling either name does the right thing.
    append = add

    # -- expand / collapse API ------------------------------------------------

    def expand(self) -> None:
        if not self.expanded:
            self.expanded = True
            if self._toggle_handler:
                self._toggle_handler(True)

    def collapse(self) -> None:
        if self.expanded:
            self.expanded = False
            if self._toggle_handler:
                self._toggle_handler(False)

    def toggle(self) -> None:
        self.collapse() if self.expanded else self.expand()

    def on_toggle(self, func):
        """Called with the new expanded bool whenever state changes."""
        self._toggle_handler = func
        return self

    # -- Widget interface -----------------------------------------------------

    @property
    def selected(self):
        """Value of the highlighted item.  Widgets return the widget itself."""
        if not self._items:
            return None
        return _value(self._items[self._index])

    def natural_width(self, scale) -> int:
        header_w = len(self.title) + 2  # "v " / "> " prefix
        if not self.expanded or not self._items:
            return header_w
        child_w = 0
        for item in self._items:
            if isinstance(item, Widget):
                w = item.x + item.natural_width(scale)
            else:
                w = len(_display(item)) + 2  # "> " prefix
            child_w = max(child_w, w)
        return max(header_w, child_w)

    def natural_height(self, scale) -> int:
        if not self.expanded or not self._items:
            return 1
        return 1 + len(self._items)  # header row + one row per item

    def on_key(self, key) -> None:
        if key == Key.LEFT:
            self.collapse()
        elif key == Key.RIGHT:
            self.expand()
        elif key == Key.UP:
            if self._items and self._index > 0:
                self._move(self._index - 1)
        elif key == Key.DOWN:
            if self._items and self._index < len(self._items) - 1:
                self._move(self._index + 1)
        elif key == Key.HOME:
            if self._items:
                self._move(0)
        elif key == Key.END:
            if self._items:
                self._move(len(self._items) - 1)
        elif key in (Key.ENTER, " "):
            if not self.expanded:
                self.expand()
            elif self._items:
                item = self._items[self._index]
                if isinstance(item, Widget):
                    item.on_key(key)
                else:
                    self._activate(from_click=False)

    def on_mouse_click(self, col=None, row=None) -> None:
        if row is None:
            return
        if row == self.abs_y:
            self.toggle()
            return
        if not self.expanded:
            return
        for i, item in enumerate(self._items):
            item_row = self.abs_y + 1 + i
            if isinstance(item, Widget):
                if item.contains(col, row):
                    self._move(i)
                    item.on_mouse_click(col, row)
                    break
            elif row == item_row:
                self._move(i)
                self._activate(from_click=True)
                break

    def draw(self, canvas) -> None:
        is_focused = canvas.focused is self
        arrow = "v" if self.expanded else ">"
        header = f"{arrow} {self.title}"

        if is_focused:
            header_style = Style(fg="bright_white", styles=["bold"])
        else:
            header_style = self.style

        canvas.write(self.abs_x, self.abs_y, header, header_style)

        if not self.expanded:
            return

        w = self.natural_width(1)
        for i, item in enumerate(self._items):
            is_sel = is_focused and i == self._index
            row = self.abs_y + 1 + i

            if isinstance(item, Widget):
                # Force sequential layout: abs_y = parent.abs_y + item.y + _layout_y
                # => set _layout_y = 1 + i - item.y so abs_y = parent.abs_y + 1 + i
                item._layout_y = 1 + i - item.y
                if is_sel:
                    real_focused = canvas.focused
                    canvas.focused = item
                    try:
                        item.draw(canvas)
                    finally:
                        canvas.focused = real_focused
                else:
                    item.draw(canvas)
            else:
                # ListItem or str: render as a text row with selection prefix.
                text = _display(item)
                prefix = "> " if is_sel else "  "
                line = (prefix + text).ljust(w)[:w]
                if is_sel:
                    style = selection_style()
                else:
                    style = self.style
                canvas.write(self.abs_x, row, line, style)
