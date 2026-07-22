"""The Dream System: sleeping fish occasionally dream, shown as a 💭
indicator (see fish.py's `sleeping` draw branch and inspectors.py's Castle
Interior) and, on click, a small read-only animated view (see
ui.build_dream_view()). Personality biases which *category* of dream a fish
gets (see choose_dream()) -- purely cosmetic texture, matching the
"personality, not optimization" thread already running through
Treats/Axolotl/Achievements/Random Events.

Phase 2: memory-linked dream selection. choose_dream() reads `f`'s own
memory_log (aquarium.py's _log_memory()) before falling back to plain
personality weighting -- a recent shark scare is a much-better-than-usual
chance of dreaming about it again tonight, a recent memory naming the
fish's current friend nudges toward a "friendship" dream about that same
friend, and a fish that once logged a tankmate's departure can, for as
long as that memory survives the log's cap, occasionally dream the
departed friend came back."""

import random
import re
import time
from collections import namedtuple

from cozy_tui.widget import Widget

from .constants import (
    DREAM_FRAME_SECONDS,
    DREAM_NIGHTMARE_CHANCE,
    DREAM_PERSONALITY_CHANCE,
    DREAM_REUNION_CHANCE,
    DREAM_SHARK_NIGHTMARE_CHANCE,
    MEMORY_DREAM_LOOKBACK,
)

Dream = namedtuple("Dream", "category icon title description frames")

# A single variant within a category: `frames` is a fish's whole dream
# tonight (chosen at random from its category, see choose_dream()) -- a
# short tuple of frames, each a tuple of rows building one small *visual*
# scene (not a caption to read) -- emoji carry real color straight from the
# terminal's own emoji font regardless of our Style (the same reason
# Decoration art in constants.py is plain ASCII, not emoji: emoji ignore our
# recoloring, which here is exactly what makes 🔴🟠🟡🟢🔵🟣/🌈 read as actual
# color instead of a Style this library would have to fake). Consecutive
# frames nudge the same scene slightly (a fish drifting, a shark closing in)
# rather than jumping to an unrelated picture. `title`/`description` are the
# plain-language caption build_dream_view() prints below the animation --
# not everyone reads "🌈🌈🌈🌈🌈 / 🔴🟠🟡🟢🔵🟣" as "a rainbow ocean" on sight,
# so this is a clue, not a replacement for the visual. "{friend}" in either
# field or in `frames` is substituted by choose_dream() only for the
# "friendship" category.
DreamVariant = namedtuple("DreamVariant", "title description frames")

DREAM_FRAMES = {
    "happy": [
        DreamVariant(
            "A Snowy Hill",
            "Sledding down on a shell, having the time of its life.",
            (
                ("❄️  ❄️  ❄️  ❄️  ❄️", "    🐠🛷", "▔▔▔▔▔▔▔▔▔▔▔▔▔▔"),
                ("❄️  ❄️  ❄️  ❄️  ❄️", "        🐠🛷", "▔▔▔▔▔▔▔▔▔▔▔▔▔▔"),
            ),
        ),
        DreamVariant(
            "A Vast Coral Reef",
            "Swimming through every color of the reef.",
            (
                ("🌊🌊🌊🌊🌊🌊🌊", "🐠 🪸 🐡 🪸 🐟", "🪸 🪸 🪸 🪸 🪸"),
                ("🌊🌊🌊🌊🌊🌊🌊", "🪸 🐠 🪸 🐟 🪸", "🪸 🪸 🪸 🪸 🪸"),
            ),
        ),
        DreamVariant(
            "A Floating Island",
            "Just... floating there, peacefully.",
            (
                ("  ☁️        ☁️", "   🏝️🌴", "🌊🌊🌊🌊🌊🌊🌊"),
                ("      ☁️      ☁️", "   🏝️🌴", "🌊🌊🌊🌊🌊🌊🌊"),
            ),
        ),
        DreamVariant(
            "Endless Bubbles",
            "Floating up through bubbles that never stop.",
            (
                ("🌊🌊🌊🌊🌊🌊🌊", "  o  O  o  °", "    🐠"),
                ("🌊🌊🌊🌊🌊🌊🌊", "    o  O  o", "      🐠"),
            ),
        ),
        DreamVariant(
            "A Sunlit Anemone Garden",
            "Swaying anemones in the warm afternoon light.",
            (
                ("☀️", "🌸 🪸 🌸 🪸 🌸", "  🐠"),
                ("☀️", "🪸 🌸 🪸 🌸 🪸", "    🐠"),
            ),
        ),
        DreamVariant(
            "Racing the Waves",
            "Riding the crest of every wave, again and again.",
            (
                ("🌊    🌊    🌊", "  🐠", "〰️〰️〰️〰️〰️〰️"),
                ("🌊    🌊    🌊", "      🐠", "〰️〰️〰️〰️〰️〰️"),
            ),
        ),
    ],
    "food": [
        DreamVariant(
            "An Endless Worm Buffet",
            "As many worms as it could ever want.",
            (
                ("🪱  🪱  🪱  🪱", "    🐠", "🌊🌊🌊🌊🌊🌊"),
                ("  🪱  🪱  🪱", "   😋🐠", "🌊🌊🌊🌊🌊🌊"),
            ),
        ),
        DreamVariant(
            "A Shrimp Feast",
            "Shrimp. So much shrimp.",
            (
                ("🦐    🦐    🦐", "    🐠", "🌊🌊🌊🌊🌊🌊"),
                ("🦐    🦐    🦐", "      🐠", "🌊🌊🌊🌊🌊🌊"),
            ),
        ),
        DreamVariant(
            "A Mountain of Bloodworms",
            "A whole mountain, and it's all just for it.",
            (
                ("🩸🩸🩸🩸🩸", "  🩸🩸🩸", "    🐠"),
                ("🩸🩸🩸🩸🩸", "  🩸🩸🩸", "   😋🐠"),
            ),
        ),
        DreamVariant(
            "The Pizza That Never Ends",
            "Slice after slice after slice.",
            (
                ("🍕🍕🍕🍕🍕", "    🐠", "🌊🌊🌊🌊🌊🌊"),
                ("🍕🍕🍕🍕🍕", "   😋🐠", "🌊🌊🌊🌊🌊🌊"),
            ),
        ),
        DreamVariant(
            "A Plankton Cloud",
            "Barely a mouthful each, but there's no end to them.",
            (
                ("🦠 🦠 🦠 🦠 🦠", "    🐠", "🌊🌊🌊🌊🌊🌊"),
                (" 🦠 🦠 🦠 🦠 🦠", "      🐠", "🌊🌊🌊🌊🌊🌊"),
            ),
        ),
    ],
    "friendship": [
        DreamVariant(
            "A Snowy Mountain, Together",
            "Sharing ice cream with {friend}.",
            (
                ("🏔️  ❄️  ❄️  🏔️", "   🐠   🐡", "      🍧", "with {friend}"),
                ("🏔️  ❄️  ❄️  🏔️", "    🐠🐡", "      🍧", "with {friend}"),
            ),
        ),
        DreamVariant(
            "Side by Side",
            "Just swimming along with {friend}.",
            (
                ("🌊   🐠🐡   🌊", "  side by side", "with {friend}"),
                ("🌊    🐠🐡  🌊", "  side by side", "with {friend}"),
            ),
        ),
        DreamVariant(
            "Racing Bubbles Together",
            "Chasing bubbles to the surface with {friend}.",
            (
                ("o   O   o", "🐠🐡", "with {friend}"),
                ("  o   O   o", " 🐠🐡", "with {friend}"),
            ),
        ),
        DreamVariant(
            "Sharing the Favorite Spot",
            "Just the two of them, and their favorite spot.",
            (
                ("🪨", "🐠🐡 zzz", "with {friend}"),
                ("🪨✨", "🐠🐡 zzz", "with {friend}"),
            ),
        ),
    ],
    "home": [
        DreamVariant(
            "A Much Bigger Castle",
            "Room for everyone, and then some.",
            (("🏰🏰🏰", "🌊🌊🌊🌊🌊"), ("🏰🏰🏰✨", "🌊🌊🌊🌊🌊")),
        ),
        DreamVariant(
            "The Coziest Little Rock",
            "Perfectly warm, perfectly quiet.",
            (("🪨", "🐠 zzz"), ("🪨✨", "🐠 zzz")),
        ),
        DreamVariant(
            "A Brand New Plant Forest",
            "Swimming and exploring the forest.",
            (
                ("🌲  🌲  🌲", "🌲 🐠 🌲"),
                (" 🌲  🌲  🌲", "🌲 🐠  🌲"),
            ),
        ),
        DreamVariant(
            "The Warmest Corner",
            "Doesn't need to be big. Just warm.",
            (("🏠", "🐠 zzz"), ("🏠✨", "🐠 zzz")),
        ),
    ],
    "fantasy": [
        DreamVariant(
            "Clouds, a Castle, and the Moon",
            "None of it makes any sense. It doesn't have to.",
            (
                ("☁️      🌙", "   🏰", "🐠  ✨"),
                ("   ☁️   🌙", "   🏰", "  🐠✨"),
            ),
        ),
        DreamVariant(
            "A Rainbow Ocean",
            "Swimming through a kaleidoscope of color.",
            (
                ("🌈🌈🌈🌈🌈", "🔴🟠🟡🟢🔵🟣", "🌊🌊🌊🌊🌊🌊"),
                ("🌈🌈🌈🌈🌈", "🔴🐠🟡🟢🐟🟣", "🌊🌊🌊🌊🌊🌊"),
            ),
        ),
        DreamVariant(
            "Swimming Among the Stars",
            "Somehow, the water became the night sky.",
            (
                ("✨  ⭐  ✨", "  🐠", "⭐  ✨  ⭐"),
                ("⭐  ✨  ⭐", "    🐠", "✨  ⭐  ✨"),
            ),
        ),
        DreamVariant(
            "An Upside-Down Ocean",
            "The waves are on the ceiling. That's fine.",
            (
                ("🌊🌊🌊🌊🌊🌊🌊", "  🐠", "☁️     ☁️"),
                ("🌊🌊🌊🌊🌊🌊🌊", "    🐠", "  ☁️     ☁️"),
            ),
        ),
    ],
    "bad": [
        DreamVariant(
            "A Shark in the Dark Water",
            "Getting closer. Too close.",
            (("🦈", "     🐠", "🌊🌊🌊🌊🌊🌊"), ("   🦈", "  🐠", "🌊🌊🌊🌊🌊🌊")),
        ),
        DreamVariant(
            "Lost in the Dark",
            "Which way is up?",
            (
                ("⬛⬛⬛⬛⬛", "   🐠", "⬛⬛⬛⬛⬛"),
                ("⬛⬛⬛⬛⬛", "     🐠", "⬛⬛⬛⬛⬛"),
            ),
        ),
        DreamVariant(
            "Caught in a Net",
            "Struggling. Getting nowhere.",
            (
                ("▦▦▦▦▦", " 🐠", "▦▦▦▦▦"),
                ("▦▦▦▦▦", "🐠", "▦▦▦▦▦"),
            ),
        ),
        DreamVariant(
            "The Water Turned to Ice",
            "Can't move. Can't breathe right.",
            (
                ("❄️❄️❄️❄️❄️", "  🐠", "❄️❄️❄️❄️❄️"),
                ("❄️❄️❄️❄️❄️", " 🐠", "❄️❄️❄️❄️❄️"),
            ),
        ),
    ],
    # Only ever reached through the memory-linked check in choose_dream() --
    # never a personality's plain default (see _PERSONALITY_CATEGORY, which
    # deliberately has no "reunion" entry) -- a fish doesn't "prefer" grief
    # dreams, it only has one because it actually lost someone.
    "reunion": [
        DreamVariant(
            "{name} Coming Back",
            "I woke up smiling. Then I remembered.",
            (
                ("🐠   🐡", "  side by side again"),
                ("🐠", "   (just a dream)"),
            ),
        ),
        DreamVariant(
            "One More Day with {name}",
            "It felt so real. Then it didn't.",
            (
                ("🌊  🐠🐡  🌊", "   one more day"),
                ("🌊    🐠  🌊", "   (just a dream)"),
            ),
        ),
    ],
}

_CATEGORY_ICON = {
    "happy": "😊",
    "food": "🍕",
    "friendship": "❤️",
    "home": "🏠",
    "fantasy": "🌌",
    "bad": "😨",
    "reunion": "🥹",
}

# Matches aquarium.py's _log_departure() line format exactly
# (f"{departed.display_name} isn't around anymore.", after the "[Day N] "
# prefix _log_memory() adds) -- string-matching against the memory log is
# the same lightweight "memory-linked" technique the shark/friendship
# checks below use, not a separate structured event log.
_DEPARTURE_RE = re.compile(r"^\[Day \d+\] (.+) isn't around anymore\.$")


def _departed_friend_name(memory_log):
    """The most recently logged departed tankmate's name still present in
    `memory_log`, or None -- naturally stops being findable once
    MEMORY_LOG_LIMIT pushes that entry out, so grief fades on its own."""
    for entry in reversed(memory_log):
        match = _DEPARTURE_RE.match(entry)
        if match:
            return match.group(1)
    return None


# Which category each of the game's *actual* PERSONALITIES (constants.py)
# leans toward -- there's no "Curious"/"Brave" personality in this game, so
# these map onto the six that really exist (Friendly/Explorer/Shy/Greedy/
# Lazy/Playful) rather than the pitch's own trait names. A *lean*, not a
# lock: choose_dream() only picks this category DREAM_PERSONALITY_CHANCE of
# the time, spreading the rest across the other non-nightmare categories --
# a Greedy fish should dream about food *often*, not exclusively.
_PERSONALITY_CATEGORY = {
    "Explorer": "fantasy",
    "Greedy": "food",
    "Shy": "home",
    "Friendly": "friendship",
    "Lazy": "happy",
    "Playful": "happy",
}
_ALL_CATEGORIES = ("happy", "food", "friendship", "home", "fantasy")


def _build_dream(category: str, variant: DreamVariant, **format_kwargs) -> Dream:
    title = variant.title.format(**format_kwargs) if format_kwargs else variant.title
    description = (
        variant.description.format(**format_kwargs)
        if format_kwargs
        else variant.description
    )
    frames = variant.frames
    if format_kwargs:
        frames = tuple(
            tuple(line.format(**format_kwargs) for line in frame) for frame in frames
        )
    return Dream(category, _CATEGORY_ICON[category], title, description, frames)


def make_dream(f, category: str = "happy") -> Dream:
    """Build a Dream of an explicit `category` for `f` -- the deterministic
    counterpart to choose_dream()'s weighted roll, used by the cheat
    console's give_dream/give_nightmare. Handles the variants that need a
    name (friendship/reunion), falling back gracefully when there's nobody
    to name. Raises ValueError for an unknown category."""
    if category not in DREAM_FRAMES:
        valid = ", ".join(sorted(DREAM_FRAMES))
        raise ValueError(f"Unknown dream category {category!r}. Try one of: {valid}.")
    if category == "friendship" and f.friend is None:
        category = "happy"  # nobody to dream about -- same fallback as choose_dream()
    variant = random.choice(DREAM_FRAMES[category])
    if category == "friendship":
        return _build_dream(category, variant, friend=f.friend.display_name)
    if category == "reunion":
        name = _departed_friend_name(f.memory_log) or "an old friend"
        return _build_dream(category, variant, name=name)
    return _build_dream(category, variant)


def choose_dream(f) -> Dream:
    """Pick tonight's dream for `f`. Checked in order, each independent of
    the ones below it:

    1. A "reunion" dream about a still-remembered departed tankmate
       (DREAM_REUNION_CHANCE) -- see _departed_friend_name().
    2. A shark-specific nightmare (DREAM_SHARK_NIGHTMARE_CHANCE, well above
       the plain nightmare rate below) if a recent memory mentions one --
       see MEMORY_DREAM_LOOKBACK.
    3. A rare, flat, personality-independent plain nightmare
       (DREAM_NIGHTMARE_CHANCE).
    4. Otherwise, a personality-weighted category (falling back to "happy"
       for Friendly with no current friend to dream about) -- nudged toward
       "friendship" instead, regardless of personality, if a recent memory
       already names the current friend.
    """
    recent = f.memory_log[-MEMORY_DREAM_LOOKBACK:]

    departed_name = _departed_friend_name(f.memory_log)
    if departed_name is not None and random.random() < DREAM_REUNION_CHANCE:
        variant = random.choice(DREAM_FRAMES["reunion"])
        return _build_dream("reunion", variant, name=departed_name)

    had_shark_scare = any("shark" in entry.lower() for entry in recent)
    if had_shark_scare and random.random() < DREAM_SHARK_NIGHTMARE_CHANCE:
        variant = next(
            v for v in DREAM_FRAMES["bad"] if v.title == "A Shark in the Dark Water"
        )
        return _build_dream("bad", variant)

    if random.random() < DREAM_NIGHTMARE_CHANCE:
        category = "bad"
    else:
        preferred = _PERSONALITY_CATEGORY.get(f.personality, "happy")
        if random.random() < DREAM_PERSONALITY_CHANCE:
            category = preferred
        else:
            # A lean, not a lock -- spread the rest across the other
            # categories so e.g. a Greedy fish doesn't dream about food
            # literally every single night.
            category = random.choice([c for c in _ALL_CATEGORIES if c != preferred])
        if category == "friendship" and f.friend is None:
            category = "happy"
        elif (
            category != "friendship"
            and f.friend is not None
            and any(f.friend.display_name in entry for entry in recent)
        ):
            # A recent memory already involves the current friend -- real
            # experience gets a say alongside plain personality weighting.
            category = "friendship"

    variant = random.choice(DREAM_FRAMES[category])
    if category == "friendship":
        return _build_dream(category, variant, friend=f.friend.display_name)
    return _build_dream(category, variant)


class DreamAnimation(Widget):
    """The Dream view's slow, looping frame-by-frame animation -- built the
    same way as vignettes.MorningVignette's own elapsed-time frame pick, just
    open-ended (loops for as long as the view stays open) instead of a fixed
    total_seconds. Purely decorative: nothing here is clickable, matching
    the "no gameplay, just enjoy it" framing this system was pitched with."""

    def __init__(self, x, y, dream: Dream, style):
        super().__init__(x, y, style)
        self.dream = dream
        self._start = time.monotonic()

    def natural_width(self, scale) -> int:
        return max(len(line) for frame in self.dream.frames for line in frame)

    def natural_height(self, scale) -> int:
        return max(len(frame) for frame in self.dream.frames)

    def draw(self, canvas) -> None:
        elapsed = time.monotonic() - self._start
        index = int(elapsed // DREAM_FRAME_SECONDS) % len(self.dream.frames)
        for row, line in enumerate(self.dream.frames[index]):
            canvas.write(self.abs_x, self.abs_y + row, line, self.style)
        # Keep the loop redrawing so the animation advances on its own --
        # same mechanism AnimatedLabel/DevToolsPanel use.
        request = getattr(canvas, "request_frame", None)
        if request is not None:
            request(DREAM_FRAME_SECONDS)
