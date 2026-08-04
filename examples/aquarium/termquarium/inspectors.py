"""Fish/Decoration inspector panels, the Daily Summary, and Settings --
small Box-building functions with no shared state between them."""

import textwrap
import time

from cozy_tui import Style, clipboard
from cozy_tui.widgets import Box, Button, Checkbox, Label, ProgressBar, ScrollView

from .constants import (
    TRAIT_DREAMER,
    TRAIT_ENERGETIC,
    TRAIT_FOOD_LOVER,
    TRAIT_INFO,
    TRAIT_MISCHIEVOUS,
    TREAT_SHOP_ITEMS,
)
from .fish import Fish, occupants_of
from .relationships import relationship_state
from .styles import HEART_STYLE, MUTED
from .tank_objects import Decoration

# Update 1's four Feeling bands (Fish.feeling), for the Inspector's own
# "Feeling: Very Happy 😄" line -- kept here, not constants.py, since it's
# purely a display concern (Fish.feeling itself is the plain band string;
# only the Inspector needs an emoji for it).
_FEELING_EMOJI = {
    "Sad": "😞",
    "Neutral": "🙂",
    "Happy": "😊",
    "Very Happy": "😄",
}

# Hunger update's five hunger bands (Fish.hunger_feeling), same reasoning as
# _FEELING_EMOJI above -- Fish.hunger_feeling is the plain band string, this
# is purely the Inspector's display of it.
_HUNGER_EMOJI = {
    "Full": "🙂",
    "Content": "😊",
    "A little hungry": "😐",
    "Hungry": "🙁",
    "Low energy": "😴",
}

# Personality System 2.0's "personality interactions" (updates.md): a small,
# curated set of flavor lines for specific personality+trait or trait+trait
# combinations -- purely cosmetic texture, kept here (not constants.py) for
# the same reason _FEELING_EMOJI/_HUNGER_EMOJI are: no mechanical effect
# anywhere depends on which combination is present, only on which individual
# personality/traits are, so this table can grow (or shrink) freely without
# touching any gameplay code. Deliberately small and hand-picked rather than
# generated for every possible pair -- most combinations just don't have
# anything clever to say yet.
_PERSONALITY_TRAIT_FLAVOR = {
    ("Explorer", TRAIT_DREAMER): (
        "A fish that dreams about places it has never visited."
    ),
    ("Friendly", TRAIT_MISCHIEVOUS): (
        "A fish that loves its friends... but constantly plays pranks on them."
    ),
}
_TRAIT_PAIR_FLAVOR = {
    frozenset({TRAIT_FOOD_LOVER, TRAIT_MISCHIEVOUS}): (
        "A fish that LOVES food... but also steals everyone else's."
    ),
    frozenset({TRAIT_ENERGETIC, TRAIT_DREAMER}): (
        "Very active during the day. Very imaginative at night."
    ),
}


def _combo_flavor_text(f: Fish) -> str | None:
    """A short flavor line for a specific personality+trait or trait+trait
    combination `f` currently matches, or None. Checked in the order the two
    tables above are defined; first match wins (a fish matching more than
    one just shows the first, rather than stacking captions)."""
    for (personality, trait), text in _PERSONALITY_TRAIT_FLAVOR.items():
        if f.personality == personality and trait in f.traits:
            return text
    for pair, text in _TRAIT_PAIR_FLAVOR.items():
        if pair <= f.traits:
            return text
    return None


def _build_inspector(
    app, f: Fish, on_rename, on_sell, treats, on_feed_treat, on_view_history=None
) -> Box:
    """A read-only stat card for one Fish (name/species/age+growth/health/
    fullness/personality/favorite spot/favorite foods/sell value) with Rename
    and Sell buttons. A snapshot at open-time, not live-refreshing --
    matching the Shop's own money label, which likewise only updates on
    explicit actions.

    "Favorite foods" (only shown for a species that has any, e.g. Axolotl)
    is a hint, not a requirement -- feeding any treat still works the same,
    a favorite just earns a nicer toast (see aquarium.py's _feed_treat).
    Sell asks for confirmation first (app.confirm(), stacked on top of this
    modal exactly like Rename's prompt already does) since it's the one
    irreversible action here.

    "Home tonight" (only shown while actually housed) is deliberately
    separate from "Favorite spot": the favorite spot is a permanent daytime
    hangout picked once at birth, while a home is re-claimed fresh every
    night (see Fish._claim_home()) and isn't always the favorite spot --
    a fish can have one of each, or neither.

    The relationship section (Step 8) never shows the raw score -- just
    its state (relationship_state()) and its most recent reasons, straight
    from that pair's shared memory log.

    `treats` is the shared `state["treats"]` stock dict -- a "Feed a
    Treat" row appears only for kinds actually in stock (bought from the
    Shop), one button each. Feeding applies the same economy.feed() relief
    regular food gives (deliberately no bonus for a treat -- see
    constants.TREAT_SHOP_ITEMS) and closes this Inspector, same as Sell."""
    spot = (
        f.favorite_decoration.kind if f.favorite_decoration is not None else "none yet"
    )
    box = Box(0, 0, "380x520", title=f.display_name, border="rounded", style=app.style)
    box.add(Label(2, 1, f"Species: {f.species_name}"))
    box.add(Label(2, 2, f"Age: {f.age_days:.1f} days ({f.growth_stage})"))
    box.add(Label(2, 3, f"Health: {f.health:.0f}%"))
    box.add(
        Label(
            2,
            4,
            f"Fullness: {f.hunger:.0f}% {_HUNGER_EMOJI[f.hunger_feeling]} {f.hunger_feeling}",
        )
    )
    # Update 1: happiness as a "personality amplifier," shown as a bar (not
    # just a number) since it's the one stat here meant to be glanced at,
    # not managed -- the Feeling line underneath is the part that actually
    # matters to a player, the bar is just the at-a-glance version of it.
    box.add(ProgressBar(2, 6, "█", " ", int(f.happiness), width=30, style=app.style))
    box.add(Label(2, 7, f"Feeling: {f.feeling} {_FEELING_EMOJI[f.feeling]}"))
    personality_line = f"Personality: {f.personality}"
    if f.is_sleepy:
        personality_line += " (also Sleepy 😴)"
    if f.traits:
        # Personality System 2.0 (ROADMAP.md): earned traits, appended the
        # same way Sleepy already is above -- one more stackable layer on
        # the same line, not a mechanic that needs its own row.
        badges = ", ".join(
            f"{TRAIT_INFO[t][0]} {TRAIT_INFO[t][1]}" for t in sorted(f.traits)
        )
        personality_line += f" · {badges}"
    combo_flavor = _combo_flavor_text(f)
    if combo_flavor is not None:
        personality_line += f'  — "{combo_flavor}"'
    box.add(Label(2, 8, personality_line))
    box.add(Label(2, 9, f"Favorite spot: {spot}"))
    y = 10
    if f.relaxing and f._relax_spot is not None:
        # Surfaces the relax mechanic in the one place a player is already
        # looking at this fish -- a snapshot of "what are you up to right now",
        # shown only when it's actually settled (see fish.py's relax/join
        # branches). `_relax_spot` rather than `favorite_decoration`: while
        # joined at a friend's spot they can differ, and a joiner may have no
        # favorite_decoration of its own at all.
        companion = (
            f", with {f._relaxing_with.display_name}"
            if f._relaxing_with is not None
            else ""
        )
        box.add(
            Label(2, y, f"Status: 😌 Relaxing near the {f._relax_spot.kind}{companion}")
        )
        y += 1
    if f.favorite_foods:
        emojis = " ".join(
            item.emoji for item in TREAT_SHOP_ITEMS if item.kind in f.favorite_foods
        )
        box.add(Label(2, y, f"Favorite foods: {emojis}"))
        y += 1
    if f.sleeping_in is not None:
        box.add(Label(2, y, f"Home tonight: {f.sleeping_in.kind} 😴"))
        y += 1

    def _add_bond(other, style):
        nonlocal y
        label, emoji = relationship_state(f.relationships[other].score)
        box.add(Label(2, y, f"{label}: {other.display_name} {emoji}", style))
        y += 1
        for reason in f.relationships[other].memories[-2:]:
            box.add(Label(4, y, f"- {reason}", MUTED))
            y += 1

    if f.friend is not None:
        _add_bond(f.friend, HEART_STYLE)
    if f.rival is not None:
        _add_bond(f.rival, Style(fg="bright_red"))

    if f.memory_log:
        # This fish's own diary (aquarium.py's _log_memory()) -- distinct
        # from the friend/rival "why" lines above, which are a shared pair
        # record. Newest last, like the log itself; only the last 5 shown
        # so this section stays glanceable rather than a scrolling wall --
        # "See All History" below is the uncapped version, for the player
        # rather than for the fish (see fish.py's full_memory_log).
        box.add(Label(2, y, "Memory Log", Style(styles=["bold"])))
        y += 1
        for entry in f.memory_log[-5:]:
            box.add(Label(2, y, entry, MUTED))
            y += 1
        y += 1
        if on_view_history is not None:
            box.add(
                Button(2, y, "See All History").on_click(lambda _w: on_view_history(f))
            )
            y += 2

    box.add(Label(2, y, f"Sell value: ${f.sell_value}"))
    y += 2

    in_stock = [item for item in TREAT_SHOP_ITEMS if treats.get(item.kind, 0) > 0]
    if in_stock:
        box.add(Label(2, y, "Feed a Treat", Style(styles=["bold"])))
        y += 1
        for item in in_stock:
            box.add(
                Button(
                    2, y, f"{item.emoji} {item.kind} ({treats[item.kind]})"
                ).on_click(
                    lambda _w, kind=item.kind: (
                        on_feed_treat(f, kind),
                        app.close_overlay(box),
                    )
                )
            )
            y += 1
        y += 1

    def _on_sell(_widget):
        app.confirm(
            f"Sell {f.display_name} for ${f.sell_value}?",
            on_yes=lambda: (on_sell(f), app.close_overlay(box)),
        )

    box.add(Button(2, y, "Rename").on_click(lambda _w: on_rename(f)))
    box.add(Button(14, y, "Sell").on_click(_on_sell))
    box.add(Button(24, y, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box


def _build_fish_history(app, f: Fish) -> Box:
    """Every entry ever logged for this fish (aquarium.py's _log_memory()),
    with no cap -- purely a player-facing archive (fish.py's
    full_memory_log), reached via the ordinary Inspector's "See All History"
    button. Deliberately separate from what the fish itself "remembers":
    the Inspector's own Memory Log section (last 5 of the *capped*
    memory_log) is what still feeds dream selection and what actually fades
    with time -- this view exists so a real moment the player cared about
    isn't lost just because the fish has since moved on. Read-only, and
    scrollable (ScrollView, the same widget the crash screen's traceback and
    DevTools' Console tab use) since a long-lived fish's full history can
    run well past a fixed panel's height.

    A dream memory ("[Day N] I dreamed about ... <full description>.") can
    easily run past a single row -- each entry is wrapped (textwrap, the same
    approach the Text widget itself uses for prose) across as many rows as it
    needs, rather than silently clipped at the viewport edge."""
    width_cells = 56
    box = Box(
        0,
        0,
        f"{width_cells * 10}x460",
        title=f"{f.display_name}'s History",
        border="rounded",
        style=app.style,
    )
    view_width_cells = width_cells - 6  # inset + scrollbar column
    view = ScrollView(
        2, 1, f"{view_width_cells * 10}x380", autoscroll=False, style=app.style
    )
    y = 0
    for entry in f.full_memory_log:
        for line in textwrap.wrap(entry, width=view_width_cells - 2) or [""]:
            view.add(Label(0, y, line, MUTED))
            y += 1
    box.add(view)
    box.add(Button(2, 41, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box


def _build_decoration_inspector(
    app, d: Decoration, fish, on_sell, on_enter
) -> Box:
    """Decorations are sellable too -- an emergency option (per the user's
    own framing: "instead of game over, I guess the castle has to go...")
    rather than just cosmetic. Sell asks for confirmation first, same
    pattern as the Fish Inspector's Sell button.

    Containers (capacity > 0, e.g. the Castle) also show who's sleeping
    inside right now, plus an "Enter {kind}" button into the dedicated,
    quieter Castle Interior view (_build_castle_interior) -- a deliberate
    choice to actually go look, rather than this stat list being the only
    way to see them.

    `on_sell=None` (the Forest's shelter fixtures -- Tree House/Hidden
    Cave/Dense Plants Thicket) omits the Sell row entirely: those are
    scenery the player finds already there, never bought from the Shop
    and not in the `decorations` list a real sale would remove from, so
    there's no sale to offer (and no $0 "Sell value" to show for it)."""
    box = Box(0, 0, "340x220", title=d.kind, border="rounded", style=app.style)
    y = 1
    if d.is_container:
        occupants = occupants_of(d, fish)
        box.add(Label(2, y, f"Capacity: {len(occupants)}/{d.capacity}"))
        y += 1
        if occupants:
            for guest in occupants:
                box.add(Label(2, y, f"😴 {guest.display_name}", MUTED))
                y += 1
        else:
            box.add(Label(2, y, "(nobody home right now)", MUTED))
            y += 1
        box.add(
            Button(2, y, f"Enter {d.kind}").on_click(
                lambda _w: (app.close_overlay(box), on_enter(d))
            )
        )
        y += 2

    if on_sell is not None:
        box.add(Label(2, y, f"Sell value: ${d.sell_value}"))
        y += 2

        def _on_sell(_widget):
            app.confirm(
                f"Sell this {d.kind} for ${d.sell_value}?",
                on_yes=lambda: (on_sell(d), app.close_overlay(box)),
            )

        box.add(Button(2, y, "Sell").on_click(_on_sell))
        box.add(Button(12, y, "Close").on_click(lambda _w: app.close_overlay(box)))
    else:
        box.add(Button(2, y, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box


def _build_castle_interior(app, d: Decoration, fish, on_open_dream=None) -> Box:
    """The "Enter {kind}" destination: a quiet, read-only look at whoever's
    sleeping inside right now, laid out as beds of two -- pillows (⬜) and
    all, per the user's own ASCII language for this. Deliberately reached
    by choice from the Decoration Inspector, not shoved in the player's
    face; deliberately read-only (no Sell/Rename here) since this is for
    watching, not managing. Leave just closes like any other Inspector's
    Close button -- cleanup (canceling the live-refresh timer, see
    aquarium.py's _enter_decoration()) is wired through open_overlay's own
    on_close hook instead, so it fires no matter how this gets dismissed
    (Leave, click-outside, Esc), not only the one button.

    Fish are shown as a generic "🐠 Name 😴"/"🐠 Name 🙂", not each fish's
    species glyph -- the glyph is for open-water movement/direction, this
    is a name-forward "who's home" list. A woken fish doesn't vanish the
    instant it wakes: it lingers here, shown 🙂 (see fish.py's
    _awake_in_home / WAKE_LINGER_SECONDS), before actually leaving --
    and the whole room leaves together once everyone's awake
    (Fish._roommates_ready_to_leave()), not one at a time. Mid wake
    attempt, the attempting fish's mood is replaced by "*boop*" for
    BOOP_FLASH_SECONDS (set in aquarium.py's _process_sleepy_holds(), for
    every attempt -- resisted or not); the tankmate on the receiving end
    shows "*...zzz*" for the same window if that attempt was resisted.
    aquarium.py's _enter_decoration() re-opens this same box on a timer
    while it's up so none of this goes stale while the player's watching.

    Since most sleeping fish end up housed once a player owns any container,
    a dreaming occupant's row gets a 💭 next to its 😴 (same as the
    open-tank indicator, fish.py's draw()) and becomes clickable into the
    Dream view (on_open_dream) instead of a plain Label -- every other
    occupant is unchanged. A nightmare forces its own early, one-fish wake
    (see aquarium.py's _process_nightmares()): mood briefly shows 😨, then
    -- once it's relocated to sleep beside a Friend, possibly in a
    different bed shown here (or its own, if no Friend exists) -- 🥺 for a
    moment before settling back to a plain mood."""
    occupants = occupants_of(d, fish)
    now = time.monotonic()
    beds = -(-d.capacity // 2)  # ceil division; today's containers are even
    box = Box(
        0, 0, "380x300", title=f"{d.kind} Interior", border="rounded", style=app.style
    )
    y = 1
    slot = 0
    for _ in range(beds):
        box.add(Label(2, y, "-" * 16, MUTED))
        y += 1
        for _ in range(min(2, d.capacity - slot)):
            if slot < len(occupants):
                guest = occupants[slot]
                if (
                    guest._just_booped_until is not None
                    and now < guest._just_booped_until
                ):
                    mood = "*boop*"
                elif (
                    guest._just_scared_until is not None
                    and now < guest._just_scared_until
                ):
                    mood = "😨"
                elif (
                    guest._nightmare_comfort_until is not None
                    and now < guest._nightmare_comfort_until
                ):
                    mood = "🥺"
                elif (
                    guest._just_resisted_wake_until is not None
                    and now < guest._just_resisted_wake_until
                ):
                    mood = "*...zzz*"
                elif guest._awake_in_home:
                    mood = "🙂"
                elif guest.dream is not None:
                    mood = "😴💭"
                else:
                    mood = "😴"
                text = f"⬜ 🐠 {guest.display_name} {mood}"
                if mood == "😴💭" and on_open_dream is not None:
                    box.add(
                        Button(2, y, text).on_click(
                            lambda _w, guest=guest: on_open_dream(guest)
                        )
                    )
                else:
                    box.add(Label(2, y, text))
            else:
                box.add(Label(2, y, "⬜ (empty)", MUTED))
            slot += 1
            y += 1
        box.add(Label(2, y, "-" * 16, MUTED))
        y += 2
    box.add(Button(2, y, "Leave").on_click(lambda _w: app.close_overlay(box)))
    return box


def _build_daily_summary(
    style,
    day: int,
    visitors: int,
    ticket_sales: int,
    donations: int,
    grant: int,
    food_expense: int,
    net: int,
) -> Box:
    """The end-of-day report -- non-modal and auto-dismissing (see main()),
    since it's a periodic ceremony, not something that should interrupt
    whatever the player's doing every couple of minutes."""
    green, red = Style(fg="bright_green"), Style(fg="bright_red")
    box = Box(0, 0, "380x220", title=f"Day {day}", border="rounded", style=style)
    box.add(Label(2, 1, f"Visitors: {visitors}"))
    box.add(Label(2, 2, f"Ticket Sales: +${ticket_sales}", green))
    box.add(Label(2, 3, f"Donations Today: +${donations}", green))
    box.add(Label(2, 4, f"Maintenance Grant: +${grant}", green))
    box.add(Label(2, 5, f"Food Expenses: -${food_expense}", red))
    sign = (
        "+" if net >= 0 else "-"
    )  # goes before the $, not net's own minus (avoids "$-20")
    box.add(
        Label(
            2,
            7,
            f"Net Profit: {sign}${abs(net)}",
            Style(fg=green.fg if net >= 0 else red.fg, styles=["bold"]),
        )
    )
    return box


def _build_settings(
    app,
    state,
    cloud_key,
    on_setup_cloud,
    on_change_key,
    on_forget_key,
    on_restore,
) -> Box:
    """Gameplay (Emergency Aquarium Welfare, Auto-Pause), Display (ambient
    bubbles), and Cloud Saves. Checked state lives directly in `state`, the
    same dict everything else in this economy reads/writes -- Auto-Pause is
    read live by aquarium.py's _enter_auto_pause(), so toggling it here
    takes effect the next time Pause/Shop/Settings/the Cheat Console opens,
    not retroactively on whichever of them is already open. `cloud_key` is a
    snapshot at open-time (None if cloud saves has never been set up on
    this machine); the four callbacks are aquarium.py's actual network/
    storage actions -- this function only builds the box and closes itself
    before handing off, so it doesn't need to know how any of them work."""
    box = Box(0, 0, "440x400", title="Settings", border="rounded", style=app.style)
    box.add(Label(2, 1, "Gameplay", Style(styles=["bold"])))

    welfare_cb = Checkbox(
        2, 3, "Emergency Aquarium Welfare", checked=state.get("welfare_enabled", True)
    )
    welfare_cb.on_change(lambda checked: state.update(welfare_enabled=checked))
    box.add(welfare_cb)

    box.add(Label(2, 5, "If enabled, a bankrupt tank (no money, no food,", MUTED))
    box.add(Label(2, 6, "no fish) gets a small fresh start instead of", MUTED))
    box.add(Label(2, 7, "staying empty forever. Turn it off for hardcore mode.", MUTED))

    auto_pause_cb = Checkbox(2, 9, "Auto-Pause", checked=state.get("auto_pause", True))
    auto_pause_cb.on_change(lambda checked: state.update(auto_pause=checked))
    box.add(auto_pause_cb)

    box.add(Label(2, 11, "Pause, Shop, Settings, and the Cheat Console freeze", MUTED))
    box.add(Label(2, 12, "the tank while open. Off, it keeps running behind them.", MUTED))

    box.add(Label(2, 14, "Display", Style(styles=["bold"])))

    bubbles_cb = Checkbox(
        2, 16, "Ambient Bubbles", checked=state.get("bubbles_enabled", True)
    )
    bubbles_cb.on_change(lambda checked: state.update(bubbles_enabled=checked))
    box.add(bubbles_cb)

    box.add(Label(2, 18, "Purely cosmetic rising bubbles. Turn off if you", MUTED))
    box.add(Label(2, 19, "find them distracting.", MUTED))

    box.add(Label(2, 21, "Cloud Saves", Style(styles=["bold"])))

    def _run_and_close(callback):
        # Every cloud action needs this Settings box gone before it runs --
        # setup/restore reopen a fresh Settings once they're done (so the
        # key/key-less state shown here stays honest), and none of them
        # should have to know this box exists to close it themselves.
        def _handler(_w=None):
            app.close_overlay(box)
            callback()

        return _handler

    if cloud_key:
        box.add(Label(2, 23, f"Key: {cloud_key}", MUTED))

        def _copy(_w=None):
            clipboard.copy(cloud_key)
            app.toast("Cloud Key copied.", level="success")

        box.add(Button(2, 25, "Copy Key").on_click(_copy))
        box.add(
            Button(16, 25, "Use a Different Key").on_click(
                _run_and_close(on_change_key)
            )
        )
        box.add(Button(2, 27, "Restore My Saves").on_click(_run_and_close(on_restore)))
        box.add(Button(22, 27, "Forget Key").on_click(_run_and_close(on_forget_key)))
    else:
        box.add(Label(2, 23, "Not set up yet -- saves stay local only.", MUTED))
        box.add(
            Button(2, 25, "Set Up Cloud Saves").on_click(_run_and_close(on_setup_cloud))
        )

    box.add(Button(2, 29, "Close").on_click(lambda _w: app.close_overlay(box)))
    return box
