"""Day/night cycle and water temperature (Phase 5) for the TermQuarium example."""

import math

from examples.aquarium.termquarium.constants import (
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


def test_compute_water_temperature_matches_each_phase_anchor():
    # 0.225/0.45/0.675/0.95 are each phase band's own representative
    # midpoint (see world._TEMPERATURE_ANCHORS) -- warmest in the Morning,
    # coldest at Night's, not a single sinusoid peaking at midday.
    assert compute_water_temperature(0.225) == MORNING_WATER_TEMP
    assert compute_water_temperature(0.45) == AFTERNOON_WATER_TEMP
    assert compute_water_temperature(0.675) == EVENING_WATER_TEMP
    assert compute_water_temperature(0.95) == NIGHT_WATER_TEMP


def test_compute_water_temperature_wraps_smoothly_across_midnight():
    # Just before fraction=0 (Night, still cooled toward NIGHT_WATER_TEMP)
    # and just after (still Night, warming back toward Morning) must be
    # close to each other -- no jump at the midnight boundary.
    just_before = compute_water_temperature(0.999)
    just_after = compute_water_temperature(0.001)
    assert math.isclose(just_before, just_after, abs_tol=0.1)


def test_compute_water_temperature_stays_within_range():
    for i in range(21):
        fraction = i / 20
        temp = compute_water_temperature(fraction)
        assert NIGHT_WATER_TEMP <= temp <= MORNING_WATER_TEMP


def test_temperature_chill_is_zero_during_morning_and_afternoon():
    # The regression this covers: chill used to be measured against the
    # day's peak warmth, so an ordinary Afternoon (nowhere near
    # COLD_TEMP_THRESHOLD) already produced a real, if small, chance to
    # seek warmth. Anchored to the real cold threshold instead, neither
    # should ever register as chilly at all.
    assert temperature_chill(MORNING_WATER_TEMP) == 0.0
    assert temperature_chill(AFTERNOON_WATER_TEMP) == 0.0


def test_temperature_chill_is_zero_at_evenings_own_temperature_and_above():
    assert temperature_chill(EVENING_WATER_TEMP) == 0.0
    assert temperature_chill(EVENING_WATER_TEMP + 5.0) == 0.0


def test_temperature_chill_is_one_at_and_below_the_cold_threshold():
    assert temperature_chill(COLD_TEMP_THRESHOLD) == 1.0
    assert temperature_chill(COLD_TEMP_THRESHOLD - 5.0) == 1.0
    assert temperature_chill(NIGHT_WATER_TEMP) == 1.0


def test_temperature_chill_rises_across_evening_into_night():
    fractions = [i / 40 for i in range(11)]  # 0.675 (Evening) to 0.95 (Night)
    chills = [temperature_chill(compute_water_temperature(0.675 + f)) for f in fractions]
    assert chills == sorted(chills)
    assert chills[0] == 0.0  # right at Evening's own midpoint -- still comfortable
    assert chills[-1] == 1.0  # right at Night's own midpoint -- properly cold


def test_night_blend_zero_at_midday_one_at_midnight():
    assert math.isclose(night_blend(0.5), 0.0, abs_tol=1e-9)
    assert math.isclose(night_blend(0.0), 1.0)
    assert math.isclose(night_blend(1.0), 1.0)


def test_night_blend_stays_in_unit_range():
    for i in range(21):
        fraction = i / 20
        assert 0.0 <= night_blend(fraction) <= 1.0
