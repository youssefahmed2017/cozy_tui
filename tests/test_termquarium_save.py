"""Persistence contract tests for the TermQuarium example."""

import json
import time
from datetime import datetime, timedelta, timezone

from examples.aquarium.termquarium.save import (
    delete_save,
    duplicate_save,
    format_relative_time,
    list_saves,
    load_cloud_key,
    load_unlocked_achievements,
    read_save,
    rename_save,
    store_cloud_key,
    store_unlocked_achievements,
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


# ── delete_save / rename_save / duplicate_save ────────────────────────────────


def test_delete_save_removes_the_file(tmp_path):
    path = write_save("Gone Soon", {"state": {}, "day": 1, "fish": []}, home=tmp_path)
    assert path.exists()

    delete_save(path)

    assert not path.exists()
    assert list_saves(home=tmp_path) == []


def test_delete_save_missing_file_is_a_no_op(tmp_path):
    missing = tmp_path / ".termquarium" / "saves" / "Never Existed.json"
    delete_save(missing)  # must not raise


def test_rename_save_moves_content_under_the_new_name(tmp_path):
    path = write_save(
        "Old Name", {"state": {"money": 5}, "day": 3, "fish": []}, home=tmp_path
    )

    new_path = rename_save(path, "New Name", home=tmp_path)

    assert not path.exists()  # old file removed
    assert new_path.name == "New Name.json"
    data = read_save(new_path)
    assert data["metadata"]["name"] == "New Name"
    assert data["aquarium"]["state"]["money"] == 5


def test_rename_save_preserves_original_created_time(tmp_path):
    path = write_save("Old Name", {"state": {}, "day": 1, "fish": []}, home=tmp_path)
    created = read_save(path)["metadata"]["created"]
    time.sleep(1.1)

    new_path = rename_save(path, "New Name", home=tmp_path)

    assert read_save(new_path)["metadata"]["created"] == created


def test_rename_save_to_the_same_name_is_a_harmless_no_op(tmp_path):
    path = write_save("Same Name", {"state": {}, "day": 1, "fish": []}, home=tmp_path)

    new_path = rename_save(path, "Same Name", home=tmp_path)

    assert new_path == path
    assert path.exists()


def test_duplicate_save_creates_a_second_file_leaving_the_original(tmp_path):
    path = write_save(
        "Original", {"state": {"money": 7}, "day": 2, "fish": []}, home=tmp_path
    )

    copy_path = duplicate_save(path, "Original copy", home=tmp_path)

    assert path.exists()  # original untouched
    assert copy_path.exists()
    assert copy_path != path
    copy_data = read_save(copy_path)
    assert copy_data["metadata"]["name"] == "Original copy"
    assert copy_data["aquarium"]["state"]["money"] == 7
    names = {meta["name"] for _p, meta in list_saves(home=tmp_path)}
    assert names == {"Original", "Original copy"}


def test_duplicate_save_preserves_original_created_time(tmp_path):
    path = write_save("Original", {"state": {}, "day": 1, "fish": []}, home=tmp_path)
    created = read_save(path)["metadata"]["created"]
    time.sleep(1.1)

    copy_path = duplicate_save(path, "Original copy", home=tmp_path)

    assert read_save(copy_path)["metadata"]["created"] == created


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

    box = build_save_menu(
        app,
        cards,
        lambda path: None,
        lambda p, o, n: None,
        lambda p, n: None,
        lambda p, n: None,
    )
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

    box = build_save_menu(
        app,
        cards,
        loaded.append,
        lambda p, o, n: None,
        lambda p, n: None,
        lambda p, n: None,
    )
    load_btn = next(
        c
        for c in box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Load"
    )
    load_btn.on_mouse_click()

    assert loaded == [path]


def test_build_save_menu_rename_button_opens_a_prefilled_prompt():
    from cozy_tui import App
    import pathlib

    app = App(full=False, size="500x400")
    path = pathlib.Path("Castle Cove.json")
    cards = [
        (path, {"name": "Castle Cove", "fish": 7, "money": 40, "food": 8, "day": 24})
    ]
    renamed = []

    box = build_save_menu(
        app,
        cards,
        lambda p: None,
        lambda p, old, new: renamed.append((p, old, new)),
        lambda p, n: None,
        lambda p, n: None,
    )
    rename_btn = next(
        c
        for c in box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Rename"
    )
    rename_btn.on_mouse_click()

    prompt = app._overlays[-1].widget
    assert prompt.text == "Castle Cove"
    prompt.text = "New Name"
    prompt.on_key(__import__("cozy_tui").Key.ENTER)

    assert renamed == [(path, "Castle Cove", "New Name")]


def test_build_save_menu_duplicate_button_opens_a_copy_named_prompt():
    from cozy_tui import App
    import pathlib

    app = App(full=False, size="500x400")
    path = pathlib.Path("Castle Cove.json")
    cards = [
        (path, {"name": "Castle Cove", "fish": 7, "money": 40, "food": 8, "day": 24})
    ]
    duplicated = []

    box = build_save_menu(
        app,
        cards,
        lambda p: None,
        lambda p, old, new: None,
        lambda p, new: duplicated.append((p, new)),
        lambda p, n: None,
    )
    dup_btn = next(
        c
        for c in box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Duplicate"
    )
    dup_btn.on_mouse_click()

    prompt = app._overlays[-1].widget
    assert prompt.text == "Castle Cove copy"
    prompt.on_key(__import__("cozy_tui").Key.ENTER)

    assert duplicated == [(path, "Castle Cove copy")]


def test_build_save_menu_delete_button_asks_for_confirmation_first():
    from cozy_tui import App
    import pathlib

    app = App(full=False, size="500x400")
    path = pathlib.Path("Castle Cove.json")
    cards = [
        (path, {"name": "Castle Cove", "fish": 7, "money": 40, "food": 8, "day": 24})
    ]
    deleted = []

    box = build_save_menu(
        app,
        cards,
        lambda p: None,
        lambda p, o, n: None,
        lambda p, n: None,
        lambda p, name: deleted.append((p, name)),
    )
    delete_btn = next(
        c
        for c in box.children
        if c.__class__.__name__ == "Button" and c.text.strip() == "Delete"
    )
    delete_btn.on_mouse_click()

    assert deleted == []  # not yet -- confirmation is still pending
    confirm = app._overlays[-1].widget
    confirm.on_key("y")

    assert deleted == [(path, "Castle Cove")]


def test_build_save_menu_caps_at_max_cards_shown():
    from cozy_tui import App
    import pathlib
    from examples.aquarium.termquarium.ui import MAX_CARDS_SHOWN

    app = App(full=False, size="500x600")
    cards = [
        (pathlib.Path(f"Save {i}.json"), {"name": f"Save {i}", "fish": i})
        for i in range(MAX_CARDS_SHOWN + 3)
    ]

    box = build_save_menu(
        app,
        cards,
        lambda path: None,
        lambda p, o, n: None,
        lambda p, n: None,
        lambda p, n: None,
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]

    shown = sum(1 for t in labels if t.startswith("Save "))
    assert shown == MAX_CARDS_SHOWN


def test_build_save_menu_empty_shows_a_hint():
    from cozy_tui import App

    app = App(full=False, size="500x400")
    box = build_save_menu(
        app,
        [],
        lambda path: None,
        lambda p, o, n: None,
        lambda p, n: None,
        lambda p, n: None,
    )
    labels = [c.text for c in box.children if c.__class__.__name__ == "Label"]
    assert any("No saves yet" in t for t in labels)


# ── Cloud Saves: local Cloud Key storage ──────────────────────────────────────


def test_load_cloud_key_is_none_before_anything_is_set_up(tmp_path):
    assert load_cloud_key(home=tmp_path) is None


def test_store_then_load_cloud_key_round_trips(tmp_path):
    store_cloud_key("K3F9-XQ2P-7RTN-JM4W", home=tmp_path)

    assert load_cloud_key(home=tmp_path) == "K3F9-XQ2P-7RTN-JM4W"


def test_store_cloud_key_of_none_forgets_it(tmp_path):
    store_cloud_key("K3F9-XQ2P-7RTN-JM4W", home=tmp_path)
    store_cloud_key(None, home=tmp_path)

    assert load_cloud_key(home=tmp_path) is None


def test_storing_a_cloud_key_preserves_other_config_contents(tmp_path):
    from examples.aquarium.termquarium.save import _config_path

    _config_path(tmp_path).write_text(
        '{"some_other_setting": true}\n', encoding="utf-8"
    )

    store_cloud_key("K3F9-XQ2P-7RTN-JM4W", home=tmp_path)

    config = json.loads(_config_path(tmp_path).read_text(encoding="utf-8"))
    assert config["some_other_setting"] is True
    assert config["cloud_key"] == "K3F9-XQ2P-7RTN-JM4W"


# ── Achievements: account-wide, not tied to any one save ──────────────────────


def test_load_unlocked_achievements_is_empty_before_anything_is_earned(tmp_path):
    assert load_unlocked_achievements(home=tmp_path) == set()


def test_store_then_load_unlocked_achievements_round_trips(tmp_path):
    store_unlocked_achievements({"first_sale", "full_house"}, home=tmp_path)

    assert load_unlocked_achievements(home=tmp_path) == {"first_sale", "full_house"}


def test_store_unlocked_achievements_overwrites_the_previous_set(tmp_path):
    store_unlocked_achievements({"first_sale"}, home=tmp_path)
    store_unlocked_achievements({"first_sale", "full_house"}, home=tmp_path)

    assert load_unlocked_achievements(home=tmp_path) == {"first_sale", "full_house"}


def test_load_unlocked_achievements_survives_a_corrupt_file(tmp_path):
    from examples.aquarium.termquarium.save import _achievements_path

    path = _achievements_path(tmp_path)  # also creates the data dir
    path.write_text("not json", encoding="utf-8")

    assert load_unlocked_achievements(home=tmp_path) == set()
