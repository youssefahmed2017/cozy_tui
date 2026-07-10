import time

from cozy_tui._width import text_width
from cozy_tui.events import Key
from cozy_tui.motion import ease_out
from cozy_tui.style import Style
from cozy_tui.widget import Widget


class _TabPanel(Widget):
    """The content region for one tab — a plain container of widgets, positioned
    just below the tab strip. Only the active panel is drawn / focusable, because
    :class:`Tabs` exposes just that panel in its ``children``."""

    def __init__(self, tabs, x, y):
        super().__init__(x, y)
        self.parent = tabs
        self.children = []

    def add(self, widget):
        widget.parent = self
        self.children.append(widget)
        return widget

    def draw(self, canvas):
        for child in self.children:
            child.draw(canvas)


class _TabBar(Widget):
    """The clickable tab strip (title row + underline rule). Focusable, with no
    focusable children, so Tab stops here first; Left/Right (or a click) switch
    tabs and then Tab dives into the active panel's controls."""

    focusable = True

    def __init__(self, tabs):
        super().__init__(0, 0, name="Tab")
        self.parent = tabs
        self.tabs = tabs
        self._segments = []  # (local_start, local_end, index) for click hit-testing

    def natural_width(self, scale):
        return self.tabs._wc

    def natural_height(self, scale):
        return 2  # title row + rule row

    def contains(self, col, row):
        return (
            self.abs_x <= col < self.abs_x + self.tabs._wc
            and self.abs_y <= row < self.abs_y + 2
        )

    def on_key(self, key):
        if key == Key.LEFT:
            self.tabs.select(self.tabs.active - 1)
        elif key == Key.RIGHT:
            self.tabs.select(self.tabs.active + 1)
        elif key == Key.HOME:
            self.tabs.select(0)
        elif key == Key.END:
            self.tabs.select(len(self.tabs._titles) - 1)

    def on_mouse_click(self, col=None, row=None):
        if col is None:
            return
        local = col - self.abs_x
        for start, end, index in self._segments:
            if start <= local < end:
                self.tabs.select(index)
                return

    def draw(self, canvas):
        tabs = self.tabs
        x, y, w = self.abs_x, self.abs_y, tabs._wc
        focused = canvas.focused is self
        accent = tabs.accent
        raw_bg = tabs.style.raw_bg

        canvas.write(x, y, " " * w, tabs.style)  # clear the title row
        self._segments = []
        cx = 0
        for i, title in enumerate(tabs._titles):
            label = f" {title} "
            lw = text_width(label)
            active = i == tabs.active
            if active and focused:
                st = Style(fg="black", bg=accent, styles=["bold"])
            elif active:
                st = Style(fg=accent, bg=raw_bg, styles=["bold"])
            else:
                st = Style(fg="bright_black", bg=raw_bg)
            if cx < w:
                canvas.write(x + cx, y, label, st)
            self._segments.append((cx, cx + lw, i))
            cx += lw

        # underline rule; the active tab's span is drawn in the accent color. While
        # switching, the accent span glides between the old and new tab segments.
        canvas.write(x, y + 1, "─" * w, Style(fg="bright_black", bg=raw_bg))
        accent_style = Style(fg=accent, bg=raw_bg, styles=["bold"])
        ease = tabs._anim_ease()
        if ease is not None and self._segments:
            fs, ts = self._segments[tabs._from], self._segments[tabs._to]
            u0 = fs[0] + (ts[0] - fs[0]) * ease
            u1 = fs[1] + (ts[1] - fs[1]) * ease
            a, b = max(0, round(u0)), min(w, round(u1))
            if b > a:
                canvas.write(x + a, y + 1, "─" * (b - a), accent_style)
        else:
            for start, end, index in self._segments:
                if index == tabs.active and start < w:
                    span = min(end, w) - start
                    canvas.write(x + start, y + 1, "─" * span, accent_style)


class Tabs(Widget):
    """A tabbed container: a strip of clickable tab titles above a content area
    that shows the active tab's panel.

    Keyboard focus lands on the tab strip first (Left/Right or Home/End switch
    tabs); pressing Tab again dives into the active panel's own controls. A click
    on a tab title switches to it. Inactive panels are never drawn, focusable, or
    hit-tested.

    Example::

        tabs = Tabs(2, 2, "600x200")
        files = tabs.add_tab("Files")          # returns a panel container
        files.add(ListView(1, 1, [...]))
        tabs.add_tab("About", Label(1, 1, "…"))  # widgets can be passed inline
        tabs.on_change(lambda index: ...)
        box.add(tabs)

    ``size`` is a ``"WIDTHxHEIGHT"`` string in virtual pixels (÷ ``App.SCALE`` for
    cells), like :class:`Box`; a docked ``Tabs`` fills its slice instead.
    """

    def __init__(
        self,
        x,
        y,
        size,
        *,
        style=None,
        accent="bright_cyan",
        animate=True,
        anim_duration=0.18,
    ):
        super().__init__(x, y, style, name="Tabs")
        self.width, self.height = map(int, size.split("x"))
        self.accent = accent
        self.animate = animate  # slide panels + glide the underline on switch
        self.anim_duration = anim_duration
        self._titles = []
        self._panels = []
        self.active = 0
        self._bar = _TabBar(self)
        self._wc = self._hc = 0  # last drawn size in cells
        # switch-transition state (purely visual; active/focus swap immediately)
        self._transitioning = False
        self._from = self._to = 0
        self._anim_start = 0.0

    # ── building ──────────────────────────────────────────────────────────────

    def add_tab(self, title, *widgets):
        """Add a tab titled *title*. Any *widgets* are placed in its panel.
        Returns the panel container so more widgets can be ``add``-ed to it."""
        self._titles.append(title)
        panel = _TabPanel(self, 1, 2)  # content sits below the 2-row tab strip
        for widget in widgets:
            panel.add(widget)
        self._panels.append(panel)
        return panel

    def select(self, index):
        """Switch to the tab at *index* (clamped), firing ``on_change``. When
        ``animate`` is on (and the widget has been drawn), the panels slide and
        the underline glides; ``active``/focus still switch immediately."""
        if not self._panels:
            return
        index = max(0, min(index, len(self._panels) - 1))
        if index != self.active:
            old = self.active
            self.active = index
            if self.animate and self._wc > 0:  # _wc>0: at least one draw has run
                self._from = old
                self._to = index
                self._anim_start = time.monotonic()
                self._transitioning = True
            self._fire_change(index)

    @property
    def bar(self):
        """The focusable tab strip. Pass it to ``app.focus(...)`` to start focus
        on the tabs (Left/Right then switch tabs)."""
        return self._bar

    @property
    def selected_index(self):
        return self.active

    @property
    def selected_title(self):
        return self._titles[self.active] if self._titles else None

    def panel(self, index):
        """The panel container for the tab at *index*."""
        return self._panels[index]

    # ── framework hooks ─────────────────────────────────────────────────────────

    @property
    def children(self):
        # Only the tab bar and the *active* panel are live — this is what confines
        # focus, hit-testing, and drawing to the selected tab.
        if not self._panels:
            return [self._bar]
        return [self._bar, self._panels[self.active]]

    def natural_width(self, scale):
        return self.width // scale

    def natural_height(self, scale):
        return self.height // scale

    def dock_resize(self, w, h, scale):
        self.width = w * scale
        self.height = h * scale

    def contains(self, col, row):
        return (
            self.abs_x <= col < self.abs_x + self._wc
            and self.abs_y <= row < self.abs_y + self._hc
        )

    def _anim_ease(self):
        """Eased switch progress in ``[0, 1)`` while transitioning, else ``None``.
        Ease-out cubic, so the slide starts fast and settles gently."""
        if not self._transitioning:
            return None
        p = (time.monotonic() - self._anim_start) / self.anim_duration
        if p >= 1.0:
            return None
        return ease_out(p)

    def draw(self, canvas):
        self._wc = self.width // canvas.SCALE
        self._hc = self.height // canvas.SCALE
        for r in range(self._hc):  # paint the tab area (esp. if style has a bg)
            canvas.write(self.abs_x, self.abs_y + r, " " * self._wc, self.style)
        self._bar.draw(canvas)
        if not self._panels:
            return

        if self._anim_ease() is None:
            # settled (or not animating): reveal the active tab's content.
            self._transitioning = False
            # Clipped to Tabs' own assigned rectangle (like ScrollView/Splitter
            # already clip their content) -- otherwise a panel taller than the
            # available space bleeds straight through past the tab strip into
            # whatever's drawn after Tabs (typically a docked footer),
            # corrupting both instead of the overflow just being invisible.
            canvas.push_clip(
                self.abs_x, self.abs_y, self.abs_x + self._wc, self.abs_y + self._hc
            )
            self._panels[self.active].draw(canvas)
            canvas.pop_clip()
        else:
            # mid-switch: keep the content area empty while the underline glides;
            # the new panel is revealed only once the animation finishes.
            canvas.request_frame(0.033)  # ~30fps for a smooth glide
