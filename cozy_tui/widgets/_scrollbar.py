"""The shared thin, auto-hiding vertical scrollbar drawn by ScrollView and
BarChart (any widget that scrolls its content vertically).

It's a slim right-edge bar -- a right-half-block thumb over a barely-there
right-eighth track -- that rides at full strength for ``HOLD`` seconds after a
scroll, then fades over ``FADE`` toward a faint idle floor (``IDLE``). It never
vanishes completely, so its position stays readable and it's always there to
grab. Timing is read off :func:`cozy_tui.motion.now`, so the test Harness's
virtual clock drives the fade the same way ``advance()`` drives every other
animation here."""

from cozy_tui.ansi import tint
from cozy_tui.motion import now
from cozy_tui.style import Style

THUMB = "▐"  # right half block: a slim bar hugging the right edge
TRACK = "▕"  # right one-eighth block: a faint sliver

HOLD = 1.2  # seconds at full strength after a scroll
FADE = 0.5  # seconds to ease down to the idle floor
IDLE = 0.18  # opacity the thumb rests at when idle (never fully gone)


def opacity(activity: float) -> float:
    """The thumb's opacity given the time of the last scroll (``activity``)."""
    age = now() - activity
    if age <= HOLD:
        return 1.0
    if age >= HOLD + FADE:
        return IDLE
    return 1.0 - (1.0 - IDLE) * ((age - HOLD) / FADE)


def draw(canvas, col, top, vh, content_h, disp, max_scroll, accent, raw_bg, activity):
    """Paint the bar in column ``col``, rows ``top .. top+vh``. ``disp`` is the
    current (possibly eased) scroll offset, ``content_h`` the full content
    height. Requests frames while the fade is in flight so it animates rather
    than snapping, then lets the loop go back to sleep."""
    thumb = max(1, min(vh, round(vh * vh / content_h)))
    span = vh - thumb
    pos = round(span * (disp / max_scroll)) if max_scroll else 0

    op = opacity(activity)
    age = now() - activity
    if age < HOLD + FADE:
        canvas.request_frame(max(0.02, HOLD - age) if op >= 1.0 else 0.05)

    thumb_style = Style(fg=tint(accent, raw_bg, 1.0 - op), bg=raw_bg)
    track_style = Style(fg=tint("bright_black", raw_bg, 0.45), bg=raw_bg)
    for r in range(vh):
        on_thumb = pos <= r < pos + thumb
        canvas.write(
            col,
            top + r,
            THUMB if on_thumb else TRACK,
            thumb_style if on_thumb else track_style,
        )
