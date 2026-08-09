"""Lost Adventure (ROADMAP.md) -- pure state/decision logic for a fish
rarely gone missing in the Forest for several days. Kept separate from
aquarium.py's main() (which owns the live Fish/App side effects: toasts,
_log_memory, happiness/hunger mutation, aquarium_widgets membership) the
same way steering.py/economy.py are -- so the actual day-by-day decisions
are unit-testable without a Widget/App (see
tests/test_termquarium_adventure.py)."""

import random

from .constants import (
    LOST_ADVENTURE_DANGER_HAPPINESS_LOSS,
    LOST_ADVENTURE_DURATION_RANGE,
    LOST_ADVENTURE_SHELTERS,
    LOST_ADVENTURE_WANDER_LINES,
)

# Bubbles is a fixed Forest resident (see tank_objects.py's BubblesNPC), not
# a random encounter -- aquarium.py's _visit_bubbles() calls a hungry fish
# over to him deterministically, outside pick_event()'s weighted roll
# entirely, so these are just the flavor lines that decision reaches for.
BUBBLES_TRADE_LINE = "The fish with a cap gave me food in return of wood."
BUBBLES_NO_WOOD_LINE = (
    'Met a fish wearing a cap. He said: "Anyone want some food?". I had nothing to '
    "trade yet."
)
# Shared with aquarium.py's _wander_lost_adventure_fish(), which now finds
# wood the same way real foraging fish do (steering to an actual Wood
# widget in the Forest, see forest_wood) rather than waiting on pick_event()'s
# find_wood roll below -- one line either way keeps the memory log consistent
# regardless of which path actually found it.
FOUND_WOOD_LINE = "Found a piece of driftwood."


def roll_duration() -> int:
    return random.randint(*LOST_ADVENTURE_DURATION_RANGE)


def new_state(duration: int | None = None) -> dict:
    """A fresh Lost Adventure state dict -- see fish.py's
    Fish.lost_adventure for the field meanings."""
    return {
        "day": 0,
        "duration": duration if duration is not None else roll_duration(),
        "shelter": None,
        "has_wood": False,
        # One-shot reminder gate for a hungry, empty-handed Bubbles visit --
        # see aquarium.py's _advance_lost_adventure()/_visit_bubbles(). A
        # save from before this existed just has no key here; the aquarium.py
        # read side already defaults a missing key to False (an old save's
        # fish hasn't been reminded yet either), so no migration needed.
        "told_to_find_wood": False,
    }


def pick_event(adv: dict) -> str:
    """Weighted pick among this day's possible events -- calm "wander" days
    dominate ("99% cozy, occasional event"); find_shelter/find_wood are
    only offered while there's still something new to find. Only reached
    when the fish *isn't* hungry enough to visit Bubbles instead (see
    aquarium.py's _advance_lost_adventure(), which checks that first,
    deterministically, before ever calling this)."""
    events = ["wander"]
    weights = [50]
    if adv["shelter"] is None:
        events.append("find_shelter")
        weights.append(15)
    if not adv["has_wood"]:
        events.append("find_wood")
        weights.append(10)
    events.append("danger")
    weights.append(10)
    return random.choices(events, weights=weights, k=1)[0]


def apply_event(adv: dict, event: str) -> dict:
    """Mutates `adv` in place for the chosen event and returns a plain
    effects dict describing what the caller needs to apply to the live
    Fish: {"memory": str, "happiness_delta": float, "feed": bool}."""
    if event == "wander":
        return {
            "memory": random.choice(LOST_ADVENTURE_WANDER_LINES),
            "happiness_delta": 0.0,
            "feed": False,
        }
    if event == "find_shelter":
        shelter = random.choice(LOST_ADVENTURE_SHELTERS)
        adv["shelter"] = shelter
        return {
            "memory": f"Found the {shelter}. It looks safe to hide in.",
            "happiness_delta": 0.0,
            "feed": False,
        }
    if event == "find_wood":
        adv["has_wood"] = True
        return {
            "memory": FOUND_WOOD_LINE,
            "happiness_delta": 0.0,
            "feed": False,
        }
    if event == "danger":
        # Always survived (matches the Forest Tiger Shark precedent --
        # "nobody is ever caught"), but never free: a flat happiness cost
        # either way. A shelter found earlier is remembered by name in the
        # flavor line rather than changing the outcome.
        shelter = adv["shelter"] or random.choice(LOST_ADVENTURE_SHELTERS)
        if adv["shelter"] is None:
            adv["shelter"] = shelter
        return {
            "memory": f"A huge fish chased me. I made it back to the {shelter} safely.",
            "happiness_delta": -LOST_ADVENTURE_DANGER_HAPPINESS_LOSS,
            "feed": False,
        }
    raise ValueError(f"Unknown Lost Adventure event: {event!r}")


