import time

from cozy_tui.style import Style
from cozy_tui.widget import Widget


class GlowAnimation:
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

        self._colors: list[tuple[int, int, int]] = [
            c if isinstance(c, tuple) else self._hex_to_rgb(c) for c in hex_colors
        ]
        self.speed = speed
        self._start = time.monotonic()

    @property
    def colors(self) -> list[tuple[int, int, int]]:
        return self._colors

    def frame(self) -> int:
        """Current integer frame index, advancing by 1 every *speed* seconds."""
        return int((time.monotonic() - self._start) / self.speed)

    @staticmethod
    def _hex_to_rgb(color: str) -> tuple[int, int, int]:
        h = color.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class AnimatedLabel(Widget):
    """A single-row label whose text characters are colored by an animation.

    Example::

        label = AnimatedLabel(2, 2, "Working...",
                              animation=GlowAnimation(color_template="orange",
                                                      speed=0.08))
        app.add(label)
        app.tick_interval = 0.05  # refresh fast enough to see the animation
    """

    def __init__(self, x, y, text: str, *, animation: GlowAnimation, style=None):
        super().__init__(x, y, style)
        self.text = text
        self.animation = animation

    def natural_width(self, scale) -> int:
        return len(self.text)

    def contains(self, col: int, row: int) -> bool:
        return self.abs_x <= col < self.abs_x + len(self.text) and row == self.abs_y

    def draw(self, canvas) -> None:
        colors = self.animation.colors
        frame = self.animation.frame()
        n = len(colors)
        # Preserve the widget's background; strip the _bg suffix so Style()
        # can re-apply it correctly.
        raw_bg = self.style.bg
        if raw_bg and raw_bg.endswith("_bg"):
            raw_bg = raw_bg[:-3]
        extra_styles = list(self.style.styles)

        for i, ch in enumerate(self.text):
            r, g, b = colors[(frame + i) % n]
            style = Style(fg=f"rgb({r},{g},{b})", bg=raw_bg, styles=extra_styles)
            canvas.write(self.abs_x + i, self.abs_y, ch, style)
