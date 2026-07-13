"""Friend/Rival bonds, breeding, and personality -- how a fish's traits and
social ties get decided, at birth and afterward."""

import random

from .constants import FRIEND_CHANCE, PERSONALITIES, RIVAL_CHANCE


def random_personality() -> str:
    """Roll one of PERSONALITIES for a new fish, uniformly."""
    return random.choice(PERSONALITIES)


def form_relationship(new_fish, fish_list) -> None:
    """Roll a chance for `new_fish` (already appended to `fish_list`) to
    bond with an existing fish: a mutual Friend, or a mutual Rival --
    mutually exclusive for *this* roll, though a fish can still pick up the
    other kind later from a different fish's own introduction. Only
    considers partners that don't already have that kind of bond, so
    nobody's existing Friend/Rival gets silently overwritten."""
    others = [f for f in fish_list if f is not new_fish]
    if not others:
        return
    roll = random.random()
    if roll < FRIEND_CHANCE:
        candidates = [f for f in others if f.friend is None]
        if candidates:
            partner = random.choice(candidates)
            new_fish.friend = partner
            partner.friend = new_fish
    elif roll < FRIEND_CHANCE + RIVAL_CHANCE:
        candidates = [f for f in others if f.rival is None]
        if candidates:
            partner = random.choice(candidates)
            new_fish.rival = partner
            partner.rival = new_fish


def clear_relationships(removed, fish_list) -> None:
    """Called whenever a fish leaves the tank (sold, starved, eaten) so no
    survivor is left steering toward/fleeing a ghost -- the same care
    already taken for a sold favorite Decoration."""
    for f in fish_list:
        if f.friend is removed:
            f.friend = None
        if f.rival is removed:
            f.rival = None


def find_breeding_pairs(fish_list):
    """Mutual Friend pairs where both fish are grown-up (Adult) and not
    predators -- each pair returned exactly once regardless of iteration
    order. Doesn't roll BREED_CHANCE itself; the caller (main()'s daily
    tick) decides whether each pair actually has a baby this time."""
    pairs = []
    seen = set()
    for f in fish_list:
        partner = f.friend
        if (
            partner is None
            or f.is_predator
            or partner.is_predator
            or f.growth_stage != "Adult"
            or partner.growth_stage != "Adult"
            or partner.friend is not f  # must be mutual
        ):
            continue
        key = frozenset((id(f), id(partner)))
        if key in seen:
            continue
        seen.add(key)
        pairs.append((f, partner))
    return pairs


def choose_baby_species_name(parent_a, parent_b) -> str:
    """A baby inherits one parent's species, chosen at random."""
    return random.choice([parent_a.species_name, parent_b.species_name])
