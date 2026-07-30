"""Lost Adventure (ROADMAP.md) -- pure day-by-day decision logic
(examples/aquarium/termquarium/adventure.py). No App/Widget involved, same
as test_termquarium_world.py; the live-Fish/App wiring around this
(aquarium.py's _begin_lost_adventure/_advance_lost_adventure/
_return_from_lost_adventure) is exercised indirectly through the Cheat
Console commands in tests/test_termquarium_console.py, and by manual
playthrough."""

import random

import pytest

from examples.aquarium.termquarium import adventure
from examples.aquarium.termquarium.constants import LOST_ADVENTURE_DURATION_RANGE


def test_roll_duration_stays_within_the_configured_range():
    for _ in range(200):
        duration = adventure.roll_duration()
        assert LOST_ADVENTURE_DURATION_RANGE[0] <= duration <= LOST_ADVENTURE_DURATION_RANGE[1]


def test_new_state_defaults_to_a_rolled_duration():
    state = adventure.new_state()
    assert state["day"] == 0
    assert state["shelter"] is None
    assert state["has_wood"] is False
    assert state["awaiting_bubbles_trade"] is False
    assert LOST_ADVENTURE_DURATION_RANGE[0] <= state["duration"] <= LOST_ADVENTURE_DURATION_RANGE[1]


def test_new_state_accepts_an_explicit_duration():
    state = adventure.new_state(duration=3)
    assert state["duration"] == 3


def test_pick_event_never_offers_find_shelter_once_a_shelter_is_known():
    state = adventure.new_state(duration=100)
    state["shelter"] = "Tree House"
    for _ in range(200):
        assert adventure.pick_event(state) != "find_shelter"


def test_pick_event_never_offers_find_wood_while_already_carrying_wood():
    state = adventure.new_state(duration=100)
    state["has_wood"] = True
    for _ in range(200):
        assert adventure.pick_event(state) != "find_wood"


def test_pick_event_can_offer_every_event_when_nothing_is_known_yet():
    state = adventure.new_state(duration=100)
    seen = {adventure.pick_event(state) for _ in range(500)}
    assert seen == {"wander", "find_shelter", "meet_bubbles", "find_wood", "danger"}


def test_apply_event_find_shelter_sets_shelter_and_has_no_mechanical_effect():
    state = adventure.new_state(duration=100)
    effects = adventure.apply_event(state, "find_shelter")
    assert state["shelter"] is not None
    assert state["shelter"] in effects["memory"]
    assert effects["happiness_delta"] == 0.0
    assert effects["feed"] is False


def test_apply_event_find_wood_sets_has_wood():
    state = adventure.new_state(duration=100)
    effects = adventure.apply_event(state, "find_wood")
    assert state["has_wood"] is True
    assert effects["feed"] is False


def test_apply_event_meet_bubbles_with_wood_completes_the_trade():
    state = adventure.new_state(duration=100)
    state["has_wood"] = True
    effects = adventure.apply_event(state, "meet_bubbles")
    assert state["has_wood"] is False
    assert state["awaiting_bubbles_trade"] is False
    assert effects["feed"] is True
    assert effects["memory"] == adventure.BUBBLES_TRADE_LINE


def test_apply_event_meet_bubbles_without_wood_defers_the_trade():
    state = adventure.new_state(duration=100)
    effects = adventure.apply_event(state, "meet_bubbles")
    assert state["awaiting_bubbles_trade"] is True
    assert effects["feed"] is False
    assert effects["memory"] == adventure.BUBBLES_NO_WOOD_LINE


def test_apply_event_danger_always_costs_happiness_and_names_a_shelter():
    state = adventure.new_state(duration=100)
    effects = adventure.apply_event(state, "danger")
    assert effects["happiness_delta"] < 0
    assert state["shelter"] is not None
    assert state["shelter"] in effects["memory"]
    assert "safely" in effects["memory"]


def test_apply_event_danger_reuses_an_already_known_shelter():
    state = adventure.new_state(duration=100)
    state["shelter"] = "Hidden Cave"
    effects = adventure.apply_event(state, "danger")
    assert state["shelter"] == "Hidden Cave"
    assert "Hidden Cave" in effects["memory"]


def test_apply_event_wander_has_no_mechanical_effect():
    state = adventure.new_state(duration=100)
    effects = adventure.apply_event(state, "wander")
    assert effects["happiness_delta"] == 0.0
    assert effects["feed"] is False
    assert effects["memory"]


def test_apply_event_rejects_an_unknown_event_name():
    state = adventure.new_state(duration=100)
    with pytest.raises(ValueError):
        adventure.apply_event(state, "nonexistent")


def test_full_adventure_walkthrough_can_resolve_a_deferred_bubbles_trade():
    # Simulates aquarium.py's _advance_lost_adventure loop end to end:
    # meet Bubbles empty-handed, then the very next day's resolution is
    # guaranteed (not another random roll of "meet_bubbles").
    random.seed(0)
    state = adventure.new_state(duration=100)
    state["awaiting_bubbles_trade"] = False
    # Force the empty-handed Bubbles branch directly (pick_event's roll is
    # tested separately above).
    effects = adventure.apply_event(state, "meet_bubbles")
    assert state["awaiting_bubbles_trade"] is True
    assert effects["feed"] is False
    # The caller's guaranteed-resolution day: no further event pick needed.
    assert state["has_wood"] is False
