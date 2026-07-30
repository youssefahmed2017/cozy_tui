from cozy_tui.ansi import resolve_rgb
from cozy_tui.clipboard import copy as _copy_to_clipboard
from cozy_tui.events import Key
from cozy_tui.style import Style, selection_style
from cozy_tui.theme import get_theme
from cozy_tui.widget import Widget

from .slider import Slider

_CHANNELS = ("R", "G", "B")
_HINT = "[Ctrl+E] copy HEX   [Ctrl+R] copy RGB"


class ColorPicker(Widget):
    """Three R/G/B sliders (0-255 each) plus live HEX/RGB readouts -- no
    swatch grid or palette picker, just sliders.

    Up/Down move which channel Left/Right/Home/End/PageUp/PageDown affect;
    clicking or dragging a row's own track (exactly like `Slider`) jumps that
    channel directly and makes it the active one. Ctrl+E/Ctrl+R copy the
    HEX/RGB text to the clipboard -- not Ctrl+H, which is indistinguishable
    from Backspace over raw terminal input (see `Key.BACKSPACE`); both Ctrl+E
    and Ctrl+R are otherwise unused single-byte control codes.

    A single self-contained focusable widget, not three separately-focusable
    `Slider`s: cozy_tui routes a keystroke to exactly one focused widget with
    no bubbling (`App._dispatch_input`), so the copy shortcuts need to work no
    matter which channel is "active" -- they couldn't if each channel's
    Slider held focus on its own. Each channel still gets a real `Slider`
    internally for its value/clamp/step math (so that logic isn't re-derived
    three times); only drawing is done here, since `Slider.draw()`'s own
    focus highlight assumes it's the canvas's actual focused widget, which
    these child sliders never are.
    """

    focusable = True
    # PageUp/PageDown are otherwise intercepted by App._dispatch_input to
    # scroll the base UI unless the focused widget opts in (same marker
    # ScrollView/Table/BarChart use) -- this widget wants them for the active
    # channel's big-step instead.
    scrollable = True

    def __init__(
        self,
        x,
        y,
        color=(255, 255, 255),
        *,
        width=16,
        step=1,
        page_step=16,
        on_change=None,
        style=None,
    ):
        super().__init__(x, y, style)
        self._sliders = [
            Slider(
                0,
                i,
                0,
                255,
                value=v,
                step=step,
                page_step=page_step,
                width=width,
                style=self.style,
            )
            for i, v in enumerate(self._coerce(color))
        ]
        for i, slider in enumerate(self._sliders):
            slider.parent = self
            slider.on_change(lambda _v, i=i: self._on_channel_change(i))
        self._channel = 0
        self._copy_handler = None
        if on_change is not None:
            self.on_change(on_change)

    # ── public API ───────────────────────────────────────────────────────────

    @property
    def rgb(self):
        return tuple(s.get() for s in self._sliders)

    @property
    def hex(self) -> str:
        r, g, b = self.rgb
        return f"#{r:02x}{g:02x}{b:02x}"

    def set_rgb(self, color) -> None:
        for slider, v in zip(self._sliders, self._coerce(color)):
            slider.set(v)

    def on_copy(self, func):
        """Register a callback invoked after Ctrl+E/Ctrl+R copies to the
        clipboard. Receives ``(kind, text)`` -- ``kind`` is "hex" or "rgb"."""
        self._copy_handler = func
        return self

    # ── internals ────────────────────────────────────────────────────────────

    @staticmethod
    def _coerce(color):
        if isinstance(color, str):
            rgb = resolve_rgb(color)
            if rgb is None:
                raise ValueError(f"Unrecognized color: {color!r}")
            return rgb
        r, g, b = color
        return int(r), int(g), int(b)

    def _on_channel_change(self, i: int) -> None:
        self._channel = i
        self._fire_change(self.rgb)

    def _fire_copy(self, kind: str, text: str) -> None:
        if self._copy_handler:
            self._copy_handler(kind, text)

    def _copy(self, *, as_hex: bool) -> None:
        text = self.hex if as_hex else ", ".join(str(v) for v in self.rgb)
        _copy_to_clipboard(text)
        self._fire_copy("hex" if as_hex else "rgb", text)

    # ── Widget interface ─────────────────────────────────────────────────────

    def natural_width(self, scale) -> int:
        slider_row = 2 + self._sliders[0].width  # "R " prefix + the slider's row
        hex_row = len("HEX: #ffffff")
        rgb_row = len("RGB: (255, 255, 255)")  # worst case, not the live value
        return max(slider_row, hex_row, rgb_row, len(_HINT))

    def natural_height(self, scale) -> int:
        return 7  # 3 sliders + a blank row + HEX + RGB + the shortcut hint

    def contains(self, col: int, row: int) -> bool:
        return self.abs_x <= col < self.abs_x + self.natural_width(
            1
        ) and self.abs_y <= row < self.abs_y + self.natural_height(1)

    def on_key(self, key) -> None:
        if key == Key.UP:
            self._channel = max(0, self._channel - 1)
        elif key == Key.DOWN:
            self._channel = min(2, self._channel + 1)
        elif key == Key.ctrl("e"):
            self._copy(as_hex=True)
        elif key == Key.CTRL_R:
            self._copy(as_hex=False)
        else:
            self._sliders[self._channel].on_key(key)

    def on_mouse_click(self, col=None, row=None) -> None:
        if row is None:
            return
        i = row - self.abs_y
        if 0 <= i < 3:
            self._channel = i
            self._sliders[i].on_mouse_click(col, row)

    def on_mouse_drag(self, col=None, row=None) -> None:
        self._sliders[self._channel].on_mouse_drag(col, row)
        self._fire_drag(col, row)

    def draw(self, canvas) -> None:
        is_focused = canvas.focused is self
        fg = self.style.fg or "white"
        raw_bg = self.style.raw_bg
        plain = Style(fg=fg, bg=raw_bg)
        label_style = Style(fg=fg, bg=raw_bg, styles=["bold"])
        muted = Style(fg=get_theme().muted, bg=raw_bg)

        for i, slider in enumerate(self._sliders):
            row_y = self.abs_y + i
            canvas.write(self.abs_x, row_y, f"{_CHANNELS[i]} ", label_style)

            bar_w = slider._bar_width()
            handle = slider._handle_pos(bar_w)
            active = is_focused and i == self._channel
            handle_style = selection_style() if active else label_style
            bx = self.abs_x + 2
            bar = ("━" * handle) + "●" + ("─" * (bar_w - handle - 1))
            canvas.write(bx, row_y, bar, plain)
            canvas.write(bx + handle, row_y, "●", handle_style)
            if slider.show_value:
                text = slider._fmt(slider.get()).rjust(slider._label_w)
                canvas.write(bx + bar_w + 1, row_y, text, plain)

        r, g, b = self.rgb
        color_style = Style(fg=f"rgb({r},{g},{b})", bg=raw_bg, styles=["bold"])
        canvas.write(self.abs_x, self.abs_y + 4, f"HEX: {self.hex}", color_style)
        canvas.write(self.abs_x, self.abs_y + 5, f"RGB: ({r}, {g}, {b})", color_style)
        canvas.write(self.abs_x, self.abs_y + 6, _HINT, muted)
