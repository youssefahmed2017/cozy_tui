"""Day/night cycle and water temperature (Phase 5) for the TermQuarium example."""

import math

from examples.aquarium.termquarium.constants import (
    AFTERNOON_END,
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
    temperature_chill,
)


def test_compute_time_of_day_wraps_via_modulo():
    assert compute_time_of_day(0.0, 100.0) == 0.0
    assert compute_time_of_day(50.0, 100.0) == 0.5
    assert compute_time_of_day(150.0, 100.0) == 0.5  # wrapped into the next day
    assert compute_time_of_day(250.0, 100.0) == 0.5  # and the one after that


def test_compute_time_of_day_zero_length_day_is_zero():
    assert compute_time_of_day(50.0, 0.0) == 0.0


def test_get_day_phase_midday_is_afternoon():
    assert get_day_phase(0.5) == "Afternoon"


def test_get_day_phase_night_wraps_around_midnight():
    assert get_day_phase(NIGHT_START) == "Night"
    assert get_day_phase(0.99) == "Night"
    assert get_day_phase(0.0) == "Night"
    assert get_day_phase(NIGHT_END - 0.01) == "Night"


def test_get_day_phase_morning_is_between_night_and_afternoon():
    assert get_day_phase(NIGHT_END) == "Morning"
    assert get_day_phase(MORNING_END - 0.01) == "Morning"


def test_get_day_phase_afternoon_follows_morning():
    assert get_day_phase(MORNING_END) == "Afternoon"
    assert get_day_phase(AFTERNOON_END - 0.01) == "Afternoon"


def test_get_day_phase_evening_follows_afternoon():
    assert get_day_phase(AFTERNOON_END) == "Evening"
    assert get_day_phase(NIGHT_START - 0.01) == "Evening"


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


def test_temperature_chill_is_zero_at_the_daily_peak():
    peak = BASE_WATER_TEMP + WATER_TEMP_SWING
    assert temperature_chill(peak) == 0.0


def test_temperature_chill_is_one_at_the_daily_trough():
    trough = BASE_WATER_TEMP - WATER_TEMP_SWING
    assert temperature_chill(trough) == 1.0


def test_temperature_chill_clamps_beyond_the_normal_range():
    peak = BASE_WATER_TEMP + WATER_TEMP_SWING
    trough = BASE_WATER_TEMP - WATER_TEMP_SWING
    assert temperature_chill(peak + 10.0) == 0.0
    assert temperature_chill(trough - 10.0) == 1.0


def test_temperature_chill_is_already_meaningfully_above_zero_by_evening():
    # The whole point: Evening should feel a bit cold well before the water
    # actually crosses COLD_TEMP_THRESHOLD (which only happens near
    # midnight) -- see world.temperature_chill()'s own docstring.
    evening_temp = compute_water_temperature(AFTERNOON_END)
    assert 0.0 < temperature_chill(evening_temp) < 0.5


def test_temperature_chill_rises_monotonically_from_peak_to_trough():
    fractions = [i / 20 for i in range(11)]  # 0.5 (peak) to 1.0 (trough)
    chills = [temperature_chill(compute_water_temperature(0.5 + f)) for f in fractions]
    assert chills == sorted(chills)


def test_night_blend_zero_at_midday_one_at_midnight():
    assert math.isclose(night_blend(0.5), 0.0, abs_tol=1e-9)
    assert math.isclose(night_blend(0.0), 1.0)
    assert math.isclose(night_blend(1.0), 1.0)


def test_night_blend_stays_in_unit_range():
    for i in range(21):
        fraction = i / 20
        assert 0.0 <= night_blend(fraction) <= 1.0
