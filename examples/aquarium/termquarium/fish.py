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
    EXPLORER_HOME_SHUFFLE_CHANCE,
    FLEE_STEER_RATE,
    FOLLOW_MOUSE_RATE,
    FOOD_STEER_RATE,
    FRIEND_STEER_RATE,
    GREEDY_RATE_MULT,
    GREEDY_SPEED_MULT,
    GROWTH_STAGES,
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
    PLAYFUL_SPEED_VARIANCE,
    PLAYFUL_TURN_DIV,
    RELAX_ARRIVE_MARGIN,
    RELAX_CHANCE,
    RELAX_CHECK_MAX,
    RELAX_CHECK_MIN,
    RELAX_DURATION_MAX,
    RELAX_DURATION_MIN,
    RELAX_STEER_RATE,
    RIVAL_FLEE_RADIUS,
    RIVAL_FOOD_BOOST,
    SCHOOL_ALIGNMENT_WEIGHT,
    SCHOOL_COHESION_WEIGHT,
    SCHOOL_RADIUS,
    SCHOOL_SEPARATION_DISTANCE,
    SCHOOL_SEPARATION_WEIGHT,
    SCHOOL_STEER_RATE,
    SHY_FLEE_RADIUS,
    SLEEP_CLOSE_DISTANCE,
    SLEEP_FAR_DISTANCE,
    SLEEP_HUNGER_THRESHOLD,
    SLEEP_STEER_RATE,
    SOCIAL_STEER_RATE,
    AGE_SECONDS_PER_DAY,
    WAKE_LINGER_SECONDS,
    Species,
)
from .economy import feed
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
        # Shared {"phase": "Day"/"Morning"/"Night", "temperature": float}
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
        self.mouse_pos = mouse_pos  # shared {"x":.., "y":..} dict, or None
        self.personality = random_personality()
        # Independent of (and stackable with) personality -- see
        # roll_is_sleepy()'s docstring. A Greedy fish can also be Sleepy.
        self.is_sleepy = roll_is_sleepy()
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
        self.speed = random.uniform(MIN_SPEED, MAX_SPEED)
        self.vx, self.vy = random_velocity(self._effective_speed())
        self.hunger = 0.0  # 0 = full, 100 = starving
        self.health = 100.0
        # Rolled fresh each night by aquarium.py's _assign_dreams(), cleared
        # the moment this fish wakes (see the wake-reset block below) --
        # None means "not dreaming tonight", not "hasn't been asked yet".
        self.dream = None
        # This fish's own diary -- distinct from Relationship.memories
        # (relationships.py), which is a shared pair record. Populated by
        # aquarium.py's _log_memory() at real, already-tracked event sites;
        # newest last, oldest dropped once it exceeds MEMORY_LOG_LIMIT.
        self.memory_log: list[str] = []
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
                min_age for name, min_age, _mult in GROWTH_STAGES if name == "Adult"
            )
            self.birth_time -= AGE_SECONDS_PER_DAY * (adult_age_days + 0.5)
        self._last = time.monotonic()
        self._next_turn = self._last + random.uniform(MIN_TURN_DELAY, MAX_TURN_DELAY)
        self._relaxing_until = 0.0
        self._next_relax_check = self._last + random.uniform(
            RELAX_CHECK_MIN, RELAX_CHECK_MAX
        )

    @property
    def age_days(self) -> float:
        return (time.monotonic() - self.birth_time) / AGE_SECONDS_PER_DAY

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
        if self.growth_stage == "Elder":
            mult *= ELDER_SPEED_MULT  # measurably slower with age
        if self.environment is not None:
            temperature = self.environment.get("temperature")
            if temperature is not None and temperature < COLD_TEMP_THRESHOLD:
                mult *= COLD_SPEED_MULT  # cold-blooded and sluggish
        return self.speed * mult

    def _nearest_food(self):
        i = nearest_index(self.fx, self.fy, [(f.fx, f.fy) for f in self.foods])
        return self.foods[i] if i is not None else None

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
        # Sleepers and hiders share one capacity pool per container -- a
        # Rock already holding 2 sleepers for the night can't also cram in
        # 2 more fish hiding from a Shark.
        return sum(
            1
            for f in self.fish_list
            if f is not self
            and (f.sleeping_in is decoration or f._hiding_in is decoration)
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
        if self.growth_stage == "Baby":
            return BABY_RIGHT if self.vx >= 0 else BABY_LEFT
        # An Axolotl visibly looks different while resting (see the
        # Axolotl-tuned relax mechanic above) -- a closed-eyes glyph instead
        # of its normal one, the one purely visual "idle animation" touch.
        if self.species_name == "Axolotl" and time.monotonic() < self._relaxing_until:
            return AXOLOTL_RESTING_GLYPH
        return self.right_glyph if self.vx >= 0 else self.left_glyph

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
            canvas.write(self.abs_x, self.abs_y, self._glyph(), self.style)
            self._draw_carried_wood(canvas)
            return

        if self._hide_until is not None and now >= self._hide_until:
            # Safe to come back out -- reposition at the container's door,
            # same as a fish leaving its claimed home for the night, and
            # let a fresh Shark approach retrigger hiding later.
            self.fx, self.fy = self._hiding_in.fx, self._hiding_in.fy
            self._hiding_in = None
            self._hide_until = None
            self._entered = False
            self._shark_scare_active = False

        speed = self._effective_speed()
        mouse_pos = self._mouse_point()
        # Fully asleep -- not just slower. A sleeping fish doesn't wander,
        # chase food, flee, or relax; it just settles into position (see
        # below) and stops, same as the turn/relax timers not advancing
        # while asleep (so it picks a fresh direction/relax roll the moment
        # it wakes, rather than acting on a stale decision from before it
        # fell asleep). A fish hungry enough to actually be in danger stays
        # up instead -- sleeping through your own starvation isn't cozy,
        # it's just a bug wearing a nightcap. A Shark never qualifies at
        # all, regardless of hunger or time of day -- the whole point of
        # buying one is an ever-present threat, and a sleeping predator
        # could otherwise claim a container alongside its own prey, bond
        # with it (record_slept_together doesn't distinguish predators),
        # and even get a nightmare of its own (see aquarium.py's
        # _assign_dreams(), which excludes predators for the same reason).
        sleeping = (
            not self.is_predator  # a Shark stays active -- and hunting -- all night
            and self.environment is not None
            and (self.environment.get("phase") == "Night" or self._holding_asleep)
            and self.hunger <= SLEEP_HUNGER_THRESHOLD
        )

        if sleeping:
            self._awake_in_home = False  # guards against a stale True if
            # `sleeping` somehow flips back True mid-linger (day-cycle
            # timing makes this very unlikely, but the invariant "asleep
            # implies not shown awake" should hold regardless of path).
            if self.sleeping_in is None:
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
                if self.friend is not None:
                    close_enough = (
                        math.hypot(self.fx - self.friend.fx, self.fy - self.friend.fy)
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
                            (self.friend.fx, self.friend.fy),
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
                elif self._roommates_ready_to_leave():
                    # Everyone sharing this home is awake and lingering,
                    # and it's been WAKE_LINGER_SECONDS since the *last* of
                    # them woke -- the whole room leaves together this
                    # frame instead of trickling out one at a time (each
                    # roommate's own draw() computes this same condition
                    # independently, so they all resolve it simultaneously).
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
            self.dream = None  # whatever it dreamed about, it's awake now
            # Defensive cleanup for a normal wake landing mid-nightmare-
            # reaction (e.g. morning arrives before the 5s scare timer, or
            # while still mid-comfort-flash) -- _process_nightmares() itself
            # clears these the moment it actually fires each phase.
            self._nightmare_wake_at = None
            self._nightmare_relocate_at = None
            self._just_scared_until = None
            self._nightmare_comfort_until = None
            self._seeking_friend_after_nightmare = False
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
                self.vx, self.vy = random_velocity(turn_speed)
                self._next_turn = now + random.uniform(lo, hi)

            if self.favorite_decoration is not None and now >= self._next_relax_check:
                self._next_relax_check = now + random.uniform(
                    RELAX_CHECK_MIN, RELAX_CHECK_MAX
                )
                is_axolotl = self.species_name == "Axolotl"
                chance = AXOLOTL_RELAX_CHANCE if is_axolotl else RELAX_CHANCE
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
                    food_speed = speed * (
                        (GREEDY_SPEED_MULT if greedy else 1.0)
                        * (RIVAL_FOOD_BOOST if has_rival else 1.0)
                    )
                    rate = FOOD_STEER_RATE * (
                        (GREEDY_RATE_MULT if greedy else 1.0)
                        * (RIVAL_FOOD_BOOST if has_rival else 1.0)
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
                        if self.is_predator:
                            self.fish_list.remove(target)
                            self.on_eat_fish(target)
                        else:
                            self.foods.remove(target)
                            self.on_eat_food(target)
                        self.hunger, self.health = feed(self.hunger, self.health)
                        # A special food (a dropped treat) reacts to whoever
                        # actually ate it -- fired here, after feed(), so the
                        # reaction sees the fed hunger/health. Plain food and
                        # eaten prey have no such hook.
                        on_eaten = getattr(target, "on_eaten", None)
                        if on_eaten is not None:
                            on_eaten(self)
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
                            self.vx *= IDLE_DAMPING
                            self.vy *= IDLE_DAMPING
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
                elif self.friend is not None:
                    # "They often swim together" -- unlike Friendly's group pull,
                    # this is a specific bond, not personality-gated, and applies
                    # to any fish with a Friend once nothing more urgent (food,
                    # fleeing, its own personality-steering) claims this frame.
                    blend = min(1.0, FRIEND_STEER_RATE * dt)
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
            # Tucked inside a container -- frozen in place and invisible
            # from the tank view, same as the player physically not being
            # able to see through the Castle's walls. See
            # _build_decoration_inspector() for how to peek inside.
            return

        self.fx, self.fy, self.vx, self.vy = steer(
            self.fx, self.fy, self.vx, self.vy, self.bounds, dt
        )
        self.x, self.y = round(self.fx), round(self.fy)
        canvas.write(self.abs_x, self.abs_y, self._glyph(), self.style)

        if self._just_scared_until is not None and now < self._just_scared_until:
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
        elif sleeping:
            # Sleep takes visual priority over a Friendly heart -- a fish
            # fast asleep isn't also mooning over the cursor. A dreaming
            # fish gets a 💭 alongside its 😴 -- purely a hint that there's
            # something to click open (see aquarium.py's _open_dream()).
            glyph = "😴💭" if self.dream is not None else "😴"
            canvas.write(self.abs_x, max(0, self.abs_y - 1), glyph, MUTED)
        elif self.personality == "Friendly" and mouse_pos is not None:
            close = (
                math.hypot(self.fx - mouse_pos[0], self.fy - mouse_pos[1])
                < HEART_RADIUS
            )
            if close:
                canvas.write(self.abs_x, max(0, self.abs_y - 1), "💕", HEART_STYLE)


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
    hunger, and (if any) a short relationship hint -- the full detail
    (state + recent reasons) lives in the Inspector, this is just enough to
    notice a bond exists. Never shows the raw score (Step 8), only the
    state's own emoji (relationship_state())."""
    relationship = ""
    if f.friend is not None:
        _label, emoji = relationship_state(f.relationships[f.friend].score)
        relationship = f" - {emoji} {f.friend.display_name}"
    elif f.rival is not None:
        _label, emoji = relationship_state(f.relationships[f.rival].score)
        relationship = f" - {emoji} {f.rival.display_name}"
    return (
        f"{f.display_name} ({f.species_name}, {f.growth_stage}) - "
        f"{f.personality} - Hunger {f.hunger:.0f}%{relationship}"
    )
