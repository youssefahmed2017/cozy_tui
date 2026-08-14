"""The Cheat Console (backtick key) -- a dev/testing tool for setting up a
specific scenario in seconds ("does the shark actually eat fish?") instead
of grinding money and raising fish for real every time. Every named command
(spawn_fish, set_health, give_dream, ...) is still parsed the original way:
parse_command() uses ast.parse(mode="eval") structurally and
ast.literal_eval() per-argument, so a typed command can only ever supply
plain literal values -- never call anything, access an attribute, or run
arbitrary code.

The one exception is run(code="..."), for when a single named call isn't
expressive enough (loops, conditionals, touching several fish in one go).
Its `code` string argument is still just a plain literal by the same
parse_command() rule above -- what makes run() different is what happens
to *that string*: it's compiled and executed through RestrictedPython
(see _run_script()), a real sandboxing compiler (used by Zope/Plone) that
rejects dunder/attribute-gadget escapes at compile time, not a hand-rolled
`{"__builtins__": {}}` dict (which doesn't actually stop anything -- the
classic `().__class__.__base__.__subclasses__()` walk reaches arbitrary
classes using nothing but objects already in scope, no builtins needed)."""

import ast
import math
import random
import textwrap
from collections import namedtuple

from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widget import Widget
from cozy_tui.widgets.selection._search_palette import draw_panel_frame

from .constants import (
    CONSOLE_LOG_LIMIT,
    DECORATION_SHOP_ITEMS,
    FOOD_PACK_PRICE,
    FOOD_PACK_SIZE,
    MAX_SPEED,
    MIN_SPEED,
    PERSONALITIES,
    RANDOM_EVENT_NAMES,
    SHOP_ITEMS,
    TRAITS,
    TREAT_SHOP_ITEMS,
)


class ConsoleError(Exception):
    """A user-facing console error -- the message is shown as-is in the
    console's log, never a raw Python traceback."""


def parse_command(text: str):
    """ "name(arg1, kw=val, ...)" or a bare "name" -> (name, positional_args,
    kwargs). Structural parse only (ast.parse(mode="eval")) plus
    ast.literal_eval() per-argument -- this never executes anything, unlike
    eval(). Raises ConsoleError on anything that doesn't parse as that
    shape, or whose arguments aren't plain literals."""
    text = text.strip()
    if not text:
        raise ConsoleError("Type a command, or `help` to see what's available.")
    if "(" not in text:
        return text, [], {}
    try:
        node = ast.parse(text, mode="eval").body
    except SyntaxError:
        raise ConsoleError(f"Couldn't parse: {text!r}")
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        raise ConsoleError("Expected a command like name(arg=value).")
    positional = []
    for arg in node.args:
        try:
            positional.append(ast.literal_eval(arg))
        except (ValueError, SyntaxError):
            raise ConsoleError(
                "Arguments must be plain values (a string or a number), "
                "not expressions."
            )
    kwargs = {}
    for kw in node.keywords:
        if kw.arg is None:  # a **spread -- not a plain literal
            raise ConsoleError(
                "Arguments must be plain values (a string or a number), "
                "not expressions."
            )
        try:
            kwargs[kw.arg] = ast.literal_eval(kw.value)
        except (ValueError, SyntaxError):
            raise ConsoleError(
                f"Argument {kw.arg!r} must be a plain value (a string or a number)."
            )
    return node.func.id, positional, kwargs


Command = namedtuple("Command", "usage handler")


def build_console_commands(
    *,
    state,
    fish,
    add_fish,
    spawn_fish,
    buy_food,
    buy_treat,
    add_decoration,
    refresh_stats,
    set_day_phase,
    spawn_food,
    give_nightmare,
    give_dream,
    grant_trait,
    advance_day,
    start_lost_adventure,
    advance_adventure_day,
    set_happiness,
    set_speed,
    set_personality,
    force_relationship,
    set_day,
    toggle_forest,
    spawn_decoration,
    remove_fish,
    find_legendary,
    force_random_event,
) -> dict:
    """The command registry, closing over the same real state/mutators the
    Shop/Inspector already use (see aquarium.py's main()) -- every command
    is a real effect on the live tank, not a separate cheat-only code path."""

    def _find_species(name):
        species = next(
            (s for s in SHOP_ITEMS if s.name.lower() == str(name).lower()), None
        )
        if species is None:
            names = ", ".join(s.name for s in SHOP_ITEMS)
            raise ConsoleError(f"Unknown species: {name!r}. Try one of: {names}.")
        return species

    def _find_fish(name):
        target = next((f for f in fish if f.display_name == name), None)
        if target is None:
            raise ConsoleError(f"No fish named {name!r} in the tank.")
        return target

    def _require_number(value, what: str) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ConsoleError(f"{what} must be a number.")
        return float(value)

    def cmd_spawn_fish(args, kwargs):
        species_name = kwargs.get("species", args[0] if args else None)
        if species_name is None:
            raise ConsoleError(
                'Usage: spawn_fish(species="Goldfish", name=None, amount=1)'
            )
        species = _find_species(species_name)
        name = kwargs.get("name")
        amount = kwargs.get("amount", 1)
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 1:
            raise ConsoleError("amount must be a positive whole number.")
        amount = min(amount, 20)  # a fat-fingered amount=99999 stays harmless
        spawned = [add_fish(species) for _ in range(amount)]
        if name:
            for f in spawned:
                f.display_name = str(name)
        return f"Spawned {len(spawned)} {species.name}(s)."

    def _set_fish_stat(attr: str, args, kwargs):
        fish_name = kwargs.get("fish_name", args[0] if args else None)
        amount = kwargs.get("amount", args[1] if len(args) > 1 else None)
        if fish_name is None or amount is None:
            raise ConsoleError(f"Usage: set_{attr}(fish_name=..., amount=...)")
        target = _find_fish(str(fish_name))
        clamped = max(0.0, min(100.0, _require_number(amount, "amount")))
        setattr(target, attr, clamped)
        return f"Set {target.display_name}'s {attr} to {clamped:.0f}."

    def cmd_set_health(args, kwargs):
        return _set_fish_stat("health", args, kwargs)

    def cmd_set_hunger(args, kwargs):
        return _set_fish_stat("hunger", args, kwargs)

    def _set_economy(key: str, args, kwargs):
        amount = kwargs.get("amount", args[0] if args else None)
        if amount is None:
            raise ConsoleError(f"Usage: set_{key}(amount=...)")
        state[key] = max(0, int(_require_number(amount, "amount")))
        refresh_stats()
        return f"Set {key} to {state[key]}."

    def cmd_set_money(args, kwargs):
        return _set_economy("money", args, kwargs)

    def cmd_set_food(args, kwargs):
        return _set_economy("food", args, kwargs)

    def _purchase(price: int, callback, message: str) -> str:
        if state["money"] < price:
            raise ConsoleError("Not enough money!")
        state["money"] -= price
        callback()
        refresh_stats()
        return message

    def cmd_buy(args, kwargs):
        item_name = kwargs.get("name", args[0] if args else None)
        if item_name is None:
            raise ConsoleError('Usage: buy(name="Shark")')
        item_name = str(item_name)
        species = next(
            (s for s in SHOP_ITEMS if s.name.lower() == item_name.lower()), None
        )
        if species is not None:
            return _purchase(
                species.price, lambda: spawn_fish(species), f"Bought a {species.name}."
            )
        decoration = next(
            (d for d in DECORATION_SHOP_ITEMS if d.kind.lower() == item_name.lower()),
            None,
        )
        if decoration is not None:
            return _purchase(
                decoration.price,
                lambda: add_decoration(decoration),
                f"Bought a {decoration.kind}.",
            )
        treat = next(
            (t for t in TREAT_SHOP_ITEMS if t.kind.lower() == item_name.lower()), None
        )
        if treat is not None:
            return _purchase(
                treat.price, lambda: buy_treat(treat), f"Bought {treat.kind}."
            )
        if item_name.lower() in ("food", "fish food"):
            return _purchase(
                FOOD_PACK_PRICE, buy_food, f"Bought {FOOD_PACK_SIZE} fish food."
            )
        raise ConsoleError(f"Unknown item: {item_name!r}.")

    def cmd_set_time(args, kwargs):
        phase = kwargs.get("phase", args[0] if args else None)
        if phase is None:
            raise ConsoleError(
                'Usage: set_time("morning" | "afternoon" | "evening" | "night")'
            )
        try:
            label = set_day_phase(str(phase))
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Set the time to {label}."

    def cmd_spawn(args, kwargs):
        kind = kwargs.get("item", args[0] if args else None)
        if kind is None:
            raise ConsoleError('Usage: spawn(item="Pizza", amount=1)')
        amount = kwargs.get("amount", args[1] if len(args) > 1 else 1)
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 1:
            raise ConsoleError("amount must be a positive whole number.")
        amount = min(amount, 50)  # a fat-fingered amount=99999 stays harmless
        try:
            count, label = spawn_food(str(kind), amount)
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Dropped {count} {label} into the tank."

    def cmd_give_nightmare(args, kwargs):
        name = kwargs.get("fish_name", args[0] if args else None)
        if name is None:
            raise ConsoleError(
                'Usage: give_nightmare(fish_name="Steve", '
                'variant="ice" (optional), scare=True (optional))'
            )
        variant = kwargs.get("variant", args[1] if len(args) > 1 else None)
        scare = kwargs.get("scare", args[2] if len(args) > 2 else True)
        target = _find_fish(str(name))
        try:
            give_nightmare(
                target, str(variant) if variant is not None else None, bool(scare)
            )
        except ValueError as error:
            raise ConsoleError(str(error))
        if scare:
            return f"Gave {target.display_name} a nightmare."
        return (
            f"Gave {target.display_name} a lingering nightmare "
            "(watch it while it sleeps)."
        )

    def cmd_give_dream(args, kwargs):
        name = kwargs.get("fish_name", args[0] if args else None)
        if name is None:
            raise ConsoleError('Usage: give_dream(fish_name="Alex", category="happy")')
        category = kwargs.get("category", args[1] if len(args) > 1 else None)
        target = _find_fish(str(name))
        try:
            title = give_dream(target, str(category) if category is not None else None)
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Gave {target.display_name} a dream about {title}."

    def cmd_find_legendary(args, kwargs):
        species_name = kwargs.get("species_name", args[0] if args else None)
        try:
            f = find_legendary(str(species_name) if species_name is not None else None)
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"You found one?? A {f.species_name} appeared in the tank."

    def cmd_force_random_event(args, kwargs):
        event = kwargs.get("event", args[0] if args else None)
        if event is None:
            names = ", ".join(RANDOM_EVENT_NAMES)
            raise ConsoleError(
                f'Usage: force_random_event(event="storm") -- one of: {names}'
            )
        event = str(event)
        try:
            force_random_event(event)
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Fired the {event!r} event."

    def cmd_grant_trait(args, kwargs):
        name = kwargs.get("fish_name", args[0] if args else None)
        trait = kwargs.get("trait", args[1] if len(args) > 1 else None)
        if name is None or trait is None:
            names = ", ".join(TRAITS)
            raise ConsoleError(
                f'Usage: grant_trait(fish_name="Steve", trait="food_lover") '
                f"-- trait is one of: {names}"
            )
        target = _find_fish(str(name))
        try:
            return grant_trait(target, str(trait))
        except ValueError as error:
            raise ConsoleError(str(error))

    def cmd_advance_day(args, kwargs):
        amount = kwargs.get("amount", args[0] if args else 1)
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 1:
            raise ConsoleError("amount must be a positive whole number.")
        amount = min(amount, 100)  # a fat-fingered amount=99999 stays harmless
        for _ in range(amount):
            advance_day()
        return f"Advanced {amount} day(s)." if amount > 1 else "Advanced 1 day."

    def cmd_start_lost_adventure(args, kwargs):
        name = kwargs.get("fish_name", args[0] if args else None)
        if name is None:
            raise ConsoleError(
                'Usage: start_lost_adventure(fish_name="Steve", duration=None '
                "(optional, days))"
            )
        duration = kwargs.get("duration", args[1] if len(args) > 1 else None)
        if duration is not None and (
            not isinstance(duration, int)
            or isinstance(duration, bool)
            or duration < 1
        ):
            raise ConsoleError("duration must be a positive whole number of days.")
        target = _find_fish(str(name))
        if target.lost_adventure is not None:
            raise ConsoleError(f"{target.display_name} is already lost in the forest.")
        start_lost_adventure(target, duration)
        return f"{target.display_name} is now lost in the forest."

    def cmd_advance_adventure_day(args, kwargs):
        name = kwargs.get("fish_name", args[0] if args else None)
        if name is None:
            raise ConsoleError('Usage: advance_adventure_day(fish_name="Steve")')
        target = _find_fish(str(name))
        if target.lost_adventure is None:
            raise ConsoleError(f"{target.display_name} isn't on a Lost Adventure.")
        advance_adventure_day(target)
        return f"Advanced {target.display_name}'s Lost Adventure by one day."

    def cmd_set_happiness(args, kwargs):
        fish_name = kwargs.get("fish_name", args[0] if args else None)
        amount = kwargs.get("amount", args[1] if len(args) > 1 else None)
        if fish_name is None or amount is None:
            raise ConsoleError("Usage: set_happiness(fish_name=..., amount=...)")
        target = _find_fish(str(fish_name))
        set_happiness(target, _require_number(amount, "amount"))
        return f"Set {target.display_name}'s happiness to {target.happiness:.0f}."

    def cmd_set_speed(args, kwargs):
        fish_name = kwargs.get("fish_name", args[0] if args else None)
        amount = kwargs.get("amount", args[1] if len(args) > 1 else None)
        if fish_name is None or amount is None:
            raise ConsoleError("Usage: set_speed(fish_name=..., amount=...)")
        target = _find_fish(str(fish_name))
        set_speed(target, _require_number(amount, "amount"))
        return f"Set {target.display_name}'s speed to {target.speed:.1f}."

    def cmd_set_personality(args, kwargs):
        fish_name = kwargs.get("fish_name", args[0] if args else None)
        personality = kwargs.get("personality", args[1] if len(args) > 1 else None)
        if fish_name is None or personality is None:
            names = ", ".join(PERSONALITIES)
            raise ConsoleError(
                f'Usage: set_personality(fish_name="Steve", personality="Greedy") '
                f"-- one of: {names}"
            )
        target = _find_fish(str(fish_name))
        try:
            set_personality(target, str(personality))
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Set {target.display_name}'s personality to {target.personality}."

    def cmd_force_relationship(args, kwargs):
        a_name = kwargs.get("fish_a", args[0] if args else None)
        b_name = kwargs.get("fish_b", args[1] if len(args) > 1 else None)
        score = kwargs.get("score", args[2] if len(args) > 2 else None)
        if a_name is None or b_name is None or score is None:
            raise ConsoleError(
                'Usage: force_relationship(fish_a="Steve", fish_b="Kitty", score=80)'
            )
        a = _find_fish(str(a_name))
        b = _find_fish(str(b_name))
        clamped = _require_number(score, "score")
        force_relationship(a, b, clamped)
        return f"Set {a.display_name}/{b.display_name}'s relationship score to {clamped:.0f}."

    def cmd_set_day(args, kwargs):
        amount = kwargs.get("amount", args[0] if args else None)
        if (
            amount is None
            or not isinstance(amount, int)
            or isinstance(amount, bool)
            or amount < 0
        ):
            raise ConsoleError("Usage: set_day(amount=...) -- a non-negative whole number")
        set_day(amount)
        return f"Jumped straight to day {amount}."

    def cmd_toggle_forest(args, kwargs):
        unlocked = kwargs.get("unlocked", args[0] if args else None)
        if not isinstance(unlocked, bool):
            raise ConsoleError("Usage: toggle_forest(unlocked=True)")
        toggle_forest(unlocked)
        return "Forest unlocked." if unlocked else "Forest locked."

    def cmd_spawn_decoration(args, kwargs):
        kind = kwargs.get("kind", args[0] if args else None)
        if kind is None:
            names = ", ".join(d.kind for d in DECORATION_SHOP_ITEMS)
            raise ConsoleError(
                f'Usage: spawn_decoration(kind="Castle") -- one of: {names}'
            )
        try:
            kind_name = spawn_decoration(str(kind))
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Spawned a {kind_name}, free of charge."

    def cmd_remove_fish(args, kwargs):
        name = kwargs.get("fish_name", args[0] if args else None)
        if name is None:
            raise ConsoleError('Usage: remove_fish(fish_name="Steve")')
        target = _find_fish(str(name))
        remove_fish(target)
        return f"Removed {target.display_name} from the tank."

    def _script_call(name):
        # Every run() script global is just "call this same named command,
        # with real Python arguments instead of typed console text" -- one
        # code path, one set of validation/errors, not a second parallel
        # implementation per command.
        def _call(*args, **kwargs):
            return commands[name].handler(list(args), kwargs)

        return _call

    def _find_fish_or_none(name):
        return next((f for f in fish if f.display_name == name), None)

    class _ReadOnlyState:
        """A read-only view onto the live `state` dict, exposed to run()
        scripts. Reads (state["money"], state.get(...), "money" in state,
        iteration) all see the same live values as every other command --
        only *writes* are blocked. Without this, `state["money"] = -999`
        (or any type at all -- a string, None) would land directly in the
        real economy dict, bypassing every clamp/type-check the named
        commands (set_money, set_food, ...) apply, and later crash whatever
        code first does arithmetic on it. Change state through those
        commands instead -- they're callable from run() too."""

        def __init__(self, real):
            self._real = real

        def __getitem__(self, key):
            return self._real[key]

        def get(self, key, default=None):
            return self._real.get(key, default)

        def __contains__(self, key):
            return key in self._real

        def __iter__(self):
            return iter(self._real)

        def __len__(self):
            return len(self._real)

        def __setitem__(self, key, value):
            raise ConsoleError(
                "state is read-only in run() -- change it with the matching "
                "command (set_money, set_food, toggle_forest, ...) instead "
                "of assigning state[...] directly."
            )

    class _ReadOnlyFish:
        """A read-only view onto the live `fish` list, exposed to run()
        scripts. Reads (indexing, iteration, len, membership) all see the
        same live fish as every other command -- only *writes* are blocked.
        Without this, `fish[0] = "oops"` (or `.append`/`.clear`/...) would
        land directly in the real tank list, and the next frame's draw loop
        would crash trying to treat a non-Fish value as one. Change the tank
        through spawn_fish/remove_fish instead -- they're callable from
        run() too."""

        def __init__(self, real):
            self._real = real

        def __getitem__(self, key):
            return self._real[key]

        def __iter__(self):
            return iter(self._real)

        def __len__(self):
            return len(self._real)

        def __contains__(self, item):
            return item in self._real

        def __setitem__(self, key, value):
            raise ConsoleError(
                "fish is read-only in run() -- change the tank with "
                "spawn_fish/remove_fish instead of assigning fish[...] "
                "directly."
            )

    # Built once per console session (matches every other closure here) --
    # run() scripts get the *same* fish and the *same* commands as
    # everything else typed into this console, just callable as real
    # function calls instead of one line of structural text each. `state`
    # and `fish` are read-only views (see _ReadOnlyState/_ReadOnlyFish) --
    # scripts change them through the named commands, same as every other
    # console command does.
    script_globals = {
        "fish": _ReadOnlyFish(fish),
        "state": _ReadOnlyState(state),
        "random": random,
        "math": math,
        "find_fish": _find_fish_or_none,
    }
    for _name in (
        "spawn_fish",
        "set_health",
        "set_hunger",
        "set_money",
        "set_food",
        "buy",
        "set_time",
        "spawn",
        "give_nightmare",
        "give_dream",
        "find_legendary",
        "grant_trait",
        "advance_day",
        "start_lost_adventure",
        "advance_adventure_day",
        "set_happiness",
        "set_speed",
        "set_personality",
        "force_relationship",
        "set_day",
        "toggle_forest",
        "spawn_decoration",
        "remove_fish",
        "force_random_event",
    ):
        script_globals[_name] = _script_call(_name)

    def _ensure_restricted_python():
        try:
            import RestrictedPython  # noqa: F401
        except ImportError as error:
            raise ConsoleError(
                "run() needs the RestrictedPython package -- "
                "not installed (pip install RestrictedPython)."
            ) from error

    def _run_script(code: str) -> str:
        # A real sandboxing *compiler*, not a hand-rolled restricted-globals
        # dict: RestrictedPython rejects dunder/attribute-gadget access
        # (the ().__class__.__base__.__subclasses__() family of escapes) at
        # compile time, before the script ever runs -- see this module's
        # docstring. It does not limit CPU time or memory (an intentional
        # `while True: pass` will hang the game); that's an accepted,
        # low-severity gap for a single-player local console -- no worse
        # than a player hanging their own Python REPL.
        _ensure_restricted_python()
        from RestrictedPython import compile_restricted_exec
        from RestrictedPython.Guards import (
            guarded_iter_unpack_sequence,
            safe_builtins,
            safer_getattr,
        )
        from RestrictedPython.PrintCollector import PrintCollector

        result = compile_restricted_exec(code)
        if result.errors:
            raise ConsoleError("; ".join(result.errors))

        # safe_builtins is deliberately minimal (no list/dict/sum/min/max/...)
        # -- these are all pure, I/O-free, well-understood builtins with no
        # introspection risk, added on top rather than missing entirely.
        builtins_dict = dict(safe_builtins)
        builtins_dict.update(
            {
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "sum": sum,
                "min": min,
                "max": max,
                "enumerate": enumerate,
                "any": any,
                "all": all,
                "sorted": sorted,
                "zip": zip,
                "map": map,
                "filter": filter,
            }
        )

        def _write_guard(obj):
            return obj

        def _inplacevar_(op, x, y):
            import operator

            ops = {
                "+=": operator.add,
                "-=": operator.sub,
                "*=": operator.mul,
                "/=": operator.truediv,
            }
            if op not in ops:
                raise ConsoleError(f"Operator {op!r} isn't supported in run().")
            return ops[op](x, y)

        exec_globals = dict(script_globals)
        exec_globals["__builtins__"] = builtins_dict
        exec_globals["_getattr_"] = safer_getattr
        exec_globals["_getitem_"] = lambda obj, index: obj[index]
        exec_globals["_getiter_"] = iter
        exec_globals["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence
        exec_globals["_write_"] = _write_guard
        exec_globals["_inplacevar_"] = _inplacevar_
        exec_globals["_print_"] = PrintCollector

        exec_locals = {}
        try:
            exec(result.code, exec_globals, exec_locals)
        except ConsoleError:
            raise
        except Exception as error:
            raise ConsoleError(f"Script error: {error}")

        printer = exec_locals.get("_print")
        if printer is not None:
            output = str(printer()).rstrip("\n")
            if output:
                return output
        return "Ran."

    def cmd_run(args, kwargs):
        code = kwargs.get("code", args[0] if args else None)
        if code is None:
            raise ConsoleError(
                'Usage: run(code="for f in fish: print(f.display_name)") -- '
                "a snippet of real Python, sandboxed by RestrictedPython"
            )
        return _run_script(str(code))

    def cmd_help(_args, _kwargs):
        return "\n".join(f"{name}: {cmd.usage}" for name, cmd in commands.items())

    commands = {
        "help": Command("list every available command", cmd_help),
        "spawn_fish": Command(
            "spawn_fish(species: name of the species, name: the fish's name "
            "(optional), amount: how many to spawn (optional), default is 1)",
            cmd_spawn_fish,
        ),
        "set_health": Command(
            "set_health(fish_name: the fish to apply this to, amount: the "
            "health it should have, 0-100)",
            cmd_set_health,
        ),
        "set_hunger": Command(
            "set_hunger(fish_name: the fish to apply this to, amount: the "
            "hunger it should have, 0-100 -- 0 is starving, 100 is full)",
            cmd_set_hunger,
        ),
        "set_money": Command(
            "set_money(amount: the amount of money to have)", cmd_set_money
        ),
        "set_food": Command(
            "set_food(amount: the amount of food to have)", cmd_set_food
        ),
        "buy": Command(
            "buy(name: the name of the fish/decoration/treat/food to buy) "
            "-- still costs money, just like the real Shop",
            cmd_buy,
        ),
        "set_time": Command(
            'set_time(phase: "morning", "afternoon", "evening", or "night") '
            "-- jumps the day/night clock to that time of day",
            cmd_set_time,
        ),
        "spawn": Command(
            'spawn(item: a special food like "Pizza", amount: how many '
            "(optional, default 1)) -- drops it in the tank at your mouse for "
            "fish to eat, free (unlike the Shop)",
            cmd_spawn,
        ),
        "give_nightmare": Command(
            "give_nightmare(fish_name: the fish to spook, variant: which bad "
            'dream, e.g. "ice" (optional; random if omitted), scare: True by '
            "default -- pass False to let the bad dream linger so you can watch "
            "it instead of it waking the fish) -- a forced bad dream",
            cmd_give_nightmare,
        ),
        "give_dream": Command(
            "give_dream(fish_name: the fish, category: happy/food/friendship/"
            "home/fantasy (optional)) -- gives it a nice dream to view",
            cmd_give_dream,
        ),
        "find_legendary": Command(
            "find_legendary(species_name: which one, e.g. \"Ghost Fish\" "
            "(optional; random of the 5 if omitted)) -- More Fish's "
            "Legendary tier is found, never bought, so this is the only "
            "way to add one outside the real (very rare) daily roll",
            cmd_find_legendary,
        ),
        "grant_trait": Command(
            "grant_trait(fish_name: the fish, trait: food_lover/dreamer/"
            "fast_swimmer) -- Personality System 2.0's traits, without "
            "waiting on that trait's own rare, chance-based growth trigger",
            cmd_grant_trait,
        ),
        "advance_day": Command(
            "advance_day(amount: how many in-game days to fast-forward "
            "through, optional, default 1) -- runs the real daily tick "
            "(breeding, natural deaths, the Shop's stock rotation, and the "
            "random-event roll) exactly as if that many real days had "
            "passed, so you don't have to wait 6 real minutes per day",
            cmd_advance_day,
        ),
        "start_lost_adventure": Command(
            "start_lost_adventure(fish_name: the fish, duration: how many days "
            "the trip should last (optional, random 4-8 if omitted)) -- forces "
            "the rare 'gets lost in the forest for days' event, without "
            "waiting on its own 2%-per-day roll",
            cmd_start_lost_adventure,
        ),
        "advance_adventure_day": Command(
            "advance_adventure_day(fish_name: the fish, must already be on a "
            "Lost Adventure) -- advances that fish's adventure by exactly one "
            "day, rolling that day's event (shelter/Bubbles/danger/plain "
            "wander) or returning it home if this was the last day",
            cmd_advance_adventure_day,
        ),
        "set_happiness": Command(
            "set_happiness(fish_name: the fish, amount: 0-100)",
            cmd_set_happiness,
        ),
        "set_speed": Command(
            f"set_speed(fish_name: the fish, amount: cells/second, "
            f"{MIN_SPEED}-{MAX_SPEED})",
            cmd_set_speed,
        ),
        "set_personality": Command(
            "set_personality(fish_name: the fish, personality: one of "
            + ", ".join(PERSONALITIES) + ")",
            cmd_set_personality,
        ),
        "force_relationship": Command(
            "force_relationship(fish_a: a fish, fish_b: another fish, score: "
            "-100 to 100) -- sets their relationship score directly instead "
            "of waiting for real events to earn it",
            cmd_force_relationship,
        ),
        "set_day": Command(
            "set_day(amount: the day number to jump straight to) -- unlike "
            "advance_day(), this doesn't run any real daily-tick side effects",
            cmd_set_day,
        ),
        "toggle_forest": Command(
            "toggle_forest(unlocked: True or False) -- force the Forest "
            "unlocked/locked, without paying or waiting",
            cmd_toggle_forest,
        ),
        "spawn_decoration": Command(
            "spawn_decoration(kind: e.g. \"Castle\") -- adds it to the tank "
            "free of charge",
            cmd_spawn_decoration,
        ),
        "remove_fish": Command(
            "remove_fish(fish_name: the fish) -- removes it from the tank "
            "immediately, no toast or memory flavor (unlike natural death/"
            "starvation)",
            cmd_remove_fish,
        ),
        "force_random_event": Command(
            "force_random_event(event: one of "
            + ", ".join(RANDOM_EVENT_NAMES)
            + ") -- fires that day's random event immediately, without "
            "waiting on its own daily roll (fails with an error if that "
            "event isn't currently applicable, e.g. a second storm while "
            "one's already rolling)",
            cmd_force_random_event,
        ),
        "run": Command(
            "run(code: a snippet of real Python, e.g. "
            '\'for f in fish: print(f.display_name)\') -- sandboxed by '
            "RestrictedPython (pip install RestrictedPython); every command "
            "above is also callable as a real function inside it (fish "
            "names as strings, e.g. give_dream(\"Steve\", \"happy\")), plus "
            "fish/state/find_fish()/random/math",
            cmd_run,
        ),
    }
    return commands


def run_console_command(commands: dict, text: str) -> str:
    """Parse and dispatch one typed line against `commands`
    (build_console_commands()'s registry) -- the single entry point
    CheatConsole.on_run is wired to."""
    name, args, kwargs = parse_command(text)
    command = commands.get(name)
    if command is None:
        raise ConsoleError(
            f"Unknown command: {name!r}. Type help to see what's available."
        )
    return command.handler(args, kwargs)


_VISIBLE_LINES = 14
_WIDTH = 64
_WELCOME = (
    "=== Welcome to the TermQuarium Cheat Console ===",
    "Type help to see the available commands.",
    "",
    "Getting started:",
    '  spawn_fish(species="Goldfish")',
)


class CheatConsole(Widget):
    """A self-contained modal console (own text buffer, own scrollback, own
    draw()), the same "no child Input/ListView" shape as PromptDialog/
    ConfirmDialog -- a modal routes every key straight to this one widget,
    so splitting the typing half and the scrollback half into two child
    widgets would need a hand-written wrapper deciding which key goes where
    anyway, for no less code. `on_run(text) -> str` (raising ConsoleError
    for a user-facing problem) is the only thing the caller needs to
    supply -- see aquarium.py's _open_console()."""

    focusable = True

    def __init__(self, on_run, *, width: int = _WIDTH, style=None):
        super().__init__(0, 0, style or Style(fg="white", bg="black"))
        self.on_run = on_run
        self.width = max(20, width)
        self.buffer = ""
        self.lines: list[tuple[str, bool]] = []  # (text, is_error)
        self._history: list[str] = []
        self._history_index = None

    def natural_width(self, scale) -> int:
        return self.width + 2

    def natural_height(self, scale) -> int:
        return _VISIBLE_LINES + 5  # border(2) + title + input + hint

    def contains(self, col: int, row: int) -> bool:
        return self.abs_x <= col < self.abs_x + self.natural_width(
            1
        ) and self.abs_y <= row < self.abs_y + self.natural_height(1)

    def _emit(self, text: str, is_error: bool) -> None:
        # Word-wrap into the panel's own interior width -- without this, a
        # long line (help()'s usage strings, an "> {typed command}" echo)
        # either got silently truncated (ljust(w)[:w] in draw()) or, worse,
        # multiple newline-joined lines (help()'s own "\n".join(...)) landed
        # in *one* `lines` entry and rendered as one run-together row.
        wrap_width = max(1, self.width - 2)
        for raw_line in text.split("\n"):
            for wrapped in textwrap.wrap(raw_line, width=wrap_width) or [""]:
                self.lines.append((wrapped, is_error))

    def _run(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        self._emit(f"> {text}", False)
        self._history.append(text)
        del self._history[:-CONSOLE_LOG_LIMIT]
        self._history_index = None
        try:
            result = self.on_run(text)
            if result:
                self._emit(result, False)
        except ConsoleError as error:
            self._emit(str(error), True)
        del self.lines[:-CONSOLE_LOG_LIMIT]

    def on_key(self, key) -> None:
        if key == Key.ENTER:
            self._run(self.buffer)
            self.buffer = ""
        elif key == Key.BACKSPACE:
            self.buffer = self.buffer[:-1]
        elif key == Key.UP:
            if self._history:
                self._history_index = (
                    len(self._history) - 1
                    if self._history_index is None
                    else max(0, self._history_index - 1)
                )
                self.buffer = self._history[self._history_index]
        elif key == Key.DOWN:
            if self._history_index is not None:
                self._history_index += 1
                if self._history_index >= len(self._history):
                    self._history_index = None
                    self.buffer = ""
                else:
                    self.buffer = self._history[self._history_index]
        elif isinstance(key, str) and len(key) == 1 and key.isprintable():
            self.buffer += key

    def _palette(self):
        from cozy_tui.theme import get_theme  # local: theme.py builds on Style

        raw_bg = self.style.raw_bg
        border = Style(fg=get_theme().accent, bg=raw_bg, styles=["bold"])
        error = Style(fg="bright_red", bg=raw_bg)
        dim = Style(fg="bright_black", bg=raw_bg)
        return self.style, border, error, dim

    def draw(self, canvas) -> None:
        panel, border, error_style, dim = self._palette()
        x, y, w = self.abs_x, self.abs_y, self.width
        h = self.natural_height(1)
        draw_panel_frame(canvas, x, y, w, h, border, panel)
        canvas.write(x + 1, y + 1, " Cheat Console".ljust(w)[:w], border)

        body = self.lines if self.lines else [(line, False) for line in _WELCOME]
        for row, (text, is_error) in enumerate(body[-_VISIBLE_LINES:]):
            style = error_style if is_error else panel
            canvas.write(x + 1, y + 2 + row, (" " + text).ljust(w)[:w], style)

        input_row = y + 2 + _VISIBLE_LINES
        line = "> " + self.buffer
        line = line[-(w - 2) :] if len(line) > w - 2 else line
        canvas.write(x + 1, input_row, (" " + line + "▏").ljust(w)[:w], panel)
        canvas.write(
            x + 1,
            input_row + 1,
            "  Enter: run    Esc: close    Up/Down: history".ljust(w)[:w],
            dim,
        )
