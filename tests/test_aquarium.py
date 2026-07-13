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

    box = aq._build_shop(app, state, bought.append, lambda: None, lambda item: None)
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

    box = aq._build_shop(app, state, bought.append, lambda: None, lambda item: None)
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
    for _ in range(300):
        time.sleep(0.005)
        f.draw(canvas)
        d = math.hypot(f.fx - decoration.fx, f.fy - decoration.fy)
        if min_dist_to_rock is None or d < min_dist_to_rock:
            min_dist_to_rock = d

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
        app, state, lambda species: None, lambda: None, lambda item: None
    )
    app.open_overlay(box)
    assert app._overlays  # opened

    close_btn = [c for c in box.children if c.__class__.__name__ == "Button"][-1]
    close_btn.on_mouse_click()
    assert not app._overlays


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
        time.sleep(0.01)
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
    for _ in range(15):
        time.sleep(0.01)
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

    box = aq._build_inspector(app, f, lambda fish: None, lambda fish: None)
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

    box = aq._build_inspector(app, f, renamed.append, lambda fish: None)
    buttons = [c for c in box.children if c.__class__.__name__ == "Button"]
    rename_btn = buttons[0]  # Rename, then Close
    rename_btn.on_mouse_click()

    assert renamed == [f]


def test_inspector_close_button_closes_the_overlay():
    from cozy_tui import App

    app = App(full=False, size="400x300")
    f = _neutral_fish(5.0, 5.0)

    box = aq._build_inspector(app, f, lambda fish: None, lambda fish: None)
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

    canvas = _FakeCanvas()
    for _ in range(6000):
        time.sleep(0.0005)
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

    box = aq._build_inspector(app, f, lambda fish: None, lambda fish: None)
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert any("Favorite spot: Rock" in t for t in labels)


def test_inspector_shows_none_yet_with_no_favorite_spot():
    from cozy_tui import App

    app = App(full=False, size="400x300")
    f = _neutral_fish(5.0, 5.0, decorations=[])

    box = aq._build_inspector(app, f, lambda fish: None, lambda fish: None)
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

    box = aq._build_decoration_inspector(app, d, sold.append)
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


# ── Phase 3: Daily Summary ─────────────────────────────────────────────────────


def test_daily_summary_shows_all_line_items():
    from cozy_tui import Style

    box = aq._build_daily_summary(Style(), 12, 18, 42, 13, 10, 20, 45)
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert box.title == "Day 12"
    assert any("Visitors: 18" in t for t in labels)
    assert any("Ticket Sales: +$42" in t for t in labels)
    assert any("Donations: +$13" in t for t in labels)
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
    box = aq._build_settings(app, state)
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
    box = aq._build_settings(app, state)
    app.open_overlay(box)
    assert app._overlays

    close_btn = next(c for c in box.children if c.__class__.__name__ == "Button")
    close_btn.on_mouse_click()
    assert not app._overlays


# ── Phase 4: relationships ─────────────────────────────────────────────────────


def test_form_relationship_noop_with_no_other_fish():
    f = _neutral_fish(0.0, 0.0)
    aq.form_relationship(f, [f])
    assert f.friend is None
    assert f.rival is None


def test_form_relationship_friend_is_mutual():
    random.seed(0)
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    # Force the roll into the "friend" branch regardless of seed luck.
    import unittest.mock as mock

    with mock.patch.object(aq.random, "random", return_value=0.0):
        aq.form_relationship(b, [a, b])
    assert b.friend is a
    assert a.friend is b
    assert b.rival is None


def test_form_relationship_rival_is_mutual():
    import unittest.mock as mock

    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    mid = aq.FRIEND_CHANCE + aq.RIVAL_CHANCE / 2  # strictly between the two thresholds
    with mock.patch.object(aq.random, "random", return_value=mid):
        aq.form_relationship(b, [a, b])
    assert b.rival is a
    assert a.rival is b
    assert b.friend is None


def test_form_relationship_does_not_overwrite_an_existing_friend():
    import unittest.mock as mock

    a = _neutral_fish(0.0, 0.0)
    a_existing_friend = _neutral_fish(2.0, 0.0)
    a.friend = a_existing_friend
    a_existing_friend.friend = a
    available = _neutral_fish(3.0, 0.0)  # not bonded to anyone yet
    b = _neutral_fish(1.0, 0.0)

    with mock.patch.object(aq.random, "random", return_value=0.0):
        aq.form_relationship(b, [a, a_existing_friend, available, b])

    # a and a_existing_friend already have each other -- neither is a valid
    # candidate, so b bonds with `available` instead of overwriting anyone.
    assert a.friend is a_existing_friend  # untouched
    assert b.friend is available
    assert available.friend is b


def test_form_relationship_over_many_rolls_produces_both_kinds():
    friends_seen = False
    rivals_seen = False
    for _ in range(300):
        a = _neutral_fish(0.0, 0.0)
        b = _neutral_fish(1.0, 0.0)
        aq.form_relationship(b, [a, b])
        friends_seen = friends_seen or b.friend is not None
        rivals_seen = rivals_seen or b.rival is not None
        if friends_seen and rivals_seen:
            break
    assert friends_seen
    assert rivals_seen


def test_clear_relationships_clears_friend_and_rival_pointing_at_removed():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    c = _neutral_fish(2.0, 0.0)
    a.friend = b
    b.friend = a
    c.rival = b
    b.rival = c

    aq.clear_relationships(b, [a, c])

    assert a.friend is None
    assert c.rival is None


def test_clear_relationships_leaves_unrelated_fish_untouched():
    a = _neutral_fish(0.0, 0.0)
    b = _neutral_fish(1.0, 0.0)
    c = _neutral_fish(2.0, 0.0)
    a.friend = b
    b.friend = a

    aq.clear_relationships(c, [a, b])

    assert a.friend is b
    assert b.friend is a


def _grown_fish(x=0.0, y=0.0, is_predator=False):
    f = _neutral_fish(x, y)
    f.birth_time -= aq.AGE_SECONDS_PER_DAY * 5
    f.is_predator = is_predator
    return f


def test_find_breeding_pairs_requires_mutual_friendship():
    a = _grown_fish()
    b = _grown_fish()
    a.friend = b  # one-directional -- b doesn't reciprocate
    assert aq.find_breeding_pairs([a, b]) == []


def test_find_breeding_pairs_finds_a_mutual_adult_pair():
    a = _grown_fish()
    b = _grown_fish()
    a.friend = b
    b.friend = a
    pairs = aq.find_breeding_pairs([a, b])
    assert len(pairs) == 1
    assert set(pairs[0]) == {a, b}


def test_find_breeding_pairs_excludes_babies():
    a = _grown_fish()
    b = _neutral_fish(1.0, 0.0)  # freshly made -- still a Baby
    a.friend = b
    b.friend = a
    assert aq.find_breeding_pairs([a, b]) == []


def test_find_breeding_pairs_excludes_predators():
    a = _grown_fish()
    b = _grown_fish(is_predator=True)
    a.friend = b
    b.friend = a
    assert aq.find_breeding_pairs([a, b]) == []


def test_find_breeding_pairs_each_pair_once():
    a = _grown_fish()
    b = _grown_fish()
    a.friend = b
    b.friend = a
    pairs = aq.find_breeding_pairs([a, b, b, a])  # duplicated on purpose
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
    f.rival = rival
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
    f.rival = rival
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
    f.rival = rival
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vx > 0.0  # fled the mouse (+x), not the distant rival


def test_friend_following_when_nothing_more_urgent():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(5.0, 5.0, bounds)
    friend = _neutral_fish(20.0, 5.0, bounds)
    f.friend = friend
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
    f.friend = friend
    f._next_turn = float("inf")
    f.vx, f.vy = 0.0, 0.0

    _age(f)
    f.draw(_FakeCanvas())

    assert f.vy > 0.0  # chasing the food (+y), not the friend (+x)


def test_rival_gives_a_food_speed_boost():
    bounds = (0.0, 0.0, 50.0, 50.0)

    with_rival = _neutral_fish(5.0, 5.0, bounds)
    with_rival.foods = [aq.Food(30.0, 5.0)]
    with_rival.rival = _neutral_fish(
        40.0, 40.0, bounds
    )  # far away, not actively fleeing
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
    f.friend = friend
    f.rival = rival

    box = aq._build_inspector(app, f, lambda fish: None, lambda fish: None)
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert any("Friend: Bob" in t for t in labels)
    assert any("Rival: Kevin" in t for t in labels)


def test_inspector_omits_friend_rival_lines_when_absent():
    from cozy_tui import App

    app = App(full=False, size="400x300")
    f = _neutral_fish(5.0, 5.0)

    box = aq._build_inspector(app, f, lambda fish: None, lambda fish: None)
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert not any(t.startswith("Friend:") for t in labels)
    assert not any(t.startswith("Rival:") for t in labels)


def test_describe_fish_includes_friend_hint():
    f = _neutral_fish(5.0, 5.0)
    friend = _neutral_fish(1.0, 1.0)
    friend.display_name = "Bob"
    f.friend = friend
    assert "Bob" in aq.describe_fish(f)


def test_describe_fish_includes_rival_hint_when_no_friend():
    f = _neutral_fish(5.0, 5.0)
    rival = _neutral_fish(1.0, 1.0)
    rival.display_name = "Kevin"
    f.rival = rival
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
    fishes[0].friend = fishes[1]
    fishes[1].friend = fishes[0]

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


def test_friends_sleep_close_together():
    bounds = (0.0, 0.0, 50.0, 50.0)
    f = _neutral_fish(
        5.0, 5.0, bounds, environment={"phase": "Night", "temperature": 23.0}
    )
    friend = _neutral_fish(30.0, 5.0, bounds)
    f.friend = friend
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
    f.friend = friend
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
    f.rival = rival
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
    f.rival = rival
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
    a.rival = b
    b.rival = a
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
    box = aq._build_settings(app, state)
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
    assert (same_species_near.fx, same_species_near.fy, same_species_near.vx, same_species_near.vy) in mates
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
    f.friend = None
    f.rival = None
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
