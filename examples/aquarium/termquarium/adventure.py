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
    LOST_ADVENTURE_HUNGER_SEEK_BUBBLES_THRESHOLD,
    LOST_ADVENTURE_SHELTERS,
    LOST_ADVENTURE_WANDER_LINES,
)

# Bubbles: always meetable, but a trade needs Wood in hand. A fish that
# meets Bubbles empty-handed goes looking and the trade resolves
# automatically the very next day (BUBBLES_RESOLVED_LINE, applied by
# aquarium.py's _advance_lost_adventure before it even calls pick_event()
# again) rather than waiting on another random roll of "meet_bubbles".
BUBBLES_TRADE_LINE = "The fish with a cap gave me food in return of wood."
BUBBLES_NO_WOOD_LINE = (
    'Met a fish wearing a cap. He said: "Anyone want some food?". I had nothing to '
    "trade yet."
)
BUBBLES_GLYPH = "🐠🧢"
BUBBLES_RESOLVED_LINE = (
    "Found a piece of driftwood and remembered Bubbles. Traded it for shrimp."
)


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
        "awaiting_bubbles_trade": False,
    }


def pick_event(adv: dict, hunger: float | None = None) -> str:
    """Weighted pick among this day's possible events -- calm "wander" days
    dominate ("99% cozy, occasional event"); find_shelter/find_wood are
    only offered while there's still something new to find.

    `hunger` is optional (aquarium.py's _resolve_lost_adventure_event()
    always passes the fish's real hunger; direct/test callers that don't
    care about this can omit it and get the plain weighted roll). A hungry
    fish (< LOST_ADVENTURE_HUNGER_SEEK_BUBBLES_THRESHOLD) already carrying
    wood to trade goes looking for Bubbles outright rather than leaving it
    to chance -- it has both a reason and the means, so waiting on a 15%
    daily roll to maybe bump into someone doesn't read as "actively
    searching" the way the flavor implies."""
    if (
        hunger is not None
        and hunger < LOST_ADVENTURE_HUNGER_SEEK_BUBBLES_THRESHOLD
        and adv["has_wood"]
    ):
        return "meet_bubbles"
    events = ["wander"]
    weights = [50]
    if adv["shelter"] is None:
        events.append("find_shelter")
        weights.append(15)
    events.append("meet_bubbles")
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
            "memory": "Found a piece of driftwood.",
            "happiness_delta": 0.0,
            "feed": False,
        }
    if event == "meet_bubbles":
        if adv["has_wood"]:
            adv["has_wood"] = False
            return {
                "memory": BUBBLES_TRADE_LINE,
                "happiness_delta": 0.0,
                "feed": True,
            }
        adv["awaiting_bubbles_trade"] = True
        return {
            "memory": BUBBLES_NO_WOOD_LINE,
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


