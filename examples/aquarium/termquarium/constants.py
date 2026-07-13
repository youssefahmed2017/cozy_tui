"""Shared gameplay thresholds and tuning values."""

from collections import namedtuple

# A single tank-level toast is shown when one or more fish cross this level.
# It is intentionally below starvation (100) so the player has time to act.
HUNGER_WARNING_THRESHOLD = 50.0
# name, right-facing glyph, left-facing glyph (hand-mirrored rather than
# auto-flipped so each species still looks recognizable facing the other
# way, not just a reversed string), color, shop price, predator flag.
Species = namedtuple("Species", "name right left color price predator")

SHOP_ITEMS = [
    Species("Goldfish", "><>", "<><", "bright_yellow", 20, False),
    Species("Angelfish", "><(((°>", "<°)))><", "bright_cyan", 40, False),
    Species("Betta", "><{{{°>", "<°}}}><", "bright_red", 55, False),
    Species("Shark", "▶===>", "<===◀", "white", 500, True),
]
STARTER_SPECIES = [s for s in SHOP_ITEMS if not s.predator]

FOOD_PACK_SIZE = 20
FOOD_PACK_PRICE = 5

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
# just a number in the Inspector.
GROWTH_STAGES = (
    ("Baby", 0.0, 0.25),
    ("Juvenile", 1.0, 0.6),
    ("Adult", 3.0, 1.0),
)
BABY_RIGHT, BABY_LEFT = "o>", "<o"

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
# of truth for each kind's art/colors/price.
DecorationItem = namedtuple("DecorationItem", "kind art colors price")
DECORATION_SHOP_ITEMS = [
    DecorationItem("Plant", PLANT_ART, PLANT_COLORS, 10),
    DecorationItem("Driftwood", DRIFTWOOD_ART, DRIFTWOOD_COLORS, 15),
    DecorationItem("Rock", ROCK_ART, ROCK_COLORS, 12),
    DecorationItem("Castle", CASTLE_ART, CASTLE_COLORS, 100),
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

# Phase 4: relationships. Rolled once, when a fish is introduced to the tank
# (mutually exclusive -- a brand new bond is either a Friend or a Rival, never
# both at once, though a fish can pick up the *other* kind later from a
# different fish's own roll -- see form_relationship()).
FRIEND_CHANCE = 0.3
RIVAL_CHANCE = 0.2
RIVAL_FLEE_RADIUS = 8.0  # cells -- how close a rival must get to spook you
RIVAL_FOOD_BOOST = 1.3  # food-steering speed/rate multiplier once you have a rival
FRIEND_STEER_RATE = 1.2  # gentle blend toward a friend's current position
BREED_CHANCE = (
    0.25  # per eligible (mutual, grown-up, non-predator) friend pair, per day
)
MAX_FISH_FOR_BREEDING = 30  # a sane cap so breeding doesn't run away forever

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

# Phase 6: polish + stress test. The dev/debug key mass-spawns free starter
# fish up to this many total, to prove the diff-renderer stays smooth with
# a lot of independently-moving widgets at once -- the whole point of this
# example (see the module docstring).
STRESS_TEST_TARGET = 50

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
SCHOOL_RADIUS = 6.0  # cells -- how far a same-species fish still counts as "in the school"
SCHOOL_STEER_RATE = 1.0
SCHOOL_COHESION_WEIGHT = 1.0
SCHOOL_ALIGNMENT_WEIGHT = 0.8
SCHOOL_SEPARATION_WEIGHT = 1.2
SCHOOL_SEPARATION_DISTANCE = 1.5  # cells -- push apart once a schoolmate gets this close
