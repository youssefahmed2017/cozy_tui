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
from cozy_tui.widgets import Box, Button, Label

from examples.aquarium.termquarium.bubbles import BubbleField, _Bubble, rise_bubble
from examples.aquarium.termquarium.constants import *
from examples.aquarium.termquarium.economy import (
    compute_attractiveness,
    compute_visitor_income,
    decay_hunger,
    feed,
    should_grant_welfare,
    should_warn_hungry,
)
from examples.aquarium.termquarium.fish import Fish, _make_fish, describe_fish, fish_at
from examples.aquarium.termquarium.inspectors import (
    _build_daily_summary,
    _build_decoration_inspector,
    _build_inspector,
    _build_settings,
)
from examples.aquarium.termquarium.relationships import (
    choose_baby_species_name,
    clear_relationships,
    find_breeding_pairs,
    form_relationship,
    random_personality,
)
from examples.aquarium.termquarium.save import list_saves, read_save, write_save
from examples.aquarium.termquarium.shop import build_shop as _build_shop
from examples.aquarium.termquarium.steering import (
    avoid_decorations,
    nearest_index,
    random_velocity,
    school_velocity,
    steer,
    steer_away_from,
    steer_toward_food,
)
from examples.aquarium.termquarium.styles import (
    BUBBLE_STYLE,
    FOOD_STYLE,
    HEART_STYLE,
    MUTED,
    STATS,
    TITLE,
    WATER_LINE,
)
from examples.aquarium.termquarium.tank_objects import Decoration, Food, decoration_at
from examples.aquarium.termquarium.ui import (
    build_help_menu,
    build_save_menu,
    build_start_menu,
)
from examples.aquarium.termquarium.world import (
    compute_time_of_day,
    compute_water_temperature,
    get_day_phase,
    night_blend,
)


def main() -> None:
    app = App(full=True, style=Style(fg="white", bg="black"), title="TermQuarium")
    app.tick_interval = 0.05  # continuous redraws; each Fish gates its own dt

    app.add(
        Label(
            2,
            0,
            "TermQuarium -- click to feed, S: shop, G: settings, P: save, L: load, "
            "Z: stress test, Esc: quit",
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
    state = {
        "money": 120,
        "food": 15,
        "food_spent_today": 0,
        "welfare_enabled": True,
        "bubbles_enabled": True,
    }
    hungry_warning_active = {"value": False}
    day_count = {"n": 0}
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
    app.add(BubbleField(bounds, lambda: state["bubbles_enabled"]))

    def _make_starting_decoration(kind: str, x) -> Decoration:
        item = DECORATION_CATALOG[kind]
        return Decoration(
            x,
            floor_y - len(item.art) + 1,
            item.art,
            item.colors,
            kind=kind,
            price=item.price,
        )

    decorations = [
        _make_starting_decoration("Plant", tank_x + 3),
        _make_starting_decoration("Driftwood", tank_x + tank_w // 3),
        _make_starting_decoration("Rock", tank_x + tank_w // 2),
        _make_starting_decoration("Castle", tank_x + max(tank_w - 10, tank_w * 4 // 5)),
    ]
    for d in decorations:
        app.add(d)

    PHASE_ICON = {"Day": "☀️", "Morning": "🌅", "Night": "🌙"}

    def _refresh_stats():
        icon = PHASE_ICON.get(environment["phase"], "☀️")
        stats.text = (
            f"Money: ${state['money']}   Food: {state['food']}   Fish: {len(fish)}"
            f"   {icon} {environment['phase']}, {environment['temperature']:.0f}°C"
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
        clear_relationships(f, fish)
        state["money"] += f.sell_value
        _refresh_stats()
        app.toast(f"Sold {f.display_name} for ${f.sell_value}.", level="success")

    def _open_inspector(f: Fish) -> None:
        app.open_overlay(
            _build_inspector(app, f, _rename_fish, _sell_fish),
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
            _build_decoration_inspector(app, d, _sell_decoration),
            close_on_click_outside=True,
        )

    def _on_eat_food(food):
        app.widgets.remove(food)

    def _on_eat_fish(eaten):
        app.widgets.remove(eaten)
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
        )
        fish.append(f)
        app.add(f)
        _wire_tooltip(f)
        form_relationship(f, fish)
        return f

    for _ in range(3):
        _add_fish(random.choice(STARTER_SPECIES))
    _refresh_stats()

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

    def _buy_food():
        state["food"] += FOOD_PACK_SIZE
        state["food_spent_today"] += FOOD_PACK_PRICE
        _refresh_stats()
        app.toast(f"Bought {FOOD_PACK_SIZE} fish food!", level="success")

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
                    "age_seconds": max(0.0, time.monotonic() - f.birth_time),
                    "favorite": decoration_index.get(id(f.favorite_decoration)),
                    "friend": fish_index.get(id(f.friend)),
                    "rival": fish_index.get(id(f.rival)),
                }
                for f in fish
            ],
        }

    def _load_snapshot(snapshot: dict) -> None:
        """Replace the tank from a validated save while retaining the UI."""
        for widget in [*foods, *fish, *decorations]:
            if widget in app.widgets:
                app.widgets.remove(widget)
        foods.clear()
        fish.clear()
        decorations.clear()
        state.clear()
        state.update(
            {"money": 120, "food": 15, "food_spent_today": 0, "welfare_enabled": True}
        )
        state.update(snapshot.get("state", {}))
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
            )
            f.display_name = saved.get("name", species.name)
            for attr in ("vx", "vy", "speed", "hunger", "health", "personality"):
                if attr in saved:
                    setattr(f, attr, saved[attr])
            f.birth_time = time.monotonic() - max(0.0, saved.get("age_seconds", 0.0))
            fish.append(f)
            app.add(f)
            _wire_tooltip(f)
        for f, saved in zip(fish, snapshot.get("fish", [])):
            favorite = saved.get("favorite")
            friend = saved.get("friend")
            rival = saved.get("rival")
            f.favorite_decoration = (
                decorations[favorite]
                if isinstance(favorite, int) and 0 <= favorite < len(decorations)
                else None
            )
            f.friend = (
                fish[friend]
                if isinstance(friend, int) and 0 <= friend < len(fish)
                else None
            )
            f.rival = (
                fish[rival]
                if isinstance(rival, int) and 0 <= rival < len(fish)
                else None
            )
        for saved in snapshot.get("foods", []):
            food = Food(saved.get("x", tank_x + 1), saved.get("y", tank_y + 1))
            foods.append(food)
            app.add(food)
        _refresh_stats()

    def _save_game() -> None:
        default_name = f"Aquarium Day {day_count['n']}"
        app.prompt(
            "Save aquarium as",
            initial=default_name,
            on_submit=lambda name: _write_named_save(name),
        )

    def _write_named_save(name: str) -> None:
        path = write_save(name, _snapshot())
        app.toast(f"Saved {path.stem}.", level="success")

    def _open_load_menu(on_loaded=None) -> None:
        cards = list_saves()

        def _load(path):
            try:
                _load_snapshot(read_save(path)["aquarium"])
                app.close_overlay(box)
                if on_loaded is not None:
                    on_loaded()
                app.toast(f"Loaded {path.stem}.", level="success")
            except (OSError, ValueError) as error:
                app.toast(f"Couldn't load save: {error}", level="error")

        box = build_save_menu(app, cards, _load)
        app.open_overlay(box, close_on_click_outside=True)

    def _open_shop():
        app.open_overlay(
            _build_shop(app, state, _spawn_fish, _buy_food, _add_decoration),
            close_on_click_outside=True,
        )

    def _open_settings():
        app.open_overlay(_build_settings(app, state), close_on_click_outside=True)

    def _open_help():
        app.open_overlay(build_help_menu(app), close_on_click_outside=True)

    def _open_start_menu():
        menu = None

        def _new_aquarium():
            app.close_overlay(menu)

        def _load_save():
            _open_load_menu(lambda: app.close_overlay(menu))

        def _settings():
            _open_settings()

        def _help():
            _open_help()

        menu = build_start_menu(app, _new_aquarium, _load_save, _settings, _help)
        app.open_overlay(menu, close_on_escape=False)

    app.add(Button(2, 2, "Open Shop").on_click(lambda _w: _open_shop()))
    app.add(Button(16, 2, "Settings").on_click(lambda _w: _open_settings()))
    app.add(Button(29, 2, "Save").on_click(lambda _w: _save_game()))
    app.add(Button(39, 2, "Load").on_click(lambda _w: _open_load_menu()))
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

    def _on_mouse(event):
        if isinstance(event, MouseMove):
            mouse_pos["x"], mouse_pos["y"] = float(event.col), float(event.row)
            return False  # not consumed -- normal hover dispatch still runs (tooltips)
        if any(e.modal for e in app._overlays):
            return False  # a modal (Shop/Inspector/prompt) is open -- let it handle its own clicks
        if isinstance(event, MouseClick) and event.btn == 0:
            clicked = fish_at(fish, event.col, event.row)
            if clicked is not None:
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

    def _update_environment():
        fraction = compute_time_of_day(
            time.monotonic() - session_start, AGE_SECONDS_PER_DAY
        )
        environment["phase"] = get_day_phase(fraction)
        environment["temperature"] = compute_water_temperature(fraction)
        app.style.bg = lerp_color(DAY_BG, NIGHT_BG, night_blend(fraction))

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
            app.widgets.remove(f)
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
            )
            fish.append(baby)
            app.add(baby)
            _wire_tooltip(baby)
            form_relationship(baby, fish)
            app.toast(
                f"{parent_a.display_name} and {parent_b.display_name} had a baby! "
                f"Welcome, {baby.display_name}.",
                level="success",
                icon="👶",
            )
        _refresh_stats()

    def _daily_tick():
        day_count["n"] += 1
        _try_breeding()
        attractiveness = compute_attractiveness(fish, decorations, foods)
        visitors, ticket_sales, donations = compute_visitor_income(attractiveness)
        grant = MAINTENANCE_GRANT
        food_expense = state["food_spent_today"]
        state["food_spent_today"] = 0
        state["money"] += ticket_sales + donations + grant
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

    app.on_key(Key.ESC, lambda: "quit")
    _open_start_menu()
    app.run()


if __name__ == "__main__":
    main()
