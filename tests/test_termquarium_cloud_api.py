"""Cloud Saves API storage-logic tests (examples/aquarium/website/api/store.py).

Loaded the same way tests/test_aquarium.py loads aquarium.py: this file
lives outside any installed package (it's deployed separately, as a Vercel
Python function) and deliberately has no dependency on FastAPI -- only
store.py's plain Redis-command-building logic is under test here, with
_redis_command() replaced by a tiny in-memory fake so nothing touches a
real network or a real Upstash instance.
"""

import importlib.util
import pathlib

_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "examples"
    / "aquarium"
    / "website"
    / "api"
    / "store.py"
)
_spec = importlib.util.spec_from_file_location("store", _PATH)
store = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(store)


class _FakeRedis:
    """A tiny in-memory stand-in for the handful of Redis commands
    store.py actually issues (SET/GET/HSET/HGETALL/HDEL/DEL)."""

    def __init__(self):
        self.strings = {}
        self.hashes = {}

    def __call__(self, *args):
        command, *rest = args
        if command == "SET":
            key, value = rest
            self.strings[key] = value
            return "OK"
        if command == "GET":
            (key,) = rest
            return self.strings.get(key)
        if command == "DEL":
            (key,) = rest
            return 1 if self.strings.pop(key, None) is not None else 0
        if command == "HSET":
            key, field, value = rest
            self.hashes.setdefault(key, {})[field] = value
            return 1
        if command == "HGETALL":
            (key,) = rest
            flat = []
            for field, value in self.hashes.get(key, {}).items():
                flat.extend([field, value])
            return flat
        if command == "HDEL":
            key, field = rest
            return 1 if self.hashes.get(key, {}).pop(field, None) is not None else 0
        raise AssertionError(f"unexpected Redis command: {args}")


def test_put_then_get_round_trips(monkeypatch):
    monkeypatch.setattr(store, "_redis_command", _FakeRedis())

    payload = {"version": 1, "metadata": {"name": "Steve's Kingdom"}, "aquarium": {}}
    store.put_save("KEY-A", "Steve's Kingdom", payload)

    assert store.get_save("KEY-A", "Steve's Kingdom") == payload


def test_get_nonexistent_save_returns_none(monkeypatch):
    monkeypatch.setattr(store, "_redis_command", _FakeRedis())

    assert store.get_save("KEY-A", "Never Saved") is None


def test_list_saves_returns_name_and_metadata_without_the_full_aquarium(monkeypatch):
    monkeypatch.setattr(store, "_redis_command", _FakeRedis())

    store.put_save(
        "KEY-A",
        "Castle Cove",
        {"version": 1, "metadata": {"day": 3}, "aquarium": {"big": "blob"}},
    )

    [entry] = store.list_saves("KEY-A")
    assert entry == {"name": "Castle Cove", "metadata": {"day": 3}}


def test_delete_save_removes_both_the_value_and_the_metadata_entry(monkeypatch):
    monkeypatch.setattr(store, "_redis_command", _FakeRedis())

    store.put_save("KEY-A", "Old One", {"version": 1, "metadata": {}, "aquarium": {}})
    store.delete_save("KEY-A", "Old One")

    assert store.get_save("KEY-A", "Old One") is None
    assert store.list_saves("KEY-A") == []


def test_different_keys_never_see_each_others_saves(monkeypatch):
    # The one real security property of this whole design: the Cloud Key
    # *is* the auth model, so namespace isolation has to actually hold.
    monkeypatch.setattr(store, "_redis_command", _FakeRedis())

    store.put_save(
        "KEY-A", "Same Name", {"version": 1, "metadata": {"owner": "A"}, "aquarium": {}}
    )
    store.put_save(
        "KEY-B", "Same Name", {"version": 1, "metadata": {"owner": "B"}, "aquarium": {}}
    )

    assert store.get_save("KEY-A", "Same Name")["metadata"]["owner"] == "A"
    assert store.get_save("KEY-B", "Same Name")["metadata"]["owner"] == "B"
    assert [e["name"] for e in store.list_saves("KEY-A")] == ["Same Name"]
    assert [e["name"] for e in store.list_saves("KEY-B")] == ["Same Name"]
