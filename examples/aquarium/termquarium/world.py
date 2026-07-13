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
    BASE_WATER_TEMP,
    MORNING_END,
    NIGHT_END,
    NIGHT_START,
    WATER_TEMP_SWING,
)


def compute_time_of_day(elapsed_seconds: float, day_length_seconds: float) -> float:
    """Fraction (0..1) of the way through the current day. Wraps forever via
    modulo, so callers never need to track day boundaries explicitly."""
    if day_length_seconds <= 0:
        return 0.0
    return (elapsed_seconds % day_length_seconds) / day_length_seconds


def get_day_phase(fraction: float) -> str:
    """Night / Morning / Day, for behavior gating and the status readout.
    Night wraps around the fraction=0 boundary (e.g. NIGHT_START=0.75 to
    NIGHT_END=0.15 spans midnight)."""
    if fraction >= NIGHT_START or fraction < NIGHT_END:
        return "Night"
    if fraction < MORNING_END:
        return "Morning"
    return "Day"


def day_night_curve(fraction: float) -> float:
    """1.0 at midday (fraction=0.5), -1.0 at midnight (fraction=0 or 1),
    smooth in between. The one continuous signal both water temperature and
    the background tint are derived from."""
    return math.cos(2 * math.pi * (fraction - 0.5))


def compute_water_temperature(fraction: float) -> float:
    """Warmest at midday, coolest at night -- a smooth curve, not a coin
    flip, so it reads as "the tank" rather than a randomized stat."""
    return BASE_WATER_TEMP + WATER_TEMP_SWING * day_night_curve(fraction)


def night_blend(fraction: float) -> float:
    """0.0 at midday, 1.0 at midnight, smooth in between -- how far to
    lerp_color() the background from DAY_BG toward NIGHT_BG."""
    return (1.0 - day_night_curve(fraction)) / 2.0
