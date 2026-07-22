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

    def give_nightmare(f):
        events.append(("give_nightmare", f.display_name))

    def give_dream(f, category=None):
        events.append(("give_dream", f.display_name, category))
        return "A Sunny Reef"

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
    assert ("give_nightmare", "Steve") in events


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


def test_help_command_lists_every_command():
    commands, _fish, _state, _events = _build_registry()
    output = run_console_command(commands, "help")
    for name in commands:
        assert name in output


def test_run_console_command_raises_for_an_unknown_command_name():
    commands, _fish, _state, _events = _build_registry()
    with pytest.raises(ConsoleError):
        run_console_command(commands, "nonexistent_command()")
