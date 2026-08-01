import colorsys
import math
import time
import random
import sys
from typing import Iterator, Tuple, Optional, List

from cozy_tui.markup import render
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

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} speed={self.speed!r}>"

    def frame(self, now: Optional[float] = None) -> int:
        """Current integer frame index, advancing by 1 every ``speed`` seconds.

        Optional *now* can be provided (a monotonic timestamp) so callers can
        compute a single timestamp per draw and pass it through to keep all
        animations in a single frame consistent.
        """
        if now is None:
            now = time.monotonic()
        return int((now - self._start) / self.speed)

    def cells(self, text: str, style: Style) -> Iterator[Tuple[int, int, str, Style]]:
        """Yield ``(dx, dy, char, cell_style)`` for each glyph of *text*, where
        ``dx``/``dy`` are cell offsets from the label's top-left origin."""
        raise NotImplementedError


ZALGO_UP = ['̍', '̎', '̄', '̅', '̿', '̑', '̆', '̐', '͒', '͗', '͑', '̇', '̈', '̊', '͂', '̓', '̈́', '͊', '͋', '͌', '̃',
            '̂', '̌', '͐', '̀', '́', '̋', '̏', '̽', '̾', '͛', '͆', '̚']
ZALGO_MID = ['̕', '̛', '̀', '́', '͘', '̡', '̢', '̧', '̨', '̴', '̵', '̶', '͜', '͝', '͞', '͟', '͠', '͢', '̸', '̷', '͡']
ZALGO_DOWN = ['̖', '̗', '̘', '̙', '̜', '̝', '̞', '̟', '̠', '̤', '̥', '̦', '̩', '̪', '̫', '̬', '̭', '̮', '̯', '̰', '̱',
              '̲', '̳', '̹', '̺', '̻', '̼', 'ͅ', '͇', '͈', '͉', '͍', '͎', '͓', '͔', '͕', '͖', '͙', '͚', '̣']


class GlitchAnimation(Animation):
    """Zalgo-style glitch — stacks combining diacritics on each character.
    WARNING: May not work in non-Zalgo supported terminals
    """

    def __init__(self, *, intensity: int = 3, speed: float = 0.08):
        super().__init__(speed)
        self.intensity = intensity  # how many diacritics per char

    def cells(self, text: str, style: Style) -> Iterator[Tuple[int, int, str, Style]]:
        frame = self.frame()
        for i, ch in enumerate(text):
            if ch == " ":
                yield i, 0, ch, style
                continue

            rng = random.Random(frame * 997 + i * 131)

            glitched = ch
            glitched += "".join(
                rng.choice(ZALGO_UP)
                for _ in range(rng.randint(0, self.intensity))
            )
            glitched += "".join(
                rng.choice(ZALGO_MID)
                for _ in range(rng.randint(0, self.intensity))
            )
            glitched += "".join(
                rng.choice(ZALGO_DOWN)
                for _ in range(rng.randint(0, self.intensity))
            )

            yield i, 0, glitched, style


class TypewriterAnimation(Animation):
    """Types through a list of phrases, erasing and retyping each one.

    Args:
        phrases:   List of strings to cycle through.
        speed:     Seconds between each character add/remove.
        pause:     Frames to hold the fully-typed phrase before erasing.
        cursor:    Show the terminal cursor blinking at the typing position.
        cursor_output: optional file-like object to write cursor show/hide
            escape sequences to (default sys.stdout). Pass None to suppress
            printing entirely (useful for tests/headless).
    """

    vertical_span: int = 0

    # Cursor blink via ANSI — show/hide the real terminal cursor
    _SHOW = "\033[?25h"
    _HIDE = "\033[?25l"

    def __init__(
        self,
        phrases: List[str],
        *,
        speed: float = 0.08,
        pause: int = 15,
        cursor: bool = True,
        cursor_output: Optional[object] = sys.stdout,
    ):
        super().__init__(speed)
        self.phrases = phrases
        self.pause = pause
        self.cursor = cursor
        self._cursor_hidden = False
        # allow callers (tests) to disable/redirect the escape sequence output
        self.cursor_output = cursor_output

    def _current(self, frame: int):
        """Return (text, visible_count, state) for the current frame."""
        f = frame
        idx = 0

        while True:
            text = self.phrases[idx % len(self.phrases)]
            total = len(text)
            # one full cycle: type in + pause + type out
            cycle = total + self.pause + total

            if f < cycle:
                if f < total:
                    # typing in
                    return text, f + 1, "typing_in"
                elif f < total + self.pause:
                    # holding
                    return text, total, "pausing"
                else:
                    # typing out
                    gone = f - total - self.pause
                    return text, max(0, total - gone), "typing_out"

            f -= cycle
            idx += 1

    def _write_cursor_seq(self, seq: str) -> None:
        if self.cursor_output is not None:
            try:
                # file-like objects (stdout) support write/flush
                self.cursor_output.write(seq)
                try:
                    self.cursor_output.flush()
                except Exception:
                    pass
            except Exception:
                # best-effort: don't let cursor output failures break the app
                pass

    def _hide_cursor(self) -> None:
        if not self._cursor_hidden:
            self._write_cursor_seq(self._HIDE)
            self._cursor_hidden = True

    def _show_cursor(self) -> None:
        if self._cursor_hidden:
            self._write_cursor_seq(self._SHOW)
            self._cursor_hidden = False

    def cells(self, text_hint: str, style: Style) -> Iterator[Tuple[int, int, str, Style]]:
        frame = self.frame()
        text, visible, state = self._current(frame)

        # cursor management
        if self.cursor:
            if state in ("typing_in", "typing_out"):
                self._hide_cursor()
            else:
                self._show_cursor()

        # yield visible characters
        for i, ch in enumerate(text[:visible]):
            yield i, 0, ch, style

        # fake cursor block at end of visible text
        # only shown while actively typing (not during pause — real cursor handles that)
        if self.cursor and state in ("typing_in", "typing_out"):
            cursor_char = "▏"
            # blink: on for 6 frames, off for 6 frames
            blink_on = (frame // 6) % 2 == 0
            if blink_on:
                yield visible, 0, cursor_char, style

    def __del__(self):
        """Always restore the terminal cursor on cleanup — best-effort, silence errors."""
        try:
            # May be called during interpreter shutdown; guard aggressively.
            self._write_cursor_seq(self._SHOW)
        except Exception:
            pass


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
        colors: Optional[List[str | Tuple[int, int, int]]] = None,
        color_template: Optional[str] = None,
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
        self._colors: List[Tuple[int, int, int]] = [
            c if isinstance(c, tuple) else self._hex_to_rgb(c) for c in hex_colors
        ]

    @property
    def colors(self) -> List[Tuple[int, int, int]]:
        return self._colors

    @staticmethod
    def _hex_to_rgb(color: str) -> Tuple[int, int, int]:
        h = color.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def cells(self, text: str, style: Style) -> Iterator[Tuple[int, int, str, Style]]:
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

    def cells(self, text: str, style: Style) -> Iterator[Tuple[int, int, str, Style]]:
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

    def cells(self, text: str, style: Style) -> Iterator[Tuple[int, int, str, Style]]:
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

    def __init__(
        self, x, y, text: str, *, animation: Animation, markup: bool = False, style=None
    ):
        super().__init__(x, y, style)
        self.text = text
        self.animation = animation
        self.markup = markup
        self._markup_key = None
        self._plain = ""
        self._char_styles: list = []

    def _sync(self) -> None:
        # Use a hashable key (tuple) — style.styles may be a list, so convert.
        key = (self.text, self.style.fg, self.style.bg, tuple(self.style.styles))
        if self._markup_key == key:
            return
        self._markup_key = key
        runs = render(self.text, self.style)
        self._plain = "".join(t for t, _s in runs)
        # One style per character, so the animation's per-glyph output can be
        # merged against whatever tag that glyph sits inside.
        self._char_styles = [s for text, s in runs for _ in text]

    def _visible(self) -> str:
        if not self.markup:
            return self.text
        self._sync()
        return self._plain

    def natural_width(self, scale) -> int:
        return len(self._visible())

    def natural_height(self, scale) -> int:
        # Motion animations (e.g. Levitate) occupy extra rows below the baseline.
        return 1 + self.animation.vertical_span

    def contains(self, col: int, row: int) -> bool:
        h = self.natural_height(1)
        return (
            self.abs_x <= col < self.abs_x + len(self._visible())
            and self.abs_y <= row < self.abs_y + h
        )

    def _merge(self, animated: Style, tag: Style) -> Style:
        """Combine one animation cell's style with the markup style its
        character sits inside.

        The animation keeps the foreground **only if it actually chose one** —
        i.e. changed it from the base it was handed. Color animations
        (:class:`GlowAnimation`, :class:`RainbowAnimation`) do; motion ones
        (:class:`LevitateAnimation`) pass the base through untouched, and there
        the tag's color is what the author meant. Background and attributes
        always come from the tag, since no built-in animation sets them.
        """
        fg = animated.fg if animated.fg != self.style.fg else tag.fg
        return Style(fg=fg, bg=tag.raw_bg, styles=tag.styles)

    def draw(self, canvas) -> None:
        text = self._visible()
        # Let the animation decide a consistent frame itself; we could also
        # compute now=time.monotonic() once and pass into animation.frame(now)
        # if needed to keep multiple animations in perfect sync.
        cells = self.animation.cells(text, self.style)
        if self.markup:
            styles = self._char_styles
            cells = (
                (dx, dy, ch, self._merge(st, styles[i]) if i < len(styles) else st)
                for i, (dx, dy, ch, st) in enumerate(cells)
            )
        for dx, dy, ch, style in cells:
            canvas.write(self.abs_x + dx, self.abs_y + dy, ch, style)

        # Keep the loop redrawing so the animation advances even without input
        # and without the app configuring tick_interval.
        request = getattr(canvas, "request_frame", None)
        if request is not None:
            request(self.animation.speed)

