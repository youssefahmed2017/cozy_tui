"""Smoke tests for the deploy console (examples/deploy/deploy.py), the example
that merges the old State / Log / overlay demos.

Like the other example tests, this builds a real App at import time, so it's
loaded with ``run()`` stubbed and then driven through its own handlers. The
deploy itself is a fixed STEPS list, so nothing here needs a random seed.
"""

import importlib.util
import pathlib

import pytest

from cozy_tui.markup import plain
from cozy_tui.testing import Harness

import cozy_tui

_PATH = pathlib.Path(__file__).resolve().parents[1] / "examples" / "deploy" / "deploy.py"


@pytest.fixture
def example(monkeypatch):
    monkeypatch.setattr(cozy_tui.App, "run", lambda self: None)

    spec = importlib.util.spec_from_file_location("deploy_example", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ui = Harness(module.app, size="900x220")
    return module


def run_deploy(example):
    example.deploy()
    for _ in range(len(example.STEPS)):
        example.tick()


# ── State ────────────────────────────────────────────────────────────────────


def test_one_state_drives_the_panel_title_and_the_header_label(example):
    text = example.ui.screen
    assert text.count("checkout-api") >= 2  # box border title + header label


def test_renaming_the_service_updates_every_reader(example):
    example.service.value = "orders-api"
    text = example.ui.screen
    assert text.count("orders-api") >= 2
    assert "checkout-api" not in text.split("\n")[0]  # the border title moved


def test_a_log_line_snapshots_the_name_instead_of_following_it(example):
    # emit() reads service.value rather than binding, so renaming later must
    # not rewrite history -- that distinction is the point of the comment there.
    example.emit("INFO", "before")
    example.service.value = "orders-api"
    example.emit("INFO", "after")
    assert plain(example.log.lines[-2]).endswith("checkout-api before")
    assert plain(example.log.lines[-1]).endswith("orders-api after")


def test_the_progress_bar_and_the_stage_follow_the_same_deploy(example):
    example.deploy()
    assert example.stage.value == "Deploying…"
    example.tick()
    assert example.percent.value == example.STEPS[0][0]
    assert str(example.STEPS[0][0]) in example.ui.screen


# ── Log ──────────────────────────────────────────────────────────────────────


def test_the_console_starts_attached(example):
    assert len(example.log.lines) == 1
    assert "console attached" in example.ui.screen


def test_a_deploy_logs_one_line_per_step(example):
    run_deploy(example)
    # 1 attached + 1 "deploy started by" + one per step
    assert len(example.log.lines) == 2 + len(example.STEPS)
    assert plain(example.log.lines[-1]).endswith("traffic shifted — deploy complete")


def test_the_level_tag_is_colored_but_the_message_is_not(example):
    example.clear_log()
    example.emit("ERROR", "boom")
    ui = example.ui
    row = next(i for i, line in enumerate(ui.lines) if line.startswith("ERROR"))
    assert ui.cell(0, row).style.fg == "red"
    assert "bold" in ui.cell(0, row).style.styles
    assert ui.cell(6, row).style.fg is None  # the service/message beside it


def test_a_bracket_group_that_is_not_a_tag_survives(example):
    run_deploy(example)
    assert "GET /v2/registry/blobs?digest=[a-f0-9]+" in example.ui.screen


def test_escape_protects_a_name_that_would_parse_as_markup(example):
    example.deploy()
    assert example.current_user() in example.ui.screen  # shown, not obeyed
    assert "\\[" not in example.ui.screen


def test_clearing_the_log_empties_it_and_updates_the_counter(example):
    run_deploy(example)
    example.clear_log()
    assert example.log.lines == []
    assert "0 lines" in example.ui.screen


# ── overlays ─────────────────────────────────────────────────────────────────


def test_confirm_deploy_opens_a_modal_and_does_not_deploy_by_itself(example):
    example.confirm_deploy()
    assert "Deploy checkout-api to production?" in example.ui.screen
    assert example.timer is None  # gated: nothing started yet
    assert example.stage.value == "Idle — press Deploy"


def test_the_dialog_confines_focus_and_dismisses_on_escape(example):
    ui = example.ui
    example.confirm_deploy()
    assert example.app._overlays  # modal is on the stack
    ui.press(cozy_tui.Key.ESC)
    assert not example.app._overlays
    assert "Deploy checkout-api to production?" not in ui.screen


def test_confirming_in_the_dialog_starts_the_deploy(example):
    ui = example.ui
    example.confirm_deploy()
    ui.press("\t")  # Cancel -> Deploy
    ui.press("\r")
    assert not example.app._overlays
    assert example.stage.value == "Deploying…"
    assert example.timer is not None


def test_rollback_is_gated_by_the_built_in_confirm(example):
    run_deploy(example)
    example.confirm_rollback()
    assert "previous release" in example.ui.screen
    example.ui.press("y")
    assert example.stage.value == "Rolled back"
    assert example.percent.value == 0


def test_cancelling_the_rollback_leaves_the_release_alone(example):
    run_deploy(example)
    example.confirm_rollback()
    example.ui.press(cozy_tui.Key.ESC)
    assert example.stage.value == "Live ✔"


def test_rename_writes_back_into_the_state_explicitly(example):
    example.rename()
    dialog = example.app._overlays[-1].widget
    assert dialog.text == "checkout-api"  # seeded from the state
    example.ui.type("!")
    example.ui.press("\r")
    assert example.service.value == "checkout-api!"
    assert "checkout-api!" in example.ui.screen


def test_an_empty_rename_falls_back_to_the_default(example):
    example.service.value = "orders-api"
    example.rename()
    example.app._overlays[-1].widget.text = "   "
    example.ui.press("\r")
    assert example.service.value == "checkout-api"


def test_finishing_a_deploy_stops_the_timer_and_toasts(example):
    run_deploy(example)
    assert example.timer is None
    assert example.stage.value == "Live ✔"
    assert "is live" in example.ui.screen
