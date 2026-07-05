import time

from cozy_tui.ansi import tint
from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widget import Widget


class Button(Widget):
    """A clickable button.

    Visual states, from least to most prominent: idle → hovered → focused →
    active. The hover state is opt-in: set ``mouse_moves=True`` on the button
    (or register an ``on_enter``/``on_leave``/``on_hover`` callback, which does
    it for you). On activation the button
    plays a brief **active effect** — modelled on Textual's ``-active`` state:
    the whole button tints toward the screen background for
    ``active_effect_duration`` seconds, giving a "pressed-in" flash — then
    reverts.

    Pass ``animation=`` a color animation (``GlowAnimation`` / ``RainbowAnimation``
    or any :class:`Animation`) to animate the label text while the button is
    focused or hovered.
    """

    focusable = True

    #: How far the active effect tints toward the background (Textual uses 30%).
    ACTIVE_TINT = 0.3

    def __init__(
        self,
        x,
        y,
        text,
        style=None,
        width=None,
        *,
        animation=None,
        active_effect_duration: float = 0.2,
    ):
        super().__init__(x, y, style)  # hover state is opt-in (set mouse_moves=True)
        self.text = text
        self.width = width
        self.animation = animation
        self.active_effect_duration = active_effect_duration
        self._active = False
        self._active_time = 0.0
        self._hovered = False

    def _width(self):
        return max(self.width or 0, len(self.text) + 4, 8)

    def natural_width(self, scale):
        return self._width()

    def contains(self, col: int, row: int) -> bool:
        return self.abs_x <= col < self.abs_x + self._width() and self.abs_y == row

    def _activate(self):
        """Start the active effect and fire the click (cf. Textual's press())."""
        if self.active_effect_duration > 0:
            self._active = True
            self._active_time = time.monotonic()
        self._fire_click()

    def on_key(self, key):
        if key in (Key.ENTER, " "):
            self._activate()

    def on_mouse_click(self, col=None, row=None):
        self._activate()

    def on_mouse_enter(self):
        self._hovered = True
        self._fire_enter()

    def on_mouse_leave(self):
        self._hovered = False
        self._fire_leave()

    def draw(self, canvas):
        # Retire the active effect once its duration has elapsed.
        if self._active and time.monotonic() - self._active_time >= self.active_effect_duration:
            self._active = False

        is_focused = canvas.focused is self
        w = self._width()
        raw_bg = self.style.raw_bg
        fg = self.style.fg or "white"

        label = self.text.center(w)

        if is_focused:
            fg_c, bg_c, styles = raw_bg or "black", fg, ["bold"]
        elif self._hovered:
            fg_c, bg_c, styles = fg, raw_bg, ["bold"]  # subtle lift
        else:
            fg_c, bg_c, styles = fg, raw_bg, []

        if self._active:
            # Tint the whole button toward the screen background (Textual's
            # -active effect), producing a brief "pressed-in" darkening.
            screen_bg = canvas.style.bg
            if screen_bg and screen_bg.endswith("_bg"):
                screen_bg = screen_bg[:-3]
            fg_c = tint(fg_c, screen_bg, self.ACTIVE_TINT)
            bg_c = tint(bg_c, screen_bg, self.ACTIVE_TINT) if bg_c else bg_c

        canvas.write(self.abs_x, self.abs_y, label, Style(fg=fg_c, bg=bg_c, styles=styles))

        # While the active effect plays, keep redrawing so it reverts on its own
        # even without other input.
        if self._active:
            request = getattr(canvas, "request_frame", None)
            if request is not None:
                request(self.active_effect_duration)

        # Animate the label text while active-idle (focused/hovered, not pressed).
        if self.animation is not None and (is_focused or self._hovered) and not self._active:
            start = self.abs_x + (w - len(self.text)) // 2
            base = Style(fg=fg, bg=raw_bg, styles=list(styles))
            for dx, _dy, ch, cell_style in self.animation.cells(self.text, base):
                canvas.write(start + dx, self.abs_y, ch, cell_style)
            request = getattr(canvas, "request_frame", None)
            if request is not None:
                request(self.animation.speed)
