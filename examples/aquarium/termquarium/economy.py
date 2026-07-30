"""Economy and tank-level gameplay decisions."""

import random

from .constants import (
    AGE_SECONDS_PER_DAY,
    ATTRACTIVENESS_BY_DECORATION,
    ATTRACTIVENESS_PER_FISH,
    ATTRACTIVENESS_PER_RARE_FISH,
    CLEAN_TANK_ATTRACTIVENESS,
    DONATION_PER_VISITOR_MAX,
    HAPPINESS_MAX,
    HAPPINESS_MIN,
    HEALTH_GAIN,
    HUNGER_RELIEF,
    HUNGER_STEP,
    HUNGER_WARNING_THRESHOLD,
    RARE_PRICE_THRESHOLD,
    STARVE_HEALTH_LOSS,
    TICKET_PRICE,
    VISITORS_PER_ATTRACTIVENESS,
)


def should_warn_hungry(hunger_levels, warning_active: bool) -> bool:
    """Whether this tick should raise the one-shot hunger notification."""
    return not warning_active and any(
        level < HUNGER_WARNING_THRESHOLD for level in hunger_levels
    )


def decay_hunger(
    hunger, health, hunger_step=HUNGER_STEP, starve_loss=STARVE_HEALTH_LOSS
):
    """One tick of a fish going hungrier; once hunger bottoms out, health
    starts draining too -- unchanged, still real, for a fish in the main
    tank. `starve_loss=0.0` is how aquarium.py's _per_second_tick() exempts
    a fish that's currently away doing Forest/fishing-style biome mechanics
    (see constants.py's Hunger update comment): hunger still drains and
    bottoms out at 0 ("Low energy"), it just never starts draining health
    while the player has no way to see or feed that fish. Called on its own
    periodic clock (app.every), not every frame -- hunger/health are a slow
    background process, unlike the continuous position update.

    Scale (updates.md): 0 = starving, 100 = full -- flipped from the
    original 0=full/100=starving, which read backwards ("100% hungry"
    meaning "just ate")."""
    hunger = max(0.0, hunger - hunger_step)
    if hunger <= 0.0:
        health = max(0.0, health - starve_loss)
    return hunger, health


def feed(hunger, health, relief=HUNGER_RELIEF, gain=HEALTH_GAIN):
    """One bite of food: relieve hunger (push it back up toward full) and
    restore a bit of health."""
    return min(100.0, hunger + relief), min(100.0, health + gain)


def adjust_happiness(happiness: float, delta: float) -> float:
    """Move `happiness` by `delta` (positive or negative), clamped to
    [HAPPINESS_MIN, HAPPINESS_MAX]. The one choke point every Happiness gain/
    loss in aquarium.py goes through -- same shape as feed()/decay_hunger()
    clamping hunger and health, just for the one new stat that never decays
    on its own (see constants.py's Happiness block for why)."""
    return max(HAPPINESS_MIN, min(HAPPINESS_MAX, happiness + delta))


def compute_attractiveness(fish_list, decoration_list, food_list) -> int:
    """Visitor Donations, Phase 3: decorating isn't just cosmetic, it feeds
    a score that drives daily visitor income. Each fish is worth
    ATTRACTIVENESS_PER_FISH (ATTRACTIVENESS_PER_RARE_FISH instead if its
    Shop price meets RARE_PRICE_THRESHOLD), each decoration is worth
    whatever ATTRACTIVENESS_BY_DECORATION says for its kind, and a tank
    with no food currently sitting uneaten counts as "clean" for a flat
    bonus."""
    total = 0
    for f in fish_list:
        total += (
            ATTRACTIVENESS_PER_RARE_FISH
            if f.price >= RARE_PRICE_THRESHOLD
            else ATTRACTIVENESS_PER_FISH
        )
    for d in decoration_list:
        total += ATTRACTIVENESS_BY_DECORATION.get(d.kind, 0)
    if not food_list:
        total += CLEAN_TANK_ATTRACTIVENESS
    return total


def compute_visitor_income(attractiveness: int):
    """visitors = attractiveness // VISITORS_PER_ATTRACTIVENESS; each pays a
    fixed ticket price plus a randomized donation on top. Returns
    (visitors, ticket_sales, donations)."""
    visitors = attractiveness // VISITORS_PER_ATTRACTIVENESS
    ticket_sales = visitors * TICKET_PRICE
    donations = (
        random.randint(0, visitors * DONATION_PER_VISITOR_MAX) if visitors > 0 else 0
    )
    return visitors, ticket_sales, donations


def roll_visitor_donation(
    visitors: int, day_seconds: float = AGE_SECONDS_PER_DAY
) -> int:
    """Called once per real-time second (see aquarium.py's _per_second_tick)
    to spread a day's worth of visitor donations out as individual events
    instead of one lump sum the player only sees at day's end. Each second
    has roughly a visitors/day_seconds chance that a visitor donates right
    now, for a randomized $1..DONATION_PER_VISITOR_MAX -- so across a full
    day this fires about `visitors` times, matching the old aggregate math,
    just paid out (and toasted) as it actually happens. Returns 0 on a
    second where nobody donates."""
    if visitors <= 0 or random.random() >= visitors / day_seconds:
        return 0
    return random.randint(1, DONATION_PER_VISITOR_MAX)


def should_grant_welfare(money: int, food: int, fish_count: int, enabled: bool) -> bool:
    """Emergency Aquarium Welfare's trigger condition: totally bankrupt
    (money = food = fish = 0) and the player hasn't opted out in Settings."""
    return enabled and money == 0 and food == 0 and fish_count == 0

