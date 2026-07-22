"""Smoke tests for the screens example (examples/screens/screens.py).

Like the other example tests, this builds a real App at import time, so it's
loaded with ``run()`` stubbed and driven through its own handlers. Time is the
Harness's virtual clock, so the 15-second round costs nothing.
"""

import importlib.util
import pathlib

import pytest

from cozy_tui.testing import Harness

import cozy_tui

_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "examples" / "screens" / "screens.py"
)


@pytest.fixture
def example(monkeypatch):
    monkeypatch.setattr(cozy_tui.App, "run", lambda self: None)

    spec = importlib.util.spec_from_file_location("screens_example", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ui = Harness(module.app, size="560x140")
    return module


def run_clock(example, seconds):
    """Advance the round. A repeating timer fires at most once per drain, so
    the ticks are stepped rather than jumped — that's what the running game
    sees too. A little slack covers the float accumulation over 150 steps."""
    for _ in range(int(seconds / example.TICK) + 20):
        example.ui.advance(example.TICK)


# ── navigation ───────────────────────────────────────────────────────────────


def test_the_app_opens_on_the_menu_without_an_explicit_show(example):
    # The first screen created adopts the app and starts out current.
    assert example.app.current_screen is example.menu
    assert "COZY ARCADE" in example.ui.screen


def test_playing_switches_to_the_game_screen(example):
    example.start_round()
    assert example.app.current_screen is example.game
    assert "TAP SPACE" in example.ui.screen
    assert "COZY ARCADE" not in example.ui.screen


def test_each_screen_shows_its_own_docked_footer(example):
    assert "[menu]" in example.ui.screen
    example.start_round()
    screen = example.ui.screen
    assert "[game]" in screen and "[menu]" not in screen


def test_escape_walks_back_toward_the_menu(example):
    example.start_round()
    example.on_escape()
    assert example.app.current_screen is example.menu


def test_settings_returns_to_wherever_it_was_opened_from(example):
    example.open_settings()
    example.go_back()
    assert example.app.current_screen is example.menu

    example.start_round()
    example.open_settings()
    assert example.app.current_screen is example.settings
    example.go_back()
    assert example.app.current_screen is example.game


# ── state survives a switch ──────────────────────────────────────────────────


def test_the_score_and_clock_survive_a_trip_to_settings(example):
    example.start_round()
    for _ in range(4):
        example.on_space()
    run_clock(example, 1.0)
    score, clock = example.score.value, example.clock.value

    example.open_settings()
    example.go_back()
    assert example.score.value == score
    assert example.clock.value == clock
    assert f"Score: {score}" in example.ui.screen


def test_the_settings_field_keeps_what_was_typed(example):
    example.open_settings()
    example.ui.focus(example.name_field)
    example.name_field.value = ""
    example.ui.type("ada")
    example.go_back()
    example.open_settings()
    assert example.name_field.value == "ada"
    assert "ada" in example.ui.screen


def test_a_screen_restores_the_widget_that_had_focus(example):
    example.open_settings()
    example.ui.focus(example.name_field)
    example.go_back()
    example.open_settings()
    assert example.ui.focused is example.name_field


# ── on_show / on_hide ────────────────────────────────────────────────────────


def test_the_clock_runs_only_while_the_game_screen_is_showing(example):
    example.start_round()
    assert example.timer is not None
    run_clock(example, 1.0)
    remaining = example.clock.value
    assert remaining < example.ROUND_SECONDS

    example.open_settings()
    assert example.timer is None  # on_hide cancelled it
    run_clock(example, 5.0)
    assert example.clock.value == remaining  # the round did not run out unwatched

    example.go_back()
    assert example.timer is not None  # on_show restarted it
    run_clock(example, 1.0)
    assert example.clock.value < remaining


def test_the_round_ends_on_the_over_screen_with_the_final_score(example):
    example.start_round()
    for _ in range(3):
        example.on_space()
    run_clock(example, example.ROUND_SECONDS)
    assert example.app.current_screen is example.over
    assert example.clock.value == 0
    assert "scored 3" in example.ui.screen
    assert example.timer is None  # on_hide stopped it on the way out


def test_space_does_nothing_outside_the_game(example):
    example.on_space()
    assert example.score.value == 0
    example.open_settings()
    example.on_space()
    assert example.score.value == 0


def test_playing_again_resets_the_round(example):
    example.start_round()
    example.on_space()
    run_clock(example, example.ROUND_SECONDS)
    example.start_round()
    assert example.app.current_screen is example.game
    assert example.score.value == 0
    assert example.clock.value == example.ROUND_SECONDS


# ── shared state across screens ──────────────────────────────────────────────


def test_the_player_name_typed_in_settings_reaches_the_other_screens(example):
    example.open_settings()
    example.ui.focus(example.name_field)
    example.name_field.value = ""
    example.ui.type("grace")
    example.go_back()
    example.start_round()
    assert "playing as grace" in example.ui.screen
    run_clock(example, example.ROUND_SECONDS)
    assert "grace scored" in example.ui.screen


def test_clearing_the_name_falls_back_to_the_default(example):
    example.open_settings()
    example.ui.focus(example.name_field)
    for _ in range(len("player one")):
        example.ui.press(cozy_tui.Key.BACKSPACE)
    assert example.player.value == "player one"
