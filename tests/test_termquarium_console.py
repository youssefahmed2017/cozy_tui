"""Tests for the Cheat Console's command registry and RestrictedPython
execution (examples/aquarium/termquarium/console.py) -- pure logic, no App/
overlay plumbing needed (see tests/test_aquarium.py for the headless-app-
level integration tests: opening the console via the backtick key, typing
into the real CheatConsole widget, etc.).

There is no more parse_command() to test separately -- the console *is*
RestrictedPython now (see console.py's own module docstring): every typed
line is compiled and run through it directly, tried first as a single
expression (eval, covers the overwhelming majority of typed commands) and
falling back to a real exec (a loop, an assignment, several statements) --
so what used to be a separate run(code="...") escape hatch is now just
typing that code directly. RestrictedPython's own sandboxing (rejecting
dunder/attribute-gadget escapes at compile time) is exercised below the
same way it always was, just without the run() wrapper.
"""

import pytest

from examples.aquarium.termquarium.console import ConsoleError, build_console_commands, run_console_command
from examples.aquarium.termquarium.fish import Fish


def _fake_fish(name="Fishy"):
    f = Fish(
        0.0,
        0.0,
        (0.0, 0.0, 10.0, 10.0),
        [],
        [],
        lambda x: None,
        lambda x: None,
        "><>",
        "<><",
        "yellow",
    )
    f.display_name = name
    return f


def _build_registry():
    fish = []
    state = {"money": 100, "food": 10, "treats": {}, "sound_enabled": True}
    events = []

    def add_fish_cb(species):
        f = _fake_fish(species.name)
        fish.append(f)
        return f

    def spawn_fish_cb(species):
        events.append(("spawn_fish_cb", species.name))

    def buy_food_cb():
        events.append(("buy_food_cb",))

    def buy_treat_cb(item):
        events.append(("buy_treat_cb", item.kind))

    def add_decoration_cb(item):
        events.append(("add_decoration_cb", item.kind))

    def refresh_stats_cb():
        events.append(("refresh_stats_cb",))

    def set_day_phase_cb(phase):
        if phase.lower() not in ("morning", "afternoon", "evening", "night"):
            raise ValueError("bad phase")
        events.append(("set_day_phase_cb", phase))
        return phase.capitalize()

    def spawn_food_cb(kind, amount):
        if kind.lower() != "pizza":
            raise ValueError("unknown food")
        events.append(("spawn_food_cb", kind, amount))
        return amount, "Pizza"

    def give_nightmare_cb(f, variant=None, scare=True):
        events.append(("give_nightmare_cb", f.display_name, variant, scare))
        if variant is not None and variant.lower() not in ("ice", "shark"):
            raise ValueError(f"No 'bad' dream matching {variant!r}.")

    def give_dream_cb(f, category=None):
        events.append(("give_dream_cb", f.display_name, category))
        return "A Sunny Reef"

    def grant_trait_cb(f, trait):
        events.append(("grant_trait_cb", f.display_name, trait))
        if trait not in ("food_lover", "dreamer", "fast_swimmer"):
            raise ValueError(f"Unknown trait: {trait!r}.")
        return f"Gave {f.display_name} the {trait} trait."

    def advance_day_cb():
        events.append(("advance_day_cb",))

    def start_lost_adventure_cb(f, duration=None):
        f.lost_adventure = {"day": 0, "duration": duration or 5}
        events.append(("start_lost_adventure_cb", f.display_name, duration))

    def advance_adventure_day_cb(f):
        events.append(("advance_adventure_day_cb", f.display_name))

    def set_happiness_cb(f, amount):
        f.happiness = max(0.0, min(100.0, amount))
        events.append(("set_happiness_cb", f.display_name, amount))

    def set_speed_cb(f, amount):
        f.speed = max(2.5, min(6.0, amount))
        events.append(("set_speed_cb", f.display_name, amount))

    def set_personality_cb(f, personality):
        if personality not in ("Friendly", "Explorer", "Shy", "Greedy", "Lazy", "Playful"):
            raise ValueError(f"Unknown personality: {personality!r}.")
        f.personality = personality
        events.append(("set_personality_cb", f.display_name, personality))

    def force_relationship_cb(a, b, score):
        events.append(("force_relationship_cb", a.display_name, b.display_name, score))

    def set_day_cb(amount):
        events.append(("set_day_cb", amount))

    def toggle_forest_cb(unlocked):
        state["forest_unlocked"] = unlocked
        events.append(("toggle_forest_cb", unlocked))

    def spawn_decoration_cb(kind):
        if kind not in ("Castle", "Rock"):
            raise ValueError(f"Unknown decoration: {kind!r}.")
        events.append(("spawn_decoration_cb", kind))
        return kind

    def remove_fish_cb(f):
        if f in fish:
            fish.remove(f)
        events.append(("remove_fish_cb", f.display_name))

    def find_legendary_cb(species_name=None):
        events.append(("find_legendary_cb", species_name))
        if species_name is not None and species_name not in (
            "Golden Axolotl",
            "Ghost Fish",
            "Crystal Fish",
            "Lunar Betta",
            "Moon Jellyfish",
        ):
            raise ValueError(f"Unknown Legendary species: {species_name!r}.")
        f = _fake_fish(species_name or "Ghost Fish")
        fish.append(f)
        return f

    def force_random_event_cb(event):
        events.append(("force_random_event_cb", event))
        if event not in ("legendary", "lucky_find", "showing_off", "storm", "stray_fish"):
            raise ValueError(f"Unknown event: {event!r}.")
        if event == "storm" and state.get("storm_active"):
            raise ValueError("A storm is already rolling through.")

    def trigger_birthday_cb(f):
        events.append(("trigger_birthday_cb", f.display_name))

    def bubbles_visit_cb(f):
        events.append(("bubbles_visit_cb", f.display_name))

    def end_storm_cb():
        state["storm_active"] = False
        events.append(("end_storm_cb",))

    def unlock_achievement_cb(achievement_id):
        events.append(("unlock_achievement_cb", achievement_id))

    def sync_ambience_cb():
        events.append(("sync_ambience_cb",))

    commands = build_console_commands(
        state=state,
        fish=fish,
        add_fish_cb=add_fish_cb,
        spawn_fish_cb=spawn_fish_cb,
        buy_food_cb=buy_food_cb,
        buy_treat_cb=buy_treat_cb,
        add_decoration_cb=add_decoration_cb,
        refresh_stats_cb=refresh_stats_cb,
        set_day_phase_cb=set_day_phase_cb,
        spawn_food_cb=spawn_food_cb,
        give_nightmare_cb=give_nightmare_cb,
        give_dream_cb=give_dream_cb,
        grant_trait_cb=grant_trait_cb,
        advance_day_cb=advance_day_cb,
        start_lost_adventure_cb=start_lost_adventure_cb,
        advance_adventure_day_cb=advance_adventure_day_cb,
        set_happiness_cb=set_happiness_cb,
        set_speed_cb=set_speed_cb,
        set_personality_cb=set_personality_cb,
        force_relationship_cb=force_relationship_cb,
        set_day_cb=set_day_cb,
        toggle_forest_cb=toggle_forest_cb,
        spawn_decoration_cb=spawn_decoration_cb,
        remove_fish_cb=remove_fish_cb,
        find_legendary_cb=find_legendary_cb,
        force_random_event_cb=force_random_event_cb,
        trigger_birthday_cb=trigger_birthday_cb,
        bubbles_visit_cb=bubbles_visit_cb,
        end_storm_cb=end_storm_cb,
        unlock_achievement_cb=unlock_achievement_cb,
        sync_ambience_cb=sync_ambience_cb,
    )
    return commands, fish, state, events


# ── Existing commands, still real Python calls under the hood ──────────────


def test_spawn_fish_command_adds_a_free_named_fish():
    commands, fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steven")')
    assert len(fish) == 1
    assert fish[0].display_name == "Steven"


def test_spawn_fish_command_can_spawn_several_at_once():
    commands, fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", amount=3)')
    assert len(fish) == 3


def test_spawn_fish_command_rejects_an_unknown_species():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'spawn_fish(species="Dragon")')


def test_set_health_and_set_hunger_commands_clamp_to_0_100():
    commands, fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steven")')
    run_console_command(commands, 'set_health(fish_name="Steven", amount=500)')
    run_console_command(commands, 'set_hunger(fish_name="Steven", amount=-20)')
    assert fish[0].health == 100.0
    assert fish[0].hunger == 0.0


def test_set_health_command_raises_for_an_unknown_fish():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'set_health(fish_name="Ghost", amount=50)')


def test_set_money_and_set_food_commands_set_state_exactly_not_additively():
    commands, _fish, state, events = _build_registry()
    run_console_command(commands, "set_money(1000)")
    run_console_command(commands, "set_food(50)")
    assert state["money"] == 1000
    assert state["food"] == 50
    assert ("refresh_stats_cb",) in events


def test_buy_command_deducts_price_and_calls_the_real_purchase_path():
    commands, _fish, state, events = _build_registry()
    state["money"] = 1000
    run_console_command(commands, 'buy("Shark")')
    assert state["money"] == 1000 - 500  # Shark's Shop price
    assert ("spawn_fish_cb", "Shark") in events


def test_buy_command_raises_when_money_is_insufficient():
    commands, _fish, state, events = _build_registry()
    state["money"] = 0
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'buy("Shark")')
    assert state["money"] == 0  # untouched
    assert not any(e[0] == "spawn_fish_cb" for e in events)


def test_buy_command_works_for_decorations_treats_and_food():
    commands, _fish, state, events = _build_registry()
    state["money"] = 1000
    run_console_command(commands, 'buy("Castle")')
    run_console_command(commands, 'buy("Pizza")')
    run_console_command(commands, 'buy("Food")')
    assert ("add_decoration_cb", "Castle") in events
    assert ("buy_treat_cb", "Pizza") in events
    assert ("buy_food_cb",) in events


def test_buy_command_rejects_an_unknown_item():
    commands, _fish, state, _events = _build_registry()
    state["money"] = 1000
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'buy("Nonexistent Thing")')


def test_set_time_command_accepts_the_four_phases():
    commands, _fish, _state, events = _build_registry()
    for phase in ("morning", "afternoon", "evening", "night"):
        run_console_command(commands, f'set_time("{phase}")')
    assert [e for e in events if e[0] == "set_day_phase_cb"] == [
        ("set_day_phase_cb", "morning"),
        ("set_day_phase_cb", "afternoon"),
        ("set_day_phase_cb", "evening"),
        ("set_day_phase_cb", "night"),
    ]


def test_set_time_command_rejects_a_bad_phase():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'set_time("lunchtime")')


def test_spawn_command_drops_special_food():
    commands, _fish, _state, events = _build_registry()
    result = run_console_command(commands, 'spawn("pizza", 3)')
    assert ("spawn_food_cb", "pizza", 3) in events
    assert "3 Pizza" in result


def test_spawn_command_defaults_amount_to_one_and_clamps_huge_amounts():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn("pizza")')
    run_console_command(commands, 'spawn("pizza", 99999)')
    assert ("spawn_food_cb", "pizza", 1) in events
    assert ("spawn_food_cb", "pizza", 50) in events  # clamped


def test_spawn_command_rejects_unknown_food():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'spawn("gravel")')


def test_give_nightmare_command_targets_a_named_fish():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'give_nightmare("Steve")')
    assert ("give_nightmare_cb", "Steve", None, True) in events


def test_give_nightmare_command_can_force_a_specific_variant():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'give_nightmare("Steve", "ice")')
    assert ("give_nightmare_cb", "Steve", "ice", True) in events
    # keyword form works too
    run_console_command(commands, 'give_nightmare(fish_name="Steve", variant="ice")')
    assert events.count(("give_nightmare_cb", "Steve", "ice", True)) == 2


def test_give_nightmare_command_can_let_the_dream_linger():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    result = run_console_command(commands, 'give_nightmare("Steve", "ice", scare=False)')
    assert ("give_nightmare_cb", "Steve", "ice", False) in events
    assert "linger" in result.lower()


def test_give_nightmare_command_reports_an_unknown_variant():
    commands, _fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'give_nightmare("Steve", "banana")')


def test_give_dream_command_targets_a_named_fish_and_reports_the_title():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Alex")')
    result = run_console_command(commands, 'give_dream("Alex")')
    assert ("give_dream_cb", "Alex", None) in events
    assert "A Sunny Reef" in result


def test_give_nightmare_and_give_dream_raise_for_an_unknown_fish():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'give_nightmare("Ghost")')
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'give_dream("Ghost")')


def test_start_lost_adventure_command_targets_a_named_fish():
    commands, fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'start_lost_adventure(fish_name="Steve")')
    assert ("start_lost_adventure_cb", "Steve", None) in events
    assert fish[0].lost_adventure is not None


def test_start_lost_adventure_command_accepts_an_explicit_duration():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'start_lost_adventure(fish_name="Steve", duration=3)')
    assert ("start_lost_adventure_cb", "Steve", 3) in events


def test_start_lost_adventure_command_rejects_a_non_positive_duration():
    commands, _fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'start_lost_adventure(fish_name="Steve", duration=0)')


def test_start_lost_adventure_command_rejects_a_fish_already_lost():
    commands, _fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'start_lost_adventure(fish_name="Steve")')
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'start_lost_adventure(fish_name="Steve")')


def test_start_lost_adventure_command_raises_for_an_unknown_fish():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'start_lost_adventure(fish_name="Ghost")')


def test_advance_adventure_day_command_targets_a_named_fish_already_lost():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'start_lost_adventure(fish_name="Steve")')
    run_console_command(commands, 'advance_adventure_day(fish_name="Steve")')
    assert ("advance_adventure_day_cb", "Steve") in events


def test_advance_adventure_day_command_rejects_a_fish_not_on_an_adventure():
    commands, _fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'advance_adventure_day(fish_name="Steve")')


def test_set_happiness_command_clamps_to_0_100():
    commands, fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'set_happiness(fish_name="Steve", amount=500)')
    assert fish[0].happiness == 100.0


def test_set_speed_command_targets_a_named_fish():
    commands, fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'set_speed(fish_name="Steve", amount=4.0)')
    assert ("set_speed_cb", "Steve", 4.0) in events
    assert fish[0].speed == 4.0


def test_set_personality_command_rejects_an_unknown_personality():
    commands, _fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'set_personality(fish_name="Steve", personality="Grumpy")')


def test_set_personality_command_sets_a_valid_personality():
    commands, fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'set_personality(fish_name="Steve", personality="Greedy")')
    assert fish[0].personality == "Greedy"


def test_force_relationship_command_targets_two_named_fish():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Kitty")')
    run_console_command(commands, 'force_relationship(fish_a="Steve", fish_b="Kitty", score=80)')
    assert ("force_relationship_cb", "Steve", "Kitty", 80.0) in events


def test_set_day_command_rejects_a_negative_amount():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, "set_day(amount=-1)")


def test_set_day_command_jumps_the_counter():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, "set_day(amount=50)")
    assert ("set_day_cb", 50) in events


def test_toggle_forest_command_rejects_a_non_boolean():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'toggle_forest(unlocked="yes")')


def test_toggle_forest_command_sets_state():
    commands, _fish, state, _events = _build_registry()
    run_console_command(commands, "toggle_forest(unlocked=True)")
    assert state["forest_unlocked"] is True
    run_console_command(commands, "toggle_forest(unlocked=False)")
    assert state["forest_unlocked"] is False


def test_spawn_decoration_command_rejects_an_unknown_kind():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'spawn_decoration(kind="Throne")')


def test_spawn_decoration_command_spawns_a_known_kind():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_decoration(kind="Castle")')
    assert ("spawn_decoration_cb", "Castle") in events


def test_remove_fish_command_removes_it_from_the_tank():
    commands, fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    assert len(fish) == 1
    run_console_command(commands, 'remove_fish(fish_name="Steve")')
    assert fish == []
    assert ("remove_fish_cb", "Steve") in events


def test_remove_fish_command_raises_for_an_unknown_fish():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'remove_fish(fish_name="Ghost")')


def test_force_random_event_command_fires_the_named_event():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'force_random_event(event="storm")')
    assert ("force_random_event_cb", "storm") in events


def test_force_random_event_command_requires_an_event_argument():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, "force_random_event()")


def test_force_random_event_command_surfaces_a_not_currently_applicable_error():
    commands, _fish, state, _events = _build_registry()
    state["storm_active"] = True
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'force_random_event(event="storm")')


# ── New commands ─────────────────────────────────────────────────────────


def test_set_age_command_backdates_birth_time():
    commands, fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'set_age(fish_name="Steve", days=40)')
    assert fish[0].age_days == pytest.approx(40, abs=0.01)


def test_set_age_command_rejects_a_negative_value():
    commands, _fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'set_age(fish_name="Steve", days=-1)')


def test_set_growth_stage_command_jumps_straight_there():
    commands, fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'set_growth_stage(fish_name="Steve", stage="Adult")')
    assert fish[0].growth_stage.startswith("Adult")


def test_set_growth_stage_command_rejects_an_unknown_stage():
    commands, _fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'set_growth_stage(fish_name="Steve", stage="Teenager")')


def test_feed_all_and_heal_all_set_every_fish_to_full():
    commands, fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", amount=2)')
    for f in fish:
        f.hunger = 5.0
        f.health = 5.0
    run_console_command(commands, "feed_all()")
    run_console_command(commands, "heal_all()")
    assert all(f.hunger == 100.0 for f in fish)
    assert all(f.health == 100.0 for f in fish)


def test_happify_all_sets_a_custom_amount_for_every_fish():
    commands, fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", amount=2)')
    run_console_command(commands, "happify_all(amount=30)")
    assert all(f.happiness == 30.0 for f in fish)


def test_list_fish_reports_every_fish_by_name():
    commands, _fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Kitty")')
    output = run_console_command(commands, "list_fish()")
    assert "Steve" in output
    assert "Kitty" in output


def test_list_fish_reports_an_empty_tank():
    commands, _fish, _state, _events = _build_registry()
    output = run_console_command(commands, "list_fish()")
    assert "No fish" in output


def test_describe_command_returns_the_real_tooltip_text():
    commands, _fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    output = run_console_command(commands, 'describe("Steve")')
    assert "Steve" in output


def test_give_treats_command_adds_to_inventory_for_free():
    commands, _fish, state, _events = _build_registry()
    run_console_command(commands, 'give_treats(kind="Pizza", amount=3)')
    assert state["treats"]["Pizza"] == 3


def test_give_treats_command_rejects_an_unknown_kind():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'give_treats(kind="Cake")')


def test_trigger_birthday_command_targets_a_named_fish():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'trigger_birthday(fish_name="Steve")')
    assert ("trigger_birthday_cb", "Steve") in events


def test_bubbles_visit_command_targets_a_named_fish():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'bubbles_visit(fish_name="Steve")')
    assert ("bubbles_visit_cb", "Steve") in events


def test_unlock_achievement_command_rejects_an_unknown_id():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'unlock_achievement(achievement_id="not_a_real_one")')


def test_unlock_achievement_command_fires_the_real_callback():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'unlock_achievement(achievement_id="first_friend")')
    assert ("unlock_achievement_cb", "first_friend") in events


def test_set_storm_true_delegates_to_force_random_event():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, "set_storm(active=True)")
    assert ("force_random_event_cb", "storm") in events


def test_set_storm_false_calls_end_storm():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, "set_storm(active=False)")
    assert ("end_storm_cb",) in events


def test_set_storm_rejects_a_non_boolean():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'set_storm(active="yes")')


def test_set_sound_toggles_state_and_syncs_or_mutes(monkeypatch):
    import examples.aquarium.termquarium.console as console_module

    stopped = []
    monkeypatch.setattr(console_module.sound, "stop_all", lambda: stopped.append(True))
    commands, _fish, state, events = _build_registry()

    run_console_command(commands, "set_sound(enabled=False)")
    assert state["sound_enabled"] is False
    assert stopped == [True]

    run_console_command(commands, "set_sound(enabled=True)")
    assert state["sound_enabled"] is True
    assert ("sync_ambience_cb",) in events


def test_play_sound_rejects_an_unknown_name(monkeypatch):
    import examples.aquarium.termquarium.console as console_module

    monkeypatch.setattr(console_module.sound, "play_sfx", lambda name: None)
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'play_sound(name="not_a_real_sound")')


def test_play_sound_plays_a_real_name(monkeypatch):
    import examples.aquarium.termquarium.console as console_module

    played = []
    monkeypatch.setattr(console_module.sound, "play_sfx", lambda name: played.append(name))
    commands, _fish, _state, _events = _build_registry()
    run_console_command(commands, 'play_sound(name="click")')
    assert played == ["click"]


def test_set_ambience_rejects_an_unknown_name():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'set_ambience(name="lava")')


def test_set_ambience_plays_a_real_track(monkeypatch):
    import examples.aquarium.termquarium.console as console_module

    played = []
    monkeypatch.setattr(
        console_module.sound, "play_ambience", lambda name: played.append(name)
    )
    commands, _fish, _state, _events = _build_registry()
    run_console_command(commands, 'set_ambience(name="storm")')
    assert played == ["storm"]


# ── Multi-statement scripts (what run() used to be a wrapper for) ──────────


def test_a_for_loop_can_call_another_command_per_fish():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Kitty")')
    run_console_command(
        commands, "for f in fish: give_dream(f.display_name, 'happy')"
    )
    assert ("give_dream_cb", "Steve", "happy") in events
    assert ("give_dream_cb", "Kitty", "happy") in events


def test_a_bare_expression_shows_its_printed_output():
    commands, _fish, _state, _events = _build_registry()
    result = run_console_command(commands, "print(1 + 2)")
    assert "3" in result


def test_a_dunder_escape_attempt_is_rejected_at_compile_time():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, "x = ().__class__.__base__.__subclasses__()")


def test_a_runtime_script_error_is_wrapped():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, "1 / 0")


def test_state_can_be_read_but_not_assigned_into():
    # Regression: state["money"] = ... used to write straight into the real
    # economy dict, bypassing set_money's clamp/type-check entirely -- a
    # script could set state["money"] to a negative number or a string
    # (e.g. a typo), later crashing whatever code first does arithmetic on
    # it (state["money"] += sell_value). Reading state must still work.
    commands, _fish, state, _events = _build_registry()
    state["money"] = 100
    result = run_console_command(commands, "print(state['money'])")
    assert "100" in result

    with pytest.raises(ConsoleError):
        run_console_command(commands, "state['money'] = -999")
    assert state["money"] == 100  # untouched -- the real dict, not a copy

    with pytest.raises(ConsoleError):
        run_console_command(commands, "state['money'] = 'oops'")
    assert state["money"] == 100


def test_fish_can_be_read_but_not_assigned_into():
    # Regression: fish[0] = ... used to write straight into the real tank
    # list, and the next frame's draw loop would crash trying to treat a
    # non-Fish value as one. Reading/iterating fish must still work.
    commands, fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    result = run_console_command(commands, "print(fish[0].display_name)")
    assert "Steve" in result

    with pytest.raises(ConsoleError):
        run_console_command(commands, "fish[0] = None")
    assert fish[0].display_name == "Steve"  # untouched -- the real list


def test_help_lists_every_command():
    commands, _fish, _state, _events = _build_registry()
    output = run_console_command(commands, "help()")
    for name in commands:
        if name in ("fish", "state", "random", "math", "find_fish"):
            continue  # not a documented command, just a script global
        assert name in output


def test_bare_help_without_parens_does_not_run_it():
    # A real behavior change from the old parser, which treated a bare
    # word as a zero-arg call -- this is now genuine Python, where a bare
    # name is just a reference to the function object, not a call.
    commands, _fish, _state, _events = _build_registry()
    result = run_console_command(commands, "help")
    assert "function" in result or "<" in result


def test_unknown_command_name_raises_a_clear_error():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError, match="not defined"):
        run_console_command(commands, "nonexistent_command()")


def test_empty_input_raises():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, "")
    with pytest.raises(ConsoleError):
        run_console_command(commands, "   ")
