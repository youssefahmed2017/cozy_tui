import colorsys
import math
import time

from cozy_tui.style import Style
from cozy_tui.widget import Widget


class Animation:
    """Base class for :class:`AnimatedLabel` animations.

    An animation turns the label's text into a stream of positioned, styled
    glyphs. Subclasses implement :meth:`cells`; the base provides frame timing.

    ``vertical_span`` is how many extra rows below the baseline the effect can
    occupy (0 for purely color animations), so the label can size itself.
    """

    vertical_span: int = 0

    def __init__(self, speed: float = 0.06):
        self.speed = speed
        self._start = time.monotonic()

    def frame(self) -> int:
        """Current integer frame index, advancing by 1 every ``speed`` seconds."""
        return int((time.monotonic() - self._start) / self.speed)

    def cells(self, text: str, style: Style):
        """Yield ``(dx, dy, char, cell_style)`` for each glyph of *text*, where
        ``dx``/``dy`` are cell offsets from the label's top-left origin."""
        raise NotImplementedError


class GlowAnimation(Animation):
    """Cycles a color gradient across each character of an AnimatedLabel.

    Args:
        colors: List of hex color strings, e.g. ["#ff8c00", "#ffcc44"].
        color_template: Name of a built-in gradient ("orange", "blue",
            "green", "red", "purple").  Mutually exclusive with *colors*.
        speed: Seconds between frame steps.  Lower = faster.
    """

    # Each template follows the same wave pattern as the original mouse_debug.py
    # COLORS list: a fixed primary channel, one or two channels ramping up then
    # back down in steps of 10, peak duplicated — 18 colours total.
    _TEMPLATES: dict[str, list[str]] = {
        # R=255, G: 140→220→140, B: 0→80→0  (from mouse_debug.py verbatim)
        "orange": [
            "#ff8c00",
            "#ff960a",
            "#ffa014",
            "#ffaa1e",
            "#ffb428",
            "#ffbe32",
            "#ffc83c",
            "#ffd246",
            "#ffdc50",
            "#ffdc50",
            "#ffd246",
            "#ffc83c",
            "#ffbe32",
            "#ffb428",
            "#ffaa1e",
            "#ffa014",
            "#ff960a",
            "#ff8c00",
        ],
        # B=255, G: 80→200→80 (step 15), R=0
        "blue": [
            "#0050ff",
            "#005fff",
            "#006eff",
            "#007dff",
            "#008cff",
            "#009bff",
            "#00aaff",
            "#00b9ff",
            "#00c8ff",
            "#00c8ff",
            "#00b9ff",
            "#00aaff",
            "#009bff",
            "#008cff",
            "#007dff",
            "#006eff",
            "#005fff",
            "#0050ff",
        ],
        # R=0, G: 160→240→160, B: 40→120→40  (step 10)
        "green": [
            "#00a028",
            "#00aa32",
            "#00b43c",
            "#00be46",
            "#00c850",
            "#00d25a",
            "#00dc64",
            "#00e66e",
            "#00f078",
            "#00f078",
            "#00e66e",
            "#00dc64",
            "#00d25a",
            "#00c850",
            "#00be46",
            "#00b43c",
            "#00aa32",
            "#00a028",
        ],
        # R=255, G: 0→80→0, B=0  (step 10)
        "red": [
            "#ff0000",
            "#ff0a00",
            "#ff1400",
            "#ff1e00",
            "#ff2800",
            "#ff3200",
            "#ff3c00",
            "#ff4600",
            "#ff5000",
            "#ff5000",
            "#ff4600",
            "#ff3c00",
            "#ff3200",
            "#ff2800",
            "#ff1e00",
            "#ff1400",
            "#ff0a00",
            "#ff0000",
        ],
        # B=255, R: 140→220→140, G=0  (step 10)
        "purple": [
            "#8c00ff",
            "#9600ff",
            "#a000ff",
            "#aa00ff",
            "#b400ff",
            "#be00ff",
            "#c800ff",
            "#d200ff",
            "#dc00ff",
            "#dc00ff",
            "#d200ff",
            "#c800ff",
            "#be00ff",
            "#b400ff",
            "#aa00ff",
            "#a000ff",
            "#9600ff",
            "#8c00ff",
        ],
    }

    def __init__(
        self,
        *,
        colors: list[str | tuple[int, int, int]] | None = None,
        color_template: str | None = None,
        speed: float = 0.06,
    ):
        if color_template is not None:
            if color_template not in self._TEMPLATES:
                raise ValueError(
                    f"Unknown color_template {color_template!r}. "
                    f"Available: {list(self._TEMPLATES)}"
                )
            hex_colors = self._TEMPLATES[color_template]
        elif colors:
            hex_colors = list(colors)
        else:
            raise ValueError("Provide either colors or color_template.")

        super().__init__(speed)
        self._colors: list[tuple[int, int, int]] = [
            c if isinstance(c, tuple) else self._hex_to_rgb(c) for c in hex_colors
        ]

    @property
    def colors(self) -> list[tuple[int, int, int]]:
        return self._colors

    @staticmethod
    def _hex_to_rgb(color: str) -> tuple[int, int, int]:
        h = color.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def cells(self, text, style):
        colors = self._colors
        n = len(colors)
        frame = self.frame()
        raw_bg = style.raw_bg
        extra = list(style.styles)
        for i, ch in enumerate(text):
            r, g, b = colors[(frame + i) % n]
            yield i, 0, ch, Style(fg=f"rgb({r},{g},{b})", bg=raw_bg, styles=extra)


class RainbowAnimation(Animation):
    """A full-spectrum hue that sweeps along the text and scrolls over time.

    Unlike :class:`GlowAnimation` (a fixed palette cycled across the glyphs),
    this walks the whole HSV colour wheel: adjacent characters are ``spread``
    degrees apart in hue and the whole rainbow rotates ``6°`` per frame.

    Args:
        spread: Hue degrees between adjacent characters (wider = more colours
            visible at once).
        saturation, value: HSV saturation/brightness, ``0.0``–``1.0``.
        speed: Seconds between frames.
    """

    def __init__(
        self,
        *,
        spread: float = 18.0,
        saturation: float = 1.0,
        value: float = 1.0,
        speed: float = 0.06,
    ):
        super().__init__(speed)
        self.spread = spread
        self.saturation = saturation
        self.value = value

    def cells(self, text, style):
        frame = self.frame()
        raw_bg = style.raw_bg
        extra = list(style.styles)
        for i, ch in enumerate(text):
            hue = ((frame * 6) + i * self.spread) % 360
            r, g, b = colorsys.hsv_to_rgb(hue / 360, self.saturation, self.value)
            fg = f"rgb({int(r * 255)},{int(g * 255)},{int(b * 255)})"
            yield i, 0, ch, Style(fg=fg, bg=raw_bg, styles=extra)


class LevitateAnimation(Animation):
    """A vertical bobbing effect — the text floats up and down on a sine wave.

    Two modes:
        ``"word"``  the whole text rises and falls as one block.
        ``"char"``  each character is phase-shifted, giving a travelling wave.

    Colour is left untouched (the label's own style is used), so this composes
    with any foreground/background you set.

    Args:
        mode: ``"word"`` or ``"char"``.
        amplitude: Peak rise in cells; the text travels ``0``–``2*amplitude``.
        phase: Per-character phase shift in ``"char"`` mode (radians).
        rate: Angular speed of the wave per frame.
        speed: Seconds between frames.
    """

    def __init__(
        self,
        *,
        mode: str = "char",
        amplitude: int = 4,
        phase: float = 0.6,
        rate: float = 0.15,
        speed: float = 0.03,
    ):
        if mode not in ("word", "char"):
            raise ValueError(f"mode must be 'word' or 'char', got {mode!r}")
        super().__init__(speed)
        self.mode = mode
        self.amplitude = amplitude
        self.phase = phase
        self.rate = rate
        self.vertical_span = amplitude * 2  # travels 0..2*amplitude

    def cells(self, text, style):
        frame = self.frame()
        for i, ch in enumerate(text):
            if self.mode == "word":
                offset = int((math.sin(frame * self.rate) + 1) * self.amplitude)
            else:
                angle = frame * self.rate + i * self.phase
                offset = round((math.sin(angle) + 1) * self.amplitude)
            yield i, offset, ch, style


class AnimatedLabel(Widget):
    """A single-row label whose text characters are colored by an animation.

    Example::

        label = AnimatedLabel(2, 2, "Working...",
                              animation=GlowAnimation(color_template="orange",
                                                      speed=0.08))
        app.add(label)
        app.tick_interval = 0.05  # refresh fast enough to see the animation
    """

    def __init__(self, x, y, text: str, *, animation: Animation, style=None):
        super().__init__(x, y, style)
        self.text = text
        self.animation = animation

    def natural_width(self, scale) -> int:
        return len(self.text)

    def natural_height(self, scale) -> int:
        # Motion animations (e.g. Levitate) occupy extra rows below the baseline.
        return 1 + self.animation.vertical_span

    def contains(self, col: int, row: int) -> bool:
        h = self.natural_height(1)
        return (
            self.abs_x <= col < self.abs_x + len(self.text)
            and self.abs_y <= row < self.abs_y + h
        )

    def draw(self, canvas) -> None:
        for dx, dy, ch, style in self.animation.cells(self.text, self.style):
            canvas.write(self.abs_x + dx, self.abs_y + dy, ch, style)

        # Keep the loop redrawing so the animation advances even without input
        # and without the app configuring tick_interval.
        request = getattr(canvas, "request_frame", None)
        if request is not None:
            request(self.animation.speed)
