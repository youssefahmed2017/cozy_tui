"""Calendar: a lightweight season/year layer on top of the aquarium's own
day_count -- see ROADMAP.md's Birthday System entry for the full reasoning.

Deliberately separate from world.py's day/night cycle (a 0..1 fraction
*within* one day) and from Fish.age_days (per-fish, drives growth/hunger/
death). This is the one shared "what day is it" clock other systems
(Birthdays today; ChristFishMas and updates.md's far-future Fishing Seasons
later) can read without each inventing their own.

Pure functions over plain ints -- no App/Widget/Fish involved, same
testing shape as steering.py/economy.py.
"""

from .constants import CALENDAR_YEAR_DAYS, SEASON_LENGTH_DAYS, SEASONS


def calendar_today(day_count: int) -> tuple[int, str, int]:
    """(year, season, day_of_year) for the aquarium's current day_count.

    `year` and `day_of_year` are both 0-based; `day_of_year` is
    day_count's position within the current CALENDAR_YEAR_DAYS-day cycle.
    """
    day_of_year = day_count % CALENDAR_YEAR_DAYS
    year = day_count // CALENDAR_YEAR_DAYS
    season = SEASONS[day_of_year // SEASON_LENGTH_DAYS]
    return year, season, day_of_year
