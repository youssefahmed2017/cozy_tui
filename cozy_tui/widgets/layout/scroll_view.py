from cozy_tui.events import Key
from cozy_tui.motion import Tween, ease_out
from cozy_tui.style import Style
from cozy_tui.widget import Widget


class ScrollView(Widget):
    """A scrollable viewport. Add widgets whose combined height exceeds the box;
    only the visible slice is drawn (clipped to the viewport), with a Textual-style
    scrollbar on the right edge.

    Scroll with the mouse wheel or the keyboard (↑/↓, PageUp/PageDown, Home/End)
    while it has focus; drag the scrollbar thumb to jump. Child ``y`` positions are
    in **content space** (0 = top of the content, may exceed the viewport height).

    ``autoscroll`` (default ``True``) keeps the view pinned to the bottom as content
    grows — ideal for logs — until the user scrolls up, which unpins it; scrolling
    back to the bottom re-pins.

    ``size`` is a ``"WIDTHxHEIGHT"`` string in virtual pixels (÷ ``App.SCALE`` for
    cells), like :class:`Box`; a docked ScrollView fills its slice instead.

    Example::

        log = ScrollView(2, 2, "600x160", autoscroll=True)
        for i in range(200):
            log.add(Label(0, i, f"line {i}"))
        app.add(log); app.focus(log)
    """

    focusable = True
    scrollable = True  # the App routes wheel / page keys here when focused

    THUMB = "█"
    TRACK = "│"

    def __init__(self, x, y, size, *, autoscroll=True, scrollbar=True,
                 smooth=True, style=None, accent="bright_cyan"):
        super().__init__(x, y, style)
        self.width, self.height = map(int, size.split("x"))
        self.autoscroll = autoscroll
        self.scrollbar = scrollbar
        self.smooth = smooth  # ease the displayed offset toward the target
        self.accent = accent
        self._children: list = []
        self._scroll = 0  # target offset (what scrolling sets / clamps to)
        self._disp = 0.0  # displayed offset, eased toward _scroll when smooth
        self._scroll_tween = None
        self._laid_out = False  # first layout snaps (no fly-in animation)
        self._pin_bottom = True  # stick to the bottom until the user scrolls up
        self._vw = self._vh = 0
        self._max_scroll = 0
        self._bar_col = None
        self._dragging_bar = False

    # ── building ──────────────────────────────────────────────────────────────

    def add(self, widget):
        """Add a widget at its content-space ``(x, y)``. Returns the widget."""
        widget.parent = self
        self._children.append(widget)
        return widget

    def clear(self):
        self._children.clear()
        self._scroll = 0
        self._pin_bottom = True

    @property
    def children(self):
        return self._children

    # ── scrolling ─────────────────────────────────────────────────────────────

    def scroll_to(self, offset):
        self._scroll = max(0, min(offset, self._max_scroll))
        self._pin_bottom = self._scroll >= self._max_scroll

    def scroll_by(self, delta):
        self.scroll_to(self._scroll + delta)

    def scroll_to_top(self):
        self.scroll_to(0)

    def scroll_to_bottom(self):
        self.scroll_to(self._max_scroll)

    def content_height(self, scale):
        return max((c.y + c.natural_height(scale) for c in self._children), default=0)

    def on_key(self, key):
        if key == Key.SCROLL_UP:
            self.scroll_by(-3)
        elif key == Key.SCROLL_DOWN:
            self.scroll_by(3)
        elif key in (Key.PAGE_UP, Key.CTRL_UP):
            self.scroll_by(-max(1, self._vh - 1))
        elif key in (Key.PAGE_DOWN, Key.CTRL_DOWN):
            self.scroll_by(max(1, self._vh - 1))
        elif key == Key.UP:
            self.scroll_by(-1)
        elif key == Key.DOWN:
            self.scroll_by(1)
        elif key == Key.HOME:
            self.scroll_to_top()
        elif key == Key.END:
            self.scroll_to_bottom()

    # ── mouse: drag the scrollbar thumb ─────────────────────────────────────────

    def _bar_scroll_to(self, row):
        rel = row - self.abs_y
        frac = rel / max(1, self._vh - 1)
        self.scroll_to(round(frac * self._max_scroll))

    def on_mouse_click(self, col=None, row=None):
        self._dragging_bar = (
            col is not None and self._bar_col is not None and col == self._bar_col
        )
        if self._dragging_bar and row is not None:
            self._bar_scroll_to(row)

    def on_mouse_drag(self, col=None, row=None):
        if self._dragging_bar and row is not None:
            self._bar_scroll_to(row)

    def on_mouse_release(self, col=None, row=None):
        self._dragging_bar = False

    # ── framework hooks ─────────────────────────────────────────────────────────

    def natural_width(self, scale):
        return self.width // scale

    def natural_height(self, scale):
        return self.height // scale

    def dock_resize(self, w, h, scale):
        self.width = w * scale
        self.height = h * scale

    def contains(self, col, row):
        return (
            self.abs_x <= col < self.abs_x + self._vw
            and self.abs_y <= row < self.abs_y + self._vh
        )

    def draw(self, canvas):
        vw = self._vw = self.width // canvas.SCALE
        vh = self._vh = self.height // canvas.SCALE
        x, y = self.abs_x, self.abs_y

        content_h = self.content_height(canvas.SCALE)
        self._max_scroll = max(0, content_h - vh)
        show_bar = self.scrollbar and content_h > vh
        inner_w = vw - (1 if show_bar else 0)

        if self.autoscroll and self._pin_bottom:
            self._scroll = self._max_scroll
        self._scroll = max(0, min(self._scroll, self._max_scroll))

        # ease the displayed offset toward the target; the first layout snaps.
        if not self.smooth or not self._laid_out:
            self._disp = float(self._scroll)
            self._scroll_tween = None
        else:
            if round(self._disp) != self._scroll and (
                self._scroll_tween is None or self._scroll_tween.end != self._scroll
            ):
                self._scroll_tween = Tween(self._disp, self._scroll, 0.12, ease_out)
            if self._scroll_tween is not None:
                self._disp = self._scroll_tween.value()
                if self._scroll_tween.done:
                    self._disp = float(self._scroll)
                    self._scroll_tween = None
                else:
                    canvas.request_frame(0.033)  # ~30fps until the scroll settles
            else:
                self._disp = float(self._scroll)
        self._laid_out = True
        offset = round(self._disp)

        for r in range(vh):  # paint the viewport background
            canvas.write(x, y + r, " " * vw, self.style)

        # draw children offset by the scroll, clipped to the viewport (minus the bar)
        canvas.push_clip(x, y, x + inner_w, y + vh)
        for child in self._children:
            child._layout_y = -offset
            child.draw(canvas)
        canvas.pop_clip()

        if show_bar:
            self._draw_scrollbar(canvas, x + vw - 1, y, vh, content_h)
        else:
            self._bar_col = None

    def _draw_scrollbar(self, canvas, col, top, vh, content_h):
        self._bar_col = col
        raw_bg = self.style.raw_bg
        thumb = max(1, min(vh, round(vh * vh / content_h)))
        span = vh - thumb
        pos = round(span * (self._disp / self._max_scroll)) if self._max_scroll else 0
        thumb_style = Style(fg=self.accent, bg=raw_bg)
        track_style = Style(fg="bright_black", bg=raw_bg)
        for r in range(vh):
            on_thumb = pos <= r < pos + thumb
            canvas.write(col, top + r, self.THUMB if on_thumb else self.TRACK,
                         thumb_style if on_thumb else track_style)
