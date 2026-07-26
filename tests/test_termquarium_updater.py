"""Tests for TermQuarium's self-update logic (termquarium/updater.py).

Pure logic and file IO under tmp_path -- no real network and no real
binaries. The two network functions (`fetch_manifest`/`download`) are exercised
only via monkeypatching, matching test_termquarium_cloud.py's approach.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from examples.aquarium.termquarium import updater
from examples.aquarium.termquarium.updater import (
    Manifest,
    UpdaterState,
    UpdateError,
)

NOW = datetime(2026, 7, 26, 9, 32, tzinfo=timezone.utc)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── version comparison ──────────────────────────────────────────────────────


def test_parse_version_handles_v_prefix_and_missing_segments():
    assert updater.parse_version("v1.2.0") == (1, 2, 0)
    assert updater.parse_version("1.2") == (1, 2)
    assert updater.parse_version("2.0.0-beta") == (2, 0, 0)  # suffix ignored


def test_parse_version_rejects_garbage():
    with pytest.raises(UpdateError):
        updater.parse_version("nightly")


def test_is_newer_compares_numerically_not_as_strings():
    # The whole reason not to string-compare: "0.9.0" < "0.10.0".
    assert updater.is_newer("0.10.0", "0.9.0")
    assert not updater.is_newer("0.9.0", "0.10.0")
    # A missing trailing segment is treated as zero, so 1.0 == 1.0.0.
    assert not updater.is_newer("1.0", "1.0.0")
    assert not updater.is_newer("1.0.0", "1.0")
    assert not updater.is_newer("1.0.0", "1.0.0")
    assert updater.is_newer("1.0.1", "1.0.0")


# ── manifest parsing ────────────────────────────────────────────────────────


def _manifest_dict(**overrides):
    data = {
        "version": "1.0.0",
        "url": "https://example.test/TermQuarium-1.0.0.exe",
        "sha256": "AABBCC",
        "mandatory": False,
        "min_supported": "0.5.0",
        "notes": "Forest foraging",
    }
    data.update(overrides)
    return data


def test_parse_manifest_reads_all_fields_and_lowercases_the_hash():
    m = updater.parse_manifest(_manifest_dict())
    assert m.version == "1.0.0"
    assert m.sha256 == "aabbcc"  # normalized for comparison
    assert m.min_supported == "0.5.0"
    assert m.mandatory is False


def test_parse_manifest_defaults_optional_fields():
    m = updater.parse_manifest(
        {"version": "1.0.0", "url": "https://x", "sha256": "aa"}
    )
    assert m.mandatory is False
    assert m.min_supported is None
    assert m.notes == ""


@pytest.mark.parametrize("missing", ["version", "url", "sha256"])
def test_parse_manifest_rejects_missing_required_fields(missing):
    data = _manifest_dict()
    del data[missing]
    with pytest.raises(UpdateError):
        updater.parse_manifest(data)


def test_parse_manifest_rejects_a_non_object():
    with pytest.raises(UpdateError):
        updater.parse_manifest(["not", "a", "dict"])


def test_parse_manifest_rejects_an_uncomparable_version():
    with pytest.raises(UpdateError):
        updater.parse_manifest(_manifest_dict(version="nightly"))


# ── state persistence ───────────────────────────────────────────────────────


def test_state_round_trips_through_disk(tmp_path):
    path = tmp_path / "updater.json"
    state = UpdaterState(
        last_check=NOW.isoformat(),
        pending={"version": "1.0.0", "filename": ".pending-1.0.0.exe", "sha256": "aa"},
    )
    updater.save_state(state, path)
    loaded = updater.load_state(path)
    assert loaded.last_check == state.last_check
    assert loaded.pending == state.pending


def test_load_state_treats_corruption_as_a_clean_slate(tmp_path):
    path = tmp_path / "updater.json"
    path.write_text("{ this is not json", encoding="utf-8")
    loaded = updater.load_state(path)
    assert loaded.last_check is None and loaded.pending is None


def test_load_state_of_a_missing_file_is_empty(tmp_path):
    loaded = updater.load_state(tmp_path / "nope.json")
    assert loaded == UpdaterState()


# ── should_check throttle ───────────────────────────────────────────────────


def test_should_check_when_never_checked():
    assert updater.should_check(None, NOW)


def test_should_check_after_the_interval_but_not_before():
    recent = (NOW - timedelta(hours=1)).isoformat()
    stale = (NOW - timedelta(hours=25)).isoformat()
    assert not updater.should_check(recent, NOW)
    assert updater.should_check(stale, NOW)


def test_should_check_when_the_clock_was_rolled_back():
    future = (NOW + timedelta(days=3)).isoformat()
    assert updater.should_check(future, NOW)


def test_should_check_with_an_unreadable_timestamp():
    assert updater.should_check("not-a-date", NOW)


# ── plan_launch (the pure decision) ─────────────────────────────────────────


def test_plan_applies_a_pending_build_that_is_newer():
    state = UpdaterState(
        last_check=NOW.isoformat(),
        pending={"version": "1.0.0", "filename": "x", "sha256": "aa"},
    )
    plan = updater.plan_launch("0.9.0", state, NOW)
    assert plan.apply_pending
    assert plan.pending_version == "1.0.0"
    assert not plan.check_now  # checked just now


def test_plan_ignores_a_stale_pending_no_newer_than_installed():
    # Player manually reinstalled to 1.1.0; a leftover pending 1.0.0 must not
    # downgrade them.
    state = UpdaterState(
        last_check=NOW.isoformat(),
        pending={"version": "1.0.0", "filename": "x", "sha256": "aa"},
    )
    plan = updater.plan_launch("1.1.0", state, NOW)
    assert not plan.apply_pending
    assert plan.pending_version is None


def test_plan_checks_when_the_throttle_has_elapsed():
    state = UpdaterState(last_check=(NOW - timedelta(days=2)).isoformat())
    plan = updater.plan_launch("0.9.0", state, NOW)
    assert plan.check_now


def test_plan_skip_check_suppresses_the_background_check():
    state = UpdaterState(last_check=None)
    plan = updater.plan_launch("0.9.0", state, NOW, skip_check=True)
    assert not plan.check_now


# ── checksums & apply_pending ───────────────────────────────────────────────


def _stage(tmp_path, version, data):
    """Write a fake staged build and return a state pointing at it."""
    filename = updater._staged_filename(version)
    (tmp_path / filename).write_bytes(data)
    return UpdaterState(
        pending={"version": version, "filename": filename, "sha256": _sha(data)}
    )


def test_verify_file_matches_and_rejects(tmp_path):
    payload = b"a new build"
    path = tmp_path / "build.exe"
    path.write_bytes(payload)
    assert updater.verify_file(path, _sha(payload))
    assert not updater.verify_file(path, _sha(b"tampered"))
    assert not updater.verify_file(tmp_path / "missing.exe", _sha(payload))


def test_apply_pending_swaps_the_exe_and_keeps_a_backup(tmp_path):
    (tmp_path / "TermQuarium.exe").write_bytes(b"old build")
    new = b"shiny new build"
    staged_name = updater._staged_filename("1.0.0")
    state = _stage(tmp_path, "1.0.0", new)

    applied = updater.apply_pending(state, tmp_path)

    assert applied == "1.0.0"
    assert (tmp_path / "TermQuarium.exe").read_bytes() == new
    assert (tmp_path / "TermQuarium.exe.bak").read_bytes() == b"old build"
    assert state.pending is None
    assert not (tmp_path / staged_name).exists()  # staged file consumed by the swap


def test_apply_pending_installs_even_with_no_prior_exe(tmp_path):
    new = b"first ever build"
    state = _stage(tmp_path, "1.0.0", new)
    applied = updater.apply_pending(state, tmp_path)
    assert applied == "1.0.0"
    assert (tmp_path / "TermQuarium.exe").read_bytes() == new
    assert not (tmp_path / "TermQuarium.exe.bak").exists()


def test_apply_pending_discards_a_corrupt_staged_build(tmp_path):
    (tmp_path / "TermQuarium.exe").write_bytes(b"old build")
    filename = updater._staged_filename("1.0.0")
    (tmp_path / filename).write_bytes(b"corrupted")
    # sha256 recorded for different bytes -> checksum mismatch
    state = UpdaterState(
        pending={"version": "1.0.0", "filename": filename, "sha256": _sha(b"expected")}
    )

    applied = updater.apply_pending(state, tmp_path)

    assert applied is None
    assert (tmp_path / "TermQuarium.exe").read_bytes() == b"old build"  # untouched
    assert state.pending is None
    assert not (tmp_path / filename).exists()  # discarded


def test_apply_pending_with_nothing_pending_is_a_noop(tmp_path):
    assert updater.apply_pending(UpdaterState(), tmp_path) is None


# ── stage_update / run_background_check (network monkeypatched) ──────────────


def _install_fake_network(monkeypatch, manifest_data, build_bytes):
    """Point fetch_manifest/download at in-memory fakes."""

    def fake_fetch(url=updater.VERSION_MANIFEST_URL, *, timeout=5.0):
        if manifest_data is _UNREACHABLE:
            raise OSError("no network")
        return updater.parse_manifest(manifest_data)

    def fake_download(url, dest, *, timeout=30.0):
        from pathlib import Path

        Path(dest).write_bytes(build_bytes)

    monkeypatch.setattr(updater, "fetch_manifest", fake_fetch)
    monkeypatch.setattr(updater, "download", fake_download)


_UNREACHABLE = object()


def test_stage_update_downloads_verifies_and_records_pending(tmp_path, monkeypatch):
    build = b"the 1.0.0 build"
    manifest = updater.parse_manifest(_manifest_dict(version="1.0.0", sha256=_sha(build)))
    _install_fake_network(monkeypatch, _manifest_dict(sha256=_sha(build)), build)
    state = UpdaterState()

    updater.stage_update(manifest, tmp_path, state)

    staged = tmp_path / state.pending["filename"]
    assert staged.read_bytes() == build
    assert state.pending["version"] == "1.0.0"
    assert not (tmp_path / (staged.name + ".part")).exists()  # promoted


def test_stage_update_rejects_a_checksum_mismatch(tmp_path, monkeypatch):
    build = b"actual bytes"
    manifest = updater.parse_manifest(
        _manifest_dict(version="1.0.0", sha256=_sha(b"different"))
    )
    _install_fake_network(monkeypatch, _manifest_dict(), build)
    state = UpdaterState()

    with pytest.raises(UpdateError):
        updater.stage_update(manifest, tmp_path, state)
    assert state.pending is None
    assert not list(tmp_path.glob(".pending*"))  # nothing left behind


def test_background_check_stages_a_newer_build_and_stamps_last_check(
    tmp_path, monkeypatch
):
    build = b"1.0.0 build"
    _install_fake_network(monkeypatch, _manifest_dict(version="1.0.0", sha256=_sha(build)), build)
    state = UpdaterState()

    result = updater.run_background_check("0.9.0", state, tmp_path, now=NOW)

    assert result.staged_version == "1.0.0"
    assert state.pending["version"] == "1.0.0"
    assert state.last_check == NOW.isoformat(timespec="seconds")


def test_background_check_does_not_stage_when_up_to_date(tmp_path, monkeypatch):
    build = b"same build"
    _install_fake_network(monkeypatch, _manifest_dict(version="0.9.0", sha256=_sha(build)), build)
    state = UpdaterState()

    result = updater.run_background_check("0.9.0", state, tmp_path, now=NOW)

    assert result.staged_version is None
    assert state.pending is None
    assert state.last_check == NOW.isoformat(timespec="seconds")  # still stamped


def test_background_check_survives_an_unreachable_server(tmp_path, monkeypatch):
    _install_fake_network(monkeypatch, _UNREACHABLE, b"")
    state = UpdaterState()

    result = updater.run_background_check("0.9.0", state, tmp_path, now=NOW)

    assert result.reachable is False
    assert result.error is not None
    assert state.pending is None
    assert state.last_check == NOW.isoformat(timespec="seconds")  # throttle honored


def test_background_check_skips_an_already_staged_same_version(tmp_path, monkeypatch):
    build = b"1.0.0 build"
    _install_fake_network(monkeypatch, _manifest_dict(version="1.0.0", sha256=_sha(build)), build)
    state = UpdaterState(
        pending={"version": "1.0.0", "filename": "x", "sha256": "aa"}
    )

    result = updater.run_background_check("0.9.0", state, tmp_path, now=NOW)

    assert result.staged_version is None  # already had it staged
    assert state.pending["filename"] == "x"  # untouched


# ── full round trip: stage in one run, apply in the next ────────────────────


def test_stage_then_apply_across_two_runs(tmp_path, monkeypatch):
    (tmp_path / "TermQuarium.exe").write_bytes(b"v0.9.0")
    build = b"v1.0.0 build"
    _install_fake_network(monkeypatch, _manifest_dict(version="1.0.0", sha256=_sha(build)), build)

    # Run 1: background check stages the update.
    state = updater.load_state(tmp_path / updater.STATE_FILENAME)
    updater.run_background_check("0.9.0", state, tmp_path, now=NOW)
    updater.save_state(state, tmp_path / updater.STATE_FILENAME)

    # Run 2: next launch reads state, plans, applies.
    state2 = updater.load_state(tmp_path / updater.STATE_FILENAME)
    plan = updater.plan_launch("0.9.0", state2, NOW + timedelta(minutes=1))
    assert plan.apply_pending
    applied = updater.apply_pending(state2, tmp_path)
    updater.save_state(state2, tmp_path / updater.STATE_FILENAME)

    assert applied == "1.0.0"
    assert (tmp_path / "TermQuarium.exe").read_bytes() == build
    assert updater.load_state(tmp_path / updater.STATE_FILENAME).pending is None
