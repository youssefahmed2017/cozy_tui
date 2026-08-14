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
# Same precedent, for danger: shared with aquarium.py's
# _flee_lost_adventure_fish_to_shelter(), a real encounter with the exact
# same Tiger Shark that threatens ordinary foragers (see
# _check_forest_danger()) instead of only ever an invisible daily coin
# flip. {shelter} is filled in by whichever path actually resolved it.
DANGER_LINE = "A huge fish chased me. I made it back to the {shelter} safely."


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
        # Set for the rest of the in-progress day the moment a real Tiger
        # Shark encounter resolves (see aquarium.py's
        # _flee_lost_adventure_fish_to_shelter()), so pick_event() doesn't
        # also roll the abstract "danger" event on top of one that already
        # visibly happened -- reset back to False once _advance_lost_
        # adventure() finishes resolving each day. Same missing-key-
        # defaults-safely story as told_to_find_wood above for an old save.
        "danger_today": False,
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
    # Skipped if a real Tiger Shark encounter already resolved this same
    # day (adv["danger_today"], see aquarium.py's
    # _flee_lost_adventure_fish_to_shelter()) -- same "the real path takes
    # over, the abstract roll steps aside" shape find_wood already has
    # above, just day-scoped instead of adventure-scoped since danger (unlike
    # finding wood or a shelter) is meant to be a repeatable risk, not a
    # one-time discovery.
    if not adv.get("danger_today", False):
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
            "memory": DANGER_LINE.format(shelter=shelter),
            "happiness_delta": -LOST_ADVENTURE_DANGER_HAPPINESS_LOSS,
            "feed": False,
        }
    raise ValueError(f"Unknown Lost Adventure event: {event!r}")


