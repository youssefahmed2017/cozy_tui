from cozy_tui.style import Style


class Widget:
    focusable = False

    def __init__(
        self, x=0, y=0, style=None, *, mouse_moves=False, name: str = "BaseWidget"
    ):
        self.x = x
        self.y = y
        self.parent = None
        self.style = style or Style()
        # Opt this widget into bare mouse-motion events (hover / enter / leave /
        # on_mouse_move). Off by default because any-motion tracking floods the
        # input stream; the App turns the terminal-level tracking on only while
        # at least one live widget wants it. Registering an on_hover/on_enter/
        # on_leave callback flips this on automatically.
        self.mouse_moves = mouse_moves
        self._layout_y = 0
        self._clip_width = None
        self._click_handler = None
        self._right_click_handler = None
        self._double_click_handler = None
        self._drag_handler = None
        self._release_handler = None
        self._hover_handler = None
        self._enter_handler = None
        self._leave_handler = None
        self._change_handler = None
        self.laps = False
        self.name = name

    @property
    def abs_x(self):
        if self.parent:
            return self.parent.abs_x + self.x
        return self.x

    @property
    def abs_y(self):
        if self.parent:
            return self.parent.abs_y + self.y + self._layout_y
        return self.y + self._layout_y

    def on_click(self, func):
        """Register a callback invoked when this widget is activated (mouse click
        or keyboard). Receives the widget as its only argument."""
        self._click_handler = func
        return self

    def on_right_click(self, func):
        """Register a callback for a right-click (button 2) on this widget.
        Receives (widget, col, row). A right-click never moves focus or fires the
        normal click handler."""
        self._right_click_handler = func
        return self

    def on_double_click(self, func):
        """Register a callback for a double-click. Receives the widget. If unset,
        a double-click falls back to firing the normal click handler."""
        self._double_click_handler = func
        return self

    def on_drag(self, func):
        """Register a callback for mouse motion while a button is held over this
        widget. Receives (widget, col, row) in absolute terminal cells."""
        self._drag_handler = func
        return self

    def on_release(self, func):
        """Register a callback for a mouse-button release. Receives
        (widget, col, row) in absolute terminal cells."""
        self._release_handler = func
        return self

    def on_hover(self, func):
        """Register a callback for mouse motion with no button held over this
        widget. Receives (widget, col, row). Enables ``mouse_moves`` on this
        widget so the App starts tracking motion."""
        self._hover_handler = func
        self.mouse_moves = True
        return self

    def on_enter(self, func):
        """Register a callback fired when the cursor enters this widget. Receives
        the widget. Enables ``mouse_moves`` on this widget."""
        self._enter_handler = func
        self.mouse_moves = True
        return self

    def on_leave(self, func):
        """Register a callback fired when the cursor leaves this widget. Receives
        the widget. Enables ``mouse_moves`` on this widget."""
        self._leave_handler = func
        self.mouse_moves = True
        return self

    def on_change(self, func):
        """Register a callback invoked when this widget's value changes. Receives the new value."""
        self._change_handler = func
        return self

    def _fire_click(self):
        if self._click_handler:
            self._click_handler(self)

    def _fire_right_click(self, col, row):
        if self._right_click_handler:
            self._right_click_handler(self, col, row)

    def _fire_double_click(self):
        if self._double_click_handler:
            self._double_click_handler(self)

    def _fire_drag(self, col, row):
        if self._drag_handler:
            self._drag_handler(self, col, row)

    def _fire_release(self, col, row):
        if self._release_handler:
            self._release_handler(self, col, row)

    def _fire_hover(self, col, row):
        if self._hover_handler:
            self._hover_handler(self, col, row)

    def _fire_enter(self):
        if self._enter_handler:
            self._enter_handler(self)

    def _fire_leave(self):
        if self._leave_handler:
            self._leave_handler(self)

    def _fire_change(self, value):
        if self._change_handler:
            self._change_handler(value)

    # Mouse handlers. The App loop calls these; the base implementations fire the
    # registered callbacks. Subclasses may override for custom behavior (an
    # override replaces the default, so call the matching _fire_* if you still
    # want the registered callback to run).
    def on_mouse_click(self, col=None, row=None):
        self._fire_click()

    def on_mouse_right_click(self, col=None, row=None):
        self._fire_right_click(col, row)

    def on_mouse_double_click(self, col=None, row=None):
        if self._double_click_handler:
            self._fire_double_click()
        else:
            self.on_mouse_click(col, row)  # fall back to a normal click

    def on_mouse_drag(self, col=None, row=None):
        self._fire_drag(col, row)

    def on_mouse_release(self, col=None, row=None):
        self._fire_release(col, row)

    def on_mouse_move(self, col=None, row=None):
        self._fire_hover(col, row)

    def on_mouse_enter(self):
        self._fire_enter()

    def on_mouse_leave(self):
        self._fire_leave()

    def natural_width(self, scale):
        return 0

    def natural_height(self, scale):
        return 1

    def dock_resize(self, w, h, scale):
        """Hook called by the dock layout with the (w, h) cell slice this widget
        was assigned. Fixed-size widgets ignore it; containers that can fill a
        rectangle override it to grow into their slice."""

    def contains(self, col: int, row: int) -> bool:
        """True if (col, row) falls within this widget's natural bounding box.
        The default suits any widget whose hit-box is its full natural size;
        widgets with a smaller/offset hit-box (single-row controls, bordered
        containers) override this. A zero-width base widget contains nothing."""
        w = self.natural_width(1)
        h = self.natural_height(1)
        return self.abs_x <= col < self.abs_x + w and self.abs_y <= row < self.abs_y + h

    def draw(self, canvas):
        raise NotImplementedError

    def on_key(self, key):
        pass

    def __str__(self):
        return f"Widget {self.name}"
