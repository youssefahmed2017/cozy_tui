"""Aquarium -- a cozy stress-test/showcase app.

Step 1: a tank full of independently-swimming fish, each its own Widget
instance (not one big custom-drawn Widget like examples/snake/snake.py) --
continuous motion via app.tick_interval, bouncing off the tank walls, drawn
by simple diff-rendering just like everything else in this library.

Step 2: click inside the tank to drop food; fish steer toward the nearest
food instead of just random-walking, eating it on contact. Each fish also
carries hunger/health that decays on its own clock (app.every), separate
from the per-frame movement update.

Step 3: a real economy. Money/Food counters replace Step 1's placeholders --
feeding spends food, buying spends money -- and a Shop overlay (a plain
Box + Button rows, opened with the "Open Shop" button or the S key) sells
more fish. The Shark is a deliberately different kind of fish: a predator
that hunts other fish instead of food, using the exact same steer-toward-
target/eat-on-contact mechanics Step 2 built for food.

Step 4: fixed Decoration widgets (a Plant, a Rock, a Castle) sit on the tank
floor. Fish steering gains a third blend term -- a repulsion push away from
whichever decoration they're nearest to, once inside its avoidance radius --
so they visibly curve around the furniture instead of swimming through it.
This is deliberately cheap steering-based avoidance, not real pathfinding: a
fish beelining for food directly behind a decoration will still get nudged
off course reactively rather than routing all the way around it. Decorations
are added before any fish, so (relying on plain z-order/draw-order layering,
not a real depth sort) fish always draw on top of them.

Step 5 (replacing the originally-planned settings panel -- skipped by
request): fish personality, naming, an Inspector panel, ASCII-art decorations,
food in the Shop, and starvation. Every Fish gets one of six named
personalities (Friendly/Explorer/Shy/Greedy/Lazy/Playful -- a single choice,
not independent traits) that changes its steering, turn cadence, and/or speed.
Mouse position is tracked via the same app.on_mouse() hook already used for
click-to-feed, extended to also record MouseMove; personality steering reuses
steer_toward_food/avoid_decorations exactly like food-seeking and decoration-
avoidance do, just aimed at a different target, with a fixed per-frame
priority: fleeing beats eating beats personality-driven steering beats plain
wandering. Clicking a fish opens an Inspector (name, species, age, health,
hunger, personality) with a Rename button (app.prompt()); hovering one shows a
quick live tooltip instead, via a custom on_enter/on_leave wiring rather than
App.set_tooltip() itself -- the tooltip text needs to stay live (hunger keeps
changing), and re-calling set_tooltip() to "refresh" it would silently
orphan any tooltip that happened to be open at that moment (single-slot
on_enter/on_leave, same as on_click). Decorations are real multi-row ASCII
art (Plant/Driftwood/Rock/Castle), not emoji -- an emoji glyph is drawn by the
terminal's own emoji font and mostly ignores our Style color. The Shop now
also sells a Fish Food restock. And a fish whose health reaches 0 (prolonged
starvation) dies -- removed from the tank with a toast.

Phase 2 (per the user's own roadmap): each fish randomly picks one Decoration
as its favorite spot at birth, shown in the Inspector ("Favorite spot: Rock").
On its own periodic clock (independent of the movement/hunger clocks), it has
a chance to swim over and relax there for a while -- gently damping its own
velocity once it arrives, rather than continuing to actively steer, so it
visibly settles down instead of just orbiting the spot. This sits at the
bottom of the existing steering priority (fleeing beats eating beats
personality-driven steering beats relaxing beats plain wandering): a
relaxing fish still drops everything to flee or eat, exactly like a
Friendly fish already drops its mouse-following the instant food shows up.

Phase 3: a real economy. Fish grow up (Baby -> Juvenile -> Adult, a real
glyph change, not just a number) and both fish and decorations can be sold
back for money (a fraction of their Shop price) via their Inspector panels,
each behind a confirmation. The Shop also sells decorations now. A daily
tick (app.every(AGE_SECONDS_PER_DAY, ...), the same "day" fish age by) pays
out a Maintenance Grant plus Visitor Donations -- attractiveness from fish,
decorations, and tank cleanliness drives a visitor count, each paying a
ticket price plus a random donation -- and shows a non-modal, auto-dismissing
Daily Summary. Settings (G key) holds one Gameplay toggle so far: Emergency
Aquarium Welfare, which gives a totally bankrupt tank (money = food = fish =
0) a small fresh start instead of leaving it empty forever.

Phase 4: relationships. Any newly-introduced fish (starter, bought, or born)
has a chance to bond with an existing one -- a mutual Friend (they drift
toward each other when neither has anything more urgent going on) or a
Rival (the disliked fish flees the moment its rival gets close, regardless
of personality, on top of Shy's existing mouse-fleeing; having a rival also
gives a fish's own food-seeking a modest "competitive" speed boost -- it's
racing its rival for food, not just hunger). Friend pairs where both are
grown-up, non-predator fish have a chance each day of a baby -- inheriting
one parent's species, born at their midpoint, and immediately eligible for
its own relationships and favorite spot like any other fish. Selling/losing
a fish clears any dangling friend/rival references pointing at it, the same
care already taken for a sold favorite Decoration.

Phase 5: world. A continuous day/night cycle (Night/Morning/Day, threshold-
based off one elapsed-time fraction) drives both the tank's background tint
and its water temperature (warmest at midday, coolest at midnight) off the
same underlying curve, so they stay in sync for free (see termquarium/
world.py). Temperature affects gameplay -- cold water slows fish down, hot
water speeds up hunger -- and Night puts every fish (hungry ones excepted --
see SLEEP_HUNGER_THRESHOLD) to sleep: a hard stop, not just slower, with
friends drifting to sleep close together and rivals as far apart as the
tank allows.

Phase 6: polish + stress test. A dev/debug key (Z) mass-spawns free starter
fish up to a 50-fish cap, proving the diff-renderer stays smooth with a lot
of independently-moving Fish widgets at once -- the whole point of this
example. Ambient bubbles (purely decorative, toggleable in Settings) rise
from the tank floor for a little extra life. Schooling: same-species,
non-predator fish within SCHOOL_RADIUS drift into loose groups via a
lightweight boids-style blend (cohesion + alignment + separation) once
nothing more urgent (fleeing/eating/personality steering/friend-following/
relaxing) is happening -- a species-level trait, not a personality one like
Friendly's own group pull, so it applies underneath everything else in the
priority chain, just above plain wandering.

Save/Load management: the Load menu's Rename/Duplicate/Delete (each mirroring
the Fish Inspector's own Rename/Sell pattern -- a prompt or confirm dialog,
then the actual save.py mutation once submitted/confirmed) sit alongside
Load on every card. Save (P) itself only prompts for a name the very first
time in a fresh session; once attached to a save (by loading one, or by
that first manual save), it writes straight back into the same file from
then on, so a normal session doesn't pile up one save per day.

Phase 7: container decorations. `capacity` (Rock=2, Castle=4; everything
else 0) is the one number that turns a decoration into a home a sleeping
fish can claim overnight -- no separate class, so any future decoration
becomes one just by giving it a nonzero capacity. Each night, a fish picks
a container via Fish._claim_home(), priority: its favorite spot (if that's
a container with room) -> a friend's already-claimed container (if it has
room, so best friends end up sleeping in the *same* home) -> the nearest
container with any room -> the tank floor (the original friend-close/
rival-far/settle behavior, unchanged, for whoever finds no room). Once
inside, a fish is frozen and invisible in the tank itself -- clicking the
decoration (the existing Decoration Inspector) is the only way to peek in
and see who's home. Waking clears the claim and drops the fish right back
at the door. A lighthearted one-line toast at the Night -> Morning
transition (see choose_morning_vignette()) picks a Friend pair for a bit of
narrative texture -- cosmetic only, since every fish still wakes together
mechanically; it isn't simulating individual wake times. Personality biases
which container (if any) a fish claims -- see Fish._claim_home()'s
docstring for Lazy/Shy/Friendly/Explorer's exact reordering of the baseline
priority.

Phase 8: Pause menu. Esc (which used to instantly quit) opens it instead --
every Fish/BubbleField checks the same shared `paused` flag this menu
flips, freezing solid (frozen in place and still drawn, unlike a housed
fish which stays invisible) rather than just showing a menu over a
simulation that keeps quietly running behind it. Quit lives behind its own
confirmation now, since Esc no longer doubles as instant, unconfirmed exit.

Sleepy: an independent yes/no trait rolled once at birth (roll_is_sleepy()),
stackable with a fish's regular personality rather than replacing it --
a Greedy fish can also be Sleepy. It only matters for the morning vignette
(choose_morning_vignette()): a Sleepy sleeper practically never gets the
"wake" flavor, resisting a normal boop almost every time (*boop* ... *...zzz*
instead of *awake*) rather than actually waking.

Phase 9: relationship scores, replacing the old one-time Friend/Rival dice
roll (see relationships.py's module docstring for the full model). Every
pair of fish shares exactly one continuous score in [-100, 100] -- nudged
by real interactions (record_wake_up/record_slept_together/
record_gave_up_home/record_saved_from_shark/record_pushed_from_home; the
rest of the original design -- sharing/stealing food, playing, fighting --
are natural follow-ups once those mechanics exist), decaying slowly back
toward 0 if left alone
(decay_relationships(), once a day), and never shown to the player as a
raw number -- only a state (relationship_state(): Rival/Dislikes/Neutral/
Friend/Best Friend) plus its most recent reasons. Fish.friend/Fish.rival
are now read-only properties derived from whichever relationship is
currently strongest/weakest (relationships.best_bond()/worst_bond()), so
all of Fish's existing friend-following/rival-fleeing/sleep-together/
container-priority steering keeps working unchanged. A brand new fish
(starter, bought, or born) starts with no relationships at all -- they're
earned, not rolled.

Everything reusable/testable -- pure steering/economy/relationship math, the
Fish/Decoration/Food/BubbleField widgets, and the modal-builder functions --
lives in the termquarium/ package next to this file; aquarium.py itself is
just main(), which wires all of it into one running App. See
tests/test_aquarium.py, which imports this file directly (not the package)
so every one of these re-exported names stays reachable as aq.<name>.
"""

import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cozy_tui import App, Style
from cozy_tui._width import text_width
from cozy_tui.events import Key, MouseClick, MouseMove
from cozy_tui.motion import lerp_color
from cozy_tui.widgets import Button, Dropdown, Label, ListItem

from examples.aquarium.termquarium.bubbles import BubbleField, _Bubble, rise_bubble
from examples.aquarium.termquarium.console import (
    CheatConsole,
    build_console_commands,
    run_console_command,
)
from examples.aquarium.termquarium.constants import *
from examples.aquarium.termquarium.dreams import choose_dream, make_dream
from examples.aquarium.termquarium.economy import (
    compute_attractiveness,
    compute_visitor_income,
    decay_hunger,
    feed,
    roll_visitor_donation,
    should_grant_welfare,
    should_warn_hungry,
)
from examples.aquarium.termquarium.fish import (
    Fish,
    _make_fish,
    describe_fish,
    fish_at,
    occupants_of,
)
from examples.aquarium.termquarium.inspectors import (
    _build_castle_interior,
    _build_daily_summary,
    _build_decoration_inspector,
    _build_inspector,
    _build_settings,
)
from examples.aquarium.termquarium.relationships import (
    all_relationship_pairs,
    choose_baby_species_name,
    choose_morning_vignette,
    clear_relationships,
    decay_relationships,
    find_breeding_pairs,
    find_eligible_waker,
    find_mutual_friend_pairs,
    get_relationship,
    random_personality,
    record_gave_up_home,
    record_pushed_from_home,
    record_saved_from_shark,
    record_slept_together,
    record_wake_up,
    relationship_state,
    remember,
    resolve_wake_attempt,
    roll_is_sleepy,
    roll_wake_threshold,
    set_relationship,
)
from examples.aquarium.termquarium.cloud import (
    delete_cloud_save,
    download_save as download_cloud_save,
    generate_cloud_key,
    list_cloud_saves,
    upload_save as upload_cloud_save,
)
from examples.aquarium.termquarium.save import (
    delete_save,
    duplicate_save,
    list_saves,
    load_cloud_key,
    load_unlocked_achievements,
    read_save,
    rename_save,
    store_cloud_key,
    store_unlocked_achievements,
    write_save,
)
from examples.aquarium.termquarium.shop import build_shop as _build_shop
from examples.aquarium.termquarium.steering import (
    avoid_decorations,
    nearest_index,
    random_velocity,
    school_velocity,
    steer,
    steer_toward_food,
)
from examples.aquarium.termquarium.styles import (
    STATS,
    TITLE,
    VIGNETTE_STYLE,
    WATER_LINE,
)
from examples.aquarium.termquarium.tank_objects import (
    Decoration,
    Food,
    TigerShark,
    Wood,
    decoration_at,
)
from examples.aquarium.termquarium.ui import (
    build_achievements_menu,
    build_dream_view,
    build_forest_scene,
    build_help_menu,
    build_pause_menu,
    build_restore_menu,
    build_save_menu,
    build_start_menu,
)
from examples.aquarium.termquarium.vignettes import MorningVignette
from examples.aquarium.termquarium.world import (
    compute_time_of_day,
    compute_water_temperature,
    get_day_phase,
    night_blend,
)

import math


def main() -> None:
    app = App(full=True, style=Style(fg="white", bg="black"), title="TermQuarium")
    app.tick_interval = 0.05  # continuous redraws; each Fish gates its own dt
    # The real, persistent aquarium scene -- the exact same list object as
    # app.widgets from here on (an alias, not a copy), so every existing
    # app.add()/app.widgets.remove()/insert() call below keeps working
    # completely unchanged. Only meaningful once the Forest exists (see
    # _enter_forest()/_leave_forest()): app.widgets gets pointed at
    # `forest_widgets` instead while the Forest is shown, and back at this
    # same object on Leave -- nothing in between needs to know that ever
    # happened.
    aquarium_widgets = app.widgets

    app.add(
        Label(
            2,
            0,
            "TermQuarium -- click to feed, S: shop, G: settings, P: save, L: load, "
            "Z: stress test, Esc: pause",
            TITLE,
        )
    )
    stats = Label(2, 1, "", STATS)
    app.add(stats)

    tank_x, tank_y = 2, 3
    tank_w = min(70, max(20, app.cols - 6))
    tank_h = min(20, max(8, app.rows - 8))

    app.add(Label(tank_x, tank_y, "~" * tank_w, WATER_LINE))
    app.add(Label(tank_x, tank_y + tank_h + 1, "~" * tank_w, WATER_LINE))

    bounds = (
        float(tank_x),
        float(tank_y + 1),
        float(tank_x + tank_w - 1),
        float(tank_y + tank_h),
    )
    foods = []
    fish = []
    # Exploration Update Slice 1: live Wood items currently sitting in the
    # Forest, regardless of whether that scene is the one currently shown
    # -- mirrors `foods`' own shape. `in_forest` mirrors `paused`'s shared-
    # mutable-flag pattern, checked by _on_mouse()/_check_foraging() alike.
    forest_wood = []
    in_forest = {"value": False}
    # The Tiger Shark currently prowling the Forest during a forage-danger
    # event, or None (see _check_forest_danger()) -- transient, at most one
    # at a time, and never persisted (a save mid-visit just resets like a
    # fish mid-forage-trip does). Same shared-mutable-dict shape as
    # `in_forest`, so the per-second check can carry it across ticks.
    forest_shark = {"widget": None, "until": None}
    # Built once, at boot -- see build_forest_scene()'s own docstring for
    # why fish/wood don't need to be part of this initial construction.
    # `forest_button` is a real Button from the start too, just not
    # attached to `aquarium_widgets` (so not visible/clickable) until
    # _unlock_forest() adds it.
    forest_widgets, forest_stats_label, forest_bounds = build_forest_scene(
        app, lambda: _leave_forest(), lambda: paused["value"]
    )
    forest_button = Button(59, 2, "Enter Forest").on_click(lambda _w: _enter_forest())
    state = {
        "money": 120,
        "food": 15,
        "food_spent_today": 0,
        "donations_today": 0,
        "welfare_enabled": True,
        "bubbles_enabled": True,
        "treats": {},
        "forest_unlocked": False,
    }
    hungry_warning_active = {"value": False}
    day_count = {"n": 0}
    # Which tier ("rival"/"neutral"/"friend") each pair was in as of the
    # last daily scan (see _check_milestone_achievements()) -- lets a real
    # tier *crossing* get its own one-shot memory-log line ("I became
    # friends with X") instead of re-logging it every single day the pair
    # simply stays there. Deliberately session-only, not saved/restored:
    # worst case after a reload is one re-logged crossing, not worth the
    # save-format churn to avoid.
    relationship_tier_seen: dict = {}
    # Fish ids already announced as having reached Elder (see
    # _check_milestone_achievements()) -- the achievement itself is
    # account-wide/one-shot already (_unlock_achievement()'s own guard),
    # but the per-fish "I'm getting older" memory line needs its own
    # one-shot tracking so it doesn't repeat every single day a fish stays
    # Elder. Session-only, same reasoning as relationship_tier_seen above.
    elder_announced: set = set()
    # None until Cloud Saves is set up (or restored via an existing key) on
    # this machine -- see _open_settings()'s Cloud Saves section. Kept
    # separate from `state`/save snapshots deliberately: the key lives with
    # the *machine*, not with any one aquarium's save file.
    cloud = {"key": load_cloud_key()}
    # Achievement ids already unlocked -- account-wide like the Cloud Key
    # above (see save.py's load_unlocked_achievements()), not tied to any
    # one aquarium's save, so a New Aquarium or Load never resets these.
    unlocked_achievements = load_unlocked_achievements()
    # Name of the save this session is currently "attached to" -- None until
    # the player has either loaded or manually saved once. Once set, Save
    # (P) writes straight back into that same save instead of prompting for
    # a new name every time, so a normal play session doesn't pile up one
    # file per day (see _save_game()).
    current_save = {"name": None}
    # Shared with every Fish/BubbleField -- the Pause menu (Esc) flips this
    # and everything freezes solid; see _open_pause_menu().
    paused = {"value": False}
    mouse_pos = {
        "x": None,
        "y": None,
    }  # shared with every Fish -- see personality steering
    # Day/night fraction is elapsed-time-since-start, modulo a day -- offset
    # so a fresh session (and a loaded save, which doesn't itself store a
    # time of day) always starts at midday (fraction 0.5), not fraction 0
    # (which get_day_phase() defines as Night).
    session_start = time.monotonic() - AGE_SECONDS_PER_DAY * 0.5
    environment = {
        "phase": "Day",
        "temperature": BASE_WATER_TEMP,
        # A live storm in progress -- see _maybe_trigger_random_event()'s
        # "storm" branch/_end_storm() below and fish.py's draw(), which
        # steers every awake fish toward the nearest container while True.
        "storm": False,
    }  # shared with every Fish -- see world.py

    # Decorations sit on the tank floor and are added before any fish, so
    # (plain add-order z-layering, see the module docstring) fish always
    # draw on top of them. Built from DECORATION_CATALOG (the same source
    # the Shop sells from) so a starting Castle sells for the same value as
    # a bought one.
    floor_y = tank_y + tank_h

    # Ambient bubbles, added before decorations so (plain add-order
    # z-layering, same convention as decorations-before-fish) they always
    # drift behind the furniture and fish rather than over them.
    app.add(
        BubbleField(bounds, lambda: state["bubbles_enabled"], lambda: paused["value"])
    )

    def _make_starting_decoration(kind: str, x) -> Decoration:
        item = DECORATION_CATALOG[kind]
        return Decoration(
            x,
            floor_y - len(item.art) + 1,
            item.art,
            item.colors,
            kind=kind,
            price=item.price,
            capacity=item.capacity,
        )

    # Seeded by _seed_starter_aquarium() (defined below, once _add_fish
    # exists) -- called once at the bottom of main() for the initial boot,
    # and again from _return_to_main_menu()'s "New Aquarium" for a real
    # mid-session reset.
    decorations = []

    PHASE_ICON = {"Day": "☀️", "Morning": "🌅", "Night": "🌙"}

    def _refresh_stats():
        icon = PHASE_ICON.get(environment["phase"], "☀️")
        stats.text = (
            f"Money: ${state['money']}   Food: {state['food']}   Fish: {len(fish)}"
            f"   {icon} {environment['phase']}, {environment['temperature']:.0f}°C"
        )

    def _in_tank(f: Fish) -> bool:
        # True only for a fish genuinely present in the aquarium right now
        # -- excludes a fish away in the Forest *and* one mid-transit
        # between biomes (see _check_foraging()), whose fx/fy are stale
        # tank coordinates that must never spuriously match real tank-only
        # checks (shark scares, night-event pairing, dream assignment).
        return f.biome == "aquarium" and f._travel_until is None

    def _unlock_achievement(achievement_id: str) -> None:
        # A no-op past the first call for any given id -- every call site
        # below fires unconditionally whenever its event happens, trusting
        # this to only ever toast/persist once.
        if achievement_id in unlocked_achievements:
            return
        unlocked_achievements.add(achievement_id)
        store_unlocked_achievements(unlocked_achievements)
        achievement = next(a for a in ACHIEVEMENTS if a.id == achievement_id)
        app.toast(
            f"Achievement unlocked: {achievement.name}",
            level="success",
            icon="🏆",
            duration=6.0,
        )

    def _check_new_fish_achievements(f: Fish) -> None:
        if f.species_name == "Axolotl":
            _unlock_achievement("first_axolotl")

    def _open_achievements():
        app.open_overlay(
            build_achievements_menu(app, ACHIEVEMENTS, unlocked_achievements),
            close_on_click_outside=True,
        )

    def _log_memory(f: Fish, text: str) -> None:
        # This fish's own diary (see fish.py's Fish.memory_log) -- distinct
        # from Relationship.memories, which is a shared pair record. Every
        # call site below is an already-real, already-firing event; no new
        # mechanics invented just to have something to write down.
        f.memory_log.append(f"[Day {day_count['n']}] {text}")
        del f.memory_log[:-MEMORY_LOG_LIMIT]

    def _log_departure(departed: Fish, cause: str | None = None) -> None:
        # Must run before clear_relationships(departed, fish) -- that's what
        # erases the bond info this reads. A deliberately simpler version of
        # "the tank is getting quieter": one line per real departure, for
        # bonded tankmates only, not a batched roster-comparison narrative.
        # The standard line's exact wording is load-bearing: dreams.py's
        # _DEPARTURE_RE matches it verbatim to power reunion dreams, so it
        # must stay identical for every cause of death, including this
        # optional `cause` flavor line, which is purely additive.
        for other in fish:
            if other is not departed and departed in other.relationships:
                _log_memory(other, f"{departed.display_name} isn't around anymore.")
                if cause:
                    _log_memory(other, cause.format(name=departed.display_name))

    def _open_dream(f: Fish) -> None:
        app.open_overlay(
            build_dream_view(app, f, _open_inspector), close_on_click_outside=True
        )

    def _wire_tooltip(f: Fish) -> None:
        # Not app.set_tooltip(f, fixed_text): that captures `text` once at
        # registration time, but a fish's hunger (and display_name, after a
        # rename) changes over its life. Wiring on_enter/on_leave directly,
        # once, and computing describe_fish(f) lazily inside _open() (i.e.
        # at the moment the tooltip actually opens, not when this function
        # ran) keeps it live without ever needing to re-register the
        # handlers -- re-calling set_tooltip later to "refresh" the text
        # would replace on_enter/on_leave (single-callback-slot, like
        # on_click) out from under a tooltip that's *currently* open,
        # orphaning it: nothing would ever close it again.
        state = {"timer": None, "tip": None}

        def _hide(_w=None):
            if state["timer"] is not None:
                app.cancel(state["timer"])
                state["timer"] = None
            if state["tip"] is not None:
                app.close_overlay(state["tip"])
                state["tip"] = None

        def _open():
            from cozy_tui.widgets.display.tooltip import Tooltip

            state["timer"] = None
            tip = Tooltip(f, describe_fish(f))
            state["tip"] = tip
            app.open_overlay(
                tip, modal=False, dim=False, center=False, close_on_escape=False
            )

        def _show(_w):
            _hide()
            state["timer"] = app.after(0.4, _open)

        f.on_enter(_show)
        f.on_leave(_hide)

    def _rename_fish(f: Fish) -> None:
        app.prompt(
            f"Rename your {f.species_name}",
            initial=f.display_name,
            on_submit=lambda new_name: setattr(
                f, "display_name", new_name.strip() or f.display_name
            ),
        )

    def _sell_fish(f: Fish) -> None:
        fish.remove(f)
        app.widgets.remove(f)
        _log_departure(f)
        clear_relationships(f, fish)
        state["money"] += f.sell_value
        _refresh_stats()
        app.toast(f"Sold {f.display_name} for ${f.sell_value}.", level="success")
        _unlock_achievement("first_sale")

    def _open_inspector(f: Fish) -> None:
        app.open_overlay(
            _build_inspector(
                app, f, _rename_fish, _sell_fish, state["treats"], _feed_treat
            ),
            close_on_click_outside=True,
        )

    def _sell_decoration(d: Decoration) -> None:
        decorations.remove(d)
        app.widgets.remove(d)
        # A fish whose favorite spot just got sold adopts a new one, rather
        # than being left pining after a decoration that no longer exists.
        for f in fish:
            if f.favorite_decoration is d:
                f.favorite_decoration = (
                    random.choice(decorations) if decorations else None
                )
        state["money"] += d.sell_value
        _refresh_stats()
        app.toast(f"Sold the {d.kind} for ${d.sell_value}.", level="success")

    def _open_decoration_inspector(d: Decoration) -> None:
        app.open_overlay(
            _build_decoration_inspector(
                app, d, fish, _sell_decoration, _enter_decoration
            ),
            close_on_click_outside=True,
        )

    def _enter_decoration(d: Decoration) -> None:
        # A lightweight poll rather than hooking every individual event
        # that can change who's home (the nightly wake transition, or the
        # rarer case of a housed fish starving) -- see _build_castle_interior's
        # docstring. on_close fires no matter how the overlay is dismissed
        # (Leave, click-outside, Esc), which is also true of _refresh()'s
        # own close-then-reopen when occupants change -- `rebuilding` tells
        # on_close apart from an actual "the player left" close, so the
        # poll only ever stops on the latter.
        interior = {"box": None, "occupants": None, "rebuilding": False}

        def _on_close(_widget):
            if interior["rebuilding"]:
                interior["rebuilding"] = False
                return
            app.cancel(timer)

        def _signature():
            # Identity, mood, *and* boop-flash state -- a fish waking but
            # lingering (still occupants_of()-eligible, see fish.py's
            # _awake_in_home) or mid-attempt (_just_booped_until) needs to
            # trigger a redraw too, not just someone actually arriving or
            # leaving.
            now = time.monotonic()
            return [
                (
                    o,
                    o._awake_in_home,
                    o._just_booped_until is not None and now < o._just_booped_until,
                )
                for o in occupants_of(d, fish)
            ]

        def _show():
            interior["occupants"] = _signature()
            interior["box"] = app.open_overlay(
                _build_castle_interior(app, d, fish, _open_dream),
                close_on_click_outside=True,
                on_close=_on_close,
            )

        def _refresh():
            if _signature() != interior["occupants"]:
                interior["rebuilding"] = True
                app.close_overlay(interior["box"])
                _show()

        timer = app.every(1.0, _refresh)
        _show()

    def _on_eat_food(food):
        app.widgets.remove(food)

    def _on_eat_fish(eaten):
        # fish.py's own predator-eats-prey code already does
        # fish_list.remove(target) right before calling this -- eaten is
        # never in `fish` by this point (see test_shark_eats_nearby_prey_
        # and_is_fed). A shark only ever hunts in the aquarium scene (a
        # forest-biome fish can't be reached -- see Fish.draw()'s early
        # forest-mode return), so `eaten` is always in aquarium_widgets.
        app.widgets.remove(eaten)
        _log_departure(eaten)
        clear_relationships(eaten, fish)
        app.toast(f"The shark ate {eaten.display_name}!", level="warning", icon="🦈")
        _refresh_stats()

    def _add_fish(species: Species) -> Fish:
        f = _make_fish(
            bounds,
            foods,
            fish,
            _on_eat_food,
            _on_eat_fish,
            species,
            decorations,
            mouse_pos,
            environment,
            paused,
        )
        fish.append(f)
        app.add(f)
        _wire_tooltip(f)
        _check_new_fish_achievements(f)
        return f

    def _seed_starter_aquarium() -> None:
        """Everything a brand-new aquarium starts with -- the same starter
        decorations/fish boot has always created, factored out so
        _return_to_main_menu()'s "New Aquarium" can genuinely start over
        mid-session instead of only being meaningful at launch."""
        for kind, x in (
            ("Plant", tank_x + 3),
            ("Driftwood", tank_x + tank_w // 3),
            ("Rock", tank_x + tank_w // 2),
            ("Castle", tank_x + max(tank_w - 10, tank_w * 4 // 5)),
        ):
            d = _make_starting_decoration(kind, x)
            decorations.append(d)
            app.add(d)
        for _ in range(3):
            _add_fish(random.choice(STARTER_SPECIES))
        _refresh_stats()

    _seed_starter_aquarium()

    def _spawn_fish(species: Species):
        # Only for purchases (see the Shop below) -- unlike the starter fish
        # above, a bought fish gets a confirmation toast and a naming prompt.
        f = _add_fish(species)
        _refresh_stats()
        if species.predator:
            app.toast(f"Bought a {species.name}! Watch out, fish...", level="warning")
        else:
            app.toast(f"Bought a {species.name}!", level="success")
        _rename_fish(f)

    def _stress_test():
        # Free, no rename prompt -- this is a dev/debug key for proving the
        # diff-renderer stays smooth with a lot of independently-moving
        # Fish widgets at once (see the module docstring), not a normal
        # gameplay action.
        added = 0
        while len(fish) < STRESS_TEST_TARGET:
            _add_fish(random.choice(STARTER_SPECIES))
            added += 1
        _refresh_stats()
        if added:
            app.toast(
                f"Stress test: spawned {added} more fish ({len(fish)} total).",
                level="info",
            )
        else:
            app.toast(
                f"Already at the stress-test cap ({STRESS_TEST_TARGET} fish).",
                level="info",
            )
        if len(fish) >= STRESS_TEST_TARGET:
            _unlock_achievement("full_house")

    def _buy_food():
        state["food"] += FOOD_PACK_SIZE
        state["food_spent_today"] += FOOD_PACK_PRICE
        _refresh_stats()
        app.toast(f"Bought {FOOD_PACK_SIZE} fish food!", level="success")

    def _buy_treat(item) -> None:
        state["treats"][item.kind] = state["treats"].get(item.kind, 0) + item.pack_size
        unit = "" if item.pack_size == 1 else f" x{item.pack_size}"
        app.toast(f"Bought {item.kind}{unit}.", level="success")

    def _treat_reaction(f: Fish, kind: str) -> None:
        # The flavor half of eating a treat -- toast/achievement/diary, no
        # inventory or hunger side effects. Shared by _feed_treat() (feed a
        # specific fish from the Inspector) and a dropped special food's
        # on_eaten hook (see _drop_special_food()), so both paths react
        # identically no matter how the treat reached the fish.
        if kind == "Pizza":
            # Universal delight, regardless of species or favorite --
            # matching Pizza's flavor text (see constants.TREAT_SHOP_ITEMS):
            # nobody has it as a declared favorite, everyone loves it anyway.
            app.toast(
                f"{f.display_name} devoured an entire {kind}. Nobody knows why.",
                level="success",
                icon="🍕",
            )
            _unlock_achievement("mystery_craving")
            _log_memory(f, "I ate pizza 🍕. It was delicious!")
        elif kind in f.favorite_foods:
            # Flavor only -- same feed() relief as any other treat, just a
            # nicer reaction. Personality, not a better stat stick.
            item = next(i for i in TREAT_SHOP_ITEMS if i.kind == kind)
            app.toast(
                f"{f.display_name} lights up at the {kind}! Favorite food.",
                level="success",
                icon=item.emoji,
            )
            _unlock_achievement("their_favorite")
            _log_memory(f, f"Ate my favorite: {kind} {item.emoji}.")
        else:
            app.toast(f"Fed {f.display_name} some {kind}.", level="success")

    def _feed_treat(f: Fish, kind: str) -> None:
        state["treats"][kind] -= 1
        f.hunger, f.health = feed(f.hunger, f.health)
        _treat_reaction(f, kind)
        _refresh_stats()

    def _drop_special_food(kind: str, x: float, y: float) -> Food:
        # Drop one piece of a special food (a treat kind) into the water at
        # (x, y). Unlike _feed_treat() it doesn't pick a fish or apply
        # relief itself: it's a real Food in the tank that whichever fish
        # reaches it eats (fish.py applies the feed()), and its on_eaten
        # hook then fires _treat_reaction() for that eater. Callers handle
        # any inventory accounting (the HUD dropdown) or skip it (the cheat
        # console's spawn()).
        item = next((i for i in TREAT_SHOP_ITEMS if i.kind == kind), None)
        glyph = item.emoji if item is not None else Food.GLYPH
        food = Food(x, y, glyph=glyph, kind=kind)

        def _eaten(eater: Fish) -> None:
            _treat_reaction(eater, kind)
            _refresh_stats()

        food.on_eaten = _eaten
        foods.append(food)
        app.add(food)
        return food

    def _add_decoration(item: DecorationItem) -> None:
        width = max(text_width(line) for line in item.art)
        x = random.uniform(tank_x + 1, max(tank_x + 1, tank_x + tank_w - 1 - width))
        d = Decoration(
            x,
            floor_y - len(item.art) + 1,
            item.art,
            item.colors,
            kind=item.kind,
            price=item.price,
            capacity=item.capacity,
        )
        decorations.append(d)
        # Insert right after the last existing Decoration (not app.add(),
        # which would append it *after* every already-added Fish -- new
        # decorations still need to draw behind all fish, matching every
        # decoration already in the tank; see the module docstring).
        insert_at = 0
        for i, w in enumerate(app.widgets):
            if isinstance(w, Decoration):
                insert_at = i + 1
        app.widgets.insert(insert_at, d)
        app.toast(f"Bought a {item.kind}!", level="success")

    def _snapshot() -> dict:
        """Convert live Widgets to plain JSON-friendly state."""
        fish_index = {id(f): i for i, f in enumerate(fish)}
        decoration_index = {id(d): i for i, d in enumerate(decorations)}
        return {
            "state": dict(state),
            "day": day_count["n"],
            "foods": [{"x": food.fx, "y": food.fy} for food in foods],
            "decorations": [
                {"kind": d.kind, "x": d.fx, "y": d.fy, "price": d.price}
                for d in decorations
            ],
            "fish": [
                {
                    "species": f.species_name,
                    "name": f.display_name,
                    "x": f.fx,
                    "y": f.fy,
                    "vx": f.vx,
                    "vy": f.vy,
                    "speed": f.speed,
                    "hunger": f.hunger,
                    "health": f.health,
                    "personality": f.personality,
                    "is_sleepy": f.is_sleepy,
                    "memory_log": list(f.memory_log),
                    "age_seconds": max(0.0, time.monotonic() - f.birth_time),
                    "favorite": decoration_index.get(id(f.favorite_decoration)),
                }
                for f in fish
            ],
            "relationships": [
                {
                    "a": fish_index[id(a)],
                    "b": fish_index[id(b)],
                    "score": rel.score,
                    "memories": list(rel.memories),
                }
                for a, b, rel in all_relationship_pairs(fish)
            ],
        }

    def _clear_tank() -> None:
        """Removes every fish/food/decoration widget and resets `state`/
        `day_count`/`current_save` back to defaults -- the common first
        half of both loading a save (_load_snapshot) and starting fresh
        mid-session (_return_to_main_menu()'s "New Aquarium"). Callers
        already guarantee the Forest isn't the active scene at this point
        (see _return_to_main_menu()) -- `app.widgets` here is always
        `aquarium_widgets`, but a fish could still be away in the Forest
        (or its Wood sitting there) when this runs, so those are cleaned
        up explicitly rather than assumed empty."""
        for widget in [*foods, *fish, *decorations]:
            if widget in app.widgets:
                app.widgets.remove(widget)
            if widget in forest_widgets:
                forest_widgets.remove(widget)
        for wood in forest_wood:
            if wood in forest_widgets:
                forest_widgets.remove(wood)
        if forest_shark["widget"] is not None:
            if forest_shark["widget"] in forest_widgets:
                forest_widgets.remove(forest_shark["widget"])
            forest_shark["widget"] = None
            forest_shark["until"] = None
        if forest_button in app.widgets:
            app.widgets.remove(forest_button)
        foods.clear()
        fish.clear()
        decorations.clear()
        forest_wood.clear()
        state.clear()
        state.update(
            {
                "money": 100,
                "food": 15,
                "food_spent_today": 0,
                "donations_today": 0,
                "welfare_enabled": True,
                "bubbles_enabled": True,
                "treats": {},
                "forest_unlocked": False,
            }
        )
        day_count["n"] = 0
        current_save["name"] = None

    def _load_snapshot(snapshot: dict) -> None:
        """Replace the tank from a validated save while retaining the UI.
        Deliberately doesn't restore which biome a fish was in or any Wood
        currently sitting in the Forest -- a fish mid-forage-trip at save
        time just resets to the aquarium on load, and Wood simply
        respawns over time; only whether the Forest itself is unlocked
        (state["forest_unlocked"], restored generically below like every
        other state flag) survives."""
        _clear_tank()
        state.update(snapshot.get("state", {}))
        if state.get("forest_unlocked") and forest_button not in aquarium_widgets:
            aquarium_widgets.append(forest_button)
        day_count["n"] = int(snapshot.get("day", 0))
        for saved in snapshot.get("decorations", []):
            item = DECORATION_CATALOG.get(saved.get("kind"))
            if item is None:
                continue
            d = Decoration(
                saved.get("x", tank_x + 1),
                saved.get("y", floor_y),
                item.art,
                item.colors,
                kind=item.kind,
                price=item.price,
                capacity=item.capacity,
            )
            decorations.append(d)
            app.add(d)
        for saved in snapshot.get("fish", []):
            species = next(
                (s for s in SHOP_ITEMS if s.name == saved.get("species")),
                STARTER_SPECIES[0],
            )
            f = Fish(
                saved.get("x", tank_x + 1),
                saved.get("y", tank_y + 1),
                bounds,
                foods,
                fish,
                _on_eat_food,
                _on_eat_fish,
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
            )
            f.display_name = saved.get("name", species.name)
            for attr in (
                "vx",
                "vy",
                "speed",
                "hunger",
                "health",
                "personality",
                "is_sleepy",
                "memory_log",
            ):
                if attr in saved:
                    setattr(f, attr, saved[attr])
            f.birth_time = time.monotonic() - max(0.0, saved.get("age_seconds", 0.0))
            fish.append(f)
            app.add(f)
            _wire_tooltip(f)
        for f, saved in zip(fish, snapshot.get("fish", [])):
            favorite = saved.get("favorite")
            f.favorite_decoration = (
                decorations[favorite]
                if isinstance(favorite, int) and 0 <= favorite < len(decorations)
                else None
            )
        for saved in snapshot.get("relationships", []):
            a_idx, b_idx = saved.get("a"), saved.get("b")
            if (
                not isinstance(a_idx, int)
                or not isinstance(b_idx, int)
                or not (0 <= a_idx < len(fish))
                or not (0 <= b_idx < len(fish))
            ):
                continue
            rel = set_relationship(fish[a_idx], fish[b_idx], saved.get("score", 0.0))
            rel.memories.extend(saved.get("memories", []))
        for saved in snapshot.get("foods", []):
            food = Food(saved.get("x", tank_x + 1), saved.get("y", tank_y + 1))
            foods.append(food)
            app.add(food)
        _refresh_stats()

    def _save_game() -> None:
        # Once attached to a save (loaded, or saved manually once already
        # this session), Save just writes back into it -- no prompt, no new
        # file every day. Only the very first save of a fresh session (never
        # loaded, never saved) asks for a name.
        if current_save["name"] is not None:
            _write_named_save(current_save["name"])
            return
        default_name = f"Aquarium Day {day_count['n']}"
        app.prompt(
            "Save aquarium as",
            initial=default_name,
            on_submit=lambda name: _write_named_save(name),
        )

    def _write_named_save(name: str) -> None:
        payload_path = write_save(name, _snapshot())
        current_save["name"] = name
        app.toast(f"Saved {payload_path.stem}.", level="success")
        if cloud["key"] is not None:
            # Fire-and-forget: the local save above already succeeded and
            # is what Load reads from, so a slow/failed cloud sync should
            # never block or roll back the (already-real) local save.
            app.run_worker(
                upload_cloud_save,
                cloud["key"],
                name,
                read_save(payload_path),
                on_result=lambda _r: app.toast("Synced to cloud.", level="success"),
                on_error=lambda _e: app.toast(
                    "Cloud sync failed -- saved locally only.", level="warning"
                ),
            )

    def _open_load_menu(on_loaded=None) -> None:
        cards = list_saves()

        def _load(path):
            try:
                payload = read_save(path)
                _load_snapshot(payload["aquarium"])
                current_save["name"] = payload["metadata"].get("name", path.stem)
                app.close_overlay(box)
                if on_loaded is not None:
                    on_loaded()
                app.toast(f"Loaded {path.stem}.", level="success")
            except (OSError, ValueError) as error:
                app.toast(f"Couldn't load save: {error}", level="error")

        def _rename(path, old_name, new_name):
            try:
                rename_save(path, new_name)
                if current_save["name"] == old_name:
                    current_save["name"] = new_name
                app.toast(f"Renamed to {new_name}.", level="success")
            except (OSError, ValueError) as error:
                app.toast(f"Couldn't rename: {error}", level="error")
            app.close_overlay(box)
            _open_load_menu(on_loaded)

        def _duplicate(path, new_name):
            try:
                duplicate_save(path, new_name)
                app.toast(f"Duplicated as {new_name}.", level="success")
            except (OSError, ValueError) as error:
                app.toast(f"Couldn't duplicate: {error}", level="error")
            app.close_overlay(box)
            _open_load_menu(on_loaded)

        def _delete(path, name):
            delete_save(path)
            if current_save["name"] == name:
                # The save this session was attached to is gone -- the next
                # Save should ask for a fresh name rather than silently
                # recreating the exact file just deleted.
                current_save["name"] = None
            app.toast(f"Deleted {name}.", level="success")
            app.close_overlay(box)
            _open_load_menu(on_loaded)

        box = build_save_menu(app, cards, _load, _rename, _duplicate, _delete)
        app.open_overlay(box, close_on_click_outside=True)

    def _open_shop():
        app.open_overlay(
            _build_shop(
                app,
                state,
                _spawn_fish,
                _buy_food,
                _add_decoration,
                _buy_treat,
                _unlock_forest,
            ),
            close_on_click_outside=True,
        )

    def _unlock_forest() -> None:
        state["forest_unlocked"] = True
        if forest_button not in aquarium_widgets:
            aquarium_widgets.append(forest_button)
        app.toast(
            "Forest unlocked! Hungry fish may now wander off to forage.",
            level="success",
            icon="🌲",
        )

    def _enter_forest() -> None:
        # The aquarium's own "Enter Forest" button (forest_button, in
        # aquarium_widgets) is a separate widget from the Forest scene's
        # own "Leave Forest" button (built into forest_widgets) -- since
        # each only ever exists in the scene you can reach it from, there's
        # no toggle-label bookkeeping needed on either one.
        if in_forest["value"]:
            return
        in_forest["value"] = True
        forest_stats_label.text = (
            f"Money: ${state['money']}   Wood in the forest: {len(forest_wood)}"
        )
        app.widgets = forest_widgets
        app.focus(None)
        app.invalidate()

    def _leave_forest() -> None:
        if not in_forest["value"]:
            return
        in_forest["value"] = False
        app.widgets = aquarium_widgets
        app.focus(None)
        app.invalidate()

    def _open_settings():
        def _setup_cloud():
            key = generate_cloud_key()
            cloud["key"] = key
            store_cloud_key(key)
            app.toast(
                f"Cloud Saves set up. Your key: {key} -- write it down, it's "
                "the only way to get your saves back on a new PC.",
                level="info",
                duration=8.0,
            )
            _unlock_achievement("backed_up")
            _open_settings()

        def _change_key():
            def _use_key(entered: str):
                entered = entered.strip()
                if not entered:
                    return
                cloud["key"] = entered
                store_cloud_key(entered)
                app.toast("Cloud Key updated.", level="success")
                _open_settings()

            app.prompt("Enter an existing Cloud Key", on_submit=_use_key)

        def _forget_key():
            def _yes():
                cloud["key"] = None
                store_cloud_key(None)
                app.toast(
                    "Cloud Key forgotten -- saves stay local only now.", level="info"
                )
                _open_settings()

            app.confirm(
                "Forget this Cloud Key? Local saves are untouched, but this "
                "machine won't sync to the cloud until you set one up again.",
                on_yes=_yes,
            )

        def _restore():
            key = cloud["key"]
            if key is None:
                return

            def _download(name: str) -> None:
                def _on_downloaded(payload):
                    write_save(name, payload["aquarium"])
                    app.toast(f"Downloaded {name} -- find it in Load.", level="success")

                app.run_worker(
                    download_cloud_save,
                    key,
                    name,
                    on_result=_on_downloaded,
                    on_error=lambda error: app.toast(
                        f"Couldn't download: {error}", level="error"
                    ),
                )

            def _on_listed(cloud_saves):
                app.open_overlay(
                    build_restore_menu(app, cloud_saves, _download),
                    close_on_click_outside=True,
                )

            app.run_worker(
                list_cloud_saves,
                key,
                on_result=_on_listed,
                on_error=lambda error: app.toast(
                    f"Couldn't reach the cloud: {error}", level="error"
                ),
            )

        app.open_overlay(
            _build_settings(
                app,
                state,
                cloud["key"],
                _setup_cloud,
                _change_key,
                _forget_key,
                _restore,
            ),
            close_on_click_outside=True,
        )

    def _open_help():
        app.open_overlay(build_help_menu(app), close_on_click_outside=True)

    # Representative day-fraction for each phase the console's set_time()
    # accepts -- midway through Morning/Day, and safely into Night (see
    # world.get_day_phase()'s NIGHT_START/NIGHT_END/MORNING_END bands).
    _PHASE_FRACTIONS = {"morning": 0.22, "day": 0.52, "night": 0.875}

    def _set_day_phase(phase: str) -> str:
        # Shift session_start so the derived day-fraction lands in the target
        # phase, then recompute immediately -- a real move of the same clock
        # _update_environment() reads every tick (aging/day_count run off a
        # separate app.every timer, so this never touches them). Letting the
        # normal transition side effects fire (dreams at dusk, the morning
        # vignette at dawn) is deliberate: a real effect, not a cheat-only path.
        nonlocal session_start
        key = str(phase).strip().lower()
        if key not in _PHASE_FRACTIONS:
            raise ValueError('Time must be "day", "morning", or "night".')
        session_start = time.monotonic() - _PHASE_FRACTIONS[key] * AGE_SECONDS_PER_DAY
        _update_environment()
        return environment["phase"]

    def _console_spawn_food(kind: str, amount: int):
        item = next(
            (i for i in TREAT_SHOP_ITEMS if i.kind.lower() == str(kind).lower()), None
        )
        if item is None:
            names = ", ".join(i.kind for i in TREAT_SHOP_ITEMS)
            raise ValueError(f"Unknown special food: {kind!r}. Try one of: {names}.")
        x0, y0, x1, y1 = bounds
        mx, my = mouse_pos["x"], mouse_pos["y"]
        at_mouse = (
            mx is not None and my is not None and x0 <= mx <= x1 and y0 <= my <= y1
        )
        for _ in range(amount):
            if at_mouse:
                x = min(x1, max(x0, mx + random.uniform(-2.0, 2.0)))
                y = min(y1, max(y0, my + random.uniform(-1.0, 1.0)))
            else:
                # No usable mouse position (console covers the screen, or the
                # cursor's outside the tank) -- scatter near the surface so
                # the food still lands where fish can reach it.
                x = random.uniform(x0, x1)
                y = random.uniform(y0, min(y1, y0 + 2.0))
            _drop_special_food(item.kind, x, y)
        return amount, item.kind

    def _give_nightmare(f: Fish) -> None:
        # A forced bad dream plus the real scare (wake, 😨 flash, and the
        # relocation-to-a-friend follow-up all play out via the normal
        # _process_nightmares() path afterward) -- see _trigger_nightmare_scare().
        f.dream = make_dream(f, "bad")
        _trigger_nightmare_scare(f)

    def _give_dream(f: Fish, category: str = None) -> str:
        key = (category or "happy").strip().lower()
        if key in ("bad", "reunion"):
            raise ValueError(
                "give_dream is for nice dreams -- use give_nightmare for a bad one."
            )
        f.dream = make_dream(f, key)  # raises ValueError on an unknown category
        _log_memory(f, f"I dreamed about {f.dream.title}. {f.dream.description}")
        return f.dream.title

    def _open_console():
        # A dev/testing tool (backtick key) -- built fresh each time so its
        # command registry always closes over the *current* fish/state,
        # never a stale snapshot from an earlier "New Aquarium".
        commands = build_console_commands(
            state=state,
            fish=fish,
            add_fish=_add_fish,
            spawn_fish=_spawn_fish,
            buy_food=_buy_food,
            buy_treat=_buy_treat,
            add_decoration=_add_decoration,
            refresh_stats=_refresh_stats,
            set_day_phase=_set_day_phase,
            spawn_food=_console_spawn_food,
            give_nightmare=_give_nightmare,
            give_dream=_give_dream,
        )
        console = CheatConsole(
            lambda text: run_console_command(commands, text), style=app.style
        )
        app.open_overlay(console, close_on_click_outside=True)

    def _open_start_menu(on_resume=None):
        # `on_resume` is only ever passed by _return_to_main_menu() (a real
        # mid-session reset is now possible -- see _new_aquarium below);
        # boot's own call leaves it None, exactly as before this existed.
        menu = None

        def _new_aquarium():
            _clear_tank()
            _seed_starter_aquarium()
            app.close_overlay(menu)

        def _load_save():
            _open_load_menu(lambda: app.close_overlay(menu))

        def _settings():
            _open_settings()

        def _help():
            _open_help()

        # Boot's call (on_resume=None) keeps today's exact behavior: no
        # Resume button, Esc/click-outside do nothing. Reached mid-session
        # via Ctrl+C, both dismiss it too -- on_close (fires no matter
        # which of Resume/Esc/click-outside/New/Load is what closes it)
        # is what actually unpauses, so all of them resume correctly.
        resumable = on_resume is not None
        menu = build_start_menu(
            app,
            _new_aquarium,
            _load_save,
            _settings,
            _help,
            on_resume,
            on_achievements=_open_achievements,
        )
        app.open_overlay(
            menu,
            close_on_escape=resumable,
            close_on_click_outside=resumable,
            on_close=(lambda _w: paused.update(value=False)) if resumable else None,
        )

    def _confirm_quit():
        app.confirm(
            "Quit without saving? Progress since your last save will be lost.",
            on_yes=lambda: app.quit(),
        )

    def _open_pause_menu():
        # Esc used to instantly quit the whole app -- a single accidental
        # keypress destroying an unsaved session. Now it pauses instead:
        # every Fish/BubbleField freezes solid (see their own `paused`
        # checks), and Quit lives behind this menu's own confirmation.
        paused["value"] = True
        box = None

        def _resume():
            app.close_overlay(box)

        box = build_pause_menu(
            app,
            on_resume=_resume,
            on_save=_save_game,
            on_settings=_open_settings,
            on_help=_open_help,
            on_quit=_confirm_quit,
            on_achievements=_open_achievements,
        )
        app.open_overlay(
            box,
            close_on_click_outside=True,
            on_close=lambda _w: paused.update(value=False),
        )

    app.add(Button(2, 2, "Open Shop").on_click(lambda _w: _open_shop()))
    app.add(Button(16, 2, "Settings").on_click(lambda _w: _open_settings()))
    app.add(Button(29, 2, "Save").on_click(lambda _w: _save_game()))
    app.add(Button(39, 2, "Load").on_click(lambda _w: _open_load_menu()))
    app.add(Button(49, 2, "Pause").on_click(lambda _w: _open_pause_menu()))

    def _on_treat_selected(kind: str) -> None:
        # The HUD's faster path for handing out treats: instead of opening
        # each fish's Inspector and feeding it there, pick a treat here and
        # it drops into the water for whoever reaches it first (same
        # _drop_special_food()/on_eaten reaction as the console's spawn(),
        # but this one spends from the treats you actually bought). Nothing
        # to drop -> a nudge toward the Shop rather than a silent no-op.
        if kind is None:
            return  # the leading "Drop treat…" hint row -- not a real choice
        have = state["treats"].get(kind, 0)
        if have <= 0:
            app.toast(f"No {kind} to drop -- buy some in the Shop.", level="warning")
            return
        state["treats"][kind] = have - 1
        x0, y0, x1, y1 = bounds
        _drop_special_food(
            kind, random.uniform(x0, x1), random.uniform(y0, min(y1, y0 + 2.0))
        )
        app.toast(f"Dropped a {kind} into the tank.", level="info")

    # A leading non-choice row makes the closed dropdown label itself the
    # affordance ("🍤 Drop treat…"), so no separate caption Label is needed.
    # It lives on the stats row (y=1), right-aligned to the terminal so it
    # sits in the free space past the stats readout and never runs off a
    # narrow screen (the label widths count an emoji as one char but it
    # renders two cells wide, hence the extra slack).
    _treat_items = [ListItem("🍤 Drop treat…", None)]
    _treat_items += [ListItem(f"{i.emoji} {i.kind}", i.kind) for i in TREAT_SHOP_ITEMS]
    _treat_dd_w = max(len(it.text) for it in _treat_items) + 7
    _treat_dropdown = Dropdown(max(2, app.cols - _treat_dd_w), 1, _treat_items)
    _treat_dropdown.on_select(_on_treat_selected)
    app.add(_treat_dropdown)
    app.on_key("s", lambda: _open_shop())
    app.on_key("S", lambda: _open_shop())
    app.on_key("g", lambda: _open_settings())
    app.on_key("G", lambda: _open_settings())
    app.on_key("p", lambda: _save_game())
    app.on_key("P", lambda: _save_game())
    app.on_key("l", lambda: _open_load_menu())
    app.on_key("L", lambda: _open_load_menu())
    app.on_key("h", lambda: _open_help())
    app.on_key("H", lambda: _open_help())
    app.on_key("z", lambda: _stress_test())
    app.on_key("Z", lambda: _stress_test())
    app.on_key("`", lambda: _open_console())

    def _on_mouse(event):
        if isinstance(event, MouseMove):
            mouse_pos["x"], mouse_pos["y"] = float(event.col), float(event.row)
            return False  # not consumed -- normal hover dispatch still runs (tooltips)
        if any(e.modal for e in app._overlays):
            return False  # a modal (Shop/Inspector/prompt) is open -- let it handle its own clicks
        if in_forest["value"]:
            # The Forest isn't read-only -- clicking a fish there opens the
            # exact same Inspector as in the tank -- but there's no water
            # to feed and no decorations to sell here (yet), so nothing
            # else in this handler applies.
            if isinstance(event, MouseClick) and event.btn == 0:
                forest_fish = [f for f in fish if f.biome == "forest"]
                clicked = fish_at(forest_fish, event.col, event.row)
                if clicked is not None:
                    _open_inspector(clicked)
                    return True
            return False
        if isinstance(event, MouseClick) and event.btn == 0:
            tank_fish = [f for f in fish if _in_tank(f)]
            clicked = fish_at(tank_fish, event.col, event.row)
            if clicked is not None:
                if clicked.dream is not None:
                    _open_dream(clicked)
                else:
                    _open_inspector(clicked)
                return True
            clicked_dec = decoration_at(decorations, event.col, event.row)
            if clicked_dec is not None:
                _open_decoration_inspector(clicked_dec)
                return True
            x0, y0, x1, y1 = bounds
            if x0 <= event.col <= x1 and y0 <= event.row <= y1:
                if state["food"] <= 0:
                    app.toast("Out of food -- visit the shop!", level="warning")
                    return True
                state["food"] -= 1
                food = Food(event.col, event.row)
                foods.append(food)
                app.add(food)
                _refresh_stats()
                return True
        return False

    app.on_mouse(_on_mouse)

    def _end_storm() -> None:
        environment["storm"] = False
        app.toast("The storm has ended. Clear skies again.", level="info", icon="🌤️")

    def _maybe_trigger_random_event() -> None:
        # Only ever chooses among currently-applicable events (rather than
        # rolling first and silently no-op'ing on a bad fit, e.g. a Storm
        # with no fish to rattle) -- no fallback/no-op branch needed.
        if random.random() >= RANDOM_EVENT_CHANCE:
            return
        candidates = ["lucky_find"]
        if fish:
            candidates.append("showing_off")
            if not environment["storm"]:  # never stack a second storm on a live one
                candidates.append("storm")
        if len(fish) < MAX_FISH_FOR_BREEDING:
            candidates.append("stray_fish")
        event = random.choice(candidates)

        if event == "stray_fish":
            species = random.choice(STARTER_SPECIES)
            f = _add_fish(species)
            app.toast(
                f"A stray {species.name} wandered in overnight and decided to "
                f"stay! Welcome, {f.display_name}.",
                level="info",
                icon="🐟",
                duration=6.0,
            )
            _log_memory(f, "I wandered in one night and decided to stay.")
        elif event == "storm":
            # A real, live weather state (not just a retroactive toast) --
            # environment["storm"] is shared with every Fish, so this frame
            # onward they steer for the nearest container and huddle there
            # (see fish.py's draw()) until _end_storm() clears it.
            environment["storm"] = True
            app.after(STORM_DURATION_SECONDS, _end_storm)
            for f in fish:
                f.hunger = min(100.0, f.hunger + STORM_HUNGER_BUMP)
                # A fish whose favorite spot is a real container gets the
                # cozier line -- approximate (favorite_decoration, not
                # tonight's actual sleeping_in, since this fires once per
                # day and sleeping_in has already reverted to None by then)
                # but a fair enough proxy for "usually has a home to shelter in".
                if (
                    f.favorite_decoration is not None
                    and f.favorite_decoration.is_container
                ):
                    _log_memory(
                        f,
                        f"A storm rolled through, but the "
                        f"{f.favorite_decoration.kind} kept me warm and dry.",
                    )
                else:
                    _log_memory(f, "Survived a rough storm last night.")
            app.toast(
                "A storm is rolling in! The fish are seeking shelter.",
                level="warning",
                icon="⛈️",
                duration=6.0,
            )
        elif event == "lucky_find":
            amount = random.randint(*LUCKY_FIND_RANGE)
            state["money"] += amount
            _refresh_stats()
            app.toast(
                f"Found some loose change in the gravel: +${amount}.",
                level="success",
                icon="🪙",
            )
        elif event == "showing_off":
            f = random.choice(fish)
            app.toast(
                f"{f.display_name} does a little spin, just because.",
                level="info",
                icon="✨",
            )
            _log_memory(f, "Did a little spin, just because.")

    def _check_emergency_welfare():
        if not should_grant_welfare(
            state["money"], state["food"], len(fish), state.get("welfare_enabled", True)
        ):
            return
        # A gift, not a purchase -- _add_fish() directly, skipping
        # _spawn_fish()'s "Bought a ..." toast and forced rename prompt,
        # so this reads as one clear message instead of a noisy pile-up.
        state["money"] += WELFARE_MONEY_GRANT
        state["food"] += WELFARE_FOOD_GRANT
        _add_fish(random.choice(STARTER_SPECIES))
        _refresh_stats()
        app.toast(
            "Aquarium Welfare: your aquarium fell on hard times -- here's a "
            f"fresh start. +1 Fish, +{WELFARE_FOOD_GRANT} Food, +${WELFARE_MONEY_GRANT}. Good luck.",
            level="info",
            icon="❤️",
            duration=6.0,
        )

    def _fire_morning_vignette():
        # A one-line Night -> Morning flavor toast for a Friend pair -- see
        # choose_morning_vignette()'s docstring for why this is cosmetic
        # texture, not a real per-fish wake-time simulation. "wake"/"resist"
        # also get a short in-tank caption right where the pair actually
        # are -- the toast is the headline, this is the cute moment.
        result = choose_morning_vignette(find_mutual_friend_pairs(fish))
        if result is None:
            return
        waker, sleeper, flavor = result

        def _add_vignette(wakes: bool) -> None:
            vignette = MorningVignette(
                (waker.fx + sleeper.fx) / 2,
                min(waker.fy, sleeper.fy) - 2,
                waker._glyph(),
                sleeper._glyph(),
                VIGNETTE_STYLE,
                wakes=wakes,
            )
            app.add(vignette)
            app.after(
                vignette.total_seconds,
                lambda: (
                    app.widgets.remove(vignette) if vignette in app.widgets else None
                ),
            )

        if flavor == "wake":
            app.toast(
                f"{waker.display_name} notices {sleeper.display_name} is still "
                f"asleep... *boop*... {sleeper.display_name} woke up!",
                level="info",
            )
            record_wake_up(waker, sleeper)
            _log_memory(sleeper, f"{waker.display_name} woke me up.")
            _log_memory(waker, f"I woke up {sleeper.display_name}.")
            _add_vignette(wakes=True)
        elif flavor == "resist":
            app.toast(
                f"{waker.display_name} tries to boop {sleeper.display_name} awake... "
                f"but {sleeper.display_name} is too sleepy to notice!",
                level="info",
            )
            _log_memory(
                waker,
                f"I tried to wake {sleeper.display_name} up, but they were too "
                "sleepy to notice.",
            )
            _add_vignette(wakes=False)
        else:
            app.toast(
                f"{waker.display_name} notices {sleeper.display_name} is still "
                f"asleep. {waker.display_name} leaves without them.",
                level="info",
            )

    def _check_night_events():
        # Relationship-building checks run once at the Night -> Morning
        # transition, alongside the vignette: pairs who ended up sleeping
        # together (a shared container, or just close on the floor), a
        # homeless fish whose nearest housed tankmate benefits from the
        # spot it didn't get, and (below) two already-unfriendly fish
        # forced into the same container anyway. All real,
        # currently-triggerable events -- see relationships.py's module
        # docstring for which interactions from the original design aren't
        # wired up yet (no mechanic exists for them today).
        counted_together = set()
        for a in fish:
            if not _in_tank(a):
                continue
            for b in fish:
                if a is b or not _in_tank(b):
                    continue
                key = frozenset((id(a), id(b)))
                if key in counted_together:
                    continue
                shares_container = (
                    a.sleeping_in is not None and a.sleeping_in is b.sleeping_in
                )
                floor_close = (
                    a.sleeping_in is None
                    and b.sleeping_in is None
                    and math.hypot(a.fx - b.fx, a.fy - b.fy) <= SLEEP_CLOSE_DISTANCE
                )
                if not (shares_container or floor_close):
                    continue
                counted_together.add(key)
                # Rivals actively sleep as far apart as the tank allows when
                # there's no container involved (see Fish.draw()), so this
                # only really happens for two who each independently reached
                # for a container and unluckily landed on the same one.
                already_unfriendly = (
                    shares_container
                    and get_relationship(a, b).score <= RELATIONSHIP_DISLIKE_THRESHOLD
                )
                if already_unfriendly:
                    pusher, pushed = random.sample([a, b], 2)
                    record_pushed_from_home(pusher, pushed)
                    _log_memory(
                        pushed,
                        f"{pusher.display_name} pushed me out of the "
                        f"{a.sleeping_in.kind}. I am angry.",
                    )
                else:
                    record_slept_together(a, b)
                    if floor_close:
                        _log_memory(
                            a,
                            "We watched the moon together tonight. Nobody said "
                            "anything. It was nice.",
                        )
                        _log_memory(
                            b,
                            "We watched the moon together tonight. Nobody said "
                            "anything. It was nice.",
                        )

        # Crowded-container flavor -- once per full container, not once per
        # pair sharing it (a Castle's capacity-4 room has up to 6 pairs).
        seen_containers = set()
        for f in fish:
            home = f.sleeping_in
            if home is None or id(home) in seen_containers:
                continue
            seen_containers.add(id(home))
            occupants = occupants_of(home, fish)
            if len(occupants) >= home.capacity:
                for guest in occupants:
                    _log_memory(
                        guest,
                        f"It was crowded in the {home.kind} last night. Nobody "
                        "complained.",
                    )

        # A solitary floor sleeper (no friend/rival pulling it anywhere)
        # settled near its own favorite non-container spot -- a quieter
        # counterpart to the shared-floor "watched the moon" memory above.
        for f in fish:
            if (
                _in_tank(f)
                and f.sleeping_in is None
                and f.friend is None
                and f.rival is None
                and f.favorite_decoration is not None
                and not f.favorite_decoration.is_container
            ):
                _log_memory(
                    f,
                    f"Slept near the {f.favorite_decoration.kind} floor tonight. "
                    "Peaceful.",
                )

        counted_gave_up = set()
        for f in fish:
            if not _in_tank(f) or f.sleeping_in is not None:
                continue
            housed_nearby = [
                o
                for o in fish
                if o is not f
                and o.sleeping_in is not None
                and math.hypot(o.fx - f.fx, o.fy - f.fy) <= RELATIONSHIP_NEARBY_RADIUS
            ]
            if not housed_nearby:
                continue
            beneficiary = min(
                housed_nearby, key=lambda o: math.hypot(o.fx - f.fx, o.fy - f.fy)
            )
            key = frozenset((id(f), id(beneficiary)))
            if key in counted_gave_up:
                continue
            counted_gave_up.add(key)
            record_gave_up_home(f, beneficiary)

    def _start_sleepy_holds():
        # Must run in this exact spot -- right at the Night->Morning
        # transition, before any fish's own draw() has processed the new
        # phase -- because a non-Sleepy tankmate's `sleeping_in` reverts to
        # None the instant its own next frame sees the phase change. One
        # tick later (_process_sleepy_holds, on the ordinary 1-second
        # timer) would already be too late to find who was actually
        # sleeping alongside a Sleepy fish overnight.
        for f in fish:
            if not f.is_sleepy or f.sleeping_in is None:
                continue
            f._holding_asleep = True
            f._held_since = time.monotonic()
            tankmates = [
                o for o in fish if o is not f and o.sleeping_in is f.sleeping_in
            ]
            waker, tier = find_eligible_waker(f, tankmates)
            if waker is not None:
                f._wake_waker = waker
                f._wake_threshold = roll_wake_threshold(tier)
                f._wake_next_attempt = time.monotonic() + WAKE_ATTEMPT_INTERVAL_SECONDS

    def _process_sleepy_holds():
        # The ongoing half, on the ordinary per-second tick: resolve an
        # attempt once its cooldown has passed, or force a wake once
        # SLEEPY_HOLD_MAX_SECONDS has passed regardless -- the fallback
        # that keeps "never permanently impossible" true even when
        # _start_sleepy_holds() found nobody eligible to try at all.
        now = time.monotonic()
        for f in fish:
            if not f._holding_asleep:
                continue
            if now - f._held_since >= SLEEPY_HOLD_MAX_SECONDS:
                f._holding_asleep = False
                continue
            waker = f._wake_waker
            if waker is None or waker not in fish or now < f._wake_next_attempt:
                continue
            # Every attempt actually happens visibly -- see BOOP_FLASH_SECONDS
            # -- resisted or not, not just the one that finally succeeds.
            waker._just_booped_until = now + BOOP_FLASH_SECONDS
            if resolve_wake_attempt(f._wake_attempts_used, f._wake_threshold):
                record_wake_up(waker, f)
                _log_memory(f, f"{waker.display_name} woke me up.")
                _log_memory(waker, f"I woke up {f.display_name}.")
                app.toast(
                    f"{waker.display_name} notices {f.display_name} is still "
                    f"asleep... *boop*... {f.display_name} woke up!",
                    level="info",
                )
                f._holding_asleep = False
            else:
                f._wake_attempts_used += 1
                f._wake_next_attempt = now + WAKE_ATTEMPT_INTERVAL_SECONDS

    def _release_home(f: Fish) -> None:
        # Shared by "starts traveling to the Forest" below and the
        # nightmare reaction -- a fish leaving the tank (for whatever
        # reason) can't keep holding a claimed container behind it.
        if f.sleeping_in is not None:
            f.fx, f.fy = f.sleeping_in.fx, f.sleeping_in.fy
            f.sleeping_in = None
        f._entered = False
        f._awake_in_home = False
        f._holding_asleep = False

    def _check_foraging() -> None:
        # Exploration Update Slice 1 -- entirely timer-driven (no per-frame
        # steering), so it's exactly as correct whether or not the Forest
        # happens to be the scene currently shown (see constants.py's
        # comment on FOREST_UNLOCK_PRICE). Order matters within one tick:
        # an arrival is resolved before that same fish is considered for
        # its *next* step (foraging fresh off the boat, heading home fresh
        # off a successful forage), so nothing waits a whole extra second
        # for something that already happened this tick.
        if not state.get("forest_unlocked"):
            return
        now = time.monotonic()

        # 1. Decide to travel (aquarium -> forest), once hungry enough --
        # personality-flavored (Phase 2): Shy opts out entirely (consistent
        # with Shy avoiding things elsewhere -- the mouse, taking a
        # container over company at night); Greedy/Explorer are eager, so
        # their own chance is boosted; a Friendly fish can additionally
        # join a Friend who's already heading out/there, regardless of its
        # own hunger ("Steve's going, I'll help").
        for f in fish:
            if not (_in_tank(f) and not f.is_predator):
                continue
            joined_friend = None
            goes = False
            if f.hunger >= HUNGER_WARNING_THRESHOLD and not (
                f.personality == "Shy" and FOREST_SHY_OPT_OUT
            ):
                chance = FOREST_TRAVEL_CHANCE_PER_CHECK
                if f.personality == "Greedy":
                    chance *= FOREST_GREEDY_CHANCE_MULT
                elif f.personality == "Explorer":
                    chance *= FOREST_EXPLORER_CHANCE_MULT
                goes = random.random() < chance
            if not goes and f.personality == "Friendly" and f.friend is not None:
                friend = f.friend
                friend_heading_out = (
                    friend.biome == "forest" or friend._travel_target == "forest"
                )
                if friend_heading_out and random.random() < FOREST_FRIEND_JOIN_CHANCE:
                    goes = True
                    joined_friend = friend
            if not goes:
                continue

            _release_home(f)
            if f in aquarium_widgets:
                aquarium_widgets.remove(f)
            f._travel_until = now + FOREST_TRAVEL_SECONDS
            f._travel_target = "forest"
            if joined_friend is not None:
                memory_line = f"{joined_friend.display_name}'s going. I'll help."
                toast_line = (
                    f"{f.display_name} joined {joined_friend.display_name} in "
                    "the forest."
                )
            elif f.personality == "Greedy":
                memory_line = "I'm hungry. I'm going."
                toast_line = f"{f.display_name} went looking for food in the forest."
            elif f.personality == "Explorer":
                memory_line = "The forest? I'm already halfway there."
                toast_line = f"{f.display_name} went looking for food in the forest."
            else:
                memory_line = "I went looking for food in the forest."
                toast_line = f"{f.display_name} went looking for food in the forest."
            _log_memory(f, memory_line)
            # Without this, a hungry fish leaving the tank is a silent
            # vanish -- easy to mistake for a shark kill or a crash,
            # especially if it happens right after the fish narrowly
            # survived one. Every other way a fish leaves the tank
            # (eaten, starved, old age) already toasts; departure to
            # forage should too.
            app.toast(toast_line, level="info", icon="🌲")

        # 2. Resolve arrivals (either direction).
        for f in fish:
            if f._travel_until is None or now < f._travel_until:
                continue
            destination = f._travel_target
            f._travel_until = None
            f._travel_target = None
            f.biome = destination
            if destination == "forest":
                fx0, fy0, fx1, fy1 = forest_bounds
                f.fx = random.uniform(fx0, fx1)
                f.fy = random.uniform(fy0, fy1)
                f.x, f.y = round(f.fx), round(f.fy)
                f._forest_arrived_at = now
                if f not in forest_widgets:
                    forest_widgets.append(f)
                # Friend collaboration (Phase 2): a shared diary entry (for
                # both) when their paths genuinely cross in the Forest,
                # rather than a full joint-travel state machine -- the
                # concrete, scoped version of "friend collaboration on
                # forage trips" from the Exploration Update vision.
                friend = f.friend
                if friend is not None and friend.biome == "forest":
                    _log_memory(
                        f,
                        f"I found {friend.display_name} in the forest. Glad I'm "
                        "not alone out here.",
                    )
                    _log_memory(
                        friend,
                        f"{f.display_name} found me in the forest. We looked "
                        "for wood together.",
                    )
                    app.toast(
                        f"{f.display_name} and {friend.display_name} are "
                        "exploring the forest together.",
                        level="info",
                        icon="🌲",
                    )
            else:
                f._forest_arrived_at = None
                if f in forest_widgets:
                    forest_widgets.remove(f)
                x0, y0, x1, y1 = bounds
                f.fx = random.uniform(x0, x1)
                f.fy = random.uniform(y0, y1)
                f.x, f.y = round(f.fx), round(f.fy)
                if f not in aquarium_widgets:
                    aquarium_widgets.append(f)
                if f.carrying == "Wood":
                    f.carrying = None
                    state["money"] += WOOD_SELL_PRICE
                    _refresh_stats()
                    _log_memory(f, "I brought back a piece of wood.")
                    app.toast(
                        f"{f.display_name} brought back a piece of wood. Sold "
                        f"for ${WOOD_SELL_PRICE}.",
                        level="success",
                        icon="🪵",
                    )

        # 3. Forage once actually in the Forest with nothing to carry yet.
        # The dwell-time gate keeps a fish visibly present for a beat
        # rather than potentially foraging on the very first check right
        # after it arrives. It doesn't head home immediately on a success --
        # it picks up the wood and lingers with it (step 3b), so the find
        # is actually seen and a Tiger Shark has a carrying fish to scare.
        for f in fish:
            if (
                f.biome == "forest"
                and f._travel_until is None
                and f.carrying is None
                and f._forest_arrived_at is not None
                and now - f._forest_arrived_at >= FOREST_MIN_DWELL_SECONDS
                and forest_wood
                and random.random() < FOREST_FORAGE_CHANCE_PER_CHECK
            ):
                wood = forest_wood.pop()
                if wood in forest_widgets:
                    forest_widgets.remove(wood)
                f.carrying = "Wood"
                # Reuse _forest_arrived_at as the linger clock now that
                # carrying is set (step 3b distinguishes the two phases by
                # `carrying`), rather than adding a third Forest timestamp.
                f._forest_arrived_at = now

        # 3b. A fish that's found its wood heads home once it's lingered
        # with it a moment (FOREST_CARRY_LINGER_SECONDS) -- deterministic,
        # not a roll, so it always makes the trip back. A Tiger Shark can
        # still catch it during this window (see _check_forest_danger()),
        # which is the whole point of the linger.
        for f in fish:
            if (
                f.biome == "forest"
                and f._travel_until is None
                and f.carrying == "Wood"
                and f._forest_arrived_at is not None
                and now - f._forest_arrived_at >= FOREST_CARRY_LINGER_SECONDS
            ):
                f._forest_arrived_at = None
                if f in forest_widgets:
                    forest_widgets.remove(f)
                f._travel_until = now + FOREST_TRAVEL_SECONDS
                f._travel_target = "aquarium"

        # 4. Wood slowly replenishes on its own.
        if (
            len(forest_wood) < WOOD_MAX_COUNT
            and random.random() < WOOD_SPAWN_CHANCE_PER_CHECK
        ):
            fx0, fy0, fx1, fy1 = forest_bounds
            item = Wood(random.uniform(fx0, fx1), random.uniform(fy0, fy1))
            forest_wood.append(item)
            forest_widgets.append(item)

    def _flee_from_tiger_shark(forest_fish, now: float) -> None:
        # Everyone in the Forest bolts for home the instant a Tiger Shark is
        # around -- dropping any Wood they were carrying right where they
        # stand (a carrying fish dropping its load to flee is the one
        # genuinely new detail of forage-danger). Nobody is ever caught:
        # this only ever sends fish home, never removes one. Diary lines
        # stay in the fish's innocent, cause-and-effect voice (they don't
        # grasp money -- see the Exploration Update vision's framing note),
        # and are logged in a second pass so a "we both ran" line can see
        # the whole fleeing group.
        dropped = set()
        for f in forest_fish:
            if f.carrying == "Wood":
                f.carrying = None
                item = Wood(f.fx, f.fy)
                forest_wood.append(item)
                forest_widgets.append(item)
                dropped.add(f)
            f._forest_arrived_at = None
            if f in forest_widgets:
                forest_widgets.remove(f)
            f._travel_until = now + FOREST_TRAVEL_SECONDS
            f._travel_target = "aquarium"

        fled = set(forest_fish)
        for f in forest_fish:
            friend = f.friend
            if friend is not None and friend in fled:
                _log_memory(
                    f,
                    f"{friend.display_name} and I ran from a huge fish. We both "
                    "made it home.",
                )
            elif f in dropped:
                _log_memory(
                    f,
                    "A huge fish appeared out of nowhere. I dropped my wood and "
                    "swam home.",
                )
            else:
                _log_memory(
                    f, "A huge fish chased me out of the forest. I made it home."
                )

        names = [f.display_name for f in forest_fish]
        shout = '"DROP THE LOG!" ' if dropped else ""
        if len(names) == 1:
            message = (
                f"{shout}A tiger shark spooked {names[0]} out of the forest. "
                "Safe, but no wood this time."
            )
        elif len(names) == 2:
            message = (
                f"{shout}A tiger shark! {names[0]} and {names[1]} bolted for "
                "home -- both made it back safe."
            )
        else:
            message = (
                f"{shout}A tiger shark scattered the foragers -- all "
                f"{len(names)} made it home safe."
            )
        app.toast(message, level="warning", icon="🦈")

    def _check_forest_danger() -> None:
        # Danger while foraging (Exploration Update vision): a Tiger Shark
        # can prowl into the Forest while fish are there. Unlike the tank's
        # own Shark it never eats -- it's a scare that sends every foraging
        # fish fleeing home (dropping any wood), and everyone survives.
        # Entirely timer/state-driven like the rest of the Forest, so it
        # stays correct regardless of which scene is currently shown.
        if not state.get("forest_unlocked"):
            return
        now = time.monotonic()

        if forest_shark["widget"] is None:
            # A shark only ever appears when there's actually someone to
            # menace (never prowls an empty forest) and none is already
            # visiting.
            present = [
                f
                for f in fish
                if f.biome == "forest" and f._travel_until is None and not f.is_predator
            ]
            if not present:
                return
            if random.random() >= TIGER_SHARK_APPEAR_CHANCE_PER_CHECK:
                return
            fx0, fy0, fx1, fy1 = forest_bounds
            from_left = random.random() < 0.5
            start_x, vx = (
                (fx0, TIGER_SHARK_SPEED) if from_left else (fx1, -TIGER_SHARK_SPEED)
            )
            shark = TigerShark(
                start_x, random.uniform(fy0, fy1), vx, lambda: paused["value"]
            )
            forest_shark["widget"] = shark
            forest_shark["until"] = now + TIGER_SHARK_STAY_SECONDS
            forest_widgets.append(shark)
        elif now >= forest_shark["until"]:
            # Visit's over -- it swims off and the Forest is safe again.
            if forest_shark["widget"] in forest_widgets:
                forest_widgets.remove(forest_shark["widget"])
            forest_shark["widget"] = None
            forest_shark["until"] = None
            return

        # While the shark is present nobody just stands there -- flee the
        # fish that were here when it arrived plus any that blunder in
        # mid-visit (an already-fleeing fish has _travel_until set, so it's
        # excluded here and never re-toasted).
        present = [
            f
            for f in fish
            if f.biome == "forest" and f._travel_until is None and not f.is_predator
        ]
        if present:
            _flee_from_tiger_shark(present, now)

    def _check_shark_scares() -> None:
        # Fills in relationships.py's long-noted gap ("protecting from a
        # shark" was never a real mechanic) -- every non-predator fish
        # within SHARK_SCARE_RADIUS of a Shark counts as scared, once per
        # approach (Fish._shark_scare_active is the rising-edge guard, reset
        # the moment it drifts back out of range so a later approach can
        # fire again). A sleeping fish doesn't consciously experience fear
        # or get "saved" -- Fish.draw()'s own sleeping condition applies
        # regardless of a Shark's hunting, so a housed/floor sleeper can
        # genuinely sleep right through a close call.
        sharks = [f for f in fish if f.is_predator]
        if not sharks:
            return
        for f in fish:
            if f.is_predator or f.biome != "aquarium" or f._entered:
                # _entered covers both a fish already asleep in a container
                # and one already hiding from this very Shark -- either way
                # it's already safe and shouldn't be re-evaluated here.
                continue
            near_shark = any(
                math.hypot(f.fx - s.fx, f.fy - s.fy) <= SHARK_SCARE_RADIUS
                for s in sharks
            )
            if not near_shark:
                f._shark_scare_active = False
                continue
            if f._shark_scare_active:
                continue
            f._shark_scare_active = True
            asleep = (
                environment["phase"] == "Night" and f.hunger <= SLEEP_HUNGER_THRESHOLD
            )
            if asleep:
                _log_memory(f, "Slept through a shark getting close. Impressive.")
                continue
            shelter = f._nearest_container_with_room()
            if shelter is not None:
                # Hiding beats a rescue -- draw()'s new _hiding_in branch
                # takes it from here (steer to the shelter, then invisible
                # and safe once it arrives, same as sleeping in a
                # container). No same-tick rescuer race to worry about.
                f._hiding_in = shelter
                _log_memory(f, f"I hid in the {shelter.kind} until the shark passed.")
                continue
            rescuer = next(
                (
                    o
                    for o in fish
                    if o is not f
                    and not o.is_predator
                    and math.hypot(o.fx - f.fx, o.fy - f.fy) <= SHARK_RESCUE_RADIUS
                    and get_relationship(f, o).score >= RELATIONSHIP_FRIEND_THRESHOLD
                ),
                None,
            )
            if rescuer is not None:
                record_saved_from_shark(rescuer, f)
                _log_memory(f, f"{rescuer.display_name} saved me from a shark!")
                _log_memory(rescuer, f"I saved {f.display_name} from a shark!")
            else:
                _log_memory(
                    f,
                    random.choice(
                        [
                            "I heard the alarm. I've never swum that fast before.",
                            "The shark looked right at me. I still remember its "
                            "eyes.",
                            "I narrowly escaped a shark. That was close!",
                        ]
                    ),
                )

    def _trigger_nightmare_scare(f: Fish) -> None:
        # Phase 1: the scare itself. The fish stays exactly where it is
        # (still tucked into its claimed home, if any) for
        # NIGHTMARE_SCARE_FLASH_SECONDS while the 😨 mood shows -- see
        # _trigger_nightmare_relocation() for the actual early wake.
        dream = f.dream
        now = time.monotonic()
        f._nightmare_wake_at = None
        f._just_scared_until = now + NIGHTMARE_SCARE_FLASH_SECONDS
        f._nightmare_relocate_at = now + NIGHTMARE_SCARE_FLASH_SECONDS
        _log_memory(f, f"I had a nightmare about {dream.title}. I woke up scared.")
        app.toast(
            f"{f.display_name} had a nightmare about {dream.title} and woke "
            "up scared!",
            level="warning",
            icon="😨",
        )
        f.dream = None

    def _trigger_nightmare_relocation(f: Fish) -> None:
        # Phase 2, NIGHTMARE_SCARE_FLASH_SECONDS after the scare: the
        # actual early, solo wake and (if there's a Friend) the quiet
        # relocation to sleep beside them. Reuses Fish.draw()'s existing
        # housing/floor-settle steering entirely unchanged -- setting
        # sleeping_in (or leaving it None with a Friend present) is all
        # that's needed; no new movement code.
        f._nightmare_relocate_at = None
        old_home = f.sleeping_in
        if old_home is not None:
            f.fx, f.fy = old_home.fx, old_home.fy
            f.sleeping_in = None
            f._entered = False
            f._awake_in_home = False
        friend = f.friend
        if friend is None:
            return  # simply settles back to sleep on its own, no relocation
        friend_home = friend.sleeping_in
        if friend_home is not None and len(occupants_of(friend_home, fish)) < (
            friend_home.capacity
        ):
            f.sleeping_in = friend_home  # go straight there, room to spare
        # else: leave sleeping_in None -- Fish.draw()'s own floor-settle
        # logic already steers toward a Friend when unhoused, whether the
        # friend is floor-sleeping or its container simply has no room left.
        f._seeking_friend_after_nightmare = True

    def _process_nightmares() -> None:
        now = time.monotonic()
        for f in fish:
            if f._nightmare_wake_at is not None and now >= f._nightmare_wake_at:
                _trigger_nightmare_scare(f)
            if f._nightmare_relocate_at is not None and now >= f._nightmare_relocate_at:
                _trigger_nightmare_relocation(f)
            if f._seeking_friend_after_nightmare:
                friend = f.friend
                arrived = f._entered or (
                    friend is not None
                    and f.sleeping_in is None
                    and math.hypot(f.fx - friend.fx, f.fy - friend.fy)
                    <= SLEEP_CLOSE_DISTANCE
                )
                if arrived:
                    f._seeking_friend_after_nightmare = False
                    f._nightmare_comfort_until = now + NIGHTMARE_COMFORT_FLASH_SECONDS
                    _log_memory(
                        f,
                        f"I quietly went to sleep beside {friend.display_name} "
                        "after a bad dream.",
                    )
                    app.toast(
                        f"{f.display_name} quietly went to sleep beside "
                        f"{friend.display_name}.",
                        level="info",
                        icon="🥺",
                    )

    def _assign_dreams() -> None:
        # Rolled once per fish, right as Night begins -- not every sleeper,
        # every night: "ooh, Steve is dreaming tonight" should read as a
        # notice-worthy exception (see constants.DREAM_CHANCE). Mirrors the
        # same hunger gate Fish.draw() itself uses to decide `sleeping` at
        # the start of a fresh Night (the `_holding_asleep` half of that
        # condition doesn't apply yet this early) -- including excluding
        # predators, which never sleep at all (see Fish.draw()'s own
        # `sleeping` computation for why a Shark shouldn't get a bedtime
        # story either) and a fish currently away in the Forest, or
        # mid-transit -- it isn't asleep in the tank, so nothing to dream
        # about there tonight.
        for f in fish:
            if (
                not f.is_predator
                and _in_tank(f)
                and f.hunger <= SLEEP_HUNGER_THRESHOLD
                and random.random() < DREAM_CHANCE
            ):
                f.dream = choose_dream(f)
                _log_memory(
                    f, f"I dreamed about {f.dream.title}. {f.dream.description}"
                )
                if f.dream.category == "bad":
                    # A nightmare forces a real, early, solo wake -- see
                    # _process_nightmares(), on the per-second tick.
                    f._nightmare_wake_at = (
                        time.monotonic() + NIGHTMARE_WAKE_DELAY_SECONDS
                    )

    def _update_environment():
        previous_phase = environment["phase"]
        fraction = compute_time_of_day(
            time.monotonic() - session_start, AGE_SECONDS_PER_DAY
        )
        environment["phase"] = get_day_phase(fraction)
        environment["temperature"] = compute_water_temperature(fraction)
        app.style.bg = lerp_color(DAY_BG, NIGHT_BG, night_blend(fraction))
        if previous_phase == "Night" and environment["phase"] == "Morning":
            _check_night_events()
            _fire_morning_vignette()
            _start_sleepy_holds()
        elif previous_phase != "Night" and environment["phase"] == "Night":
            _assign_dreams()

    def _hunger_step() -> float:
        # Night: sleeping fish get hungry slower. Heat: a stressed fish
        # burns through energy faster. Both are independent of each other
        # and of Lazy/Greedy/etc, which act on speed, not hunger.
        step = HUNGER_STEP
        if environment["phase"] == "Night":
            step *= NIGHT_HUNGER_MULT
        if environment["temperature"] > HOT_TEMP_THRESHOLD:
            step *= HOT_HUNGER_MULT
        return step

    def _per_second_tick():
        if paused["value"]:
            return  # environment/hunger/breeding all frozen while paused
        _update_environment()
        hunger_step = _hunger_step()
        dead = []
        for f in fish:
            f.hunger, f.health = decay_hunger(
                f.hunger, f.health, hunger_step=hunger_step
            )
            if f.health <= 0:
                dead.append(f)
        for f in dead:
            fish.remove(f)
            # Not necessarily in app.widgets right now -- e.g. away in the
            # Forest, or mid-travel there -- so check both persistent
            # scene lists rather than assuming which one currently holds it.
            if f in aquarium_widgets:
                aquarium_widgets.remove(f)
            if f in forest_widgets:
                forest_widgets.remove(f)
            _log_departure(f)
            clear_relationships(f, fish)
            app.toast(f"{f.display_name} starved to death...", level="error", icon="💀")
        _refresh_stats()
        hungry_levels = [f.hunger for f in fish]
        if should_warn_hungry(hungry_levels, hungry_warning_active["value"]):
            hungry_warning_active["value"] = True
            hungry_names = [
                f.display_name for f in fish if f.hunger > HUNGER_WARNING_THRESHOLD
            ]
            message = (
                f"{hungry_names[0]} is getting hungry!"
                if len(hungry_names) == 1
                else f"{len(hungry_names)} fish are getting hungry!"
            )
            app.toast(message, level="warning", icon="⚠️", duration=5.0)
        elif not any(level > HUNGER_WARNING_THRESHOLD for level in hungry_levels):
            # Back under the threshold -- rearm the one-shot warning so it
            # can fire again next time hunger climbs, instead of staying
            # permanently latched from the first warning of the session.
            hungry_warning_active["value"] = False
        _check_emergency_welfare()
        _process_sleepy_holds()
        _check_shark_scares()
        _process_nightmares()
        _check_foraging()
        _check_forest_danger()

        # Visitor donations pay out the moment they happen instead of being
        # bundled into the once-a-day summary -- see roll_visitor_donation()
        # for why this fires at roughly the same daily rate as before.
        attractiveness = compute_attractiveness(fish, decorations, foods)
        visitors = attractiveness // VISITORS_PER_ATTRACTIVENESS
        donation = roll_visitor_donation(visitors)
        if donation:
            state["money"] += donation
            state["donations_today"] += donation
            _refresh_stats()
            app.toast(f"A visitor donated ${donation}!", level="info")

    def _try_breeding():
        if len(fish) >= MAX_FISH_FOR_BREEDING:
            return
        for parent_a, parent_b in find_breeding_pairs(fish):
            if len(fish) >= MAX_FISH_FOR_BREEDING:
                break
            if random.random() >= BREED_CHANCE:
                continue
            species_name = choose_baby_species_name(parent_a, parent_b)
            species = next(s for s in SHOP_ITEMS if s.name == species_name)
            baby_x = (parent_a.fx + parent_b.fx) / 2
            baby_y = (parent_a.fy + parent_b.fy) / 2
            baby = Fish(
                baby_x,
                baby_y,
                bounds,
                foods,
                fish,
                _on_eat_food,
                _on_eat_fish,
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
            fish.append(baby)
            app.add(baby)
            _wire_tooltip(baby)
            _check_new_fish_achievements(baby)
            app.toast(
                f"{parent_a.display_name} and {parent_b.display_name} had a baby! "
                f"Welcome, {baby.display_name}.",
                level="success",
                icon="👶",
            )
            _unlock_achievement("first_baby")
            _log_memory(
                parent_a,
                f"Me and {parent_b.display_name} had a baby, {baby.display_name}! "
                "I love them.",
            )
            _log_memory(
                parent_b,
                f"Me and {parent_a.display_name} had a baby, {baby.display_name}! "
                "I love them.",
            )
            _log_memory(baby, "I was born today.")
        _refresh_stats()

    def _relationship_tier(score: float) -> str:
        if score <= RELATIONSHIP_RIVAL_THRESHOLD:
            return "rival"
        if score >= RELATIONSHIP_FRIEND_THRESHOLD:
            return "friend"
        return "neutral"

    def _check_milestone_achievements() -> None:
        # A plain once-a-day scan rather than hooking every interaction
        # site directly -- a toast landing up to a day "late" is fine for
        # flavor text, and this keeps achievement-awareness out of the hot
        # per-second tick and out of fish.py/relationships.py entirely.
        if day_count["n"] >= 7:
            _unlock_achievement("one_week_in")
        if any(f.sleeping_in is not None for f in fish):
            _unlock_achievement("tucked_in")
        for f in fish:
            if f.growth_stage == "Elder" and id(f) not in elder_announced:
                elder_announced.add(id(f))
                _unlock_achievement("golden_years")
                _log_memory(
                    f, "I'm getting older now, but I still feel young at heart."
                )
        for a, b, rel in all_relationship_pairs(fish):
            if rel.score >= RELATIONSHIP_FRIEND_THRESHOLD:
                _unlock_achievement("first_friend")
            if rel.score >= RELATIONSHIP_BEST_FRIEND_THRESHOLD:
                _unlock_achievement("best_friends")

            key = frozenset((id(a), id(b)))
            tier = _relationship_tier(rel.score)
            previous = relationship_tier_seen.get(key)
            if tier != previous:
                if tier == "friend":
                    _log_memory(a, f"I became friends with {b.display_name}.")
                    _log_memory(b, f"I became friends with {a.display_name}.")
                elif tier == "rival":
                    _log_memory(a, f"I became rivals with {b.display_name}.")
                    _log_memory(b, f"I became rivals with {a.display_name}.")
                relationship_tier_seen[key] = tier

    def _check_natural_deaths() -> None:
        # Once a day, per Elder fish -- see constants.NATURAL_DEATH_CHANCE_PER_DAY.
        # Same remove/log/clear/toast shape as _sell_fish/_on_eat_fish/the
        # starvation-death loop, just with its own calm cause line rather
        # than the "sold"/"eaten"/"starved" toasts those use.
        dying = [
            f
            for f in fish
            if f.growth_stage == "Elder"
            and random.random() < NATURAL_DEATH_CHANCE_PER_DAY
        ]
        for f in dying:
            fish.remove(f)
            # Not necessarily in app.widgets right now -- e.g. away in the
            # Forest, or mid-travel there -- so check both persistent
            # scene lists rather than assuming which one currently holds it.
            if f in aquarium_widgets:
                aquarium_widgets.remove(f)
            if f in forest_widgets:
                forest_widgets.remove(f)
            _log_departure(f, cause="{name} passed peacefully in old age.")
            clear_relationships(f, fish)
            app.toast(
                f"{f.display_name} passed peacefully in old age.",
                level="info",
                icon="🧓",
            )

    def _daily_tick():
        if paused["value"]:
            return
        day_count["n"] += 1
        decay_relationships(fish)
        _check_milestone_achievements()
        _check_natural_deaths()
        _try_breeding()
        _maybe_trigger_random_event()
        attractiveness = compute_attractiveness(fish, decorations, foods)
        # Donations were already paid out (and toasted) second by second in
        # _per_second_tick as they happened -- only ticket sales and the
        # maintenance grant are new money here. `donations` is still read
        # from state for the summary below, then reset for the next day.
        visitors, ticket_sales, _donations = compute_visitor_income(attractiveness)
        grant = MAINTENANCE_GRANT
        food_expense = state["food_spent_today"]
        donations = state["donations_today"]
        state["food_spent_today"] = 0
        state["donations_today"] = 0
        state["money"] += ticket_sales + grant
        net = ticket_sales + donations + grant - food_expense
        _refresh_stats()

        box = _build_daily_summary(
            app.style,
            day_count["n"],
            visitors,
            ticket_sales,
            donations,
            grant,
            food_expense,
            net,
        )
        app.open_overlay(
            box, modal=False, dim=False, center=True, close_on_escape=False
        )
        app.after(6.0, lambda: app.close_overlay(box))

    app.every(1.0, _per_second_tick)
    app.every(AGE_SECONDS_PER_DAY, _daily_tick)

    def _return_to_main_menu():
        # Ctrl+C reaches here even through a modal (see cozy_tui's
        # App._handle_ctrl_c()) -- close whatever's currently stacked
        # first (there's no public "close everything", so this loops the
        # ordinary "close the topmost" call), same as the Pause Menu,
        # pause the simulation so nothing keeps aging/starving behind the
        # menu, and unpause via open_overlay's own on_close hook so
        # Resume, Esc, and click-outside all correctly resume regardless
        # of which one is used.
        while app._overlays:
            app.close_overlay()
        if in_forest["value"]:
            # Ctrl+C reaches here even from inside the Forest (a global key
            # binding, not tied to which scene is currently shown) -- back
            # to the aquarium's own widget list first, so New Aquarium/Load
            # right after this don't add the fresh tank's fish/decorations
            # into the Forest scene by mistake.
            _leave_forest()
        paused["value"] = True
        # The menu is the only overlay open at this point, so closing
        # "the topmost" (no widget arg needed) always means this one.
        _open_start_menu(on_resume=lambda: app.close_overlay())

    app.on_key(Key.ESC, lambda: _open_pause_menu())
    app.on_key(Key.CTRL_C, _return_to_main_menu)
    _open_start_menu()
    app.run()


if __name__ == "__main__":
    main()
