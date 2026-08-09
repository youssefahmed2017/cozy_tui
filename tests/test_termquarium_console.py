"""Tests for the Cheat Console's command parser and command registry
(examples/aquarium/termquarium/console.py) -- pure logic, no App/overlay
plumbing needed (see tests/test_aquarium.py for the headless-app-level
integration tests: opening the console via the backtick key, typing into
the real CheatConsole widget, etc.)."""

import pytest

from examples.aquarium.termquarium.console import (
    ConsoleError,
    build_console_commands,
    parse_command,
    run_console_command,
)
from examples.aquarium.termquarium.fish import Fish

# ── parse_command(): structural parsing only, never eval()/exec() ──────────


def test_parse_command_handles_a_bare_command():
    assert parse_command("help") == ("help", [], {})


def test_parse_command_handles_positional_string_args():
    assert parse_command('buy("Shark")') == ("buy", ["Shark"], {})


def test_parse_command_handles_keyword_args():
    name, args, kwargs = parse_command(
        'spawn_fish(species="Goldfish", name="Steven", amount=2)'
    )
    assert name == "spawn_fish"
    assert args == []
    assert kwargs == {"species": "Goldfish", "name": "Steven", "amount": 2}


def test_parse_command_handles_mixed_positional_and_keyword_args():
    assert parse_command('set_health("Steven", 50)') == (
        "set_health",
        ["Steven", 50],
        {},
    )


def test_parse_command_handles_numbers():
    assert parse_command("set_money(1000)") == ("set_money", [1000], {})


def test_parse_command_rejects_empty_input():
    with pytest.raises(ConsoleError):
        parse_command("")


def test_parse_command_rejects_non_call_syntax():
    # No "(" at all -- read as a bare command name (rejected later, by
    # run_console_command's registry lookup, as "unknown command").
    assert parse_command("1 + 1") == ("1 + 1", [], {})
    # Has a "(" but isn't a call -- this is where parse_command itself
    # must reject it.
    with pytest.raises(ConsoleError):
        parse_command("(1 + 1)")


def test_parse_command_rejects_a_function_call_as_an_argument():
    # Proves no code execution is possible: os.system(...) is a Call node,
    # never literal-evaluable, so this must be rejected, not silently run.
    with pytest.raises(ConsoleError):
        parse_command("set_money(amount=os.system('x'))")


def test_parse_command_rejects_a_bare_name_reference_as_an_argument():
    with pytest.raises(ConsoleError):
        parse_command("set_money(amount=some_variable)")


# ── build_console_commands() / run_console_command(): the registry ─────────


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
    state = {"money": 100, "food": 10}
    events = []

    def add_fish(species):
        f = _fake_fish(species.name)
        fish.append(f)
        return f

    def spawn_fish(species):
        events.append(("spawn_fish", species.name))

    def buy_food():
        events.append(("buy_food",))

    def buy_treat(item):
        events.append(("buy_treat", item.kind))

    def add_decoration(item):
        events.append(("add_decoration", item.kind))

    def refresh_stats():
        events.append(("refresh_stats",))

    def set_day_phase(phase):
        if phase.lower() not in ("day", "morning", "night"):
            raise ValueError("bad phase")
        events.append(("set_day_phase", phase))
        return phase.capitalize()

    def spawn_food(kind, amount):
        if kind.lower() != "pizza":
            raise ValueError("unknown food")
        events.append(("spawn_food", kind, amount))
        return amount, "Pizza"

    def give_nightmare(f, variant=None, scare=True):
        events.append(("give_nightmare", f.display_name, variant, scare))
        if variant is not None and variant.lower() not in ("ice", "shark"):
            raise ValueError(f"No 'bad' dream matching {variant!r}.")

    def give_dream(f, category=None):
        events.append(("give_dream", f.display_name, category))
        return "A Sunny Reef"

    def grant_trait(f, trait):
        events.append(("grant_trait", f.display_name, trait))
        if trait not in ("food_lover", "dreamer", "fast_swimmer"):
            raise ValueError(f"Unknown trait: {trait!r}.")
        return f"Gave {f.display_name} the {trait} trait."

    def advance_day():
        events.append(("advance_day",))

    def start_lost_adventure(f, duration=None):
        f.lost_adventure = {"day": 0, "duration": duration or 5}
        events.append(("start_lost_adventure", f.display_name, duration))

    def advance_adventure_day(f):
        events.append(("advance_adventure_day", f.display_name))

    def set_happiness(f, amount):
        f.happiness = max(0.0, min(100.0, amount))
        events.append(("set_happiness", f.display_name, amount))

    def set_speed(f, amount):
        f.speed = max(2.5, min(6.0, amount))
        events.append(("set_speed", f.display_name, amount))

    def set_personality(f, personality):
        if personality not in ("Friendly", "Explorer", "Shy", "Greedy", "Lazy", "Playful"):
            raise ValueError(f"Unknown personality: {personality!r}.")
        f.personality = personality
        events.append(("set_personality", f.display_name, personality))

    def force_relationship(a, b, score):
        events.append(("force_relationship", a.display_name, b.display_name, score))

    def set_day(amount):
        events.append(("set_day", amount))

    def toggle_forest(unlocked):
        state["forest_unlocked"] = unlocked
        events.append(("toggle_forest", unlocked))

    def spawn_decoration(kind):
        if kind not in ("Castle", "Rock"):
            raise ValueError(f"Unknown decoration: {kind!r}.")
        events.append(("spawn_decoration", kind))
        return kind

    def remove_fish(f):
        if f in fish:
            fish.remove(f)
        events.append(("remove_fish", f.display_name))

    commands = build_console_commands(
        state=state,
        fish=fish,
        add_fish=add_fish,
        spawn_fish=spawn_fish,
        buy_food=buy_food,
        buy_treat=buy_treat,
        add_decoration=add_decoration,
        refresh_stats=refresh_stats,
        set_day_phase=set_day_phase,
        spawn_food=spawn_food,
        give_nightmare=give_nightmare,
        give_dream=give_dream,
        grant_trait=grant_trait,
        advance_day=advance_day,
        start_lost_adventure=start_lost_adventure,
        advance_adventure_day=advance_adventure_day,
        set_happiness=set_happiness,
        set_speed=set_speed,
        set_personality=set_personality,
        force_relationship=force_relationship,
        set_day=set_day,
        toggle_forest=toggle_forest,
        spawn_decoration=spawn_decoration,
        remove_fish=remove_fish,
    )
    return commands, fish, state, events


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
    assert ("refresh_stats",) in events


def test_buy_command_deducts_price_and_calls_the_real_purchase_path():
    commands, _fish, state, events = _build_registry()
    state["money"] = 1000
    run_console_command(commands, 'buy("Shark")')
    assert state["money"] == 1000 - 500  # Shark's Shop price
    assert ("spawn_fish", "Shark") in events


def test_buy_command_raises_when_money_is_insufficient():
    commands, _fish, state, events = _build_registry()
    state["money"] = 0
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'buy("Shark")')
    assert state["money"] == 0  # untouched
    assert not any(e[0] == "spawn_fish" for e in events)


def test_buy_command_works_for_decorations_treats_and_food():
    commands, _fish, state, events = _build_registry()
    state["money"] = 1000
    run_console_command(commands, 'buy("Castle")')
    run_console_command(commands, 'buy("Pizza")')
    run_console_command(commands, 'buy("Food")')
    assert ("add_decoration", "Castle") in events
    assert ("buy_treat", "Pizza") in events
    assert ("buy_food",) in events


def test_buy_command_rejects_an_unknown_item():
    commands, _fish, state, _events = _build_registry()
    state["money"] = 1000
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'buy("Nonexistent Thing")')


def test_set_time_command_accepts_the_three_phases():
    commands, _fish, _state, events = _build_registry()
    for phase in ("day", "morning", "night"):
        run_console_command(commands, f'set_time("{phase}")')
    assert [e for e in events if e[0] == "set_day_phase"] == [
        ("set_day_phase", "day"),
        ("set_day_phase", "morning"),
        ("set_day_phase", "night"),
    ]


def test_set_time_command_rejects_a_bad_phase():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'set_time("lunchtime")')


def test_spawn_command_drops_special_food():
    commands, _fish, _state, events = _build_registry()
    result = run_console_command(commands, 'spawn("pizza", 3)')
    assert ("spawn_food", "pizza", 3) in events
    assert "3 Pizza" in result


def test_spawn_command_defaults_amount_to_one_and_clamps_huge_amounts():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn("pizza")')
    run_console_command(commands, 'spawn("pizza", 99999)')
    assert ("spawn_food", "pizza", 1) in events
    assert ("spawn_food", "pizza", 50) in events  # clamped


def test_spawn_command_rejects_unknown_food():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'spawn("gravel")')


def test_give_nightmare_command_targets_a_named_fish():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'give_nightmare("Steve")')
    assert ("give_nightmare", "Steve", None, True) in events


def test_give_nightmare_command_can_force_a_specific_variant():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'give_nightmare("Steve", "ice")')
    assert ("give_nightmare", "Steve", "ice", True) in events
    # keyword form works too
    run_console_command(commands, 'give_nightmare(fish_name="Steve", variant="ice")')
    assert events.count(("give_nightmare", "Steve", "ice", True)) == 2


def test_give_nightmare_command_can_let_the_dream_linger():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    result = run_console_command(
        commands, 'give_nightmare("Steve", "ice", scare=False)'
    )
    assert ("give_nightmare", "Steve", "ice", False) in events
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
    assert ("give_dream", "Alex", None) in events
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
    assert ("start_lost_adventure", "Steve", None) in events
    assert fish[0].lost_adventure is not None


def test_start_lost_adventure_command_accepts_an_explicit_duration():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(
        commands, 'start_lost_adventure(fish_name="Steve", duration=3)'
    )
    assert ("start_lost_adventure", "Steve", 3) in events


def test_start_lost_adventure_command_rejects_a_non_positive_duration():
    commands, _fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    with pytest.raises(ConsoleError):
        run_console_command(
            commands, 'start_lost_adventure(fish_name="Steve", duration=0)'
        )


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
    assert ("advance_adventure_day", "Steve") in events


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
    assert ("set_speed", "Steve", 4.0) in events
    assert fish[0].speed == 4.0


def test_set_personality_command_rejects_an_unknown_personality():
    commands, _fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    with pytest.raises(ConsoleError):
        run_console_command(
            commands, 'set_personality(fish_name="Steve", personality="Grumpy")'
        )


def test_set_personality_command_sets_a_valid_personality():
    commands, fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(
        commands, 'set_personality(fish_name="Steve", personality="Greedy")'
    )
    assert fish[0].personality == "Greedy"


def test_force_relationship_command_targets_two_named_fish():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Kitty")')
    run_console_command(
        commands, 'force_relationship(fish_a="Steve", fish_b="Kitty", score=80)'
    )
    assert ("force_relationship", "Steve", "Kitty", 80.0) in events


def test_set_day_command_rejects_a_negative_amount():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, "set_day(amount=-1)")


def test_set_day_command_jumps_the_counter():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, "set_day(amount=50)")
    assert ("set_day", 50) in events


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
    assert ("spawn_decoration", "Castle") in events


def test_remove_fish_command_removes_it_from_the_tank():
    commands, fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    assert len(fish) == 1
    run_console_command(commands, 'remove_fish(fish_name="Steve")')
    assert fish == []
    assert ("remove_fish", "Steve") in events


def test_remove_fish_command_raises_for_an_unknown_fish():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'remove_fish(fish_name="Ghost")')


# ── run(): RestrictedPython-sandboxed scripting ─────────────────────────────


def test_run_command_can_loop_over_fish_and_call_another_command():
    commands, _fish, _state, events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Kitty")')
    run_console_command(
        commands,
        'run(code="for f in fish: give_dream(f.display_name, \'happy\')")',
    )
    assert ("give_dream", "Steve", "happy") in events
    assert ("give_dream", "Kitty", "happy") in events


def test_run_command_returns_printed_output():
    commands, _fish, _state, _events = _build_registry()
    result = run_console_command(commands, 'run(code="print(1 + 2)")')
    assert "3" in result


def test_run_command_rejects_a_dunder_escape_attempt_at_compile_time():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(
            commands,
            'run(code="x = ().__class__.__base__.__subclasses__()")',
        )


def test_run_command_wraps_a_runtime_script_error():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, 'run(code="1 / 0")')


def test_run_command_can_read_state_but_not_assign_into_it():
    # Regression: state["money"] = ... used to write straight into the real
    # economy dict, bypassing set_money's clamp/type-check entirely -- a
    # script could set state["money"] to a negative number or a string
    # (e.g. a typo), later crashing whatever code first does arithmetic on
    # it (state["money"] += sell_value). Reading state must still work.
    commands, _fish, state, _events = _build_registry()
    state["money"] = 100
    result = run_console_command(
        commands, 'run(code="print(state[\'money\'])")'
    )
    assert "100" in result

    with pytest.raises(ConsoleError):
        run_console_command(commands, 'run(code="state[\'money\'] = -999")')
    assert state["money"] == 100  # untouched -- the real dict, not a copy

    with pytest.raises(ConsoleError):
        run_console_command(commands, 'run(code="state[\'money\'] = \'oops\'")')
    assert state["money"] == 100


def test_run_command_can_read_fish_but_not_assign_into_it():
    # Regression: fish[0] = ... used to write straight into the real tank
    # list, and the next frame's draw loop would crash trying to treat a
    # non-Fish value as one. Reading/iterating fish must still work.
    commands, fish, _state, _events = _build_registry()
    run_console_command(commands, 'spawn_fish(species="Goldfish", name="Steve")')
    result = run_console_command(
        commands, 'run(code="print(fish[0].display_name)")'
    )
    assert "Steve" in result

    with pytest.raises(ConsoleError):
        run_console_command(commands, 'run(code="fish[0] = None")')
    assert fish[0].display_name == "Steve"  # untouched -- the real list


def test_run_command_requires_a_code_argument():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, "run()")


def test_run_command_reports_missing_restrictedpython_clearly(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "RestrictedPython", None)
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError, match="RestrictedPython"):
        run_console_command(commands, 'run(code="print(1)")')


def test_help_command_lists_every_command():
    commands, _fish, _state, _events = _build_registry()
    output = run_console_command(commands, "help")
    for name in commands:
        assert name in output


def test_run_console_command_raises_for_an_unknown_command_name():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, "nonexistent_command()")
