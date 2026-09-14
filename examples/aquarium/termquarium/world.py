"""Day/night cycle and water temperature -- Phase 5's "aquarium conditions".

Not outside weather: the only thing that fluctuates is the tank itself. Both
mechanics are driven by the same continuous 0..1 fraction of progress through
the current day (the same "day" fish age by, and the daily tick fires on),
so they naturally stay in sync with each other without separately-tuned
schedules.
"""

from __future__ import annotations

import math

from .constants import (
    AFTERNOON_END,
    AFTERNOON_WATER_TEMP,
    COLD_TEMP_THRESHOLD,
    EVENING_WATER_TEMP,
    MORNING_END,
    MORNING_WATER_TEMP,
    NIGHT_END,
    NIGHT_START,
    NIGHT_WATER_TEMP,
)

# (representative fraction, temperature) for the midpoint of each phase
# band, in chronological order -- see compute_water_temperature().
_TEMPERATURE_ANCHORS = (
    (0.225, MORNING_WATER_TEMP),  # Morning midpoint (NIGHT_END..MORNING_END)
    (0.45, AFTERNOON_WATER_TEMP),  # Afternoon midpoint (MORNING_END..AFTERNOON_END)
    (0.675, EVENING_WATER_TEMP),  # Evening midpoint (AFTERNOON_END..NIGHT_START)
    (0.95, NIGHT_WATER_TEMP),  # Night midpoint (wraps across midnight)
)


def compute_time_of_day(elapsed_seconds: float, day_length_seconds: float) -> float:
    """Fraction (0..1) of the way through the current day. Wraps forever via
    modulo, so callers never need to track day boundaries explicitly."""
    if day_length_seconds <= 0:
        return 0.0
    return (elapsed_seconds % day_length_seconds) / day_length_seconds


def get_day_phase(fraction: float) -> str:
    """Morning / Afternoon / Evening / Night, for behavior gating and the
    status readout. Night wraps around the fraction=0 boundary (e.g.
    NIGHT_START=0.75 to NIGHT_END=0.15 spans midnight)."""
    if fraction >= NIGHT_START or fraction < NIGHT_END:
        return "Night"
    if fraction < MORNING_END:
        return "Morning"
    if fraction < AFTERNOON_END:
        return "Afternoon"
    return "Evening"


def day_night_curve(fraction: float) -> float:
    """1.0 at midday (fraction=0.5), -1.0 at midnight (fraction=0 or 1),
    smooth in between. The one continuous signal both water temperature and
    the background tint are derived from."""
    return math.cos(2 * math.pi * (fraction - 0.5))


def compute_water_temperature(fraction: float) -> float:
    """Piecewise-linear between each phase's own representative midpoint
    (_TEMPERATURE_ANCHORS) -- warmest in the Morning, coldest at Night's,
    cooling steadily across the day rather than peaking at midday. Still
    one continuous curve, not a coin flip, just shaped by four anchors
    instead of a single sinusoid. Wraps smoothly from Night's own midpoint
    back to Morning's across the 0/1 boundary."""
    anchors = _TEMPERATURE_ANCHORS
    wrapped = anchors[1:] + ((anchors[0][0] + 1.0, anchors[0][1]),)
    for (f0, t0), (f1, t1) in zip(anchors, wrapped):
        if f0 <= fraction <= f1:
            return t0 + (t1 - t0) * (fraction - f0) / (f1 - f0)
    # fraction is before the first anchor (0 <= fraction < anchors[0][0]) --
    # still warming up from the *previous* cycle's Night anchor.
    f0, t0 = anchors[-1][0] - 1.0, anchors[-1][1]
    f1, t1 = anchors[0]
    return t0 + (t1 - t0) * (fraction - f0) / (f1 - f0)


def night_blend(fraction: float) -> float:
    """0.0 at midday, 1.0 at midnight, smooth in between -- how far to
    lerp_color() the background from DAY_BG toward NIGHT_BG."""
    return (1.0 - day_night_curve(fraction)) / 2.0


def temperature_chill(temperature: float) -> float:
    """0.0 at EVENING_WATER_TEMP and above (still comfortable), 1.0 at
    COLD_TEMP_THRESHOLD and below (properly cold -- the same point
    Fish._effective_speed() turns sluggish at) -- a smooth "how chilly does
    the water feel right now" ramp for fish.py's Evening warming-up
    behavior. Deliberately anchored to the real cold threshold, not the
    day's peak warmth: an earlier version measured distance from Morning's
    own peak, which meant an ordinary, nowhere-near-cold Afternoon already
    produced a real (if small) chance to seek warmth -- confusing, since
    nothing about that temperature was actually cold. Anchoring here means
    Morning/Afternoon are always exactly 0.0, and the ramp itself only
    exists across Evening's own cooling stretch, right where the water is
    actually approaching COLD_TEMP_THRESHOLD."""
    comfortable = EVENING_WATER_TEMP
    cold = COLD_TEMP_THRESHOLD
    chill = (comfortable - temperature) / (comfortable - cold)
    return max(0.0, min(1.0, chill))
