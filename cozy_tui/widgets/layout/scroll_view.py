from cozy_tui.events import Key
from cozy_tui.motion import Tween, ease_out, now
from cozy_tui.widget import Widget
from cozy_tui.widgets import _scrollbar


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

    # The thin, auto-hiding edge scrollbar shared with BarChart (see
    # widgets/_scrollbar.py). Exposed as class attrs so tests reference them.
    THUMB = _scrollbar.THUMB
    TRACK = _scrollbar.TRACK

    def __init__(
        self,
        x,
        y,
        size,
        *,
        autoscroll=True,
        scrollbar=True,
        smooth=True,
        style=None,
        accent="bright_cyan",
    ):
        super().__init__(x, y, style)
        # Opts into any-motion tracking unconditionally (like Table's own
        # row-hover tracking) rather than exposing it as a constructor kwarg
        # -- wheel routing (App._dispatch_input) prefers whatever's actually
        # hovered over whatever merely holds keyboard focus, and a
        # ScrollView full of focusable children (e.g. Buttons) can never
        # become focused itself (a focusable container always defers Tab to
        # its focusable descendants -- see App._focusables_in()), so without
        # this the wheel could never reach it at all in that shape.
        self.mouse_moves = True
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
        # Wall-clock time of the last scroll, driving the bar's auto-hide fade.
        # Seeded to "now" so a freshly built view shows its bar, then fades.
        self._bar_activity = now()

    # ── building ──────────────────────────────────────────────────────────────

    def add(self, widget):
        """Add a widget at its content-space ``(x, y)``. Returns the widget."""
        widget.parent = self
        self._children.append(widget)
        return widget

    def clear(self):
        super().clear()  # detaches each child's parent
        self._scroll = 0
        self._pin_bottom = True
        return self

    @property
    def children(self):
        return self._children

    # ── scrolling ─────────────────────────────────────────────────────────────

    def scroll_to(self, offset):
        self._scroll = max(0, min(offset, self._max_scroll))
        self._pin_bottom = self._scroll >= self._max_scroll
        self._bar_activity = now()  # wake the scrollbar out of its faded idle

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

        # draw children offset by the scroll, clipped to the viewport (minus the bar).
        # Children fully outside [offset, offset+vh) are skipped entirely (not just
        # clipped) so a long log/list doesn't pay for off-screen widgets' draw() every
        # frame — _layout_y is still kept current for all of them so hit-testing
        # (contains()) never sees a stale position for a child scrolled into view by
        # a mouse-only change (e.g. a drag) that doesn't itself trigger a redraw.
        canvas.push_clip(x, y, x + inner_w, y + vh)
        for child in self._children:
            child._layout_y = -offset
            top = child.y - offset
            if (
                child.visible
                and top + child.natural_height(canvas.SCALE) > 0
                and top < vh
            ):
                child.draw(canvas)
        canvas.pop_clip()

        if show_bar:
            self._draw_scrollbar(canvas, x + vw - 1, y, vh, content_h)
        else:
            self._bar_col = None

    def _draw_scrollbar(self, canvas, col, top, vh, content_h):
        self._bar_col = col
        # _disp is the eased displayed offset, so the thumb glides with a smooth
        # scroll rather than jumping to the target row.
        _scrollbar.draw(
            canvas,
            col,
            top,
            vh,
            content_h,
            self._disp,
            self._max_scroll,
            self.accent,
            self.style.raw_bg,
            self._bar_activity,
        )
