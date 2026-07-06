"""Reusable motion primitives: easing curves, value/colour interpolation, and a
self-timing ``Tween``.

Animations in a cell grid come in two flavours: **position** (quantised to whole
cells, kept smooth by a high redraw rate + easing) and **colour** (genuinely
smooth, since RGB has fine gradation). This module supplies both.

A widget animates by holding a :class:`Tween` and, from its ``draw``, reading
``tween.value()`` and calling ``canvas.request_frame(...)`` until ``tween.done``::

    self._t = Tween(0, 1, 0.15, ease_out)
    ...
    v = self._t.value()
    if not self._t.done:
        canvas.request_frame(0.033)
"""

import time

__all__ = [
    "linear", "ease_in", "ease_out", "ease_in_out", "ease_out_quad",
    "lerp", "lerp_color", "Tween",
]


# ── easing curves (t and the return value are both in [0, 1]) ────────────────────


def linear(t):
    return t


def ease_in(t):
    return t * t * t


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_quad(t):
    return 1 - (1 - t) * (1 - t)


# ── interpolation ────────────────────────────────────────────────────────────


def lerp(a, b, t):
    """Linear interpolation from ``a`` to ``b`` by fraction ``t``."""
    return a + (b - a) * t


# The standard 16 ANSI colours (matching cozy_tui.ansi's downgrade table) so
# named colours can be interpolated too.
_NAMED = {
    "black": (0, 0, 0), "red": (128, 0, 0), "green": (0, 128, 0),
    "yellow": (128, 128, 0), "blue": (0, 0, 128), "magenta": (128, 0, 128),
    "cyan": (0, 128, 128), "white": (192, 192, 192),
    "bright_black": (128, 128, 128), "gray": (128, 128, 128), "grey": (128, 128, 128),
    "bright_red": (255, 0, 0), "bright_green": (0, 255, 0),
    "bright_yellow": (255, 255, 0), "bright_blue": (0, 0, 255),
    "bright_magenta": (255, 0, 255), "bright_cyan": (0, 255, 255),
    "bright_white": (255, 255, 255),
}


def _to_rgb(color):
    """Parse ``(r, g, b)`` / ``"#rrggbb"`` / ``"#rgb"`` / ``"rgb(r,g,b)"`` / a named
    ANSI colour into an ``(r, g, b)`` int tuple."""
    if isinstance(color, (tuple, list)) and len(color) == 3:
        return tuple(int(c) for c in color)
    if isinstance(color, str):
        s = color.strip()
        if s in _NAMED:
            return _NAMED[s]
        if s.startswith("#"):
            h = s[1:]
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            if len(h) == 6:
                return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        elif s.startswith("rgb(") and s.endswith(")"):
            parts = [int(p) for p in s[4:-1].split(",")]
            if len(parts) == 3:
                return tuple(parts)
    raise ValueError(f"can't interpolate colour {color!r} (use rgb/hex/named)")


def lerp_color(c0, c1, t):
    """Interpolate between two colours (rgb tuple, ``#hex``, or ``rgb(...)``) and
    return an ``"rgb(r,g,b)"`` string that :class:`~cozy_tui.style.Style` accepts."""
    r0, g0, b0 = _to_rgb(c0)
    r1, g1, b1 = _to_rgb(c1)
    r = round(lerp(r0, r1, t))
    g = round(lerp(g0, g1, t))
    b = round(lerp(b0, b1, t))
    return f"rgb({r},{g},{b})"


# ── tween ──────────────────────────────────────────────────────────────────────


class Tween:
    """Eases a scalar from ``start`` to ``end`` over ``duration`` seconds, timed off
    a wall clock so it needs no external ticking — read :meth:`value` each frame."""

    def __init__(self, start, end, duration, easing=ease_out):
        self.start = float(start)
        self.end = float(end)
        self.duration = max(0.0, float(duration))
        self.easing = easing
        self._t0 = time.monotonic()

    def progress(self):
        """Raw (un-eased) progress in ``[0, 1]``."""
        if self.duration <= 0:
            return 1.0
        return min(1.0, (time.monotonic() - self._t0) / self.duration)

    def value(self):
        """The current eased value between ``start`` and ``end``."""
        return self.start + (self.end - self.start) * self.easing(self.progress())

    @property
    def done(self):
        return self.progress() >= 1.0

    def restart(self, start=None, end=None, duration=None):
        """Retarget and restart the clock. Handy for re-aiming an in-flight tween
        (e.g. scrolling further before the last scroll settled)."""
        if start is not None:
            self.start = float(start)
        if end is not None:
            self.end = float(end)
        if duration is not None:
            self.duration = max(0.0, float(duration))
        self._t0 = time.monotonic()
        return self
