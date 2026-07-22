"""Personality, Sleepy, breeding, and the relationship-score system --
how a fish's traits and social ties get decided and evolve over its life.

Relationships (Phase 9) replace the old one-time Friend/Rival dice roll:
every *pair* of fish shares exactly one continuous score, nudged by real
interactions (see the record_*() functions), decaying slowly toward 0 if
left alone (decay_relationships()), and never shown to the player as a raw
number -- only as a state (relationship_state()) plus a short list of why
(Relationship.memories). Fish.friend/Fish.rival stay as read-only
properties on Fish (see fish.py), derived from whichever relationship is
currently strongest/weakest (best_bond()/worst_bond()) -- every existing
piece of steering that already reads .friend/.rival keeps working exactly
as before, now driven by an earned score instead of a coin flip."""

import random

from .constants import (
    MORNING_VIGNETTE_CHANCE,
    PERSONALITIES,
    RELATIONSHIP_BEST_FRIEND_THRESHOLD,
    RELATIONSHIP_DECAY_PER_DAY,
    RELATIONSHIP_DISLIKE_THRESHOLD,
    RELATIONSHIP_FRIEND_THRESHOLD,
    RELATIONSHIP_FRIENDLY_BONUS,
    RELATIONSHIP_LAZY_DAMPING,
    RELATIONSHIP_MAX,
    RELATIONSHIP_MEMORY_LIMIT,
    RELATIONSHIP_MIN,
    RELATIONSHIP_RIVAL_THRESHOLD,
    SLEEPY_CHANCE,
    SLEEPY_RESIST_CHANCE,
    SLEPT_TOGETHER_SCORE,
    WAKE_CHANCES_FRIEND,
    WAKE_CHANCES_NEUTRAL,
    WAKE_UP_SCORE,
    WAKE_UP_SCORE_PLAYFUL,
    GAVE_UP_HOME_SCORE,
    SAVED_FROM_SHARK_SCORE,
    PUSHED_FROM_HOME_SCORE,
)


def random_personality() -> str:
    """Roll one of PERSONALITIES for a new fish, uniformly."""
    return random.choice(PERSONALITIES)


def roll_is_sleepy() -> bool:
    """Whether a new fish is also Sleepy -- independent of (and stackable
    with) its regular personality, e.g. a Greedy fish can also be Sleepy.
    Affects only how hard it is to wake (see find_eligible_waker()/
    resolve_wake_attempt()); nothing else about it changes."""
    return random.random() < SLEEPY_CHANCE


def find_eligible_waker(sleeper, candidates):
    """Among `candidates` (a Sleepy sleeper's same-container tankmates),
    the one best placed to attempt waking it -- Friend/Best Friend or
    Neutral tier only, picking the strongest bond if more than one
    qualifies. A Rival or a fish that Dislikes the sleeper never attempts
    at all; it wouldn't bother. Returns (waker, tier) where tier is
    "Friend" or "Neutral", or (None, None) if nobody here is willing."""
    best, best_score = None, None
    for other in candidates:
        if other is sleeper:
            continue
        score = get_relationship(sleeper, other).score
        if score <= RELATIONSHIP_DISLIKE_THRESHOLD:
            continue
        if best is None or score > best_score:
            best, best_score = other, score
    if best is None:
        return None, None
    tier = "Friend" if best_score >= RELATIONSHIP_FRIEND_THRESHOLD else "Neutral"
    return best, tier


def roll_wake_threshold(tier: str) -> int:
    """How many failed attempts a Sleepy fish can resist from this tier of
    tankmate before the next attempt always succeeds -- rolled once per
    holding period, not per attempt."""
    lo, hi = WAKE_CHANCES_FRIEND if tier == "Friend" else WAKE_CHANCES_NEUTRAL
    return random.randint(lo, hi)


def resolve_wake_attempt(attempts_used: int, threshold: int) -> bool:
    """One wake attempt against a Sleepy fish: True if it succeeds. Once
    `attempts_used` has reached `threshold`, success is unconditional --
    the whole point of a threshold is that waking one up is never
    permanently impossible, just harder for some tiers than others."""
    if attempts_used >= threshold:
        return True
    return random.random() >= SLEEPY_RESIST_CHANCE


class Relationship:
    """The one shared record for a pair of fish: a continuous score and a
    short, bounded memory log of *why* (newest last). Never shown to the
    player as a raw number -- see relationship_state()."""

    __slots__ = ("score", "memories")

    def __init__(self, score: float = 0.0):
        self.score = score
        self.memories: list[str] = []


def get_relationship(a, b) -> Relationship:
    """The shared Relationship between `a` and `b`, creating a fresh
    (Neutral, no memories) one on first contact. The *same* object is
    stored on both fish's `.relationships` dicts, so updating it through
    either side keeps them in sync automatically -- there's only ever one
    score per pair, not two independently-drifting opinions."""
    rel = a.relationships.get(b)
    if rel is None:
        rel = Relationship()
        a.relationships[b] = rel
        b.relationships[a] = rel
    return rel


def set_relationship(a, b, score: float, reason: str | None = None) -> Relationship:
    """Directly set the shared score between two fish, clamped to
    [RELATIONSHIP_MIN, RELATIONSHIP_MAX] -- the explicit escape hatch
    tests and save/load use instead of the old `f.friend = mate` pattern,
    since `.friend`/`.rival` are now read-only, score-derived views."""
    rel = get_relationship(a, b)
    rel.score = max(RELATIONSHIP_MIN, min(RELATIONSHIP_MAX, score))
    if reason:
        rel.memories.append(reason)
        del rel.memories[:-RELATIONSHIP_MEMORY_LIMIT]
    return rel


def relationship_state(score: float) -> tuple[str, str]:
    """(label, emoji) for a raw score -- the only thing the player ever
    sees (Step 8): never the number itself."""
    if score <= RELATIONSHIP_RIVAL_THRESHOLD:
        return "Rival", "😠"
    if score <= RELATIONSHIP_DISLIKE_THRESHOLD:
        return "Dislikes", "😒"
    if score < RELATIONSHIP_FRIEND_THRESHOLD:
        return "Neutral", "😐"
    if score < RELATIONSHIP_BEST_FRIEND_THRESHOLD:
        return "Friend", "🙂"
    return "Best Friend", "❤️"


def best_bond(fish):
    """The other fish `fish` gets along with best, if that's at least
    Friend-level, else None -- what Fish.friend reads."""
    candidates = [
        (other, rel.score)
        for other, rel in fish.relationships.items()
        if rel.score >= RELATIONSHIP_FRIEND_THRESHOLD
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda pair: pair[1])[0]


def worst_bond(fish):
    """The other fish `fish` gets along with least, if that's Rival-level,
    else None -- what Fish.rival reads."""
    candidates = [
        (other, rel.score)
        for other, rel in fish.relationships.items()
        if rel.score <= RELATIONSHIP_RIVAL_THRESHOLD
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda pair: pair[1])[0]


def remember(
    a, b, delta: float, reason: str, *, dampen_if_lazy: bool = True
) -> Relationship:
    """Apply one interaction's score delta to the shared relationship
    between `a` and `b` (creating it if needed), clamped to
    [RELATIONSHIP_MIN, RELATIONSHIP_MAX], and append `reason` to their
    shared memory log (oldest dropped once it exceeds
    RELATIONSHIP_MEMORY_LIMIT). Either fish being Lazy dampens the delta
    toward 0 (Step 6: Lazy rarely helps, rarely hurts, mostly neutral)
    unless dampen_if_lazy=False."""
    if dampen_if_lazy and (a.personality == "Lazy" or b.personality == "Lazy"):
        delta *= RELATIONSHIP_LAZY_DAMPING
    rel = get_relationship(a, b)
    rel.score = max(RELATIONSHIP_MIN, min(RELATIONSHIP_MAX, rel.score + delta))
    rel.memories.append(reason)
    del rel.memories[:-RELATIONSHIP_MEMORY_LIMIT]
    return rel


def record_wake_up(waker, sleeper) -> None:
    """A Friend/Best Friend actually wakes another up (the morning
    vignette's "wake" flavor -- see choose_morning_vignette()). Playful
    fish get an extra kick out of it (Step 6)."""
    delta = WAKE_UP_SCORE_PLAYFUL if waker.personality == "Playful" else WAKE_UP_SCORE
    remember(
        waker, sleeper, delta, f"{waker.display_name} woke {sleeper.display_name} up"
    )


def record_slept_together(a, b) -> None:
    """Two fish end up asleep close together (floor) or sharing a
    container for the night -- checked once at the Night -> Morning
    transition (see main()'s _check_night_events())."""
    remember(a, b, SLEPT_TOGETHER_SCORE, "Slept together for the night")


def record_gave_up_home(generous, beneficiary) -> None:
    """`generous` wanted a container but there wasn't room while
    `beneficiary` (a nearby or bonded tankmate) got the spot -- checked
    once at the same Night -> Morning transition as record_slept_together().
    A Friendly fish's generosity means a bit more (Step 6)."""
    delta = GAVE_UP_HOME_SCORE
    if generous.personality == "Friendly":
        delta *= RELATIONSHIP_FRIENDLY_BONUS
    remember(
        beneficiary,
        generous,
        delta,
        f"{generous.display_name} slept on the floor so "
        f"{beneficiary.display_name} could have the spot",
    )


def record_saved_from_shark(rescuer, saved) -> None:
    """A Shark got within SHARK_SCARE_RADIUS of `saved`, and `rescuer` (an
    existing Friend) was within SHARK_RESCUE_RADIUS at that moment -- see
    aquarium.py's _check_shark_scares(). A bigger bump than the other
    interactions here: real fear shared together is a strong bonding
    moment, not a mild pleasantry like sleeping nearby."""
    remember(
        saved,
        rescuer,
        SAVED_FROM_SHARK_SCORE,
        f"{rescuer.display_name} saved {saved.display_name} from a shark",
    )


def record_pushed_from_home(pusher, pushed) -> None:
    """Two fish who already Dislike each other or worse end up sharing a
    container overnight anyway (see aquarium.py's _check_night_events()) --
    the unfriendly counterpart to record_slept_together(): forced proximity
    sours an already-bad bond instead of warming a neutral one."""
    remember(
        pushed,
        pusher,
        PUSHED_FROM_HOME_SCORE,
        f"{pusher.display_name} pushed {pushed.display_name} out of their shared home",
    )


def decay_relationships(fish_list) -> None:
    """Nudge every relationship a little back toward Neutral (Step 5) --
    friends drift apart, rivals eventually forgive, unless reinforced by
    new interactions. Called once a day (see main()'s _daily_tick())."""
    for a, b, rel in all_relationship_pairs(fish_list):
        if rel.score > 0:
            rel.score = max(0.0, rel.score - RELATIONSHIP_DECAY_PER_DAY)
        elif rel.score < 0:
            rel.score = min(0.0, rel.score + RELATIONSHIP_DECAY_PER_DAY)


def clear_relationships(removed, fish_list) -> None:
    """Called whenever a fish leaves the tank (sold, starved, eaten) so no
    survivor is left steering toward/fleeing a ghost -- the same care
    already taken for a sold favorite Decoration. Drops the relationship
    entirely rather than leaving a stale, unreachable entry behind."""
    for f in fish_list:
        f.relationships.pop(removed, None)


def all_relationship_pairs(fish_list):
    """Every (fish_a, fish_b, Relationship) triple that currently exists,
    each pair returned exactly once regardless of iteration order."""
    seen = set()
    pairs = []
    for f in fish_list:
        for other, rel in f.relationships.items():
            key = frozenset((id(f), id(other)))
            if key in seen:
                continue
            seen.add(key)
            pairs.append((f, other, rel))
    return pairs


def find_breeding_pairs(fish_list):
    """Friend-or-better pairs where both fish are grown-up (Adult) and not
    predators -- each pair returned exactly once. Doesn't roll BREED_CHANCE
    itself; the caller (main()'s daily tick) decides whether each pair
    actually has a baby this time."""
    pairs = []
    for a, b, rel in all_relationship_pairs(fish_list):
        if (
            rel.score < RELATIONSHIP_FRIEND_THRESHOLD
            or a.is_predator
            or b.is_predator
            or a.growth_stage != "Adult"
            or b.growth_stage != "Adult"
        ):
            continue
        pairs.append((a, b))
    return pairs


def choose_baby_species_name(parent_a, parent_b) -> str:
    """A baby inherits one parent's species, chosen at random."""
    return random.choice([parent_a.species_name, parent_b.species_name])


def find_mutual_friend_pairs(fish_list):
    """Every Friend-or-better pair, each returned exactly once --
    find_breeding_pairs()'s pairing logic, minus the Adult/non-predator
    breeding-eligibility filters, for anything (like the morning vignette)
    that cares about the bond itself, not whether it's old enough to
    breed."""
    return [
        (a, b)
        for a, b, rel in all_relationship_pairs(fish_list)
        if rel.score >= RELATIONSHIP_FRIEND_THRESHOLD
    ]


def choose_morning_vignette(friend_pairs, chance: float = MORNING_VIGNETTE_CHANCE):
    """Pick one Friend pair and a flavor for a lighthearted Night -> Morning
    toast, or None (no vignette this morning, or no eligible pairs at all).

    Every fish already wakes up together, mechanically, the instant Night
    ends (see Fish.draw()'s `sleeping` check) -- there's no per-fish wake
    timer to actually query here. This is cheap narrative texture on top of
    that: "waker"/"sleeper" are just which friend the two flavor templates
    put in each role, not a real difference in behavior -- except Sleepy
    (see roll_is_sleepy()): a Sleepy sleeper practically never gets the
    "wake" flavor, resisting the boop outright almost every time instead
    (occasionally still resolving as the waker just leaving, same as a
    non-Sleepy sleeper can). A genuine "wake" outcome also records a real
    relationship-score bump (see main()'s call to record_wake_up()).
    Returns (waker, sleeper, flavor) where flavor is "wake", "resist", or
    "leave"."""
    if not friend_pairs or random.random() >= chance:
        return None
    a, b = random.choice(friend_pairs)
    waker, sleeper = random.sample([a, b], 2)
    if getattr(sleeper, "is_sleepy", False):
        flavor = "resist" if random.random() < SLEEPY_RESIST_CHANCE else "leave"
    else:
        flavor = "wake" if random.random() < 0.5 else "leave"
    return waker, sleeper, flavor
