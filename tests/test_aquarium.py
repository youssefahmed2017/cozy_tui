"""Pure logic tests for the Aquarium example (examples/aquarium/aquarium.py),
Step 1: the steer() wall-bounce/movement function. Mirrors
tests/test_game_2048.py's importlib-load pattern -- no Widget/App involved."""

import importlib.util
import json
import math
import pathlib
import random
import time

import pytest

_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "examples"
    / "aquarium"
    / "aquarium.py"
)
_spec = importlib.util.spec_from_file_location("aquarium", _PATH)
aq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aq)

BOUNDS = (0.0, 0.0, 20.0, 20.0)


def test_straight_line_motion_away_from_walls():
    x, y, vx, vy = aq.steer(5.0, 5.0, 2.0, 3.0, BOUNDS, 1.0)
    assert (x, y) == (7.0, 8.0)
    assert (vx, vy) == (2.0, 3.0)  # velocity unchanged, no wall hit


def test_bounces_off_right_wall():
    x, y, vx, vy = aq.steer(19.0, 5.0, 3.0, 0.0, BOUNDS, 1.0)
    assert vx < 0
    assert x <= 20.0


def test_bounces_off_left_wall():
    x, y, vx, vy = aq.steer(1.0, 5.0, -3.0, 0.0, BOUNDS, 1.0)
    assert vx > 0
    assert x >= 0.0


def test_bounces_off_bottom_wall():
    x, y, vx, vy = aq.steer(5.0, 19.0, 0.0, 3.0, BOUNDS, 1.0)
    assert vy < 0
    assert y <= 20.0


def test_bounces_off_top_wall():
    x, y, vx, vy = aq.steer(5.0, 1.0, 0.0, -3.0, BOUNDS, 1.0)
    assert vy > 0
    assert y >= 0.0


def test_never_leaves_bounds_for_arbitrary_inputs():
    rng = random.Random(0)
    x0, y0, x1, y1 = BOUNDS
    for _ in range(2000):
        x = rng.uniform(x0, x1)
        y = rng.uniform(y0, y1)
        vx = rng.uniform(-20, 20)
        vy = rng.uniform(-20, 20)
        nx, ny, _nvx, _nvy = aq.steer(x, y, vx, vy, BOUNDS, 0.5)
        assert x0 <= nx <= x1
        assert y0 <= ny <= y1


def test_random_velocity_has_the_requested_speed():
    for _ in range(50):
        speed = random.uniform(1, 10)
        vx, vy = aq.random_velocity(speed)
        assert math.isclose(math.hypot(vx, vy), speed, rel_tol=1e-9)


def test_random_velocity_varies_direction():
    directions = {aq.random_velocity(5.0) for _ in range(20)}
    assert len(directions) > 1  # not always the same angle


# ── Step 2: steering toward food ──────────────────────────────────────────────


def test_steer_toward_food_none_leaves_velocity_unchanged():
    vx, vy, ate = aq.steer_toward_food(1.0, 2.0, 0.0, 0.0, None, 5.0, 1.0)
    assert (vx, vy, ate) == (1.0, 2.0, False)


def test_steer_toward_food_blends_velocity_toward_target():
    vx, vy, ate = aq.steer_toward_food(0.0, 0.0, 0.0, 0.0, (10.0, 0.0), 5.0, 1.0)
    assert not ate
    assert math.isclose(vx, 5.0)
    assert math.isclose(vy, 0.0, abs_tol=1e-9)


def test_steer_toward_food_partial_blend_moves_only_part_way():
    vx, vy, ate = aq.steer_toward_food(0.0, 0.0, 0.0, 0.0, (10.0, 0.0), 5.0, 0.5)
    assert not ate
    assert math.isclose(vx, 2.5)


def test_steer_toward_food_reports_ate_within_eat_radius():
    vx, vy, ate = aq.steer_toward_food(3.0, 4.0, 0.0, 0.0, (0.5, 0.0), 5.0, 1.0)
    assert ate
    assert (vx, vy) == (3.0, 4.0)  # velocity untouched once "ate"


# ── Step 2: hunger / health decay and feeding ─────────────────────────────────


def test_decay_hunger_decrements_hunger_above_min():
    hunger, health = aq.decay_hunger(100.0, 100.0)
    assert hunger == 100.0 - aq.HUNGER_STEP
    assert health == 100.0


def test_decay_hunger_floors_at_zero():
    hunger, health = aq.decay_hunger(1.0, 100.0)
    assert hunger == 0.0


def test_decay_hunger_drains_health_once_starving():
    hunger, health = aq.decay_hunger(0.0, 100.0)
    assert hunger == 0.0
    assert health == 100.0 - aq.STARVE_HEALTH_LOSS


def test_decay_hunger_health_does_not_go_negative():
    hunger, health = aq.decay_hunger(0.0, 2.0)
    assert health == 0.0


def test_feed_relieves_hunger_and_restores_health():
    hunger, health = aq.feed(20.0, 50.0)
    assert hunger == 20.0 + aq.HUNGER_RELIEF
    assert health == 50.0 + aq.HEALTH_GAIN


def test_feed_clamps_hunger_and_health_to_bounds():
    hunger, health = aq.feed(90.0, 98.0)
    assert hunger == 100.0
    assert health == 100.0


# ── Update 1: Happiness ───────────────────────────────────────────────────────


def test_adjust_happiness_moves_by_delta():
    assert aq.adjust_happiness(50.0, 10.0) == 60.0
    assert aq.adjust_happiness(50.0, -10.0) == 40.0


def test_adjust_happiness_clamps_to_bounds():
    assert aq.adjust_happiness(95.0, 10.0) == 100.0
    assert aq.adjust_happiness(5.0, -10.0) == 0.0


# ── Step 3: nearest_index (shared by food-seeking and prey-seeking) ──────────


def test_nearest_index_empty_is_none():
    assert aq.nearest_index(0.0, 0.0, []) == None  # noqa: E711


def test_nearest_index_picks_the_closest_point():
    positions = [(10.0, 0.0), (1.0, 0.0), (5.0, 5.0)]
    assert aq.nearest_index(0.0, 0.0, positions) == 1


def test_nearest_index_ties_pick_the_first():
    positions = [(3.0, 0.0), (0.0, 3.0)]
    assert aq.nearest_index(0.0, 0.0, positions) == 0


# ── Step 3: shop catalog ──────────────────────────────────────────────────────


def test_shop_items_have_exactly_one_predator():
    predators = [s for s in aq.SHOP_ITEMS if s.predator]
    assert [s.name for s in predators] == ["Shark"]


def test_starter_species_excludes_predators():
    assert all(not s.predator for s in aq.STARTER_SPECIES)
    assert len(aq.STARTER_SPECIES) == len(aq.SHOP_ITEMS) - 1


def test_axolotl_is_a_non_predator_starter_species_with_its_favorite_foods():
    axolotl = next(s for s in aq.SHOP_ITEMS if s.name == "Axolotl")
    assert axolotl.predator is False
    assert axolotl in aq.STARTER_SPECIES
    assert axolotl.favorite_foods == ("Brine Shrimp", "Bloodworms", "Worms")


def test_other_species_have_no_favorite_foods_by_default():
    for species in aq.SHOP_ITEMS:
        if species.name != "Axolotl":
            assert species.favorite_foods == ()


# ── Step 3: predator (Shark) eats prey ────────────────────────────────────────


def _make_fish(x, y, bounds, foods, fish_list, on_eat_food, on_eat_fish, species):
    return aq.Fish(
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
    )


def test_shark_eats_nearby_prey_and_is_fed():
    bounds = (0.0, 0.0, 50.0, 50.0)
    foods = []
    fish_list = []
    eaten = []

    shark_species = next(s for s in aq.SHOP_ITEMS if s.predator)
    prey_species = next(s for s in aq.SHOP_ITEMS if not s.predator)

    shark = _make_fish(
        5.0, 5.0, bounds, foods, fish_list, lambda f: None, eaten.append, shark_species
    )
    prey = _make_fish(
        5.5, 5.0, bounds, foods, fish_list, lambda f: None, eaten.append, prey_species
    )
    fish_list.extend([shark, prey])
    shark._next_turn = float("inf")
    shark.hunger = 20.0
    shark.health = 50.0

    class _FakeCanvas:
        def write(self, *a, **k):
            pass

    shark.draw(_FakeCanvas())

    assert prey not in fish_list
    assert eaten == [prey]
    assert shark.hunger == 20.0 + aq.HUNGER_RELIEF
    assert shark.health == 50.0 + aq.HEALTH_GAIN


def test_shark_never_targets_another_shark():
    bounds = (0.0, 0.0, 50.0, 50.0)
    foods = []
    fish_list = []

    shark_species = next(s for s in aq.SHOP_ITEMS if s.predator)
    shark_a = _make_fish(
        5.0,
        5.0,
        bounds,
        foods,
        fish_list,
        lambda f: None,
        lambda f: None,
        shark_species,
    )
    shark_b = _make_fish(
        5.5,
        5.0,
        bounds,
        foods,
        fish_list,
        lambda f: None,
        lambda f: None,
        shark_species,
    )
    fish_list.extend([shark_a, shark_b])

    assert shark_a._nearest_prey() is None


def test_ordinary_fish_never_targets_other_fish_as_prey():
    bounds = (0.0, 0.0, 50.0, 50.0)
    foods = []
    fish_list = []

    prey_species = next(s for s in aq.SHOP_ITEMS if not s.predator)
    a = _make_fish(
        5.0, 5.0, bounds, foods, fish_list, lambda f: None, lambda f: None, prey_species
    )
    b = _make_fish(
        5.5, 5.0, bounds, foods, fish_list, lambda f: None, lambda f: None, prey_species
    )
    fish_list.extend([a, b])
    a._next_turn = float("inf")

    class _FakeCanvas:
        def write(self, *a, **k):
            pass

    a.draw(_FakeCanvas())
    assert b in fish_list  # untouched -- a isn't a predator, so no hunting


# ── Step 3: shop buy flow (through the real Button click path) ───────────────


def test_shop_buy_button_deducts_money_and_spawns_a_fish():
    from cozy_tui import App

    app = App(full=False, size="400x200")
    state = {"money": 120, "food": 15}
    bought = []

    box = aq._build_shop(
        app,
        state,
        bought.append,
        lambda: None,
        lambda item: None,
        lambda item: None,
        lambda: None,
    )
    buttons = [c for c in box.children if c.__class__.__name__ == "Button"]
    # rows are: Fish Food, then SHOP_ITEMS in order, then Close.
    goldfish_buy = buttons[1]
    goldfish_buy.on_mouse_click()

    assert state["money"] == 120 - aq.SHOP_ITEMS[0].price
    assert bought == [aq.SHOP_ITEMS[0]]


def test_shop_buy_refuses_when_too_poor():
    from cozy_tui import App

    app = App(full=False, size="400x200")
    state = {"money": 1, "food": 15}
    bought = []

    box = aq._build_shop(
        app,
        state,
        bought.append,
        lambda: None,
        lambda item: None,
        lambda item: None,
        lambda: None,
    )
    buttons = [c for c in box.children if c.__class__.__name__ == "Button"]
    shark_buy = buttons[
        4
    ]  # Fish Food, Goldfish, Angelfish, Betta, Shark, decorations, Close
    shark_buy.on_mouse_click()

    assert state["money"] == 1  # untouched
    assert bought == []


def test_shop_sells_fish_food():
    from cozy_tui import App

    app = App(full=False, size="400x200")
    state = {"money": 120, "food": 0}
    bought_food = []

    box = aq._build_shop(
        app,
        state,
        lambda species: None,
        lambda: bought_food.append(1),
        lambda item: None,
        lambda item: None,
        lambda: None,
    )
    buttons = [c for c in box.children if c.__class__.__name__ == "Button"]
    food_buy = buttons[0]
    food_buy.on_mouse_click()

    assert state["money"] == 120 - aq.FOOD_PACK_PRICE
    assert bought_food == [1]


def test_shop_food_refuses_when_too_poor():
    from cozy_tui import App

    app = App(full=False, size="400x200")
    state = {"money": 0, "food": 0}
    bought_food = []

    box = aq._build_shop(
        app,
        state,
        lambda species: None,
        lambda: bought_food.append(1),
        lambda item: None,
        lambda item: None,
        lambda: None,
    )
    buttons = [c for c in box.children if c.__class__.__name__ == "Button"]
    buttons[0].on_mouse_click()

    assert state["money"] == 0
    assert bought_food == []


# ── Step 4: decoration avoidance ──────────────────────────────────────────────


def test_avoid_decorations_no_decorations_leaves_velocity_unchanged():
    vx, vy = aq.avoid_decorations(1.0, 2.0, 0.0, 0.0, [], 5.0, 1.0)
    assert (vx, vy) == (1.0, 2.0)


def test_avoid_decorations_outside_influence_leaves_velocity_unchanged():
    # radius 1 + AVOID_MARGIN(3) = 4 influence; fish is 10 away -- untouched.
    vx, vy = aq.avoid_decorations(0.0, 0.0, 10.0, 0.0, [(0.0, 0.0, 1.0)], 5.0, 1.0)
    assert (vx, vy) == (0.0, 0.0)


def test_avoid_decorations_pushes_directly_away_when_inside_influence():
    vx, vy = aq.avoid_decorations(0.0, 0.0, 2.0, 0.0, [(0.0, 0.0, 1.0)], 5.0, 1.0)
    assert math.isclose(vx, 5.0)
    assert math.isclose(vy, 0.0, abs_tol=1e-9)


def test_avoid_decorations_partial_blend_moves_only_part_way():
    vx, vy = aq.avoid_decorations(0.0, 0.0, 2.0, 0.0, [(0.0, 0.0, 1.0)], 5.0, 0.5)
    assert math.isclose(vx, 2.5)


def test_avoid_decorations_picks_the_nearest_decoration():
    decorations = [(0.0, 0.0, 1.0), (2.1, 0.0, 1.0)]
    # fish is at (2.0, 0.0) -- much closer to the second decoration.
    vx, vy = aq.avoid_decorations(0.0, 0.0, 2.0, 0.0, decorations, 5.0, 1.0)
    # pushed away from (2.1, 0.0), i.e. toward -x, not away from the origin.
    assert vx < 0.0


def test_avoid_decorations_degenerate_zero_distance_does_not_crash():
    vx, vy = aq.avoid_decorations(0.0, 0.0, 0.0, 0.0, [(0.0, 0.0, 1.0)], 5.0, 1.0)
    assert math.isclose(math.hypot(vx, vy), 5.0)


# ── Step 4: Decoration widget ──────────────────────────────────────────────────


def test_decoration_radius_from_its_art_bounding_box():
    d = aq.Decoration(5.0, 5.0, ["🌿", "🌿", "🌿"], "bright_green")
    # width 2 (wide glyph), height 3 -- radius is max(w, h) / 2.
    assert d.radius == 1.5


def test_decoration_single_row_art_radius():
    d = aq.Decoration(5.0, 5.0, ["🪨"], "bright_black")
    assert d.radius == 1.0


# ── Step 4: fish steer around a decoration in their path ──────────────────────


def test_fish_curves_around_a_decoration_directly_ahead():
    bounds = (0.0, 0.0, 50.0, 50.0)
    foods, fish_list = [], []
    decoration = aq.Decoration(20.0, 5.0, aq.ROCK_ART, "bright_black")

    f = aq.Fish(
        5.0,
        5.0,
        bounds,
        foods,
        fish_list,
        lambda x: None,
        lambda x: None,
        "><>",
        "<><",
        "bright_yellow",
        decorations=[decoration],
    )
    fish_list.append(f)
    f._next_turn = float("inf")
    f.vx, f.vy = 3.0, 0.0  # heads straight at the rock

    class _FakeCanvas:
        def write(self, *a, **k):
            pass

    canvas = _FakeCanvas()
    min_dist_to_rock = None
    start_x = f.fx
    for _ in _simulated_frames(f, seconds=5.0):
        f.draw(canvas)
        d = math.hypot(f.fx - decoration.fx, f.fy - decoration.fy)
        if min_dist_to_rock is None or d < min_dist_to_rock:
            min_dist_to_rock = d

    # Guard against passing for the wrong reason: if the fish had barely
    # moved, "never overlapped the rock" would be trivially true.
    assert abs(f.fx - start_x) > decoration.radius

    # The fish gets pushed off its straight-line path well before reaching
    # the rock's center -- it never has to actually overlap the decoration.
    assert min_dist_to_rock > decoration.radius
    # And it still made real forward progress rather than getting stuck.
    assert f.fx > 5.0


def test_shop_close_button_closes_the_overlay():
    from cozy_tui import App

    app = App(full=False, size="400x200")
    state = {"money": 120, "food": 15}
    box = aq._build_shop(
        app,
        state,
        lambda species: None,
        lambda: None,
        lambda item: None,
        lambda item: None,
        lambda: None,
    )
    app.open_overlay(box)
    assert app._overlays  # opened

    close_btn = [c for c in box.children if c.__class__.__name__ == "Button"][-1]
    close_btn.on_mouse_click()
    assert not app._overlays


# ── Treats: named foods fed directly to one fish ──────────────────────────────


def test_shop_buy_treat_deducts_price_and_calls_buy_treat_with_the_item():
    from cozy_tui import App

    app = App(full=False, size="400x440")
    state = {"money": 120}
    bought = []

    box = aq._build_shop(
        app,
        state,
        lambda s: None,
        lambda: None,
        lambda item: None,
        bought.append,
        lambda: None,
    )
    buttons = [c for c in box.children if c.__class__.__name__ == "Button"]
    # Fish Food(1) + one per species + one per decoration = buttons before Treats.
    treats_start = 1 + len(aq.SHOP_ITEMS) + len(aq.DECORATION_SHOP_ITEMS)
    first_treat_buy = buttons[treats_start]
    first_treat_buy.on_mouse_click()

    assert bought == [aq.TREAT_SHOP_ITEMS[0]]
    assert state["money"] == 120 - aq.TREAT_SHOP_ITEMS[0].price


def test_shop_shows_current_treat_stock_and_updates_after_buying():
    from cozy_tui import App

    app = App(full=False, size="400x440")
    state = {"money": 120, "treats": {"Brine Shrimp": 2}}

    def buy_treat(item):
        state["treats"][item.kind] = state["treats"].get(item.kind, 0) + item.pack_size

    box = aq._build_shop(
        app,
        state,
        lambda s: None,
        lambda: None,
        lambda item: None,
        buy_treat,
        lambda: None,
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert any("(have 2)" in t for t in labels)

    buttons = [c for c in box.children if c.__class__.__name__ == "Button"]
    treats_start = 1 + len(aq.SHOP_ITEMS) + len(aq.DECORATION_SHOP_ITEMS)
    buttons[treats_start].on_mouse_click()  # buy another Brine Shrimp pack

    labels_after = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    expected = 2 + aq.TREAT_SHOP_ITEMS[0].pack_size
    assert any(f"(have {expected})" in t for t in labels_after)


def test_shop_treat_stock_display_is_robust_with_no_treats_key():
    # Ad-hoc state dicts (older saves, some tests) may not have "treats" at
    # all -- the Shop shouldn't crash building/refreshing its stock display.
    from cozy_tui import App

    app = App(full=False, size="400x440")
    state = {"money": 120}
    box = aq._build_shop(
        app,
        state,
        lambda s: None,
        lambda: None,
        lambda item: None,
        lambda item: None,
        lambda: None,
    )
    assert box is not None


def test_inspector_hides_feed_a_treat_with_no_stock():
    from cozy_tui import App

    app = App(full=False, size="380x440")
    f = _neutral_fish(5.0, 5.0)
    box = aq._build_inspector(
        app, f, lambda f: None, lambda f: None, {}, lambda f, kind: None
    )
    assert not any(
        "Feed a Treat" in c.text
        for c in box.children
        if c.__class__.__name__ == "Label"
    )


def test_inspector_shows_favorite_foods_line_for_a_species_that_has_them():
    from cozy_tui import App

    app = App(full=False, size="380x440")
    f = _neutral_fish(5.0, 5.0, favorite_foods=("Brine Shrimp", "Bloodworms", "Worms"))
    box = aq._build_inspector(
        app, f, lambda f: None, lambda f: None, {}, lambda f, kind: None
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert any(t.startswith("Favorite foods:") for t in labels)


def test_inspector_hides_favorite_foods_line_with_no_favorites():
    from cozy_tui import App

    app = App(full=False, size="380x440")
    f = _neutral_fish(5.0, 5.0)  # default favorite_foods=()
    box = aq._build_inspector(
        app, f, lambda f: None, lambda f: None, {}, lambda f, kind: None
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert not any(t.startswith("Favorite foods:") for t in labels)


def test_inspector_shows_feed_a_treat_row_only_for_stocked_kinds():
    from cozy_tui import App

    app = App(full=False, size="380x440")
    f = _neutral_fish(5.0, 5.0)
    box = aq._build_inspector(
        app, f, lambda f: None, lambda f: None, {"Worms": 3}, lambda f, kind: None
    )
    buttons = [c.text for c in box.children if c.__class__.__name__ == "Button"]
    assert any("Worms" in t and "(3)" in t for t in buttons)
    assert not any("Brine Shrimp" in t for t in buttons)  # not in stock


def test_inspector_feed_a_treat_button_invokes_callback_and_closes():
    from cozy_tui import App

    app = App(full=False, size="380x440")
    f = _neutral_fish(5.0, 5.0)
    fed = []
    box = aq._build_inspector(
        app,
        f,
        lambda f: None,
        lambda f: None,
        {"Pizza": 1},
        lambda fish, kind: fed.append((fish, kind)),
    )
    app.open_overlay(box)
    feed_btn = next(
        c
        for c in box.children
        if c.__class__.__name__ == "Button" and "Pizza" in c.text
    )
    feed_btn.on_mouse_click()

    assert fed == [(f, "Pizza")]
    assert not app._overlays  # closes like Sell does


# ── Step 5: random_personality() ──────────────────────────────────────────────


def test_random_personality_always_one_of_the_six():
    for _ in range(200):
        assert aq.random_personality() in aq.PERSONALITIES


def test_random_personality_every_name_shows_up_over_many_rolls():
    rolls = [aq.random_personality() for _ in range(500)]
    for name in aq.PERSONALITIES:
        assert name in rolls


# ── Step 5: fish_at() / describe_fish() ───────────────────────────────────────


def _neutral_fish(
    x, y, bounds=(0.0, 0.0, 50.0, 50.0), foods=None, fish_list=None, **kw
):
    f = aq.Fish(
        x,
        y,
        bounds,
        foods if foods is not None else [],
        fish_list if fish_list is not None else [],
        lambda x: None,
        lambda x: None,
        "><>",
        "<><",
        "bright_yellow",
        **kw,
    )
    f.personality = "Explorer"  # least intrusive default; tests override as needed
    f.is_sleepy = False  # ditto -- roll_is_sleepy() is random at construction
    return f


def test_fish_starts_with_happiness_in_the_documented_range():
    # personality (and so its start bonus) is rolled internally before this
    # test can control it -- widen the bound by the largest bonus magnitude
    # rather than pin to one personality after the fact (too late to affect
    # the happiness already computed at construction).
    max_bonus = max(aq.HAPPINESS_PERSONALITY_START_BONUS.values())
    min_bonus = min(aq.HAPPINESS_PERSONALITY_START_BONUS.values())
    for _ in range(30):
        f = _neutral_fish(5.0, 5.0)
        assert aq.HAPPINESS_START_MIN + min_bonus <= f.happiness
        assert f.happiness <= aq.HAPPINESS_START_MAX + max_bonus


def test_fish_starting_happiness_leans_per_personality():
    # _neutral_fish() always overwrites personality to "Explorer" right after
    # construction -- bypass it and build directly, matching its own internal
    # shape, so personality stays whatever random_personality() actually
    # rolled (happiness is computed from that same real roll, at __init__).
    def _fresh_fish():
        return aq.Fish(
            5.0,
            5.0,
            (0.0, 0.0, 50.0, 50.0),
            [],
            [],
            lambda x: None,
            lambda x: None,
            "><>",
            "<><",
            "bright_yellow",
        )

    many = [_fresh_fish() for _ in range(400)]
    friendly = [f for f in many if f.personality == "Friendly"]
    lazy = [f for f in many if f.personality == "Lazy"]
    assert friendly and lazy  # both personalities show up in a large sample
    midpoint = (aq.HAPPINESS_START_MIN + aq.HAPPINESS_START_MAX) / 2
    assert sum(f.happiness for f in friendly) / len(friendly) > midpoint
    assert sum(f.happiness for f in lazy) / len(lazy) < midpoint


def test_fish_feeling_bands_match_happiness():
    f = _neutral_fish(5.0, 5.0)
    f.happiness = 0.0
    assert f.feeling == "Sad"
    f.happiness = aq.HAPPINESS_SAD_THRESHOLD - 0.1
    assert f.feeling == "Sad"
    f.happiness = aq.HAPPINESS_SAD_THRESHOLD
    assert f.feeling == "Neutral"
    f.happiness = aq.HAPPINESS_HAPPY_THRESHOLD - 0.1
    assert f.feeling == "Neutral"
    f.happiness = aq.HAPPINESS_HAPPY_THRESHOLD
    assert f.feeling == "Happy"
    f.happiness = aq.HAPPINESS_VERY_HAPPY_THRESHOLD - 0.1
    assert f.feeling == "Happy"
    f.happiness = aq.HAPPINESS_VERY_HAPPY_THRESHOLD
    assert f.feeling == "Very Happy"
    f.happiness = 100.0
    assert f.feeling == "Very Happy"


def test_fish_hunger_feeling_bands_match_hunger():
    # Scale is 0=starving/100=full, so the ladder reads top-down from Full.
    f = _neutral_fish(5.0, 5.0)
    f.hunger = 100.0
    assert f.hunger_feeling == "Full"
    f.hunger = aq.HUNGER_CONTENT_THRESHOLD
    assert f.hunger_feeling == "Full"
    f.hunger = aq.HUNGER_CONTENT_THRESHOLD - 0.1
    assert f.hunger_feeling == "Content"
    f.hunger = aq.HUNGER_A_LITTLE_HUNGRY_THRESHOLD
    assert f.hunger_feeling == "Content"
    f.hunger = aq.HUNGER_A_LITTLE_HUNGRY_THRESHOLD - 0.1
    assert f.hunger_feeling == "A little hungry"
    f.hunger = aq.HUNGER_WARNING_THRESHOLD
    assert f.hunger_feeling == "A little hungry"
    f.hunger = aq.HUNGER_WARNING_THRESHOLD - 0.1
    assert f.hunger_feeling == "Hungry"
    f.hunger = aq.HUNGER_LOW_ENERGY_THRESHOLD
    assert f.hunger_feeling == "Hungry"
    f.hunger = aq.HUNGER_LOW_ENERGY_THRESHOLD - 0.1
    assert f.hunger_feeling == "Low energy"
    f.hunger = 0.0
    assert f.hunger_feeling == "Low energy"


def test_eating_regular_food_gives_the_fed_happiness_gain():
    bounds = (0.0, 0.0, 50.0, 50.0)
    foods = [aq.Food(5.0, 5.0)]  # exactly at the fish -- guaranteed within EAT_RADIUS
    f = _neutral_fish(5.0, 5.0, bounds, foods=foods)
    f.happiness = 50.0
    f._next_turn = float("inf")

    _age(f)
    f.draw(_FakeCanvas())

    assert f.happiness == 50.0 + aq.HAPPINESS_FED_GAIN


def test_fish_at_finds_a_fish_on_its_row_within_its_glyph_width():
    f = _neutral_fish(5.0, 5.0)
    f.birth_time -= (
        aq.AGE_SECONDS_PER_DAY * 12
    )  # past Baby -- use the real "><>" adult glyph
    f.x, f.y = 5, 5  # natural_width("><>") == 3 -> occupies cols 5,6,7
    assert aq.fish_at([f], 5, 5) is f
    assert aq.fish_at([f], 7, 5) is f
    assert aq.fish_at([f], 8, 5) is None
    assert aq.fish_at([f], 5, 6) is None


def test_fish_at_empty_list_is_none():
    assert aq.fish_at([], 0, 0) is None


def test_describe_fish_includes_name_species_personality_hunger():
    f = _neutral_fish(5.0, 5.0)
    f.personality = "Greedy"
    f.hunger = 42.0
    text = aq.describe_fish(f)
    assert f.display_name in text
    assert f.species_name in text
    assert "Greedy" in text
    assert "Fullness 42%" in text


def test_describe_fish_reflects_a_rename():
    f = _neutral_fish(5.0, 5.0)
    f.display_name = "Bubbles"
    assert "Bubbles" in aq.describe_fish(f)


# ── Step 5: personality-driven steering ───────────────────────────────────────


class _FakeCanvas:
    def write(self, *a, **k):
        pass


def _age(f, seconds=0.1):
    # draw() computes dt from time.monotonic() - f._last -- back-date it so a
    # single draw() call has a real, non-negligible dt to blend velocity
    # with, instead of the ~0 elapsed since __init__ a moment ago.
    f._last = time.monotonic() - seconds


def _simulated_frames(f, *, seconds, step=1 / 60.0):
    """Yield one item per frame of a `seconds`-long simulation, back-dating
    `f._last` before each so `draw()` sees an exact `step` dt no matter how
    fast the machine is. Same trick as `_age`, for loops rather than a single
    call -- driving a multi-frame simulation with `time.sleep` instead makes
    the covered distance depend on the platform's sleep granularity."""
    for frame in range(int(seconds / step)):
        _age(f, step)
        yield frame


def test_shy_fish_flees_directly_from_the_mouse_with_no_decorations():
    bounds = (0.0, 0.0, 50.0, 50.0)
    mouse_pos = {"x": 5.0, "y": 5.0}
    f = _neutral_fish(6.0, 5.0, bounds, mouse_pos=mouse_pos)
    f.personality = "Shy"
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # pushed away from the mouse at (5, 5), i.e. toward +x


def test_shy_fish_flees_toward_the_nearest_decoration_when_one_exists():
    bounds = (0.0, 0.0, 50.0, 50.0)
    mouse_pos = {"x": 5.0, "y": 5.0}
    decoration = aq.Decoration(20.0, 5.0, aq.ROCK_ART, "bright_black")
    f = _neutral_fish(6.0, 5.0, bounds, mouse_pos=mouse_pos, decorations=[decoration])
    f.personality = "Shy"
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # heading toward the decoration at x=20, away from f.fx=6


def test_shy_fish_ignores_a_distant_mouse():
    bounds = (0.0, 0.0, 50.0, 50.0)
    mouse_pos = {"x": 40.0, "y": 40.0}  # far outside SHY_FLEE_RADIUS
    f = _neutral_fish(6.0, 5.0, bounds, mouse_pos=mouse_pos)
    f.personality = "Shy"
    f._next_turn = float("inf")
    f.vx, f.vy = 1.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert (f.vx, f.vy) == (1.0, 0.0)  # untouched -- no food/mouse/decorations either


def test_friendly_fish_steers_toward_the_cursor_when_present():
    bounds = (0.0, 0.0, 50.0, 50.0)
    mouse_pos = {"x": 20.0, "y": 5.0}
    f = _neutral_fish(5.0, 5.0, bounds, mouse_pos=mouse_pos)
    f.personality = "Friendly"
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # blends toward the mouse at higher x


def test_friendly_fish_drifts_toward_the_group_with_no_mouse():
    bounds = (0.0, 0.0, 50.0, 50.0)
    fish_list = []
    f = _neutral_fish(5.0, 5.0, bounds, fish_list=fish_list)
    f.personality = "Friendly"
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0
    fish_list.append(f)

    other = _neutral_fish(20.0, 5.0, bounds)
    fish_list.append(other)

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # drifts toward the other fish at higher x


def test_friendly_fish_with_no_mouse_and_no_other_fish_is_untouched():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(5.0, 5.0, bounds, fish_list=[])
    f.personality = "Friendly"
    f._next_turn = float("inf")
    f.vx, f.vy = 1.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert (f.vx, f.vy) == (1.0, 0.0)


def test_food_seeking_takes_priority_over_friendly_mouse_pull():
    bounds = (0.0, 0.0, 50.0, 50.0)
    mouse_pos = {"x": 20.0, "y": 5.0}
    foods = [aq.Food(5.0, 30.0)]  # straight up, away from the mouse
    f = _neutral_fish(5.0, 5.0, bounds, mouse_pos=mouse_pos)
    f.foods = foods
    f.personality = "Friendly"
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vy > 0.0  # chasing the food (+y), not the mouse (+x)


def test_fleeing_takes_priority_over_food_seeking():
    bounds = (0.0, 0.0, 50.0, 50.0)
    mouse_pos = {"x": 5.0, "y": 5.0}
    foods = [aq.Food(20.0, 5.0)]  # tempting food off to the right
    f = _neutral_fish(6.0, 5.0, bounds, mouse_pos=mouse_pos)
    f.foods = foods
    f.personality = "Shy"
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # fled from the mouse (+x), ignoring the food entirely
    assert foods == [foods[0]]  # untouched -- never even considered eating it


def test_greedy_fish_reaches_food_faster_than_an_explorer():
    bounds = (0.0, 0.0, 50.0, 50.0)

    greedy = _neutral_fish(5.0, 5.0, bounds)
    greedy.foods = [aq.Food(30.0, 5.0)]
    greedy.personality = "Greedy"
    greedy._next_turn = float("inf")
    greedy.speed = 5.0
    greedy.vx, greedy.vy = 0.0, 0.0

    normal = _neutral_fish(5.0, 5.0, bounds)
    normal.foods = [aq.Food(30.0, 5.0)]
    normal.personality = "Explorer"
    normal._next_turn = float("inf")
    normal.speed = 5.0
    normal.vx, normal.vy = 0.0, 0.0

    canvas = _FakeCanvas()
    for _ in range(20):
        _age(greedy, 0.01)  # identical dt for both, so the comparison is fair
        _age(normal, 0.01)
        greedy.draw(canvas)
        normal.draw(canvas)

    assert greedy.fx > normal.fx


def test_lazy_fish_has_a_slower_effective_speed():
    lazy_speeds = []
    for _ in range(200):
        f = aq.Fish(
            0.0,
            0.0,
            (0.0, 0.0, 50.0, 50.0),
            [],
            [],
            lambda x: None,
            lambda x: None,
            "><>",
            "<><",
            "bright_yellow",
        )
        if f.personality == "Lazy":
            lazy_speeds.append(f._effective_speed())
    assert lazy_speeds  # statistically should have rolled at least one
    assert max(lazy_speeds) <= aq.MAX_SPEED * aq.LAZY_SPEED_MULT + 1e-9


def test_effective_speed_reflects_personality_reassigned_after_construction():
    # _effective_speed() is checked fresh every use (see Fish.draw()), unlike
    # a value baked in once at construction -- so setting .personality after
    # the fact (as every other steering test in this file already does)
    # still changes it correctly.
    f = _neutral_fish(0.0, 0.0)
    f.speed = 5.0
    f.personality = "Explorer"
    assert f._effective_speed() == 5.0
    f.personality = "Lazy"
    assert f._effective_speed() == pytest.approx(5.0 * aq.LAZY_SPEED_MULT)


def test_playful_fish_varies_speed_on_each_turn():
    f = _neutral_fish(5.0, 5.0)
    f.personality = "Playful"
    f.speed = 5.0
    f._next_turn = 0.0  # force an immediate turn on the next draw()
    speeds = set()
    canvas = _FakeCanvas()
    for _ in _simulated_frames(f, seconds=0.15, step=0.01):
        f._next_turn = f._last  # force a turn every frame
        f.draw(canvas)
        speeds.add(round(math.hypot(f.vx, f.vy), 3))
    assert len(speeds) > 1  # varies rather than always the same magnitude


# ── Step 5: Decoration per-row colors ─────────────────────────────────────────


def test_decoration_single_color_string_applies_to_every_row():
    d = aq.Decoration(5.0, 5.0, ["a", "b", "c"], "bright_green")
    assert [s.fg for s in d.row_styles] == ["bright_green"] * 3


def test_decoration_color_list_applies_per_row():
    d = aq.Decoration(5.0, 5.0, ["a", "b"], ["white", "bright_black"])
    assert [s.fg for s in d.row_styles] == ["white", "bright_black"]


# ── Step 5: age_days ───────────────────────────────────────────────────────────


def test_age_days_starts_near_zero_and_increases():
    f = _neutral_fish(5.0, 5.0)
    assert f.age_days == pytest.approx(0.0, abs=0.01)
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 2.5
    assert f.age_days == pytest.approx(2.5, abs=0.01)


# ── Step 5: Fish Inspector ────────────────────────────────────────────────────


def test_inspector_shows_name_species_age_health_hunger_personality():
    from cozy_tui import App

    app = App(full=False, size="400x300")
    f = _neutral_fish(5.0, 5.0)
    f.display_name = "Bubbles"
    f.species_name = "Goldfish"
    f.personality = "Greedy"
    f.health = 87.0
    f.hunger = 33.0

    box = aq._build_inspector(
        app, f, lambda fish: None, lambda fish: None, {}, lambda fish, kind: None
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert box.title == "Bubbles"
    assert any("Goldfish" in t for t in labels)
    assert any("Greedy" in t for t in labels)
    assert any("87" in t for t in labels)
    assert any("33" in t for t in labels)


def test_inspector_rename_button_invokes_the_callback():
    from cozy_tui import App

    app = App(full=False, size="400x300")
    f = _neutral_fish(5.0, 5.0)
    renamed = []

    box = aq._build_inspector(
        app, f, renamed.append, lambda fish: None, {}, lambda fish, kind: None
    )
    buttons = [c for c in box.children if c.__class__.__name__ == "Button"]
    rename_btn = buttons[0]  # Rename, then Close
    rename_btn.on_mouse_click()

    assert renamed == [f]


def test_inspector_close_button_closes_the_overlay():
    from cozy_tui import App

    app = App(full=False, size="400x300")
    f = _neutral_fish(5.0, 5.0)

    box = aq._build_inspector(
        app, f, lambda fish: None, lambda fish: None, {}, lambda fish, kind: None
    )
    app.open_overlay(box)
    assert app._overlays

    close_btn = [c for c in box.children if c.__class__.__name__ == "Button"][-1]
    close_btn.on_mouse_click()
    assert not app._overlays


# ── Phase 2: favorite spots ────────────────────────────────────────────────────


def test_decoration_kind_defaults_and_can_be_set():
    plain = aq.Decoration(0.0, 0.0, ["x"], "white")
    assert plain.kind == "Decoration"
    rock = aq.Decoration(0.0, 0.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock")
    assert rock.kind == "Rock"


def test_fish_picks_a_favorite_decoration_when_some_exist():
    decorations = [
        aq.Decoration(1.0, 1.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock"),
        aq.Decoration(2.0, 2.0, aq.PLANT_ART, aq.PLANT_COLORS, kind="Plant"),
    ]
    f = _neutral_fish(5.0, 5.0, decorations=decorations)
    assert f.favorite_decoration in decorations


def test_fish_has_no_favorite_with_no_decorations():
    f = _neutral_fish(5.0, 5.0, decorations=[])
    assert f.favorite_decoration is None


def test_relaxing_fish_steers_toward_its_favorite_spot_when_far():
    bounds = (0.0, 0.0, 50.0, 50.0)
    spot = aq.Decoration(30.0, 5.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock")
    f = _neutral_fish(5.0, 5.0, bounds, decorations=[spot])
    f.favorite_decoration = spot  # deterministic even with only one candidate
    f._next_turn = float("inf")
    f._next_relax_check = float("inf")  # don't re-roll mid-test
    f._relaxing_until = float("inf")  # already relaxing, and stays that way
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # blends toward the spot at higher x


def test_relaxing_fish_settles_down_once_it_arrives():
    bounds = (0.0, 0.0, 50.0, 50.0)
    spot = aq.Decoration(6.0, 5.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock")
    f = _neutral_fish(
        5.0, 5.0, bounds, decorations=[spot]
    )  # 1 cell away -- well within arrival
    f.favorite_decoration = spot
    f._next_turn = float("inf")
    f._next_relax_check = float("inf")
    f._relaxing_until = float("inf")
    f.vx, f.vy = 3.0, 4.0

    _age(f)
    f.draw(_FakeCanvas())

    # Damped toward zero (IDLE_DAMPING < 1), not blended toward a target.
    assert math.hypot(f.vx, f.vy) < math.hypot(3.0, 4.0)


# ── Relaxation surfacing (existing relax mechanic, made visible) ────────────


def _relaxed_fish(bounds=(0.0, 0.0, 50.0, 50.0), kind="Rock"):
    """A fish already settled at its favorite spot -- same setup as
    test_relaxing_fish_settles_down_once_it_arrives(), one draw() call in."""
    spot = aq.Decoration(6.0, 5.0, aq.ROCK_ART, aq.ROCK_COLORS, kind=kind)
    f = _neutral_fish(5.0, 5.0, bounds, decorations=[spot])
    f.favorite_decoration = spot
    f._next_turn = float("inf")
    f._next_relax_check = float("inf")
    f._relaxing_until = float("inf")
    _age(f)
    f.draw(_FakeCanvas())
    return f, spot


def test_settling_to_relax_marks_the_fish_relaxing_and_flags_the_one_shot():
    f, _spot = _relaxed_fish()
    assert f.relaxing is True
    assert f._relax_began is True  # consumed by aquarium.py's _process_relaxing


def test_relax_one_shot_does_not_refire_on_a_later_frame_while_still_relaxing():
    f, _spot = _relaxed_fish()
    f._relax_began = False  # simulate _process_relaxing having consumed it

    _age(f)
    f.draw(_FakeCanvas())

    assert f.relaxing is True
    assert f._relax_began is False  # still relaxing, but not a fresh settle


def test_relax_flash_shows_above_the_fish_right_after_settling():
    f, _spot = _relaxed_fish()

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f, 0.01)  # small dt -- still well inside RELAX_FLASH_SECONDS
    f.draw(canvas)

    assert any(text == "😌" for _x, _y, text in writes)


def test_relax_flash_fades_after_relax_flash_seconds():
    f, _spot = _relaxed_fish()
    f._relax_flash_until = time.monotonic() - 0.01  # already elapsed

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f)
    f.draw(canvas)

    assert not any(text == "😌" for _x, _y, text in writes)
    assert f.relaxing is True  # the mechanic itself is unaffected -- just the flash


def test_relaxing_stops_the_moment_it_leaves_the_spot():
    f, _spot = _relaxed_fish()
    assert f.relaxing is True

    f._relaxing_until = 0.0  # the episode ends
    _age(f)
    f.draw(_FakeCanvas())

    assert f.relaxing is False


def test_sleep_mood_takes_visual_priority_over_the_relax_flash():
    bounds = (0.0, 0.0, 50.0, 50.0)
    spot = aq.Decoration(6.0, 5.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock")
    f = _sleepy_fish(5.0, 5.0, bounds, decorations=[spot])
    f.favorite_decoration = spot
    f._relax_flash_until = time.monotonic() + 10.0

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f)
    f.draw(canvas)

    assert any(text in ("😴", "😴💭") for _x, _y, text in writes)
    assert not any(text == "😌" for _x, _y, text in writes)


def test_relax_status_appears_in_the_inspector_while_relaxing():
    from cozy_tui import App

    app = App(full=False, size="380x520")
    f, spot = _relaxed_fish()

    box = aq._build_inspector(
        app, f, lambda f: None, lambda f: None, {}, lambda f, k: None
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any("Relaxing" in t and spot.kind in t for t in labels)


def test_relax_status_absent_from_the_inspector_when_not_relaxing():
    from cozy_tui import App

    app = App(full=False, size="380x520")
    f = _neutral_fish(5.0, 5.0)
    f.favorite_decoration = aq.Decoration(
        6.0, 5.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock"
    )

    box = aq._build_inspector(
        app, f, lambda f: None, lambda f: None, {}, lambda f, k: None
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert not any("Relaxing" in t for t in labels)


def test_relax_toast_wording_is_specific_per_decoration_kind():
    assert aq._relax_toast_message("Castle", "Steve") == (
        "🏰 Steve is relaxing by the Castle."
    )
    assert aq._relax_toast_message("Rock", "Steve") == (
        "🪨 Steve found some quiet time by the Rock."
    )
    assert aq._relax_toast_message("Plant", "Steve") == (
        "🌿 Steve is relaxing near their favorite Plant."
    )
    assert aq._relax_toast_message("Driftwood", "Steve") == (
        "🪵 Steve is drifting lazily by the Driftwood."
    )


def test_relax_toast_wording_falls_back_for_an_unknown_kind():
    message = aq._relax_toast_message("Anemone", "Bob")
    assert "Bob" in message


def test_join_relax_toast_wording_matches_the_pitched_message():
    message = aq._join_relax_toast_message("Rock", "Steve", "Alex")
    assert message == "🪨 Steve joined Alex. Both of them happily relaxed together."


# ── A friend joining one already relaxing ───────────────────────────────────


def test_friend_steers_toward_a_relaxing_friends_spot_when_far():
    bounds = (0.0, 0.0, 50.0, 50.0)
    host, spot = _relaxed_fish(bounds, kind="Rock")  # already settled at `spot`

    joiner = _neutral_fish(30.0, 30.0, bounds, decorations=[spot])
    joiner._next_turn = float("inf")
    joiner._next_relax_check = float("inf")
    _befriend(host, joiner)
    joiner.vx, joiner.vy = 0.0, 0.0

    _age(joiner)
    joiner.draw(_FakeCanvas())

    # Steered toward the host's spot (not yet arrived) rather than settling.
    assert joiner.relaxing is False
    assert math.hypot(joiner.vx, joiner.vy) > 0
    # Genuinely aimed at the spot (down-left of the joiner's start), not an
    # arbitrary direction: both velocity components point that way.
    assert joiner.vx < 0
    assert joiner.vy < 0


def test_friend_settles_and_becomes_relaxing_once_it_arrives_at_the_hosts_spot():
    bounds = (0.0, 0.0, 50.0, 50.0)
    host, spot = _relaxed_fish(bounds, kind="Rock")

    joiner = _neutral_fish(6.5, 5.0, bounds, decorations=[spot])  # 1 cell away
    joiner._next_turn = float("inf")
    joiner._next_relax_check = float("inf")
    _befriend(host, joiner)
    joiner.vx, joiner.vy = 3.0, 4.0

    _age(joiner)
    joiner.draw(_FakeCanvas())

    assert joiner.relaxing is True
    assert joiner._relax_spot is spot
    assert joiner._relaxing_with is host
    assert joiner._joined_friend_relax is True
    # Damped toward zero (IDLE_DAMPING), same settle shape as solo relaxing.
    assert math.hypot(joiner.vx, joiner.vy) < math.hypot(3.0, 4.0)


def test_joining_does_not_refire_the_one_shot_on_a_later_frame():
    bounds = (0.0, 0.0, 50.0, 50.0)
    host, spot = _relaxed_fish(bounds, kind="Rock")
    joiner = _neutral_fish(6.5, 5.0, bounds, decorations=[spot])
    joiner._next_turn = float("inf")
    joiner._next_relax_check = float("inf")
    _befriend(host, joiner)
    _age(joiner)
    joiner.draw(_FakeCanvas())
    assert joiner._joined_friend_relax is True
    joiner._joined_friend_relax = False  # simulate _process_relaxing consuming it

    _age(joiner)
    joiner.draw(_FakeCanvas())

    assert joiner.relaxing is True  # still joined...
    assert joiner._joined_friend_relax is False  # ...but not a fresh settle


def test_joining_only_happens_between_actual_friends():
    bounds = (0.0, 0.0, 50.0, 50.0)
    host, spot = _relaxed_fish(bounds, kind="Rock")
    stranger = _neutral_fish(6.5, 5.0, bounds, decorations=[spot])
    stranger._next_turn = float("inf")
    stranger._next_relax_check = float("inf")
    # No _befriend() call -- host.friend is None for a stranger.

    _age(stranger)
    stranger.draw(_FakeCanvas())

    assert stranger.relaxing is False
    assert stranger._joined_friend_relax is False


def test_joining_takes_priority_over_plain_friend_following():
    # Without a relaxing friend, a fish with a Friend just generically follows
    # them (the pre-existing "elif self.friend is not None" branch), aimed at
    # the friend's live position. Once that friend is relaxing, the same
    # steering should aim at the friend's fixed spot instead -- a different
    # target whenever the friend's live position isn't already the spot.
    # Two independent hosts (rather than flipping one mid-test) sidestep an
    # unrelated, pre-existing precedence quirk: a *bonded* host's own
    # draw() would itself just plain-follow the joiner back (friend-follow
    # already outranks solo relaxing for any fish with a Friend), so it
    # can never be made to genuinely settle by drawing it after befriending.
    bounds = (0.0, 0.0, 50.0, 50.0)
    spot = aq.Decoration(6.0, 5.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock")

    live_host = _neutral_fish(20.0, 2.0, bounds, decorations=[spot])  # not at `spot`
    joiner_a = _neutral_fish(30.0, 30.0, bounds, decorations=[spot])
    joiner_a._next_turn = float("inf")
    joiner_a._next_relax_check = float("inf")
    _befriend(live_host, joiner_a)
    _age(joiner_a)
    joiner_a.draw(_FakeCanvas())
    vx_following, vy_following = joiner_a.vx, joiner_a.vy

    relaxing_host, _spot = _relaxed_fish(bounds, kind="Rock")  # settled, no friend
    joiner_b = _neutral_fish(30.0, 30.0, bounds, decorations=[spot])
    joiner_b._next_turn = float("inf")
    joiner_b._next_relax_check = float("inf")
    _befriend(relaxing_host, joiner_b)
    _age(joiner_b)
    joiner_b.draw(_FakeCanvas())

    # Aimed at the fixed spot (6.0, 5.0), not the live_host's live position
    # (20.0, 2.0) the plain-follow case targeted -- a different direction.
    assert (joiner_b.vx, joiner_b.vy) != (vx_following, vy_following)


def test_inspector_status_mentions_the_friend_while_joined():
    from cozy_tui import App

    app = App(full=False, size="380x520")
    bounds = (0.0, 0.0, 50.0, 50.0)
    host, spot = _relaxed_fish(bounds, kind="Rock")
    host.display_name = "Steve"
    joiner = _neutral_fish(6.5, 5.0, bounds, decorations=[spot])
    joiner.display_name = "Alex"
    joiner._next_turn = float("inf")
    joiner._next_relax_check = float("inf")
    _befriend(host, joiner)
    _age(joiner)
    joiner.draw(_FakeCanvas())

    box = aq._build_inspector(
        app, joiner, lambda f: None, lambda f: None, {}, lambda f, k: None
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any("Relaxing" in t and "Rock" in t and "Steve" in t for t in labels)


def test_process_relaxing_fires_the_join_toast(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fish_list = [w for w in app.widgets if isinstance(w, aq.Fish)]
    host, joiner = fish_list[0], fish_list[1]
    host.display_name = "Steve"
    joiner.display_name = "Alex"
    rock = aq.Decoration(0.0, 0.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock")
    joiner._relax_spot = rock
    joiner._relaxing_with = host
    joiner._joined_friend_relax = True
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert joiner._joined_friend_relax is False
    assert "🪨 Alex joined Steve. Both of them happily relaxed together." in toasts


# ── The tiny relax wiggle ────────────────────────────────────────────────────


def test_is_asleep_true_at_night_with_low_hunger():
    f = _neutral_fish(5.0, 5.0)
    f.environment = {"phase": "Night", "temperature": 23.0}
    f.hunger = 100.0
    assert f.is_asleep is True


def test_is_asleep_false_when_too_hungry_to_actually_sleep():
    f = _neutral_fish(5.0, 5.0)
    f.environment = {"phase": "Night", "temperature": 23.0}
    f.hunger = aq.SLEEP_HUNGER_THRESHOLD - 10.0
    assert f.is_asleep is False


def test_is_asleep_always_false_for_a_predator():
    f = _neutral_fish(5.0, 5.0, is_predator=True)
    f.environment = {"phase": "Night", "temperature": 23.0}
    f.hunger = 100.0
    assert f.is_asleep is False


def test_is_asleep_false_with_no_environment():
    f = _neutral_fish(5.0, 5.0)
    assert f.environment is None
    assert f.is_asleep is False


def test_happiness_flourishes_never_roll_for_a_sleeping_fish(tmp_path, monkeypatch):
    # Regression: an earlier version rolled sparkle/circle/wiggle/follow for
    # every fish unconditionally, so a Very Happy fish sound asleep at night
    # could still sparkle or swim in circles mid-dream.
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.happiness = 100.0
    f.hunger = 100.0
    # _update_environment() recomputes environment["phase"] from real elapsed
    # time every tick (Fish.environment is the *same shared dict*), so
    # setting "phase" directly wouldn't stick -- pin compute_time_of_day
    # itself instead, the same way every other Night-dependent test does.
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: 0.9)  # Night
    f._sparkle_next_check = time.monotonic()
    f._circle_next_check = time.monotonic()
    f._wiggle_next_check = time.monotonic()

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()
    assert f.is_asleep is True
    for _ in range(5):
        second_timer.callback()

    assert f._sparkle_until == 0.0
    assert f._circling_until == 0.0
    assert f._excited_wiggle_until == 0.0


def test_happiness_decays_toward_the_floor_and_stops_there(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.happiness = 90.0
    f.environment["phase"] = "Day"
    f.hunger = 0.0

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    for _ in range(30):
        second_timer.callback()

    assert f.happiness < 90.0
    assert (
        f.happiness >= aq.HAPPINESS_DECAY_FLOOR - 0.5
    )  # decay alone doesn't dip below it


def test_happiness_does_not_decay_below_the_floor_on_its_own(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.happiness = aq.HAPPINESS_DECAY_FLOOR - 5.0
    f.environment["phase"] = "Day"
    f.hunger = 100.0
    start = f.happiness

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    for _ in range(10):
        second_timer.callback()

    # Only the small ambient gains apply below the floor -- decay itself
    # never pushes it lower.
    assert f.happiness >= start


def test_serious_event_suppresses_happiness_flourishes_tank_wide(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    victim, bystander = fishes[0], fishes[1]
    # Pinned Day (not just set on the shared dict, which _update_environment()
    # would overwrite from real elapsed time) so neither fish is asleep --
    # isolates the suppression from is_asleep's own, separate gating.
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: 0.5)
    for f in fishes:
        f.hunger = 0.0
    victim.decorations = []  # no hiding -- isolates the scare
    bystander.happiness = 100.0  # Very Happy, and due for a circle check
    bystander._circle_next_check = time.monotonic()
    bystander.fx, bystander.fy = victim.fx + 30.0, victim.fy  # elsewhere, uninvolved
    _add_real_fish(
        app, victim.fx + 1.0, victim.fy, is_predator=True, species_name="Shark"
    )

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()  # triggers the scare -> serious_event_at set

    # The *bystander* -- not even the scared fish -- still doesn't flourish,
    # because the suppression is tank-wide, not per-fish.
    assert bystander._circling_until == 0.0


def test_relaxing_fish_occasionally_shows_a_wiggle_glyph():
    f, _spot = _relaxed_fish()
    f.species_name = "Goldfish"
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 12  # past Baby -- real "><>" glyph
    base = f.right_glyph if f.vx >= 0 else f.left_glyph
    aged = f.birth_time

    # Sweep enough of a wiggle cycle to guarantee landing inside the wiggle
    # window at least once, without depending on wall-clock timing. Each
    # offset nudges only the sub-cycle phase -- `aged` keeps the fish's real
    # age (and so growth stage) fixed regardless.
    saw_wiggle = False
    for offset in [i * 0.05 for i in range(60)]:
        f.birth_time = aged - offset
        glyph = f._glyph()
        if glyph != base:
            saw_wiggle = True
            assert "~" in glyph
            break
    assert saw_wiggle


def test_non_relaxing_fish_never_shows_the_wiggle_glyph():
    f = _neutral_fish(5.0, 5.0)
    f.species_name = "Goldfish"
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 12  # past Baby
    assert f.relaxing is False
    base = f.right_glyph if f.vx >= 0 else f.left_glyph
    aged = f.birth_time

    for offset in [i * 0.05 for i in range(60)]:
        f.birth_time = aged - offset
        assert f._glyph() == base


def test_axolotls_own_resting_glyph_takes_priority_over_the_generic_wiggle():
    f, _spot = _relaxed_fish()
    f.species_name = "Axolotl"
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 12  # past Baby
    f._relaxing_until = time.monotonic() + 10.0

    assert f._glyph() == aq.AXOLOTL_RESTING_GLYPH


def test_relaxing_fish_gains_happiness_every_second(tmp_path, monkeypatch):
    # _process_happiness() also runs every tick and adds its own small
    # passive gains/decay -- started well above HAPPINESS_DECAY_FLOOR so
    # decay is deterministic (always applies); the temp-comfort gain still
    # depends on where in the real day/night cycle this tick lands
    # (compute_water_temperature() varies by elapsed wall-clock time), so
    # that one's left uncertain -- the tolerance absorbs it either way.
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.happiness = 70.0
    f.relaxing = True  # already settled, mid-episode -- not a fresh _relax_began

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    expected = 70.0 + aq.HAPPINESS_RELAX_TICK_GAIN - aq.HAPPINESS_DECAY_PER_SECOND
    assert f.happiness == pytest.approx(expected, abs=0.15)


def test_non_relaxing_fish_gets_no_relax_tick_happiness(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.happiness = 70.0
    f.relaxing = False

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    # Ambient gains/decay only (see the test above) -- no relax-specific
    # gain since this fish isn't relaxing.
    expected = 70.0 - aq.HAPPINESS_DECAY_PER_SECOND
    assert f.happiness == pytest.approx(expected, abs=0.15)


def test_process_relaxing_consumes_the_one_shot_and_respects_the_toast_cooldown(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fish_list = [w for w in app.widgets if isinstance(w, aq.Fish)]
    f = fish_list[0]
    f.favorite_decoration = aq.Decoration(
        0.0, 0.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock"
    )
    f._relax_began = True
    # Always land inside both the memory and toast chances, and never blocked
    # by the cooldown (nothing has toasted yet this test).
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert f._relax_began is False  # consumed
    assert any("Rock" in t for t in toasts)
    assert any("peaceful moment" in entry.lower() for entry in f.memory_log)


def test_process_relaxing_second_settle_is_blocked_by_the_toast_cooldown(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fish_list = [w for w in app.widgets if isinstance(w, aq.Fish)]
    a, b = fish_list[0], fish_list[1]
    rock = aq.Decoration(0.0, 0.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock")
    a.favorite_decoration = rock
    b.favorite_decoration = rock
    a._relax_began = True
    b._relax_began = True
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # always inside chance
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    # Both settle this same tick, but the tank-wide cooldown allows only one
    # ambient toast -- relaxing must stay rare, not become a notification per
    # fish (see constants.RELAX_TOAST_COOLDOWN). Filtered to relax-specific
    # wording since random.random() pinned at 0.0 also clears other unrelated
    # per-second chance rolls (e.g. visitor donations) on this same tick.
    relax_toasts = [t for t in toasts if "Rock" in t]
    assert len(relax_toasts) == 1


def test_process_relaxing_skips_a_fish_with_no_favorite_decoration(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.favorite_decoration = None
    f._relax_began = True
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    # Still consumed, just nothing to announce (filtered for the same reason
    # as the cooldown test above -- other unrelated per-second toasts can
    # fire on this same tick once random.random() is pinned at 0.0).
    assert f._relax_began is False
    assert not any("😌" in t or "peaceful" in t.lower() for t in toasts)


def test_axolotl_relax_check_uses_its_own_higher_chance_and_longer_duration(
    monkeypatch,
):
    # Real axolotls rest on the substrate far more than fish do -- reuses the
    # exact same relax mechanic, just tuned higher for this one species.
    bounds = (0.0, 0.0, 50.0, 50.0)
    spot = aq.Decoration(30.0, 5.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock")
    f = _neutral_fish(5.0, 5.0, bounds, decorations=[spot])
    f.species_name = "Axolotl"
    f.favorite_decoration = spot
    f._next_turn = float("inf")
    f._next_relax_check = time.monotonic() - 0.01  # fires this frame
    f._relaxing_until = 0.0

    # Between RELAX_CHANCE (0.4) and AXOLOTL_RELAX_CHANCE (0.75): a regular
    # fish would NOT start relaxing on this roll, but an Axolotl does.
    monkeypatch.setattr(aq.random, "random", lambda: 0.5)
    monkeypatch.setattr(aq.random, "uniform", lambda lo, hi: hi)

    _age(f)
    f.draw(_FakeCanvas())

    remaining = f._relaxing_until - time.monotonic()
    assert remaining > aq.RELAX_DURATION_MAX  # longer than any regular fish's max
    assert remaining == pytest.approx(aq.AXOLOTL_RELAX_DURATION_MAX, abs=1.0)


def test_axolotl_shows_a_resting_glyph_only_while_actually_relaxing():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(5.0, 5.0, bounds)
    f.species_name = "Axolotl"
    f.right_glyph, f.left_glyph = "(°.°)~", "~(°.°)"
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 12  # past Baby

    f._relaxing_until = 0.0  # not relaxing
    assert f._glyph() != aq.AXOLOTL_RESTING_GLYPH

    f._relaxing_until = time.monotonic() + 10.0  # relaxing now
    assert f._glyph() == aq.AXOLOTL_RESTING_GLYPH


def test_friendly_fish_alone_falls_through_to_relaxing():
    # Regression: a Friendly fish with no mouse and no other fish to
    # socialize with must not silently "claim" this frame's personality-
    # steering slot while doing nothing -- it should fall through to
    # relaxing (or plain wandering) instead, exactly like a non-Friendly fish
    # would once personality-steering has nothing to do.
    bounds = (0.0, 0.0, 50.0, 50.0)
    spot = aq.Decoration(30.0, 5.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock")
    f = _neutral_fish(5.0, 5.0, bounds, fish_list=[], decorations=[spot])
    f.personality = "Friendly"
    f.favorite_decoration = spot
    f._next_turn = float("inf")
    f._next_relax_check = float("inf")
    f._relaxing_until = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # actually relaxing toward the spot, not frozen


def test_relaxing_still_steers_when_just_outside_the_spots_own_avoidance_influence():
    # Regression: "arrived" must be defined relative to the spot's own
    # avoid_decorations() influence radius, not a fixed distance smaller than
    # it -- otherwise a relaxing fish would perpetually fight the every-frame
    # push away from its own favorite decoration instead of ever settling.
    bounds = (0.0, 0.0, 50.0, 50.0)
    spot = aq.Decoration(0.0, 5.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock")
    arrive_radius = spot.radius + aq.AVOID_MARGIN + aq.RELAX_ARRIVE_MARGIN
    assert (
        arrive_radius > spot.radius + aq.AVOID_MARGIN
    )  # sits just past the influence boundary

    just_outside = arrive_radius + 0.5
    f = _neutral_fish(just_outside, 5.0, bounds, decorations=[spot])
    f.favorite_decoration = spot
    f._next_turn = float("inf")
    f._next_relax_check = float("inf")
    f._relaxing_until = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert (
        f.vx < 0.0
    )  # still actively steering back toward the spot (-x, spot is to the left)


def test_food_seeking_takes_priority_over_relaxing():
    bounds = (0.0, 0.0, 50.0, 50.0)
    spot = aq.Decoration(
        5.0, 30.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock"
    )  # straight down
    foods = [aq.Food(20.0, 5.0)]  # straight right, away from the spot
    f = _neutral_fish(5.0, 5.0, bounds, foods=foods, decorations=[spot])
    f.favorite_decoration = spot
    f._next_turn = float("inf")
    f._next_relax_check = float("inf")
    f._relaxing_until = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # chasing the food (+x), not relaxing toward the spot (+y)


def test_seeking_food_skips_decoration_avoidance_this_frame():
    # Regression: avoid_decorations() used to run unconditionally every
    # frame, even while a fish was actively chasing food. Food sitting
    # inside a decoration's avoidance radius (but outside EAT_RADIUS) could
    # then never actually be reached -- every frame, avoid_decorations()
    # shoved the fish back out before it arrived, so it got stuck near the
    # furniture instead of eating.
    bounds = (0.0, 0.0, 50.0, 50.0)
    spot = aq.Decoration(10.0, 5.0, aq.CASTLE_ART, aq.CASTLE_COLORS, kind="Castle")
    influence = spot.radius + aq.AVOID_MARGIN
    foods = [aq.Food(spot.fx + influence - 1.0, spot.fy)]  # inside the influence radius
    f = _neutral_fish(0.0, 5.0, bounds, foods=foods, decorations=[spot])
    f.personality = "Explorer"
    f._next_turn = float("inf")

    # Fish.draw() derives dt from time.monotonic(), so a frame only advances
    # the simulation by however long really elapsed. Sleeping to manufacture
    # that is not portable -- Linux honours a 0.5ms sleep far more closely
    # than Windows or macOS do, so the same loop covered several times less
    # simulated distance there and the fish never reached the food (this test
    # passed on two of the three CI platforms). Rewinding _last by a fixed
    # amount instead hands draw() an exact timestep on every platform, and
    # runs instantly.
    canvas = _FakeCanvas()
    for _ in _simulated_frames(f, seconds=30.0):
        f.draw(canvas)
        if not foods:
            break

    assert not foods  # the food got eaten, not perpetually dodged


def test_not_relaxing_when_relax_window_has_not_started():
    bounds = (0.0, 0.0, 50.0, 50.0)
    spot = aq.Decoration(30.0, 5.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock")
    f = _neutral_fish(5.0, 5.0, bounds, decorations=[spot])
    f.favorite_decoration = spot
    f._next_turn = float("inf")
    f._next_relax_check = float("inf")  # never rolls again
    f._relaxing_until = 0.0  # never started relaxing
    f.vx, f.vy = 1.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert (f.vx, f.vy) == (1.0, 0.0)  # untouched -- no food/mouse/relax active


def test_inspector_shows_favorite_spot_kind():
    from cozy_tui import App

    app = App(full=False, size="400x300")
    spot = aq.Decoration(0.0, 0.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock")
    f = _neutral_fish(5.0, 5.0, decorations=[spot])
    f.favorite_decoration = spot

    box = aq._build_inspector(
        app, f, lambda fish: None, lambda fish: None, {}, lambda fish, kind: None
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert any("Favorite spot: Rock" in t for t in labels)


def test_inspector_shows_none_yet_with_no_favorite_spot():
    from cozy_tui import App

    app = App(full=False, size="400x300")
    f = _neutral_fish(5.0, 5.0, decorations=[])

    box = aq._build_inspector(
        app, f, lambda fish: None, lambda fish: None, {}, lambda fish, kind: None
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert any("Favorite spot: none yet" in t for t in labels)


# ── Phase 3: growth, sell value, buying decorations ───────────────────────────


def test_baby_fish_uses_the_universal_fry_glyph():
    f = _neutral_fish(5.0, 5.0)
    assert f.growth_stage == "Baby"
    f.vx = 1.0
    assert f._glyph() == aq.BABY_RIGHT
    f.vx = -1.0
    assert f._glyph() == aq.BABY_LEFT


def test_fish_grows_up_and_uses_its_real_glyph():
    f = _neutral_fish(5.0, 5.0)
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 32
    assert f.growth_stage == "Adult"
    f.vx = 1.0
    assert f._glyph() == "><>"


def test_fish_sell_value_scales_with_growth_stage():
    f = _neutral_fish(5.0, 5.0)
    f.price = 100
    assert f.growth_stage == "Baby"
    assert f.sell_value == 25
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 12
    assert f.growth_stage == "Juvenile"
    assert f.sell_value == 60
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 20  # cumulative 32 days -- Adult
    assert f.growth_stage == "Adult"
    assert f.sell_value == 100


def test_predator_fish_starts_already_adult():
    # Every predator (Shark) comes from a Shop purchase -- never bred,
    # never a starter (both exclude predators) -- so showing up as a
    # generic Baby blob for several minutes would undercut the whole
    # point of paying for one. See Fish.__init__'s is_predator check.
    f = _neutral_fish(5.0, 5.0, is_predator=True)
    assert f.growth_stage == "Adult"


def test_non_predator_fish_is_unaffected_and_still_starts_as_baby():
    f = _neutral_fish(5.0, 5.0, is_predator=False)
    assert f.growth_stage == "Baby"


def test_fish_reaches_elder_and_sells_for_less_than_an_adult():
    f = _neutral_fish(5.0, 5.0)
    f.price = 100
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 60
    assert f.growth_stage == "Elder"
    assert f.sell_value == 80  # 0.8x -- worth a bit less than an Adult's 100


def test_predator_fish_starts_adult_not_elder():
    # Regression: Fish.__init__ used to compute the Shark-starts-grown-up
    # age via GROWTH_STAGES[-1], which quietly became Elder once that stage
    # was appended -- a brand new Shark must still start exactly Adult.
    f = _neutral_fish(5.0, 5.0, is_predator=True)
    assert f.growth_stage == "Adult"


def test_elder_fish_moves_slower():
    f = _neutral_fish(5.0, 5.0)
    f.speed = 10.0
    f.personality = "Explorer"  # no Lazy multiplier to isolate Elder's own
    young_speed = f._effective_speed()
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 60
    assert f.growth_stage == "Elder"
    assert f._effective_speed() == pytest.approx(young_speed * aq.ELDER_SPEED_MULT)


def test_decoration_sell_value_is_half_its_price():
    d = aq.Decoration(
        0.0, 0.0, aq.CASTLE_ART, aq.CASTLE_COLORS, kind="Castle", price=100
    )
    assert d.sell_value == 50


def test_decoration_at_finds_a_decoration_by_bounding_box():
    d = aq.Decoration(10.0, 5.0, aq.CASTLE_ART, aq.CASTLE_COLORS, kind="Castle")
    w, h = d.natural_width(1), d.natural_height(1)
    assert aq.decoration_at([d], 10, 5) is d
    assert aq.decoration_at([d], 10 + w - 1, 5 + h - 1) is d
    assert aq.decoration_at([d], 10 + w, 5) is None
    assert aq.decoration_at([d], 10, 5 + h) is None


def test_decoration_at_empty_list_is_none():
    assert aq.decoration_at([], 0, 0) is None


def test_decoration_inspector_shows_sell_value_and_sell_button_works():
    from cozy_tui import App

    app = App(full=False, size="300x200")
    d = aq.Decoration(0.0, 0.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock", price=12)
    sold = []

    box = aq._build_decoration_inspector(app, d, [], sold.append, lambda d: None)
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert any("Sell value: $6" in t for t in labels)

    buttons = [c for c in box.children if c.__class__.__name__ == "Button"]
    app.open_overlay(box)
    buttons[0].on_mouse_click()  # Sell -> opens a confirm dialog
    confirm = app._overlays[-1].widget
    confirm.on_key("y")

    assert sold == [d]
    assert not app._overlays  # both the confirm and the inspector box closed


def test_decoration_shop_items_have_expected_kinds_and_prices():
    kinds = {item.kind: item.price for item in aq.DECORATION_SHOP_ITEMS}
    assert kinds == {"Plant": 10, "Driftwood": 15, "Rock": 12, "Castle": 100}


def test_decoration_catalog_matches_shop_items():
    for item in aq.DECORATION_SHOP_ITEMS:
        assert aq.DECORATION_CATALOG[item.kind] is item


# ── Phase 3: attractiveness / visitor income ──────────────────────────────────


def _fish_with_price(price):
    f = _neutral_fish(0.0, 0.0)
    f.price = price
    return f


def test_attractiveness_common_fish():
    assert aq.compute_attractiveness(
        [_fish_with_price(20)], [], [aq.Food(0.0, 0.0)]
    ) == (aq.ATTRACTIVENESS_PER_FISH)


def test_attractiveness_rare_fish_worth_more():
    assert (
        aq.compute_attractiveness(
            [_fish_with_price(aq.RARE_PRICE_THRESHOLD)], [], [aq.Food(0.0, 0.0)]
        )
        == aq.ATTRACTIVENESS_PER_RARE_FISH
    )


def test_attractiveness_decorations_by_kind():
    decs = [
        aq.Decoration(0.0, 0.0, aq.PLANT_ART, aq.PLANT_COLORS, kind="Plant"),
        aq.Decoration(0.0, 0.0, aq.CASTLE_ART, aq.CASTLE_COLORS, kind="Castle"),
    ]
    assert aq.compute_attractiveness([], decs, [aq.Food(0.0, 0.0)]) == (
        aq.ATTRACTIVENESS_BY_DECORATION["Plant"]
        + aq.ATTRACTIVENESS_BY_DECORATION["Castle"]
    )


def test_attractiveness_clean_tank_bonus_when_no_food_left():
    assert aq.compute_attractiveness([], [], []) == aq.CLEAN_TANK_ATTRACTIVENESS


def test_attractiveness_no_clean_bonus_with_food_still_out():
    assert aq.compute_attractiveness([], [], [aq.Food(0.0, 0.0)]) == 0


def test_visitor_income_zero_attractiveness_means_no_visitors_or_donations():
    visitors, ticket_sales, donations = aq.compute_visitor_income(0)
    assert (visitors, ticket_sales, donations) == (0, 0, 0)


def test_visitor_income_scales_with_attractiveness():
    attractiveness = aq.VISITORS_PER_ATTRACTIVENESS * 3
    visitors, ticket_sales, donations = aq.compute_visitor_income(attractiveness)
    assert visitors == 3
    assert ticket_sales == 3 * aq.TICKET_PRICE
    assert 0 <= donations <= 3 * aq.DONATION_PER_VISITOR_MAX


def test_visitor_income_donations_stay_in_bounds_over_many_rolls():
    attractiveness = aq.VISITORS_PER_ATTRACTIVENESS * 5
    for _ in range(200):
        visitors, _ticket, donations = aq.compute_visitor_income(attractiveness)
        assert 0 <= donations <= visitors * aq.DONATION_PER_VISITOR_MAX


def test_roll_visitor_donation_no_visitors_never_donates():
    for _ in range(50):
        assert aq.roll_visitor_donation(0) == 0


def test_roll_visitor_donation_stays_in_bounds_over_many_rolls():
    for _ in range(500):
        amount = aq.roll_visitor_donation(5, day_seconds=10)
        assert 0 <= amount <= aq.DONATION_PER_VISITOR_MAX


def test_roll_visitor_donation_fires_when_the_gate_roll_wins(monkeypatch):
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)
    amount = aq.roll_visitor_donation(1, day_seconds=100)
    assert 1 <= amount <= aq.DONATION_PER_VISITOR_MAX


def test_roll_visitor_donation_stays_silent_when_the_gate_roll_loses(monkeypatch):
    monkeypatch.setattr(aq.random, "random", lambda: 0.999999)
    assert aq.roll_visitor_donation(1, day_seconds=100) == 0


# ── Phase 3: Daily Summary ─────────────────────────────────────────────────────


def test_daily_summary_shows_all_line_items():
    from cozy_tui import Style

    box = aq._build_daily_summary(Style(), 12, 18, 42, 13, 10, 20, 45)
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert box.title == "Day 12"
    assert any("Visitors: 18" in t for t in labels)
    assert any("Ticket Sales: +$42" in t for t in labels)
    assert any("Donations Today: +$13" in t for t in labels)
    assert any("Maintenance Grant: +$10" in t for t in labels)
    assert any("Food Expenses: -$20" in t for t in labels)
    assert any("Net Profit: +$45" in t for t in labels)


def test_daily_summary_shows_negative_net_profit_without_a_plus_sign():
    from cozy_tui import Style

    box = aq._build_daily_summary(Style(), 1, 0, 0, 0, 10, 30, -20)
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert any("Net Profit: -$20" in t for t in labels)


# ── Phase 3: Settings / Emergency Aquarium Welfare ────────────────────────────


def test_should_grant_welfare_only_when_fully_bankrupt_and_enabled():
    assert aq.should_grant_welfare(0, 0, 0, True) is True
    assert aq.should_grant_welfare(1, 0, 0, True) is False
    assert aq.should_grant_welfare(0, 1, 0, True) is False
    assert aq.should_grant_welfare(0, 0, 1, True) is False
    assert aq.should_grant_welfare(0, 0, 0, False) is False


def test_settings_checkbox_toggles_state():
    from cozy_tui import App

    app = App(full=False, size="400x200")
    state = {"welfare_enabled": True}
    box = aq._build_settings(
        app, state, None, lambda: None, lambda: None, lambda: None, lambda: None
    )
    checkbox = next(c for c in box.children if c.__class__.__name__ == "Checkbox")
    assert checkbox.checked is True

    checkbox.on_key(" ")
    assert state["welfare_enabled"] is False
    assert checkbox.checked is False

    checkbox.on_key(" ")
    assert state["welfare_enabled"] is True


def test_settings_close_button_closes_the_overlay():
    from cozy_tui import App

    app = App(full=False, size="400x200")
    state = {"welfare_enabled": True}
    box = aq._build_settings(
        app, state, None, lambda: None, lambda: None, lambda: None, lambda: None
    )
    app.open_overlay(box)
    assert app._overlays

    close_btn = next(c for c in box.children if c.__class__.__name__ == "Button")
    close_btn.on_mouse_click()
    assert not app._overlays


# ── Phase 9: relationship scores ──────────────────────────────────────────────


def _befriend(a, b, score=None):
    """Test helper: give two fish a mutual bond at (or above) the given
    tier, replacing the old `f.friend = mate; mate.friend = f` pattern --
    .friend/.rival are now read-only, score-derived views (see
    relationships.best_bond()/worst_bond())."""
    aq.set_relationship(
        a, b, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD if score is None else score
    )


def _make_rivals(a, b, score=None):
    aq.set_relationship(
        a, b, aq.RELATIONSHIP_RIVAL_THRESHOLD if score is None else score
    )


def test_relationship_state_boundaries():
    assert aq.relationship_state(-50.0) == ("Rival", "😠")
    assert aq.relationship_state(-49.9) == ("Dislikes", "😒")
    assert aq.relationship_state(-15.0) == ("Dislikes", "😒")
    assert aq.relationship_state(-14.9) == ("Neutral", "😐")
    assert aq.relationship_state(14.9) == ("Neutral", "😐")
    assert aq.relationship_state(15.0) == ("Friend", "🙂")
    assert aq.relationship_state(49.9) == ("Friend", "🙂")
    assert aq.relationship_state(50.0) == ("Best Friend", "❤️")


def test_new_fish_start_with_no_relationships():
    f = _neutral_fish(0.0, 0.0)
    assert f.relationships == {}
    assert f.friend is None
    assert f.rival is None


def test_get_relationship_returns_the_same_object_from_either_side():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    rel = aq.get_relationship(a, b)
    assert a.relationships[b] is rel
    assert b.relationships[a] is rel
    assert aq.get_relationship(b, a) is rel


def test_set_relationship_clamps_to_the_valid_range():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    aq.set_relationship(a, b, 500.0)
    assert a.relationships[b].score == aq.RELATIONSHIP_MAX
    aq.set_relationship(a, b, -500.0)
    assert a.relationships[b].score == aq.RELATIONSHIP_MIN


def test_remember_applies_delta_and_logs_the_reason():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    a.personality = b.personality = "Greedy"  # avoid Lazy dampening
    aq.remember(a, b, 10.0, "Did a nice thing")

    rel = a.relationships[b]
    assert rel.score == 10.0
    assert rel.memories == ["Did a nice thing"]


def test_remember_bounds_the_memory_log():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    a.personality = b.personality = "Greedy"
    for i in range(aq.RELATIONSHIP_MEMORY_LIMIT + 3):
        aq.remember(a, b, 1.0, f"reason {i}")

    memories = a.relationships[b].memories
    assert len(memories) == aq.RELATIONSHIP_MEMORY_LIMIT
    assert memories[-1] == f"reason {aq.RELATIONSHIP_MEMORY_LIMIT + 2}"  # newest kept


def test_remember_dampens_when_either_fish_is_lazy():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    a.personality = "Lazy"
    b.personality = "Greedy"
    aq.remember(a, b, 10.0, "reason")

    assert a.relationships[b].score == 10.0 * aq.RELATIONSHIP_LAZY_DAMPING


def test_record_wake_up_gives_playful_a_bonus():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    a.personality, b.personality = "Playful", "Greedy"
    aq.record_wake_up(a, b)
    assert a.relationships[b].score == aq.WAKE_UP_SCORE_PLAYFUL

    c = _neutral_fish(0.0, 0.0)
    d = _neutral_fish(1.0, 0.0)
    c.personality, d.personality = "Greedy", "Greedy"
    aq.record_wake_up(c, d)
    assert c.relationships[d].score == aq.WAKE_UP_SCORE


def test_record_slept_together_awards_a_small_bump():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    a.personality = b.personality = "Greedy"
    aq.record_slept_together(a, b)
    assert a.relationships[b].score == aq.SLEPT_TOGETHER_SCORE
    assert "Slept together" in a.relationships[b].memories[0]


def test_record_gave_up_home_gives_friendly_a_bonus():
    generous = _neutral_fish(0.0, 0.0)
    beneficiary = _neutral_fish(1.0, 0.0)
    generous.personality = "Friendly"
    beneficiary.personality = "Greedy"
    aq.record_gave_up_home(generous, beneficiary)
    assert generous.relationships[beneficiary].score == (
        aq.GAVE_UP_HOME_SCORE * aq.RELATIONSHIP_FRIENDLY_BONUS
    )


def test_best_bond_requires_at_least_friend_level():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    a.personality = b.personality = "Greedy"
    aq.set_relationship(a, b, aq.RELATIONSHIP_FRIEND_THRESHOLD - 1.0)
    assert a.friend is None  # not quite Friend yet

    aq.set_relationship(a, b, aq.RELATIONSHIP_FRIEND_THRESHOLD)
    assert a.friend is b
    assert b.friend is a  # symmetric -- one shared score, not two opinions


def test_best_bond_picks_the_strongest_of_several():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    c = _neutral_fish(2.0, 0.0)
    a.personality = b.personality = c.personality = "Greedy"
    aq.set_relationship(a, b, aq.RELATIONSHIP_FRIEND_THRESHOLD)
    aq.set_relationship(a, c, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)

    assert a.friend is c


def test_worst_bond_requires_rival_level():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    a.personality = b.personality = "Greedy"
    aq.set_relationship(a, b, aq.RELATIONSHIP_RIVAL_THRESHOLD + 1.0)
    assert a.rival is None  # Dislikes, not quite Rival

    aq.set_relationship(a, b, aq.RELATIONSHIP_RIVAL_THRESHOLD)
    assert a.rival is b
    assert b.rival is a


def test_find_eligible_waker_excludes_rivals_and_dislikes():
    sleeper = _neutral_fish(0.0, 0.0)
    rival = _neutral_fish(1.0, 0.0)
    disliker = _neutral_fish(2.0, 0.0)
    aq.set_relationship(sleeper, rival, aq.RELATIONSHIP_RIVAL_THRESHOLD)
    aq.set_relationship(sleeper, disliker, aq.RELATIONSHIP_DISLIKE_THRESHOLD)

    waker, tier = aq.find_eligible_waker(sleeper, [rival, disliker])

    assert (waker, tier) == (None, None)


def test_find_eligible_waker_picks_the_strongest_bond():
    sleeper = _neutral_fish(0.0, 0.0)
    neutral_mate = _neutral_fish(1.0, 0.0)
    friend = _neutral_fish(2.0, 0.0)
    aq.set_relationship(sleeper, neutral_mate, 0.0)
    aq.set_relationship(sleeper, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD)

    waker, tier = aq.find_eligible_waker(sleeper, [neutral_mate, friend])

    assert waker is friend
    assert tier == "Friend"


def test_find_eligible_waker_reports_neutral_tier():
    sleeper = _neutral_fish(0.0, 0.0)
    neutral_mate = _neutral_fish(1.0, 0.0)
    aq.set_relationship(sleeper, neutral_mate, 0.0)

    waker, tier = aq.find_eligible_waker(sleeper, [neutral_mate])

    assert waker is neutral_mate
    assert tier == "Neutral"


def test_find_eligible_waker_with_no_candidates_at_all():
    sleeper = _neutral_fish(0.0, 0.0)
    assert aq.find_eligible_waker(sleeper, []) == (None, None)


def test_find_eligible_waker_excludes_a_sleepy_tankmate():
    # Regression: a Sleepy tankmate sharing the same container overnight is
    # itself about to be held asleep -- picking it as the designated waker
    # let one sleeping fish "wake up" another sleeping fish. Checked via
    # is_sleepy (not just is_asleep), since the only caller
    # (_start_sleepy_holds) evaluates every Sleepy+housed tankmate in one
    # synchronous pass -- a candidate not yet reached by that pass would
    # still read is_asleep=False (its own _holding_asleep isn't set yet)
    # despite being about to become held right alongside the sleeper.
    sleeper = _neutral_fish(0.0, 0.0)
    sleepy_mate = _neutral_fish(1.0, 0.0)
    sleepy_mate.is_sleepy = True
    aq.set_relationship(sleeper, sleepy_mate, aq.RELATIONSHIP_FRIEND_THRESHOLD)

    waker, tier = aq.find_eligible_waker(sleeper, [sleepy_mate])

    assert (waker, tier) == (None, None)


def test_find_eligible_waker_excludes_a_currently_asleep_tankmate():
    sleeper = _neutral_fish(0.0, 0.0)
    drowsy_mate = _neutral_fish(
        1.0, 0.0, environment={"phase": "Night", "temperature": 23.0}
    )
    aq.set_relationship(sleeper, drowsy_mate, aq.RELATIONSHIP_FRIEND_THRESHOLD)
    assert drowsy_mate.is_asleep

    waker, tier = aq.find_eligible_waker(sleeper, [drowsy_mate])

    assert (waker, tier) == (None, None)


def test_roll_wake_threshold_stays_in_the_tiers_own_range():
    for _ in range(100):
        assert (
            aq.WAKE_CHANCES_FRIEND[0]
            <= aq.roll_wake_threshold("Friend")
            <= aq.WAKE_CHANCES_FRIEND[1]
        )
        assert (
            aq.WAKE_CHANCES_NEUTRAL[0]
            <= aq.roll_wake_threshold("Neutral")
            <= aq.WAKE_CHANCES_NEUTRAL[1]
        )


def test_resolve_wake_attempt_always_succeeds_once_threshold_is_used_up(monkeypatch):
    # Force the "resist" roll every time -- even so, once attempts_used
    # reaches the threshold, the wake must succeed anyway.
    monkeypatch.setattr(
        aq.random, "random", lambda: 0.0
    )  # < SLEEPY_RESIST_CHANCE always
    assert aq.resolve_wake_attempt(attempts_used=0, threshold=3) is False
    assert aq.resolve_wake_attempt(attempts_used=2, threshold=3) is False
    assert aq.resolve_wake_attempt(attempts_used=3, threshold=3) is True
    assert aq.resolve_wake_attempt(attempts_used=10, threshold=3) is True


def test_resolve_wake_attempt_can_succeed_early(monkeypatch):
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)  # >= SLEEPY_RESIST_CHANCE
    assert aq.resolve_wake_attempt(attempts_used=0, threshold=5) is True


def test_decay_relationships_nudges_scores_toward_zero():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    c = _neutral_fish(2.0, 0.0)
    aq.set_relationship(a, b, 10.0)
    aq.set_relationship(a, c, -10.0)

    aq.decay_relationships([a, b, c])

    assert a.relationships[b].score == 10.0 - aq.RELATIONSHIP_DECAY_PER_DAY
    assert a.relationships[c].score == -10.0 + aq.RELATIONSHIP_DECAY_PER_DAY


def test_decay_relationships_does_not_overshoot_past_zero():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    aq.set_relationship(a, b, 0.5)  # smaller than one day's decay step

    aq.decay_relationships([a, b])

    assert a.relationships[b].score == 0.0


def test_clear_relationships_removes_the_pair_entirely():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    c = _neutral_fish(2.0, 0.0)
    a.personality = b.personality = c.personality = "Greedy"
    _befriend(a, b)
    _make_rivals(c, b)

    aq.clear_relationships(b, [a, c])

    assert b not in a.relationships
    assert a.friend is None
    assert b not in c.relationships
    assert c.rival is None


def test_clear_relationships_leaves_unrelated_fish_untouched():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    c = _neutral_fish(2.0, 0.0)
    _befriend(a, b)

    aq.clear_relationships(c, [a, b])

    assert a.friend is b
    assert b.friend is a


def _grown_fish(x=0.0, y=0.0, is_predator=False):
    f = _neutral_fish(x, y)
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 32  # breeding eligibility needs Adult
    f.is_predator = is_predator
    return f


def test_find_breeding_pairs_requires_at_least_friend_level():
    a = _grown_fish()
    b = _grown_fish()
    aq.set_relationship(a, b, aq.RELATIONSHIP_FRIEND_THRESHOLD - 1.0)
    assert aq.find_breeding_pairs([a, b]) == []


def test_find_breeding_pairs_finds_a_friend_adult_pair():
    a = _grown_fish()
    b = _grown_fish()
    _befriend(a, b)
    pairs = aq.find_breeding_pairs([a, b])
    assert len(pairs) == 1
    assert set(pairs[0]) == {a, b}


def test_find_breeding_pairs_excludes_babies():
    a = _grown_fish()
    b = _neutral_fish(1.0, 0.0)  # freshly made -- still a Baby
    _befriend(a, b)
    assert aq.find_breeding_pairs([a, b]) == []


def test_find_breeding_pairs_excludes_predators():
    a = _grown_fish()
    b = _grown_fish(is_predator=True)
    _befriend(a, b)
    assert aq.find_breeding_pairs([a, b]) == []


def test_find_breeding_pairs_each_pair_once():
    a = _grown_fish()
    b = _grown_fish()
    _befriend(a, b)
    pairs = aq.find_breeding_pairs([a, b, b, a])  # duplicated on purpose
    assert len(pairs) == 1


def test_find_mutual_friend_pairs_only_returns_friend_or_better():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    c = _neutral_fish(2.0, 0.0)
    _befriend(a, b)
    aq.set_relationship(
        a, c, aq.RELATIONSHIP_FRIEND_THRESHOLD - 1.0
    )  # not quite Friend

    pairs = aq.find_mutual_friend_pairs([a, b, c])

    assert len(pairs) == 1
    assert set(pairs[0]) == {a, b}


def test_find_mutual_friend_pairs_deduplicates():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    _befriend(a, b)

    pairs = aq.find_mutual_friend_pairs([a, b])

    assert len(pairs) == 1


def test_choose_baby_species_name_is_one_of_the_parents():
    a = _grown_fish()
    a.species_name = "Goldfish"
    b = _grown_fish()
    b.species_name = "Betta"
    names = {aq.choose_baby_species_name(a, b) for _ in range(30)}
    assert names <= {"Goldfish", "Betta"}
    assert len(names) == 2  # statistically both should show up


# ── Phase 4: steering (rival-fleeing, friend-following, rival food boost) ─────


def test_rival_scares_regardless_of_personality():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(6.0, 5.0, bounds)
    rival = _neutral_fish(5.0, 5.0, bounds)
    f.personality = "Explorer"  # deliberately not Shy
    aq.set_relationship(f, rival, aq.RELATIONSHIP_RIVAL_THRESHOLD)
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # fled away from the rival at lower x


def test_rival_out_of_range_does_not_scare():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(6.0, 5.0, bounds)
    rival = _neutral_fish(40.0, 5.0, bounds)  # far beyond RIVAL_FLEE_RADIUS
    f.personality = "Explorer"
    aq.set_relationship(f, rival, aq.RELATIONSHIP_RIVAL_THRESHOLD)
    f._next_turn = float("inf")
    f.vx, f.vy = 1.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert (f.vx, f.vy) == (1.0, 0.0)


def test_mouse_scare_takes_priority_over_rival_scare():
    bounds = (0.0, 0.0, 50.0, 50.0)
    mouse_pos = {"x": 5.0, "y": 5.0}
    f = _neutral_fish(6.0, 5.0, bounds, mouse_pos=mouse_pos)
    rival = _neutral_fish(6.0, 20.0, bounds)  # far below, would flee -y if chosen
    f.personality = "Shy"
    aq.set_relationship(f, rival, aq.RELATIONSHIP_RIVAL_THRESHOLD)
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # fled the mouse (+x), not the distant rival


def test_friend_following_when_nothing_more_urgent():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(5.0, 5.0, bounds)
    friend = _neutral_fish(20.0, 5.0, bounds)
    aq.set_relationship(f, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # drifting toward the friend at higher x


def test_food_seeking_takes_priority_over_friend_following():
    bounds = (0.0, 0.0, 50.0, 50.0)
    foods = [aq.Food(5.0, 30.0)]  # straight up
    f = _neutral_fish(5.0, 5.0, bounds, foods=foods)
    friend = _neutral_fish(20.0, 5.0, bounds)  # to the right
    aq.set_relationship(f, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vy > 0.0  # chasing the food (+y), not the friend (+x)


def test_rival_gives_a_food_speed_boost():
    bounds = (0.0, 0.0, 50.0, 50.0)

    with_rival = _neutral_fish(5.0, 5.0, bounds)
    with_rival.foods = [aq.Food(30.0, 5.0)]
    aq.set_relationship(
        with_rival,
        _neutral_fish(40.0, 40.0, bounds),  # far away, not actively fleeing
        aq.RELATIONSHIP_RIVAL_THRESHOLD,
    )
    with_rival._next_turn = float("inf")
    with_rival.speed = 5.0
    with_rival.vx, with_rival.vy = 0.0, 0.0

    without_rival = _neutral_fish(5.0, 5.0, bounds)
    without_rival.foods = [aq.Food(30.0, 5.0)]
    without_rival._next_turn = float("inf")
    without_rival.speed = 5.0
    without_rival.vx, without_rival.vy = 0.0, 0.0

    _age(with_rival)
    _age(without_rival)
    with_rival.draw(_FakeCanvas())
    without_rival.draw(_FakeCanvas())

    assert with_rival.vx > without_rival.vx


# ── Phase 4: Inspector / tooltip relationship display ─────────────────────────


def test_inspector_shows_friend_and_rival_lines():
    from cozy_tui import App

    app = App(full=False, size="400x300")
    f = _neutral_fish(5.0, 5.0)
    friend = _neutral_fish(1.0, 1.0)
    friend.display_name = "Bob"
    rival = _neutral_fish(2.0, 2.0)
    rival.display_name = "Kevin"
    aq.set_relationship(f, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD)
    aq.set_relationship(f, rival, aq.RELATIONSHIP_RIVAL_THRESHOLD)

    box = aq._build_inspector(
        app, f, lambda fish: None, lambda fish: None, {}, lambda fish, kind: None
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert any("Friend: Bob" in t for t in labels)
    assert any("Rival: Kevin" in t for t in labels)


def test_inspector_omits_friend_rival_lines_when_absent():
    from cozy_tui import App

    app = App(full=False, size="400x300")
    f = _neutral_fish(5.0, 5.0)

    box = aq._build_inspector(
        app, f, lambda fish: None, lambda fish: None, {}, lambda fish, kind: None
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert not any(t.startswith("Friend:") for t in labels)
    assert not any(t.startswith("Rival:") for t in labels)


def test_describe_fish_includes_friend_hint():
    f = _neutral_fish(5.0, 5.0)
    friend = _neutral_fish(1.0, 1.0)
    friend.display_name = "Bob"
    aq.set_relationship(f, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD)
    assert "Bob" in aq.describe_fish(f)


def test_describe_fish_includes_rival_hint_when_no_friend():
    f = _neutral_fish(5.0, 5.0)
    rival = _neutral_fish(1.0, 1.0)
    rival.display_name = "Kevin"
    aq.set_relationship(f, rival, aq.RELATIONSHIP_RIVAL_THRESHOLD)
    assert "Kevin" in aq.describe_fish(f)


# ── Saves: full round trip + regression tests ─────────────────────────────────


def _headless_app(tmp_path, monkeypatch):
    """Boot the real main() against a temp save directory (never the user's
    real ~/.termquarium) and dismiss the start menu, returning the live App."""
    monkeypatch.setattr(aq.Path, "home", lambda: tmp_path)
    captured = {}
    monkeypatch.setattr(aq.App, "run", lambda self: captured.__setitem__("app", self))
    aq.main()
    app = captured["app"]
    start_menu = app._overlays[-1].widget
    new_btn = next(
        c
        for c in start_menu.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "New Aquarium"
    )
    new_btn.on_mouse_click()
    return app


def test_save_then_load_round_trip_preserves_names_species_and_friendship(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    fishes[0].display_name = "Steve"
    fishes[1].display_name = "Bob"
    aq.set_relationship(fishes[0], fishes[1], aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)

    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = "Steve's Kingdom"
    prompt.on_key(aq.Key.ENTER)

    assert (tmp_path / ".termquarium" / "saves" / "Steve's Kingdom.json").exists()

    app._key_handlers["l"]()
    load_box = app._overlays[-1].widget
    load_btn = next(
        c
        for c in load_box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Load"
    )
    load_btn.on_mouse_click()

    fishes_after = [w for w in app.widgets if isinstance(w, aq.Fish)]
    steve = next(f for f in fishes_after if f.display_name == "Steve")
    bob = next(f for f in fishes_after if f.display_name == "Bob")
    assert steve.friend is bob
    assert bob.friend is steve
    assert steve.species_name in [s.name for s in aq.SHOP_ITEMS]


def test_save_then_load_round_trip_preserves_relationship_score_and_memories(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    fishes[0].display_name = "Steve"
    fishes[1].display_name = "Bob"
    aq.remember(fishes[0], fishes[1], 20.0, "Slept together for the night")

    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = "Steve and Bob"
    prompt.on_key(aq.Key.ENTER)

    app._key_handlers["l"]()
    load_box = app._overlays[-1].widget
    load_btn = next(
        c
        for c in load_box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Load"
    )
    load_btn.on_mouse_click()

    fishes_after = [w for w in app.widgets if isinstance(w, aq.Fish)]
    steve = next(f for f in fishes_after if f.display_name == "Steve")
    bob = next(f for f in fishes_after if f.display_name == "Bob")
    rel = steve.relationships[bob]
    assert rel.score > 0
    assert "Slept together for the night" in rel.memories


def test_load_resyncs_the_daily_tick_instead_of_giving_a_fresh_full_day(
    tmp_path, monkeypatch
):
    # Regression: the Shop's stock rotation rides on the same daily-tick
    # timer as aging/visitors/etc (_refresh_shop_stock(), called from
    # _daily_tick()). _load_snapshot() used to restore day_count without
    # touching that timer, so a save made moments before the timer was due
    # would come back from Load facing a fresh full AGE_SECONDS_PER_DAY wait
    # -- the Shop "refills too late". Loading should instead pick up with
    # whatever time was actually left in the saved day.
    app = _headless_app(tmp_path, monkeypatch)
    daily_timer = next(t for t in app._timers if t.interval == aq.AGE_SECONDS_PER_DAY)
    daily_timer.deadline = time.monotonic() + 5.0  # almost due when saved

    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = "Almost Rotating"
    prompt.on_key(aq.Key.ENTER)

    saved = json.loads(
        (tmp_path / ".termquarium" / "saves" / "Almost Rotating.json").read_text()
    )
    assert saved["aquarium"]["day_tick_remaining"] == pytest.approx(5.0, abs=1.0)

    # Simulate what an unpatched session would have left running: a stale
    # timer with a nearly-full day still to go, as if the game had just
    # been (re)launched instead of mid-day when the save happened.
    daily_timer.deadline = time.monotonic() + aq.AGE_SECONDS_PER_DAY

    app._key_handlers["l"]()
    load_box = app._overlays[-1].widget
    load_btn = next(
        c
        for c in load_box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Load"
    )
    load_btn.on_mouse_click()

    resynced = next(
        t
        for t in app._timers
        if t.alive and t.interval is None and t is not daily_timer
    )
    remaining = resynced.deadline - time.monotonic()
    assert remaining < aq.AGE_SECONDS_PER_DAY / 2


def test_emergency_welfare_fires_even_with_zero_fish(tmp_path, monkeypatch):
    # Regression: _check_emergency_welfare() must run every tick regardless
    # of whether any fish are currently hungry -- it used to be nested
    # inside a "for f in hungry_fish" loop, so it silently never ran at all
    # in the exact all-fish-gone bankruptcy scenario it exists for.
    app = _headless_app(tmp_path, monkeypatch)
    for f in [w for w in app.widgets if isinstance(w, aq.Fish)]:
        app.widgets.remove(f)
    monkeypatch.setattr(aq, "should_grant_welfare", lambda *a, **k: True)

    stats_label = next(
        w for w in app.widgets if getattr(w, "text", "").startswith("Money")
    )
    before = stats_label.text

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert stats_label.text != before
    assert any(isinstance(w, aq.Fish) for w in app.widgets)


def test_hungry_warning_toast_is_a_complete_message(tmp_path, monkeypatch):
    # Regression: the toast text used to be a truncated f"{name} are " with
    # nothing after it.
    app = _headless_app(tmp_path, monkeypatch)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    for f in [w for w in app.widgets if isinstance(w, aq.Fish)]:
        f.hunger = aq.HUNGER_WARNING_THRESHOLD + 1

    # Hunger only actually decays once every HUNGER_TICK_SECONDS worth of
    # 1.0s ticks (see _per_second_tick()'s hunger_tick_accum) -- three
    # ticks is one hunger application.
    second_timer = next(t for t in app._timers if t.interval == 1.0)
    for _ in range(int(aq.HUNGER_TICK_SECONDS)):
        second_timer.callback()

    hungry_toasts = [t for t in toasts if "hungry" in t]
    assert hungry_toasts
    assert all(t.strip().endswith("hungry!") for t in hungry_toasts)


def _open_shop_and_buy(app, kind):
    app._key_handlers["s"]()
    shop = app._overlays[-1].widget
    label = next(
        c for c in shop.children if c.__class__.__name__ == "Label" and kind in c.text
    )
    buy_btn = next(
        c
        for c in shop.children
        if c.__class__.__name__ == "Button"
        and c.text.strip() == "Buy"
        and c.y == label.y
    )
    buy_btn.on_mouse_click()
    app.close_overlay(shop)


def _open_inspector_for(app, f):
    app._mouse_handler(aq.MouseClick(f.x, f.y, 0))
    return app._overlays[-1].widget


def test_feeding_a_favorite_treat_gives_a_delighted_toast(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    axolotl = next(w for w in app.widgets if isinstance(w, aq.Fish))
    axolotl.species_name = "Axolotl"
    axolotl.favorite_foods = ("Brine Shrimp", "Bloodworms", "Worms")

    _open_shop_and_buy(app, "Brine Shrimp")

    inspector = _open_inspector_for(app, axolotl)
    feed_btn = next(
        c
        for c in inspector.children
        if c.__class__.__name__ == "Button" and "Brine Shrimp" in c.text
    )
    feed_btn.on_mouse_click()

    assert any("Favorite food" in t for t in toasts)


def test_feeding_a_non_favorite_treat_gives_the_plain_toast(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    fish.species_name = "Goldfish"
    fish.favorite_foods = ()

    _open_shop_and_buy(app, "Brine Shrimp")

    inspector = _open_inspector_for(app, fish)
    feed_btn = next(
        c
        for c in inspector.children
        if c.__class__.__name__ == "Button" and "Brine Shrimp" in c.text
    )
    feed_btn.on_mouse_click()

    assert not any("Favorite food" in t for t in toasts)
    assert any("Fed" in t and "Brine Shrimp" in t for t in toasts)


def test_feeding_a_favorite_treat_gives_both_the_fed_and_favorite_happiness_gain(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    axolotl = next(w for w in app.widgets if isinstance(w, aq.Fish))
    axolotl.species_name = "Axolotl"
    axolotl.favorite_foods = ("Brine Shrimp", "Bloodworms", "Worms")
    axolotl.happiness = 50.0

    _open_shop_and_buy(app, "Brine Shrimp")
    inspector = _open_inspector_for(app, axolotl)
    feed_btn = next(
        c
        for c in inspector.children
        if c.__class__.__name__ == "Button" and "Brine Shrimp" in c.text
    )
    feed_btn.on_mouse_click()

    assert (
        axolotl.happiness
        == 50.0 + aq.HAPPINESS_FED_GAIN + aq.HAPPINESS_FAVORITE_TREAT_GAIN
    )


def test_feeding_a_non_favorite_treat_gives_only_the_fed_happiness_gain(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    fish.species_name = "Goldfish"
    fish.favorite_foods = ()
    fish.happiness = 50.0

    _open_shop_and_buy(app, "Brine Shrimp")
    inspector = _open_inspector_for(app, fish)
    feed_btn = next(
        c
        for c in inspector.children
        if c.__class__.__name__ == "Button" and "Brine Shrimp" in c.text
    )
    feed_btn.on_mouse_click()

    assert fish.happiness == 50.0 + aq.HAPPINESS_FED_GAIN


# ── Achievements: end-to-end unlock checks ─────────────────────────────────────


def test_feeding_a_favorite_treat_unlocks_their_favorite_achievement(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    axolotl = next(w for w in app.widgets if isinstance(w, aq.Fish))
    axolotl.species_name = "Axolotl"
    axolotl.favorite_foods = ("Brine Shrimp", "Bloodworms", "Worms")

    _open_shop_and_buy(app, "Brine Shrimp")
    inspector = _open_inspector_for(app, axolotl)
    feed_btn = next(
        c
        for c in inspector.children
        if c.__class__.__name__ == "Button" and "Brine Shrimp" in c.text
    )
    feed_btn.on_mouse_click()

    assert "their_favorite" in aq.load_unlocked_achievements(home=tmp_path)


def test_feeding_pizza_unlocks_mystery_craving_achievement(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))

    _open_shop_and_buy(app, "Pizza")
    inspector = _open_inspector_for(app, fish)
    feed_btn = next(
        c
        for c in inspector.children
        if c.__class__.__name__ == "Button" and "Pizza" in c.text
    )
    feed_btn.on_mouse_click()

    assert "mystery_craving" in aq.load_unlocked_achievements(home=tmp_path)


def test_selling_a_fish_unlocks_first_sale_achievement(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    inspector = _open_inspector_for(app, fish)
    sell_btn = next(
        c
        for c in inspector.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Sell"
    )
    sell_btn.on_mouse_click()
    confirm = app._overlays[-1].widget
    confirm.on_key("y")

    assert "first_sale" in aq.load_unlocked_achievements(home=tmp_path)


def test_buying_an_axolotl_unlocks_first_axolotl_achievement(tmp_path, monkeypatch):
    # Regression: _seed_starter_aquarium() calls _refresh_shop_stock(), which
    # marks one random species "Out of Stock" (no Buy button) via an unseeded
    # random.sample() -- this test was flaky whenever that species happened to
    # be Axolotl itself. Force the rotation to land on some other species so
    # Axolotl's Buy button is always present here.
    monkeypatch.setattr(
        aq.random,
        "sample",
        lambda names, count: [n for n in names if n != "Axolotl"][:count],
    )
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["s"]()
    shop = app._overlays[-1].widget
    label = next(
        c
        for c in shop.children
        if c.__class__.__name__ == "Label" and c.text.startswith("Axolotl")
    )
    buy_btn = next(
        c
        for c in shop.children
        if c.__class__.__name__ == "Button"
        and c.text.strip() == "Buy"
        and c.y == label.y
    )
    buy_btn.on_mouse_click()

    assert "first_axolotl" in aq.load_unlocked_achievements(home=tmp_path)


def test_stress_test_reaching_the_cap_unlocks_full_house_achievement(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["z"]()

    assert "full_house" in aq.load_unlocked_achievements(home=tmp_path)


def test_setting_up_cloud_saves_unlocks_backed_up_achievement(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["g"]()
    settings = app._overlays[-1].widget
    setup_btn = next(
        c
        for c in settings.children
        if c.__class__.__name__ == "Button" and "Cloud" in c.text
    )
    setup_btn.on_mouse_click()

    assert "backed_up" in aq.load_unlocked_achievements(home=tmp_path)


def test_reaching_day_seven_unlocks_one_week_in_achievement(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    daily_timer = next(t for t in app._timers if t.interval == aq.AGE_SECONDS_PER_DAY)
    for _ in range(7):
        daily_timer.callback()

    assert "one_week_in" in aq.load_unlocked_achievements(home=tmp_path)


def test_breeding_a_baby_unlocks_first_baby_achievement(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    a, b = fishes[0], fishes[1]
    a.is_predator = b.is_predator = False
    a.birth_time -= aq.AGE_SECONDS_PER_DAY * 32  # breeding needs Adult
    b.birth_time -= aq.AGE_SECONDS_PER_DAY * 32  # breeding needs Adult
    aq.set_relationship(a, b, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)

    daily_timer = next(t for t in app._timers if t.interval == aq.AGE_SECONDS_PER_DAY)
    daily_timer.callback()

    assert "first_baby" in aq.load_unlocked_achievements(home=tmp_path)


def test_breeding_with_an_axolotl_parent_babies_inherit_favorite_foods(
    tmp_path, monkeypatch
):
    # Regression: _try_breeding() constructs its baby Fish(...) directly
    # rather than through fish.py's _make_fish, and was missing
    # favorite_foods=species.favorite_foods -- a baby bred from an Axolotl
    # parent would otherwise silently have no favorite foods.
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    a, b = fishes[0], fishes[1]
    a.species_name = "Axolotl"
    a.favorite_foods = ("Brine Shrimp", "Bloodworms", "Worms")
    a.is_predator = b.is_predator = False
    a.birth_time -= aq.AGE_SECONDS_PER_DAY * 32  # breeding needs Adult
    b.birth_time -= aq.AGE_SECONDS_PER_DAY * 32  # breeding needs Adult
    aq.set_relationship(a, b, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)
    monkeypatch.setattr(
        aq.random, "choice", lambda seq: "Axolotl" if "Axolotl" in seq else seq[0]
    )

    daily_timer = next(t for t in app._timers if t.interval == aq.AGE_SECONDS_PER_DAY)
    daily_timer.callback()

    babies = [f for f in app.widgets if isinstance(f, aq.Fish) and f not in fishes]
    assert babies
    assert babies[0].favorite_foods == ("Brine Shrimp", "Bloodworms", "Worms")


# ── Random events ────────────────────────────────────────────────────────────


def _force_random_event(monkeypatch, event_id):
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # always clears the roll
    monkeypatch.setattr(
        aq.random, "choice", lambda seq: event_id if event_id in seq else seq[0]
    )


def _fire_daily_tick(app):
    daily_timer = next(t for t in app._timers if t.interval == aq.AGE_SECONDS_PER_DAY)
    daily_timer.callback()


def test_lucky_find_event_toasts_and_adds_money(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    _force_random_event(monkeypatch, "lucky_find")

    _fire_daily_tick(app)

    assert any("loose change" in t for t in toasts)


def test_storm_event_bumps_every_fishs_hunger(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    for f in fishes:
        f.hunger = 90.0
    _force_random_event(monkeypatch, "storm")

    _fire_daily_tick(app)

    assert any("storm" in t.lower() for t in toasts)
    assert all(f.hunger == pytest.approx(90.0 - aq.STORM_HUNGER_BUMP) for f in fishes)


def _find_end_storm_timer(app):
    return next(
        t
        for t in app._timers
        if t.interval is None and getattr(t.callback, "__name__", "") == "_end_storm"
    )


def test_storm_event_sets_the_live_flag_and_later_ends_with_a_toast(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    _force_random_event(monkeypatch, "storm")

    _fire_daily_tick(app)

    # environment isn't exposed on app directly -- every Fish shares the
    # exact same dict, so reading it back off any one of them is exact.
    assert fish.environment["storm"] is True

    _find_end_storm_timer(app).callback()

    assert fish.environment["storm"] is False
    assert any("storm has ended" in t.lower() for t in toasts)


def test_lightning_flashes_during_a_live_storm_and_stops_once_it_ends(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    lightning = next(w for w in app.widgets if isinstance(w, aq.LightningField))
    _force_random_event(monkeypatch, "storm")
    _fire_daily_tick(app)

    lightning._next_flash = 0.0  # force an immediate flash
    app._compose()
    assert lightning._flash_until is not None

    _find_end_storm_timer(app).callback()
    app._compose()

    assert lightning._flash_until is None


def test_storm_cannot_restart_while_already_active(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    _force_random_event(monkeypatch, "storm")
    _fire_daily_tick(app)
    assert fish.environment["storm"] is True

    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    _fire_daily_tick(app)  # "storm" is no longer even a candidate while active

    assert not any("rolling in" in t for t in toasts)


def test_showing_off_event_toasts_about_a_fish(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    _force_random_event(monkeypatch, "showing_off")

    _fire_daily_tick(app)

    assert any("does a little spin" in t for t in toasts)


def test_stray_fish_event_adds_a_free_fish_with_no_rename_prompt(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    fish_before = len([w for w in app.widgets if isinstance(w, aq.Fish)])
    _force_random_event(monkeypatch, "stray_fish")

    _fire_daily_tick(app)

    fish_after = len([w for w in app.widgets if isinstance(w, aq.Fish)])
    assert fish_after == fish_before + 1
    assert any("wandered in overnight" in t for t in toasts)
    assert app._topmost_modal() is None  # a gift, not a purchase -- no rename prompt


def test_stray_fish_event_is_never_chosen_once_at_the_breeding_cap(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["z"]()  # stress test: fills up to STRESS_TEST_TARGET (50)
    fish_count = len([w for w in app.widgets if isinstance(w, aq.Fish)])
    assert fish_count >= aq.MAX_FISH_FOR_BREEDING
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    _force_random_event(monkeypatch, "stray_fish")

    _fire_daily_tick(app)

    assert not any("wandered in overnight" in t for t in toasts)


# ── Dreams (Phase 1) ─────────────────────────────────────────────────────────


def _force_night_transition(monkeypatch, fraction=0.9):
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: fraction)


def test_assign_dreams_gives_a_hunger_eligible_fish_a_dream_at_night(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    hungry, sleepy_ready = fishes[0], fishes[1]
    hungry.hunger = aq.SLEEP_HUNGER_THRESHOLD - 10.0  # too hungry to actually sleep
    sleepy_ready.hunger = 100.0
    _force_night_transition(monkeypatch)
    monkeypatch.setattr(
        aq.random, "random", lambda: 0.0
    )  # clears the DREAM_CHANCE gate

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert sleepy_ready.dream is not None
    assert hungry.dream is None  # never rolled -- too hungry to sleep tonight


def test_dreams_are_never_assigned_outside_the_dream_chance_roll(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    for f in fishes:
        f.hunger = 100.0
    _force_night_transition(monkeypatch)
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)  # always misses DREAM_CHANCE

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert all(f.dream is None for f in fishes)


def test_dream_is_cleared_once_the_fish_wakes():
    f = _neutral_fish(5.0, 5.0)
    f.dream = aq.choose_dream(f)
    _age(f)
    f.draw(_FakeCanvas())  # environment is None -- always resolves as "awake"
    assert f.dream is None


def test_sleeping_glyph_includes_the_dream_indicator_while_dreaming():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _sleepy_fish(5.0, 5.0, bounds)
    f.fish_list = [f]
    f.dream = aq.choose_dream(f)

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f)
    f.draw(canvas)

    assert any(text == "😴💭" for _x, _y, text in writes)


def test_choose_dream_favors_food_for_a_greedy_fish(monkeypatch):
    f = _neutral_fish(5.0, 5.0)
    f.personality = "Greedy"
    monkeypatch.setattr(aq.random, "random", lambda: 0.5)  # clears the nightmare gate
    assert aq.choose_dream(f).category == "food"


def test_choose_dream_falls_back_to_happy_for_a_friendless_friendly_fish(monkeypatch):
    f = _neutral_fish(5.0, 5.0)
    f.personality = "Friendly"
    monkeypatch.setattr(aq.random, "random", lambda: 0.5)
    assert aq.choose_dream(f).category == "happy"


def test_choose_dream_interpolates_the_friends_name(monkeypatch):
    friend = _neutral_fish(6.0, 5.0)
    friend.display_name = "Alex"
    f = _neutral_fish(5.0, 5.0)
    f.personality = "Friendly"
    aq.set_relationship(f, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    monkeypatch.setattr(aq.random, "random", lambda: 0.5)

    dream = aq.choose_dream(f)

    assert dream.category == "friendship"
    assert any("Alex" in line for frame in dream.frames for line in frame)


def test_choose_dream_nudges_toward_home_after_a_recent_peaceful_moment(monkeypatch):
    # Lazy's own preferred category is "happy" (dreams.py's
    # _PERSONALITY_CATEGORY), not "home" -- proves the relax-memory nudge
    # actually changed the pick rather than personality landing there anyway.
    f = _neutral_fish(5.0, 5.0)
    f.personality = "Lazy"
    f.memory_log.append("[Day 4] Spent a peaceful moment by the Rock.")
    monkeypatch.setattr(aq.random, "random", lambda: 0.5)  # personality-weighted pick

    assert aq.choose_dream(f).category == "home"


def test_choose_dream_friendship_nudge_still_wins_over_a_peaceful_memory(monkeypatch):
    # If both a friend-mention and a peaceful-moment memory are recent, the
    # existing friendship nudge takes priority (see choose_dream()'s
    # docstring) -- the peaceful-moment nudge is only a fallback.
    friend = _neutral_fish(6.0, 5.0)
    friend.display_name = "Alex"
    f = _neutral_fish(5.0, 5.0)
    f.personality = "Lazy"
    aq.set_relationship(f, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    f.memory_log.append("[Day 4] Spent a peaceful moment by the Rock.")
    f.memory_log.append("[Day 4] Swam alongside Alex all afternoon.")
    monkeypatch.setattr(aq.random, "random", lambda: 0.5)

    assert aq.choose_dream(f).category == "friendship"


def test_choose_dream_ignores_a_peaceful_memory_outside_the_lookback_window(
    monkeypatch,
):
    f = _neutral_fish(5.0, 5.0)
    f.personality = "Lazy"
    # Padded past MEMORY_DREAM_LOOKBACK with unrelated, more recent entries.
    f.memory_log.append("[Day 1] Spent a peaceful moment by the Rock.")
    for i in range(aq.MEMORY_DREAM_LOOKBACK):
        f.memory_log.append(f"[Day {i + 2}] Ate some food.")
    monkeypatch.setattr(aq.random, "random", lambda: 0.5)

    assert aq.choose_dream(f).category == "happy"  # Lazy's own default, unnudged


def test_choose_dream_can_roll_a_rare_nightmare(monkeypatch):
    f = _neutral_fish(5.0, 5.0)
    f.personality = "Lazy"
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # always within the chance
    assert aq.choose_dream(f).category == "bad"


def test_clicking_a_dreaming_fish_opens_the_dream_view_not_the_inspector(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.dream = aq.choose_dream(f)

    app._mouse_handler(aq.MouseClick(f.x, f.y, 0))
    view = app._overlays[-1].widget

    assert "Dream" in view.title


def test_clicking_an_awake_fish_still_opens_the_normal_inspector(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    assert f.dream is None

    inspector = _open_inspector_for(app, f)

    assert inspector.title == f.display_name


def test_dream_views_view_stats_button_opens_the_real_inspector(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.dream = aq.choose_dream(f)

    app._mouse_handler(aq.MouseClick(f.x, f.y, 0))
    dream_view = app._overlays[-1].widget
    stats_btn = next(
        c
        for c in dream_view.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "View Stats"
    )
    stats_btn.on_mouse_click()

    inspector = app._overlays[-1].widget
    assert inspector.title == f.display_name


def test_dream_view_shows_a_plain_language_caption_below_the_animation(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.dream = aq.choose_dream(f)

    app._mouse_handler(aq.MouseClick(f.x, f.y, 0))
    dream_view = app._overlays[-1].widget
    labels = [c.text for c in dream_view.children if c.__class__.__name__ == "Label"]

    assert any(f.display_name in t and "dreaming about" in t for t in labels)
    assert any(f.dream.title in t for t in labels)
    assert any(f.dream.description in t for t in labels)


def test_castle_interior_marks_a_dreaming_occupant_and_opens_its_dream_on_click():
    from cozy_tui import App

    app = App(full=False, size="380x300")
    castle = _castle()
    guest = _neutral_fish(5.0, 5.0)
    guest.display_name = "Steve"
    guest.sleeping_in = castle
    guest.dream = aq.choose_dream(guest)
    opened = []

    box = aq._build_castle_interior(app, castle, [guest], opened.append)
    buttons = [c for c in box.children if c.__class__.__name__ == "Button"]
    dream_btn = next(c for c in buttons if "Steve" in c.text and "💭" in c.text)
    dream_btn.on_mouse_click()

    assert opened == [guest]


def test_castle_interior_without_a_dream_callback_still_shows_a_plain_row():
    # _build_castle_interior's on_open_dream is optional (defaults to None)
    # so pre-existing direct callers (and older tests) that don't pass one
    # keep working -- a dreaming occupant just isn't clickable there.
    app_style = None
    from cozy_tui import App

    app = App(full=False, size="380x300")
    castle = _castle()
    guest = _neutral_fish(5.0, 5.0)
    guest.display_name = "Steve"
    guest.sleeping_in = castle
    guest.dream = aq.choose_dream(guest)

    box = aq._build_castle_interior(app, castle, [guest])
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any("Steve" in t and "💭" in t for t in labels)


# ── Fish Memory Log ──────────────────────────────────────────────────────────


def test_feeding_pizza_logs_a_memory_entry(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))

    _open_shop_and_buy(app, "Pizza")
    inspector = _open_inspector_for(app, fish)
    feed_btn = next(
        c
        for c in inspector.children
        if c.__class__.__name__ == "Button" and "Pizza" in c.text
    )
    feed_btn.on_mouse_click()

    assert any(
        "pizza" in entry.lower() and "[Day 0]" in entry for entry in fish.memory_log
    )


def test_feeding_a_favorite_treat_logs_a_memory_entry(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    axolotl = next(w for w in app.widgets if isinstance(w, aq.Fish))
    axolotl.species_name = "Axolotl"
    axolotl.favorite_foods = ("Brine Shrimp", "Bloodworms", "Worms")

    _open_shop_and_buy(app, "Brine Shrimp")
    inspector = _open_inspector_for(app, axolotl)
    feed_btn = next(
        c
        for c in inspector.children
        if c.__class__.__name__ == "Button" and "Brine Shrimp" in c.text
    )
    feed_btn.on_mouse_click()

    assert any("favorite" in entry.lower() for entry in axolotl.memory_log)


def test_a_successful_wake_attempt_logs_a_memory_entry_for_the_sleeper(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    sleepy, friend = fishes[0], fishes[1]
    sleepy.is_sleepy = True
    friend.is_sleepy = False  # must be a genuinely eligible (awake) waker
    sleepy.sleeping_in = castle
    friend.sleeping_in = castle
    aq.set_relationship(sleepy, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD)

    fractions = iter([0.9, 0.2, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)  # any attempt succeeds

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()  # still Night
    second_timer.callback()  # holding begins
    sleepy._wake_next_attempt = 0.0  # force the next tick to resolve immediately
    second_timer.callback()

    assert any("woke me up" in entry for entry in sleepy.memory_log)


def test_breeding_logs_memory_entries_for_both_parents_and_the_baby(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    for f in fishes:
        f.birth_time -= aq.AGE_SECONDS_PER_DAY * 32  # grown up -- breeding needs Adult
    parent_a, parent_b = fishes[0], fishes[1]
    aq.set_relationship(parent_a, parent_b, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # always breeds

    _fire_daily_tick(app)

    babies = [f for f in app.widgets if isinstance(f, aq.Fish) and f not in fishes]
    assert babies
    baby = babies[0]
    assert any(baby.display_name in entry for entry in parent_a.memory_log)
    assert any(baby.display_name in entry for entry in parent_b.memory_log)
    assert any("born today" in entry for entry in baby.memory_log)


def test_a_baby_is_permanently_flagged_with_both_parents_names(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    for f in fishes:
        f.birth_time -= aq.AGE_SECONDS_PER_DAY * 32
    parent_a, parent_b = fishes[0], fishes[1]
    aq.set_relationship(parent_a, parent_b, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)

    _fire_daily_tick(app)

    baby = next(f for f in app.widgets if isinstance(f, aq.Fish) and f not in fishes)
    assert baby.parent_names == (parent_a.display_name, parent_b.display_name)


def test_random_events_log_memory_entries(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    _force_random_event(monkeypatch, "storm")

    _fire_daily_tick(app)

    assert all(any("storm" in entry.lower() for entry in f.memory_log) for f in fishes)


def test_stray_fish_event_logs_its_own_arrival(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _force_random_event(monkeypatch, "stray_fish")

    _fire_daily_tick(app)

    baby = next(w for w in app.widgets if isinstance(w, aq.Fish) and w.memory_log)
    assert any("decided to stay" in entry for entry in baby.memory_log)


def test_selling_a_fish_logs_a_departure_memory_for_its_friend(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    departing, friend = fishes[0], fishes[1]
    aq.set_relationship(departing, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD)

    inspector = _open_inspector_for(app, departing)
    sell_btn = next(
        c
        for c in inspector.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Sell"
    )
    sell_btn.on_mouse_click()
    confirm = app._overlays[-1].widget
    confirm.on_key("y")

    assert any(
        departing.display_name in entry and "isn't around anymore" in entry
        for entry in friend.memory_log
    )


def test_shark_eating_a_fish_logs_a_departure_memory_for_its_friend(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    eaten, friend = fishes[0], fishes[1]
    aq.set_relationship(eaten, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD)

    eaten.fish_list.remove(eaten)  # mirrors Fish.draw()'s predator branch
    eaten.on_eat_fish(eaten)

    assert any(
        eaten.display_name in entry and "isn't around anymore" in entry
        for entry in friend.memory_log
    )


def test_starving_to_death_logs_a_departure_memory_for_its_friend(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    dying, friend = fishes[0], fishes[1]
    aq.set_relationship(dying, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD)
    dying.health = 0.0

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert dying not in app.widgets
    assert any(
        dying.display_name in entry and "isn't around anymore" in entry
        for entry in friend.memory_log
    )


def test_a_fish_in_the_main_tank_can_still_starve_to_death(tmp_path, monkeypatch):
    # Hunger update (updates.md): starvation is unchanged for a fish
    # actually in the main tank -- only a fish away doing Forest/fishing
    # mechanics is exempt (see the test below).
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.hunger = 0.0
    f.health = aq.STARVE_HEALTH_LOSS  # one more hunger application kills it
    assert f.biome == "aquarium" and f._travel_until is None

    # Hunger only actually decays once every HUNGER_TICK_SECONDS worth of
    # 1.0s ticks (see _per_second_tick()'s hunger_tick_accum).
    second_timer = next(t for t in app._timers if t.interval == 1.0)
    for _ in range(int(aq.HUNGER_TICK_SECONDS)):
        second_timer.callback()

    assert f not in [w for w in app.widgets if isinstance(w, aq.Fish)]


def test_a_fish_away_in_the_forest_never_starves_to_death(tmp_path, monkeypatch):
    # The actual bug this fixes: going away (Forest today, fishing once
    # that exists) must never come back to "while you were away, X died" --
    # hunger still drains and bottoms out at "Low energy", it just never
    # drains health while the fish is somewhere the player can't see or
    # feed it.
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.biome = "forest"
    f.hunger = 0.0
    f.health = aq.STARVE_HEALTH_LOSS  # would die next tick if not exempted

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    for _ in range(5):
        second_timer.callback()

    assert f.health == aq.STARVE_HEALTH_LOSS  # untouched the whole time -- never died
    assert f.hunger == 0.0  # floored, not draining forever


def test_a_fish_mid_travel_to_the_forest_never_starves_to_death(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f._travel_until = time.monotonic() + 999.0  # still mid-trip, far from due
    f._travel_target = "forest"
    f.hunger = 0.0
    f.health = aq.STARVE_HEALTH_LOSS

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert f.health == aq.STARVE_HEALTH_LOSS


def test_memory_log_is_capped_at_the_limit(tmp_path, monkeypatch):
    # Real repeated hook firing (not a hand-rolled duplicate of the cap
    # arithmetic) -- the same "showing_off" event, forced every day,
    # exercises the actual _log_memory() closure through its real call site.
    # Not "storm": that one is now a live weather state that can't re-fire
    # until _end_storm() clears it (see test_storm_cannot_restart_while_active).
    app = _headless_app(tmp_path, monkeypatch)
    target_fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)

    def _choice(seq):
        # One combined stub covers both random.choice() call sites this
        # exercises: picking "showing_off" among the day's event candidates,
        # and then picking which fish gets featured within that event.
        if "showing_off" in seq:
            return "showing_off"
        return target_fish

    monkeypatch.setattr(aq.random, "choice", _choice)

    for _ in range(aq.MEMORY_LOG_LIMIT + 3):
        _fire_daily_tick(app)

    assert len(target_fish.memory_log) == aq.MEMORY_LOG_LIMIT


def test_full_memory_log_never_caps_while_memory_log_does(tmp_path, monkeypatch):
    # Same real _log_memory() call site as the cap test above -- but this is
    # the player-facing archive (fish.py's full_memory_log), which exists
    # specifically so a real moment survives past MEMORY_LOG_LIMIT even
    # though the fish itself has "forgotten" it (see the See All History
    # feature: only the player sees this, not the fish's own dream/grief
    # logic, which still reads the capped memory_log).
    app = _headless_app(tmp_path, monkeypatch)
    target_fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)

    def _choice(seq):
        if "showing_off" in seq:
            return "showing_off"
        return target_fish

    monkeypatch.setattr(aq.random, "choice", _choice)

    rounds = aq.MEMORY_LOG_LIMIT + 3
    for _ in range(rounds):
        _fire_daily_tick(app)

    # +1: with random.random() pinned to 0.0, the very first "showing off"
    # spin also (once) grants Energetic (Personality System 2.0) -- its own
    # memory-log line, on top of one "did a little spin" per round.
    assert len(target_fish.memory_log) == aq.MEMORY_LOG_LIMIT
    assert len(target_fish.full_memory_log) == rounds + 1
    # The capped log is exactly the uncapped log's tail -- same entries,
    # same order, just windowed.
    assert target_fish.memory_log == target_fish.full_memory_log[-aq.MEMORY_LOG_LIMIT :]


def test_memory_log_round_trips_through_save_and_load(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    fish.display_name = "Steve"
    fish.memory_log.append("[Day 3] A memorable day.")

    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = "Steve's Memories"
    prompt.on_key(aq.Key.ENTER)

    app._key_handlers["l"]()
    load_box = app._overlays[-1].widget
    load_btn = next(
        c
        for c in load_box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Load"
    )
    load_btn.on_mouse_click()

    steve = next(
        w for w in app.widgets if isinstance(w, aq.Fish) and w.display_name == "Steve"
    )
    assert "[Day 3] A memorable day." in steve.memory_log


def test_memory_log_shown_in_the_inspector():
    f = _neutral_fish(5.0, 5.0)
    f.memory_log.append("[Day 2] Something happened.")
    from cozy_tui import App

    app = App(full=False, size="380x520")
    box = aq._build_inspector(
        app, f, lambda f: None, lambda f: None, {}, lambda f, k: None
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any("Memory Log" in t for t in labels)
    assert any("[Day 2] Something happened." in t for t in labels)


# ── "See All History": the player-facing uncapped memory archive ────────────


def test_full_memory_log_round_trips_through_save_and_load(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    fish.display_name = "Steve"
    # More entries than MEMORY_LOG_LIMIT -- proves the archive survives the
    # round trip whole, not windowed the way memory_log itself would be.
    fish.full_memory_log = [
        f"[Day {i}] Entry {i}." for i in range(aq.MEMORY_LOG_LIMIT + 5)
    ]

    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = "Steve's Full History"
    prompt.on_key(aq.Key.ENTER)

    app._key_handlers["l"]()
    load_box = app._overlays[-1].widget
    load_btn = next(
        c
        for c in load_box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Load"
    )
    load_btn.on_mouse_click()

    steve = next(
        w for w in app.widgets if isinstance(w, aq.Fish) and w.display_name == "Steve"
    )
    assert len(steve.full_memory_log) == aq.MEMORY_LOG_LIMIT + 5
    assert steve.full_memory_log == fish.full_memory_log


def test_parent_names_round_trip_through_save_and_load(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    fish.display_name = "Steve"
    fish.parent_names = ("Mom", "Dad")

    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = "Steve's Parents"
    prompt.on_key(aq.Key.ENTER)

    app._key_handlers["l"]()
    load_box = app._overlays[-1].widget
    load_btn = next(
        c
        for c in load_box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Load"
    )
    load_btn.on_mouse_click()

    steve = next(
        w for w in app.widgets if isinstance(w, aq.Fish) and w.display_name == "Steve"
    )
    assert steve.parent_names == ("Mom", "Dad")


def test_loading_a_save_without_parent_names_leaves_it_none(tmp_path, monkeypatch):
    # A save from before this feature existed has no parent_names key at
    # all -- must not crash, and the fish is simply treated as not having
    # been born in-tank.
    app = _headless_app(tmp_path, monkeypatch)
    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    fish.display_name = "Steve"

    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = "Old Save Without Parents"
    prompt.on_key(aq.Key.ENTER)

    app._key_handlers["l"]()
    load_box = app._overlays[-1].widget
    load_btn = next(
        c
        for c in load_box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Load"
    )
    load_btn.on_mouse_click()

    steve = next(
        w for w in app.widgets if isinstance(w, aq.Fish) and w.display_name == "Steve"
    )
    assert steve.parent_names is None


def test_loading_a_save_without_full_memory_log_seeds_it_from_memory_log(
    tmp_path, monkeypatch
):
    # A save from before "See All History" existed has no full_memory_log key
    # at all -- there's nothing to restore, so it should seed from whatever
    # memory_log still has rather than starting completely blank.
    aq.write_save(
        "Old Save",
        {
            "state": {},
            "day": 5,
            "fish": [
                {
                    "species": "Goldfish",
                    "name": "Steve",
                    "x": 5.0,
                    "y": 5.0,
                    "memory_log": ["[Day 3] Something happened."],
                }
            ],
        },
        home=tmp_path,
    )
    app = _headless_app(tmp_path, monkeypatch)

    _open_load_button(app, "Load").on_mouse_click()

    steve = next(
        w for w in app.widgets if isinstance(w, aq.Fish) and w.display_name == "Steve"
    )
    assert steve.full_memory_log == ["[Day 3] Something happened."]


def test_inspector_see_all_history_button_only_appears_when_wired():
    from cozy_tui import App

    app = App(full=False, size="380x520")
    f = _neutral_fish(5.0, 5.0)
    f.memory_log.append("[Day 2] Something happened.")
    f.full_memory_log.append("[Day 2] Something happened.")

    wired = aq._build_inspector(
        app, f, lambda f: None, lambda f: None, {}, lambda f, k: None, lambda f: None
    )
    unwired = aq._build_inspector(
        app, f, lambda f: None, lambda f: None, {}, lambda f, k: None
    )

    wired_buttons = [c.text for c in wired.children if c.__class__.__name__ == "Button"]
    unwired_buttons = [
        c.text for c in unwired.children if c.__class__.__name__ == "Button"
    ]
    assert any("See All History" in t for t in wired_buttons)
    assert not any("See All History" in t for t in unwired_buttons)


def test_see_all_history_button_opens_every_entry_including_ones_older_than_the_cap():
    from cozy_tui import App

    app = App(full=False, size="380x520")
    f = _neutral_fish(5.0, 5.0)
    f.display_name = "Steve"
    f.memory_log = [f"[Day {i}] Recent {i}." for i in range(3)]
    f.full_memory_log = [f"[Day {i}] Old {i}." for i in range(20)] + f.memory_log
    opened = []

    box = aq._build_inspector(
        app, f, lambda f: None, lambda f: None, {}, lambda f, k: None, opened.append
    )
    history_btn = next(
        c
        for c in box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "See All History"
    )
    history_btn.on_mouse_click()

    assert opened == [f]


def test_build_fish_history_lists_every_entry_in_the_full_log():
    from cozy_tui import App

    app = App(full=False, size="400x420")
    f = _neutral_fish(5.0, 5.0)
    f.display_name = "Steve"
    f.full_memory_log = [f"[Day {i}] Entry {i}." for i in range(20)]

    history_box = aq._build_fish_history(app, f)
    scroll_view = next(
        c for c in history_box.children if c.__class__.__name__ == "ScrollView"
    )
    entries = [c.text for c in scroll_view.children]

    assert entries == f.full_memory_log
    assert "Steve" in history_box.title


def test_build_fish_history_wraps_long_entries_instead_of_clipping_them():
    from cozy_tui import App

    app = App(full=False, size="400x420")
    f = _neutral_fish(5.0, 5.0)
    f.display_name = "Steve"
    long_entry = (
        "[Day 3] I dreamed about The Tunnel of Bubbles. I swam through a "
        "tunnel made of bubbles. Every one popped into tiny stars."
    )
    f.full_memory_log = [long_entry]

    history_box = aq._build_fish_history(app, f)
    scroll_view = next(
        c for c in history_box.children if c.__class__.__name__ == "ScrollView"
    )
    lines = [c.text for c in scroll_view.children]

    # Wrapped across more than one row -- nothing silently clipped -- and
    # rejoining the wrapped lines recovers the original text exactly.
    assert len(lines) > 1
    assert all(len(line) <= 48 for line in lines)
    assert " ".join(lines) == long_entry


# ── Phase 2: shark scares, home conflicts, relationship-crossing memories,
#    and memory-linked dreams ─────────────────────────────────────────────────


def _add_real_fish(app, x, y, is_predator=False, species_name="Goldfish"):
    """A second real Fish sharing the same shared bounds/foods/fish_list/
    callbacks/decorations/environment/paused as an existing headless-app
    fish -- the same direct-Fish(...)-construction approach _load_snapshot()
    itself uses, so it's indistinguishable from a fish main() created."""
    template = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f = aq.Fish(
        x,
        y,
        template.bounds,
        template.foods,
        template.fish_list,
        template.on_eat_food,
        template.on_eat_fish,
        "▶===>" if is_predator else "><>",
        "<===◀" if is_predator else "<><",
        "white" if is_predator else "bright_yellow",
        is_predator=is_predator,
        decorations=template.decorations,
        species_name=species_name,
        mouse_pos=template.mouse_pos,
        price=500 if is_predator else 20,
        environment=template.environment,
        paused=template.paused,
    )
    template.fish_list.append(f)
    app.widgets.append(f)
    return f


def test_shark_scare_logs_a_solo_escape_memory(tmp_path, monkeypatch):
    # No container with room nearby -- prey.decorations emptied so hiding
    # (which now takes priority, see Fish._nearest_container_with_room())
    # can't intercept this scare, isolating the original memory-only path.
    app = _headless_app(tmp_path, monkeypatch)
    prey = next(w for w in app.widgets if isinstance(w, aq.Fish))
    prey.decorations = []
    _add_real_fish(app, prey.fx + 1.0, prey.fy, is_predator=True, species_name="Shark")

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert any(
        any(kw in entry for kw in ("alarm", "shark looked", "narrowly escaped"))
        for entry in prey.memory_log
    )


def test_shark_scare_costs_happiness(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    prey = next(w for w in app.widgets if isinstance(w, aq.Fish))
    prey.decorations = []
    prey.happiness = 50.0
    _add_real_fish(app, prey.fx + 1.0, prey.fy, is_predator=True, species_name="Shark")

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert prey.happiness == pytest.approx(
        50.0 - aq.HAPPINESS_PREDATOR_SCARE_PENALTY, abs=0.5
    )


def test_shark_scare_with_a_nearby_friend_credits_a_rescuer(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    prey, rescuer = fishes[0], fishes[1]
    prey.decorations = []  # no container to hide in -- isolates the rescue path
    prey.fx, prey.fy = 10.0, 10.0
    rescuer.fx, rescuer.fy = 10.0, 6.0  # within SHARK_RESCUE_RADIUS, not SCARE_RADIUS
    prey.happiness = rescuer.happiness = 65.0
    aq.set_relationship(prey, rescuer, aq.RELATIONSHIP_FRIEND_THRESHOLD)
    _add_real_fish(app, 10.0, 14.0, is_predator=True, species_name="Shark")
    rel_before = aq.get_relationship(prey, rescuer).score

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert any(
        rescuer.display_name in entry and "saved me" in entry
        for entry in prey.memory_log
    )
    assert any(
        prey.display_name in entry and "I saved" in entry
        for entry in rescuer.memory_log
    )
    assert aq.get_relationship(prey, rescuer).score > rel_before
    # The rescued fish still nets negative overall (the scare penalty
    # outweighs its half of the rescue's friend-interaction gain) -- being
    # saved doesn't erase having been scared, just softens it a little.
    net = aq.HAPPINESS_FRIEND_INTERACTION_GAIN - aq.HAPPINESS_PREDATOR_SCARE_PENALTY
    assert prey.happiness == pytest.approx(65.0 + net, abs=0.5)
    # The rescuer, never itself scared, comes out purely ahead.
    assert rescuer.happiness > 65.0


# ── Hiding from predators (a container decoration with room) ──────────────────


def test_shark_scare_hides_the_fish_in_a_nearby_container(tmp_path, monkeypatch):
    # A fresh tank already starts with container decorations (Rock, Castle)
    # with room -- hiding now takes priority over the old memory-only/
    # rescuer reaction (see the two tests above, which explicitly empty
    # decorations to isolate that older fallback path).
    app = _headless_app(tmp_path, monkeypatch)
    prey = next(w for w in app.widgets if isinstance(w, aq.Fish))
    _add_real_fish(app, prey.fx + 1.0, prey.fy, is_predator=True, species_name="Shark")

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert prey._hiding_in is not None
    assert any("hid in the" in entry for entry in prey.memory_log)


def test_hiding_fish_steers_into_the_container_then_becomes_invisible_and_safe():
    bounds = (0.0, 0.0, 50.0, 50.0)
    fish_list = []
    eaten = []
    prey_species = next(s for s in aq.SHOP_ITEMS if not s.predator)
    shark_species = next(s for s in aq.SHOP_ITEMS if s.predator)
    castle = aq.Decoration(
        20.0, 5.0, aq.CASTLE_ART, aq.CASTLE_COLORS, kind="Castle", capacity=2
    )

    prey = aq.Fish(
        5.0,
        5.0,
        bounds,
        [],
        fish_list,
        lambda f: None,
        eaten.append,
        prey_species.right,
        prey_species.left,
        prey_species.color,
        decorations=[castle],
    )
    shark = aq.Fish(
        20.0,
        5.0,
        bounds,
        [],
        fish_list,
        lambda f: None,
        eaten.append,
        shark_species.right,
        shark_species.left,
        shark_species.color,
        is_predator=True,
    )
    fish_list.extend([prey, shark])
    shark._next_turn = float("inf")
    prey._hiding_in = castle  # simulates _check_shark_scares() having triggered this

    class _FakeCanvas:
        def write(self, *a, **k):
            pass

    canvas = _FakeCanvas()
    for _ in range(60):
        _age(prey, 0.5)
        prey.draw(canvas)
        if prey._entered:
            break

    assert prey._entered
    assert prey._hide_until is not None
    assert prey in fish_list  # still exists, just hidden

    # A Shark can no longer reach it while hidden.
    _age(shark, 0.5)
    shark.draw(canvas)
    assert eaten == []
    assert prey in fish_list


def test_hidden_fish_re_emerges_after_hide_duration():
    bounds = (0.0, 0.0, 50.0, 50.0)
    fish_list = []
    castle = aq.Decoration(
        20.0, 5.0, aq.CASTLE_ART, aq.CASTLE_COLORS, kind="Castle", capacity=2
    )
    prey = aq.Fish(
        20.0,
        5.0,
        bounds,
        [],
        fish_list,
        lambda f: None,
        lambda f: None,
        ">",
        "<",
        "white",
        decorations=[castle],
    )
    fish_list.append(prey)
    prey._hiding_in = castle
    prey._entered = True
    prey._shark_scare_active = True
    prey._hide_until = time.monotonic() - 1.0  # already past

    class _FakeCanvas:
        def write(self, *a, **k):
            pass

    _age(prey, 0.1)
    prey.draw(_FakeCanvas())

    assert not prey._entered
    assert prey._hiding_in is None
    assert prey._hide_until is None
    assert not prey._shark_scare_active


def test_hiding_only_happens_when_a_container_has_room():
    castle = aq.Decoration(
        20.0, 5.0, aq.CASTLE_ART, aq.CASTLE_COLORS, kind="Castle", capacity=1
    )
    fish_list = []
    prey = aq.Fish(
        5.0,
        5.0,
        (0.0, 0.0, 50.0, 50.0),
        [],
        fish_list,
        lambda f: None,
        lambda f: None,
        ">",
        "<",
        "white",
        decorations=[castle],
    )
    occupant = aq.Fish(
        20.0,
        5.0,
        (0.0, 0.0, 50.0, 50.0),
        [],
        fish_list,
        lambda f: None,
        lambda f: None,
        ">",
        "<",
        "white",
    )
    occupant.sleeping_in = castle  # the castle's only slot is already taken
    fish_list.extend([prey, occupant])

    assert prey._nearest_container_with_room() is None


def test_home_occupancy_counts_sleepers_and_hiders_together():
    castle = aq.Decoration(
        0.0, 0.0, aq.CASTLE_ART, aq.CASTLE_COLORS, kind="Castle", capacity=2
    )
    fish_list = []
    bounds = (0.0, 0.0, 10.0, 10.0)
    f = aq.Fish(
        0.0,
        0.0,
        bounds,
        [],
        fish_list,
        lambda f: None,
        lambda f: None,
        ">",
        "<",
        "white",
    )
    sleeper = aq.Fish(
        0.0,
        0.0,
        bounds,
        [],
        fish_list,
        lambda f: None,
        lambda f: None,
        ">",
        "<",
        "white",
    )
    hider = aq.Fish(
        0.0,
        0.0,
        bounds,
        [],
        fish_list,
        lambda f: None,
        lambda f: None,
        ">",
        "<",
        "white",
    )
    sleeper.sleeping_in = castle
    hider._hiding_in = castle
    fish_list.extend([f, sleeper, hider])

    assert f._home_occupancy(castle) == 2


def test_nearest_prey_never_returns_a_hidden_or_sleeping_fish():
    bounds = (0.0, 0.0, 20.0, 20.0)
    fish_list = []
    shark = aq.Fish(
        0.0,
        0.0,
        bounds,
        [],
        fish_list,
        lambda f: None,
        lambda f: None,
        ">",
        "<",
        "white",
        is_predator=True,
    )
    hidden = aq.Fish(
        1.0,
        0.0,
        bounds,
        [],
        fish_list,
        lambda f: None,
        lambda f: None,
        ">",
        "<",
        "white",
    )
    visible = aq.Fish(
        2.0,
        0.0,
        bounds,
        [],
        fish_list,
        lambda f: None,
        lambda f: None,
        ">",
        "<",
        "white",
    )
    hidden._entered = True
    fish_list.extend([shark, hidden, visible])

    assert shark._nearest_prey() is visible


def test_sleeping_fish_slept_through_a_shark_scare(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    prey = next(w for w in app.widgets if isinstance(w, aq.Fish))
    prey.hunger = 100.0
    _force_night_transition(monkeypatch)
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)  # isolate from dream noise
    _add_real_fish(app, prey.fx + 1.0, prey.fy, is_predator=True, species_name="Shark")

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert any("Slept through" in entry for entry in prey.memory_log)


def test_shark_scare_only_fires_once_per_continuous_approach(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    prey = next(w for w in app.widgets if isinstance(w, aq.Fish))
    _add_real_fish(app, prey.fx + 1.0, prey.fy, is_predator=True, species_name="Shark")

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()
    count_after_first = len(prey.memory_log)
    second_timer.callback()

    assert len(prey.memory_log) == count_after_first


def test_two_disliking_fish_sharing_a_container_get_pushed_from_home_memory(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    a, b = fishes[0], fishes[1]
    a.sleeping_in = b.sleeping_in = castle
    aq.set_relationship(a, b, aq.RELATIONSHIP_DISLIKE_THRESHOLD)
    rel_before = aq.get_relationship(a, b).score

    fractions = iter([0.9, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(
        aq.random, "random", lambda: 0.99
    )  # isolate from vignette/dream

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()  # Day -> Night
    second_timer.callback()  # Night -> Morning: _check_night_events fires

    assert any("pushed me out of the Castle" in e for e in a.memory_log) or any(
        "pushed me out of the Castle" in e for e in b.memory_log
    )
    assert aq.get_relationship(a, b).score < rel_before


def test_full_container_logs_a_crowded_memory_to_every_occupant(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    fourth = _add_real_fish(app, 5.0, 5.0)
    occupants = fishes + [fourth]
    for f in occupants:
        f.sleeping_in = castle  # 4/4 capacity -- full

    fractions = iter([0.9, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()
    second_timer.callback()

    assert all(
        any("crowded in the Castle" in e for e in f.memory_log) for f in occupants
    )


def test_friends_sleeping_close_on_the_floor_log_the_moon_memory(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    a, b = fishes[0], fishes[1]
    a.sleeping_in = b.sleeping_in = None
    a.fx, a.fy = 5.0, 5.0
    b.fx, b.fy = 5.0 + aq.SLEEP_CLOSE_DISTANCE - 0.5, 5.0
    aq.set_relationship(a, b, aq.RELATIONSHIP_FRIEND_THRESHOLD)

    fractions = iter([0.9, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()
    second_timer.callback()

    assert any("watched the moon together" in e for e in a.memory_log)
    assert any("watched the moon together" in e for e in b.memory_log)


def test_solo_floor_sleeper_near_a_favorite_plant_logs_peaceful_memory(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    solo = fishes[0]
    plant = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Plant"
    )
    solo.sleeping_in = None
    solo.favorite_decoration = plant  # a real fish starts with no bonds at all

    fractions = iter([0.9, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()
    second_timer.callback()

    assert any("Slept near the Plant floor" in e for e in solo.memory_log)


def test_relationship_tier_crossings_log_became_friends_and_rivals_memories(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    a, b = fishes[0], fishes[1]
    monkeypatch.setattr(
        aq.random, "random", lambda: 0.99
    )  # no breeding/random-event noise

    aq.set_relationship(a, b, aq.RELATIONSHIP_FRIEND_THRESHOLD + 5.0)  # survives decay
    _fire_daily_tick(app)

    assert any(f"became friends with {b.display_name}" in e for e in a.memory_log)
    assert any(f"became friends with {a.display_name}" in e for e in b.memory_log)

    aq.set_relationship(a, b, aq.RELATIONSHIP_RIVAL_THRESHOLD - 5.0)
    _fire_daily_tick(app)

    assert any(f"became rivals with {b.display_name}" in e for e in a.memory_log)
    assert any(f"became rivals with {a.display_name}" in e for e in b.memory_log)


def test_relationship_milestone_memories_do_not_repeat_every_day(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    a, b = fishes[0], fishes[1]
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)
    aq.set_relationship(a, b, aq.RELATIONSHIP_FRIEND_THRESHOLD + 5.0)

    _fire_daily_tick(app)
    count_after_first = sum("became friends" in e for e in a.memory_log)
    aq.set_relationship(a, b, aq.RELATIONSHIP_FRIEND_THRESHOLD + 5.0)  # still friends
    _fire_daily_tick(app)

    assert sum("became friends" in e for e in a.memory_log) == count_after_first


def test_became_friends_memory_does_not_spam_when_score_hovers_at_the_line(
    tmp_path, monkeypatch
):
    # Regression: _relationship_tier() had no hysteresis, so a pair sitting
    # right at RELATIONSHIP_FRIEND_THRESHOLD could get nudged under it by
    # decay_relationships() (silently -- only *entering* a tier logs
    # anything) and straight back over it by the next routine bonding event,
    # re-announcing "I became friends with X" every single time even though
    # the bond never meaningfully lapsed (reported as it repeating every
    # ~10 days in real play).
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    a, b = fishes[0], fishes[1]
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)

    aq.set_relationship(a, b, aq.RELATIONSHIP_FRIEND_THRESHOLD + 5.0)
    _fire_daily_tick(app)
    assert sum("became friends" in e for e in a.memory_log) == 1

    # Dips just under the threshold (as a day of decay would), then a small
    # reinforcing event nudges it right back over -- oscillating around the
    # line without ever dropping RELATIONSHIP_TIER_HYSTERESIS points below it.
    aq.set_relationship(a, b, aq.RELATIONSHIP_FRIEND_THRESHOLD - 1.0)
    _fire_daily_tick(app)
    aq.set_relationship(a, b, aq.RELATIONSHIP_FRIEND_THRESHOLD + 1.0)
    _fire_daily_tick(app)

    assert sum("became friends" in e for e in a.memory_log) == 1


def test_dream_assignment_logs_a_dream_summary_memory(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    for f in fishes:
        f.hunger = 100.0
    _force_night_transition(monkeypatch)
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    dreamer = next(f for f in fishes if f.dream is not None)
    assert any(
        f"I dreamed about {dreamer.dream.title}" in entry
        for entry in dreamer.memory_log
    )


def test_a_shark_never_gets_assigned_a_dream(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    shark = _add_real_fish(app, 5.0, 5.0, is_predator=True, species_name="Shark")
    shark.hunger = 0.0
    _force_night_transition(monkeypatch)
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # always dreams, if eligible

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert shark.dream is None


def test_together_forever_dream_requires_a_best_friend_not_just_a_friend(monkeypatch):
    f = _neutral_fish(5.0, 5.0)
    friend = _neutral_fish(1.0, 1.0)
    friend.display_name = "Kitty"
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # would always win otherwise

    aq.set_relationship(f, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD + 1)
    assert aq.choose_dream(f).category != "together_forever"  # Friend, not Best Friend

    aq.set_relationship(f, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    dream = aq.choose_dream(f)
    assert dream.category == "together_forever"
    assert "Kitty" in dream.title or "Kitty" in dream.description


def test_together_forever_dream_never_fires_with_no_friend_at_all(monkeypatch):
    f = _neutral_fish(5.0, 5.0)
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)

    assert aq.choose_dream(f).category != "together_forever"


def test_make_dream_together_forever_falls_back_to_happy_with_no_friend():
    f = _neutral_fish(5.0, 5.0)
    dream = aq.make_dream(f, "together_forever")
    assert dream.category == "happy"


def test_make_dream_together_forever_names_the_friend():
    f = _neutral_fish(5.0, 5.0)
    friend = _neutral_fish(1.0, 1.0)
    friend.display_name = "Kitty"
    aq.set_relationship(f, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)

    dream = aq.make_dream(f, "together_forever")

    assert dream.category == "together_forever"
    assert "Kitty" in dream.description


def test_reunion_dream_can_be_chosen_after_a_departure_memory(monkeypatch):
    f = _neutral_fish(5.0, 5.0)
    f.memory_log.append("[Day 4] Alice isn't around anymore.")
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # within DREAM_REUNION_CHANCE

    dream = aq.choose_dream(f)

    assert dream.category == "reunion"
    assert "Alice" in dream.title


def test_shark_nightmare_is_more_likely_after_a_recent_shark_memory(monkeypatch):
    f = _neutral_fish(5.0, 5.0)
    f.personality = "Lazy"  # would otherwise land in the "happy" category
    f.memory_log.append("[Day 2] I narrowly escaped a shark. That was close!")
    # < DREAM_SHARK_NIGHTMARE_CHANCE (0.35) but >= the plain DREAM_NIGHTMARE_CHANCE
    # (0.04) -- only the shark-specific check should fire.
    monkeypatch.setattr(aq.random, "random", lambda: 0.2)

    dream = aq.choose_dream(f)

    assert dream.category == "bad"
    assert dream.title == "A Shark in the Dark Water"


def test_personality_is_a_lean_not_a_lock_on_dream_category():
    # Regression: a Greedy fish used to get the "food" category every
    # single time (and Explorer always "fantasy", etc.) -- personality
    # should bias category selection, not hard-lock it.
    f = _neutral_fish(5.0, 5.0)
    f.personality = "Greedy"
    categories = {aq.choose_dream(f).category for _ in range(60)}
    assert categories != {"food"}
    assert "food" in categories  # still the personality's own lean, often


# ── Nightmare reaction: scare, then quietly seek a friend ───────────────────


def test_a_bad_dream_schedules_a_forced_nightmare_wake(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    for f in fishes:
        f.hunger = 100.0
    _force_night_transition(monkeypatch)
    monkeypatch.setattr(
        aq.random, "random", lambda: 0.0
    )  # always dreams, always a nightmare

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    dreamer = fishes[0]
    assert dreamer._nightmare_wake_at is not None


def test_nightmare_scare_phase_clears_the_dream_and_logs_it_with_a_description(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.dream = aq.choose_dream(f)._replace(
        category="bad",
        title="A Shark in the Dark Water",
        description="Getting closer. Too close.",
    )
    f._nightmare_wake_at = time.monotonic()  # due now
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert f.dream is None
    assert f._nightmare_wake_at is None
    assert f._just_scared_until is not None and f._just_scared_until > time.monotonic()
    assert f._nightmare_relocate_at is not None
    assert any(
        "nightmare about A Shark in the Dark Water" in entry for entry in f.memory_log
    )
    assert any("A Shark in the Dark Water" in t for t in toasts)


def test_nightmare_scare_costs_happiness(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.dream = aq.choose_dream(f)._replace(category="bad")
    f._nightmare_wake_at = time.monotonic()
    f.happiness = 50.0

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert f.happiness == pytest.approx(50.0 - aq.HAPPINESS_BAD_DREAM_PENALTY, abs=0.5)


def test_nightmare_relocation_joins_a_friends_container_when_room_available(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    dreamer, friend = fishes[0], fishes[1]
    aq.set_relationship(dreamer, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    friend.sleeping_in = castle
    dreamer.sleeping_in = None
    dreamer._nightmare_relocate_at = time.monotonic()  # due now

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert dreamer.sleeping_in is castle
    assert dreamer._seeking_friend_after_nightmare is True
    assert dreamer._nightmare_relocate_at is None


def test_nightmare_relocation_without_a_friend_just_settles_back_down(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    assert f.friend is None
    f._nightmare_relocate_at = time.monotonic()

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert f.sleeping_in is None
    assert f._seeking_friend_after_nightmare is False


def test_nightmare_relocation_seeks_a_living_parent_over_a_friend(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    child, friend, parent = fishes[0], fishes[1], fishes[2]
    child.display_name, friend.display_name, parent.display_name = (
        "Child",
        "Friend",
        "Parent",
    )
    # A Best Friend bond, but no relationship at all with the parent -- the
    # blood bond must still win over the (much stronger) friendship.
    aq.set_relationship(child, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    child.parent_names = (parent.display_name, "Someone Else")
    friend.sleeping_in = castle
    child.sleeping_in = None
    child._nightmare_relocate_at = time.monotonic()

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert child._nightmare_seek_target is parent
    assert child._seeking_friend_after_nightmare is True


def test_nightmare_relocation_falls_back_to_a_friend_once_no_parent_is_left(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    child, friend = fishes[0], fishes[1]
    aq.set_relationship(child, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    child.parent_names = ("A Fish That Was Sold", "Another That Died")
    child._nightmare_relocate_at = time.monotonic()

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert child._nightmare_seek_target is friend


def test_arriving_beside_a_parent_after_a_nightmare_logs_both_diaries(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    child, parent = fishes[0], fishes[1]
    child.parent_names = (parent.display_name, "Someone Else")
    child._seeking_friend_after_nightmare = True
    child._nightmare_seek_target = parent
    child._entered = True
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert child._seeking_friend_after_nightmare is False
    assert child._nightmare_comfort_until is not None
    assert any(
        f"I was scared. I found {parent.display_name}." in entry
        for entry in child.memory_log
    )
    assert any(
        f"{child.display_name} came to me after a nightmare" in entry
        for entry in parent.memory_log
    )
    assert any(parent.display_name in t for t in toasts)


def test_arriving_beside_the_friend_triggers_a_comfort_flash_and_memory(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    dreamer, friend = fishes[0], fishes[1]
    aq.set_relationship(dreamer, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    dreamer._seeking_friend_after_nightmare = True
    dreamer._nightmare_seek_target = friend
    dreamer._entered = True  # arrived and settled into the shared container
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert dreamer._seeking_friend_after_nightmare is False
    assert dreamer._nightmare_comfort_until is not None
    assert any(f"beside {friend.display_name}" in entry for entry in dreamer.memory_log)
    assert any(friend.display_name in t for t in toasts)


def test_scared_mood_takes_visual_priority_over_the_sleep_glyph():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _sleepy_fish(5.0, 5.0, bounds)
    f.fish_list = [f]
    f._just_scared_until = time.monotonic() + 10.0

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f)
    f.draw(canvas)

    assert any(text == "😨" for _x, _y, text in writes)
    assert not any(text in ("😴", "😴💭") for _x, _y, text in writes)


def test_comfort_mood_takes_visual_priority_over_the_sleep_glyph():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _sleepy_fish(5.0, 5.0, bounds)
    f.fish_list = [f]
    f._nightmare_comfort_until = time.monotonic() + 10.0

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f)
    f.draw(canvas)

    assert any(text == "🥺" for _x, _y, text in writes)
    assert not any(text in ("😴", "😴💭") for _x, _y, text in writes)


def test_castle_interior_shows_scared_and_comfort_moods():
    from cozy_tui import App

    app = App(full=False, size="380x300")
    castle = _castle()
    scared = _neutral_fish(5.0, 5.0)
    scared.display_name = "Steve"
    scared.sleeping_in = castle
    scared._just_scared_until = time.monotonic() + 10.0
    comforted = _neutral_fish(6.0, 5.0)
    comforted.display_name = "Alice"
    comforted.sleeping_in = castle
    comforted._nightmare_comfort_until = time.monotonic() + 10.0

    box = aq._build_castle_interior(app, castle, [scared, comforted])
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any("Steve" in t and "😨" in t for t in labels)
    assert any("Alice" in t and "🥺" in t for t in labels)


def test_scared_mood_surfaces_above_a_housed_fish_even_while_tucked_in():
    # A nightmare's scare phase deliberately leaves the fish tucked inside its
    # claimed home (see aquarium.py's _trigger_nightmare_scare) -- so the mood
    # must still reach the open tank view, not just the Castle Interior panel,
    # or a player watching the tank (rather than that one decoration) never
    # sees it at all.
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _sleepy_fish(5.0, 5.0, bounds)
    f.fish_list = [f]
    f._entered = True
    f._just_scared_until = time.monotonic() + 10.0

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f)
    f.draw(canvas)

    assert any(text == "😨" for _x, _y, text in writes)


def test_housed_mood_glyph_anchors_to_the_container_not_the_fishs_own_position():
    # Regression: a housed fish's fx/fy is wherever it happened to cross
    # arrive_radius (up to a container-radius-plus-margin away from the
    # container's own glyph) -- anchoring the mood glyph to self, as it
    # used to, could float it out over open water with nothing nearby to
    # explain it (reported as a "stray" floating emoji). It must appear at
    # the container's own position instead.
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(x=30.0, y=20.0)
    f = _sleepy_fish(5.0, 5.0, bounds)  # far from the castle
    f.fish_list = [f]
    f.sleeping_in = castle
    f._entered = True
    f._just_scared_until = time.monotonic() + 10.0

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f)
    f.draw(canvas)

    scare_writes = [(x, y) for x, y, text in writes if text == "😨"]
    assert scare_writes
    x, y = scare_writes[0]
    assert x == castle.abs_x
    assert y == max(0, castle.abs_y - 1)
    assert (x, y) != (f.abs_x, max(0, f.abs_y - 1))


def test_comfort_mood_surfaces_above_a_housed_fish_even_while_tucked_in():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _sleepy_fish(5.0, 5.0, bounds)
    f.fish_list = [f]
    f._entered = True
    f._nightmare_comfort_until = time.monotonic() + 10.0

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f)
    f.draw(canvas)

    assert any(text == "🥺" for _x, _y, text in writes)


def test_opening_a_dream_that_vanished_since_the_panel_was_drawn_falls_back_to_the_inspector(
    tmp_path, monkeypatch
):
    # Reproduces the real crash: the Castle Interior panel draws a guest's
    # dream button only while `guest.dream is not None` (inspectors.py), but
    # that panel is a snapshot -- a nightmare firing on the per-second tick
    # (aquarium.py's _trigger_nightmare_scare) clears `f.dream` without
    # rebuilding the still-open panel, so the button the player is looking at
    # now points at a dream that no longer exists. Clicking it used to crash
    # deep in build_dream_view() with AttributeError: 'NoneType' object has no
    # attribute 'frames'. _open_dream() must fall back to the ordinary
    # Inspector instead.
    app = _headless_app(tmp_path, monkeypatch)
    fish_list = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    guest = fish_list[0]
    guest.display_name = "Steve"
    guest.sleeping_in = castle
    guest._entered = True
    guest.dream = aq.choose_dream(guest)

    app._mouse_handler(aq.MouseClick(castle.x, castle.y, 0))
    decoration_box = app._overlays[-1].widget
    enter_btn = next(
        c
        for c in decoration_box.children
        if c.__class__.__name__ == "Button" and c.text.strip().startswith("Enter")
    )
    enter_btn.on_mouse_click()
    interior = app._overlays[-1].widget
    dream_btn = next(
        c
        for c in interior.children
        if c.__class__.__name__ == "Button" and "Steve" in c.text
    )

    # The dream vanishes exactly as a nightmare's scare phase would clear it,
    # without the already-open panel being rebuilt.
    guest.dream = None

    dream_btn.on_mouse_click()  # must not raise

    opened = app._overlays[-1].widget
    assert opened.title == "Steve"  # the ordinary Inspector, not a dream view


def test_open_castle_interior_refreshes_to_show_a_nightmare_scare(
    tmp_path, monkeypatch
):
    # The bug: _enter_decoration()'s live-refresh poll (_signature()) tracked
    # _awake_in_home/_just_booped_until/_just_resisted_wake_until but not
    # _just_scared_until/_nightmare_comfort_until -- so a fish scared by a
    # nightmare while its Interior panel was already open never got its 😨
    # shown, even though _build_castle_interior itself renders it correctly
    # when built fresh (see test_castle_interior_shows_scared_and_comfort_moods).
    app = _headless_app(tmp_path, monkeypatch)
    fish_list = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    guest = fish_list[0]
    guest.display_name = "Kitty"
    guest.sleeping_in = castle
    guest._entered = True

    app._mouse_handler(aq.MouseClick(castle.x, castle.y, 0))
    decoration_box = app._overlays[-1].widget
    enter_btn = next(
        c
        for c in decoration_box.children
        if c.__class__.__name__ == "Button" and c.text.strip().startswith("Enter")
    )
    enter_btn.on_mouse_click()
    interior_before = app._overlays[-1].widget
    labels_before = [
        c.text for c in interior_before.children if c.__class__.__name__ == "Label"
    ]
    assert not any("😨" in t for t in labels_before)

    # The nightmare scare fires while the panel is still open, unrelated to
    # any occupant arriving/leaving/waking.
    guest._just_scared_until = time.monotonic() + 10.0

    # _per_second_tick's own timer is also interval==1.0 and was registered
    # first at boot -- the Interior panel's own poll (_enter_decoration's
    # app.every(1.0, _refresh)) is the one registered after Enter was
    # clicked, i.e. the last one.
    refresh_timer = [t for t in app._timers if t.interval == 1.0][-1]
    refresh_timer.callback()

    interior_after = app._overlays[-1].widget
    labels_after = [
        c.text for c in interior_after.children if c.__class__.__name__ == "Label"
    ]
    assert any("Kitty" in t and "😨" in t for t in labels_after)


def test_housed_fish_with_no_active_nightmare_mood_stays_invisible():
    # The exception is narrow: a housed fish with neither mood active must
    # still draw nothing at all (the ordinary "tucked away, can't see through
    # the walls" behavior), not just skip its body glyph.
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _sleepy_fish(5.0, 5.0, bounds)
    f.fish_list = [f]
    f._entered = True

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f)
    f.draw(canvas)

    assert writes == []


# ── Aging: Elder stage + natural death ──────────────────────────────────────


def test_reaching_elder_unlocks_the_achievement_and_logs_it_once(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 60
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)  # no natural death this tick

    _fire_daily_tick(app)

    assert "golden_years" in aq.load_unlocked_achievements(home=tmp_path)
    assert sum("getting older" in entry for entry in f.memory_log) == 1

    _fire_daily_tick(app)  # still Elder the next day -- must not repeat

    assert sum("getting older" in entry for entry in f.memory_log) == 1


def test_natural_death_only_ever_picks_elder_fish(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    elder, young = fishes[0], fishes[1]
    elder.birth_time -= aq.AGE_SECONDS_PER_DAY * 60
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # always within the chance

    _fire_daily_tick(app)

    assert elder not in [w for w in app.widgets if isinstance(w, aq.Fish)]
    assert young in [w for w in app.widgets if isinstance(w, aq.Fish)]


def test_natural_death_logs_departure_and_cause_and_toasts(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    elder, friend = fishes[0], fishes[1]
    elder.birth_time -= aq.AGE_SECONDS_PER_DAY * 60
    aq.set_relationship(elder, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)

    _fire_daily_tick(app)

    assert any("isn't around anymore" in e for e in friend.memory_log)
    assert any("passed peacefully in old age" in e for e in friend.memory_log)
    assert any("passed peacefully in old age" in t for t in toasts)


def test_reunion_dream_still_works_after_an_old_age_death(monkeypatch):
    # The standard "isn't around anymore" departure line must stay exactly
    # matchable by dreams.py's _DEPARTURE_RE regardless of the cause of
    # death -- old age included, even with the extra cause line right
    # after it in the log.
    f = _neutral_fish(5.0, 5.0)
    f.memory_log.append("[Day 12] Alice isn't around anymore.")
    f.memory_log.append("[Day 12] Alice passed peacefully in old age.")
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # within DREAM_REUNION_CHANCE

    dream = aq.choose_dream(f)

    assert dream.category == "reunion"
    assert "Alice" in dream.title


# ── Cheat Console ────────────────────────────────────────────────────────────


def _type_into_console(console, text):
    for ch in text:
        console.on_key(ch)
    console.on_key(aq.Key.ENTER)


def test_backtick_opens_the_cheat_console(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    assert isinstance(console, aq.CheatConsole)


def test_spawn_fish_command_adds_a_free_named_fish(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fish_before = len([w for w in app.widgets if isinstance(w, aq.Fish)])
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, 'spawn_fish(species="Goldfish", name="Steven")')

    fishes_after = [w for w in app.widgets if isinstance(w, aq.Fish)]
    assert len(fishes_after) == fish_before + 1
    assert any(f.display_name == "Steven" for f in fishes_after)


def test_set_money_command_sets_state_exactly(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, "set_money(1000)")

    stats_label = next(
        w for w in app.widgets if getattr(w, "text", "").startswith("Money")
    )
    assert "Money: $1000" in stats_label.text


def test_set_happiness_command_wires_through_to_the_real_fish(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, 'set_happiness(fish_name="Steve", amount=500)')

    assert steve.happiness == 100.0


def test_remove_fish_command_wires_through_to_the_real_tank(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, 'remove_fish(fish_name="Steve")')

    assert steve not in [w for w in app.widgets if isinstance(w, aq.Fish)]


def test_remove_fish_command_grieves_a_bonded_friend(tmp_path, monkeypatch):
    # Regression: the console's remove_fish used to call clear_relationships()
    # directly, skipping _log_departure() -- so a bonded tankmate got no
    # grief penalty and no memory line to trigger a reunion dream, unlike
    # every other way a fish can leave (sold, eaten, starved, old age).
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    departing, friend = fishes[0], fishes[1]
    departing.display_name = "Angelfish"
    aq.set_relationship(departing, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, 'remove_fish(fish_name="Angelfish")')

    assert any(
        "Angelfish" in entry and "isn't around anymore" in entry
        for entry in friend.memory_log
    )


def test_run_command_wires_through_to_the_real_app(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(
        console, 'run(code="for f in fish: set_happiness(f.display_name, 100)")'
    )

    assert steve.happiness == 100.0


def test_buy_command_deducts_money_and_spawns_a_shark(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, "set_money(1000)")

    _type_into_console(console, 'buy("Shark")')

    assert any(isinstance(w, aq.Fish) and w.is_predator for w in app.widgets)
    # Shark costs $500; the console is still on top, so close its own
    # rename prompt before reading state back off the stats label.
    while app._overlays and app._overlays[-1].widget is not console:
        app.close_overlay()
    stats_label = next(
        w for w in app.widgets if getattr(w, "text", "").startswith("Money")
    )
    assert "Money: $500" in stats_label.text


def test_buy_command_with_insufficient_funds_shows_an_error_line(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, "set_money(0)")

    _type_into_console(console, 'buy("Shark")')

    assert not any(isinstance(w, aq.Fish) and w.is_predator for w in app.widgets)
    assert any("Not enough money" in text for text, _is_error in console.lines)
    assert any(is_error for _text, is_error in console.lines if "Not enough" in _text)


def test_unknown_command_shows_an_error_line(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, "nonexistent_command()")

    assert any("Unknown command" in text for text, _is_error in console.lines)


def test_help_output_is_split_across_separate_lines_not_run_together(
    tmp_path, monkeypatch
):
    # Regression: help()'s "\n".join(...) result used to land in *one*
    # `lines` entry, rendering every command run together on a single row
    # (e.g. "help: ...commandspawn_fish: spawn_fish(speci...").
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, "help")

    assert not any("\n" in text for text, _is_error in console.lines)
    assert not any(
        "help:" in text and "spawn_fish:" in text for text, _is_error in console.lines
    )
    assert any(text.startswith("help:") for text, _is_error in console.lines)
    assert any(text.startswith("spawn_fish:") for text, _is_error in console.lines)


def test_long_output_lines_wrap_instead_of_getting_cut_off(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, "help")

    assert all(len(text) <= console.width - 2 for text, _is_error in console.lines)
    # The full spawn_fish usage text is long enough that it must have
    # wrapped across more than one line to satisfy the width check above.
    spawn_fish_lines = [
        text
        for text, _is_error in console.lines
        if "spawn_fish" in text or "amount" in text
    ]
    assert len(spawn_fish_lines) > 1


def test_console_history_recalls_previous_commands(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, "set_money(1000)")
    _type_into_console(console, "set_food(50)")

    console.on_key(aq.Key.UP)
    assert console.buffer == "set_food(50)"
    console.on_key(aq.Key.UP)
    assert console.buffer == "set_money(1000)"
    console.on_key(aq.Key.DOWN)
    assert console.buffer == "set_food(50)"


def test_set_time_command_changes_the_day_phase(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, 'set_time("night")')
    assert steve.environment["phase"] == "Night"  # env dict is shared with fish
    _type_into_console(console, 'set_time("morning")')
    assert steve.environment["phase"] == "Morning"
    _type_into_console(console, 'set_time("day")')
    assert steve.environment["phase"] == "Day"


def test_set_time_command_rejects_a_bad_phase(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, 'set_time("lunch")')
    assert any(is_error for _text, is_error in console.lines)


def test_spawn_command_drops_special_food_into_the_tank(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, 'spawn("Pizza", 3)')

    pizzas = [
        w
        for w in app.widgets
        if isinstance(w, aq.Food) and getattr(w, "kind", None) == "Pizza"
    ]
    assert len(pizzas) == 3
    assert all(p.glyph == "🍕" for p in pizzas)
    assert all(p.on_eaten is not None for p in pizzas)  # reacts when eaten


def test_a_fish_eating_a_special_food_fires_its_on_eaten_hook():
    bounds = (0.0, 0.0, 50.0, 50.0)
    foods = []
    fish_list = []
    species = next(s for s in aq.SHOP_ITEMS if not s.predator)
    f = _make_fish(
        5.0, 5.0, bounds, foods, fish_list, lambda x: None, lambda x: None, species
    )
    fish_list.append(f)
    eaten_by = []
    food = aq.Food(5.0, 5.0, glyph="🍕", kind="Pizza")
    food.on_eaten = lambda eater: eaten_by.append(eater)
    foods.append(food)

    class _FakeCanvas:
        def write(self, *a, **k):
            pass

    for _ in range(30):
        f.draw(_FakeCanvas())
        if food not in foods:
            break
    assert food not in foods  # got eaten
    assert eaten_by == [f]  # the hook fired, with the eater


def test_eating_a_dropped_pizza_triggers_the_pizza_reaction(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, 'spawn("Pizza")')
    pizza = next(
        w
        for w in app.widgets
        if isinstance(w, aq.Food) and getattr(w, "kind", None) == "Pizza"
    )

    pizza.on_eaten(steve)  # simulate Steve reaching and eating it

    assert any("devoured an entire Pizza" in t for t in toasts)
    assert any("I ate pizza" in m for m in steve.memory_log)


def test_give_dream_command_sets_a_viewable_dream(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, 'give_dream("Steve")')

    assert steve.dream is not None
    assert steve.dream.category != "bad"
    assert any("I dreamed about" in m for m in steve.memory_log)


def test_advance_day_command_runs_the_real_daily_tick(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, "advance_day()")

    assert any("Advanced 1 day." in text for text, _err in console.lines)


def test_advance_day_command_accepts_an_amount_and_advances_the_shop_stock(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, "advance_day(amount=5)")

    assert any("Advanced 5 day(s)." in text for text, _err in console.lines)


def test_advance_day_command_rejects_a_non_positive_amount(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, "advance_day(amount=0)")

    assert any(is_err for _text, is_err in console.lines)


def test_give_nightmare_command_shows_the_dream_then_scares(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, 'give_nightmare("Steve")')

    # The bad dream shows first (😴💭); the scare is scheduled, not immediate --
    # so a wake doesn't wipe the dream before it can be seen.
    assert steve.dream is not None
    assert steve.dream.category == "bad"
    assert steve._nightmare_wake_at is not None
    assert steve._just_scared_until is None
    assert any("dreamed about" in m.lower() for m in steve.memory_log)

    # Close the console first -- Auto-Pause (default on) freezes the tank
    # while it's open, and this is testing the nightmare tick, not that.
    app.close_overlay(console)

    # After the wake delay, the per-second tick fires the scare (😨).
    steve._nightmare_wake_at = time.monotonic()  # due now
    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert steve.dream is None
    assert steve._just_scared_until is not None
    assert any("nightmare" in t.lower() for t in toasts)


def test_give_nightmare_command_scare_false_lingers_without_waking(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, 'give_nightmare("Steve", "ice", scare=False)')

    # The exact bad dream is set, viewable, and no wake-up is scheduled.
    assert steve.dream is not None
    assert steve.dream.title == "The Water Turned to Ice"
    assert steve._nightmare_wake_at is None
    assert steve._just_scared_until is None


def test_hud_treat_dropdown_drops_from_inventory_and_warns_when_empty(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    # Buy exactly one Pizza into the treat inventory via the console.
    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, "set_money(1000)")
    _type_into_console(console, 'buy("Pizza")')
    app.close_overlay(console)

    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    dropdown = next(w for w in app.widgets if isinstance(w, aq.Dropdown))

    # Choosing Pizza drops one into the tank (same reacting Food the console's
    # spawn() makes), spending the one we bought.
    dropdown._select_handler("Pizza")
    pizzas = [
        w
        for w in app.widgets
        if isinstance(w, aq.Food) and getattr(w, "kind", None) == "Pizza"
    ]
    assert len(pizzas) == 1
    assert pizzas[0].on_eaten is not None
    assert any("Dropped a Pizza" in t for t in toasts)

    # Inventory is now empty -- a second pick warns instead of dropping.
    toasts.clear()
    dropdown._select_handler("Pizza")
    still_one = [
        w
        for w in app.widgets
        if isinstance(w, aq.Food) and getattr(w, "kind", None) == "Pizza"
    ]
    assert len(still_one) == 1  # nothing new dropped
    assert any("No Pizza to drop" in t for t in toasts)


def test_hud_treat_dropdown_hint_row_is_a_no_op(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    dropdown = next(w for w in app.widgets if isinstance(w, aq.Dropdown))

    dropdown._select_handler(None)  # the "🍤 Drop treat…" caption row

    assert not any(isinstance(w, aq.Food) for w in app.widgets)
    assert toasts == []


# ── Save/Load: same-slot saving, Rename, Duplicate, Delete ────────────────────


def _saves_dir(tmp_path):
    return tmp_path / ".termquarium" / "saves"


def _save_via_prompt(app, name):
    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = name
    prompt.on_key(aq.Key.ENTER)


def _open_load_button(app, label):
    app._key_handlers["l"]()
    load_box = app._overlays[-1].widget
    return next(
        c
        for c in load_box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == label
    )


def test_second_save_reuses_the_same_slot_instead_of_prompting(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _save_via_prompt(app, "My Aquarium")
    assert app._topmost_modal() is None
    assert {p.stem for p in _saves_dir(tmp_path).glob("*.json")} == {"My Aquarium"}

    app._key_handlers["p"]()  # second save -- no prompt this time

    assert app._topmost_modal() is None  # no new prompt opened
    assert {p.stem for p in _saves_dir(tmp_path).glob("*.json")} == {"My Aquarium"}


def test_loading_a_save_attaches_future_saves_to_it(tmp_path, monkeypatch):
    aq.write_save(
        "Existing Save", {"state": {"money": 999}, "day": 5, "fish": []}, home=tmp_path
    )
    app = _headless_app(tmp_path, monkeypatch)

    _open_load_button(app, "Load").on_mouse_click()
    app._key_handlers["p"]()  # should attach to "Existing Save", not prompt

    assert app._topmost_modal() is None
    assert {p.stem for p in _saves_dir(tmp_path).glob("*.json")} == {"Existing Save"}


def test_load_menu_rename_renames_the_file_in_place(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _save_via_prompt(app, "Old Name")

    _open_load_button(app, "Rename").on_mouse_click()
    rename_prompt = app._overlays[-1].widget
    assert rename_prompt.text == "Old Name"
    rename_prompt.text = "New Name"
    rename_prompt.on_key(aq.Key.ENTER)

    assert {p.stem for p in _saves_dir(tmp_path).glob("*.json")} == {"New Name"}


def test_load_menu_rename_updates_the_attached_save_name(tmp_path, monkeypatch):
    # Renaming the save the session is currently attached to must repoint
    # future Saves at the new name too, not the now-deleted old one.
    app = _headless_app(tmp_path, monkeypatch)
    _save_via_prompt(app, "Old Name")

    _open_load_button(app, "Rename").on_mouse_click()
    rename_prompt = app._overlays[-1].widget
    rename_prompt.text = "New Name"
    rename_prompt.on_key(aq.Key.ENTER)
    # Rename reopens a fresh Load menu (its card list changed) -- close it,
    # same as the player closing the menu before pressing Save.
    app.close_overlay(app._topmost_modal().widget)

    app._key_handlers[
        "p"
    ]()  # should save into "New Name", not prompt or recreate "Old Name"

    assert app._topmost_modal() is None
    assert {p.stem for p in _saves_dir(tmp_path).glob("*.json")} == {"New Name"}


def test_load_menu_duplicate_creates_a_second_save(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _save_via_prompt(app, "Original")

    _open_load_button(app, "Duplicate").on_mouse_click()
    dup_prompt = app._overlays[-1].widget
    assert dup_prompt.text == "Original copy"
    dup_prompt.on_key(aq.Key.ENTER)

    assert {p.stem for p in _saves_dir(tmp_path).glob("*.json")} == {
        "Original",
        "Original copy",
    }


def test_load_menu_delete_removes_the_save_after_confirmation(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _save_via_prompt(app, "Doomed")

    _open_load_button(app, "Delete").on_mouse_click()
    confirm = app._overlays[-1].widget
    assert list(_saves_dir(tmp_path).glob("*.json"))  # not yet deleted
    confirm.on_key("y")

    assert list(_saves_dir(tmp_path).glob("*.json")) == []


def test_deleting_the_attached_save_makes_the_next_save_prompt_again(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    _save_via_prompt(app, "Doomed")

    _open_load_button(app, "Delete").on_mouse_click()
    confirm = app._overlays[-1].widget
    confirm.on_key("y")

    app._key_handlers["p"]()

    assert app._overlays  # a fresh Save prompt opened, not a silent re-save
    assert app._overlays[-1].widget.text == "Aquarium Day 0"  # the default-name prompt


# ── Phase 5: fish react to the environment (day/night, water temperature) ────


def test_night_does_not_affect_effective_speed():
    # Night no longer lives in _effective_speed() -- a sleeping fish is a
    # hard stop (see the sleeping-behavior tests below), not just slower.
    f = _neutral_fish(5.0, 5.0, environment={"phase": "Night", "temperature": 23.0})
    f.personality = "Explorer"
    f.speed = 5.0
    assert f._effective_speed() == 5.0


def test_day_is_full_speed_when_temperature_is_comfortable():
    f = _neutral_fish(5.0, 5.0, environment={"phase": "Day", "temperature": 23.0})
    f.personality = "Explorer"
    f.speed = 5.0
    assert f._effective_speed() == 5.0


def test_cold_water_slows_fish_down():
    f = _neutral_fish(
        5.0,
        5.0,
        environment={"phase": "Day", "temperature": aq.COLD_TEMP_THRESHOLD - 1},
    )
    f.personality = "Explorer"
    f.speed = 5.0
    assert f._effective_speed() == pytest.approx(5.0 * aq.COLD_SPEED_MULT)


def test_cold_still_applies_regardless_of_phase():
    f = _neutral_fish(
        5.0,
        5.0,
        environment={"phase": "Night", "temperature": aq.COLD_TEMP_THRESHOLD - 1},
    )
    f.personality = "Explorer"
    f.speed = 5.0
    assert f._effective_speed() == pytest.approx(5.0 * aq.COLD_SPEED_MULT)


def test_no_environment_is_unaffected():
    f = _neutral_fish(5.0, 5.0)  # environment=None by default
    f.personality = "Explorer"
    f.speed = 5.0
    assert f._effective_speed() == 5.0


def test_sleeping_fish_draws_a_zzz_glyph_above_itself():
    f = _neutral_fish(5.0, 5.0, environment={"phase": "Night", "temperature": 23.0})
    f._next_turn = float("inf")
    f.x, f.y = 5, 5

    canvas = _FakeCanvas()
    writes = []
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    f.draw(canvas)

    assert any(text == "😴" for _x, _y, text in writes)


def test_awake_fish_does_not_draw_the_sleeping_glyph():
    f = _neutral_fish(5.0, 5.0, environment={"phase": "Day", "temperature": 23.0})
    f._next_turn = float("inf")
    f.x, f.y = 5, 5

    canvas = _FakeCanvas()
    writes = []
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    f.draw(canvas)

    assert not any(text == "😴" for _x, _y, text in writes)


def test_sleep_takes_visual_priority_over_the_friendly_heart():
    bounds = (0.0, 0.0, 50.0, 50.0)
    mouse_pos = {"x": 5.0, "y": 5.0}
    f = _neutral_fish(
        5.0,
        5.0,
        bounds,
        mouse_pos=mouse_pos,
        environment={"phase": "Night", "temperature": 23.0},
    )
    f.personality = "Friendly"
    f._next_turn = float("inf")

    canvas = _FakeCanvas()
    writes = []
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    f.draw(canvas)

    assert any(text == "😴" for _x, _y, text in writes)
    assert not any(text == "💕" for _x, _y, text in writes)


def test_sleeping_fish_with_no_friend_or_rival_comes_to_a_full_stop():
    f = _neutral_fish(5.0, 5.0, environment={"phase": "Night", "temperature": 23.0})
    f._next_turn = float("inf")
    f.vx, f.vy = 3.0, 4.0

    _age(f)
    f.draw(_FakeCanvas())

    # Damped toward zero (IDLE_DAMPING < 1), not wandering off at full speed.
    assert math.hypot(f.vx, f.vy) < math.hypot(3.0, 4.0)


def test_hungry_fish_refuses_to_sleep():
    bounds = (0.0, 0.0, 50.0, 50.0)
    foods = [aq.Food(20.0, 5.0)]
    f = _neutral_fish(
        5.0,
        5.0,
        bounds,
        foods=foods,
        environment={"phase": "Night", "temperature": 23.0},
    )
    f.hunger = aq.SLEEP_HUNGER_THRESHOLD - 1
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # awake and chasing food despite being nighttime


def test_hungry_fish_does_not_draw_the_sleeping_glyph():
    f = _neutral_fish(5.0, 5.0, environment={"phase": "Night", "temperature": 23.0})
    f.hunger = aq.SLEEP_HUNGER_THRESHOLD - 1
    f._next_turn = float("inf")

    canvas = _FakeCanvas()
    writes = []
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    f.draw(canvas)

    assert not any(text == "😴" for _x, _y, text in writes)


def test_fish_at_the_hunger_threshold_still_sleeps():
    f = _neutral_fish(5.0, 5.0, environment={"phase": "Night", "temperature": 23.0})
    f.hunger = aq.SLEEP_HUNGER_THRESHOLD  # exactly at the boundary, not over it
    f._next_turn = float("inf")

    canvas = _FakeCanvas()
    writes = []
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    f.draw(canvas)

    assert any(text == "😴" for _x, _y, text in writes)


def test_a_shark_never_sleeps_even_at_night_with_low_hunger():
    f = _neutral_fish(
        5.0,
        5.0,
        environment={"phase": "Night", "temperature": 23.0},
        is_predator=True,
    )
    f.hunger = 100.0
    f._next_turn = float("inf")

    canvas = _FakeCanvas()
    writes = []
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    f.draw(canvas)

    assert not any(text in ("😴", "😴💭") for _x, _y, text in writes)


def test_friends_sleep_close_together():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(
        5.0, 5.0, bounds, environment={"phase": "Night", "temperature": 23.0}
    )
    friend = _neutral_fish(30.0, 5.0, bounds)
    aq.set_relationship(f, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # drifting toward the friend at higher x, even while asleep


def test_sleeping_fish_settles_once_close_enough_to_its_friend():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(
        5.0, 5.0, bounds, environment={"phase": "Night", "temperature": 23.0}
    )
    friend = _neutral_fish(6.0, 5.0, bounds)  # already within SLEEP_CLOSE_DISTANCE
    aq.set_relationship(f, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    f._next_turn = float("inf")
    f.vx, f.vy = 3.0, 4.0

    _age(f)
    f.draw(_FakeCanvas())

    assert math.hypot(f.vx, f.vy) < math.hypot(3.0, 4.0)  # settling, not still chasing


def test_nightmare_seeking_fish_is_not_auto_claimed_into_a_different_home():
    # Regression: draw()'s "if sleeping_in is None: auto-claim a home" ran
    # unconditionally, so the very next frame after _trigger_nightmare_
    # relocation() deliberately left sleeping_in=None (to steer this fish
    # toward a companion instead), it silently grabbed some other nearby
    # container and short-circuited the seek before the fish ever moved --
    # the "went to sleep beside X" toast/log then fired even though the
    # fish never actually went anywhere near its companion.
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(6.0, 5.0)  # right next to the fish -- an easy auto-claim
    companion = _neutral_fish(40.0, 5.0, bounds)
    f = _neutral_fish(
        5.0,
        5.0,
        bounds,
        decorations=[castle],
        environment={"phase": "Night", "temperature": 23.0},
    )
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0
    f._seeking_friend_after_nightmare = True
    f._nightmare_seek_target = companion

    _age(f)
    f.draw(_FakeCanvas())

    assert f.sleeping_in is None  # not auto-claimed into the castle
    assert not f._entered
    assert f.vx > 0.0  # steering toward the companion at higher x instead


def test_rivals_sleep_far_apart():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(
        20.0, 5.0, bounds, environment={"phase": "Night", "temperature": 23.0}
    )
    rival = _neutral_fish(21.0, 5.0, bounds)  # right next to it
    aq.set_relationship(f, rival, aq.RELATIONSHIP_RIVAL_THRESHOLD)
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx < 0.0  # fleeing toward lower x, away from the rival at x=21


def test_sleeping_fish_settles_once_far_enough_from_its_rival():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(
        0.0, 5.0, bounds, environment={"phase": "Night", "temperature": 23.0}
    )
    rival = _neutral_fish(
        aq.SLEEP_FAR_DISTANCE + 1, 5.0, bounds
    )  # already beyond SLEEP_FAR_DISTANCE
    aq.set_relationship(f, rival, aq.RELATIONSHIP_RIVAL_THRESHOLD)
    f._next_turn = float("inf")
    f.vx, f.vy = 3.0, 4.0

    _age(f)
    f.draw(_FakeCanvas())

    assert math.hypot(f.vx, f.vy) < math.hypot(3.0, 4.0)  # settling, not still fleeing


def test_rival_fleeing_never_converges_on_a_shared_hiding_decoration():
    # Regression: fleeing a Rival used to reuse Shy's "hide behind the
    # nearest decoration" response. If that decoration was nearest to both
    # rivals, they'd both steer toward the *same* spot -- converging
    # instead of separating, i.e. "stuck next to each other".
    bounds = (0.0, 0.0, 50.0, 50.0)
    spot = aq.Decoration(10.0, 5.0, aq.ROCK_ART, aq.ROCK_COLORS, kind="Rock")
    a = _neutral_fish(8.0, 5.0, bounds, decorations=[spot])
    b = _neutral_fish(12.0, 5.0, bounds, decorations=[spot])
    aq.set_relationship(a, b, aq.RELATIONSHIP_RIVAL_THRESHOLD)
    a._next_turn = float("inf")
    b._next_turn = float("inf")
    a.vx = b.vx = 0.0
    a.vy = b.vy = 0.0

    _age(a)
    _age(b)
    a.draw(_FakeCanvas())
    b.draw(_FakeCanvas())

    assert a.vx < 0.0  # a flees left, away from b
    assert b.vx > 0.0  # b flees right, away from a -- they separate, not converge


def test_mouse_fleeing_with_no_decorations_works_at_any_distance_within_flee_radius():
    # Regression: the no-decoration fallback used to reuse avoid_decorations()
    # with AVOID_MARGIN as its influence radius (3.0), far shorter than
    # SHY_FLEE_RADIUS (6.0) -- a Shy fish "scared" of a mouse 4-6 cells away
    # would report fleeing=True but avoid_decorations() would then silently
    # leave its velocity untouched, since it was outside AVOID_MARGIN.
    bounds = (0.0, 0.0, 50.0, 50.0)
    mouse_pos = {"x": 0.0, "y": 5.0}
    f = _neutral_fish(5.0, 5.0, bounds, mouse_pos=mouse_pos)  # distance 5, within 3..6
    f.personality = "Shy"
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # fled toward +x, away from the mouse at x=0


# ── Phase 6: polish + stress test ─────────────────────────────────────────────


def test_rise_bubble_moves_up_over_time():
    assert aq.rise_bubble(10.0, 2.0, 1.0) == 8.0


def test_rise_bubble_faster_speed_moves_further():
    assert aq.rise_bubble(10.0, 4.0, 1.0) < aq.rise_bubble(10.0, 2.0, 1.0)


def _bubble_field(bounds=(0.0, 0.0, 20.0, 10.0), enabled=True):
    field = aq.BubbleField(bounds, lambda: enabled)
    field._last = time.monotonic() - 0.1
    return field


def test_bubble_field_spawns_a_bubble_once_its_timer_elapses():
    field = _bubble_field()
    field._next_spawn = 0.0
    field.draw(_FakeCanvas())
    assert len(field._bubbles) == 1


def test_bubble_field_disabled_draws_nothing_and_clears_existing_bubbles():
    field = _bubble_field(enabled=False)
    field._bubbles = [aq._Bubble(5.0, 5.0, 2.0, "o")]

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    field.draw(canvas)

    assert writes == []
    assert field._bubbles == []


def test_bubble_field_removes_bubbles_once_they_reach_the_top():
    x0, y0, x1, y1 = 0.0, 0.0, 20.0, 10.0
    field = _bubble_field((x0, y0, x1, y1))
    field._bubbles = [aq._Bubble(5.0, y0 + 0.05, 100.0, "o")]  # one frame from the top
    field._next_spawn = 999.0  # don't also spawn a fresh one this frame

    field.draw(_FakeCanvas())

    assert field._bubbles == []


def test_bubble_field_caps_at_max_bubble_count():
    field = _bubble_field()
    field._bubbles = [
        aq._Bubble(1.0, 5.0, 0.0, "o") for _ in range(aq.BUBBLE_MAX_COUNT)
    ]
    field._next_spawn = 0.0

    field.draw(_FakeCanvas())

    assert len(field._bubbles) == aq.BUBBLE_MAX_COUNT


def test_bubble_field_freezes_existing_bubbles_and_spawns_none_while_paused():
    field = aq.BubbleField(
        (0.0, 0.0, 20.0, 10.0), lambda: True, lambda: True  # enabled, paused
    )
    field._last = time.monotonic() - 0.5
    field._bubbles = [aq._Bubble(5.0, 5.0, 2.0, "o")]
    field._next_spawn = 0.0  # would spawn immediately if not paused

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    field.draw(canvas)

    assert len(field._bubbles) == 1  # unchanged -- no spawn, no removal
    assert field._bubbles[0].y == 5.0  # frozen, didn't rise
    assert writes == [(5, 5, "o")]  # still drawn, just not moving


def test_stress_test_key_mass_spawns_fish_up_to_the_cap(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["z"]()
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    assert len(fishes) == aq.STRESS_TEST_TARGET


def test_stress_test_key_is_a_no_op_once_already_at_the_cap(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["z"]()
    app._key_handlers["z"]()  # pressed again, already at the cap
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    assert len(fishes) == aq.STRESS_TEST_TARGET


def test_settings_bubbles_checkbox_toggles_state():
    from cozy_tui import App

    app = App(full=False, size="400x200")
    state = {"bubbles_enabled": True}
    box = aq._build_settings(
        app, state, None, lambda: None, lambda: None, lambda: None, lambda: None
    )
    bubbles_cb = next(
        c
        for c in box.children
        if c.__class__.__name__ == "Checkbox" and "Bubbles" in c.text
    )
    bubbles_cb.on_mouse_click()  # was checked=True, so this unchecks it

    assert state["bubbles_enabled"] is False


def test_settings_auto_pause_checkbox_toggles_state():
    from cozy_tui import App

    app = App(full=False, size="400x200")
    state = {"auto_pause": True}
    box = aq._build_settings(
        app, state, None, lambda: None, lambda: None, lambda: None, lambda: None
    )
    auto_pause_cb = next(
        c
        for c in box.children
        if c.__class__.__name__ == "Checkbox" and "Auto-Pause" in c.text
    )
    auto_pause_cb.on_mouse_click()  # was checked=True, so this unchecks it

    assert state["auto_pause"] is False


# ── Schooling ──────────────────────────────────────────────────────────────


def test_school_velocity_no_neighbors_leaves_velocity_unchanged():
    vx, vy = aq.school_velocity(0.0, 0.0, 1.0, 2.0, [], 5.0, 1.0, 1.0, 0.8, 1.2, 1.5)
    assert (vx, vy) == (1.0, 2.0)


def test_school_velocity_cohesion_pulls_toward_flock_center():
    # One neighbor far to +x with no velocity (alignment contributes
    # nothing) and far enough away that separation doesn't trigger.
    neighbors = [(10.0, 0.0, 0.0, 0.0)]
    vx, _vy = aq.school_velocity(
        0.0, 0.0, 0.0, 5.0, neighbors, 5.0, 1.0, 1.0, 0.8, 1.2, 1.5
    )
    assert vx > 0.0  # pulled toward the neighbor at +x


def test_school_velocity_alignment_matches_average_heading():
    # Neighbor exactly overlapping (no cohesion pull) but moving toward +x --
    # isolates alignment by zeroing cohesion/separation weights.
    neighbors = [(0.0, 0.0, 5.0, 0.0)]
    vx, _vy = aq.school_velocity(
        0.0, 0.0, 0.0, 5.0, neighbors, 5.0, 1.0, 0.0, 0.8, 0.0, 1.5
    )
    assert vx > 0.0  # matched the neighbor's +x heading


def test_school_velocity_separation_pushes_apart_when_crowded():
    # Neighbor very close at +x -- isolates separation by zeroing the other
    # two weights, so any pull is purely "too crowded, back away".
    neighbors = [(1.0, 0.0, 0.0, 0.0)]
    vx, _vy = aq.school_velocity(
        0.0, 0.0, 0.0, 5.0, neighbors, 5.0, 1.0, 0.0, 0.0, 1.0, 1.5
    )
    assert vx < 0.0  # pushed away from the crowding neighbor at +x


def test_schoolmates_only_includes_same_species_within_radius():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(5.0, 5.0, bounds)
    same_species_near = _neutral_fish(6.0, 5.0, bounds)
    same_species_far = _neutral_fish(5.0 + aq.SCHOOL_RADIUS + 5.0, 5.0, bounds)
    other_species_near = _neutral_fish(5.5, 5.0, bounds)
    other_species_near.species_name = "Betta"

    fish_list = [f, same_species_near, same_species_far, other_species_near]
    f.fish_list = fish_list
    same_species_near.fish_list = fish_list
    same_species_far.fish_list = fish_list
    other_species_near.fish_list = fish_list

    mates = f._schoolmates()
    assert (
        same_species_near.fx,
        same_species_near.fy,
        same_species_near.vx,
        same_species_near.vy,
    ) in mates
    assert len(mates) == 1


def test_schoolmates_excludes_predators():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(5.0, 5.0, bounds)
    shark = _neutral_fish(6.0, 5.0, bounds, is_predator=True)
    shark.species_name = f.species_name

    fish_list = [f, shark]
    f.fish_list = fish_list
    shark.fish_list = fish_list

    assert f._schoolmates() == []


def test_predator_never_schools():
    bounds = (0.0, 0.0, 50.0, 50.0)
    shark = _neutral_fish(5.0, 5.0, bounds, is_predator=True)
    other_shark = _neutral_fish(6.0, 5.0, bounds, is_predator=True)
    other_shark.species_name = shark.species_name

    fish_list = [shark, other_shark]
    shark.fish_list = fish_list
    other_shark.fish_list = fish_list

    assert shark._schoolmates() == []


def test_axolotl_never_schools_even_with_another_axolotl():
    # Solitary/independent is one of the small ways an Axolotl feels
    # different from the schooling fish species -- not a stat difference.
    bounds = (0.0, 0.0, 50.0, 50.0)
    axolotl = _neutral_fish(5.0, 5.0, bounds)
    axolotl.species_name = "Axolotl"
    other_axolotl = _neutral_fish(6.0, 5.0, bounds)
    other_axolotl.species_name = "Axolotl"

    fish_list = [axolotl, other_axolotl]
    axolotl.fish_list = fish_list
    other_axolotl.fish_list = fish_list

    assert axolotl._schoolmates() == []


def test_fish_with_no_schoolmates_still_draws_without_error():
    f = _neutral_fish(5.0, 5.0)
    f._next_turn = float("inf")
    _age(f)
    f.draw(_FakeCanvas())  # must not raise even with an empty fish_list


def test_lone_schoolmate_pulls_fish_toward_it():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(5.0, 5.0, bounds)
    mate = _neutral_fish(5.0 + aq.SCHOOL_RADIUS - 1.0, 5.0, bounds)
    fish_list = [f, mate]
    f.fish_list = fish_list
    mate.fish_list = fish_list
    f.personality = "Explorer"  # not Friendly/etc -- isolate schooling
    f._next_turn = float("inf")
    f.favorite_decoration = None
    f.vx, f.vy = 0.0, 5.0  # heading straight up, away from the mate at +x

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # schooling pulled it toward the mate at +x


def test_schooling_is_overridden_by_fleeing():
    # Regression: schooling sits at the very bottom of the priority chain --
    # a Shy fish fleeing the mouse must not have that overridden by a
    # same-species schoolmate pulling it back the other way.
    bounds = (0.0, 0.0, 50.0, 50.0)
    mouse_pos = {"x": 6.0, "y": 5.0}
    f = _neutral_fish(5.0, 5.0, bounds, mouse_pos=mouse_pos)
    mate = _neutral_fish(0.0, 5.0, bounds)  # schoolmate in the opposite direction
    fish_list = [f, mate]
    f.fish_list = fish_list
    mate.fish_list = fish_list
    f.personality = "Shy"
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx < 0.0  # fled left, away from the mouse -- not pulled toward the mate


# ── Phase 7: container decorations (fish sleep inside) ────────────────────────


def _castle(x=10.0, y=5.0):
    return aq.Decoration(
        x, y, aq.CASTLE_ART, aq.CASTLE_COLORS, kind="Castle", capacity=2
    )


def _sleepy_fish(x, y, bounds, decorations=None, **kw):
    f = _neutral_fish(
        x,
        y,
        bounds,
        decorations=decorations,
        environment={"phase": "Night", "temperature": 23.0},
        **kw,
    )
    f._next_turn = float("inf")
    f.hunger = 100.0
    # Baseline (non-personality-specific) priority tests want a personality
    # with no special-cased _claim_home() behavior -- Explorer's random
    # shuffle chance would otherwise make them flaky. Tests targeting a
    # specific personality override this explicitly.
    f.personality = "Greedy"
    return f


def test_decoration_default_capacity_is_zero_and_not_a_container():
    d = aq.Decoration(0.0, 0.0, ["x"], "white")
    assert d.capacity == 0
    assert not d.is_container


def test_decoration_with_capacity_is_a_container():
    d = _castle()
    assert d.is_container


def test_castle_and_rock_are_containers_plant_and_driftwood_are_not():
    catalog = aq.DECORATION_CATALOG
    assert catalog["Castle"].capacity > 0
    assert catalog["Rock"].capacity > 0
    assert catalog["Plant"].capacity == 0
    assert catalog["Driftwood"].capacity == 0


def test_occupants_of_returns_fish_sleeping_in_that_decoration():
    castle = _castle()
    other = _castle(30.0, 5.0)
    a = _neutral_fish(10.0, 5.0)
    b = _neutral_fish(10.0, 5.0)
    c = _neutral_fish(10.0, 5.0)
    a.sleeping_in = castle
    b.sleeping_in = other
    c.sleeping_in = None

    assert aq.occupants_of(castle, [a, b, c]) == [a]


def test_claim_home_prefers_the_favorite_container_when_it_has_room():
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(10.0, 5.0)
    other = _castle(40.0, 5.0)
    f = _sleepy_fish(11.0, 5.0, bounds, decorations=[castle, other])
    f.favorite_decoration = castle
    f.fish_list = [f]

    assert f._claim_home() is castle


def test_claim_home_skips_a_full_favorite_container():
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(10.0, 5.0)  # capacity 2
    f = _sleepy_fish(11.0, 5.0, bounds, decorations=[castle])
    f.favorite_decoration = castle
    a = _sleepy_fish(10.0, 5.0, bounds)
    b = _sleepy_fish(10.0, 5.0, bounds)
    a.sleeping_in = castle
    b.sleeping_in = castle  # castle is now full (capacity 2)
    f.fish_list = [f, a, b]

    assert f._claim_home() is None  # no other container available


def test_claim_home_joins_a_friends_container_when_favorite_is_unavailable():
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(10.0, 5.0)
    plant = aq.Decoration(20.0, 5.0, aq.PLANT_ART, aq.PLANT_COLORS, kind="Plant")
    friend = _sleepy_fish(10.0, 5.0, bounds)
    friend.sleeping_in = castle

    f = _sleepy_fish(11.0, 5.0, bounds, decorations=[plant, castle])
    f.favorite_decoration = plant  # not a container -- falls through
    aq.set_relationship(f, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    f.fish_list = [f, friend]

    assert f._claim_home() is castle


def test_claim_home_looks_elsewhere_if_the_friends_container_is_full():
    bounds = (0.0, 0.0, 50.0, 50.0)
    full_castle = _castle(10.0, 5.0)  # capacity 2
    empty_castle = _castle(40.0, 5.0)
    friend = _sleepy_fish(10.0, 5.0, bounds)
    friend.sleeping_in = full_castle
    a = _sleepy_fish(10.0, 5.0, bounds)
    a.sleeping_in = full_castle  # full_castle now has 2/2

    f = _sleepy_fish(11.0, 5.0, bounds, decorations=[full_castle, empty_castle])
    f.favorite_decoration = None  # isolate the "friend's container" tier
    aq.set_relationship(f, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    f.fish_list = [f, friend, a]

    assert f._claim_home() is empty_castle


def test_claim_home_picks_the_nearest_container_with_room():
    bounds = (0.0, 0.0, 50.0, 50.0)
    near = _castle(11.0, 5.0)
    far = _castle(40.0, 5.0)
    f = _sleepy_fish(10.0, 5.0, bounds, decorations=[far, near])
    f.favorite_decoration = None  # isolate the "nearest container" tier
    f.fish_list = [f]

    assert f._claim_home() is near


def test_claim_home_returns_none_when_every_container_is_full():
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(10.0, 5.0)
    a = _sleepy_fish(10.0, 5.0, bounds)
    b = _sleepy_fish(10.0, 5.0, bounds)
    a.sleeping_in = castle
    b.sleeping_in = castle

    f = _sleepy_fish(11.0, 5.0, bounds, decorations=[castle])
    f.fish_list = [f, a, b]

    assert f._claim_home() is None


# ── Phase 7: personality-driven sleep-location bias ───────────────────────────


def test_lazy_sleeps_on_the_floor_when_no_container_is_close():
    bounds = (0.0, 0.0, 50.0, 50.0)
    far_castle = _castle(10.0 + aq.LAZY_HOME_RADIUS + 5.0, 5.0)
    f = _sleepy_fish(10.0, 5.0, bounds, decorations=[far_castle])
    f.favorite_decoration = None
    f.personality = "Lazy"
    f.fish_list = [f]

    assert f._claim_home() is None


def test_lazy_takes_a_container_that_is_already_close():
    # Lazy won't travel for a container, but won't turn one down either.
    bounds = (0.0, 0.0, 50.0, 50.0)
    near_castle = _castle(10.0 + aq.LAZY_HOME_RADIUS - 1.0, 5.0)
    f = _sleepy_fish(10.0, 5.0, bounds, decorations=[near_castle])
    f.favorite_decoration = None
    f.personality = "Lazy"
    f.fish_list = [f]

    assert f._claim_home() is near_castle


def test_lazy_does_not_claim_a_full_container_even_if_close():
    bounds = (0.0, 0.0, 50.0, 50.0)
    near_castle = _castle(10.0 + aq.LAZY_HOME_RADIUS - 1.0, 5.0)  # capacity 2
    a = _sleepy_fish(10.0, 5.0, bounds)
    b = _sleepy_fish(10.0, 5.0, bounds)
    a.sleeping_in = near_castle
    b.sleeping_in = near_castle

    f = _sleepy_fish(10.0, 5.0, bounds, decorations=[near_castle])
    f.favorite_decoration = None
    f.personality = "Lazy"
    f.fish_list = [f, a, b]

    assert f._claim_home() is None


def test_shy_prefers_any_nearby_container_over_a_friends():
    bounds = (0.0, 0.0, 50.0, 50.0)
    near_empty = _castle(11.0, 5.0)
    far_friend_castle = _castle(40.0, 5.0)
    friend = _sleepy_fish(40.0, 5.0, bounds)
    friend.sleeping_in = far_friend_castle

    f = _sleepy_fish(10.0, 5.0, bounds, decorations=[near_empty, far_friend_castle])
    f.favorite_decoration = None
    f.personality = "Shy"
    aq.set_relationship(f, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    f.fish_list = [f, friend]

    assert f._claim_home() is near_empty  # shelter over togetherness


def test_shy_still_prefers_its_favorite_spot_first():
    bounds = (0.0, 0.0, 50.0, 50.0)
    favorite = _castle(10.0, 5.0)
    other = _castle(40.0, 5.0)
    f = _sleepy_fish(11.0, 5.0, bounds, decorations=[favorite, other])
    f.favorite_decoration = favorite
    f.personality = "Shy"
    f.fish_list = [f]

    assert f._claim_home() is favorite


def test_friendly_prefers_a_friends_container_over_its_own_favorite_spot():
    bounds = (0.0, 0.0, 50.0, 50.0)
    favorite = _castle(40.0, 5.0)
    friend_castle = _castle(10.0, 5.0)
    friend = _sleepy_fish(10.0, 5.0, bounds)
    friend.sleeping_in = friend_castle

    f = _sleepy_fish(11.0, 5.0, bounds, decorations=[favorite, friend_castle])
    f.favorite_decoration = favorite  # has room, but Friendly ranks friend first
    f.personality = "Friendly"
    aq.set_relationship(f, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    f.fish_list = [f, friend]

    assert f._claim_home() is friend_castle


def test_explorer_usually_picks_the_nearest_container(monkeypatch):
    bounds = (0.0, 0.0, 50.0, 50.0)
    near = _castle(11.0, 5.0)
    far = _castle(40.0, 5.0)
    f = _sleepy_fish(10.0, 5.0, bounds, decorations=[far, near])
    f.favorite_decoration = None
    f.personality = "Explorer"
    f.fish_list = [f]
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)  # above the shuffle chance

    assert f._claim_home() is near


def test_explorer_sometimes_shuffles_to_a_different_container(monkeypatch):
    bounds = (0.0, 0.0, 50.0, 50.0)
    near = _castle(11.0, 5.0)
    far = _castle(40.0, 5.0)
    f = _sleepy_fish(10.0, 5.0, bounds, decorations=[far, near])
    f.favorite_decoration = None
    f.personality = "Explorer"
    f.fish_list = [f]
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # below the shuffle chance
    monkeypatch.setattr(aq.random, "choice", lambda seq: far)

    assert f._claim_home() is far


def test_sleeping_fish_steers_toward_its_claimed_home():
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(20.0, 5.0)
    f = _sleepy_fish(5.0, 5.0, bounds, decorations=[castle])
    f.fish_list = [f]
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.sleeping_in is castle
    assert f.vx > 0.0  # steering toward the castle at +x


def test_a_live_storm_makes_an_awake_fish_steer_toward_the_nearest_container():
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(20.0, 5.0)
    f = _neutral_fish(
        5.0,
        5.0,
        bounds,
        decorations=[castle],
        environment={"phase": "Day", "temperature": 23.0, "storm": True},
    )
    f._next_turn = float("inf")  # isolate from the random-turn-timer
    f.hunger = 0.0
    f.fish_list = [f]
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.sleeping_in is None  # a live storm, not real sleep -- no housing claim
    assert not f._entered  # stays visible, unlike genuine night sleep
    assert f.vx > 0.0  # steering toward the castle at +x


def test_a_live_storm_settles_a_fish_once_it_reaches_shelter():
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(6.0, 5.0)  # 1 cell away -- well within arrival
    f = _neutral_fish(
        5.0,
        5.0,
        bounds,
        decorations=[castle],
        environment={"phase": "Day", "temperature": 23.0, "storm": True},
    )
    f._next_turn = float("inf")
    f.hunger = 0.0
    f.fish_list = [f]
    f.vx, f.vy = 3.0, 4.0

    _age(f)
    f.draw(_FakeCanvas())

    # Damped toward zero (IDLE_DAMPING < 1), not blended toward the target --
    # same "already arrived" shape as the relaxing/home-steering tests.
    assert math.hypot(f.vx, f.vy) < math.hypot(3.0, 4.0)
    # Regression: arrival never set _entered, so a sheltering fish stayed
    # fully visible, idling next to the shelter instead of tucking inside
    # it the way a sleeping/shark-hiding fish does.
    assert f._entered
    assert f._storm_sheltering is castle


def test_a_storm_sheltering_fish_reappears_once_the_storm_ends():
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(6.0, 5.0)
    environment = {"phase": "Day", "temperature": 23.0, "storm": True}
    f = _neutral_fish(
        5.0, 5.0, bounds, decorations=[castle], environment=environment
    )
    f._next_turn = float("inf")
    f.hunger = 0.0
    f.fish_list = [f]
    f.vx, f.vy = 3.0, 4.0

    _age(f)
    f.draw(_FakeCanvas())
    assert f._entered  # tucked in for the storm

    environment["storm"] = False  # mirrors aquarium.py's _end_storm()
    _age(f)
    f.draw(_FakeCanvas())

    assert not f._entered
    assert f._storm_sheltering is None


def test_no_storm_means_no_shelter_seeking():
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(20.0, 5.0)
    f = _neutral_fish(
        5.0,
        5.0,
        bounds,
        decorations=[castle],
        environment={"phase": "Day", "temperature": 23.0, "storm": False},
    )
    f._next_turn = float("inf")
    f.hunger = 0.0
    f.fish_list = [f]
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx == 0.0  # no storm -- nothing pulls it toward the castle
    assert not f._entered  # not close enough yet


def test_sleeping_fish_enters_and_disappears_once_arrived():
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(5.0, 5.0)
    f = _sleepy_fish(5.0, 5.0, bounds, decorations=[castle])  # already right there
    f.fish_list = [f]
    f.vx, f.vy = 0.0, 0.0

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f)
    f.draw(canvas)

    assert f._entered
    assert writes == []  # invisible -- nothing drawn for it this frame


def test_entered_fish_stays_hidden_and_frozen_on_later_frames():
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(5.0, 5.0)
    f = _sleepy_fish(5.0, 5.0, bounds, decorations=[castle])
    f.fish_list = [f]
    _age(f)
    f.draw(_FakeCanvas())
    assert f._entered
    fx_before, fy_before = f.fx, f.fy

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f)
    f.draw(canvas)

    assert writes == []
    assert (f.fx, f.fy) == (fx_before, fy_before)  # frozen in place


def test_waking_lingers_before_clearing_home_and_reappearing():
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(5.0, 5.0)
    f = _sleepy_fish(5.0, 5.0, bounds, decorations=[castle])
    f.fish_list = [f]
    _age(f)
    f.draw(_FakeCanvas())
    assert f._entered
    assert f.sleeping_in is castle

    f.environment["phase"] = "Day"  # morning -- wake up
    _age(f)
    f.draw(_FakeCanvas())

    # Doesn't vanish instantly -- lingers, still tucked in/invisible from
    # the open tank, just no longer shown asleep (see _awake_in_home).
    assert f.sleeping_in is castle
    assert f._awake_in_home is True
    assert f._entered

    f._wake_time = 0.0  # force WAKE_LINGER_SECONDS to have elapsed
    _age(f)
    f.draw(_FakeCanvas())

    assert f.sleeping_in is None
    assert not f._entered
    assert not f._awake_in_home
    # Reappears right at the castle, then immediately resumes normal
    # movement for the rest of that same frame -- close to the castle, not
    # pinned to it forever.
    assert math.hypot(f.fx - castle.fx, f.fy - castle.fy) < 1.0


def test_roommates_ready_to_leave_waits_for_the_last_to_wake():
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = _castle(5.0, 5.0)
    a = _neutral_fish(5.0, 5.0, bounds, decorations=[castle])
    b = _neutral_fish(5.0, 5.0, bounds, decorations=[castle])
    a.fish_list = b.fish_list = [a, b]
    a.sleeping_in = b.sleeping_in = castle
    a._entered = b._entered = True

    a._awake_in_home = True
    a._wake_time = 0.0  # long enough ago on its own
    b._awake_in_home = False  # b still asleep

    assert a._roommates_ready_to_leave() is False  # waiting on b

    b._awake_in_home = True
    b._wake_time = time.monotonic()  # b just woke

    assert a._roommates_ready_to_leave() is False  # not enough time since b woke

    b._wake_time = 0.0  # force enough time to have passed for b too

    assert a._roommates_ready_to_leave() is True
    assert (
        b._roommates_ready_to_leave() is True
    )  # both agree -> both leave the same frame


def test_wake_attempt_sets_a_boop_flash_on_the_waker(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    sleepy, friend = fishes[0], fishes[1]
    sleepy.is_sleepy = True
    friend.is_sleepy = False  # must be a genuinely eligible (awake) waker
    sleepy.sleeping_in = castle
    friend.sleeping_in = castle
    aq.set_relationship(sleepy, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD)

    fractions = iter([0.9, 0.2, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(
        aq.random, "random", lambda: 0.0
    )  # resists, but still a real attempt

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()  # still Night
    second_timer.callback()  # holding begins
    assert friend._just_booped_until is None  # no attempt has happened yet

    sleepy._wake_next_attempt = 0.0  # force the next tick to resolve immediately
    second_timer.callback()

    assert friend._just_booped_until is not None
    assert sleepy._holding_asleep is True  # resisted this time, still held


def test_resisted_wake_attempt_sets_a_zzz_flash_on_the_sleeper(tmp_path, monkeypatch):
    # The other half of test_wake_attempt_sets_a_boop_flash_on_the_waker --
    # the fish being booped, not just the one doing the booping, needs its
    # own visible reaction to a resisted attempt.
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    sleepy, friend = fishes[0], fishes[1]
    sleepy.is_sleepy = True
    friend.is_sleepy = False  # must be a genuinely eligible (awake) waker
    sleepy.sleeping_in = castle
    friend.sleeping_in = castle
    aq.set_relationship(sleepy, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD)

    fractions = iter([0.9, 0.2, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # resists

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()  # still Night
    second_timer.callback()  # holding begins
    assert sleepy._just_resisted_wake_until is None  # no attempt has happened yet

    sleepy._wake_next_attempt = 0.0
    second_timer.callback()

    assert sleepy._just_resisted_wake_until is not None
    assert sleepy._holding_asleep is True


def test_resisted_wake_attempt_toasts_only_on_the_first_try(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    sleepy, friend = fishes[0], fishes[1]
    sleepy.display_name, friend.display_name = "Kitty", "Steve"
    sleepy.is_sleepy = True
    friend.is_sleepy = False  # only Kitty's hold should ever be created
    sleepy.sleeping_in = castle
    friend.sleeping_in = castle
    aq.set_relationship(sleepy, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD)

    fractions = iter([0.9, 0.2, 0.2, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # always resists
    # Isolated from the (unrelated) Morning Vignette, which fires at the same
    # Night -> Morning transition and -- with random() pinned this low --
    # would otherwise also roll Kitty/Steve as its own featured pair with its
    # own "resist" flavor, independently reusing the exact same wording and
    # making this look like a duplicate toast from _process_sleepy_holds.
    monkeypatch.setattr(aq, "find_mutual_friend_pairs", lambda *a, **k: [])

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()  # still Night
    second_timer.callback()  # holding begins

    sleepy._wake_next_attempt = 0.0
    second_timer.callback()  # first resisted attempt

    resist_toasts = [t for t in toasts if "too sleepy to notice" in t]
    assert resist_toasts == [
        "Steve tries to boop Kitty awake... but Kitty is too sleepy to notice!"
    ]
    assert any(
        "tried to wake Kitty up" in m and "too sleepy to notice" in m
        for m in friend.memory_log
    )

    sleepy._wake_next_attempt = 0.0
    second_timer.callback()  # second resisted attempt -- no new toast

    resist_toasts = [t for t in toasts if "too sleepy to notice" in t]
    assert len(resist_toasts) == 1  # unchanged -- not a toast per retry


def test_boop_and_zzz_moods_surface_above_housed_fish_in_the_open_tank():
    bounds = (0.0, 0.0, 50.0, 50.0)
    waker = _sleepy_fish(5.0, 5.0, bounds)
    waker.fish_list = [waker]
    waker._entered = True
    waker._just_booped_until = time.monotonic() + 10.0

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(waker)
    waker.draw(canvas)
    assert any(text == "*boop*" for _x, _y, text in writes)

    sleeper = _sleepy_fish(5.0, 5.0, bounds)
    sleeper.fish_list = [sleeper]
    sleeper._entered = True
    sleeper._just_resisted_wake_until = time.monotonic() + 10.0

    writes.clear()
    _age(sleeper)
    sleeper.draw(canvas)
    assert any(text == "*...zzz*" for _x, _y, text in writes)


def test_boop_mood_takes_visual_priority_over_scared_and_comfort():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _sleepy_fish(5.0, 5.0, bounds)
    f.fish_list = [f]
    f._just_booped_until = time.monotonic() + 10.0
    f._just_scared_until = time.monotonic() + 10.0
    f._nightmare_comfort_until = time.monotonic() + 10.0

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f)
    f.draw(canvas)

    assert any(text == "*boop*" for _x, _y, text in writes)
    assert not any(text in ("😨", "🥺") for _x, _y, text in writes)


def test_castle_interior_shows_the_zzz_mood():
    from cozy_tui import App

    app = App(full=False, size="380x300")
    castle = _castle()
    sleeper = _neutral_fish(5.0, 5.0)
    sleeper.display_name = "Kitty"
    sleeper.sleeping_in = castle
    sleeper._just_resisted_wake_until = time.monotonic() + 10.0

    box = aq._build_castle_interior(app, castle, [sleeper])
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any("Kitty" in t and "*...zzz*" in t for t in labels)


def test_capacity_is_enforced_across_two_fish_over_several_frames():
    bounds = (0.0, 0.0, 50.0, 50.0)
    castle = aq.Decoration(
        5.0, 5.0, aq.CASTLE_ART, aq.CASTLE_COLORS, kind="Castle", capacity=1
    )
    a = _sleepy_fish(5.0, 5.0, bounds, decorations=[castle])
    b = _sleepy_fish(5.0, 5.0, bounds, decorations=[castle])
    fish_list = [a, b]
    a.fish_list = fish_list
    b.fish_list = fish_list

    for _ in range(5):
        _age(a)
        _age(b)
        a.draw(_FakeCanvas())
        b.draw(_FakeCanvas())

    entered = [f for f in fish_list if f._entered]
    assert len(entered) == 1  # only one fit -- capacity 1
    assert {f.sleeping_in for f in fish_list if f.sleeping_in is not None} == {castle}


def test_decoration_inspector_shows_capacity_and_occupants():
    from cozy_tui import App

    app = App(full=False, size="340x220")
    castle = _castle()
    guest = _neutral_fish(5.0, 5.0)
    guest.display_name = "Steve"
    guest.sleeping_in = castle

    box = aq._build_decoration_inspector(
        app, castle, [guest], lambda d: None, lambda d: None
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any("Capacity: 1/2" in t for t in labels)
    assert any("Steve" in t for t in labels)


def test_decoration_inspector_shows_empty_message_with_no_occupants():
    from cozy_tui import App

    app = App(full=False, size="340x220")
    castle = _castle()

    box = aq._build_decoration_inspector(
        app, castle, [], lambda d: None, lambda d: None
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any("nobody home" in t for t in labels)


def test_decoration_inspector_omits_capacity_for_a_non_container():
    from cozy_tui import App

    app = App(full=False, size="340x220")
    plant = aq.Decoration(0.0, 0.0, aq.PLANT_ART, aq.PLANT_COLORS, kind="Plant")

    box = aq._build_decoration_inspector(app, plant, [], lambda d: None, lambda d: None)
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert not any("Capacity" in t for t in labels)


def test_decoration_inspector_has_no_enter_button_for_a_non_container():
    from cozy_tui import App

    app = App(full=False, size="340x220")
    plant = aq.Decoration(0.0, 0.0, aq.PLANT_ART, aq.PLANT_COLORS, kind="Plant")

    box = aq._build_decoration_inspector(app, plant, [], lambda d: None, lambda d: None)
    buttons = [c.text for c in box.children if c.__class__.__name__ == "Button"]

    assert not any("Enter" in t for t in buttons)


def test_decoration_inspector_enter_button_opens_the_castle_interior():
    from cozy_tui import App

    app = App(full=False, size="340x220")
    castle = _castle()
    entered = []

    box = aq._build_decoration_inspector(
        app, castle, [], lambda d: None, entered.append
    )
    enter_btn = next(
        c
        for c in box.children
        if c.__class__.__name__ == "Button" and "Enter" in c.text
    )
    enter_btn.on_mouse_click()

    assert entered == [castle]


def test_castle_interior_shows_a_bed_per_two_capacity():
    from cozy_tui import App

    app = App(full=False, size="380x300")
    castle = aq.Decoration(
        0.0, 0.0, aq.CASTLE_ART, aq.CASTLE_COLORS, kind="Castle", capacity=4
    )
    guest = _neutral_fish(5.0, 5.0)
    guest.display_name = "Steve"
    guest.sleeping_in = castle

    box = aq._build_castle_interior(app, castle, [guest])
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert sum(1 for t in labels if set(t) == {"-"}) == 4  # 2 beds -> 4 divider rows
    assert any("Steve" in t and "😴" in t for t in labels)
    assert sum(1 for t in labels if "(empty)" in t) == 3  # 4 slots, 1 filled


def test_castle_interior_shows_species_agnostic_generic_fish_icon():
    from cozy_tui import App

    app = App(full=False, size="380x300")
    castle = _castle()
    guest = _neutral_fish(5.0, 5.0)  # a Goldfish glyph ("><>"), per _neutral_fish
    guest.display_name = "Steve"
    guest.sleeping_in = castle

    box = aq._build_castle_interior(app, castle, [guest])
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any("🐠 Steve" in t for t in labels)
    assert not any("><>" in t for t in labels)


def test_castle_interior_shows_a_lingering_woken_fish_as_awake_not_asleep():
    from cozy_tui import App

    app = App(full=False, size="380x300")
    castle = _castle()
    sleeper = _neutral_fish(5.0, 5.0)
    sleeper.display_name = "Alice"
    sleeper.sleeping_in = castle
    woken = _neutral_fish(6.0, 5.0)
    woken.display_name = "Steve"
    woken.sleeping_in = castle
    woken._awake_in_home = True  # lingering, per WAKE_LINGER_SECONDS

    box = aq._build_castle_interior(app, castle, [sleeper, woken])
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any("Alice" in t and "😴" in t for t in labels)
    assert any("Steve" in t and "🙂" in t for t in labels)


def test_castle_interior_shows_boop_instead_of_mood_during_a_flash():
    from cozy_tui import App

    app = App(full=False, size="380x300")
    castle = _castle()
    guest = _neutral_fish(5.0, 5.0)
    guest.display_name = "Steve"
    guest.sleeping_in = castle
    guest._awake_in_home = True
    guest._just_booped_until = time.monotonic() + 10.0  # well within the flash window

    box = aq._build_castle_interior(app, castle, [guest])
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any("Steve" in t and "*boop*" in t for t in labels)
    assert not any("Steve" in t and "🙂" in t for t in labels)


def test_castle_interior_reverts_to_mood_once_the_boop_flash_expires():
    from cozy_tui import App

    app = App(full=False, size="380x300")
    castle = _castle()
    guest = _neutral_fish(5.0, 5.0)
    guest.display_name = "Steve"
    guest.sleeping_in = castle
    guest._awake_in_home = True
    guest._just_booped_until = time.monotonic() - 1.0  # already expired

    box = aq._build_castle_interior(app, castle, [guest])
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any("Steve" in t and "🙂" in t for t in labels)
    assert not any("*boop*" in t for t in labels)


def test_castle_interior_empty_container_shows_all_empty_slots():
    from cozy_tui import App

    app = App(full=False, size="380x300")
    castle = _castle()

    box = aq._build_castle_interior(app, castle, [])
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert sum(1 for t in labels if "(empty)" in t) == 2


def test_castle_interior_leave_button_closes_the_overlay():
    from cozy_tui import App

    app = App(full=False, size="380x300")
    castle = _castle()

    box = aq._build_castle_interior(app, castle, [])
    app.open_overlay(box)
    assert app._overlays

    leave_btn = next(c for c in box.children if c.__class__.__name__ == "Button")
    assert leave_btn.text == "Leave"
    leave_btn.on_mouse_click()

    assert not app._overlays


def test_fish_inspector_shows_home_tonight_only_while_housed():
    castle = _castle()
    awake = _neutral_fish(5.0, 5.0)
    housed = _neutral_fish(5.0, 5.0)
    housed.sleeping_in = castle

    box_awake = aq._build_inspector(
        aq.App(full=False, size="360x300"),
        awake,
        lambda f: None,
        lambda f: None,
        {},
        lambda f, kind: None,
    )
    box_housed = aq._build_inspector(
        aq.App(full=False, size="360x300"),
        housed,
        lambda f: None,
        lambda f: None,
        {},
        lambda f, kind: None,
    )

    labels_awake = [
        c.text for c in box_awake.children if c.__class__.__name__ == "Label"
    ]
    labels_housed = [
        c.text for c in box_housed.children if c.__class__.__name__ == "Label"
    ]

    assert not any("Home tonight" in t for t in labels_awake)
    assert any("Home tonight: Castle" in t for t in labels_housed)


# ── Phase 7: morning vignettes ────────────────────────────────────────────────


def test_choose_morning_vignette_none_with_no_pairs():
    assert aq.choose_morning_vignette([]) is None


def test_choose_morning_vignette_respects_the_chance_gate(monkeypatch):
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(0.0, 0.0)
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)

    assert aq.choose_morning_vignette([(a, b)], chance=0.35) is None


def test_choose_morning_vignette_returns_a_pair_member_and_a_flavor(monkeypatch):
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(0.0, 0.0)
    a.is_sleepy = b.is_sleepy = False  # isolate the non-Sleepy wake/leave path
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)

    result = aq.choose_morning_vignette([(a, b)], chance=0.35)

    assert result is not None
    waker, sleeper, flavor = result
    assert {waker, sleeper} == {a, b}
    assert waker is not sleeper
    assert flavor in ("wake", "leave")


# ── Sleepy ─────────────────────────────────────────────────────────────────────


def test_roll_is_sleepy_respects_the_chance(monkeypatch):
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)
    assert aq.roll_is_sleepy() is True

    monkeypatch.setattr(aq.random, "random", lambda: 0.99)
    assert aq.roll_is_sleepy() is False


def test_is_sleepy_is_independent_of_personality():
    f = _neutral_fish(0.0, 0.0)
    f.personality = "Greedy"
    f.is_sleepy = True  # stacks fine -- not one of PERSONALITIES

    assert f.personality == "Greedy"
    assert f.is_sleepy is True


def test_choose_morning_vignette_sleepy_sleeper_resists_or_leaves_never_wakes(
    monkeypatch,
):
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(0.0, 0.0)
    monkeypatch.setattr(
        aq.random, "random", lambda: 0.0
    )  # fires; sleeper is whichever is_sleepy

    seen = set()
    for _ in range(20):
        a.is_sleepy, b.is_sleepy = True, True  # whichever role either lands in
        waker, sleeper, flavor = aq.choose_morning_vignette([(a, b)], chance=0.35)
        assert sleeper.is_sleepy
        seen.add(flavor)

    assert seen <= {"resist", "leave"}
    assert "wake" not in seen


def test_choose_morning_vignette_non_sleepy_sleeper_never_resists(monkeypatch):
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(0.0, 0.0)
    a.is_sleepy = b.is_sleepy = False
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)

    _waker, _sleeper, flavor = aq.choose_morning_vignette([(a, b)], chance=0.35)

    assert flavor != "resist"


def test_morning_vignette_widget_stays_asleep_when_wakes_is_false():
    v = aq.MorningVignette(10.0, 5.0, "><>", "<><", aq.VIGNETTE_STYLE, wakes=False)
    v._start = time.monotonic() - aq.MORNING_VIGNETTE_FRAME_SECONDS - 0.1

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append(text)
    v.draw(canvas)

    assert any("*...zzz*" in t for t in writes)
    assert not any("*awake*" in t for t in writes)


def test_resist_flavor_fires_a_sleepy_toast_and_a_non_waking_vignette(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    aq.set_relationship(fishes[0], fishes[1], aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    fishes[0].is_sleepy = True
    fishes[1].is_sleepy = True

    fractions = iter([0.9, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # fires; resists

    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()
    second_timer.callback()

    assert any("too sleepy to notice" in t for t in toasts)
    vignettes = [w for w in app.widgets if isinstance(w, aq.MorningVignette)]
    assert len(vignettes) == 1
    assert vignettes[0].wakes is False


def test_inspector_shows_sleepy_tag_only_when_set():
    awake_prone = _neutral_fish(5.0, 5.0)
    awake_prone.is_sleepy = False
    sleepy = _neutral_fish(5.0, 5.0)
    sleepy.is_sleepy = True

    box_plain = aq._build_inspector(
        aq.App(full=False, size="360x300"),
        awake_prone,
        lambda f: None,
        lambda f: None,
        {},
        lambda f, kind: None,
    )
    box_sleepy = aq._build_inspector(
        aq.App(full=False, size="360x300"),
        sleepy,
        lambda f: None,
        lambda f: None,
        {},
        lambda f, kind: None,
    )
    labels_plain = [
        c.text for c in box_plain.children if c.__class__.__name__ == "Label"
    ]
    labels_sleepy = [
        c.text for c in box_sleepy.children if c.__class__.__name__ == "Label"
    ]

    assert not any("Sleepy" in t for t in labels_plain)
    assert any("also Sleepy" in t for t in labels_sleepy)


def test_morning_transition_fires_a_friend_vignette_toast(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    aq.set_relationship(fishes[0], fishes[1], aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    fishes[0].is_sleepy = fishes[1].is_sleepy = False  # isolate the wake/leave path

    fractions = iter([0.9, 0.2])  # Night, then Morning -- a transition
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # always fires

    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()  # Day -> Night, no vignette yet
    second_timer.callback()  # Night -> Morning, vignette fires

    assert any("still asleep" in t for t in toasts)


def test_morning_vignette_widget_shows_boop_then_awake():
    v = aq.MorningVignette(10.0, 5.0, "><>", "<><", aq.VIGNETTE_STYLE)

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append(text)
    v.draw(canvas)
    assert any("*boop*" in t for t in writes)
    assert any("><>" in t and "<><" in t for t in writes)

    v._start = time.monotonic() - aq.MORNING_VIGNETTE_FRAME_SECONDS - 0.1
    writes.clear()
    v.draw(canvas)
    assert any("*awake*" in t for t in writes)


def test_morning_vignette_total_seconds_is_two_frames():
    v = aq.MorningVignette(0.0, 0.0, "a", "b", aq.VIGNETTE_STYLE)
    assert v.total_seconds == aq.MORNING_VIGNETTE_FRAME_SECONDS * 2


def test_wake_flavor_adds_an_in_tank_vignette_that_later_removes_itself(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    aq.set_relationship(fishes[0], fishes[1], aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    fishes[0].is_sleepy = fishes[1].is_sleepy = False  # isolate the wake/leave path

    fractions = iter([0.9, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # fires, flavor "wake"

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()
    second_timer.callback()

    vignettes = [w for w in app.widgets if isinstance(w, aq.MorningVignette)]
    assert len(vignettes) == 1
    vignette = vignettes[0]

    for t in list(app._timers):
        if t.interval is None:
            t.callback()

    assert vignette not in app.widgets


def test_leave_flavor_adds_no_in_tank_vignette(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    aq.set_relationship(fishes[0], fishes[1], aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    # Isolate this test from _assign_dreams(), which also calls
    # random.random() once per hunger-eligible fish right at the Day->Night
    # transition below and would otherwise steal from the stubbed sequence.
    for f in fishes:
        f.hunger = aq.SLEEP_HUNGER_THRESHOLD - 1.0

    fractions = iter([0.9, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    # choose_morning_vignette() calls random.random() twice: the gate check
    # (wants < chance, to fire at all) then the flavor pick (wants >= 0.5,
    # for "leave"). A stateful stub gives each call its own value.
    rolls = iter([0.0, 0.9])
    monkeypatch.setattr(aq.random, "random", lambda: next(rolls))
    # Isolate this test to vignette flavor selection: roll_visitor_donation()
    # also calls random.random() every tick and would otherwise steal from
    # the same stubbed sequence above.
    monkeypatch.setattr(aq, "roll_visitor_donation", lambda *a, **k: 0)

    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()
    second_timer.callback()

    assert any("leaves without them" in t for t in toasts)
    assert not any(isinstance(w, aq.MorningVignette) for w in app.widgets)


def test_visitor_donation_pays_out_immediately_with_a_toast(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    monkeypatch.setattr(aq, "roll_visitor_donation", lambda *a, **k: 7)

    stats = next(
        w
        for w in app.widgets
        if w.__class__.__name__ == "Label" and w.text.startswith("Money: $")
    )
    money_before = int(stats.text.split("$")[1].split()[0])

    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    money_after = int(stats.text.split("$")[1].split()[0])
    assert money_after == money_before + 7
    assert any("A visitor donated $7!" in t for t in toasts)


def test_no_visitor_donation_means_no_toast(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    monkeypatch.setattr(aq, "roll_visitor_donation", lambda *a, **k: 0)

    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert not any("donated" in t for t in toasts)


def test_night_transition_records_slept_together_for_a_shared_container(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    fishes[0].sleeping_in = castle
    fishes[1].sleeping_in = castle
    fishes[0].happiness = fishes[1].happiness = 50.0

    fractions = iter([0.9, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)  # no vignette this run

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()
    second_timer.callback()

    rel = fishes[0].relationships.get(fishes[1])
    assert rel is not None
    assert "Slept together" in rel.memories[-1]
    # Both the "good sleep" (+4, every non-predator fish) and the "friend
    # interaction" (+3, this specific bonding event) gains applied.
    assert fishes[0].happiness > 50.0 + aq.HAPPINESS_GOOD_SLEEP_GAIN
    assert fishes[1].happiness > 50.0 + aq.HAPPINESS_GOOD_SLEEP_GAIN


def test_good_sleep_happiness_applies_to_every_non_predator_fish(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    for i, f in enumerate(fishes):
        f.happiness = 50.0
        f.sleeping_in = None
        # Spread far apart so _check_night_events()'s floor_close proximity
        # check can never independently credit a "slept together" bonding
        # gain -- this test isolates the good-sleep gain alone, not that one.
        f.fx, f.fy = float(i * 40), 0.0

    fractions = iter([0.9, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)  # no vignette this run

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()  # still Night
    second_timer.callback()  # Night -> Morning

    for f in fishes:
        assert f.happiness == pytest.approx(
            50.0 + aq.HAPPINESS_GOOD_SLEEP_GAIN, abs=0.5
        )


def test_night_transition_records_gave_up_home_for_a_homeless_nearby_fish(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    fishes[0].sleeping_in = None
    fishes[1].sleeping_in = castle
    fishes[0].fx, fishes[0].fy = fishes[1].fx, fishes[1].fy  # right next to it

    fractions = iter([0.9, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()
    second_timer.callback()

    rel = fishes[0].relationships.get(fishes[1])
    assert rel is not None
    assert any("slept on the floor" in m for m in rel.memories)


def test_sleepy_fish_stays_held_past_morning_with_an_eligible_tankmate(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    sleepy, friend = fishes[0], fishes[1]
    sleepy.is_sleepy = True
    friend.is_sleepy = False  # must be a genuinely eligible (awake) waker
    sleepy.sleeping_in = castle
    friend.sleeping_in = castle
    aq.set_relationship(sleepy, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD)

    fractions = iter([0.9, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)  # no vignette this run

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()  # still Night
    second_timer.callback()  # Night -> Morning transition

    assert sleepy._holding_asleep is True
    assert sleepy.sleeping_in is castle  # genuinely still asleep, not just cosmetically
    assert sleepy._wake_waker is friend
    assert sleepy._wake_threshold is not None


def test_a_successful_wake_attempt_clears_the_hold_and_records_a_wake_up(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    sleepy, friend = fishes[0], fishes[1]
    sleepy.is_sleepy = True
    friend.is_sleepy = False  # must be a genuinely eligible (awake) waker
    sleepy.sleeping_in = castle
    friend.sleeping_in = castle
    aq.set_relationship(sleepy, friend, aq.RELATIONSHIP_FRIEND_THRESHOLD)
    rel_before = aq.get_relationship(sleepy, friend).score

    fractions = iter([0.9, 0.2, 0.2])  # a third tick to resolve the forced attempt
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    # >= SLEEPY_RESIST_CHANCE, so any real attempt succeeds outright.
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()  # still Night
    second_timer.callback()  # holding begins
    assert sleepy._holding_asleep is True

    sleepy._wake_next_attempt = 0.0  # force the next tick to resolve immediately
    second_timer.callback()

    assert sleepy._holding_asleep is False
    assert aq.get_relationship(sleepy, friend).score > rel_before


def test_a_sleepy_fish_with_no_eligible_tankmate_wakes_via_the_fallback_timeout(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    castle = next(
        w for w in app.widgets if isinstance(w, aq.Decoration) and w.kind == "Castle"
    )
    sleepy = fishes[0]
    sleepy.is_sleepy = True
    sleepy.sleeping_in = castle
    # No other fish shares this container, so no waker is ever assigned.

    fractions = iter([0.9, 0.2, 0.2])  # a third tick to resolve the fallback
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()
    second_timer.callback()  # holding begins, no waker found
    assert sleepy._holding_asleep is True
    assert sleepy._wake_waker is None

    sleepy._held_since = 0.0  # force the fallback to trigger on the next tick
    second_timer.callback()

    assert sleepy._holding_asleep is False


def test_start_menu_has_no_resume_button_by_default():
    from cozy_tui import App

    app = App(full=False, size="400x300")
    box = aq.build_start_menu(
        app, lambda: None, lambda: None, lambda: None, lambda: None
    )
    buttons = [c.text for c in box.children if c.__class__.__name__ == "Button"]

    assert "Resume" not in buttons


def test_start_menu_has_no_achievements_button_by_default():
    from cozy_tui import App

    app = App(full=False, size="400x300")
    box = aq.build_start_menu(
        app, lambda: None, lambda: None, lambda: None, lambda: None
    )
    buttons = [c.text for c in box.children if c.__class__.__name__ == "Button"]

    assert "Achievements" not in buttons


def test_start_menu_achievements_button_invokes_the_callback_when_provided():
    from cozy_tui import App

    app = App(full=False, size="400x300")
    opened = []
    box = aq.build_start_menu(
        app,
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,
        on_achievements=lambda: opened.append(1),
    )
    buttons = [c for c in box.children if c.__class__.__name__ == "Button"]
    achievements_btn = next(b for b in buttons if b.text.strip() == "Achievements")
    achievements_btn.on_mouse_click()

    assert opened == [1]


def test_start_menu_shows_resume_button_when_provided():
    from cozy_tui import App

    app = App(full=False, size="400x300")
    resumed = []
    box = aq.build_start_menu(
        app,
        lambda: None,
        lambda: None,
        lambda: None,
        lambda: None,
        on_resume=lambda: resumed.append(1),
    )
    buttons = [c for c in box.children if c.__class__.__name__ == "Button"]
    resume_btn = next(b for b in buttons if b.text == "Resume")
    resume_btn.on_mouse_click()

    assert resumed == [1]


def test_ctrl_c_returns_to_the_main_menu_and_resume_restores_the_game(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fish_before = [w for w in app.widgets if isinstance(w, aq.Fish)]
    assert fish_before  # the real starter aquarium is running

    app._key_handlers[aq.Key.CTRL_C]()

    assert app._overlays  # the Start Menu is now open
    resume_btn = next(
        c
        for c in app._overlays[-1].widget.children
        if c.__class__.__name__ == "Button" and c.text == "Resume"
    )
    fish_during = [w for w in app.widgets if isinstance(w, aq.Fish)]
    assert fish_during == fish_before  # untouched -- Resume, not New Aquarium

    resume_btn.on_mouse_click()

    assert not app._overlays
    assert [w for w in app.widgets if isinstance(w, aq.Fish)] == fish_before


def test_ctrl_c_then_new_aquarium_actually_resets_the_tank(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fish_before = [w for w in app.widgets if isinstance(w, aq.Fish)]
    # Isolate from an incidental achievement toast (app.toast() is a real,
    # non-modal overlay -- see App.toast() -- that never auto-dismisses in a
    # headless test): the fresh starter fish _seed_starter_aquarium() rolls
    # below could randomly include an Axolotl, unlocking "first_axolotl" and
    # leaving a stray overlay this test isn't about.
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)

    app._key_handlers[aq.Key.CTRL_C]()
    new_btn = next(
        c
        for c in app._overlays[-1].widget.children
        if c.__class__.__name__ == "Button" and c.text == "New Aquarium"
    )
    new_btn.on_mouse_click()

    fish_after = [w for w in app.widgets if isinstance(w, aq.Fish)]
    assert len(fish_after) == len(fish_before)  # a fresh 3 starters
    assert not any(f in fish_after for f in fish_before)  # genuinely new objects
    assert not app._overlays  # New Aquarium also closes the menu


def test_new_aquarium_via_ctrl_c_does_not_break_rendering(tmp_path, monkeypatch):
    # Regression: _clear_tank()'s reset defaults were missing
    # "bubbles_enabled", so BubbleField.draw() (which reads it every
    # frame) crashed with a KeyError the instant anything rendered after
    # a mid-session "New Aquarium" reset.
    app = _headless_app(tmp_path, monkeypatch)

    app._key_handlers[aq.Key.CTRL_C]()
    new_btn = next(
        c
        for c in app._overlays[-1].widget.children
        if c.__class__.__name__ == "Button" and c.text == "New Aquarium"
    )
    new_btn.on_mouse_click()

    app._compose()  # must not raise


# ── Phase 8: Pause menu ────────────────────────────────────────────────────────


def test_fish_freezes_completely_while_paused():
    bounds = (0.0, 0.0, 50.0, 50.0)
    paused = {"value": True}
    f = _neutral_fish(5.0, 5.0, bounds, paused=paused)
    f.vx, f.vy = 3.0, 4.0
    fx_before, fy_before = f.fx, f.fy

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f)
    f.draw(canvas)

    assert (f.fx, f.fy) == (fx_before, fy_before)
    assert (f.vx, f.vy) == (3.0, 4.0)  # velocity untouched too
    assert writes  # still drawn -- frozen, not hidden


def test_paused_fish_stays_hidden_if_already_entered():
    bounds = (0.0, 0.0, 50.0, 50.0)
    paused = {"value": True}
    f = _neutral_fish(5.0, 5.0, bounds, paused=paused)
    f._entered = True

    writes = []
    canvas = _FakeCanvas()
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    _age(f)
    f.draw(canvas)

    assert writes == []


def test_unpausing_does_not_cause_a_dt_jump():
    # _last is kept fresh every frame even while paused, so the first frame
    # after resuming sees a small, normal dt -- not one covering the entire
    # time the game sat paused.
    bounds = (0.0, 0.0, 50.0, 50.0)
    paused = {"value": True}
    f = _neutral_fish(5.0, 5.0, bounds, paused=paused)
    f._next_turn = float("inf")
    f._last = time.monotonic() - 30.0  # as if it's been paused a long time
    f.draw(_FakeCanvas())  # first paused frame refreshes _last

    paused["value"] = False
    fx_before = f.fx
    f.draw(_FakeCanvas())  # first frame after resuming

    # A 30s-old dt would have flung the fish a huge distance; a fresh one
    # barely moves it.
    assert abs(f.fx - fx_before) < 1.0


def test_esc_opens_pause_menu_instead_of_quitting(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers[aq.Key.ESC]()

    assert not app._should_quit
    modal = app._topmost_modal()
    assert modal is not None
    assert modal.widget.title == "Paused"


def test_opening_pause_menu_sets_the_shared_paused_flag(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers[aq.Key.ESC]()

    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    assert fish.paused["value"] is True


def test_resume_button_closes_the_menu_and_unpauses(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers[aq.Key.ESC]()
    box = app._topmost_modal().widget
    resume_btn = next(
        c
        for c in box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Resume"
    )
    resume_btn.on_mouse_click()

    assert app._topmost_modal() is None
    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    assert fish.paused["value"] is False


def test_closing_pause_menu_via_escape_also_unpauses(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers[aq.Key.ESC]()  # open

    modal = app._topmost_modal()
    app._dispatch_input(aq.Key.ESC)  # close via the modal's own Esc-closes

    assert app._topmost_modal() is None
    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    assert fish.paused["value"] is False


def _toggle_auto_pause_off(app):
    app._key_handlers["g"]()
    box = app._topmost_modal().widget
    checkbox = next(
        c
        for c in box.children
        if c.__class__.__name__ == "Checkbox" and "Auto-Pause" in c.text
    )
    checkbox.on_mouse_click()
    close_btn = next(
        c
        for c in box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Close"
    )
    close_btn.on_mouse_click()


def test_opening_shop_pauses_the_game_by_default(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["s"]()

    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    assert fish.paused["value"] is True


def test_closing_shop_unpauses(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["s"]()
    app._dispatch_input(aq.Key.ESC)

    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    assert fish.paused["value"] is False


def test_opening_console_pauses_the_game_by_default(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()

    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    assert fish.paused["value"] is True


def test_closing_console_unpauses(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    app._dispatch_input(aq.Key.ESC)

    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    assert fish.paused["value"] is False


def test_auto_pause_off_keeps_shop_and_console_running_in_background(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    _toggle_auto_pause_off(app)
    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))

    app._key_handlers["s"]()
    assert fish.paused["value"] is False
    app._dispatch_input(aq.Key.ESC)

    app._key_handlers["`"]()
    assert fish.paused["value"] is False
    app._dispatch_input(aq.Key.ESC)


def test_auto_pause_off_also_keeps_the_pause_menu_from_freezing(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _toggle_auto_pause_off(app)
    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))

    app._key_handlers[aq.Key.ESC]()

    assert app._topmost_modal() is not None  # the menu still opens...
    assert fish.paused["value"] is False  # ...it just no longer freezes the tank


def test_settings_opened_from_pause_menu_does_not_unpause_when_settings_closes(
    tmp_path, monkeypatch
):
    # Settings is reachable from inside the Pause menu without closing it
    # first (see build_pause_menu's own Settings button) -- closing the
    # nested Settings overlay alone must not resume the game while Pause is
    # still open underneath it (see aquarium.py's _enter_auto_pause()).
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers[aq.Key.ESC]()  # Pause
    pause_box = app._topmost_modal().widget
    settings_btn = next(
        c
        for c in pause_box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Settings"
    )
    settings_btn.on_mouse_click()  # Settings, stacked on top of Pause

    fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    assert fish.paused["value"] is True

    app._dispatch_input(aq.Key.ESC)  # closes Settings, Pause still open beneath

    assert app._topmost_modal() is not None
    assert app._topmost_modal().widget.title == "Paused"
    assert fish.paused["value"] is True  # still paused -- Pause never closed

    app._dispatch_input(aq.Key.ESC)  # closes Pause too

    assert app._topmost_modal() is None
    assert fish.paused["value"] is False


# ── Achievements ───────────────────────────────────────────────────────────────


def test_achievements_menu_shows_the_unlocked_count():
    from cozy_tui import App

    app = App(full=False, size="600x500")
    box = aq.build_achievements_menu(
        app, aq.ACHIEVEMENTS, {aq.ACHIEVEMENTS[0].id, aq.ACHIEVEMENTS[1].id}
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any(f"2 / {len(aq.ACHIEVEMENTS)} unlocked" in t for t in labels)


def test_achievements_menu_marks_unlocked_entries_with_a_checkmark():
    from cozy_tui import App

    app = App(full=False, size="600x500")
    unlocked_one = aq.ACHIEVEMENTS[0]
    locked_one = aq.ACHIEVEMENTS[1]
    box = aq.build_achievements_menu(app, aq.ACHIEVEMENTS, {unlocked_one.id})
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any(unlocked_one.name in t and "✓" in t for t in labels)
    assert any(
        locked_one.name in t and "✓" not in t for t in labels if locked_one.name in t
    )


def test_achievements_menu_shows_every_entrys_description():
    from cozy_tui import App

    app = App(full=False, size="600x500")
    box = aq.build_achievements_menu(app, aq.ACHIEVEMENTS, set())
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    for achievement in aq.ACHIEVEMENTS:
        assert any(achievement.description in t for t in labels)


def test_pause_menu_achievements_button_opens_the_achievements_menu(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers[aq.Key.ESC]()
    pause_box = app._topmost_modal().widget
    achievements_btn = next(
        c
        for c in pause_box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Achievements"
    )
    achievements_btn.on_mouse_click()

    modal = app._topmost_modal()
    assert modal.widget.title == "Achievements"


def test_start_menu_achievements_button_opens_the_achievements_menu(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers[aq.Key.CTRL_C]()
    start_box = app._topmost_modal().widget
    achievements_btn = next(
        c
        for c in start_box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Achievements"
    )
    achievements_btn.on_mouse_click()

    modal = app._topmost_modal()
    assert modal.widget.title == "Achievements"


def test_quit_button_asks_for_confirmation_first(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers[aq.Key.ESC]()
    box = app._topmost_modal().widget
    quit_btn = next(
        c
        for c in box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Quit"
    )
    quit_btn.on_mouse_click()

    assert not app._should_quit  # not yet -- confirmation still pending
    confirm = app._topmost_modal().widget
    assert "without saving" in confirm.message
    confirm.on_key("y")

    assert app._should_quit


def test_hunger_does_not_advance_while_paused(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers[aq.Key.ESC]()
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    hunger_before = [f.hunger for f in fishes]

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert [f.hunger for f in fishes] == hunger_before


def test_fish_do_not_move_while_paused_through_the_real_app(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers[aq.Key.ESC]()
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    positions_before = [(f.fx, f.fy) for f in fishes]

    for f in fishes:
        f._last = time.monotonic() - 0.5
        f.draw(app)

    assert [(f.fx, f.fy) for f in fishes] == positions_before


# ── Exploration Update Slice 1: biomes, Forest, Wood loop ─────────────────────


def _unlock_forest(app):
    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, "set_money(1000)")
    app.close_overlay(console)
    _open_shop_and_buy(app, "Unlock Forest")


def _second_timer(app):
    return next(t for t in app._timers if t.interval == 1.0)


def test_unlocking_forest_reveals_enter_button_and_removes_shop_row(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    assert not any(
        c.__class__.__name__ == "Button" and c.text.strip() == "Enter Forest"
        for c in app.widgets
    )

    _unlock_forest(app)

    assert any(
        c.__class__.__name__ == "Button" and c.text.strip() == "Enter Forest"
        for c in app.widgets
    )
    app._key_handlers["s"]()
    shop = app._overlays[-1].widget
    assert not any(
        c.__class__.__name__ == "Label" and "Unlock Forest" in c.text
        for c in shop.children
    )


def test_entering_and_leaving_forest_swaps_the_scene_without_losing_fish(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    fish_count = len([w for w in app.widgets if isinstance(w, aq.Fish)])

    enter_btn = next(
        c
        for c in app.widgets
        if c.__class__.__name__ == "Button" and c.text.strip() == "Enter Forest"
    )
    enter_btn.on_mouse_click()

    assert any(
        c.__class__.__name__ == "Button" and c.text.strip() == "Leave Forest"
        for c in app.widgets
    )
    assert not any(
        c.__class__.__name__ == "Button" and c.text.strip() == "Enter Forest"
        for c in app.widgets
    )

    leave_btn = next(
        c
        for c in app.widgets
        if c.__class__.__name__ == "Button" and c.text.strip() == "Leave Forest"
    )
    leave_btn.on_mouse_click()

    assert len([w for w in app.widgets if isinstance(w, aq.Fish)]) == fish_count
    assert any(
        c.__class__.__name__ == "Button" and c.text.strip() == "Enter Forest"
        for c in app.widgets
    )


def test_hungry_fish_travels_to_forest_and_toasts_so_it_is_never_a_silent_vanish(
    tmp_path, monkeypatch
):
    # Regression: a fish leaving for the Forest used to have no toast at
    # all -- easy to mistake for a crash or a shark kill, especially right
    # after the fish narrowly survived one.
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    steve.personality = "Playful"  # baseline departure line, not a flavored one
    steve.hunger = aq.HUNGER_WARNING_THRESHOLD
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # every roll succeeds

    _second_timer(app).callback()

    assert steve not in app.widgets
    assert steve._travel_until is not None
    assert steve._travel_target == "forest"
    assert any("Steve" in t and "forest" in t for t in toasts)
    assert any("looking for food in the forest" in m for m in steve.memory_log)


def test_traveling_fish_is_in_neither_scenes_widget_list(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.personality = "Playful"  # not Shy (opts out) or flavored (Greedy/Explorer)
    steve.hunger = aq.HUNGER_WARNING_THRESHOLD
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)

    _second_timer(app).callback()  # Steve starts traveling
    assert steve not in app.widgets

    enter_btn = next(
        c
        for c in app.widgets
        if c.__class__.__name__ == "Button" and c.text.strip() == "Enter Forest"
    )
    enter_btn.on_mouse_click()
    assert steve not in app.widgets  # still mid-transit, hasn't arrived yet


def test_lost_adventure_fish_actually_appears_in_the_forest(tmp_path, monkeypatch):
    # Regression: _begin_lost_adventure set biome="forest" but never added
    # the fish to forest_widgets, so it stayed invisible in the Forest scene
    # for the entire multi-day trip unless a rare find_shelter/danger event
    # happened to flash it into view.
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, 'start_lost_adventure(fish_name="Steve")')

    assert steve not in app.widgets  # gone from the aquarium

    enter_btn = next(
        c
        for c in app.widgets
        if c.__class__.__name__ == "Button" and c.text.strip() == "Enter Forest"
    )
    enter_btn.on_mouse_click()

    assert steve in app.widgets  # but visible right away in the Forest


def test_lost_adventure_fish_settles_into_a_forest_shelter_at_night(
    tmp_path, monkeypatch
):
    # Regression: a lost-adventure fish never slept anywhere -- night simply
    # left it standing wherever it last was, forever, with no day/night
    # handling at all for a Forest-biome fish.
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, 'start_lost_adventure(fish_name="Steve")')
    app.close_overlay(console)

    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: 0.9)  # -> Night
    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert steve.sleeping_in is not None
    assert steve.sleeping_in.kind in aq.LOST_ADVENTURE_SHELTERS
    assert steve.fx == steve.sleeping_in.fx and steve.fy == steve.sleeping_in.fy
    assert steve._entered is True  # tucked in and invisible, see fish.py's draw()

    # The shelter's own Inspector now shows a real occupant.
    enter_btn = next(
        c
        for c in app.widgets
        if c.__class__.__name__ == "Button" and c.text.strip() == "Enter Forest"
    )
    enter_btn.on_mouse_click()
    shelter = steve.sleeping_in
    app._mouse_handler(aq.MouseClick(shelter.x, shelter.y, 0))
    decoration_box = app._overlays[-1].widget
    labels = [c.text for c in decoration_box.children if c.__class__.__name__ == "Label"]
    assert any("Steve" in t for t in labels)


def test_a_forest_biome_fish_tucked_into_a_shelter_draws_nothing():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(5.0, 5.0, bounds)
    f.biome = "forest"
    f._entered = True

    canvas = _FakeCanvas()
    writes = []
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    f.draw(canvas)

    assert writes == []


def test_a_forest_fish_meeting_bubbles_draws_its_glyph():
    # Regression: adventure.py's BUBBLES_GLYPH was defined but never
    # actually drawn anywhere -- the meet_bubbles event only ever logged a
    # memory line, with nothing to see happening in the Forest.
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(5.0, 5.0, bounds)
    f.biome = "forest"
    f._meeting_bubbles_until = time.monotonic() + 10.0

    canvas = _FakeCanvas()
    writes = []
    canvas.write = lambda x, y, text, style=None: writes.append((x, y, text))
    f.draw(canvas)

    assert any(aq.adventure.BUBBLES_GLYPH in text for _x, _y, text in writes)


def test_meet_bubbles_event_flashes_the_glyph_on_the_real_fish(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, 'start_lost_adventure(fish_name="Steve")')
    app.close_overlay(console)
    monkeypatch.setattr(
        aq.adventure, "pick_event", lambda adv, hunger=None: "meet_bubbles"
    )

    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, 'advance_adventure_day(fish_name="Steve")')

    assert steve._meeting_bubbles_until is not None


def test_a_hungry_lost_adventure_fish_with_wood_trades_with_bubbles_for_food(
    tmp_path, monkeypatch
):
    # Regression: _resolve_lost_adventure_event() never told pick_event()
    # the fish's actual hunger, so a hungry fish carrying wood just kept
    # rolling the plain weighted pool instead of actively seeking Bubbles
    # out to trade for food.
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, 'start_lost_adventure(fish_name="Steve")')
    app.close_overlay(console)

    steve.hunger = aq.LOST_ADVENTURE_HUNGER_SEEK_BUBBLES_THRESHOLD - 1.0
    steve.lost_adventure["has_wood"] = True

    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, 'advance_adventure_day(fish_name="Steve")')

    assert steve.hunger > aq.LOST_ADVENTURE_HUNGER_SEEK_BUBBLES_THRESHOLD - 1.0
    assert steve.lost_adventure["has_wood"] is False
    assert any(aq.adventure.BUBBLES_TRADE_LINE in m for m in steve.memory_log)


def test_lost_adventure_fish_wakes_and_leaves_the_shelter_by_morning(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, 'start_lost_adventure(fish_name="Steve")')
    app.close_overlay(console)

    fractions = iter([0.9, 0.2])  # Day -> Night, then Night -> Morning
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()
    assert steve.sleeping_in is not None

    second_timer.callback()

    assert steve.sleeping_in is None
    assert steve._entered is False


def test_lost_adventure_fish_wanders_the_forest_between_events(tmp_path, monkeypatch):
    # Regression: a lost fish just sat exactly where the last discrete event
    # left it, potentially for a whole in-game day between events -- reading
    # as frozen/broken rather than calm.
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, 'start_lost_adventure(fish_name="Steve")')
    app.close_overlay(console)

    steve._next_turn = 0.0  # force an immediate direction pick
    start_x, start_y = steve.fx, steve.fy

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert (steve.fx, steve.fy) != (start_x, start_y)


def test_forest_shelter_is_clickable_and_opens_an_inspector_without_sell(
    tmp_path, monkeypatch
):
    # Regression: the Forest's mouse handler only ever checked for fish
    # clicks -- clicking the Tree House/Hidden Cave/Dense Plants Thicket
    # did nothing at all, unlike Castle/Rock in the tank.
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    enter_btn = next(
        c
        for c in app.widgets
        if c.__class__.__name__ == "Button" and c.text.strip() == "Enter Forest"
    )
    enter_btn.on_mouse_click()
    tree_house = next(
        w
        for w in app.widgets
        if isinstance(w, aq.Decoration) and w.kind == "Tree House"
    )

    app._mouse_handler(aq.MouseClick(tree_house.x, tree_house.y, 0))

    decoration_box = app._overlays[-1].widget
    assert decoration_box.title == "Tree House"
    # Never bought, never sellable -- no Sell button (see
    # _open_forest_shelter_inspector/_build_decoration_inspector's
    # on_sell=None docs).
    assert not any(
        c.__class__.__name__ == "Button" and c.text.strip() == "Sell"
        for c in decoration_box.children
    )
    assert any(
        c.__class__.__name__ == "Button" and c.text.strip() == "Enter Tree House"
        for c in decoration_box.children
    )


def test_fish_arriving_in_forest_is_positioned_within_the_visible_terminal(
    tmp_path, monkeypatch
):
    # Regression: the Forest used to position fish/wood using fixed
    # FOREST_WIDTH/FOREST_HEIGHT constants regardless of the actual
    # terminal size, so a smaller terminal could place a fish off-screen --
    # invisible even after correctly entering the scene.
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.personality = "Playful"  # not Shy (opts out) or flavored (Greedy/Explorer)
    steve.hunger = aq.HUNGER_WARNING_THRESHOLD
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)
    # No Tiger Shark scaring the fish back out of the forest mid-test.
    monkeypatch.setattr(aq, "TIGER_SHARK_APPEAR_CHANCE_PER_CHECK", 0.0)
    clock = {"t": 1000.0}
    monkeypatch.setattr(aq.time, "monotonic", lambda: clock["t"])

    _second_timer(app).callback()  # starts traveling
    clock["t"] += aq.FOREST_TRAVEL_SECONDS + 0.1
    _second_timer(app).callback()  # arrives in the forest

    assert steve.biome == "forest"
    assert 0.0 <= steve.fx <= float(app.cols)
    assert 0.0 <= steve.fy <= float(app.rows)

    enter_btn = next(
        c
        for c in app.widgets
        if c.__class__.__name__ == "Button" and c.text.strip() == "Enter Forest"
    )
    enter_btn.on_mouse_click()
    assert steve in app.widgets  # actually visible once the scene is entered


def test_forage_is_gated_by_a_minimum_dwell_time_in_the_forest(tmp_path, monkeypatch):
    # Regression: FOREST_FORAGE_CHANCE_PER_CHECK could succeed on the very
    # first per-second check after arrival, so a fish could forage and
    # start heading home again before a player who just clicked "Enter
    # Forest" ever saw it there.
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.personality = "Playful"  # not Shy (opts out) or flavored (Greedy/Explorer)
    steve.hunger = aq.HUNGER_WARNING_THRESHOLD
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # every roll always wins
    # No Tiger Shark scaring the fish back out of the forest mid-test.
    monkeypatch.setattr(aq, "TIGER_SHARK_APPEAR_CHANCE_PER_CHECK", 0.0)
    clock = {"t": 1000.0}
    monkeypatch.setattr(aq.time, "monotonic", lambda: clock["t"])

    _second_timer(app).callback()  # starts traveling
    clock["t"] += aq.FOREST_TRAVEL_SECONDS + 0.1
    _second_timer(app).callback()  # arrives in the forest
    assert steve.carrying is None

    _second_timer(app).callback()  # one more tick, same moment -- still too soon
    assert steve.carrying is None

    clock["t"] += aq.FOREST_MIN_DWELL_SECONDS + 0.1
    _second_timer(app).callback()  # dwell satisfied -- now it can succeed
    assert steve.carrying == "Wood"


def test_fish_forages_wood_and_sells_it_on_returning_home(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    steve.personality = "Playful"  # not Shy (opts out) or flavored (Greedy/Explorer)
    steve.hunger = aq.HUNGER_WARNING_THRESHOLD
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)
    # No Tiger Shark interrupting the forage trip in this happy-path test.
    monkeypatch.setattr(aq, "TIGER_SHARK_APPEAR_CHANCE_PER_CHECK", 0.0)
    clock = {"t": 1000.0}
    monkeypatch.setattr(aq.time, "monotonic", lambda: clock["t"])

    _second_timer(app).callback()  # starts traveling to the forest
    clock["t"] += aq.FOREST_TRAVEL_SECONDS + 0.1
    _second_timer(app).callback()  # arrives in the forest
    clock["t"] += aq.FOREST_MIN_DWELL_SECONDS + 0.1
    _second_timer(app).callback()  # forages successfully, now holding the wood
    assert steve.carrying == "Wood"
    assert steve.biome == "forest"  # lingers with its find before heading home
    assert steve._travel_until is None

    clock["t"] += aq.FOREST_CARRY_LINGER_SECONDS + 0.1
    _second_timer(app).callback()  # done lingering -- heads home
    assert steve._travel_target == "aquarium"

    clock["t"] += aq.FOREST_TRAVEL_SECONDS + 0.1
    _second_timer(app).callback()  # arrives home and sells the wood

    assert steve.carrying is None
    assert steve.biome == "aquarium"
    assert steve in app.widgets
    assert any("Steve brought back a piece of wood" in t for t in toasts)
    assert any("brought back a piece of wood" in m for m in steve.memory_log)


def test_traveling_fish_does_not_break_other_tank_scoped_per_second_checks(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.personality = "Playful"  # not Shy (opts out) or flavored (Greedy/Explorer)
    steve.hunger = aq.HUNGER_WARNING_THRESHOLD
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)

    _second_timer(app).callback()  # Steve is now mid-travel
    assert steve._travel_until is not None

    # Every other per-second check (night events, shark scares, dream
    # assignment, ...) must run without crashing while a fish is mid-
    # transit -- they all guard on _in_tank(f).
    _second_timer(app).callback()


# ── Forest Phase 2: personality-driven forage decisions ───────────────────────


def test_shy_fish_never_rolls_to_forage_on_its_own(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.personality = "Shy"
    steve.hunger = aq.HUNGER_WARNING_THRESHOLD
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # would always win otherwise

    _second_timer(app).callback()

    assert steve._travel_until is None


def test_greedy_fish_forages_at_a_higher_chance_than_baseline(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.personality = "Greedy"
    steve.hunger = aq.HUNGER_WARNING_THRESHOLD
    baseline = aq.FOREST_TRAVEL_CHANCE_PER_CHECK
    boosted = baseline * aq.FOREST_GREEDY_CHANCE_MULT
    roll = (baseline + boosted) / 2  # only wins because of Greedy's multiplier
    monkeypatch.setattr(aq.random, "random", lambda: roll)

    _second_timer(app).callback()

    assert steve._travel_until is not None
    assert any("I'm hungry. I'm going." in m for m in steve.memory_log)


def test_explorer_fish_forages_at_a_higher_chance_than_baseline(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.personality = "Explorer"
    steve.hunger = aq.HUNGER_WARNING_THRESHOLD
    baseline = aq.FOREST_TRAVEL_CHANCE_PER_CHECK
    boosted = baseline * aq.FOREST_EXPLORER_CHANCE_MULT
    roll = (baseline + boosted) / 2
    monkeypatch.setattr(aq.random, "random", lambda: roll)

    _second_timer(app).callback()

    assert steve._travel_until is not None
    assert any("already halfway there" in m for m in steve.memory_log)


def test_hungry_fish_does_not_forage_while_tank_food_is_available(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.personality = "Greedy"
    steve.hunger = aq.HUNGER_WARNING_THRESHOLD
    steve.foods.append(aq.Food(steve.fx, steve.fy))  # already something to eat
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # would always win otherwise

    _second_timer(app).callback()

    assert steve._travel_until is None


def test_friendly_fish_joins_a_friend_already_heading_to_the_forest(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    leader, follower = fishes[0], fishes[1]
    follower.personality = "Friendly"
    follower.hunger = 100.0  # not hungry -- only travels via the friend-join clause
    aq.set_relationship(leader, follower, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    leader.biome = "forest"  # already heading out/there
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)

    _second_timer(app).callback()

    assert follower._travel_until is not None
    assert any("I'll help" in m for m in follower.memory_log)


def test_two_friends_arriving_in_the_forest_get_a_paired_memory_and_toast(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    a, b = fishes[0], fishes[1]
    a.display_name, b.display_name = "Alex", "Steve"
    aq.set_relationship(a, b, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)

    a.biome = "forest"  # already there
    b._travel_until = time.monotonic() - 1.0  # about to arrive
    b._travel_target = "forest"

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert any("I found Alex in the forest" in m for m in b.memory_log)
    assert any("Steve found me in the forest" in m for m in a.memory_log)
    assert any("Steve and Alex are exploring the forest together." in t for t in toasts)


# ── Forest ambience: falling leaves ────────────────────────────────────────────


def test_fall_leaf_moves_down_over_time():
    from examples.aquarium.termquarium.leaves import fall_leaf

    assert fall_leaf(5.0, 2.0, 0.5) == 6.0


def test_leaf_field_spawns_and_removes_leaves_past_the_ground():
    from examples.aquarium.termquarium.leaves import LeafField

    field = LeafField((0.0, 0.0, 20.0, 10.0))
    field._next_spawn = 0.0  # force an immediate spawn

    class _FakeCanvas:
        def write(self, *a, **k):
            pass

    canvas = _FakeCanvas()
    field._last = time.monotonic() - 0.1
    field.draw(canvas)
    assert len(field._leaves) == 1

    # Push the one leaf already past the ground line -- the next draw() drops it.
    field._leaves[0].y = 10.0
    field._next_spawn = 999.0  # don't spawn a replacement this frame
    field._last = time.monotonic() - 0.1
    field.draw(canvas)
    assert field._leaves == []


def test_leaf_field_freezes_while_paused():
    from examples.aquarium.termquarium.leaves import LeafField

    field = LeafField((0.0, 0.0, 20.0, 10.0), paused=lambda: True)
    field._next_spawn = 0.0

    class _FakeCanvas:
        def write(self, *a, **k):
            pass

    field._last = time.monotonic() - 0.1
    field.draw(_FakeCanvas())

    assert field._leaves == []  # never spawns while paused


def test_welcome_back_toast_when_a_hungry_fish_returns_from_the_forest(
    tmp_path, monkeypatch
):
    # Hunger update (updates.md): "returned from the Forest, looks hungry"
    # replaces "while you were away, X died" -- a warm nudge, not a scare.
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.biome = "forest"
    f._travel_until = time.monotonic() - 1.0  # about to arrive home
    f._travel_target = "aquarium"
    f.hunger = aq.HUNGER_WARNING_THRESHOLD - 1  # "Hungry" band
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert f.biome == "aquarium"
    assert any(
        "Welcome back" in t and f.display_name in t and "a little hungry" in t
        for t in toasts
    )


def test_welcome_back_toast_wording_for_a_low_energy_fish(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.biome = "forest"
    f._travel_until = time.monotonic() - 1.0
    f._travel_target = "aquarium"
    f.hunger = aq.HUNGER_LOW_ENERGY_THRESHOLD - 1  # "Low energy" band
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert any(
        "Welcome back" in t and f.display_name in t and "low on energy" in t
        for t in toasts
    )


def test_no_welcome_back_toast_for_a_well_fed_fish_returning_from_the_forest(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.biome = "forest"
    f._travel_until = time.monotonic() - 1.0
    f._travel_target = "aquarium"
    f.hunger = 100.0  # Full
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert not any("Welcome back" in t for t in toasts)


def test_entering_the_forest_with_leaves_enabled_does_not_crash(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    enter_btn = next(
        c
        for c in app.widgets
        if c.__class__.__name__ == "Button" and c.text.strip() == "Enter Forest"
    )
    enter_btn.on_mouse_click()

    leaf_field = next(w for w in app.widgets if w.__class__.__name__ == "LeafField")

    class _FakeCanvas:
        def write(self, *a, **k):
            pass

    leaf_field.draw(_FakeCanvas())  # a real draw() call must not raise


# ── Forest danger: the prowling Tiger Shark ────────────────────────────────────


class _FakeCanvas:
    def write(self, *a, **k):
        pass


def _send_fish_to_forest(app, monkeypatch, clock, f, carry_wood=False):
    """Drive `f` from the tank into the Forest via the real per-second ticks,
    with the Tiger Shark disabled so it never interferes during setup. Leaves
    `f` standing in the Forest -- empty-handed, or (carry_wood=True) holding a
    freshly foraged log and still within its linger window. Every other fish
    is set unhungry so only `f` makes the trip. Callers re-pin
    TIGER_SHARK_APPEAR_CHANCE_PER_CHECK / random afterward to stage the scare."""
    for other in [w for w in app.widgets if isinstance(w, aq.Fish) and w is not f]:
        other.hunger = 100.0
    f.personality = "Playful"  # not Shy (opts out) or flavored (Greedy/Explorer)
    f.hunger = aq.HUNGER_WARNING_THRESHOLD
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)
    monkeypatch.setattr(aq, "TIGER_SHARK_APPEAR_CHANCE_PER_CHECK", 0.0)
    _second_timer(app).callback()  # starts traveling
    clock["t"] += aq.FOREST_TRAVEL_SECONDS + 0.1
    _second_timer(app).callback()  # arrives in the forest
    if carry_wood:
        clock["t"] += aq.FOREST_MIN_DWELL_SECONDS + 0.1
        _second_timer(app).callback()  # forages -> now holding a log, lingering


def _forest_scene(app):
    enter_btn = next(
        c
        for c in app.widgets
        if c.__class__.__name__ == "Button" and c.text.strip() == "Enter Forest"
    )
    enter_btn.on_mouse_click()


def test_a_forest_fish_carrying_wood_draws_a_visible_log():
    from examples.aquarium.termquarium.tank_objects import Wood

    bounds = (0.0, 0.0, 50.0, 50.0)
    species = next(s for s in aq.SHOP_ITEMS if not s.predator)
    f = _make_fish(20.0, 6.0, bounds, [], [], lambda _f: None, lambda _f: None, species)
    f.biome = "forest"
    f.carrying = "Wood"

    class _RecordingCanvas:
        def __init__(self):
            self.writes = []

        def write(self, x, y, text, style=None):
            self.writes.append((x, y, text))

    # Facing right -> the log trails at the tail, on the fish's left.
    f.vx = 1.0
    canvas = _RecordingCanvas()
    f.draw(canvas)
    wood_writes = [(x, y) for (x, y, text) in canvas.writes if text == Wood.GLYPH]
    assert len(wood_writes) == 1
    assert wood_writes[0][0] < f.abs_x  # to the left of the fish glyph

    # Facing left -> the log trails on the fish's right instead.
    f.vx = -1.0
    canvas = _RecordingCanvas()
    f.draw(canvas)
    wood_writes = [x for (x, y, text) in canvas.writes if text == Wood.GLYPH]
    assert wood_writes and wood_writes[0] > f.abs_x

    # An empty-handed fish draws no log.
    f.carrying = None
    canvas = _RecordingCanvas()
    f.draw(canvas)
    assert not any(text == Wood.GLYPH for (x, y, text) in canvas.writes)


def test_tiger_shark_faces_and_swims_in_its_travel_direction():
    from examples.aquarium.termquarium.tank_objects import TigerShark

    right = TigerShark(0.0, 5.0, 6.0)
    assert right._glyph == TigerShark.ART_RIGHT
    right._last = time.monotonic() - 1.0
    right.draw(_FakeCanvas())
    assert right.fx > 0.0  # swam to the right

    left = TigerShark(20.0, 5.0, -6.0)
    assert left._glyph == TigerShark.ART_LEFT
    left._last = time.monotonic() - 1.0
    left.draw(_FakeCanvas())
    assert left.fx < 20.0  # swam to the left


def test_tiger_shark_freezes_while_paused():
    from examples.aquarium.termquarium.tank_objects import TigerShark

    shark = TigerShark(0.0, 5.0, 6.0, paused=lambda: True)
    shark._last = time.monotonic() - 1.0
    shark.draw(_FakeCanvas())
    assert shark.fx == 0.0  # never moved while paused


def test_tiger_shark_never_prowls_an_empty_forest(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    # Nobody hungry -> nobody forages -> the Forest stays empty.
    for f in [w for w in app.widgets if isinstance(w, aq.Fish)]:
        f.hunger = 0.0
    monkeypatch.setattr(aq, "TIGER_SHARK_APPEAR_CHANCE_PER_CHECK", 1.0)  # would spawn
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)

    for _ in range(5):
        _second_timer(app).callback()

    _forest_scene(app)
    assert not any(isinstance(w, aq.TigerShark) for w in app.widgets)


def test_tiger_shark_scares_a_foraging_fish_home_but_it_survives(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    clock = {"t": 1000.0}
    monkeypatch.setattr(aq.time, "monotonic", lambda: clock["t"])
    _send_fish_to_forest(app, monkeypatch, clock, steve)  # empty-handed in the forest
    assert steve.biome == "forest" and steve._travel_until is None

    monkeypatch.setattr(aq, "TIGER_SHARK_APPEAR_CHANCE_PER_CHECK", 1.0)  # guaranteed
    _second_timer(app).callback()  # shark appears, steve flees

    assert steve._travel_target == "aquarium"
    assert steve._travel_until is not None
    assert any("tiger shark" in t.lower() for t in toasts)

    # It never eats -- steve makes it all the way home, alive.
    clock["t"] += aq.FOREST_TRAVEL_SECONDS + 0.1
    monkeypatch.setattr(aq, "TIGER_SHARK_APPEAR_CHANCE_PER_CHECK", 0.0)
    _second_timer(app).callback()
    assert steve.biome == "aquarium"
    assert steve in app.widgets


def test_a_carrying_fish_drops_the_log_when_the_tiger_shark_appears(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    clock = {"t": 1000.0}
    monkeypatch.setattr(aq.time, "monotonic", lambda: clock["t"])
    _send_fish_to_forest(app, monkeypatch, clock, steve, carry_wood=True)
    assert steve.carrying == "Wood" and steve.biome == "forest"

    _forest_scene(app)
    wood_before = sum(1 for w in app.widgets if isinstance(w, aq.Wood))

    # A shark appears. Pin random to a value that spawns it (>= APPEAR is
    # False) but does NOT replenish wood (< WOOD_SPAWN is False), so the only
    # new log this tick is the one Steve drops.
    monkeypatch.setattr(aq, "TIGER_SHARK_APPEAR_CHANCE_PER_CHECK", 1.0)
    monkeypatch.setattr(aq.random, "random", lambda: 0.5)
    _second_timer(app).callback()

    assert steve.carrying is None  # dropped the log
    assert steve._travel_target == "aquarium"  # and bolted home
    wood_after = sum(1 for w in app.widgets if isinstance(w, aq.Wood))
    assert wood_after == wood_before + 1  # the dropped log stays in the forest
    assert any("DROP THE LOG" in t for t in toasts)
    assert any(isinstance(w, aq.TigerShark) for w in app.widgets)


def test_tiger_shark_leaves_after_its_visit(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    clock = {"t": 1000.0}
    monkeypatch.setattr(aq.time, "monotonic", lambda: clock["t"])
    _send_fish_to_forest(app, monkeypatch, clock, steve)

    monkeypatch.setattr(aq, "TIGER_SHARK_APPEAR_CHANCE_PER_CHECK", 1.0)
    _second_timer(app).callback()  # shark appears
    _forest_scene(app)
    assert any(isinstance(w, aq.TigerShark) for w in app.widgets)

    clock["t"] += aq.TIGER_SHARK_STAY_SECONDS + 0.1
    _second_timer(app).callback()  # visit over -- it swims off
    assert not any(isinstance(w, aq.TigerShark) for w in app.widgets)


def test_tiger_shark_will_not_reappear_immediately_after_a_visit_ends(
    tmp_path, monkeypatch
):
    """A busy Forest shouldn't stack visits back-to-back -- see
    TIGER_SHARK_COOLDOWN_SECONDS's own comment for why an unrestrained
    per-second roll made the shark feel like it "always" showed up."""
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    clock = {"t": 1000.0}
    monkeypatch.setattr(aq.time, "monotonic", lambda: clock["t"])
    _send_fish_to_forest(app, monkeypatch, clock, steve)

    monkeypatch.setattr(aq, "TIGER_SHARK_APPEAR_CHANCE_PER_CHECK", 1.0)
    _second_timer(app).callback()  # shark appears
    _forest_scene(app)
    assert any(isinstance(w, aq.TigerShark) for w in app.widgets)

    clock["t"] += aq.TIGER_SHARK_STAY_SECONDS + 0.1
    _second_timer(app).callback()  # visit over -- it swims off
    assert not any(isinstance(w, aq.TigerShark) for w in app.widgets)

    # Steve stays put in the Forest, and the odds are pinned to guaranteed --
    # without the cooldown a shark would reappear on the very next check.
    steve.biome = "forest"
    steve._travel_until = None
    clock["t"] += 1.0
    _second_timer(app).callback()
    assert not any(isinstance(w, aq.TigerShark) for w in app.widgets)

    # Once the cooldown has actually elapsed, a visit can happen again.
    clock["t"] += aq.TIGER_SHARK_COOLDOWN_SECONDS + 0.1
    _second_timer(app).callback()
    assert any(isinstance(w, aq.TigerShark) for w in app.widgets)


def test_two_fish_flee_the_tiger_shark_together_and_both_survive(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    a, b = fishes[0], fishes[1]
    a.display_name, b.display_name = "Alex", "Steve"
    for other in fishes:
        other.hunger = 100.0  # keep everyone else home
    for f in (a, b):
        f.personality = "Playful"
        f.hunger = aq.HUNGER_WARNING_THRESHOLD
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)
    monkeypatch.setattr(aq, "TIGER_SHARK_APPEAR_CHANCE_PER_CHECK", 0.0)
    clock = {"t": 1000.0}
    monkeypatch.setattr(aq.time, "monotonic", lambda: clock["t"])

    _second_timer(app).callback()  # both start traveling
    clock["t"] += aq.FOREST_TRAVEL_SECONDS + 0.1
    _second_timer(app).callback()  # both arrive in the forest
    assert a.biome == "forest" and b.biome == "forest"

    monkeypatch.setattr(aq, "TIGER_SHARK_APPEAR_CHANCE_PER_CHECK", 1.0)
    _second_timer(app).callback()  # shark appears, both flee
    assert a._travel_target == "aquarium" and b._travel_target == "aquarium"
    assert any("both made it back safe" in t for t in toasts)

    # Neither is eaten -- both arrive home.
    clock["t"] += aq.FOREST_TRAVEL_SECONDS + 0.1
    monkeypatch.setattr(aq, "TIGER_SHARK_APPEAR_CHANCE_PER_CHECK", 0.0)
    _second_timer(app).callback()
    assert a.biome == "aquarium" and a in app.widgets
    assert b.biome == "aquarium" and b in app.widgets


def test_entering_the_forest_with_a_tiger_shark_present_does_not_crash(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    clock = {"t": 1000.0}
    monkeypatch.setattr(aq.time, "monotonic", lambda: clock["t"])
    _send_fish_to_forest(app, monkeypatch, clock, steve)
    monkeypatch.setattr(aq, "TIGER_SHARK_APPEAR_CHANCE_PER_CHECK", 1.0)
    _second_timer(app).callback()  # shark appears

    _forest_scene(app)
    shark = next(w for w in app.widgets if isinstance(w, aq.TigerShark))
    shark.draw(_FakeCanvas())  # a real draw() call must not raise


# ── Personality System 2.0 (ROADMAP.md): traits earned through play ─────────


def test_grant_trait_adds_it_and_reports_whether_it_was_new():
    f = _neutral_fish(5.0, 5.0)
    assert f.traits == frozenset()

    assert aq.grant_trait(f, aq.TRAIT_FOOD_LOVER) is True
    assert f.traits == {aq.TRAIT_FOOD_LOVER}

    # Already has it -- no-op, reported as such.
    assert aq.grant_trait(f, aq.TRAIT_FOOD_LOVER) is False
    assert f.traits == {aq.TRAIT_FOOD_LOVER}

    # Traits stack -- a second, different one adds rather than replaces.
    assert aq.grant_trait(f, aq.TRAIT_DREAMER) is True
    assert f.traits == {aq.TRAIT_FOOD_LOVER, aq.TRAIT_DREAMER}


def test_grant_trait_rejects_an_unknown_trait():
    f = _neutral_fish(5.0, 5.0)
    with pytest.raises(ValueError):
        aq.grant_trait(f, "invisible")


def test_fast_swimmer_multiplies_effective_speed():
    f = _neutral_fish(5.0, 5.0)
    f.speed = 4.0
    baseline = f._effective_speed()

    f.traits = frozenset({aq.TRAIT_FAST_SWIMMER})
    assert f._effective_speed() == pytest.approx(baseline * aq.FAST_SWIMMER_SPEED_MULT)


def test_food_lover_gives_a_food_speed_boost():
    bounds = (0.0, 0.0, 50.0, 50.0)

    food_lover = _neutral_fish(5.0, 5.0, bounds)
    food_lover.foods = [aq.Food(30.0, 5.0)]
    food_lover.traits = frozenset({aq.TRAIT_FOOD_LOVER})
    food_lover._next_turn = float("inf")
    food_lover.speed = 5.0
    food_lover.vx, food_lover.vy = 0.0, 0.0

    plain = _neutral_fish(5.0, 5.0, bounds)
    plain.foods = [aq.Food(30.0, 5.0)]
    plain._next_turn = float("inf")
    plain.speed = 5.0
    plain.vx, plain.vy = 0.0, 0.0

    _age(food_lover)
    _age(plain)
    food_lover.draw(_FakeCanvas())
    plain.draw(_FakeCanvas())

    assert food_lover.vx > plain.vx


def test_food_lover_gets_extra_happiness_on_top_of_the_normal_fed_gain():
    bounds = (0.0, 0.0, 50.0, 50.0)
    foods = [aq.Food(5.0, 5.0)]  # exactly at the fish -- guaranteed within EAT_RADIUS
    f = _neutral_fish(5.0, 5.0, bounds, foods=foods)
    f.traits = frozenset({aq.TRAIT_FOOD_LOVER})
    f.happiness = 50.0
    f._next_turn = float("inf")

    _age(f)
    f.draw(_FakeCanvas())

    assert f.happiness == pytest.approx(
        50.0 + aq.HAPPINESS_FED_GAIN + aq.HAPPINESS_FOOD_LOVER_BONUS
    )


def test_predator_never_gets_the_food_lover_happiness_bonus():
    # Sharks don't have Personality System 2.0 traits conceptually, but
    # nothing stops one from carrying a stray .traits value (e.g. a bug
    # elsewhere) -- the bonus is explicitly gated on not-a-predator so that
    # can never silently change a Shark's happiness gain from eating fish.
    bounds = (0.0, 0.0, 50.0, 50.0)
    fish_list = []
    # Exactly at the shark's own position -- guaranteed within EAT_RADIUS,
    # same trick test_eating_regular_food_gives_the_fed_happiness_gain uses
    # for food, so a single draw() call is a guaranteed catch.
    prey = _neutral_fish(5.0, 5.0, bounds, fish_list=fish_list)
    fish_list.append(prey)
    shark = _neutral_fish(5.0, 5.0, bounds, fish_list=fish_list, is_predator=True)
    shark.traits = frozenset({aq.TRAIT_FOOD_LOVER})
    shark.happiness = 50.0
    shark._next_turn = float("inf")

    _age(shark)
    shark.draw(_FakeCanvas())

    assert shark.happiness == 50.0 + aq.HAPPINESS_FED_GAIN


def test_dreamer_trait_leans_the_existing_dream_chance_not_a_separate_roll(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    for f in fishes:
        f.hunger = 100.0
    dreamer, plain = fishes[0], fishes[1]
    dreamer.traits = frozenset({aq.TRAIT_DREAMER})
    _force_night_transition(monkeypatch)
    # Between DREAM_CHANCE and DREAM_CHANCE + DREAMER_DREAM_CHANCE_BONUS --
    # misses for a plain fish, hits for a Dreamer leaning the same roll.
    roll = (aq.DREAM_CHANCE + aq.DREAM_CHANCE + aq.DREAMER_DREAM_CHANCE_BONUS) / 2
    monkeypatch.setattr(aq.random, "random", lambda: roll)

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert dreamer.dream is not None
    assert plain.dream is None


def test_dreaming_can_grow_the_dreamer_trait(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    for f in fishes:
        f.hunger = 100.0
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    _force_night_transition(monkeypatch)
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # always dreams, always grows

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert all(aq.TRAIT_DREAMER in f.traits for f in fishes)
    assert any(
        "developed a new trait" in entry for f in fishes for entry in f.memory_log
    )


def test_a_shark_scare_can_grow_the_fast_swimmer_trait(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    prey = next(w for w in app.widgets if isinstance(w, aq.Fish))
    prey.decorations = []
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # always grows
    _add_real_fish(app, prey.fx + 1.0, prey.fy, is_predator=True, species_name="Shark")

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert aq.TRAIT_FAST_SWIMMER in prey.traits


def test_a_shark_scare_does_not_regrant_fast_swimmer_or_re_toast(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    prey = next(w for w in app.widgets if isinstance(w, aq.Fish))
    prey.display_name = "Steve"
    prey.decorations = []
    prey.traits = frozenset({aq.TRAIT_FAST_SWIMMER})
    # The other starter fish spawn at random positions -- push them well
    # outside SHARK_SCARE_RADIUS so only Steve is ever scared by the shark
    # placed below; otherwise one of them can, entirely correctly, earn its
    # own Fast Swimmer this same tick and pollute the toast-text assertion.
    for other in [w for w in app.widgets if isinstance(w, aq.Fish) and w is not prey]:
        other.fx, other.fy = -1000.0, -1000.0
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)
    _add_real_fish(app, prey.fx + 1.0, prey.fy, is_predator=True, species_name="Shark")

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert prey.traits == {aq.TRAIT_FAST_SWIMMER}
    assert not any(f"{prey.display_name} developed a new trait" in t for t in toasts)


def test_console_grant_trait_command(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, 'grant_trait(fish_name="Steve", trait="food_lover")')

    assert aq.TRAIT_FOOD_LOVER in steve.traits


def test_console_grant_trait_reports_when_already_held(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    steve.traits = frozenset({aq.TRAIT_DREAMER})
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, 'grant_trait(fish_name="Steve", trait="dreamer")')

    assert any("already has that trait" in text for text, _is_error in console.lines)


def test_console_grant_trait_rejects_an_unknown_trait(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, 'grant_trait(fish_name="Steve", trait="invisible")')

    assert steve.traits == frozenset()


def test_save_then_load_round_trip_preserves_traits(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    steve.traits = frozenset({aq.TRAIT_FOOD_LOVER, aq.TRAIT_FAST_SWIMMER})

    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = "Trait Save"
    prompt.on_key(aq.Key.ENTER)

    app._key_handlers["l"]()
    load_box = app._overlays[-1].widget
    load_btn = next(
        c
        for c in load_box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Load"
    )
    load_btn.on_mouse_click()

    reloaded = next(f for f in app.widgets if isinstance(f, aq.Fish))
    assert reloaded.display_name == "Steve"
    assert reloaded.traits == {aq.TRAIT_FOOD_LOVER, aq.TRAIT_FAST_SWIMMER}


def test_loading_a_save_from_before_traits_existed_defaults_to_no_traits(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"

    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = "Old Save"
    prompt.on_key(aq.Key.ENTER)

    path = tmp_path / ".termquarium" / "saves" / "Old Save.json"
    data = json.loads(path.read_text())
    del data["aquarium"]["fish"][0]["traits"]  # simulate a pre-2.0 save
    path.write_text(json.dumps(data))

    app._key_handlers["l"]()
    load_box = app._overlays[-1].widget
    load_btn = next(
        c
        for c in load_box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Load"
    )
    load_btn.on_mouse_click()

    reloaded = next(f for f in app.widgets if isinstance(f, aq.Fish))
    assert reloaded.traits == frozenset()


def test_inspector_shows_earned_traits_on_the_personality_line(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.traits = frozenset({aq.TRAIT_FOOD_LOVER})

    inspector = _open_inspector_for(app, steve)
    line = next(
        w.text
        for w in inspector.children
        if w.__class__.__name__ == "Label" and w.text.startswith("Personality:")
    )

    assert "Food Lover" in line
    assert "🍤" in line


def test_inspector_personality_line_unchanged_with_no_traits(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    assert steve.traits == frozenset()

    inspector = _open_inspector_for(app, steve)
    line = next(
        w.text
        for w in inspector.children
        if w.__class__.__name__ == "Label" and w.text.startswith("Personality:")
    )

    assert "·" not in line


# ── Personality System 2.0, part 2: Energetic / Mischievous / Keen Explorer ──


def test_energetic_reduces_the_turn_delay_range():
    f = _neutral_fish(5.0, 5.0)
    f.personality = "Explorer"  # a plain baseline turn-rate to compare against
    f._next_turn = 0.0  # already due
    _age(f, 1.0)
    baseline_delay = None
    f.draw(_FakeCanvas())
    baseline_delay = f._next_turn - f._last

    f.traits = frozenset({aq.TRAIT_ENERGETIC})
    f._next_turn = 0.0
    _age(f, 1.0)
    f.draw(_FakeCanvas())
    energetic_delay = f._next_turn - f._last

    # Both delays are randomized within a range, so compare the ranges'
    # upper bounds rather than one sampled draw.
    assert aq.MAX_TURN_DELAY / aq.EXPLORER_TURN_DIV / aq.ENERGETIC_TURN_DIV < (
        aq.MAX_TURN_DELAY / aq.EXPLORER_TURN_DIV
    )
    assert (
        energetic_delay
        <= aq.MAX_TURN_DELAY / aq.EXPLORER_TURN_DIV / aq.ENERGETIC_TURN_DIV
    )
    assert baseline_delay <= aq.MAX_TURN_DELAY / aq.EXPLORER_TURN_DIV


def test_showing_off_event_can_grow_the_energetic_trait(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    target_fish = next(w for w in app.widgets if isinstance(w, aq.Fish))
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # event fires, roll succeeds
    monkeypatch.setattr(
        aq.random,
        "choice",
        lambda seq: "showing_off" if "showing_off" in seq else target_fish,
    )

    daily_timer = next(t for t in app._timers if t.interval == aq.AGE_SECONDS_PER_DAY)
    daily_timer.callback()

    assert aq.TRAIT_ENERGETIC in target_fish.traits


def test_closer_rival_for_finds_the_nearest_closer_tankmate():
    bounds = (0.0, 0.0, 50.0, 50.0)
    fish_list = []
    thief = _neutral_fish(0.0, 0.0, bounds, fish_list=fish_list)
    far_rival = _neutral_fish(9.0, 0.0, bounds, fish_list=fish_list)
    near_rival = _neutral_fish(9.5, 0.0, bounds, fish_list=fish_list)
    fish_list.extend([thief, far_rival, near_rival])

    closest = thief._closer_rival_for((10.0, 0.0))
    assert closest is near_rival


def test_closer_rival_for_ignores_predators_and_fish_that_are_not_actually_closer():
    bounds = (0.0, 0.0, 50.0, 50.0)
    fish_list = []
    thief = _neutral_fish(9.0, 0.0, bounds, fish_list=fish_list)
    farther = _neutral_fish(0.0, 0.0, bounds, fish_list=fish_list)  # farther than thief
    shark = _neutral_fish(9.9, 0.0, bounds, fish_list=fish_list, is_predator=True)
    fish_list.extend([thief, farther, shark])

    assert thief._closer_rival_for((10.0, 0.0)) is None


def test_mischievous_gives_a_food_speed_boost():
    bounds = (0.0, 0.0, 50.0, 50.0)

    mischievous = _neutral_fish(5.0, 5.0, bounds)
    mischievous.foods = [aq.Food(30.0, 5.0)]
    mischievous.traits = frozenset({aq.TRAIT_MISCHIEVOUS})
    mischievous._next_turn = float("inf")
    mischievous.speed = 5.0
    mischievous.vx, mischievous.vy = 0.0, 0.0

    plain = _neutral_fish(5.0, 5.0, bounds)
    plain.foods = [aq.Food(30.0, 5.0)]
    plain._next_turn = float("inf")
    plain.speed = 5.0
    plain.vx, plain.vy = 0.0, 0.0

    _age(mischievous)
    _age(plain)
    mischievous.draw(_FakeCanvas())
    plain.draw(_FakeCanvas())

    assert mischievous.vx > plain.vx


def test_eating_food_a_closer_tankmate_wanted_sets_stole_food_from():
    bounds = (0.0, 0.0, 50.0, 50.0)
    fish_list = []
    # thief is 0.5 from the food (within EAT_RADIUS -- a guaranteed catch,
    # not distance 0: that would make "someone closer than me" impossible
    # for anyone to satisfy) and victim is 0.1 from it -- genuinely closer.
    thief = _neutral_fish(5.0, 5.0, bounds, fish_list=fish_list)
    victim = _neutral_fish(5.6, 5.0, bounds, fish_list=fish_list)
    fish_list.extend([thief, victim])
    thief.foods = [aq.Food(5.5, 5.0)]
    thief._next_turn = float("inf")

    _age(thief)
    thief.draw(_FakeCanvas())

    assert thief._stole_food_from is victim


def test_a_steal_can_grow_mischievous_and_dents_the_relationship(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    thief, victim = [w for w in app.widgets if isinstance(w, aq.Fish)][:2]
    # Neither Lazy -- remember() dampens the delta toward 0 for a Lazy fish
    # on either side, which would make the exact-value assertion below flaky
    # against whatever personality got randomly rolled.
    thief.personality = "Explorer"
    victim.personality = "Explorer"
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    thief._stole_food_from = victim
    before = aq.get_relationship(thief, victim).score
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # growth roll always succeeds

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()

    assert aq.TRAIT_MISCHIEVOUS in thief.traits
    assert thief._stole_food_from is None  # consumed, not reprocessed every tick
    after = aq.get_relationship(thief, victim).score
    assert after == pytest.approx(before + aq.MISCHIEVOUS_STEAL_RELATIONSHIP_PENALTY)
    assert any(
        "snagged food" in reason
        for reason in aq.get_relationship(thief, victim).memories
    )


def _return_from_forage_with_wood(app, monkeypatch, f):
    """Drive `f` all the way from a successful forage through arriving home
    with wood, via the real per-second ticks -- same sequence
    test_fish_forages_wood_and_sells_it_on_returning_home uses."""
    clock = {"t": 1000.0}
    monkeypatch.setattr(aq.time, "monotonic", lambda: clock["t"])
    _send_fish_to_forest(app, monkeypatch, clock, f, carry_wood=True)
    clock["t"] += aq.FOREST_CARRY_LINGER_SECONDS + 0.1
    _second_timer(app).callback()  # done lingering -- heads home
    clock["t"] += aq.FOREST_TRAVEL_SECONDS + 0.1
    _second_timer(app).callback()  # arrives home and sells


def test_forage_return_can_grow_the_keen_explorer_trait(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    _return_from_forage_with_wood(app, monkeypatch, steve)

    assert aq.TRAIT_KEEN_EXPLORER in steve.traits


def test_keen_explorer_can_bring_back_a_crystal_log(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    steve.traits = frozenset({aq.TRAIT_KEEN_EXPLORER})
    state_money_before = app.widgets  # placeholder, real check is via toast below
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    _return_from_forage_with_wood(app, monkeypatch, steve)

    assert any(
        f"Crystal Log! Sold for ${aq.CRYSTAL_LOG_SELL_PRICE}" in t for t in toasts
    )
    assert any("Crystal Log" in m for m in steve.memory_log)


def test_keen_explorer_needs_a_friend_for_a_giant_log(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    steve = fishes[0]
    steve.display_name = "Steve"
    steve.traits = frozenset({aq.TRAIT_KEEN_EXPLORER})
    assert steve.friend is None  # a fresh starter aquarium hasn't earned any bonds yet
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    _return_from_forage_with_wood(app, monkeypatch, steve)

    # No Friend to help carry -- always a Crystal Log, never a Giant Log,
    # even though the rare-find roll itself (pinned to 0.0 by
    # _send_fish_to_forest) always succeeds.
    assert any("Crystal Log" in t for t in toasts)
    assert not any("Giant Log" in t for t in toasts)


def test_keen_explorer_with_a_friend_can_bring_back_a_giant_log(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    steve, kitty = fishes[0], fishes[1]
    steve.display_name = "Steve"
    kitty.display_name = "Kitty"
    # Not Lazy -- remember() dampens the relationship delta for a Lazy fish
    # on either side, which would make the exact-value assertion below
    # flaky against Kitty's randomly-rolled personality (Steve's own gets
    # forced to "Playful" by _send_fish_to_forest() regardless).
    kitty.personality = "Explorer"
    steve.traits = frozenset({aq.TRAIT_KEEN_EXPLORER})
    aq.set_relationship(steve, kitty, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    assert steve.friend is kitty
    before = aq.get_relationship(steve, kitty).score
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))

    _return_from_forage_with_wood(app, monkeypatch, steve)

    assert any(
        f"Giant Log home together! Sold for ${aq.GIANT_LOG_SELL_PRICE}" in t
        for t in toasts
    )
    assert any("carried a Giant Log with Kitty" in m for m in steve.memory_log)
    assert any("Helped Steve carry a Giant Log" in m for m in kitty.memory_log)
    after = aq.get_relationship(steve, kitty).score
    assert after == pytest.approx(
        min(aq.RELATIONSHIP_MAX, before + aq.GIANT_LOG_RELATIONSHIP_BONUS)
    )


# ── Personality System 2.0, part 3: combo flavor / Keen Explorer eagerness ──


def test_keen_explorer_forages_at_a_higher_chance_than_baseline(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    clock = {"t": 1000.0}
    monkeypatch.setattr(aq.time, "monotonic", lambda: clock["t"])
    _unlock_forest(app)
    # Past the fresh-unlock urgency window -- isolates the *settled*
    # KEEN_EXPLORER_FOREST_CHANCE_MULT boost from the much stronger
    # "just unlocked, explore ASAP" spike (see the next two tests).
    clock["t"] += aq.KEEN_EXPLORER_URGENCY_DECAY_SECONDS + 0.1
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.personality = "Lazy"  # would not otherwise get any forage-chance boost
    steve.traits = frozenset({aq.TRAIT_KEEN_EXPLORER})
    steve.hunger = aq.HUNGER_WARNING_THRESHOLD
    baseline = aq.FOREST_TRAVEL_CHANCE_PER_CHECK
    boosted = baseline * aq.KEEN_EXPLORER_FOREST_CHANCE_MULT
    roll = (baseline + boosted) / 2  # only wins because of the trait's multiplier
    monkeypatch.setattr(aq.random, "random", lambda: roll)

    _second_timer(app).callback()

    assert steve._travel_until is not None


def test_keen_explorer_explores_almost_immediately_when_freshly_unlocked(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    clock = {"t": 1000.0}
    monkeypatch.setattr(aq.time, "monotonic", lambda: clock["t"])
    _unlock_forest(app)  # forest_unlocked_at["t"] == 1000.0 (just now)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.personality = "Lazy"
    steve.traits = frozenset({aq.TRAIT_KEEN_EXPLORER})
    steve.hunger = aq.HUNGER_WARNING_THRESHOLD
    # Well above the *settled* boost but comfortably below
    # KEEN_EXPLORER_FRESH_CHANCE -- only wins via the fresh-unlock spike.
    roll = (
        aq.FOREST_TRAVEL_CHANCE_PER_CHECK * aq.KEEN_EXPLORER_FOREST_CHANCE_MULT
        + aq.KEEN_EXPLORER_FRESH_CHANCE
    ) / 2
    monkeypatch.setattr(aq.random, "random", lambda: roll)

    _second_timer(app).callback()

    assert steve._travel_until is not None


def test_keen_explorer_urgency_decays_back_to_the_settled_boost(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    clock = {"t": 1000.0}
    monkeypatch.setattr(aq.time, "monotonic", lambda: clock["t"])
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.personality = "Lazy"
    steve.traits = frozenset({aq.TRAIT_KEEN_EXPLORER})
    steve.hunger = aq.HUNGER_WARNING_THRESHOLD
    # Same roll used for the "fresh" test above -- wins right after unlock,
    # but shouldn't still win once the urgency window has fully decayed.
    roll = (
        aq.FOREST_TRAVEL_CHANCE_PER_CHECK * aq.KEEN_EXPLORER_FOREST_CHANCE_MULT
        + aq.KEEN_EXPLORER_FRESH_CHANCE
    ) / 2
    monkeypatch.setattr(aq.random, "random", lambda: roll)
    clock["t"] += aq.KEEN_EXPLORER_URGENCY_DECAY_SECONDS + 0.1

    _second_timer(app).callback()

    assert steve._travel_until is None


def test_keen_explorer_stacks_with_explorer_personality():
    from examples.aquarium.termquarium import constants as c

    stacked = (
        c.FOREST_TRAVEL_CHANCE_PER_CHECK
        * c.FOREST_EXPLORER_CHANCE_MULT
        * c.KEEN_EXPLORER_FOREST_CHANCE_MULT
    )
    assert stacked > c.FOREST_TRAVEL_CHANCE_PER_CHECK * c.FOREST_EXPLORER_CHANCE_MULT


def test_combo_flavor_explorer_personality_plus_dreamer_trait():
    from examples.aquarium.termquarium.inspectors import _combo_flavor_text

    f = _neutral_fish(5.0, 5.0)
    f.personality = "Explorer"
    f.traits = frozenset({aq.TRAIT_DREAMER})
    assert (
        _combo_flavor_text(f)
        == "A fish that dreams about places it has never visited."
    )


def test_combo_flavor_food_lover_plus_mischievous_traits():
    from examples.aquarium.termquarium.inspectors import _combo_flavor_text

    f = _neutral_fish(5.0, 5.0)
    f.traits = frozenset({aq.TRAIT_FOOD_LOVER, aq.TRAIT_MISCHIEVOUS})
    assert "steals everyone else's" in _combo_flavor_text(f)


def test_combo_flavor_friendly_personality_plus_mischievous_trait():
    from examples.aquarium.termquarium.inspectors import _combo_flavor_text

    f = _neutral_fish(5.0, 5.0)
    f.personality = "Friendly"
    f.traits = frozenset({aq.TRAIT_MISCHIEVOUS})
    assert "pranks" in _combo_flavor_text(f)


def test_combo_flavor_energetic_plus_dreamer_traits():
    from examples.aquarium.termquarium.inspectors import _combo_flavor_text

    f = _neutral_fish(5.0, 5.0)
    f.personality = "Lazy"  # not Explorer/Friendly -- isolates the trait-pair check
    f.traits = frozenset({aq.TRAIT_ENERGETIC, aq.TRAIT_DREAMER})
    assert (
        _combo_flavor_text(f)
        == "Very active during the day. Very imaginative at night."
    )


def test_combo_flavor_none_when_nothing_matches():
    from examples.aquarium.termquarium.inspectors import _combo_flavor_text

    f = _neutral_fish(5.0, 5.0)
    f.personality = "Lazy"
    f.traits = frozenset({aq.TRAIT_FAST_SWIMMER})
    assert _combo_flavor_text(f) is None


def test_inspector_shows_combo_flavor_text_when_it_matches(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.personality = "Explorer"
    steve.traits = frozenset({aq.TRAIT_DREAMER})

    inspector = _open_inspector_for(app, steve)
    line = next(
        w.text
        for w in inspector.children
        if w.__class__.__name__ == "Label" and w.text.startswith("Personality:")
    )

    assert "dreams about places it has never visited" in line


def test_inspector_omits_combo_flavor_text_when_nothing_matches(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.personality = "Lazy"
    steve.traits = frozenset()

    inspector = _open_inspector_for(app, steve)
    line = next(
        w.text
        for w in inspector.children
        if w.__class__.__name__ == "Label" and w.text.startswith("Personality:")
    )

    assert "—" not in line


# ── Save/load: day/night phase and in-progress dreams (real gaps, fixed) ────


def _load_the_one_save(app, tmp_path):
    app._key_handlers["l"]()
    load_box = app._overlays[-1].widget
    load_btn = next(
        c
        for c in load_box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Load"
    )
    load_btn.on_mouse_click()


def test_save_then_load_round_trip_preserves_day_night_phase(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["`"]()
    console = app._overlays[-1].widget
    _type_into_console(console, 'set_time("night")')
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    assert steve.environment["phase"] == "Night"

    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = "Night Save"
    prompt.on_key(aq.Key.ENTER)

    _load_the_one_save(app, tmp_path)

    reloaded = next(f for f in app.widgets if isinstance(f, aq.Fish))
    assert reloaded.environment["phase"] == "Night"


def test_loading_a_save_from_before_day_fraction_existed_defaults_to_midday(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = "Old Day Save"
    prompt.on_key(aq.Key.ENTER)

    path = tmp_path / ".termquarium" / "saves" / "Old Day Save.json"
    data = json.loads(path.read_text())
    del data["aquarium"]["day_fraction"]  # simulate a pre-existing save
    path.write_text(json.dumps(data))

    _load_the_one_save(app, tmp_path)

    reloaded = next(f for f in app.widgets if isinstance(f, aq.Fish))
    assert reloaded.environment["phase"] == "Day"  # fraction 0.5 -- unchanged default


def test_save_then_load_round_trip_preserves_an_in_progress_dream(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    steve.dream = aq.make_dream(steve, "happy", variant_title="Endless Bubbles")
    original = steve.dream

    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = "Dream Save"
    prompt.on_key(aq.Key.ENTER)

    _load_the_one_save(app, tmp_path)

    reloaded = next(f for f in app.widgets if isinstance(f, aq.Fish))
    assert reloaded.dream is not None
    assert reloaded.dream.category == original.category
    assert reloaded.dream.title == original.title
    assert reloaded.dream.description == original.description
    assert reloaded.dream.frames == original.frames


def test_save_then_load_round_trip_preserves_no_dream(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    assert steve.dream is None

    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = "No Dream Save"
    prompt.on_key(aq.Key.ENTER)

    _load_the_one_save(app, tmp_path)

    reloaded = next(f for f in app.widgets if isinstance(f, aq.Fish))
    assert reloaded.dream is None


def test_loading_a_save_from_before_dreams_persisted_defaults_to_no_dream(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    app._key_handlers["p"]()
    prompt = app._overlays[-1].widget
    prompt.text = "Old Dream Save"
    prompt.on_key(aq.Key.ENTER)

    path = tmp_path / ".termquarium" / "saves" / "Old Dream Save.json"
    data = json.loads(path.read_text())
    del data["aquarium"]["fish"][0]["dream"]  # simulate a pre-existing save
    path.write_text(json.dumps(data))

    _load_the_one_save(app, tmp_path)

    reloaded = next(f for f in app.widgets if isinstance(f, aq.Fish))
    assert reloaded.dream is None
