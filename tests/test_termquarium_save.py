"""Persistence contract tests for the TermQuarium example."""

import time
from datetime import datetime, timedelta, timezone

from examples.aquarium.termquarium.save import (
    format_relative_time,
    list_saves,
    read_save,
    write_save,
)
from examples.aquarium.termquarium.economy import should_warn_hungry
from examples.aquarium.termquarium.ui import build_save_menu


def test_save_has_versioned_metadata_and_aquarium_state(tmp_path):
    path = write_save(
        "Steve's Kingdom",
        {"state": {"money": 100, "food": 13}, "day": 142, "fish": [{}, {}]},
        home=tmp_path,
    )

    data = read_save(path)

    assert path.name == "Steve's Kingdom.json"
    assert data["version"] == 1
    assert data["metadata"]["name"] == "Steve's Kingdom"
    assert data["metadata"]["money"] == 100
    assert data["metadata"]["food"] == 13
    assert data["metadata"]["fish"] == 2
    assert data["metadata"]["day"] == 142
    assert data["aquarium"]["state"]["money"] == 100


def test_save_list_returns_newest_metadata_and_creates_data_layout(tmp_path):
    write_save("Castle Cove", {"state": {}, "day": 1, "fish": []}, home=tmp_path)

    cards = list_saves(home=tmp_path)

    assert [metadata["name"] for _path, metadata in cards] == ["Castle Cove"]
    root = tmp_path / ".termquarium"
    assert (root / "config.json").exists()
    assert (root / "settings.json").exists()
    assert (root / "screenshots").is_dir()


def test_hunger_warning_fires_only_on_a_threshold_crossing():
    assert not should_warn_hungry([50.0], warning_active=False)
    assert should_warn_hungry([50.1], warning_active=False)
    assert not should_warn_hungry([100.0], warning_active=True)


def test_save_list_sorts_newest_played_first(tmp_path):
    write_save("Old One", {"state": {}, "day": 1, "fish": []}, home=tmp_path)
    time.sleep(1.1)  # last_played has second-resolution timestamps
    write_save("New One", {"state": {}, "day": 2, "fish": []}, home=tmp_path)

    cards = list_saves(home=tmp_path)

    assert [metadata["name"] for _path, metadata in cards] == ["New One", "Old One"]


def test_write_save_preserves_created_but_updates_last_played(tmp_path):
    path = write_save("Reused", {"state": {}, "day": 1, "fish": []}, home=tmp_path)
    first = read_save(path)["metadata"]["created"]
    time.sleep(1.1)
    write_save("Reused", {"state": {}, "day": 2, "fish": []}, home=tmp_path)
    second = read_save(path)["metadata"]

    assert second["created"] == first  # unchanged across re-saves
    assert second["last_played"] != first  # bumped on every save
    assert second["day"] == 2


# ── format_relative_time ───────────────────────────────────────────────────────


def test_format_relative_time_just_now():
    now = datetime.now(timezone.utc)
    assert format_relative_time(now.isoformat(), now=now) == "just now"


def test_format_relative_time_minutes_and_hours():
    now = datetime.now(timezone.utc)
    five_min_ago = (now - timedelta(minutes=5)).isoformat()
    two_hours_ago = (now - timedelta(hours=2)).isoformat()
    assert format_relative_time(five_min_ago, now=now) == "5 minutes ago"
    assert format_relative_time(two_hours_ago, now=now) == "2 hours ago"


def test_format_relative_time_singular_forms():
    now = datetime.now(timezone.utc)
    one_min_ago = (now - timedelta(minutes=1)).isoformat()
    one_hour_ago = (now - timedelta(hours=1)).isoformat()
    assert format_relative_time(one_min_ago, now=now) == "1 minute ago"
    assert format_relative_time(one_hour_ago, now=now) == "1 hour ago"


def test_format_relative_time_yesterday_and_days():
    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(days=1, hours=1)).isoformat()
    three_days_ago = (now - timedelta(days=3)).isoformat()
    assert format_relative_time(yesterday, now=now) == "Yesterday"
    assert format_relative_time(three_days_ago, now=now) == "3 days ago"


def test_format_relative_time_weeks_months_years():
    now = datetime.now(timezone.utc)
    assert (
        format_relative_time((now - timedelta(days=14)).isoformat(), now=now)
        == "2 weeks ago"
    )
    assert (
        format_relative_time((now - timedelta(days=60)).isoformat(), now=now)
        == "2 months ago"
    )
    assert (
        format_relative_time((now - timedelta(days=800)).isoformat(), now=now)
        == "2 years ago"
    )


def test_format_relative_time_invalid_input_is_unknown():
    assert format_relative_time("") == "unknown"
    assert format_relative_time(None) == "unknown"
    assert format_relative_time("not-a-date") == "unknown"


# ── build_save_menu ─────────────────────────────────────────────────────────────


def test_build_save_menu_shows_emoji_stat_lines_per_card():
    import pathlib

    from cozy_tui import App

    app = App(full=False, size="500x400")
    now = datetime.now(timezone.utc).isoformat()
    cards = [
        (
            pathlib.Path("Steve's Kingdom.json"),
            {
                "name": "Steve's Kingdom",
                "fish": 100,
                "money": 100,
                "food": 13,
                "day": 142,
                "last_played": now,
            },
        )
    ]

    box = build_save_menu(app, cards, lambda path: None)
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    assert any("Steve's Kingdom" in t for t in labels)
    assert any("🐠 100 Fish" == t for t in labels)
    assert any("💰 $100" == t for t in labels)
    assert any("🍽️ 13 Food" == t for t in labels)
    assert any("📅 Day 142" == t for t in labels)
    assert any(t.startswith("🕒 Played") for t in labels)


def test_build_save_menu_load_button_invokes_callback_with_path():
    from cozy_tui import App
    import pathlib

    app = App(full=False, size="500x400")
    path = pathlib.Path("Castle Cove.json")
    cards = [
        (path, {"name": "Castle Cove", "fish": 7, "money": 40, "food": 8, "day": 24})
    ]
    loaded = []

    box = build_save_menu(app, cards, loaded.append)
    load_btn = next(
        c
        for c in box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Load"
    )
    load_btn.on_mouse_click()

    assert loaded == [path]


def test_build_save_menu_caps_at_max_cards_shown():
    from cozy_tui import App
    import pathlib
    from examples.aquarium.termquarium.ui import MAX_CARDS_SHOWN

    app = App(full=False, size="500x600")
    cards = [
        (pathlib.Path(f"Save {i}.json"), {"name": f"Save {i}", "fish": i})
        for i in range(MAX_CARDS_SHOWN + 3)
    ]

    box = build_save_menu(app, cards, lambda path: None)
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    shown = sum(1 for t in labels if t.startswith("Save "))
    assert shown == MAX_CARDS_SHOWN


def test_build_save_menu_empty_shows_a_hint():
    from cozy_tui import App

    app = App(full=False, size="500x400")
    box = build_save_menu(app, [], lambda path: None)
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert any("No saves yet" in t for t in labels)
