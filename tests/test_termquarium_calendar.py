"""Calendar (ROADMAP.md's Birthday System): a season/year layer derived from
the aquarium's own day_count, kept separate from age_days/GROWTH_STAGES."""

from examples.aquarium.termquarium.calendar import calendar_today
from examples.aquarium.termquarium.constants import (
    CALENDAR_YEAR_DAYS,
    SEASON_LENGTH_DAYS,
    SEASONS,
)


def test_year_length_matches_seasons():
    assert CALENDAR_YEAR_DAYS == SEASON_LENGTH_DAYS * len(SEASONS)


def test_calendar_today_first_day_of_year_zero():
    assert calendar_today(0) == (0, "Spring", 0)


def test_calendar_today_walks_through_each_season():
    for index, season in enumerate(SEASONS):
        day_count = index * SEASON_LENGTH_DAYS
        year, got_season, day_of_year = calendar_today(day_count)
        assert got_season == season
        assert year == 0
        assert day_of_year == day_count


def test_calendar_today_wraps_into_the_next_year():
    year, season, day_of_year = calendar_today(CALENDAR_YEAR_DAYS)
    assert year == 1
    assert season == "Spring"
    assert day_of_year == 0


def test_calendar_today_several_years_in():
    day_count = CALENDAR_YEAR_DAYS * 3 + SEASON_LENGTH_DAYS * 2 + 4
    year, season, day_of_year = calendar_today(day_count)
    assert year == 3
    assert season == "Autumn"
    assert day_of_year == SEASON_LENGTH_DAYS * 2 + 4
