"""Day/night cycle and water temperature (Phase 5) for the TermQuarium example."""

import math

from examples.aquarium.termquarium.constants import (
    BASE_WATER_TEMP,
    MORNING_END,
    NIGHT_END,
    NIGHT_START,
    WATER_TEMP_SWING,
)
from examples.aquarium.termquarium.world import (
    compute_time_of_day,
    compute_water_temperature,
    day_night_curve,
    get_day_phase,
    night_blend,
)


def test_compute_time_of_day_wraps_via_modulo():
    assert compute_time_of_day(0.0, 100.0) == 0.0
    assert compute_time_of_day(50.0, 100.0) == 0.5
    assert compute_time_of_day(150.0, 100.0) == 0.5  # wrapped into the next day
    assert compute_time_of_day(250.0, 100.0) == 0.5  # and the one after that


def test_compute_time_of_day_zero_length_day_is_zero():
    assert compute_time_of_day(50.0, 0.0) == 0.0


def test_get_day_phase_midday_is_day():
    assert get_day_phase(0.5) == "Day"


def test_get_day_phase_night_wraps_around_midnight():
    assert get_day_phase(NIGHT_START) == "Night"
    assert get_day_phase(0.99) == "Night"
    assert get_day_phase(0.0) == "Night"
    assert get_day_phase(NIGHT_END - 0.01) == "Night"


def test_get_day_phase_morning_is_between_night_and_day():
    assert get_day_phase(NIGHT_END) == "Morning"
    assert get_day_phase(MORNING_END - 0.01) == "Morning"


def test_get_day_phase_day_follows_morning():
    assert get_day_phase(MORNING_END) == "Day"
    assert get_day_phase(NIGHT_START - 0.01) == "Day"


def test_day_night_curve_peaks_at_midday_and_troughs_at_midnight():
    assert math.isclose(day_night_curve(0.5), 1.0)
    assert math.isclose(day_night_curve(0.0), -1.0, abs_tol=1e-9)
    assert math.isclose(day_night_curve(1.0), -1.0, abs_tol=1e-9)


def test_compute_water_temperature_warmest_at_midday():
    assert compute_water_temperature(0.5) == BASE_WATER_TEMP + WATER_TEMP_SWING


def test_compute_water_temperature_coolest_at_midnight():
    assert math.isclose(
        compute_water_temperature(0.0), BASE_WATER_TEMP - WATER_TEMP_SWING
    )


def test_compute_water_temperature_stays_within_the_swing():
    for i in range(21):
        fraction = i / 20
        temp = compute_water_temperature(fraction)
        assert (
            BASE_WATER_TEMP - WATER_TEMP_SWING
            <= temp
            <= BASE_WATER_TEMP + WATER_TEMP_SWING
        )


def test_night_blend_zero_at_midday_one_at_midnight():
    assert math.isclose(night_blend(0.5), 0.0, abs_tol=1e-9)
    assert math.isclose(night_blend(0.0), 1.0)
    assert math.isclose(night_blend(1.0), 1.0)


def test_night_blend_stays_in_unit_range():
    for i in range(21):
        fraction = i / 20
        assert 0.0 <= night_blend(fraction) <= 1.0
