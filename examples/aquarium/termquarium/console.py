"""The Cheat Console (backtick key) -- a dev/testing tool for setting up a
specific scenario in seconds ("does the shark actually eat fish?") instead
of grinding money and raising fish for real every time.

The console *is* RestrictedPython now, not a hand-rolled parser that also
happens to have a run() escape hatch bolted on. Every line typed is
compiled and executed through RestrictedPython (see run_console_command())
-- a real sandboxing compiler (used by Zope/Plone) that rejects dunder/
attribute-gadget escapes (the ().__class__.__base__.__subclasses__() family)
at compile time, not a hand-rolled `{"__builtins__": {}}` dict, which
doesn't actually stop anything. RestrictedPython is a hard dependency of
this module now (not lazily imported for one command) -- the console
simply doesn't work without it.

Every named command below (spawn_fish, set_health, ...) is a plain Python
function with a real signature (defaults, positional-or-keyword, ...) --
typing `spawn_fish(species="Goldfish", amount=2)` calls it exactly the way
Python itself would, no separate arg-extraction layer to keep in sync. A
single typed expression (a bare call, most of the time) is eval()'d and its
return value is shown directly; anything that isn't a single expression
(a loop, an assignment, several statements) falls back to exec(), with
print() captured and shown instead -- there is no longer a separate run()
command for this, real Python already does both jobs. `help()` lists every
command from its own docstring, so a command's usage text and its actual
signature can never drift apart the way two hand-maintained copies could.
"""

import math
import operator
import random
import textwrap
import time

from cozy_tui.events import Key
from cozy_tui.style import Style
from cozy_tui.widget import Widget
from cozy_tui.widgets.selection._search_palette import draw_panel_frame
from RestrictedPython import compile_restricted_eval, compile_restricted_exec
from RestrictedPython.Guards import guarded_iter_unpack_sequence, safe_builtins, safer_getattr
from RestrictedPython.PrintCollector import PrintCollector

from .constants import (
    ACHIEVEMENTS,
    AGE_SECONDS_PER_DAY,
    CALENDAR_YEAR_DAYS,
    CONSOLE_LOG_LIMIT,
    DECORATION_SHOP_ITEMS,
    FOOD_PACK_PRICE,
    FOOD_PACK_SIZE,
    GROWTH_STAGES,
    MAX_SPEED,
    MIN_SPEED,
    PERSONALITIES,
    RANDOM_EVENT_NAMES,
    SHOP_ITEMS,
    TRAITS,
    TREAT_SHOP_ITEMS,
)
from .fish import describe_fish
from . import sound


class ConsoleError(Exception):
    """A user-facing console error -- the message is shown as-is in the
    console's log, never a raw Python traceback."""


# ── Command registry ─────────────────────────────────────────────────────


def build_console_commands(
    *,
    state,
    fish,
    add_fish_cb,
    spawn_fish_cb,
    buy_food_cb,
    buy_treat_cb,
    add_decoration_cb,
    refresh_stats_cb,
    set_day_phase_cb,
    spawn_food_cb,
    give_nightmare_cb,
    give_dream_cb,
    grant_trait_cb,
    advance_day_cb,
    start_lost_adventure_cb,
    advance_adventure_day_cb,
    set_happiness_cb,
    set_speed_cb,
    set_personality_cb,
    force_relationship_cb,
    set_day_cb,
    toggle_forest_cb,
    spawn_decoration_cb,
    remove_fish_cb,
    find_legendary_cb,
    force_random_event_cb,
    trigger_birthday_cb,
    bubbles_visit_cb,
    end_storm_cb,
    unlock_achievement_cb,
    sync_ambience_cb,
) -> dict:
    """The script-globals namespace RestrictedPython-compiled console text
    actually runs against -- every command closes over the same real
    state/mutators the Shop/Inspector already use (see aquarium.py's
    main()), so every command is a real effect on the live tank, not a
    separate cheat-only code path. The `_cb` suffix on every parameter here
    is deliberate: it's the raw aquarium.py mutator, kept distinct from the
    nicer-named, docstringed function below that actually gets exposed to
    typed console text (e.g. `advance_day_cb` the mutator vs. `advance_day`
    the command) -- giving both the same name would shadow one with the
    other in this function's own scope."""

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

    def _find_fish_or_none(name):
        return next((f for f in fish if f.display_name == name), None)

    def _require_number(value, what: str) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ConsoleError(f"{what} must be a number.")
        return float(value)

    def _positive_int(value, what: str, cap: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ConsoleError(f"{what} must be a positive whole number.")
        return min(value, cap)  # a fat-fingered amount=99999 stays harmless

    # ── Fish ─────────────────────────────────────────────────────────────

    def spawn_fish(species, name=None, amount=1):
        """spawn_fish(species, name=None, amount=1) -- adds `amount` of that
        species to the tank, free of charge, optionally all sharing `name`."""
        target_species = _find_species(species)
        amount = _positive_int(amount, "amount", 20)
        spawned = [add_fish_cb(target_species) for _ in range(amount)]
        if name:
            for f in spawned:
                f.display_name = str(name)
        return f"Spawned {len(spawned)} {target_species.name}(s)."

    def set_health(fish_name, amount):
        """set_health(fish_name, amount) -- amount is 0-100."""
        target = _find_fish(str(fish_name))
        target.health = max(0.0, min(100.0, _require_number(amount, "amount")))
        return f"Set {target.display_name}'s health to {target.health:.0f}."

    def set_hunger(fish_name, amount):
        """set_hunger(fish_name, amount) -- amount is 0-100 (0 starving, 100
        full)."""
        target = _find_fish(str(fish_name))
        target.hunger = max(0.0, min(100.0, _require_number(amount, "amount")))
        return f"Set {target.display_name}'s hunger to {target.hunger:.0f}."

    def set_happiness(fish_name, amount):
        """set_happiness(fish_name, amount) -- amount is 0-100."""
        target = _find_fish(str(fish_name))
        set_happiness_cb(target, _require_number(amount, "amount"))
        return f"Set {target.display_name}'s happiness to {target.happiness:.0f}."

    def set_speed(fish_name, amount):
        target = _find_fish(str(fish_name))
        set_speed_cb(target, _require_number(amount, "amount"))
        return f"Set {target.display_name}'s speed to {target.speed:.1f}."

    # A plain "docstring" literal can't be built with .format()/an f-string --
    # only a bare string constant is recognized as __doc__ at all (anything
    # else, like a .format() call, is just an expression statement that gets
    # evaluated and discarded, leaving __doc__ None). Assigning the attribute
    # directly after each def is what lets these still fold in the real
    # constants (MIN_SPEED, PERSONALITIES, ...) instead of a stale hand-typed
    # copy of them.
    set_speed.__doc__ = (
        f"set_speed(fish_name, amount) -- cells/second, {MIN_SPEED}-{MAX_SPEED}."
    )

    def set_personality(fish_name, personality):
        target = _find_fish(str(fish_name))
        try:
            set_personality_cb(target, str(personality))
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Set {target.display_name}'s personality to {target.personality}."

    set_personality.__doc__ = (
        "set_personality(fish_name, personality) -- one of: "
        + ", ".join(PERSONALITIES)
    )

    def grant_trait(fish_name, trait):
        target = _find_fish(str(fish_name))
        try:
            return grant_trait_cb(target, str(trait))
        except ValueError as error:
            raise ConsoleError(str(error))

    grant_trait.__doc__ = (
        "grant_trait(fish_name, trait) -- Personality System 2.0's traits "
        "(one of: " + ", ".join(TRAITS) + "), without waiting on that "
        "trait's own rare, chance-based growth trigger."
    )

    def remove_fish(fish_name):
        """remove_fish(fish_name) -- removes it from the tank immediately, no
        toast or memory flavor (unlike natural death/starvation)."""
        target = _find_fish(str(fish_name))
        remove_fish_cb(target)
        return f"Removed {target.display_name} from the tank."

    def set_age(fish_name, days):
        """set_age(fish_name, days) -- directly sets how many age_days old
        that fish is (backdates its birth time), so you don't have to wait
        for a growth stage, reflection memory, or birthday threshold."""
        target = _find_fish(str(fish_name))
        amount = _require_number(days, "days")
        if amount < 0:
            raise ConsoleError("days must be zero or positive.")
        target.birth_time = time.monotonic() - AGE_SECONDS_PER_DAY * amount
        return (
            f"{target.display_name} is now {amount:.1f} age_days old "
            f"({target.growth_stage})."
        )

    def set_growth_stage(fish_name, stage):
        """set_growth_stage(fish_name, stage) -- jumps straight to Baby/
        Juvenile/Adult/Elder (matched case-insensitively) instead of waiting
        for real age_days to pass."""
        target = _find_fish(str(fish_name))
        wanted = str(stage).strip().lower()
        match = next(
            (
                min_age
                for name, min_age, _mult in GROWTH_STAGES
                if name.split()[0].lower() == wanted
            ),
            None,
        )
        if match is None:
            names = ", ".join(name.split()[0] for name, _a, _m in GROWTH_STAGES)
            raise ConsoleError(f"Unknown growth stage: {stage!r}. Try: {names}.")
        target.birth_time = time.monotonic() - AGE_SECONDS_PER_DAY * (match + 0.5)
        return f"{target.display_name} is now {target.growth_stage}."

    def feed_all():
        """feed_all() -- sets every fish's hunger to full (100)."""
        for f in fish:
            f.hunger = 100.0
        return f"Fed all {len(fish)} fish to full."

    def heal_all():
        """heal_all() -- sets every fish's health to full (100)."""
        for f in fish:
            f.health = 100.0
        return f"Healed all {len(fish)} fish to full."

    def happify_all(amount=100):
        """happify_all(amount=100) -- sets every fish's happiness to
        `amount` (0-100)."""
        clamped = max(0.0, min(100.0, _require_number(amount, "amount")))
        for f in fish:
            f.happiness = clamped
        return f"Set happiness to {clamped:.0f} for all {len(fish)} fish."

    def list_fish():
        """list_fish() -- every fish currently in the tank, one per line:
        name, species, growth stage, happiness."""
        if not fish:
            return "No fish in the tank."
        return "\n".join(
            f"{f.display_name} ({f.species_name}, {f.growth_stage}, "
            f"happiness {f.happiness:.0f})"
            for f in fish
        )

    def describe(fish_name):
        """describe(fish_name) -- a one-line summary (species, growth stage,
        personality, fullness, relationship hint) -- the same text the
        tank's own tooltip shows."""
        return describe_fish(_find_fish(str(fish_name)))

    # ── Economy / Shop ───────────────────────────────────────────────────

    def set_money(amount):
        """set_money(amount) -- sets your money directly."""
        state["money"] = max(0, int(_require_number(amount, "amount")))
        refresh_stats_cb()
        return f"Set money to {state['money']}."

    def set_food(amount):
        """set_food(amount) -- sets your fish food directly."""
        state["food"] = max(0, int(_require_number(amount, "amount")))
        refresh_stats_cb()
        return f"Set food to {state['food']}."

    def _purchase(price: int, callback, message: str) -> str:
        if state["money"] < price:
            raise ConsoleError("Not enough money!")
        state["money"] -= price
        callback()
        refresh_stats_cb()
        return message

    def buy(name):
        """buy(name) -- buys a fish/decoration/treat/food by name, spending
        real money, just like the Shop."""
        item_name = str(name)
        species = next(
            (s for s in SHOP_ITEMS if s.name.lower() == item_name.lower()), None
        )
        if species is not None:
            return _purchase(
                species.price,
                lambda: spawn_fish_cb(species),
                f"Bought a {species.name}.",
            )
        decoration = next(
            (d for d in DECORATION_SHOP_ITEMS if d.kind.lower() == item_name.lower()),
            None,
        )
        if decoration is not None:
            return _purchase(
                decoration.price,
                lambda: add_decoration_cb(decoration),
                f"Bought a {decoration.kind}.",
            )
        treat = next(
            (t for t in TREAT_SHOP_ITEMS if t.kind.lower() == item_name.lower()), None
        )
        if treat is not None:
            return _purchase(
                treat.price, lambda: buy_treat_cb(treat), f"Bought {treat.kind}."
            )
        if item_name.lower() in ("food", "fish food"):
            return _purchase(
                FOOD_PACK_PRICE, buy_food_cb, f"Bought {FOOD_PACK_SIZE} fish food."
            )
        raise ConsoleError(f"Unknown item: {item_name!r}.")

    def give_treats(kind, amount=5):
        """give_treats(kind, amount=5) -- adds treats straight to your
        inventory, free (unlike buy())."""
        item = next(
            (t for t in TREAT_SHOP_ITEMS if t.kind.lower() == str(kind).lower()), None
        )
        if item is None:
            names = ", ".join(t.kind for t in TREAT_SHOP_ITEMS)
            raise ConsoleError(f"Unknown treat: {kind!r}. Try one of: {names}.")
        n = _positive_int(amount, "amount", 999)
        state["treats"][item.kind] = state["treats"].get(item.kind, 0) + n
        refresh_stats_cb()
        return f"Added {n} {item.kind} to your inventory, free of charge."

    def spawn(item, amount=1):
        """spawn(item, amount=1) -- drops a special food (e.g. "Pizza") in
        the tank at your mouse for fish to eat, free (unlike the Shop)."""
        n = _positive_int(amount, "amount", 50)
        try:
            count, label = spawn_food_cb(str(item), n)
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Dropped {count} {label} into the tank."

    def spawn_decoration(kind):
        """spawn_decoration(kind) -- adds it to the tank free of charge."""
        try:
            kind_name = spawn_decoration_cb(str(kind))
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Spawned a {kind_name}, free of charge."

    def find_legendary(species_name=None):
        """find_legendary(species_name=None) -- More Fish's Legendary tier is
        found, never bought, so this is the only way to add one outside the
        real (very rare) daily roll. Random of the 5 if omitted."""
        try:
            f = find_legendary_cb(str(species_name) if species_name else None)
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"You found one?? A {f.species_name} appeared in the tank."

    def unlock_achievement(achievement_id):
        if achievement_id not in (a.id for a in ACHIEVEMENTS):
            names = ", ".join(a.id for a in ACHIEVEMENTS)
            raise ConsoleError(f"Unknown achievement: {achievement_id!r}. Try: {names}.")
        unlock_achievement_cb(achievement_id)
        return f"Unlocked {achievement_id!r}."

    unlock_achievement.__doc__ = (
        "unlock_achievement(achievement_id) -- unlocks it immediately "
        "(idempotent -- a no-op if already unlocked). One of: "
        + ", ".join(a.id for a in ACHIEVEMENTS)
    )

    # ── Time / world ─────────────────────────────────────────────────────

    def set_time(phase):
        """set_time(phase) -- "morning", "afternoon", "evening", or "night"
        -- jumps the day/night clock to that time of day."""
        try:
            label = set_day_phase_cb(str(phase))
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Set the time to {label}."

    def advance_day(amount=1):
        """advance_day(amount=1) -- runs the real daily tick (breeding,
        natural deaths, the Shop's stock rotation, the random-event roll)
        exactly as if that many real days had passed, so you don't have to
        wait 6 real minutes per day."""
        n = _positive_int(amount, "amount", 100)
        for _ in range(n):
            advance_day_cb()
        return f"Advanced {n} day(s)." if n > 1 else "Advanced 1 day."

    def set_day(amount):
        """set_day(amount) -- jumps the day counter straight to `amount`;
        unlike advance_day(), this runs none of the real daily-tick side
        effects."""
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise ConsoleError("amount must be a non-negative whole number.")
        set_day_cb(amount)
        return f"Jumped straight to day {amount}."

    def toggle_forest(unlocked):
        """toggle_forest(unlocked) -- force the Forest unlocked/locked
        (True/False), without paying or waiting."""
        if not isinstance(unlocked, bool):
            raise ConsoleError("unlocked must be True or False.")
        toggle_forest_cb(unlocked)
        return "Forest unlocked." if unlocked else "Forest locked."

    def force_random_event(event):
        try:
            force_random_event_cb(str(event))
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Fired the {event!r} event."

    force_random_event.__doc__ = (
        "force_random_event(event) -- fires that day's random event "
        "immediately (one of: " + ", ".join(RANDOM_EVENT_NAMES) + "), without "
        "waiting on its own daily roll. Fails with an error if that event "
        "isn't currently applicable (e.g. a second storm while one's "
        "already rolling)."
    )

    def set_storm(active):
        """set_storm(active) -- True starts a storm right now (same as
        force_random_event("storm")); False ends whatever storm is
        currently rolling."""
        if not isinstance(active, bool):
            raise ConsoleError("active must be True or False.")
        if active:
            return force_random_event("storm")
        end_storm_cb()
        return "Storm ended."

    # ── Dreams / relationships / adventures ─────────────────────────────

    def give_nightmare(fish_name, variant=None, scare=True):
        """give_nightmare(fish_name, variant=None, scare=True) -- a forced
        bad dream; pass scare=False to let it linger so you can watch it
        instead of it waking the fish immediately."""
        target = _find_fish(str(fish_name))
        try:
            give_nightmare_cb(target, str(variant) if variant else None, bool(scare))
        except ValueError as error:
            raise ConsoleError(str(error))
        if scare:
            return f"Gave {target.display_name} a nightmare."
        return (
            f"Gave {target.display_name} a lingering nightmare "
            "(watch it while it sleeps)."
        )

    def give_dream(fish_name, category=None):
        """give_dream(fish_name, category=None) -- gives it a nice dream to
        view (category is happy/food/friendship/home/fantasy)."""
        target = _find_fish(str(fish_name))
        try:
            title = give_dream_cb(target, str(category) if category else None)
        except ValueError as error:
            raise ConsoleError(str(error))
        return f"Gave {target.display_name} a dream about {title}."

    def force_relationship(fish_a, fish_b, score):
        """force_relationship(fish_a, fish_b, score) -- sets their
        relationship score directly (-100 to 100) instead of waiting for
        real events to earn it."""
        a = _find_fish(str(fish_a))
        b = _find_fish(str(fish_b))
        clamped = _require_number(score, "score")
        force_relationship_cb(a, b, clamped)
        return (
            f"Set {a.display_name}/{b.display_name}'s relationship score "
            f"to {clamped:.0f}."
        )

    def start_lost_adventure(fish_name, duration=None):
        """start_lost_adventure(fish_name, duration=None) -- forces the rare
        "gets lost in the forest for days" event (duration in days, random
        4-8 if omitted), without waiting on its own 2%-per-day roll."""
        if duration is not None and (
            not isinstance(duration, int) or isinstance(duration, bool) or duration < 1
        ):
            raise ConsoleError("duration must be a positive whole number of days.")
        target = _find_fish(str(fish_name))
        if target.lost_adventure is not None:
            raise ConsoleError(f"{target.display_name} is already lost in the forest.")
        start_lost_adventure_cb(target, duration)
        return f"{target.display_name} is now lost in the forest."

    def advance_adventure_day(fish_name):
        """advance_adventure_day(fish_name) -- advances that fish's Lost
        Adventure by exactly one day (must already be on one)."""
        target = _find_fish(str(fish_name))
        if target.lost_adventure is None:
            raise ConsoleError(f"{target.display_name} isn't on a Lost Adventure.")
        advance_adventure_day_cb(target)
        return f"Advanced {target.display_name}'s Lost Adventure by one day."

    def trigger_birthday(fish_name):
        """trigger_birthday(fish_name) -- forces today to be that fish's
        birthday and runs the real birthday check immediately (friend wish/
        gift, Bubbles' visit), instead of waiting for the calendar to
        actually land on it."""
        target = _find_fish(str(fish_name))
        trigger_birthday_cb(target)
        return f"Triggered {target.display_name}'s birthday."

    def bubbles_visit(fish_name):
        """bubbles_visit(fish_name) -- sends Bubbles to visit that fish with
        a Toy Ball right now, the same visit a birthday would normally
        trigger -- independent of whether it's actually anyone's birthday."""
        target = _find_fish(str(fish_name))
        bubbles_visit_cb(target)
        return f"Bubbles is visiting {target.display_name}."

    # ── Sound ────────────────────────────────────────────────────────────

    def play_sound(name):
        if name not in sound.SFX_FILES:
            raise ConsoleError(
                f"Unknown sound: {name!r}. Try one of: {', '.join(sound.SFX_FILES)}."
            )
        sound.play_sfx(str(name))
        return f"Played {name!r}."

    play_sound.__doc__ = (
        "play_sound(name) -- plays that one-shot SFX right now, for "
        "auditioning. One of: " + ", ".join(sound.SFX_FILES) + "."
    )

    def set_ambience(name):
        if name not in sound.AMBIENCE_FILES:
            raise ConsoleError(
                f"Unknown ambience: {name!r}. "
                f"Try one of: {', '.join(sound.AMBIENCE_FILES)}."
            )
        sound.play_ambience(str(name))
        return f"Now playing {name!r} ambience."

    set_ambience.__doc__ = (
        "set_ambience(name) -- forces that ambience track to play right "
        "now, overriding whatever the game would normally choose (one of: "
        + ", ".join(sound.AMBIENCE_FILES) + ")."
    )

    def set_sound(enabled):
        """set_sound(enabled) -- turns sound on/off immediately, same as the
        Settings checkbox."""
        if not isinstance(enabled, bool):
            raise ConsoleError("enabled must be True or False.")
        state["sound_enabled"] = enabled
        if enabled:
            sync_ambience_cb()
        else:
            sound.stop_all()
        return "Sound on." if enabled else "Sound off."

    # ── Meta ─────────────────────────────────────────────────────────────

    def help():
        """help() -- list every available command."""
        return "\n".join(f"{name}: {_usage(fn)}" for name, fn in _COMMANDS.items())

    def _usage(fn) -> str:
        doc = fn.__doc__ or ""
        return " ".join(doc.split())

    # Explicit, ordered registry -- also what help() reads its text from
    # (each function's own docstring), so a command's usage text can never
    # drift out of sync with its real signature the way two hand-maintained
    # copies could.
    _COMMANDS = {
        "help": help,
        "spawn_fish": spawn_fish,
        "set_health": set_health,
        "set_hunger": set_hunger,
        "set_happiness": set_happiness,
        "set_speed": set_speed,
        "set_personality": set_personality,
        "grant_trait": grant_trait,
        "remove_fish": remove_fish,
        "set_age": set_age,
        "set_growth_stage": set_growth_stage,
        "feed_all": feed_all,
        "heal_all": heal_all,
        "happify_all": happify_all,
        "list_fish": list_fish,
        "describe": describe,
        "set_money": set_money,
        "set_food": set_food,
        "buy": buy,
        "give_treats": give_treats,
        "spawn": spawn,
        "spawn_decoration": spawn_decoration,
        "find_legendary": find_legendary,
        "unlock_achievement": unlock_achievement,
        "set_time": set_time,
        "advance_day": advance_day,
        "set_day": set_day,
        "toggle_forest": toggle_forest,
        "force_random_event": force_random_event,
        "set_storm": set_storm,
        "give_nightmare": give_nightmare,
        "give_dream": give_dream,
        "force_relationship": force_relationship,
        "start_lost_adventure": start_lost_adventure,
        "advance_adventure_day": advance_adventure_day,
        "trigger_birthday": trigger_birthday,
        "bubbles_visit": bubbles_visit,
        "play_sound": play_sound,
        "set_ambience": set_ambience,
        "set_sound": set_sound,
    }

    script_globals = dict(_COMMANDS)
    script_globals.update(
        {
            "fish": _ReadOnlyFish(fish),
            "state": _ReadOnlyState(state),
            "random": random,
            "math": math,
            "find_fish": _find_fish_or_none,
        }
    )
    return script_globals


class _ReadOnlyState:
    """A read-only view onto the live `state` dict, exposed to console
    scripts. Reads (state["money"], state.get(...), "money" in state,
    iteration) all see the same live values as every other command -- only
    *writes* are blocked. Without this, `state["money"] = -999` (or any
    type at all -- a string, None) would land directly in the real economy
    dict, bypassing every clamp/type-check the named commands (set_money,
    set_food, ...) apply, and later crash whatever code first does
    arithmetic on it. Change state through those commands instead -- they're
    callable from any typed script too."""

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
            "state is read-only here -- change it with the matching command "
            "(set_money, set_food, toggle_forest, ...) instead of assigning "
            "state[...] directly."
        )


class _ReadOnlyFish:
    """A read-only view onto the live `fish` list, exposed to console
    scripts. Reads (indexing, iteration, len, membership) all see the same
    live fish as every other command -- only *writes* are blocked. Without
    this, `fish[0] = "oops"` (or `.append`/`.clear`/...) would land directly
    in the real tank list, and the next frame's draw loop would crash
    trying to treat a non-Fish value as one. Change the tank through
    spawn_fish/remove_fish instead."""

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
            "fish is read-only here -- change the tank with spawn_fish/"
            "remove_fish instead of assigning fish[...] directly."
        )


# ── RestrictedPython execution ───────────────────────────────────────────

# safe_builtins is deliberately minimal (no list/dict/sum/min/max/...) --
# these are all pure, I/O-free, well-understood builtins with no
# introspection risk, added on top rather than missing entirely.
_EXTRA_BUILTINS = {
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
    "round": round,
    "abs": abs,
}

_INPLACE_OPS = {
    "+=": operator.add,
    "-=": operator.sub,
    "*=": operator.mul,
    "/=": operator.truediv,
}


def _inplacevar(op, x, y):
    if op not in _INPLACE_OPS:
        raise ConsoleError(f"Operator {op!r} isn't supported here.")
    return _INPLACE_OPS[op](x, y)


def _make_exec_globals(script_globals: dict) -> dict:
    builtins_dict = dict(safe_builtins)
    builtins_dict.update(_EXTRA_BUILTINS)
    exec_globals = dict(script_globals)
    exec_globals["__builtins__"] = builtins_dict
    exec_globals["_getattr_"] = safer_getattr
    exec_globals["_getitem_"] = lambda obj, index: obj[index]
    exec_globals["_getiter_"] = iter
    exec_globals["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence
    exec_globals["_write_"] = lambda obj: obj
    exec_globals["_inplacevar_"] = _inplacevar
    exec_globals["_print_"] = PrintCollector
    return exec_globals


def _format_exception(error: Exception) -> str:
    if isinstance(error, NameError):
        return f"{error} -- type help() to see what's available."
    return str(error)


def run_console_command(script_globals: dict, text: str) -> str:
    """Compile and run one typed line of console text through
    RestrictedPython -- the single entry point CheatConsole.on_run is wired
    to. Tried as a single expression first (eval -- covers the overwhelming
    majority of typed commands, a bare call like spawn_fish(...), and shows
    its return value directly); anything that isn't a single expression (an
    assignment, a loop, several statements) falls back to a real exec, with
    print() output captured and shown instead. This does not limit CPU time
    or memory (an intentional `while True: pass` will hang the game); that's
    an accepted, low-severity gap for a single-player local console -- no
    worse than a player hanging their own Python REPL."""
    text = text.strip()
    if not text:
        raise ConsoleError("Type a command, or help() to see what's available.")

    exec_globals = _make_exec_globals(script_globals)
    # eval-compiled code that calls print(...) references a bare `_print`
    # directly (LOAD_NAME _print; _print._call_print(...)) with no
    # preceding assignment -- unlike exec mode, RestrictedPython can't
    # insert a `_print = _print_()` preamble ahead of a single expression,
    # so eval needs one already sitting in globals or a bare print() inside
    # a one-line command raises NameError instead of just... printing.
    eval_printer = PrintCollector()
    exec_globals["_print"] = eval_printer

    eval_result = compile_restricted_eval(text)
    if not eval_result.errors:
        try:
            value = eval(eval_result.code, exec_globals, {})
        except ConsoleError:
            raise
        except Exception as error:
            raise ConsoleError(_format_exception(error))
        if value is not None:
            return str(value)
        printed = str(eval_printer()).rstrip("\n")
        return printed

    exec_result = compile_restricted_exec(text)
    if exec_result.errors:
        raise ConsoleError("; ".join(exec_result.errors))
    exec_locals = {}
    try:
        exec(exec_result.code, exec_globals, exec_locals)
    except ConsoleError:
        raise
    except Exception as error:
        raise ConsoleError(_format_exception(error))
    printer = exec_locals.get("_print")
    if printer is not None:
        output = str(printer()).rstrip("\n")
        if output:
            return output
    return "Ran."


_VISIBLE_LINES = 14
_WIDTH = 64
_WELCOME = (
    "=== Welcome to the TermQuarium Cheat Console ===",
    "Type help() to see the available commands.",
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
