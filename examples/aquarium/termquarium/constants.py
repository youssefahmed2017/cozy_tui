"""Shared gameplay thresholds and tuning values."""

from collections import namedtuple

# A single tank-level toast is shown when one or more fish cross this level.
# It is intentionally below starvation (100) so the player has time to act.
HUNGER_WARNING_THRESHOLD = 50.0
# name, right-facing glyph, left-facing glyph (hand-mirrored rather than
# auto-flipped so each species still looks recognizable facing the other
# way, not just a reversed string), color, shop price, predator flag,
# favorite treat kinds (TREAT_SHOP_ITEMS kinds this species reacts to with
# extra delight when fed -- see aquarium.py's _feed_treat -- defaulted to ()
# since only Axolotl has any today; never a stat bonus, just a nicer toast).
Species = namedtuple(
    "Species", "name right left color price predator favorite_foods", defaults=[()]
)

SHOP_ITEMS = [
    Species("Goldfish", "><>", "<><", "bright_yellow", 20, False),
    Species("Angelfish", "><(((°>", "<°)))><", "bright_cyan", 40, False),
    Species("Betta", "><{{{°>", "<°}}}><", "bright_red", 55, False),
    Species("Shark", "▶===>", "<===◀", "white", 500, True),
    # Not "fish with 20 unique mechanics" -- a delightful new resident that
    # reuses Fish entirely (same growth/hunger/relationships/container-
    # sleeping as everything else) with a few small, personality-flavored
    # differences instead of any stat advantage: priced between Angelfish
    # and Betta (deliberately unremarkable), and it has favorite foods that
    # give the Treats system somewhere new to matter (see _feed_treat).
    Species(
        "Axolotl",
        "(°.°)~",
        "~(°.°)",
        "bright_magenta",
        45,
        False,
        ("Brine Shrimp", "Bloodworms", "Worms"),
    ),
]
STARTER_SPECIES = [s for s in SHOP_ITEMS if not s.predator]

FOOD_PACK_SIZE = 20
FOOD_PACK_PRICE = 5

# Treats -- unlike Fish Food (dropped in the water, eaten by whoever gets
# there first), each of these is fed directly to one chosen fish (see the
# Fish Inspector's "Feed a Treat"). Same economy.feed() relief as regular
# food, deliberately no bigger number for feeding one -- these are about
# personality, not a better stat stick. Bought in small packs like Fish
# Food, except Pizza: a single-serving purchase on purpose, so it stays
# the rare, deliberate "it's a special occasion" treat rather than
# something you stock up five at a time. Nobody has Pizza as a declared
# favorite -- every fish is just delighted by it anyway.
FoodItem = namedtuple("FoodItem", "kind emoji price pack_size flavor_text")
TREAT_SHOP_ITEMS = [
    FoodItem("Brine Shrimp", "🦐", 10, 5, "A fish tank classic."),
    FoodItem("Worms", "🪱", 8, 5, "Simple, and they know it."),
    FoodItem("Bloodworms", "🩸", 12, 5, "A little extra excitement at feeding time."),
    FoodItem("Plankton", "🦠", 9, 5, "Barely a mouthful, gone in a second."),
    FoodItem("Pizza", "🍕", 12, 1, "Nobody knows why fish love this so much."),
]

# A fish gets exactly one of these (see random_personality()), not a
# checklist of independent traits:
#   Friendly  -- follows the mouse; when it's out of reach, drifts toward
#                the group (the average position of the other fish) instead.
#   Explorer  -- patrols constantly: changes direction far more often.
#   Shy       -- flees the mouse once it gets close, hiding behind the
#                nearest decoration if one exists.
#   Greedy    -- races to food much faster than everyone else.
#   Lazy      -- slower and changes direction far less often.
#   Playful   -- changes direction often *and* varies its speed wildly each
#                time (bursts of energy), unlike Explorer's steady patrol.
PERSONALITIES = ("Friendly", "Explorer", "Shy", "Greedy", "Lazy", "Playful")

AGE_SECONDS_PER_DAY = (
    60.0 * 4
)  # 4 real minutes = 1 "fish day" -- ages visibly within a sitting

# (stage name, minimum age_days to reach it, sell-value multiplier at that
# stage). A Baby doesn't get its species' real glyph yet -- see BABY_RIGHT/
# BABY_LEFT below -- so growing up is something you can actually *see*, not
# just a number in the Inspector. Elder is the last stage -- see fish.py's
# ELDER_SPEED_MULT usage and aquarium.py's natural-death check
# (_check_natural_deaths()); worth a bit less than Adult, not worthless.
GROWTH_STAGES = (
    ("Baby", 0.0, 0.25),
    ("Juvenile", 1.0, 0.6),
    ("Adult", 3.0, 1.0),
    ("Elder", 10.0, 0.8),
)
BABY_RIGHT, BABY_LEFT = "o>", "<o"

# An Elder fish is measurably slower (stacks with Lazy/cold exactly like
# every other _effective_speed() multiplier). NATURAL_DEATH_CHANCE_PER_DAY
# is checked once per day, per Elder fish -- same rarity as a nightmare
# (constants.DREAM_NIGHTMARE_CHANCE), "notice-worthy, not routine".
ELDER_SPEED_MULT = 0.7
NATURAL_DEATH_CHANCE_PER_DAY = 0.04

MIN_SPEED = 2.5  # cells/second
MAX_SPEED = 6.0
MIN_TURN_DELAY = 1.5  # seconds between random direction changes
MAX_TURN_DELAY = 4.0

EAT_RADIUS = 1.1  # cells -- close enough counts as "reached" the food
FOOD_STEER_RATE = 2.0  # how fast velocity blends toward food, per second
HUNGER_STEP = 1.0  # applied on the deliberately slow hunger clock below
STARVE_HEALTH_LOSS = 2.0  # retains the original starvation edge behavior
HUNGER_RELIEF = 70.0  # one bite usually returns a hungry fish to full
HEALTH_GAIN = 25.0  # feeding quickly reverses a close call
HUNGER_TICK_SECONDS = 3.0  # 5 real minutes from full to starving

AVOID_MARGIN = 3.0  # cells of buffer added beyond a decoration's own radius
AVOID_STEER_RATE = 3.0  # how fast velocity blends away from it, per second

SHY_FLEE_RADIUS = 6.0  # cells -- how close the mouse must get to spook a Shy fish
FLEE_STEER_RATE = (
    4.0  # blend rate while fleeing -- faster/more urgent than normal steering
)
FOLLOW_MOUSE_RATE = 2.0  # blend rate toward the mouse for Friendly
SOCIAL_STEER_RATE = (
    1.0  # gentle blend toward the group, Friendly's fallback with no mouse
)
HEART_RADIUS = (
    4.0  # cells -- shows a heart above a Friendly fish this close to the mouse
)
GREEDY_RATE_MULT = 2.5  # food-steering blend rate multiplier for Greedy
GREEDY_SPEED_MULT = 1.6  # food-chase speed multiplier for Greedy
EXPLORER_TURN_DIV = 2.0  # Explorer changes direction this many times more often
LAZY_TURN_MULT = 2.0  # Lazy changes direction this many times less often
LAZY_SPEED_MULT = 0.55  # Lazy's base speed, applied once at construction
PLAYFUL_TURN_DIV = 2.0  # Playful changes direction as often as Explorer...
PLAYFUL_SPEED_VARIANCE = (0.6, 1.9)  # ...but at a wildly different speed each time

RELAX_CHECK_MIN = 5.0  # seconds between rolls of "does it start relaxing now"
RELAX_CHECK_MAX = 12.0
RELAX_CHANCE = 0.4  # probability of starting a relax episode at each roll
RELAX_DURATION_MIN = 3.0  # seconds spent relaxing, once started
RELAX_DURATION_MAX = 8.0
RELAX_STEER_RATE = 1.5  # blend rate toward the favorite spot while relaxing
# "Arrived" is relative to the spot's own avoid_decorations() influence
# radius (radius + AVOID_MARGIN), not a fixed distance: a fixed one smaller
# than that influence radius would mean a relaxing fish never actually
# arrives -- it'd perpetually fight the every-frame push away from its own
# favorite decoration instead of settling, since that push wins every frame
# once inside its influence. This margin sits just outside it instead.
RELAX_ARRIVE_MARGIN = 1.0  # cells, added on top of a spot's radius + AVOID_MARGIN
IDLE_DAMPING = 0.9  # velocity multiplier per frame once idling at the favorite spot

# Axolotl-specific: real axolotls spend much of their time resting on the
# substrate rather than swimming constantly -- reuses the exact same relax
# mechanic above (favorite_decoration, RELAX_CHECK_MIN/MAX roll cadence),
# just tuned to trigger far more often and hold much longer, so it visibly
# reads as "calmer" than any fish rather than needing a whole new idle
# system. See Fish._glyph() for the resting-glyph swap that goes with it.
AXOLOTL_RELAX_CHANCE = 0.75
AXOLOTL_RELAX_DURATION_MIN = 12.0
AXOLOTL_RELAX_DURATION_MAX = 25.0
AXOLOTL_RESTING_GLYPH = "(-.-)~"  # closed-eyes, shown only while relaxing

# Each decoration's `art` is real (plain-character) ASCII art, not emoji --
# an emoji glyph is drawn by the terminal's own emoji font and mostly ignores
# our Style color, so it can't be shaded/recolored like the rest of this
# library's output. `art` is a list of rows; `colors` is either one color for
# every row or a list matching len(art), for a little per-part shading (e.g.
# the Castle's roofs drawn in a different shade than its stone walls). The
# avoidance radius that makes fish curve around them is tuned via
# AVOID_MARGIN above, independent of how big they're actually drawn.
PLANT_ART = [" )", "( ", " )", "=="]
PLANT_COLORS = ["bright_green", "green", "bright_green", "yellow"]

ROCK_ART = [" ___ ", "/   \\", "\\___/"]
ROCK_COLORS = "bright_black"

CASTLE_ART = [
    " /^\\ /^\\ ",
    " | | | | ",
    "_|_|_|_|_",
    "|       |",
    "|_______|",
]
CASTLE_COLORS = ["yellow", "white", "white", "white", "bright_black"]

DRIFTWOOD_ART = ["~~~~~~", "\\____/"]
DRIFTWOOD_COLORS = ["yellow", "bright_black"]

# The Shop's decoration rows (Phase 3) -- buying one spawns a fresh
# Decoration at a random floor position. The tank's starting furniture is
# also built from this catalog (see main()), so there's exactly one source
# of truth for each kind's art/colors/price/capacity.
#
# `capacity` (Phase 7) is the one number that turns any decoration into a
# "container" fish can sleep inside overnight -- 0 means "not a container",
# same as everything else here (see Decoration.is_container). Giving a
# *future* decoration a home is just picking a capacity, no new class or
# behavior needed.
DecorationItem = namedtuple("DecorationItem", "kind art colors price capacity")
DECORATION_SHOP_ITEMS = [
    DecorationItem("Plant", PLANT_ART, PLANT_COLORS, 10, 0),
    DecorationItem("Driftwood", DRIFTWOOD_ART, DRIFTWOOD_COLORS, 15, 0),
    DecorationItem("Rock", ROCK_ART, ROCK_COLORS, 12, 2),
    DecorationItem("Castle", CASTLE_ART, CASTLE_COLORS, 100, 4),
]
DECORATION_CATALOG = {item.kind: item for item in DECORATION_SHOP_ITEMS}
DECORATION_SELL_MULT = 0.5  # e.g. a $100 Castle sells back for $50

# Fish +5 attractiveness each (rare species +15 instead), decorations by
# kind, and a clean tank (no food left uneaten) -- feeds the Shop's Visitor
# Donations: visitors = attractiveness // 20, each spending a little money.
ATTRACTIVENESS_PER_FISH = 5
ATTRACTIVENESS_PER_RARE_FISH = 15
RARE_PRICE_THRESHOLD = 50  # a fish's Shop price at/above this counts as "rare"
ATTRACTIVENESS_BY_DECORATION = {"Plant": 3, "Driftwood": 4, "Rock": 2, "Castle": 10}
CLEAN_TANK_ATTRACTIVENESS = 10
VISITORS_PER_ATTRACTIVENESS = 20
TICKET_PRICE = 2  # $ per visitor, deterministic
DONATION_PER_VISITOR_MAX = 3  # $ per visitor, randomized 0..this
MAINTENANCE_GRANT = 10  # "Aquarium Maintenance Grant" -- $/day, unconditional

# Emergency Aquarium Welfare (opt-out in Settings): a bankrupt tank
# (money = food = fish = 0) gets exactly this fresh start instead of staying
# empty forever, per the user's own mockup ("+1 Fish +25 Food +$20").
WELFARE_FOOD_GRANT = 25
WELFARE_MONEY_GRANT = 20

# Phase 4/9: relationships. Bonds are earned through interactions (see
# Phase 9's relationship-score system below) rather than rolled at birth --
# a brand new fish (starter, bought, or born) starts with no relationships
# at all, per the "babies start with none, build them naturally" design.
RIVAL_FLEE_RADIUS = 8.0  # cells -- how close a rival must get to spook you
RIVAL_FOOD_BOOST = 1.3  # food-steering speed/rate multiplier once you have a rival
FRIEND_STEER_RATE = 1.2  # gentle blend toward a friend's current position
BREED_CHANCE = (
    0.25  # per eligible (mutual, grown-up, non-predator) friend pair, per day
)
MAX_FISH_FOR_BREEDING = 30  # a sane cap so breeding doesn't run away forever

# Phase 9: continuous relationship scores, replacing the old one-time
# Friend/Rival dice roll. Every *pair* of fish shares exactly one score in
# [RELATIONSHIP_MIN, RELATIONSHIP_MAX] (symmetric -- "how much do these two
# get along" rather than two separate, possibly-divergent opinions), which
# a small number of thresholds turn into a player-facing state. Fish.friend/
# Fish.rival (kept as read-only properties, see relationships.best_bond()/
# worst_bond()) are now *derived* from whichever relationship is strongest/
# weakest, not a fixed pointer set once at birth -- so all of Fish's
# existing friend-following/rival-fleeing/sleep-together/container-priority
# steering keeps working unchanged, just off a score instead of a coin flip.
RELATIONSHIP_MIN = -100.0
RELATIONSHIP_MAX = 100.0
RELATIONSHIP_RIVAL_THRESHOLD = -50.0  # score <= this: 😠 Rival
RELATIONSHIP_DISLIKE_THRESHOLD = -15.0  # score <= this (and > rival): 😒 Dislikes
RELATIONSHIP_FRIEND_THRESHOLD = 15.0  # score >= this (and < best-friend): 🙂 Friend
RELATIONSHIP_BEST_FRIEND_THRESHOLD = 50.0  # score >= this: ❤️ Best Friend
RELATIONSHIP_MEMORY_LIMIT = 5  # reasons remembered per pair, oldest dropped first

# Interaction score deltas -- each one a real, currently-triggerable event
# (see relationships.py's record_*() functions and their call sites):
#   record_wake_up          -- a Friend/Best Friend actually wakes another
#                              up via the morning vignette's "wake" flavor.
#   record_slept_together   -- two fish end up asleep close together (floor)
#                              or sharing a container, checked once at the
#                              Night -> Morning transition.
#   record_gave_up_home     -- a fish wanted a container but there wasn't
#                              room while a nearby/bonded fish got one,
#                              also checked once at that same transition.
#   record_saved_from_shark -- a Shark gets within SHARK_SCARE_RADIUS of a
#                              fish that has a Friend nearby (see
#                              aquarium.py's _check_shark_scares()).
#   record_pushed_from_home -- two already-Disliked-or-worse fish end up
#                              sharing a container overnight anyway (same
#                              Night -> Morning check as record_slept_together,
#                              just the unfriendly counterpart of it).
# A few other interactions from the original design (sharing/stealing food,
# playing, fighting, blocking a doorway, luring a shark at someone) are
# still deliberately NOT wired up -- none of those are real mechanics in
# this game today, and faking the score delta without the underlying
# behavior would be worse than not having it. They're natural follow-ups
# once/if each mechanic exists.
WAKE_UP_SCORE = 4.0
WAKE_UP_SCORE_PLAYFUL = 6.0  # Playful fish get an extra kick out of waking a friend
SLEPT_TOGETHER_SCORE = 1.0
GAVE_UP_HOME_SCORE = 7.0
SAVED_FROM_SHARK_SCORE = 10.0  # a bigger bump -- fear is a strong bonding moment
PUSHED_FROM_HOME_SCORE = -6.0  # negative -- forced proximity sours an already-bad bond

# Shark scares (see aquarium.py's _check_shark_scares(), called every
# per-second tick): any non-predator fish within SHARK_SCARE_RADIUS of a
# Shark counts as scared, once per approach (Fish._shark_scare_active guards
# against re-firing every tick while it lingers nearby). If an existing
# Friend is within SHARK_RESCUE_RADIUS at that moment, credit them with the
# save (record_saved_from_shark) instead of a lonely near-miss.
SHARK_SCARE_RADIUS = 5.0
SHARK_RESCUE_RADIUS = 6.0
# How long a fish that fled into a container to escape a Shark (see
# Fish._hiding_in/_hide_until, aquarium.py's _check_shark_scares()) stays
# tucked away -- invisible and safe from predation, same as sleeping in a
# container overnight -- before it re-emerges on its own.
HIDE_DURATION_SECONDS = 10.0

# Personality reactions to interactions (Step 6): Lazy barely reacts either
# way -- matching its low-effort theme everywhere else in this file --
# while a caring interaction from a Friendly fish means a bit more, since
# Friendly is already this game's "caring" personality (mouse-follow, group
# drift, prioritizing a friend's container over its own favorite spot).
RELATIONSHIP_LAZY_DAMPING = 0.4
RELATIONSHIP_FRIENDLY_BONUS = 1.3  # multiplies a *positive* delta only

# Step 5: unless reinforced, relationships slowly drift back toward 0 --
# friends drift apart, rivals eventually forgive -- checked once a day
# (see main()'s _daily_tick()).
RELATIONSHIP_DECAY_PER_DAY = 1.0

# How close a homeless fish must be to a housed one at the Night -> Morning
# transition to count as "nearby enough that it plausibly wanted that spot
# too" for record_gave_up_home() -- see main()'s _check_night_events().
RELATIONSHIP_NEARBY_RADIUS = 6.0

# Phase 5: world (day/night + water temperature). `fraction` is 0..1 progress
# through the current AGE_SECONDS_PER_DAY-long day -- the same "day" fish age
# by and the daily tick fires on. Night/Morning/Day are discrete, threshold-
# based (for behavior gating and the status readout); water temperature and
# the background tint are both continuous functions of the same fraction
# (see world.day_night_curve()), so the two Phase 5 mechanics stay in sync
# with each other for free instead of needing separately-tuned schedules.
NIGHT_START = 0.75  # fraction of the day at which Night begins
NIGHT_END = 0.15  # fraction of the (next) day at which Night ends
MORNING_END = 0.30  # fraction of the day at which Morning gives way to Day

NIGHT_HUNGER_MULT = 0.4  # sleeping fish get hungry slower

BASE_WATER_TEMP = 23.0  # degrees C, the comfortable midpoint (midday/midnight avg)
WATER_TEMP_SWING = 3.0  # +/- degrees across the day/night cycle
COLD_TEMP_THRESHOLD = 20.5  # below this, fish get sluggish (cold-blooded)
HOT_TEMP_THRESHOLD = 25.5  # above this, fish get stressed (hunger climbs faster)
COLD_SPEED_MULT = 0.6
HOT_HUNGER_MULT = 1.5

NIGHT_BG = (4, 6, 16)  # near-black, deep-water night tint
DAY_BG = (10, 24, 42)  # a lighter, sunlit-water blue

# A fish this hungry refuses to sleep -- it stays up looking for food
# instead of freezing in place while starving (the whole point of a
# hard-stop sleep is cozy realism, not "goes rigid and can't eat").
SLEEP_HUNGER_THRESHOLD = 60.0
SLEEP_STEER_RATE = 1.0  # gentle settling-into-position blend while falling asleep
SLEEP_CLOSE_DISTANCE = 3.0  # cells -- how close friends end up when both asleep
SLEEP_FAR_DISTANCE = (
    30.0  # cells -- rivals keep drifting apart (bounded by the tank) up to this far
)

# Phase 7: sleeping inside a container decoration (a Castle/Cave/etc with
# capacity > 0). A fish claims one per night (see Fish._claim_home()),
# priority: its favorite spot if that's a container with room -> a friend's
# already-claimed container if it has room -> the nearest container with
# room -> the tank floor (today's existing friend-close/rival-far/settle
# behavior, unchanged). HOME_ARRIVE_MARGIN mirrors RELAX_ARRIVE_MARGIN --
# same "just outside the influence radius" reasoning. Personality biases
# this per-fish (see _claim_home()'s docstring for the exact reordering):
# Lazy only bothers with a container already within LAZY_HOME_RADIUS (won't
# travel for one, but won't turn down one that's already close either) --
# otherwise the floor. Shy weights any nearby shelter over sleeping
# specifically with a friend, Friendly weights sleeping with a friend over
# even its own favorite spot, and Explorer occasionally shuffles to a
# different container than its usual pick.
HOME_ARRIVE_MARGIN = 1.0
HOME_STEER_RATE = 1.5
EXPLORER_HOME_SHUFFLE_CHANCE = 0.4
LAZY_HOME_RADIUS = 5.0  # cells -- Lazy only takes a container that's already this close

# A friend pair where one wakes up first (roughly the fraction of nights a
# vignette fires at all, then split ~evenly between the two flavors --
# waking the sleepyhead vs. leaving without them) gets a one-line toast at
# the Night -> Morning transition -- cheap narrative texture, not a new
# simulation of individual wake times. The "wake" flavor also gets a short
# in-tank caption (see vignettes.MorningVignette) -- *boop*, then *awake*,
# right where the two fish actually are.
MORNING_VIGNETTE_CHANCE = 0.35
MORNING_VIGNETTE_FRAME_SECONDS = 1.5

# Sleepy: an independent yes/no trait (not one of the mutually-exclusive
# PERSONALITIES) rolled once at birth alongside the regular personality --
# a fish can be e.g. "Greedy" and Sleepy at once. A Sleepy fish genuinely
# stays asleep past the normal Night->Morning transition (see
# Fish._holding_asleep) until a real wake attempt from an eligible
# tankmate succeeds -- see relationships.roll_wake_threshold() and
# resolve_wake_attempt(). Never permanently stuck: SLEEPY_HOLD_MAX_SECONDS
# is the fallback for when nobody eligible is even there to try.
SLEEPY_CHANCE = 0.2
SLEEPY_RESIST_CHANCE = 0.5  # per-attempt chance a Sleepy fish resists a wake try

# How many failed attempts a Sleepy fish can resist before the *next* one
# succeeds unconditionally, randomized once per holding period from a
# range keyed by the attempting tankmate's relationship tier. Only Friend
# (Friend/Best Friend) and Neutral tiers ever attempt at all -- a Rival or
# a fish that Dislikes the sleeper doesn't bother.
WAKE_CHANCES_FRIEND = (3, 5)
WAKE_CHANCES_NEUTRAL = (4, 6)
WAKE_ATTEMPT_INTERVAL_SECONDS = 4.0  # how often an assigned tankmate retries
SLEEPY_HOLD_MAX_SECONDS = 60.0  # forced wake fallback with no eligible tankmate

# A woken fish doesn't instantly vanish from its container -- it lingers
# here, still tucked in/invisible from the open tank (Fish._entered stays
# True), but shown awake (see Fish._awake_in_home) rather than asleep in
# the Castle Interior view, before it actually leaves.
WAKE_LINGER_SECONDS = 6.0

# How long a wake attempt's "*boop*" replaces the waker's mood emoji in
# the Castle Interior view -- fires for every attempt (resisted or not),
# so a Sleepy fish's several chances all read as real, visible tries.
BOOP_FLASH_SECONDS = 2.0

# Phase 6: polish + stress test. The dev/debug key mass-spawns free starter
# fish up to this many total, to prove the diff-renderer stays smooth with
# a lot of independently-moving widgets at once -- the whole point of this
# example (see the module docstring).
STRESS_TEST_TARGET = 50

# Achievements: account-wide milestones (see save.py's
# load_unlocked_achievements()/store_unlocked_achievements(), stored
# alongside the Cloud Key rather than inside any one aquarium's save file --
# starting a New Aquarium or loading an old save never resets these). Every
# entry hooks an event the game already tracks; see aquarium.py's
# _unlock_achievement() and its call sites. Transparent, not secret -- the
# Achievements menu always shows every name/description, locked or not.
Achievement = namedtuple("Achievement", "id icon name description")
ACHIEVEMENTS = [
    Achievement(
        "first_friend", "🙂", "Made a Friend", "Two fish reached Friend level."
    ),
    Achievement(
        "best_friends", "❤️", "Best Friends", "Two fish reached Best Friend level."
    ),
    Achievement("first_baby", "👶", "It's a Baby!", "Two fish had a baby."),
    Achievement(
        "first_axolotl", "🦎", "Wait, Axolotls?!", "An Axolotl joined your tank."
    ),
    Achievement(
        "full_house",
        "🐠",
        "Full House",
        f"Reached {STRESS_TEST_TARGET} fish in one tank.",
    ),
    Achievement(
        "their_favorite", "💕", "Their Favorite", "Fed a fish its favorite treat."
    ),
    Achievement("mystery_craving", "🍕", "Mystery Craving", "Fed a fish some Pizza."),
    Achievement("first_sale", "💰", "First Sale", "Sold a fish."),
    Achievement(
        "tucked_in", "🏠", "Tucked In", "A fish slept in a container overnight."
    ),
    Achievement("one_week_in", "📅", "One Week In", "Your aquarium reached Day 7."),
    Achievement("backed_up", "☁️", "Backed Up", "Set up Cloud Saves."),
    Achievement(
        "golden_years", "🧓", "Golden Years", "A fish reached its Elder years."
    ),
]

# Random events: one roll per day (see aquarium.py's
# _maybe_trigger_random_event(), called from _daily_tick()), deliberately
# rarer than MORNING_VIGNETTE_CHANCE/BREED_CHANCE above so it reads as a
# genuine surprise rather than routine. Each event reuses existing state
# (Fish.hunger, state["money"], _add_fish()) rather than a new temporary
# buff/debuff system.
RANDOM_EVENT_CHANCE = 0.12
STORM_HUNGER_BUMP = 15.0  # flat, one-time -- not a decaying effect
# A storm is a real, live weather state (environment["storm"], shared with
# every Fish -- see fish.py's draw()), not just a retroactive toast: while
# it's active, every awake fish heads for the nearest container and huddles
# there (see main()'s _end_storm() for how/when it's cleared).
STORM_DURATION_SECONDS = 25.0
LUCKY_FIND_RANGE = (5, 20)  # $ -- a small bonus, not a strategy

# Dreams: rolled once per fish at the Day/Morning -> Night transition (see
# aquarium.py's _assign_dreams()), not every night for every sleeper --
# "ooh, Steve is dreaming tonight" should feel like a notice-worthy
# exception, not the default. DREAM_NIGHTMARE_CHANCE is an independent roll
# on top of category selection (see dreams.choose_dream()), not a fifth
# equally-likely bucket.
DREAM_CHANCE = 0.25  # fraction of tonight's actually-sleeping fish that dream
DREAM_NIGHTMARE_CHANCE = 0.04  # rare, per the user's own "2-5%" ask
DREAM_FRAME_SECONDS = 2.2  # slow, bedtime-story pace between animation frames
# How often a fish's dream lands in its *own* personality-leaned category
# (see dreams.py's _PERSONALITY_CATEGORY) rather than a random other one --
# a lean, not a lock, so e.g. a Greedy fish dreams about food often, not
# every single time.
DREAM_PERSONALITY_CHANCE = 0.6

# Phase 2: memory-linked dreams -- choose_dream() looks at a fish's own
# MEMORY_DREAM_LOOKBACK most recent memory_log entries (see below) before
# falling back to plain personality weighting. A recent shark scare is a
# much better-than-usual (not guaranteed) chance of dreaming about it again
# tonight; a recent memory naming the fish's current friend nudges toward a
# "friendship" dream about that same friend, regardless of personality.
DREAM_SHARK_NIGHTMARE_CHANCE = 0.35
MEMORY_DREAM_LOOKBACK = 3
# A departed tankmate can resurface in a dream for as long as that
# "isn't around anymore" line survives MEMORY_LOG_LIMIT's cap -- grief
# fading as newer memories crowd it out, for free, with no separate decay.
DREAM_REUNION_CHANCE = 0.15

# Nightmare reaction (see aquarium.py's _process_nightmares()): a "bad"
# category dream forces a real, early, solo wake -- unlike every other
# dream, which just sits there quietly until the normal Night -> Morning
# transition. NIGHTMARE_WAKE_DELAY_SECONDS after the dream is assigned, the
# fish wakes up scared (Fish._just_scared_until, the same "flash a mood for
# N seconds" trick BOOP_FLASH_SECONDS already uses); if it has a Friend, it
# then quietly relocates to sleep beside them (joining their claimed
# container if there's room, else just settling close on the floor -- both
# paths reuse Fish.draw()'s existing housing/floor-settle steering
# entirely unchanged, no new movement code) and gets a brief comfort mood
# (Fish._nightmare_comfort_until) once it arrives. No friend: it simply
# settles back to sleep on its own, no relocation.
NIGHTMARE_WAKE_DELAY_SECONDS = 5.0
NIGHTMARE_SCARE_FLASH_SECONDS = 2.5
NIGHTMARE_COMFORT_FLASH_SECONDS = 3.0

# Fish Memory Log: a per-fish diary of real, already-tracked events (see
# aquarium.py's _log_memory()), distinct from Relationship.memories above --
# this is one fish's own history, not a shared pair record. Same
# newest-appended/oldest-dropped shape, just a different cap.
MEMORY_LOG_LIMIT = 10

# Cheat Console (backtick key, see termquarium/console.py): a dev/testing
# tool, not player-facing content -- generous compared to MEMORY_LOG_LIMIT
# since a debugging session can reasonably run many more commands than a
# fish has notable life events.
CONSOLE_LOG_LIMIT = 200

# Ambient bubbles: purely decorative, toggled in Settings. Glyphs are plain
# ASCII/Latin-1 (not emoji) on purpose -- same reasoning as the ASCII-art
# decorations: recolorable via Style, no terminal-emoji-font dependency.
BUBBLE_SPAWN_INTERVAL = (0.4, 1.2)  # seconds between new bubbles, randomized
BUBBLE_SPEED_RANGE = (2.0, 4.0)  # cells/second, rising
BUBBLE_MAX_COUNT = 40  # cap so a long session doesn't accumulate forever
BUBBLE_GLYPHS = ("o", "O", "°")  # small/medium/tiny bubble

# Schooling: fish of the same species drift into loose groups once nothing
# more urgent (fleeing/eating/personality steering/friend-following/
# relaxing) is happening -- a lightweight boids-style blend of cohesion
# (toward the flock's average position), alignment (matching its average
# heading), and separation (a gentle push apart if crowded), scaled to
# SCHOOL_STEER_RATE like every other steering target in this file.
SCHOOL_RADIUS = (
    6.0  # cells -- how far a same-species fish still counts as "in the school"
)
SCHOOL_STEER_RATE = 1.0
SCHOOL_COHESION_WEIGHT = 1.0
SCHOOL_ALIGNMENT_WEIGHT = 0.8
SCHOOL_SEPARATION_WEIGHT = 1.2
SCHOOL_SEPARATION_DISTANCE = (
    1.5  # cells -- push apart once a schoolmate gets this close
)

# Exploration Update, Slice 1: biomes. The Forest is a one-time, whole-tank
# unlock (state["forest_unlocked"]) -- once bought, the player can enter it
# as often as they like (see aquarium.py's _enter_forest()/_leave_forest(),
# a full-screen scene swap, not a modal), independent of whether any fish
# currently happens to be there. Fish decide on their own to forage there
# once hungry -- see Fish.biome/_travel_until/carrying and aquarium.py's
# _check_foraging(), which runs on the same per-second tick regardless of
# which scene is currently shown, so the aquarium (hunger, day/night,
# achievements, dreams, ...) never actually pauses while the player is
# looking at the Forest instead -- only a fish's own visual position does,
# same as an already-housed fish being invisible from the tank view.
FOREST_UNLOCK_PRICE = 700
# Real transit time (not an instant teleport) -- long enough to read as a
# trip, short enough not to feel like a chore.
FOREST_TRAVEL_SECONDS = 8.0
# Rolled once per second per eligible fish once hunger crosses
# HUNGER_WARNING_THRESHOLD -- noticeable within the usual window hunger
# sits above that line, never instant the moment it crosses.
FOREST_TRAVEL_CHANCE_PER_CHECK = 0.05
# Rolled once per second per fish already in the Forest with nothing to
# carry -- faster than the travel-decision roll above, so a fish doesn't
# idle there indefinitely once it's already made the trip.
FOREST_FORAGE_CHANCE_PER_CHECK = 0.15
# A fish can't roll for a successful forage until it's been standing in
# the Forest at least this long -- otherwise FOREST_FORAGE_CHANCE_PER_CHECK
# could succeed on the very first per-second check after arrival, making
# it easy for a player who just clicked "Enter Forest" to never actually
# see the fish there before it's already heading home again.
FOREST_MIN_DWELL_SECONDS = 4.0
# Once a fish has found its wood it lingers this long holding it before
# heading home (see _check_foraging() step 3b) -- so a foraging fish is
# actually *seen* in the Forest with its find rather than vanishing the
# instant it grabs one, and (the point of forage-danger, see
# TIGER_SHARK_* below) is catchable with a log to drop.
FOREST_CARRY_LINGER_SECONDS = 3.0
WOOD_SELL_PRICE = 15
WOOD_SPAWN_CHANCE_PER_CHECK = 0.1  # per second, while under WOOD_MAX_COUNT
WOOD_MAX_COUNT = 5
# Upper bound on the Forest scene's own coordinate space -- the scene is
# actually sized from the live terminal (see ui.py's build_forest_scene(),
# mirroring how the tank's own bounds are derived from app.cols/app.rows),
# so a smaller terminal clamps down from these rather than a fish ever
# being positioned off-screen.
FOREST_WIDTH = 70
FOREST_HEIGHT = 16

# Forest Phase 2 -- personality-flavored forage decisions (see aquarium.py's
# _check_foraging() step 1). Shy never forages on its own (consistent with
# Shy already being the personality that avoids things elsewhere -- it
# hides from the mouse, weighs shelter over company at night); Greedy/
# Explorer are eager, so FOREST_TRAVEL_CHANCE_PER_CHECK is boosted for them
# the same way GREEDY_SPEED_MULT/GREEDY_RATE_MULT already boost other
# Greedy behavior. FOREST_FRIEND_JOIN_CHANCE is a separate, additional
# roll: a Friendly fish whose Friend is already heading to/in the Forest
# can join regardless of its own hunger ("Steve's going, I'll help").
FOREST_SHY_OPT_OUT = True
FOREST_GREEDY_CHANCE_MULT = 3.0
FOREST_EXPLORER_CHANCE_MULT = 2.0
FOREST_FRIEND_JOIN_CHANCE = 0.2

# Ambient falling leaves in the Forest scene (see leaves.py's LeafField) --
# same capped-count/randomized-interval shape as the tank's own BUBBLE_*
# ambient particles, just falling instead of rising.
FOREST_LEAF_SPAWN_INTERVAL = (0.5, 1.5)  # seconds between new leaves
FOREST_LEAF_FALL_SPEED_RANGE = (0.6, 1.4)  # cells/second, falling
FOREST_LEAF_DRIFT_RANGE = (-0.4, 0.4)  # cells/second, horizontal sway
FOREST_LEAF_MAX_COUNT = 12
FOREST_LEAF_GLYPHS = (",", "'", "`", ".")

# Danger while foraging (Exploration Update vision) -- a Tiger Shark can
# prowl into the Forest while fish are there (see aquarium.py's
# _check_forest_danger(), on the same per-second tick as _check_foraging()).
# Unlike the tank's own Shark it never eats: it just sends every foraging
# fish fleeing home (dropping any Wood it was carrying -- "DROP THE LOG!").
# Everyone survives; the intended "...maybe I should buy food" is the
# player's own takeaway, never spelled out by the game.
#
# APPEAR_CHANCE is rolled once per second, only while at least one fish is
# actually in the Forest (it never prowls an empty forest) and no shark is
# already present -- moderate, so foraging stays mostly safe and the event
# reads as an occasional scare rather than a tax on every trip. STAY is how
# long the prowler lingers before leaving; SPEED is how fast it swims across
# (cells/second) -- fast enough to read as a menacing dash.
TIGER_SHARK_APPEAR_CHANCE_PER_CHECK = 0.08
TIGER_SHARK_STAY_SECONDS = 6.0
TIGER_SHARK_SPEED = 11.0
