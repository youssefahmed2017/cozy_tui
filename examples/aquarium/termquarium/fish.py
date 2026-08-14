"""The Fish widget: steering, hunger/growth, personality, relationships, and
sleep, all in its own draw() -- plus the small helpers built around it."""

import math
import random
import time

from cozy_tui import Style
from cozy_tui._width import text_width
from cozy_tui.widget import Widget

from .constants import (
    AVOID_MARGIN,
    AVOID_STEER_RATE,
    AXOLOTL_RELAX_CHANCE,
    AXOLOTL_RELAX_DURATION_MAX,
    AXOLOTL_RELAX_DURATION_MIN,
    AXOLOTL_RESTING_GLYPH,
    BUBBLE_CHASE_RADIUS,
    BUBBLE_CHASE_STEER_RATE,
    ENERGETIC_TURN_DIV,
    EXPLORER_HOME_SHUFFLE_CHANCE,
    FAST_SWIMMER_SPEED_MULT,
    FLEE_STEER_RATE,
    FOLLOW_MOUSE_RATE,
    FOOD_LOVER_FOOD_BOOST,
    FOOD_STEER_RATE,
    FRIEND_STEER_RATE,
    GREEDY_RATE_MULT,
    GREEDY_SPEED_MULT,
    GROWTH_STAGES,
    HOLD_BEFORE_EAT_SECONDS,
    HAPPINESS_CIRCLE_ANGULAR_SPEED,
    HAPPINESS_CIRCLE_RADIUS,
    HAPPINESS_CIRCLE_STEER_RATE,
    HAPPINESS_FED_GAIN,
    HAPPINESS_FOLLOW_STEER_MULT,
    HAPPINESS_FOOD_LOVER_BONUS,
    HAPPINESS_HAPPY_THRESHOLD,
    HUNGER_A_LITTLE_HUNGRY_THRESHOLD,
    HUNGER_CONTENT_THRESHOLD,
    HUNGER_LOW_ENERGY_THRESHOLD,
    HUNGER_WARNING_THRESHOLD,
    HAPPINESS_MAX,
    HAPPINESS_MIN,
    HAPPINESS_PERSONALITY_START_BONUS,
    HAPPINESS_RELAX_CHANCE_MULT,
    HAPPINESS_SAD_THRESHOLD,
    HAPPINESS_START_MAX,
    HAPPINESS_START_MIN,
    HAPPINESS_VERY_HAPPY_THRESHOLD,
    HEART_RADIUS,
    HIDE_DURATION_SECONDS,
    HOME_ARRIVE_MARGIN,
    HOME_STEER_RATE,
    IDLE_DAMPING,
    LAZY_HOME_RADIUS,
    LAZY_SPEED_MULT,
    BABY_LEFT,
    BABY_RIGHT,
    COLD_SPEED_MULT,
    COLD_TEMP_THRESHOLD,
    ELDER_SPEED_MULT,
    EXPLORER_TURN_DIV,
    LAZY_TURN_MULT,
    MAX_SPEED,
    MIN_SPEED,
    MIN_TURN_DELAY,
    MAX_TURN_DELAY,
    MISCHIEVOUS_FOOD_BOOST,
    OCTOPUS_COLOR_SHIFT_MAX,
    OCTOPUS_COLOR_SHIFT_MIN,
    OCTOPUS_COLORS,
    PIZZA_EAT_FLASH_SECONDS,
    PLANKTON_HUNGER_RELIEF,
    PLAYFUL_SPEED_VARIANCE,
    PLAYFUL_TURN_DIV,
    RELAX_ARRIVE_MARGIN,
    RELAX_CHANCE,
    RELAX_CHECK_MAX,
    RELAX_CHECK_MIN,
    RELAX_DURATION_MAX,
    RELAX_DURATION_MIN,
    RELAX_FLASH_SECONDS,
    RELAX_STEER_RATE,
    RELAX_WIGGLE_DURATION,
    RELAX_WIGGLE_INTERVAL,
    RACE_SPEED_MULT,
    RIVAL_FLEE_RADIUS,
    RIVAL_FOOD_BOOST,
    SCHOOL_ALIGNMENT_WEIGHT,
    SCHOOL_COHESION_WEIGHT,
    SCHOOL_RADIUS,
    SCHOOL_SEPARATION_DISTANCE,
    SCHOOL_SEPARATION_WEIGHT,
    SCHOOL_STEER_RATE,
    SEAHORSE_SPEED_MULT,
    SHY_FLEE_RADIUS,
    SLEEP_CLOSE_DISTANCE,
    SLEEP_FAR_DISTANCE,
    SLEEP_HUNGER_THRESHOLD,
    SLEEP_STEER_RATE,
    WARM_ARRIVE_MARGIN,
    WARM_CHANCE_MAX,
    WARM_CHECK_MAX,
    WARM_CHECK_MIN,
    WARM_DURATION_MAX,
    WARM_DURATION_MIN,
    WARM_STEER_RATE,
    TRAIT_ENERGETIC,
    TRAIT_FAST_SWIMMER,
    TRAIT_FOOD_LOVER,
    TRAIT_MISCHIEVOUS,
    SOCIAL_STEER_RATE,
    AGE_SECONDS_PER_DAY,
    WAKE_LINGER_SECONDS,
    Species,
    HAPPINESS_SPARKLE_CHECK_MAX,
    HAPPINESS_SPARKLE_CHECK_MIN,
    HAPPINESS_EXCITED_WIGGLE_CHECK_MAX,
    HAPPINESS_EXCITED_WIGGLE_CHECK_MIN,
    HAPPINESS_FOLLOW_CHECK_MAX,
    HAPPINESS_FOLLOW_CHECK_MIN,
    HAPPINESS_CIRCLE_CHECK_MAX,
    HAPPINESS_CIRCLE_CHECK_MIN,
)
from .economy import adjust_happiness, feed
from .relationships import (
    best_bond,
    random_personality,
    relationship_state,
    roll_is_sleepy,
    worst_bond,
)
from .steering import (
    avoid_decorations,
    nearest_index,
    random_velocity,
    school_velocity,
    steer,
    steer_away_from,
    steer_toward_food,
)
from .styles import HEART_STYLE, MUTED, WOOD_STYLE
from .tank_objects import Wood
from .world import temperature_chill


class Fish(Widget):
    def __init__(
        self,
        x: float,
        y: float,
        bounds,
        foods,
        fish_list,
        on_eat_food,
        on_eat_fish,
        right_glyph,
        left_glyph,
        color,
        is_predator: bool = False,
        decorations=None,
        species_name: str = "Fish",
        mouse_pos=None,
        price: int = 0,
        environment=None,
        paused=None,
        favorite_foods=(),
        rarity: str = "Common",
        bubbles=None,
    ):
        super().__init__(round(x), round(y), Style(fg=color))
        # Set before anything below that can read .age_days/.growth_stage --
        # _effective_speed() (called a few lines down, to seed initial
        # velocity) now checks growth_stage for ELDER_SPEED_MULT, so
        # birth_time has to exist first.
        self.birth_time = time.monotonic()
        self.fx, self.fy = float(x), float(y)
        self.bounds = bounds
        self.foods = foods
        self.fish_list = fish_list
        self.on_eat_food = on_eat_food
        self.on_eat_fish = on_eat_fish
        self.right_glyph = right_glyph
        self.left_glyph = left_glyph
        self.is_predator = is_predator
        self.decorations = decorations if decorations is not None else []
        # Shared {"phase": "Morning"/"Afternoon"/"Evening"/"Night", "temperature": float}
        # dict, updated once a second by main()'s _per_second_tick -- the
        # same shared-mutable-dict pattern mouse_pos already uses.
        self.environment = environment
        # Shared {"value": bool} dict, or None -- main()'s Pause menu. Checked
        # first thing in draw(): everything (movement, hunger-independent
        # timers, sleep/home logic) freezes solid while paused, see draw().
        self.paused = paused
        self.species_name = species_name
        self.display_name = species_name  # renameable -- see _rename_fish() in main()
        self.price = price  # this species' Shop price -- sell_value scales off it by growth stage
        # Treat kinds (TREAT_SHOP_ITEMS) this species is delighted by -- see
        # aquarium.py's _feed_treat. Flavor only: same economy.feed() relief
        # either way, just a nicer toast, never a bigger number.
        self.favorite_foods = favorite_foods
        # More Fish (updates.md): collection tier, flavor-only display (Shop
        # row, Inspector) -- see constants.RARITY_TIERS.
        self.rarity = rarity
        self.mouse_pos = mouse_pos  # shared {"x":.., "y":..} dict, or None
        # The tank's single shared BubbleField (bubbles.py), or None -- read
        # (never mutated) by a wandering Baby's bubble-chase steering in
        # draw(), the same "hold a live shared reference" pattern mouse_pos
        # already uses.
        self.bubbles = bubbles
        # One-shot per catch (not per-baby-ever -- see constants.py's
        # BUBBLE_CHASE_RADIUS comment): set True in draw() the instant a
        # chased bubble is reached, consumed by aquarium.py's
        # _process_bubble_chases() the same way _relax_began already is.
        self._bubble_chase_caught = False
        # Rolled fresh once a day for every Baby (aquarium.py's
        # _check_milestone_achievements(), BUBBLE_CHASE_CHANCE_PER_DAY) --
        # False by default so a fresh fish never chases before its first
        # roll. Gates the whole branch below: on a day this loses, bubbles
        # are ignored entirely, however many drift by.
        self._bubble_chase_eligible_today = False
        # Baby racing (aquarium.py's _check_baby_races()): while now is
        # before this, _effective_speed() applies RACE_SPEED_MULT and
        # draw() shows a 💨 above the fish -- a cosmetic burst, not a new
        # destination. Set on both fish at once from aquarium.py, which
        # already has both objects in hand; fish.py never mutates a rival's
        # state directly (same reasoning join-relax's `self.friend.relaxing`
        # read-only check already follows).
        self._racing_until = 0.0
        self.personality = random_personality()
        # Independent of (and stackable with) personality -- see
        # roll_is_sleepy()'s docstring. A Greedy fish can also be Sleepy.
        self.is_sleepy = roll_is_sleepy()
        # Personality System 2.0 (ROADMAP.md): traits earned through play,
        # not rolled at birth -- a brand-new fish starts with none, same
        # philosophy relationships.py already uses for Friend/Rival bonds.
        # See relationships.grant_trait(), called from aquarium.py at
        # whatever real event a given trait grows from.
        self.traits: frozenset[str] = frozenset()
        # Set the moment this fish eats food that some other (non-predator)
        # fish was actually closer to -- a real "beat someone to it", not
        # just a flat stat. aquarium.py's per-second tick reads this, rolls
        # Mischievous's growth chance, logs/toasts, nudges the two fish's
        # relationship, and clears it back to None; a plain widget can't do
        # any of that itself (no _log_memory/app/relationships access here).
        self._stole_food_from = None
        # Chosen once at birth, like a real pet's favorite spot -- never
        # re-rolled later, unlike everything else personality-related.
        self.favorite_decoration = (
            random.choice(self.decorations) if self.decorations else None
        )
        # Every pairwise relationship this fish currently has, keyed by the
        # other Fish -- starts empty (a new fish, starter/bought/born alike,
        # has no relationships yet; they're earned through interactions,
        # see relationships.py). `friend`/`rival` below are read-only views
        # derived from whichever relationship is currently strongest/
        # weakest, not fixed pointers set once at birth.
        self.relationships: dict["Fish", object] = {}
        # Which container Decoration (capacity > 0) this fish has claimed
        # for tonight, if any -- re-rolled fresh every time it falls asleep
        # (see _claim_home()), not a permanent "home" like favorite_decoration
        # is a permanent favorite. `_entered` is True once it's actually
        # arrived inside (not just still swimming toward it) -- see draw().
        self.sleeping_in = None
        self._entered = False
        # A Sleepy fish can stay genuinely asleep past the normal
        # Night->Morning transition, pending a real wake attempt from an
        # eligible tankmate (see aquarium.py's _per_second_tick and
        # relationships.find_eligible_waker()/resolve_wake_attempt()).
        # Everyone else is entirely unaffected -- these only ever get set
        # for a Sleepy fish that would otherwise have woken.
        self._holding_asleep = False
        self._wake_attempts_used = 0
        self._wake_threshold = None
        self._held_since = None
        self._wake_waker = None  # the tankmate assigned to attempt waking it
        self._wake_next_attempt = None  # monotonic() time of the next try
        # Any fish (Sleepy or not) lingers in its container a moment after
        # waking -- still tucked in/invisible in the open tank (_entered
        # stays True), but shown awake rather than asleep wherever
        # occupants_of() is read (the Castle Interior view) until
        # WAKE_LINGER_SECONDS actually passes and it leaves for real.
        self._awake_in_home = False
        self._wake_time = None
        # Set by aquarium.py's _process_sleepy_holds() on every wake
        # attempt this fish makes (resisted or not) -- a monotonic()
        # deadline the Castle Interior view shows "*boop*" until, in place
        # of this fish's normal mood emoji.
        self._just_booped_until = None
        # The other half of that same moment, on the fish *being* booped --
        # set alongside _just_booped_until, same deadline, so a resisted
        # attempt visibly reads as "tried... and *...zzz*, still asleep"
        # rather than only ever showing the waker's side of it.
        self._just_resisted_wake_until = None
        self.speed = random.uniform(MIN_SPEED, MAX_SPEED)
        self.vx, self.vy = random_velocity(self._effective_speed())
        self.hunger = 100.0  # 0 = starving, 100 = full
        self.health = 100.0
        # Update 1: a "personality amplifier," not a resource to babysit --
        # see constants.py's Happiness block for the full philosophy. The
        # starting roll leans a little per personality (flavor only; nothing
        # downstream reads personality back off of it), then clamps like
        # every other bounded stat here.
        self.happiness = max(
            HAPPINESS_MIN,
            min(
                HAPPINESS_MAX,
                random.uniform(HAPPINESS_START_MIN, HAPPINESS_START_MAX)
                + HAPPINESS_PERSONALITY_START_BONUS.get(self.personality, 0.0),
            ),
        )
        # Cosmetic-only flourishes gated on the happiness band (see
        # _process_happiness() in aquarium.py and _glyph() below) -- a brief
        # ✨ for a Very Happy fish, and the same tail-flick wiggle relaxing
        # already has, reused here for a Happy-or-better fish just swimming
        # around ("occasionally wiggles excitedly"). Each rolls on its own
        # periodic *check* (like the relax mechanic's own _next_relax_check),
        # not a bare per-second chance -- see constants.py's Happiness block
        # for why. Seeded to a random moment soon after construction, the
        # same "don't all roll in lockstep" reasoning RELAX_CHECK_MIN/MAX use.
        _now = time.monotonic()
        self._sparkle_until = 0.0
        self._sparkle_next_check = _now + random.uniform(
            HAPPINESS_SPARKLE_CHECK_MIN, HAPPINESS_SPARKLE_CHECK_MAX
        )
        self._excited_wiggle_until = 0.0
        self._wiggle_next_check = _now + random.uniform(
            HAPPINESS_EXCITED_WIGGLE_CHECK_MIN, HAPPINESS_EXCITED_WIGGLE_CHECK_MAX
        )
        # "Swims in circles" (❤️, Very Happy) -- a real steering flourish, not
        # just a glyph. `_circle_pivot`/`_circle_start` are only meaningful
        # while `_circling_until` is in the future; `_circle_began` is the
        # one-shot aquarium.py's _process_happiness() consumes for the toast.
        self._circling_until = 0.0
        self._circle_pivot = None
        self._circle_start = 0.0
        self._circle_began = False
        self._circle_next_check = _now + random.uniform(
            HAPPINESS_CIRCLE_CHECK_MIN, HAPPINESS_CIRCLE_CHECK_MAX
        )
        # "Follows friend around" (🐟, Very Happy) -- a temporary boost to the
        # existing plain friend-follow blend rate, not a new behavior.
        # `_follow_began` is the toast one-shot, same shape as `_circle_began`.
        self._following_until = 0.0
        self._follow_began = False
        self._follow_next_check = _now + random.uniform(
            HAPPINESS_FOLLOW_CHECK_MIN, HAPPINESS_FOLLOW_CHECK_MAX
        )
        # Rolled fresh each night by aquarium.py's _assign_dreams(), cleared
        # the moment this fish wakes (see the wake-reset block below) --
        # None means "not dreaming tonight", not "hasn't been asked yet".
        self.dream = None
        # This fish's own diary -- distinct from Relationship.memories
        # (relationships.py), which is a shared pair record. Populated by
        # aquarium.py's _log_memory() at real, already-tracked event sites;
        # newest last, oldest dropped once it exceeds MEMORY_LOG_LIMIT. This
        # is what the fish itself "remembers" -- dream selection and grief
        # fading (a departed friend stops surfacing in dreams once their
        # departure line ages out) both read this capped list, on purpose.
        self.memory_log: list[str] = []
        # The same diary, never capped -- a player-facing "See All History"
        # archive (inspectors.py's _build_fish_history) so a real moment isn't
        # lost forever just because the fish itself has moved on. Deliberately
        # a separate list rather than a bigger cap on memory_log: gameplay
        # (what the fish "remembers") and the player's own record of what
        # actually happened are different things, and the whole point here is
        # letting them diverge -- the fish forgets, the player doesn't have to.
        self.full_memory_log: list[str] = []
        # A curated subset of memory_log's own entries -- the handful truly
        # too important to risk aging out of the capped list above (birth,
        # a first Friend bond, a child, making it home from a Lost
        # Adventure). Appended alongside memory_log/full_memory_log by
        # aquarium.py's _log_memory(..., lifelong=True), never trimmed.
        # Deliberately excludes departure lines -- see dreams.py's
        # _departed_friend_name(): grief fading once memory_log's cap pushes
        # that line out is itself the intended behavior, not a gap to patch.
        self.pinned_memories: list[str] = []
        # Which REFLECTION_MEMORY_DAYS thresholds this fish has already
        # reflected on (see aquarium.py's _check_reflection_memories()) --
        # a frozenset, same immutable-set convention as `traits`, so each
        # milestone line fires exactly once per fish even across save/load.
        self.reflections_logged: frozenset[int] = frozenset()
        # Set once at birth (aquarium.py's _try_breeding) to the two parents'
        # display_names at that moment, and never touched again -- a "blood
        # bond" that must outlive either parent (sold, starved, eaten) or a
        # save/load round-trip, so it's a plain name snapshot rather than a
        # live Fish reference, the same reason dreams.py re-derives a departed
        # friend's name from memory_log text instead of holding a pointer to
        # it. None for any fish not born in-tank (shop-bought, or a save from
        # before this existed). aquarium.py's _find_living_parent() resolves
        # this back to a live Fish, when one still exists.
        self.parent_names: tuple[str, str] | None = None
        # True while this (non-predator) fish is currently within
        # SHARK_SCARE_RADIUS of a Shark -- guards aquarium.py's
        # _check_shark_scares() against re-firing every tick for as long as
        # the scare lingers, only on the rising edge of a fresh approach.
        self._shark_scare_active = False
        # Set by aquarium.py's _check_shark_scares() when a nearby container
        # (capacity to spare) is available at the moment of a fresh scare --
        # the *target* to flee to, and (once close enough) the container
        # actually hidden inside, mirroring sleeping_in's own overloaded
        # "heading toward or already inside" meaning. `_entered` (already
        # used for the sleeping case) does double duty as the "invisible and
        # safe from predation" flag for hiding too, since the two states
        # never overlap (an asleep fish already sleeps through a shark scare
        # -- see _check_shark_scares()). `_hide_until` is set once it
        # actually arrives (not when it starts fleeing), and read at the top
        # of draw() to release it after HIDE_DURATION_SECONDS.
        self._hiding_in = None
        self._hide_until = None
        # The container this fish is currently storm-sheltering in, once
        # arrived, or None -- same overloaded use of `_entered` as sleeping/
        # shark-hiding above (tucked in, invisible). Unlike `_hide_until`,
        # there's no per-fish timer: environment["storm"] is one shared
        # flag every fish reads (aquarium.py's _end_storm()), so release
        # happens the moment draw() next sees the storm has ended, at the
        # top of draw() alongside the `_hide_until` release below.
        self._storm_sheltering = None
        # Nightmare reaction (see aquarium.py's _process_nightmares()), a
        # two-phase timer: _nightmare_wake_at is when Phase 1 (the scare --
        # 😨, still in the same bed) fires; _nightmare_relocate_at is when
        # Phase 2 (the actual early wake + relocating to sleep beside a
        # Friend, if any) fires next, NIGHTMARE_SCARE_FLASH_SECONDS later.
        # _just_scared_until/_nightmare_comfort_until are the same "flash a
        # mood for N seconds" trick _just_booped_until already uses, for
        # the scared moment and the arrived-beside-a-friend moment;
        # _seeking_friend_after_nightmare is True only while actively
        # relocating toward a Friend after Phase 2, so _process_nightmares()
        # knows when it's arrived.
        self._nightmare_wake_at = None
        self._nightmare_relocate_at = None
        # Set by aquarium.py's _trigger_nightmare_relocation() while actively
        # relocating after a nightmare -- a living parent if one exists
        # (blood bond, no Friend-threshold needed), else the ordinary best-
        # bond Friend. A live Fish pointer, not a permanent one: cleared the
        # moment seeking ends, same lifetime as _seeking_friend_after_nightmare
        # below, and never saved/restored. None means "use self.friend as
        # normal," so every night this stays untouched, floor-settle behaves
        # exactly as it always has.
        self._nightmare_seek_target = None
        self._just_scared_until = None
        self._nightmare_comfort_until = None
        self._seeking_friend_after_nightmare = False
        # Exploration Update, Slice 1 (see aquarium.py's _check_foraging()):
        # which biome this fish is actually in right now -- "aquarium" or
        # "forest". `_travel_until`/`_travel_target` are a real transit
        # timer (mirrors the nightmare reaction's own two-phase timers):
        # while `_travel_until` is set, this fish is mid-trip and invisible
        # in *both* scenes (same "gone from view" precedent as an
        # already-housed fish), and once time catches up to it, `biome`
        # becomes `_travel_target` and both clear. `carrying` holds "Wood"
        # once foraged, cleared on delivery back home -- a plain string,
        # not a class, since only one material exists yet.
        self.biome = "aquarium"
        self._travel_until = None
        self._travel_target = None
        self.carrying = None
        # Lost Adventure (ROADMAP.md): None, or a dict while a fish is off
        # on a rare multi-day trip -- {"day", "duration", "shelter",
        # "has_wood", "told_to_find_wood"}. Unlike the routine forage
        # state above, this one *is* persisted across save/load (see
        # aquarium.py's _snapshot()/_load_snapshot()) -- a deliberate
        # exception, since a multi-day adventure silently vanishing on
        # reload would be a real loss, not the same kind of routine trip
        # the "don't persist Forest travel state" precedent was written for.
        self.lost_adventure = None
        # Set only for the few seconds a lost fish is briefly made visible
        # again, standing at a shelter it just found/fled to (see
        # aquarium.py's _start_shelter_visit()/_check_lost_adventure_
        # shelter_visits()) -- an appear-and-vanish moment, not persisted
        # and not part of Fish.lost_adventure's own saved state.
        self._shelter_visit_until = None
        # Set on Forest arrival, cleared on departure -- gates how soon a
        # fish is allowed to roll for a successful forage (see
        # FOREST_MIN_DWELL_SECONDS) so it's reliably visible in the scene
        # for a beat rather than potentially foraging on the very next
        # per-second check after showing up.
        self._forest_arrived_at = None
        if self.is_predator:
            # A predator is never bred and never a starter (both exclude
            # predators -- see STARTER_SPECIES/find_breeding_pairs()), so
            # every Shark that will ever exist comes from a Shop purchase.
            # Buying one for $500 to watch it show up as a generic "o>"
            # baby blob undercuts the whole point -- it starts already
            # Adult: full glyph, full hunting speed, hunting immediately.
            # Looked up by name, not GROWTH_STAGES[-1] -- Elder is the real
            # last stage now, and a brand-new Shark must never start there.
            adult_age_days = next(
                min_age
                for name, min_age, _mult in GROWTH_STAGES
                if name.startswith("Adult")
            )
            self.birth_time -= AGE_SECONDS_PER_DAY * (adult_age_days + 0.5)
        self._last = time.monotonic()
        self._next_turn = self._last + random.uniform(MIN_TURN_DELAY, MAX_TURN_DELAY)
        self._relaxing_until = 0.0
        self._next_relax_check = self._last + random.uniform(
            RELAX_CHECK_MIN, RELAX_CHECK_MAX
        )
        # More Fish (updates.md): Octopus's "sometimes changes color" -- only
        # meaningfully read when species_name == "Octopus" (see draw()), but
        # seeded for every fish the same unconditional way birth_time/
        # _next_turn are.
        self._next_color_shift = self._last + random.uniform(
            OCTOPUS_COLOR_SHIFT_MIN, OCTOPUS_COLOR_SHIFT_MAX
        )
        # More Fish (updates.md): Worms/Bloodworms are held at the mouth for
        # HOLD_BEFORE_EAT_SECONDS instead of eaten instantly -- see the
        # caught branch below (sets these two) and draw()'s per-frame check
        # (finishes the meal once _holding_until elapses) and _glyph() (shows
        # the held food's emoji meanwhile). None whenever nothing's held.
        self._holding_food = None
        self._holding_until = 0.0
        # More Fish (updates.md): a brief ☺️ right after finishing a Pizza --
        # the second half of the two-frame reaction (_consume_food() sets
        # this; the first half, 😋 while approaching, is live state read
        # straight off the food-seeking branch, not a timer -- see draw()).
        self._pizza_eat_flash_until = 0.0
        # Surfacing state (see the relax branch in draw()): `relaxing` is True
        # only once actually settled -- at its own favorite spot, or (see the
        # join branch) beside a friend who's already relaxing at theirs.
        # `_relax_spot` is *which* Decoration that is (may differ from
        # favorite_decoration when joined), read by the Inspector and
        # aquarium.py's _process_relaxing(); `_relaxing_with` is the friend,
        # if this is a joined episode rather than a solo one. `_relax_flash_until`
        # drives the brief 😌 above the fish; `_relax_began`/`_joined_friend_relax`
        # are one-shots the per-second tick consumes to (rarely) toast / log a
        # memory for a solo settle, or always toast for a join.
        self.relaxing = False
        self._relax_spot = None
        self._relaxing_with = None
        self._relax_flash_until = 0.0
        self._relax_began = False
        self._joined_friend_relax = False
        # Evening warming-up (see draw()'s branch right after relaxing, and
        # world.temperature_chill()): a fish that wins its chance heads for
        # a Warm Lamp if one exists (preferred -- see _nearest_heat_source()),
        # otherwise the nearest container *with room*. A container is
        # actually entered -- `_entered`/`_warming_in`, the same "tucked in,
        # invisible, frozen" mechanism sleeping_in/_hiding_in already use
        # (see the `_entered` early-return in draw()) -- but a Lamp isn't a
        # container, so a fish just lingers visibly nearby instead
        # (`_warming_at_lamp`), any number at once. `_warm_target` is which
        # one it's heading toward *before* arriving; `_warming_in`/
        # `_warming_at_lamp` is which it actually reached (mirrors
        # sleeping_in/_hiding_in's own split, extended one more way).
        # `_warming_until` is set fresh the moment it actually arrives
        # (mirrors `_hide_until`), not at the moment the urge starts --
        # travel time doesn't eat into it. `_warm_approaching` drives the
        # continuous 🥶 while still on the way (see draw()'s indicator
        # chain); the entered-a-container fish's own ☺️ is drawn from the
        # `_entered` mood-icon chain instead, the same way a housed fish's
        # other momentary moods already are, while a Lamp-basking fish's ☺️
        # is drawn from the ordinary (visible) indicator chain.
        self._warm_approaching = False
        self._warm_target = None
        self._warming_in = None
        self._warming_at_lamp = None
        self._warming_until = 0.0
        self._next_warm_check = self._last + random.uniform(
            WARM_CHECK_MIN, WARM_CHECK_MAX
        )

    @property
    def age_days(self) -> float:
        return (time.monotonic() - self.birth_time) / AGE_SECONDS_PER_DAY

    @property
    def is_asleep(self) -> bool:
        """Fully asleep -- not just slower. A sleeping fish doesn't wander,
        chase food, flee, relax, or get any Happiness flourish (see draw()'s
        `sleeping` and aquarium.py's _process_happiness(), which both read
        this same property rather than each computing their own copy of it).
        A fish hungry enough to actually be in danger stays up instead --
        sleeping through your own starvation isn't cozy, it's just a bug
        wearing a nightcap. A Shark never qualifies at all, regardless of
        hunger or time of day -- the whole point of buying one is an
        ever-present threat, and a sleeping predator could otherwise claim a
        container alongside its own prey, bond with it (record_slept_together
        doesn't distinguish predators), and even get a nightmare of its own
        (see aquarium.py's _assign_dreams(), which excludes predators for the
        same reason)."""
        return (
            not self.is_predator  # a Shark stays active -- and hunting -- all night
            and self.environment is not None
            and (self.environment.get("phase") == "Night" or self._holding_asleep)
            and self.hunger >= SLEEP_HUNGER_THRESHOLD
        )

    @property
    def feeling(self) -> str:
        """ "Sad" / "Neutral" / "Happy" / "Very Happy" -- the band `self.happiness`
        falls into, read by the Inspector and every ambient Happiness nudge
        (the relax-chance multiplier, choose_dream()'s lean, the sparkle/
        excited-wiggle flourishes). Every effect reads this band, never the
        raw number, which is what keeps a 3-point happiness wobble invisible
        to gameplay -- only crossing a threshold actually changes anything."""
        if self.happiness < HAPPINESS_SAD_THRESHOLD:
            return "Sad"
        if self.happiness >= HAPPINESS_VERY_HAPPY_THRESHOLD:
            return "Very Happy"
        if self.happiness >= HAPPINESS_HAPPY_THRESHOLD:
            return "Happy"
        return "Neutral"

    @property
    def hunger_feeling(self) -> str:
        """ "Full" / "Content" / "A little hungry" / "Hungry" / "Low energy"
        -- the band `self.hunger` falls into (Hunger update, updates.md).
        "Low energy" is hunger's own floor, not a step toward anything
        worse: staying hungry a while is a mood to notice and fix by
        feeding, never a countdown. Mirrors Fish.feeling's own
        banded-property shape exactly. Scale is 0=starving/100=full, so
        this ladder reads top-down from the fullest band."""
        if self.hunger >= HUNGER_CONTENT_THRESHOLD:
            return "Full"
        if self.hunger >= HUNGER_A_LITTLE_HUNGRY_THRESHOLD:
            return "Content"
        if self.hunger >= HUNGER_WARNING_THRESHOLD:
            return "A little hungry"
        if self.hunger >= HUNGER_LOW_ENERGY_THRESHOLD:
            return "Hungry"
        return "Low energy"

    @property
    def friend(self):
        """The other fish this one gets along with best, if that's at
        least Friend-level (relationships.RELATIONSHIP_FRIEND_THRESHOLD),
        else None. Read-only and live -- derived from the current
        relationship scores (see relationships.best_bond()), not a fixed
        pointer set once at birth."""
        return best_bond(self)

    @property
    def rival(self):
        """The other fish this one gets along with least, if that's
        Rival-level (relationships.RELATIONSHIP_RIVAL_THRESHOLD), else
        None -- the same read-only, score-derived shape as `friend`."""
        return worst_bond(self)

    def _growth_stage_index(self) -> int:
        idx = 0
        for i, (_name, min_age, _mult) in enumerate(GROWTH_STAGES):
            if self.age_days >= min_age:
                idx = i
        return idx

    @property
    def growth_stage(self) -> str:
        return GROWTH_STAGES[self._growth_stage_index()][0]

    @property
    def sell_value(self) -> int:
        return round(self.price * GROWTH_STAGES[self._growth_stage_index()][2])

    def _effective_speed(self) -> float:
        # Checked fresh every use (like every other personality effect),
        # rather than baked permanently into self.speed at construction --
        # otherwise a Lazy fish would move like a normal one everywhere
        # this file (or a test) sets .personality after construction, since
        # nothing else here treats personality as fixed-at-birth.
        # Night no longer lives here -- a sleeping fish is a hard stop
        # (see draw()), not just slower, so there's nothing left to blend.
        mult = LAZY_SPEED_MULT if self.personality == "Lazy" else 1.0
        if self.species_name == "Seahorse":
            mult *= SEAHORSE_SPEED_MULT  # More Fish (updates.md): "slow"
        if TRAIT_FAST_SWIMMER in self.traits:
            mult *= FAST_SWIMMER_SPEED_MULT  # earned trait, stacks with everything else here
        if self.growth_stage.startswith("Elder"):
            mult *= ELDER_SPEED_MULT  # measurably slower with age
        if self.environment is not None:
            temperature = self.environment.get("temperature")
            if temperature is not None and temperature < COLD_TEMP_THRESHOLD:
                mult *= COLD_SPEED_MULT  # cold-blooded and sluggish
        if self._racing_until and time.monotonic() < self._racing_until:
            mult *= RACE_SPEED_MULT  # a Baby race's cosmetic burst of speed
        return self.speed * mult

    def _nearest_food(self):
        i = nearest_index(self.fx, self.fy, [(f.fx, f.fy) for f in self.foods])
        return self.foods[i] if i is not None else None

    def _consume_food(self, target) -> None:
        """feed()/Happiness/the on_eaten flavor hook for a food item this
        fish just ate -- shared by the immediate-eat path (draw()'s caught
        branch) and the deferred Worms/Bloodworms hold (draw()'s per-frame
        check), so both apply the exact same effects once eating actually
        happens, just at different moments."""
        if getattr(target, "kind", None) == "Plankton":
            # "Barely a mouthful" -- Plankton relieves hunger by only a tiny
            # amount, dropped or fed, unlike every other food's near-full-up
            # bite (see aquarium.py's _feed_treat for the Inspector-feeding
            # equivalent).
            self.hunger, self.health = feed(
                self.hunger, self.health, relief=PLANKTON_HUNGER_RELIEF
            )
        else:
            self.hunger, self.health = feed(self.hunger, self.health)
        self.happiness = adjust_happiness(self.happiness, HAPPINESS_FED_GAIN)
        if not self.is_predator and TRAIT_FOOD_LOVER in self.traits:
            # On top of HAPPINESS_FED_GAIN above -- any food, not just a
            # favorite treat (see aquarium.py's _treat_reaction for the
            # separate favorite-food bonus, which stacks with this one too).
            self.happiness = adjust_happiness(self.happiness, HAPPINESS_FOOD_LOVER_BONUS)
        # A special food (a dropped treat) reacts to whoever actually ate it
        # -- fired here, after feed(), so the reaction sees the fed hunger/
        # health. Plain food and eaten prey have no such hook.
        on_eaten = getattr(target, "on_eaten", None)
        if on_eaten is not None:
            on_eaten(self)
        if getattr(target, "kind", None) == "Pizza":
            # More Fish (updates.md): the ☺️ half of the two-frame reaction --
            # see the 😋 half in draw()'s flourish chain.
            self._pizza_eat_flash_until = time.monotonic() + PIZZA_EAT_FLASH_SECONDS

    def _closer_rival_for(self, food_pos):
        """The nearest *other* non-predator fish that was closer to
        `food_pos` than this fish is right now, or None -- Mischievous's
        growth trigger (see aquarium.py's per-second processing of
        `_stole_food_from`): eating food some tankmate was arguably about to
        get first is a real "stole it" moment, not a flat stat check."""
        my_dist = math.hypot(self.fx - food_pos[0], self.fy - food_pos[1])
        closest, closest_dist = None, None
        for other in self.fish_list:
            if other is self or other.is_predator:
                continue
            d = math.hypot(other.fx - food_pos[0], other.fy - food_pos[1])
            if d < my_dist and (closest_dist is None or d < closest_dist):
                closest, closest_dist = other, d
        return closest

    def _nearest_prey(self):
        # Sharks hunt ordinary fish, never each other -- and never one
        # that's already invisible/safe, tucked inside a container (asleep
        # for the night via sleeping_in, or hiding from this very Shark via
        # _hiding_in). Both cases set _entered, so this one check covers
        # either reason a fish can't physically be reached right now.
        prey = [
            f
            for f in self.fish_list
            if f is not self and not f.is_predator and not f._entered
        ]
        i = nearest_index(self.fx, self.fy, [(f.fx, f.fy) for f in prey])
        return prey[i] if i is not None else None

    def _nearest_container(self):
        # Storm-shelter seeking (see draw()'s `environment["storm"]` branch)
        # -- deliberately simpler than _claim_home()'s favorite/friend/
        # nearest priority chain: a live weather reaction just wants
        # *somewhere* to huddle near right now, not tonight's considered
        # pick, and never claims/occupies the spot (no sleeping_in, no
        # invisibility) so it can't collide with that night-time bookkeeping.
        containers = [d for d in self.decorations if d.is_container]
        i = nearest_index(self.fx, self.fy, [(d.fx, d.fy) for d in containers])
        return containers[i] if i is not None else None

    def _nearest_container_with_room(self):
        # Shark-hiding (see aquarium.py's _check_shark_scares() and draw()'s
        # _hiding_in branch) -- unlike _nearest_container()'s storm-huddle,
        # this one actually claims the spot, so capacity has to be checked
        # up front (_home_occupancy() counts sleepers and hiders together
        # against the same pool).
        containers = [
            d
            for d in self.decorations
            if d.is_container and self._home_occupancy(d) < d.capacity
        ]
        i = nearest_index(self.fx, self.fy, [(d.fx, d.fy) for d in containers])
        return containers[i] if i is not None else None

    def _nearest_heat_source(self):
        # Warm Lamp (Evening warming-up) -- unlike a Rock/Castle, never
        # claims/checks capacity: it isn't a container (Decoration.
        # heat_source, not capacity), so any number of fish can bask at the
        # same one at once. Preferred over a container whenever one exists
        # (see the warming periodic-check in draw()).
        lamps = [d for d in self.decorations if d.heat_source]
        i = nearest_index(self.fx, self.fy, [(d.fx, d.fy) for d in lamps])
        return lamps[i] if i is not None else None

    def _group_centroid(self):
        """Average (x, y) of every other fish sharing this tank, or None if
        there are none -- Friendly's fallback when there's no mouse to
        follow. None (not e.g. (0, 0)) matters: it's what lets a solitary
        Friendly fish correctly fall through to relaxing/wandering instead
        of silently doing nothing while still "claiming" this frame's
        personality-steering priority slot."""
        others = [(o.fx, o.fy) for o in self.fish_list if o is not self]
        if not others:
            return None
        return sum(p[0] for p in others) / len(others), sum(p[1] for p in others) / len(
            others
        )

    def _schoolmates(self):
        """(x, y, vx, vy) for same-species, non-predator fish within
        SCHOOL_RADIUS -- schooling is a species trait (real fish shoal with
        their own kind), not a personality one like Friendly's group pull,
        and predators (Sharks) hunt alone rather than schooling. Axolotls
        don't school either, even with each other -- solitary/independent
        is part of what makes them feel different from the fish species,
        not a stat difference."""
        if self.is_predator or self.species_name == "Axolotl":
            return []
        return [
            (o.fx, o.fy, o.vx, o.vy)
            for o in self.fish_list
            if o is not self
            and not o.is_predator
            and o.species_name == self.species_name
            and math.hypot(o.fx - self.fx, o.fy - self.fy) <= SCHOOL_RADIUS
        ]

    def _home_occupancy(self, decoration) -> int:
        # Sleepers, hiders, and Evening warming-up guests all share one
        # capacity pool per container -- a Rock already holding 2 sleepers
        # for the night can't also cram in 2 more fish hiding from a Shark
        # or warming up.
        return sum(
            1
            for f in self.fish_list
            if f is not self
            and (
                f.sleeping_in is decoration
                or f._hiding_in is decoration
                or f._warming_in is decoration
            )
        )

    def _roommates_ready_to_leave(self) -> bool:
        """Every fish sharing this home (including self) has to be awake
        and lingering -- a still-asleep/held roommate means nobody leaves
        yet -- and enough time has to have passed since the *last* of them
        woke, not just this one, so the whole room empties together."""
        roommates = [f for f in self.fish_list if f.sleeping_in is self.sleeping_in]
        if any(not r._awake_in_home for r in roommates):
            return False
        latest_wake = max(r._wake_time for r in roommates)
        return time.monotonic() - latest_wake >= WAKE_LINGER_SECONDS

    def _claim_home(self):
        """Pick a container Decoration to sleep inside tonight, or None for
        the tank floor. Baseline priority: the favorite spot, if it happens
        to be a container with room -> a friend's already-claimed container,
        if it has room (so best friends end up sleeping in the same home,
        not just near each other) -> the nearest container with any room ->
        None. Only called while asleep and not yet housed (see draw()), so a
        fish that finds nothing simply retries next frame -- cheap, and
        means a spot freed up mid-night (a tankmate waking early) can still
        be claimed later.

        Personality reorders this baseline rather than replacing it:
          - Lazy won't travel for a container, but won't turn one down
            either -- only takes one already within LAZY_HOME_RADIUS,
            otherwise the floor. Matches its low-effort theme everywhere
            else (LAZY_SPEED_MULT, turn cadence) without making it *refuse*
            a home that happens to already be right there.
          - Shy weights *any* nearby shelter over specifically bunking with
            a friend -- Shy already hides behind decorations from the mouse
            while awake, so safety beats company at night too.
          - Friendly weights sleeping with a friend over even its own
            favorite spot -- being with friends is already Friendly's
            defining trait (mouse-follow, group drift) while awake.
          - Explorer occasionally shuffles to a different container than
            its usual (nearest) pick, echoing its constant-patrol restlessness.
        """
        favorite = self.favorite_decoration
        favorite_ok = (
            favorite is not None
            and favorite.is_container
            and self._home_occupancy(favorite) < favorite.capacity
        )
        friend_home = self.friend.sleeping_in if self.friend is not None else None
        friend_ok = (
            friend_home is not None
            and self._home_occupancy(friend_home) < friend_home.capacity
        )
        containers = sorted(
            (d for d in self.decorations if d.is_container),
            key=lambda d: math.hypot(d.fx - self.fx, d.fy - self.fy),
        )
        nearest = next(
            (d for d in containers if self._home_occupancy(d) < d.capacity), None
        )

        if self.personality == "Lazy":
            if (
                nearest is not None
                and math.hypot(nearest.fx - self.fx, nearest.fy - self.fy)
                <= LAZY_HOME_RADIUS
            ):
                return nearest
            return None
        if self.personality == "Friendly" and friend_ok:
            return friend_home
        if favorite_ok:
            return favorite
        if self.personality == "Shy" and nearest is not None:
            return nearest
        if friend_ok:
            return friend_home
        if (
            self.personality == "Explorer"
            and random.random() < EXPLORER_HOME_SHUFFLE_CHANCE
        ):
            available = [d for d in containers if self._home_occupancy(d) < d.capacity]
            if available:
                return random.choice(available)
        return nearest

    def _glyph(self) -> str:
        # A Baby hasn't grown into its species' real shape yet -- growing up
        # is something you can actually see, not just an Inspector number.
        if self.growth_stage.startswith("Baby"):
            return BABY_RIGHT if self.vx >= 0 else BABY_LEFT
        # An Axolotl visibly looks different while resting (see the
        # Axolotl-tuned relax mechanic above) -- a closed-eyes glyph instead
        # of its normal one, the one purely visual "idle animation" touch.
        if self.species_name == "Axolotl" and time.monotonic() < self._relaxing_until:
            return AXOLOTL_RESTING_GLYPH
        base = self.right_glyph if self.vx >= 0 else self.left_glyph
        wiggling = False
        if self.relaxing:
            # "Just enough to look comfortable" -- a brief tail-flick every
            # RELAX_WIGGLE_INTERVAL seconds, not a real animation state.
            # Phased by birth_time (unique per fish, already on hand) rather
            # than a per-fish timer, so a tank full of relaxing fish doesn't
            # wiggle in lockstep. Reached, for an Axolotl, only once its own
            # closed-eyes window above has lapsed (e.g. mid-join, see the join
            # branch in draw() -- _relaxing_until isn't set by joining).
            phase = (time.monotonic() + self.birth_time) % RELAX_WIGGLE_INTERVAL
            wiggling = phase < RELAX_WIGGLE_DURATION
        elif time.monotonic() < self._excited_wiggle_until:
            # The same tail-flick, reused for a Happy-or-better fish just
            # swimming around ("occasionally wiggles excitedly") -- a timed
            # flash rather than a periodic phase, set by aquarium.py's
            # _process_happiness(). Only reachable while not relaxing, so the
            # two flourishes never fight over the same glyph.
            wiggling = True
        if wiggling:
            base = f"{base}~" if self.vx >= 0 else f"~{base}"
        if self._holding_food is not None:
            # More Fish (updates.md): Worms/Bloodworms held at the mouth for
            # a moment before actually being eaten -- see the caught branch
            # and _consume_food() in draw(). Appended on the facing side,
            # same "mouth end" convention the carried-wood tail placement
            # (below) uses for the opposite end.
            emoji = self._holding_food.glyph
            base = f"{base}{emoji}" if self.vx >= 0 else f"{emoji}{base}"
        return base

    def natural_width(self, scale) -> int:
        return text_width(self._glyph())

    def natural_height(self, scale) -> int:
        return 1

    def _draw_carried_wood(self, canvas) -> None:
        # A foraging fish visibly tows its find home -- the log sits at its
        # tail (the side it's facing away from), so it reads as *carrying*
        # wood rather than just idling next to a stray piece. Only a Forest
        # forager ever carries (see aquarium.py's _check_foraging()), so
        # this is a no-op for every tank fish.
        if self.carrying != "Wood":
            return
        if self.vx >= 0:  # facing right -> tail (and the log) on the left
            wood_x = self.abs_x - text_width(Wood.GLYPH)
        else:  # facing left -> tail (and the log) on the right
            wood_x = self.abs_x + text_width(self._glyph())
        if wood_x >= 0:
            canvas.write(wood_x, self.abs_y, Wood.GLYPH, WOOD_STYLE)

    def _mouse_point(self):
        if self.mouse_pos and self.mouse_pos.get("x") is not None:
            return (self.mouse_pos["x"], self.mouse_pos["y"])
        return None

    def draw(self, canvas) -> None:
        now = time.monotonic()
        dt = now - self._last
        self._last = now  # updated every frame, paused or not (see below)

        # `relaxing` is recomputed from scratch every frame: reset it here so
        # every early return below (paused, travelling, in the Forest, housed)
        # correctly reads as "not relaxing", and only a settle branch far
        # below sets it back True. `was_relaxing` lets those branches fire the
        # arrival flash / one-shot exactly once, on the frame they first
        # settle -- including the transition from solo to joined (or back),
        # which is deliberately treated as a fresh settle, not a continuation.
        was_relaxing = self.relaxing
        self.relaxing = False
        self._relax_spot = None
        self._relaxing_with = None
        self._warm_approaching = False

        if self.paused is not None and self.paused.get("value"):
            # Frozen solid -- no movement, no hunger-independent timers, no
            # steering of any kind. _last still just got updated above, so
            # there's no dt jump the instant the game resumes. A housed fish
            # stays invisible even while paused, same as normal.
            if not self._entered:
                canvas.write(self.abs_x, self.abs_y, self._glyph(), self.style)
                self._draw_carried_wood(canvas)
            return

        if self._travel_until is not None:
            # Mid-trip between biomes -- gone from view in both scenes,
            # same "gone from view" precedent as an already-housed fish.
            # The actual arrival/foraging/delivery logic is entirely
            # timer-driven (see aquarium.py's _check_foraging(), on the
            # per-second tick) rather than anything happening here, so the
            # aquarium keeps running exactly the same whether or not this
            # frame's draw() ever actually gets called for it.
            return
        if self.biome == "forest":
            # None of the tank-scoped steering below applies -- self.foods/
            # self.decorations/self.fish_list all refer to the *aquarium*,
            # the wrong context for a fish physically in the Forest right
            # now. Just draw it where it is; _check_foraging() handles
            # everything else about its stay there.
            if self._entered:
                # Tucked into a Forest shelter for the night (see
                # aquarium.py's _settle_lost_adventure_fish_for_night()) --
                # invisible for the same reason a housed tank fish is: see
                # the _entered branch further down for a Castle/Rock guest.
                return
            canvas.write(self.abs_x, self.abs_y, self._glyph(), self.style)
            self._draw_carried_wood(canvas)
            return

        # More Fish (updates.md): Octopus "sometimes changes color" -- past
        # every early return above (paused/travelling/in the Forest), same
        # as the rest of this file's per-frame timers.
        if self.species_name == "Octopus" and now >= self._next_color_shift:
            self.style.fg = random.choice(OCTOPUS_COLORS)
            self._next_color_shift = now + random.uniform(
                OCTOPUS_COLOR_SHIFT_MIN, OCTOPUS_COLOR_SHIFT_MAX
            )

        # More Fish (updates.md): finishes a Worms/Bloodworms meal once it's
        # been held at the mouth for HOLD_BEFORE_EAT_SECONDS (set in the
        # caught branch further down) -- same "check a _next_/_until
        # timestamp once per frame" shape as the Octopus color shift above.
        if self._holding_food is not None and now >= self._holding_until:
            held = self._holding_food
            self._holding_food = None
            self._consume_food(held)

        if self._hide_until is not None and now >= self._hide_until:
            # Safe to come back out -- reposition at the container's door,
            # same as a fish leaving its claimed home for the night, and
            # let a fresh Shark approach retrigger hiding later.
            self.fx, self.fy = self._hiding_in.fx, self._hiding_in.fy
            self._hiding_in = None
            self._hide_until = None
            self._entered = False
            self._shark_scare_active = False

        if self._storm_sheltering is not None and not (
            self.environment is not None and self.environment.get("storm")
        ):
            # The storm passed while this fish was tucked inside -- come
            # back out right where it took shelter, same as a Shark-hide
            # release above.
            self._storm_sheltering = None
            self._entered = False

        if self._warming_in is not None and now >= self._warming_until:
            # Done warming up -- come back out right where it entered, same
            # release shape as Shark-hiding above.
            self.fx, self.fy = self._warming_in.fx, self._warming_in.fy
            self._warming_in = None
            self._warming_until = 0.0
            self._entered = False
            self._warm_target = None

        if self._warming_at_lamp is not None and now >= self._warming_until:
            # Done basking at the Lamp -- it was visible the whole time
            # (never entered anything), so there's nothing to reposition.
            self._warming_at_lamp = None
            self._warming_until = 0.0
            self._warm_target = None

        speed = self._effective_speed()
        mouse_pos = self._mouse_point()
        # Fully asleep -- not just slower (see is_asleep below for the
        # actual condition). A sleeping fish doesn't wander, chase food,
        # flee, relax, or get any Happiness flourish (aquarium.py's
        # _process_happiness() checks this same property) -- it just settles
        # into position (see below) and stops, same as the turn/relax timers
        # not advancing while asleep (so it picks a fresh direction/relax
        # roll the moment it wakes, rather than acting on a stale decision
        # from before it fell asleep).
        sleeping = self.is_asleep and not (
            self.sleeping_in is None
            and self.environment is not None
            and self.environment.get("storm")
        )
        # A fish with nowhere safe (no claimed container -- see
        # _claim_home()'s "or None for the tank floor") can't sleep through
        # a live storm: overridden back into the awake branch below so it
        # actually runs the storm-shelter-seeking steering ("no matter the
        # personality" -- the elif chain there already overrides every
        # personality branch once reached). A fish that already has a real
        # sleeping_in container stays properly asleep -- it's already safe,
        # same as an awake storm-sheltering fish once it arrives (see the
        # `_entered`/`_storm_sheltering` release check above, which is the
        # container-side half of "stays put through the storm").
        #
        # Unconditional (not just inside the awake branch's priority chain
        # below, where `target`/`seeking_food` normally get their real
        # values) so the flourish section far below -- reached by a sleeping
        # fish too -- can safely read them regardless of which branch ran
        # this frame. More Fish (updates.md): needed for the 😋-while-
        # approaching-Pizza check.
        seeking_food = False
        target = None

        if sleeping:
            self._awake_in_home = False  # guards against a stale True if
            # `sleeping` somehow flips back True mid-linger (day-cycle
            # timing makes this very unlikely, but the invariant "asleep
            # implies not shown awake" should hold regardless of path).
            if self.sleeping_in is None and not self._seeking_friend_after_nightmare:
                # The nightmare-relocation exception: _trigger_nightmare_
                # relocation() can deliberately leave sleeping_in None (no
                # room in the companion's home) so the floor-settle branch
                # below steers this fish toward _nightmare_seek_target --
                # without this guard, the very next frame's auto-claim
                # would immediately grab some other container and short-
                # circuit that seek before the fish ever moved.
                self.sleeping_in = self._claim_home()
            if self.sleeping_in is not None:
                home = self.sleeping_in
                arrive_radius = home.radius + AVOID_MARGIN + HOME_ARRIVE_MARGIN
                if math.hypot(self.fx - home.fx, self.fy - home.fy) > arrive_radius:
                    blend = min(1.0, HOME_STEER_RATE * dt)
                    self.vx, self.vy, _ = steer_toward_food(
                        self.vx,
                        self.vy,
                        self.fx,
                        self.fy,
                        (home.fx, home.fy),
                        speed,
                        blend,
                    )
                else:
                    # Arrived -- tucked inside, invisible from the tank view
                    # until the player clicks the decoration (see draw()'s
                    # early return below and _build_decoration_inspector()).
                    self.vx *= IDLE_DAMPING
                    self.vy *= IDLE_DAMPING
                    self._entered = True
            else:
                # No container claimed tonight -- the original floor
                # behavior: friends sleep close together, rivals sleep as
                # far apart as the tank allows, otherwise just settle
                # wherever night caught it.
                settle_blend = min(1.0, SLEEP_STEER_RATE * dt)
                # A nightmare-seek target (a living parent, or the ordinary
                # Friend once no parent's left -- see
                # _trigger_nightmare_relocation()) always wins over the plain
                # Friend read below; outside a nightmare it's always None,
                # so ordinary nights are completely unaffected.
                seek_toward = self._nightmare_seek_target or self.friend
                if seek_toward is not None:
                    close_enough = (
                        math.hypot(self.fx - seek_toward.fx, self.fy - seek_toward.fy)
                        <= SLEEP_CLOSE_DISTANCE
                    )
                    if close_enough:
                        self.vx *= IDLE_DAMPING
                        self.vy *= IDLE_DAMPING
                    else:
                        self.vx, self.vy, _ = steer_toward_food(
                            self.vx,
                            self.vy,
                            self.fx,
                            self.fy,
                            (seek_toward.fx, seek_toward.fy),
                            speed,
                            settle_blend,
                        )
                elif self.rival is not None:
                    far_enough = (
                        math.hypot(self.fx - self.rival.fx, self.fy - self.rival.fy)
                        >= SLEEP_FAR_DISTANCE
                    )
                    if far_enough:
                        self.vx *= IDLE_DAMPING
                        self.vy *= IDLE_DAMPING
                    else:
                        self.vx, self.vy = steer_away_from(
                            self.vx,
                            self.vy,
                            self.fx,
                            self.fy,
                            (self.rival.fx, self.rival.fy),
                            speed,
                            settle_blend,
                        )
                else:
                    self.vx *= IDLE_DAMPING
                    self.vy *= IDLE_DAMPING
        else:
            if self.sleeping_in is not None:
                if not self._awake_in_home:
                    # Just woke up -- lingers here a moment rather than
                    # instantly vanishing: still tucked in/invisible from
                    # the open tank (the _entered check below is unchanged
                    # and still applies), just no longer shown asleep
                    # wherever occupants_of() is read.
                    self._awake_in_home = True
                    self._wake_time = now
                elif self._roommates_ready_to_leave() and not (
                    self.environment is not None and self.environment.get("storm")
                ):
                    # Everyone sharing this home is awake and lingering,
                    # and it's been WAKE_LINGER_SECONDS since the *last* of
                    # them woke -- the whole room leaves together this
                    # frame instead of trickling out one at a time (each
                    # roommate's own draw() computes this same condition
                    # independently, so they all resolve it simultaneously).
                    # A live storm holds everyone inside regardless -- same
                    # "stays put through the storm" rule the awake
                    # `_storm_sheltering` branch already gives a fish that
                    # took cover this way instead of sleeping through it;
                    # _awake_in_home stays True, so nothing about being
                    # awake-but-lingering changes except the door staying
                    # shut. The very next frame this clears once the storm
                    # ends re-evaluates and lets the room leave normally.
                    self.fx, self.fy = self.sleeping_in.fx, self.sleeping_in.fy
                    self.sleeping_in = None
                    self._entered = False
                    self._awake_in_home = False
            # Whatever the reason `sleeping` just went False -- a real wake
            # attempt succeeding, the fallback timeout, or even the hunger
            # override kicking in while still held -- always clear the
            # holding state here too, so it can never stay stale-True and
            # re-trap this fish back asleep once conditions change again.
            self._holding_asleep = False
            self._wake_attempts_used = 0
            self._wake_threshold = None
            self._held_since = None
            self._wake_waker = None
            self._wake_next_attempt = None
            # A nightmare's scare/relocate/seek/comfort sequence is allowed
            # to keep running even once this fish wakes up naturally partway
            # through it (hunger crossing SLEEP_HUNGER_THRESHOLD, or night
            # simply ending before the sequence finishes) -- aquarium.py's
            # _process_nightmares() drives these fields off real time
            # regardless of is_asleep, and each phase already clears its own
            # field the moment it actually fires. Wiping them here instead
            # (the old behavior) meant a nightmare could be silently
            # cancelled mid-flight with no scare, no toast, nothing -- see
            # the awake seek-toward-companion branch below, which is what
            # actually lets _seeking_friend_after_nightmare's walk continue
            # once this fish is no longer in the sleep-steering branch at
            # all. Only truly stale/finished state (nothing pending, no
            # active flash) gets cleared here, same defensive spirit as
            # before, just narrower.
            nightmare_pending = (
                self._nightmare_wake_at is not None
                or self._nightmare_relocate_at is not None
                or self._seeking_friend_after_nightmare
                or (self._just_scared_until is not None and now < self._just_scared_until)
                or (
                    self._nightmare_comfort_until is not None
                    and now < self._nightmare_comfort_until
                )
            )
            if not nightmare_pending:
                self.dream = None  # whatever it dreamed about, it's awake now
                self._just_scared_until = None
                self._nightmare_comfort_until = None
                self._nightmare_seek_target = None
            if now >= self._next_turn:
                lo, hi = MIN_TURN_DELAY, MAX_TURN_DELAY
                turn_speed = speed
                if self.personality == "Explorer":
                    lo, hi = lo / EXPLORER_TURN_DIV, hi / EXPLORER_TURN_DIV
                elif self.personality == "Lazy":
                    lo, hi = lo * LAZY_TURN_MULT, hi * LAZY_TURN_MULT
                elif self.personality == "Playful":
                    lo, hi = lo / PLAYFUL_TURN_DIV, hi / PLAYFUL_TURN_DIV
                    turn_speed = speed * random.uniform(*PLAYFUL_SPEED_VARIANCE)
                if TRAIT_ENERGETIC in self.traits:
                    # An earned trait, not a personality -- applied after
                    # (and stacking with) whichever personality branch above
                    # just ran, e.g. an Explorer+Energetic fish turns even
                    # more often than a plain Explorer.
                    lo, hi = lo / ENERGETIC_TURN_DIV, hi / ENERGETIC_TURN_DIV
                self.vx, self.vy = random_velocity(turn_speed)
                self._next_turn = now + random.uniform(lo, hi)

            if self.favorite_decoration is not None and now >= self._next_relax_check:
                self._next_relax_check = now + random.uniform(
                    RELAX_CHECK_MIN, RELAX_CHECK_MAX
                )
                is_axolotl = self.species_name == "Axolotl"
                chance = (
                    AXOLOTL_RELAX_CHANCE
                    if is_axolotl
                    # More Fish (updates.md): Salmon "moves constantly" --
                    # never relaxes, regardless of the happiness scaling below.
                    else 0.0 if self.species_name == "Salmon" else RELAX_CHANCE
                )
                # "Visits favorite decoration more often" (Happy) / less so
                # (Sad) -- Axolotl's own already-elevated chance gets the
                # same scaling, so a happy Axolotl rests even more than usual
                # rather than the multiplier only mattering for ordinary fish.
                chance *= HAPPINESS_RELAX_CHANCE_MULT.get(self.feeling, 1.0)
                duration_range = (
                    (AXOLOTL_RELAX_DURATION_MIN, AXOLOTL_RELAX_DURATION_MAX)
                    if is_axolotl
                    else (RELAX_DURATION_MIN, RELAX_DURATION_MAX)
                )
                if random.random() < chance:
                    self._relaxing_until = now + random.uniform(*duration_range)
            relaxing = (
                self.favorite_decoration is not None and now < self._relaxing_until
            )

            if self._warm_target is None and now >= self._next_warm_check:
                # Only re-rolls while it has no target yet -- an in-progress
                # approach (or an already-entered fish, which never reaches
                # here at all -- see the `_entered` early return) keeps its
                # target instead of getting a fresh one mid-walk.
                self._next_warm_check = now + random.uniform(
                    WARM_CHECK_MIN, WARM_CHECK_MAX
                )
                temperature = (
                    self.environment.get("temperature")
                    if self.environment is not None
                    else None
                )
                if (
                    temperature is not None
                    and self.species_name != "Salmon"  # "moves constantly," like relaxing
                ):
                    chill = temperature_chill(temperature)
                    if chill > 0.0 and random.random() < WARM_CHANCE_MAX * chill:
                        # A Warm Lamp, if one exists, beats a container --
                        # _with_room(), not the storm branch's plain nearest,
                        # since a container is actually claimed on arrival,
                        # so capacity has to be checked up front (shares one
                        # pool with sleepers/hiders, see _home_occupancy()).
                        # A Lamp never needs that check (not a container).
                        self._warm_target = (
                            self._nearest_heat_source()
                            or self._nearest_container_with_room()
                        )
            should_warm = (
                not relaxing
                and self._warm_target is not None
                and self._warm_target in self.decorations
            )

            mouse_scare = (
                self.personality == "Shy"
                and mouse_pos is not None
                and math.hypot(self.fx - mouse_pos[0], self.fy - mouse_pos[1])
                < SHY_FLEE_RADIUS
            )
            rival_pos = (
                (self.rival.fx, self.rival.fy) if self.rival is not None else None
            )
            rival_scare = (
                rival_pos is not None
                and math.hypot(self.fx - rival_pos[0], self.fy - rival_pos[1])
                < RIVAL_FLEE_RADIUS
            )
            fleeing = mouse_scare or rival_scare
            # A Rival scares regardless of personality (Goldie swims away from
            # Kevin whether or not she's Shy) -- Shy's mouse-fear takes priority
            # if somehow both are true at once, since it's already the more
            # dramatic threat this fish is built to react to.
            threat_pos = mouse_pos if mouse_scare else rival_pos

            # Per-frame priority: hiding from a Shark (the biggest threat)
            # beats fleeing (fear) beats eating (hunger) beats
            # personality-driven steering (affection/socializing toward the
            # cursor or the group) beats friend-following beats relaxing at the
            # favorite spot beats plain wandering -- exactly one of these blends
            # velocity per frame.
            seeking_food = False
            if self._hiding_in is not None:
                # Set by aquarium.py's _check_shark_scares() -- a bigger
                # threat than the mouse/rival flee below, so it preempts
                # everything else including eating, exactly like fleeing
                # already beats eating (see the priority-chain comment
                # above). Mirrors sleeping_in's own steer-then-settle shape.
                home = self._hiding_in
                arrive_radius = home.radius + AVOID_MARGIN + HOME_ARRIVE_MARGIN
                if math.hypot(self.fx - home.fx, self.fy - home.fy) > arrive_radius:
                    blend = min(1.0, FLEE_STEER_RATE * dt)
                    self.vx, self.vy, _ = steer_toward_food(
                        self.vx,
                        self.vy,
                        self.fx,
                        self.fy,
                        (home.fx, home.fy),
                        speed,
                        blend,
                    )
                else:
                    self.vx *= IDLE_DAMPING
                    self.vy *= IDLE_DAMPING
                    self._entered = True
                    if self._hide_until is None:
                        self._hide_until = now + HIDE_DURATION_SECONDS
            elif fleeing:
                # Only Shy's mouse-fear hides behind a decoration. A Rival
                # never does: two mutual rivals both fleeing toward "my
                # nearest decoration" can converge on the *same* spot if
                # it's nearest to both of them, which looks like they're
                # frozen huddling together right where the user doesn't
                # want them -- the opposite of "put distance between us".
                # Fleeing a Rival always steers straight away instead, with
                # no distance cap, so they keep separating.
                hide_pos = None
                if mouse_scare and self.decorations:
                    i = nearest_index(
                        self.fx, self.fy, [(d.fx, d.fy) for d in self.decorations]
                    )
                    if i is not None:
                        hide_pos = (self.decorations[i].fx, self.decorations[i].fy)
                blend = min(1.0, FLEE_STEER_RATE * dt)
                if hide_pos is not None:
                    # Aimed at a Decoration, not food -- the "ate" flag this
                    # returns is meaningless here and deliberately discarded;
                    # avoid_decorations() below still keeps it from actually
                    # overlapping the decoration it's hiding behind.
                    self.vx, self.vy, _ = steer_toward_food(
                        self.vx, self.vy, self.fx, self.fy, hide_pos, speed, blend
                    )
                else:
                    self.vx, self.vy = steer_away_from(
                        self.vx, self.vy, self.fx, self.fy, threat_pos, speed, blend
                    )
            elif self._seeking_friend_after_nightmare and self._nightmare_seek_target:
                # Continuing a nightmare's comfort-walk (set while still
                # asleep, see the sleep branch above) even though this fish
                # is now awake -- without this, waking up before actually
                # reaching the companion stranded it: nothing here used to
                # keep steering toward them once out of the sleep branch, so
                # _process_nightmares()' arrival check (aquarium.py) could
                # wait forever and the promised comfort never showed.
                # aquarium.py clears _seeking_friend_after_nightmare/
                # _nightmare_seek_target itself the moment it detects arrival.
                companion = self._nightmare_seek_target
                blend = min(1.0, SLEEP_STEER_RATE * dt)
                self.vx, self.vy, _ = steer_toward_food(
                    self.vx,
                    self.vy,
                    self.fx,
                    self.fy,
                    (companion.fx, companion.fy),
                    speed,
                    blend,
                )
            else:
                target = (
                    self._nearest_prey() if self.is_predator else self._nearest_food()
                )
                target_pos = (target.fx, target.fy) if target is not None else None
                if target_pos is not None:
                    # Actively pursuing food/prey overrides the unconditional
                    # avoid_decorations() call below entirely (see seeking_food),
                    # not just the priority chain above -- otherwise food sitting
                    # inside a decoration's avoidance radius (but outside
                    # EAT_RADIUS) could never actually be reached: every frame
                    # avoid_decorations() would shove the fish back out before it
                    # arrived, a real "stuck near the furniture, starving" bug.
                    seeking_food = True
                    greedy = self.personality == "Greedy"
                    has_rival = self.rival is not None
                    food_lover = TRAIT_FOOD_LOVER in self.traits
                    mischievous = TRAIT_MISCHIEVOUS in self.traits
                    food_speed = speed * (
                        (GREEDY_SPEED_MULT if greedy else 1.0)
                        * (RIVAL_FOOD_BOOST if has_rival else 1.0)
                        * (FOOD_LOVER_FOOD_BOOST if food_lover else 1.0)
                        * (MISCHIEVOUS_FOOD_BOOST if mischievous else 1.0)
                    )
                    rate = FOOD_STEER_RATE * (
                        (GREEDY_RATE_MULT if greedy else 1.0)
                        * (RIVAL_FOOD_BOOST if has_rival else 1.0)
                        * (FOOD_LOVER_FOOD_BOOST if food_lover else 1.0)
                        * (MISCHIEVOUS_FOOD_BOOST if mischievous else 1.0)
                    )
                    blend = min(1.0, rate * dt)
                    self.vx, self.vy, caught = steer_toward_food(
                        self.vx,
                        self.vy,
                        self.fx,
                        self.fy,
                        target_pos,
                        food_speed,
                        blend,
                    )
                    if caught:
                        hold_kind = None
                        if self.is_predator:
                            self.fish_list.remove(target)
                            self.on_eat_fish(target)
                        else:
                            self.foods.remove(target)
                            self.on_eat_food(target)
                            self._stole_food_from = self._closer_rival_for(target_pos)
                            hold_kind = getattr(target, "kind", None)
                        if hold_kind in ("Worms", "Bloodworms"):
                            # More Fish (updates.md): held at the mouth for a
                            # moment instead of eaten instantly -- already
                            # taken out of the water (on_eat_food above), but
                            # feed()/Happiness/the on_eaten flavor hook (in
                            # _consume_food) wait for draw()'s per-frame check
                            # near the top of this file. _glyph() shows the
                            # held emoji meanwhile.
                            self._holding_food = target
                            self._holding_until = now + HOLD_BEFORE_EAT_SECONDS
                        else:
                            self._consume_food(target)
                elif self.environment is not None and self.environment.get("storm"):
                    # A live storm (see aquarium.py's _maybe_trigger_random_event()/
                    # _end_storm()) overrides personality-driven steering/friend-
                    # following/relaxing/schooling -- everyone heads for the
                    # nearest container and huddles there for the duration --
                    # but never eating/fleeing, which stay more urgent than
                    # taking cover.
                    shelter = self._nearest_container()
                    if shelter is not None:
                        arrive_radius = (
                            shelter.radius + AVOID_MARGIN + HOME_ARRIVE_MARGIN
                        )
                        if (
                            math.hypot(self.fx - shelter.fx, self.fy - shelter.fy)
                            > arrive_radius
                        ):
                            blend = min(1.0, HOME_STEER_RATE * dt)
                            self.vx, self.vy, _ = steer_toward_food(
                                self.vx,
                                self.vy,
                                self.fx,
                                self.fy,
                                (shelter.fx, shelter.fy),
                                speed,
                                blend,
                            )
                        else:
                            # Arrived -- tucked inside like a sleeping/
                            # shark-hiding fish (see draw()'s _entered
                            # early return below); released once the storm
                            # ends (see the top-of-draw() check above).
                            self.vx *= IDLE_DAMPING
                            self.vy *= IDLE_DAMPING
                            self._entered = True
                            self._storm_sheltering = shelter
                elif self.personality == "Friendly" and mouse_pos is not None:
                    blend = min(1.0, FOLLOW_MOUSE_RATE * dt)
                    self.vx, self.vy, _ = steer_toward_food(
                        self.vx, self.vy, self.fx, self.fy, mouse_pos, speed, blend
                    )
                elif (
                    self.personality == "Friendly"
                    and self._group_centroid() is not None
                ):
                    # No mouse to follow -- drift gently toward the group instead.
                    cx, cy = self._group_centroid()
                    blend = min(1.0, SOCIAL_STEER_RATE * dt)
                    self.vx, self.vy, _ = steer_toward_food(
                        self.vx, self.vy, self.fx, self.fy, (cx, cy), speed, blend
                    )
                elif (
                    self.friend is not None
                    and self.friend.relaxing
                    and self.friend._relax_spot is not None
                    and self.feeling != "Sad"
                ):
                    # A friend is already settled somewhere -- swim over and
                    # join them instead of just generically following their
                    # live position (the plain friend-follow branch below).
                    # Aimed at the friend's *spot* (a fixed Decoration), not
                    # their fx/fy, so this fish actually arrives and settles
                    # too rather than perpetually chasing a moving target.
                    spot = self.friend._relax_spot
                    arrive_radius = spot.radius + AVOID_MARGIN + RELAX_ARRIVE_MARGIN
                    if math.hypot(self.fx - spot.fx, self.fy - spot.fy) > arrive_radius:
                        blend = min(1.0, RELAX_STEER_RATE * dt)
                        self.vx, self.vy, _ = steer_toward_food(
                            self.vx,
                            self.vy,
                            self.fx,
                            self.fy,
                            (spot.fx, spot.fy),
                            speed,
                            blend,
                        )
                    else:
                        self.vx *= IDLE_DAMPING
                        self.vy *= IDLE_DAMPING
                        self.relaxing = True
                        self._relax_spot = spot
                        self._relaxing_with = self.friend
                        if not was_relaxing:
                            self._relax_flash_until = now + RELAX_FLASH_SECONDS
                            self._joined_friend_relax = True
                elif self.friend is not None and self.feeling != "Sad":
                    # "They often swim together" -- unlike Friendly's group pull,
                    # this is a specific bond, not personality-gated, and applies
                    # to any fish with a Friend once nothing more urgent (food,
                    # fleeing, its own personality-steering) claims this frame.
                    # "Follows friend around" (Very Happy, HAPPINESS_FOLLOW_*)
                    # is the same steering, just temporarily boosted -- not a
                    # separate behavior. A Sad fish skips this branch entirely
                    # ("wanders alone") and falls through toward relaxing/
                    # schooling/plain wandering below instead.
                    rate = FRIEND_STEER_RATE
                    if now < self._following_until:
                        rate *= HAPPINESS_FOLLOW_STEER_MULT
                    blend = min(1.0, rate * dt)
                    self.vx, self.vy, _ = steer_toward_food(
                        self.vx,
                        self.vy,
                        self.fx,
                        self.fy,
                        (self.friend.fx, self.friend.fy),
                        speed,
                        blend,
                    )
                elif relaxing:
                    spot = self.favorite_decoration
                    arrive_radius = spot.radius + AVOID_MARGIN + RELAX_ARRIVE_MARGIN
                    if math.hypot(self.fx - spot.fx, self.fy - spot.fy) > arrive_radius:
                        blend = min(1.0, RELAX_STEER_RATE * dt)
                        self.vx, self.vy, _ = steer_toward_food(
                            self.vx,
                            self.vy,
                            self.fx,
                            self.fy,
                            (spot.fx, spot.fy),
                            speed,
                            blend,
                        )
                    else:
                        # Arrived -- settle down instead of continuing to steer,
                        # so it visibly relaxes rather than endlessly orbiting the
                        # spot. avoid_decorations() below still keeps it from
                        # actually overlapping the decoration it's next to.
                        self.vx *= IDLE_DAMPING
                        self.vy *= IDLE_DAMPING
                        # Actually settled now -- this is the moment worth
                        # surfacing (see draw()'s indicator chain and
                        # aquarium.py's _process_relaxing()).
                        self.relaxing = True
                        self._relax_spot = spot
                        if not was_relaxing:
                            self._relax_flash_until = now + RELAX_FLASH_SECONDS
                            self._relax_began = True
                elif should_warm:
                    # Evening warming-up: same "steer to a spot" shape as
                    # relaxing just above, aimed at a Warm Lamp if one
                    # exists (preferred) or else the nearest real container
                    # with room. A container is actually entered, same
                    # tucked-in/invisible mechanism sleeping_in/_hiding_in
                    # already use (see the `_entered` early return above);
                    # a Lamp isn't a container, so it just lingers nearby,
                    # visible, instead.
                    spot = self._warm_target
                    arrive_radius = spot.radius + AVOID_MARGIN + WARM_ARRIVE_MARGIN
                    if math.hypot(self.fx - spot.fx, self.fy - spot.fy) > arrive_radius:
                        # Still on the way -- draw()'s indicator chain shows
                        # 🥶 for as long as this stays True, not a timed flash.
                        self._warm_approaching = True
                        blend = min(1.0, WARM_STEER_RATE * dt)
                        self.vx, self.vy, _ = steer_toward_food(
                            self.vx,
                            self.vy,
                            self.fx,
                            self.fy,
                            (spot.fx, spot.fy),
                            speed,
                            blend,
                        )
                    elif spot.heat_source:
                        # Arrived at the Lamp -- just settle in place, same
                        # idle-damp as relaxing, never "entered". Same
                        # release shape as the container branch below:
                        # _warming_until is only set once, right here.
                        self.vx *= IDLE_DAMPING
                        self.vy *= IDLE_DAMPING
                        self._warming_at_lamp = spot
                        self._warming_until = now + random.uniform(
                            WARM_DURATION_MIN, WARM_DURATION_MAX
                        )
                    else:
                        # Arrived at a container -- go inside. Same release
                        # shape as Shark-hiding: _warming_until is only set
                        # once, right here, not back when the urge started.
                        self._entered = True
                        self._warming_in = spot
                        self._warming_until = now + random.uniform(
                            WARM_DURATION_MIN, WARM_DURATION_MAX
                        )
                elif self._circling_until and now < self._circling_until:
                    # "Swims in circles" (❤️, Very Happy) -- orbit the pivot
                    # captured when the roll landed (aquarium.py's
                    # _process_happiness()), rather than steering anywhere
                    # else. Ranked below relaxing/friend-following/joining
                    # (nothing here ever preempts something more urgent or
                    # more meaningful) but above plain schooling/wandering,
                    # so it's visible rather than lost under ambient drift.
                    angle = (now - self._circle_start) * HAPPINESS_CIRCLE_ANGULAR_SPEED
                    pivot_x, pivot_y = self._circle_pivot
                    target = (
                        pivot_x + HAPPINESS_CIRCLE_RADIUS * math.cos(angle),
                        pivot_y + HAPPINESS_CIRCLE_RADIUS * math.sin(angle),
                    )
                    blend = min(1.0, HAPPINESS_CIRCLE_STEER_RATE * dt)
                    self.vx, self.vy, _ = steer_toward_food(
                        self.vx, self.vy, self.fx, self.fy, target, speed, blend
                    )
                else:
                    # Schooling: the bottom of the priority chain, just above
                    # plain wandering -- a species-level ambient behavior
                    # (unlike Friendly's personality-gated group pull above),
                    # so it applies to whichever fish reach here with nothing
                    # more urgent going on. No schoolmates in range simply
                    # leaves this frame's turn-timer velocity untouched.
                    schoolmates = self._schoolmates()
                    if schoolmates:
                        blend = min(1.0, SCHOOL_STEER_RATE * dt)
                        self.vx, self.vy = school_velocity(
                            self.fx,
                            self.fy,
                            self.vx,
                            self.vy,
                            schoolmates,
                            speed,
                            blend,
                            SCHOOL_COHESION_WEIGHT,
                            SCHOOL_ALIGNMENT_WEIGHT,
                            SCHOOL_SEPARATION_WEIGHT,
                            SCHOOL_SEPARATION_DISTANCE,
                        )
                    elif (
                        self.growth_stage.startswith("Baby")
                        and self.bubbles is not None
                        and self._bubble_chase_eligible_today
                    ):
                        # Even further below schooling -- purely a Baby's
                        # own whim, only when nothing else (not even a
                        # schoolmate) claimed this frame, and only on a day
                        # its own roll allows it at all (see constants.py's
                        # BUBBLE_CHASE_CHANCE_PER_DAY comment). Purely
                        # cosmetic: bubbles.py's BubbleField is never
                        # mutated here.
                        bubble = self.bubbles.nearest_bubble(
                            self.fx, self.fy, BUBBLE_CHASE_RADIUS
                        )
                        if bubble is not None:
                            blend = min(1.0, BUBBLE_CHASE_STEER_RATE * dt)
                            self.vx, self.vy, caught = steer_toward_food(
                                self.vx,
                                self.vy,
                                self.fx,
                                self.fy,
                                (bubble.x, bubble.y),
                                speed,
                                blend,
                            )
                            if caught:
                                self._bubble_chase_caught = True

            if self.decorations and not seeking_food and self._hiding_in is None:
                # A fish heading into a container to hide from a Shark needs
                # to actually reach/overlap it (unlike Shy's mouse-flee
                # hide_pos above, which deliberately only hides *behind* one
                # -- avoid_decorations() would otherwise shove it back out
                # before it ever arrived, the same "stuck near the
                # furniture" problem seeking_food already works around).
                avoid_blend = min(1.0, AVOID_STEER_RATE * dt)
                self.vx, self.vy = avoid_decorations(
                    self.vx,
                    self.vy,
                    self.fx,
                    self.fy,
                    [(d.fx, d.fy, d.radius) for d in self.decorations],
                    speed,
                    avoid_blend,
                )

        if self._entered:
            # Tucked inside a container -- frozen in place and invisible from
            # the tank view, same as not being able to see through the Castle's
            # walls. See _build_decoration_inspector() for how to peek inside.
            # The exceptions are live, momentary beats that can happen entirely
            # inside a container: a fish scared awake by a nightmare (😨), one
            # being comforted beside a friend afterward (🥺), one mid-wake-
            # attempt on a tankmate (*boop*), or the tankmate on the receiving
            # end of a resisted attempt (*...zzz*). Every one of these has a
            # housed player watching the tank, without this they'd only ever
            # show in the Castle Interior -- lost. Same priority order as
            # _build_castle_interior()'s own mood chain (boop first). The
            # mood-only glyph mirrors the main indicator chain below; nothing
            # else about being housed changes (no glyph, no steering, frozen).
            # Anchored to the container's own position, not this fish's --
            # a housed fish's fx/fy is wherever it happened to be when it
            # crossed arrive_radius (up to a container-radius-plus-margin
            # away from the container's actual glyph), so anchoring to self
            # could float the glyph out over open, unrelated water with
            # nothing nearby to explain it. Anchoring to the container
            # itself means it always appears right at the furniture the
            # player would otherwise have to open the Inspector to check.
            home = self.sleeping_in or self._hiding_in or self._warming_in
            mood_x = home.abs_x if home is not None else self.abs_x
            mood_y = max(0, (home.abs_y if home is not None else self.abs_y) - 1)
            if self._just_booped_until is not None and now < self._just_booped_until:
                canvas.write(mood_x, mood_y, "*boop*", MUTED)
            elif self._just_scared_until is not None and now < self._just_scared_until:
                canvas.write(mood_x, mood_y, "😨", MUTED)
            elif (
                self._nightmare_comfort_until is not None
                and now < self._nightmare_comfort_until
            ):
                canvas.write(mood_x, mood_y, "🥺", MUTED)
            elif (
                self._just_resisted_wake_until is not None
                and now < self._just_resisted_wake_until
            ):
                canvas.write(mood_x, mood_y, "*...zzz*", MUTED)
            elif self._warming_in is not None:
                # Content, warming up -- lowest priority here since it's the
                # only one of this group that isn't a brief, one-shot beat
                # (it holds for the fish's whole stay, same as sleep's 😴
                # would if a housed fish's ordinary glyph were shown at all).
                canvas.write(mood_x, mood_y, "☺️", MUTED)
            return

        self.fx, self.fy, self.vx, self.vy = steer(
            self.fx, self.fy, self.vx, self.vy, self.bounds, dt
        )
        self.x, self.y = round(self.fx), round(self.fy)
        canvas.write(self.abs_x, self.abs_y, self._glyph(), self.style)

        if self._just_booped_until is not None and now < self._just_booped_until:
            # Mid wake-attempt on a tankmate (aquarium.py's
            # _process_sleepy_holds()) -- same priority as the housed branch
            # above (this can also happen to a fish that's since left its
            # container while the flash was still counting down).
            canvas.write(self.abs_x, max(0, self.abs_y - 1), "*boop*", MUTED)
        elif self._just_scared_until is not None and now < self._just_scared_until:
            # A nightmare just forced an early wake -- takes visual priority
            # over everything else below, same reasoning as sleep beating
            # the Friendly heart: a fish scared awake isn't quietly dreaming
            # or mooning over the cursor.
            canvas.write(self.abs_x, max(0, self.abs_y - 1), "😨", MUTED)
        elif (
            self._nightmare_comfort_until is not None
            and now < self._nightmare_comfort_until
        ):
            canvas.write(self.abs_x, max(0, self.abs_y - 1), "🥺", MUTED)
        elif (
            self._just_resisted_wake_until is not None
            and now < self._just_resisted_wake_until
        ):
            # The other half of a resisted wake attempt -- still asleep, but
            # a beat more notable than the plain 😴 below for a moment.
            canvas.write(self.abs_x, max(0, self.abs_y - 1), "*...zzz*", MUTED)
        elif sleeping:
            # Sleep takes visual priority over a Friendly heart -- a fish
            # fast asleep isn't also mooning over the cursor. A dreaming
            # fish gets a 💭 alongside its 😴 -- purely a hint that there's
            # something to click open (see aquarium.py's _open_dream()).
            glyph = "😴💭" if self.dream is not None else "😴"
            canvas.write(self.abs_x, max(0, self.abs_y - 1), glyph, MUTED)
        elif self._racing_until and now < self._racing_until:
            # A Baby race's own visual (aquarium.py's _check_baby_races()) --
            # above sleep-adjacent flourishes' priority but below the
            # actually-serious ones above (booped/scared/comfort/resisted
            # wake), since a race is exciting, not urgent.
            canvas.write(self.abs_x, max(0, self.abs_y - 1), "💨", MUTED)
        elif self._relax_flash_until and now < self._relax_flash_until:
            # A brief 😌 when a fish first settles by its favorite spot -- a
            # glance-and-gone notice, not a permanent badge (it fades while the
            # fish keeps relaxing). Awake, so it can't collide with 😴 above.
            canvas.write(self.abs_x, max(0, self.abs_y - 1), "😌", MUTED)
        elif self._warm_approaching:
            # Still on the way to warm up -- 🥶 for the whole approach, not a
            # one-shot notice. Once it actually arrives at a container it
            # enters (see the `_entered` early return above) and this stops
            # applying; its ☺️ is drawn from that branch's own mood-icon
            # chain instead. Arriving at a Lamp falls straight into the elif
            # just below instead, since it never enters anything.
            canvas.write(self.abs_x, max(0, self.abs_y - 1), "🥶", MUTED)
        elif self._warming_at_lamp is not None:
            # Basking at a Warm Lamp -- visible the whole time (never
            # entered), so its own ☺️ lives in this ordinary indicator
            # chain rather than the `_entered` mood-icon one above.
            canvas.write(self.abs_x, max(0, self.abs_y - 1), "☺️", MUTED)
        elif self._pizza_eat_flash_until and now < self._pizza_eat_flash_until:
            # More Fish (updates.md): the second half of the two-frame Pizza
            # reaction -- 😋 while closing in (see the lowest-priority elif
            # below), ☺️ right after (_consume_food() sets this).
            canvas.write(self.abs_x, max(0, self.abs_y - 1), "☺️", MUTED)
        elif self._sparkle_until and now < self._sparkle_until:
            # A Very Happy fish's own ambient flourish -- rare and rate-
            # limited by construction (see aquarium.py's _process_happiness()'s
            # HAPPINESS_SPARKLE_CHANCE roll), so this never turns into a
            # permanent badge either.
            canvas.write(self.abs_x, max(0, self.abs_y - 1), "✨", MUTED)
        elif self._circling_until and now < self._circling_until:
            # "Swims in circles" -- see the movement branch above for the
            # actual orbiting; this is just its above-the-fish marker.
            canvas.write(self.abs_x, max(0, self.abs_y - 1), "❤️", HEART_STYLE)
        elif self.personality == "Friendly" and mouse_pos is not None:
            close = (
                math.hypot(self.fx - mouse_pos[0], self.fy - mouse_pos[1])
                < HEART_RADIUS
            )
            if close:
                canvas.write(self.abs_x, max(0, self.abs_y - 1), "💕", HEART_STYLE)
        elif (
            seeking_food
            and target is not None
            and getattr(target, "kind", None) == "Pizza"
        ):
            # More Fish (updates.md): the first half of the two-frame Pizza
            # reaction -- live state tracking the chase itself (not a timer,
            # unlike every other flourish above), so it lasts exactly as
            # long as the approach does. ☺️ (_pizza_eat_flash_until, above)
            # takes over the instant it's actually eaten.
            canvas.write(self.abs_x, max(0, self.abs_y - 1), "😋", MUTED)


def _make_fish(
    bounds,
    foods,
    fish_list,
    on_eat_food,
    on_eat_fish,
    species: Species,
    decorations=None,
    mouse_pos=None,
    environment=None,
    paused=None,
    bubbles=None,
) -> Fish:
    x0, y0, x1, y1 = bounds
    x = random.uniform(x0, x1)
    y = random.uniform(y0, y1)
    return Fish(
        x,
        y,
        bounds,
        foods,
        fish_list,
        on_eat_food,
        on_eat_fish,
        species.right,
        species.left,
        species.color,
        is_predator=species.predator,
        decorations=decorations,
        species_name=species.name,
        mouse_pos=mouse_pos,
        price=species.price,
        environment=environment,
        paused=paused,
        favorite_foods=species.favorite_foods,
        rarity=species.rarity,
        bubbles=bubbles,
    )


def fish_at(fish_list, col: int, row: int):
    """The Fish in `fish_list` currently occupying (col, row), or None --
    used to tell "clicked a fish" (rename it) apart from "clicked open
    water" (feed) in the same left-click."""
    for f in fish_list:
        w = f.natural_width(1)
        if f.y == row and f.x <= col < f.x + w:
            return f
    return None


def occupants_of(decoration, fish_list) -> list:
    """Every Fish currently sleeping inside `decoration` tonight, in no
    particular order -- what the Decoration Inspector peeks in to show
    (see _build_decoration_inspector())."""
    return [f for f in fish_list if f.sleeping_in is decoration]


def describe_fish(f: Fish) -> str:
    """One-line tooltip text: name, species, growth stage, personality,
    fullness, and (if any) a short relationship hint -- the full detail
    (state + recent reasons) lives in the Inspector, this is just enough to
    notice a bond exists. Never shows the raw score (Step 8), only the
    state's own emoji (relationship_state()). Labeled "Fullness", not
    "Hunger" -- f.hunger is 0=starving/100=full, so a literal "Hunger: 90%"
    label would read backwards (90% sounding like "very hungry")."""
    relationship = ""
    if f.friend is not None:
        _label, emoji = relationship_state(f.relationships[f.friend].score)
        relationship = f" - {emoji} {f.friend.display_name}"
    elif f.rival is not None:
        _label, emoji = relationship_state(f.relationships[f.rival].score)
        relationship = f" - {emoji} {f.rival.display_name}"
    return (
        f"{f.display_name} ({f.species_name}, {f.growth_stage}) - "
        f"{f.personality} - Fullness {f.hunger:.0f}%{relationship}"
    )
