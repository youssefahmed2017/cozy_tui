"""Pure logic tests for the Aquarium example (examples/aquarium/aquarium.py),
Step 1: the steer() wall-bounce/movement function. Mirrors
tests/test_game_2048.py's importlib-load pattern -- no Widget/App involved."""

import importlib.util
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


def test_decay_hunger_increments_hunger_below_max():
    hunger, health = aq.decay_hunger(0.0, 100.0)
    assert hunger == aq.HUNGER_STEP
    assert health == 100.0


def test_decay_hunger_caps_at_one_hundred():
    hunger, health = aq.decay_hunger(99.0, 100.0)
    assert hunger == 100.0


def test_decay_hunger_drains_health_once_starving():
    hunger, health = aq.decay_hunger(100.0, 100.0)
    assert hunger == 100.0
    assert health == 100.0 - aq.STARVE_HEALTH_LOSS


def test_decay_hunger_health_does_not_go_negative():
    hunger, health = aq.decay_hunger(100.0, 2.0)
    assert health == 0.0


def test_feed_relieves_hunger_and_restores_health():
    hunger, health = aq.feed(80.0, 50.0)
    assert hunger == 80.0 - aq.HUNGER_RELIEF
    assert health == 50.0 + aq.HEALTH_GAIN


def test_feed_clamps_hunger_and_health_to_bounds():
    hunger, health = aq.feed(10.0, 98.0)
    assert hunger == 0.0
    assert health == 100.0


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
    shark.hunger = 80.0
    shark.health = 50.0

    class _FakeCanvas:
        def write(self, *a, **k):
            pass

    shark.draw(_FakeCanvas())

    assert prey not in fish_list
    assert eaten == [prey]
    assert shark.hunger == 80.0 - aq.HUNGER_RELIEF
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
    return f


def test_fish_at_finds_a_fish_on_its_row_within_its_glyph_width():
    f = _neutral_fish(5.0, 5.0)
    f.birth_time -= (
        aq.AGE_SECONDS_PER_DAY * 5
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
    assert "Hunger 42%" in text


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
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 5  # past Baby

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
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 5
    assert f.growth_stage == "Adult"
    f.vx = 1.0
    assert f._glyph() == "><>"


def test_fish_sell_value_scales_with_growth_stage():
    f = _neutral_fish(5.0, 5.0)
    f.price = 100
    assert f.growth_stage == "Baby"
    assert f.sell_value == 25
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 1.5
    assert f.growth_stage == "Juvenile"
    assert f.sell_value == 60
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 5
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
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 11
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
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 11
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
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 5
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

    second_timer = next(t for t in app._timers if t.interval == 1.0)
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
    a.birth_time -= aq.AGE_SECONDS_PER_DAY * 5
    b.birth_time -= aq.AGE_SECONDS_PER_DAY * 5
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
    a.birth_time -= aq.AGE_SECONDS_PER_DAY * 5
    b.birth_time -= aq.AGE_SECONDS_PER_DAY * 5
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
        f.hunger = 10.0
    _force_random_event(monkeypatch, "storm")

    _fire_daily_tick(app)

    assert any("storm" in t.lower() for t in toasts)
    assert all(f.hunger == pytest.approx(10.0 + aq.STORM_HUNGER_BUMP) for f in fishes)


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
    hungry.hunger = aq.SLEEP_HUNGER_THRESHOLD + 10.0  # too hungry to actually sleep
    sleepy_ready.hunger = 0.0
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
        f.hunger = 0.0
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
        f.birth_time -= aq.AGE_SECONDS_PER_DAY * 5  # grown up
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


def test_shark_scare_with_a_nearby_friend_credits_a_rescuer(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    prey, rescuer = fishes[0], fishes[1]
    prey.decorations = []  # no container to hide in -- isolates the rescue path
    prey.fx, prey.fy = 10.0, 10.0
    rescuer.fx, rescuer.fy = 10.0, 6.0  # within SHARK_RESCUE_RADIUS, not SCARE_RADIUS
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
    prey.hunger = 0.0
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


def test_dream_assignment_logs_a_dream_summary_memory(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    for f in fishes:
        f.hunger = 0.0
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
        f.hunger = 0.0
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


def test_arriving_beside_the_friend_triggers_a_comfort_flash_and_memory(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    dreamer, friend = fishes[0], fishes[1]
    aq.set_relationship(dreamer, friend, aq.RELATIONSHIP_BEST_FRIEND_THRESHOLD)
    dreamer._seeking_friend_after_nightmare = True
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


# ── Aging: Elder stage + natural death ──────────────────────────────────────


def test_reaching_elder_unlocks_the_achievement_and_logs_it_once(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    f = next(w for w in app.widgets if isinstance(w, aq.Fish))
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 11
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
    elder.birth_time -= aq.AGE_SECONDS_PER_DAY * 11
    monkeypatch.setattr(aq.random, "random", lambda: 0.0)  # always within the chance

    _fire_daily_tick(app)

    assert elder not in [w for w in app.widgets if isinstance(w, aq.Fish)]
    assert young in [w for w in app.widgets if isinstance(w, aq.Fish)]


def test_natural_death_logs_departure_and_cause_and_toasts(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    elder, friend = fishes[0], fishes[1]
    elder.birth_time -= aq.AGE_SECONDS_PER_DAY * 11
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


def test_give_nightmare_command_scares_the_fish(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    steve = next(w for w in app.widgets if isinstance(w, aq.Fish))
    steve.display_name = "Steve"
    app._key_handlers["`"]()
    console = app._overlays[-1].widget

    _type_into_console(console, 'give_nightmare("Steve")')

    # The scare consumes the dream and marks the fish as freshly spooked.
    assert steve.dream is None
    assert steve._just_scared_until is not None
    assert any("nightmare" in t.lower() for t in toasts)
    assert any("nightmare" in m.lower() for m in steve.memory_log)


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
    f.hunger = aq.SLEEP_HUNGER_THRESHOLD + 1
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # awake and chasing food despite being nighttime


def test_hungry_fish_does_not_draw_the_sleeping_glyph():
    f = _neutral_fish(5.0, 5.0, environment={"phase": "Night", "temperature": 23.0})
    f.hunger = aq.SLEEP_HUNGER_THRESHOLD + 1
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
    f.hunger = 0.0
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
    f.hunger = 0.0
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
        f.hunger = aq.SLEEP_HUNGER_THRESHOLD + 1.0

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

    fractions = iter([0.9, 0.2])
    monkeypatch.setattr(aq, "compute_time_of_day", lambda *a, **k: next(fractions))
    monkeypatch.setattr(aq.random, "random", lambda: 0.99)  # no vignette this run

    second_timer = next(t for t in app._timers if t.interval == 1.0)
    second_timer.callback()
    second_timer.callback()

    rel = fishes[0].relationships.get(fishes[1])
    assert rel is not None
    assert "Slept together" in rel.memories[-1]


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


def test_friendly_fish_joins_a_friend_already_heading_to_the_forest(
    tmp_path, monkeypatch
):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    monkeypatch.setattr(app, "toast", lambda *a, **k: None)
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    leader, follower = fishes[0], fishes[1]
    follower.personality = "Friendly"
    follower.hunger = 0.0  # not hungry -- only travels via the friend-join clause
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
        other.hunger = 0.0
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


def test_two_fish_flee_the_tiger_shark_together_and_both_survive(tmp_path, monkeypatch):
    app = _headless_app(tmp_path, monkeypatch)
    _unlock_forest(app)
    toasts = []
    monkeypatch.setattr(app, "toast", lambda message, **kw: toasts.append(message))
    fishes = [w for w in app.widgets if isinstance(w, aq.Fish)]
    a, b = fishes[0], fishes[1]
    a.display_name, b.display_name = "Alex", "Steve"
    for other in fishes:
        other.hunger = 0.0  # keep everyone else home
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
