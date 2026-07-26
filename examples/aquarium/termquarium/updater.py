"""Self-update logic for TermQuarium's Windows launcher (`update.py`).

The desktop shortcut points at `update.exe` rather than `TermQuarium.exe`.
On Windows you cannot overwrite a running executable, so the game can never
replace its own binary -- a separate launcher that runs *first* (while the
game isn't running yet) sidesteps that entirely.

The launcher works in two phases so that startup is instant almost every time:

  1. **Apply** (local, no network): if a checksum-verified update was staged
     on a previous run, swap it into place -- a fast local file rename -- then
     launch the game.
  2. **Check** (throttled, background): at most once every 24h, a detached
     process fetches the version manifest, downloads any newer build, verifies
     it, and *stages* it as "pending" for the next launch to apply. The game is
     already running by then; the download never blocks it.

The golden rule threaded through everything here: the updater must never stop
the game from starting. Every failure path -- offline, manifest unreachable,
corrupt download, bad checksum -- falls through to launching whatever is
already installed. A player on a plane still gets their fish.

This module is deliberately pure standard library (like `cloud.py`/`save.py`)
and keeps the decision logic (`plan_launch`, `should_check`, version compare)
separate from the side-effecting IO (`download`, `fetch_manifest`,
`stage_update`, `apply_pending`) so the decisions are testable without a
network or real binaries -- see tests/test_termquarium_updater.py.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Where the published manifest lives. A static JSON on the CDN (cacheable, no
# cold start) is the plan; the URL stays the same if it later becomes a
# dynamic endpoint. The server side is not built yet -- see project memory.
VERSION_MANIFEST_URL = "https://termquarium.vercel.app/version.json"

CHECK_INTERVAL_SECONDS = 24 * 60 * 60  # throttle: at most one check per day
DEFAULT_EXE_NAME = "TermQuarium.exe"
STATE_FILENAME = "updater.json"

_HASH_CHUNK = 1 << 20  # 1 MiB


class UpdateError(Exception):
    """Anything that means an update couldn't be trusted or applied. Callers
    treat it as "skip the update, launch what's installed" -- never fatal."""


# ── semantic versions ──────────────────────────────────────────────────────
# String comparison is wrong ("0.9.0" > "0.10.0"), so versions are compared as
# integer tuples. A pre-release/build suffix (e.g. "1.0.0-beta") is ignored for
# ordering -- out of scope for now; the numeric core is what gates an update.


def parse_version(text: str) -> tuple[int, ...]:
    """Parse ``"v1.2.0"`` / ``"1.2"`` into ``(1, 2, 0)`` / ``(1, 2)``."""
    match = re.match(r"\d+(?:\.\d+)*", str(text).strip().lstrip("vV"))
    if not match:
        raise UpdateError(f"Unparsable version: {text!r}")
    return tuple(int(part) for part in match.group(0).split("."))


def is_newer(candidate: str, baseline: str) -> bool:
    """True if ``candidate`` is a strictly newer version than ``baseline``."""
    a, b = parse_version(candidate), parse_version(baseline)
    width = max(len(a), len(b))
    pad = lambda t: t + (0,) * (width - len(t))
    return pad(a) > pad(b)


# ── manifest ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Manifest:
    """The published description of the latest release."""

    version: str
    url: str
    sha256: str
    mandatory: bool = False
    min_supported: str | None = None
    notes: str = ""


def parse_manifest(data: Any) -> Manifest:
    """Validate a decoded manifest into a :class:`Manifest`.

    Strict about the three fields an update can't proceed without
    (``version``/``url``/``sha256``); tolerant of the optional ones so an older
    launcher never chokes on a field a newer manifest adds."""
    if not isinstance(data, dict):
        raise UpdateError("Manifest is not a JSON object")
    required = {}
    for name in ("version", "url", "sha256"):
        value = data.get(name)
        if not isinstance(value, str) or not value:
            raise UpdateError(f"Manifest is missing a valid {name!r}")
        required[name] = value
    parse_version(required["version"])  # reject a manifest we can't compare
    min_supported = data.get("min_supported")
    return Manifest(
        version=required["version"],
        url=required["url"],
        sha256=required["sha256"].lower(),
        mandatory=bool(data.get("mandatory", False)),
        min_supported=min_supported if isinstance(min_supported, str) else None,
        notes=data.get("notes", "") if isinstance(data.get("notes"), str) else "",
    )


# ── persisted state (last_check + a pending staged update) ──────────────────


@dataclass
class UpdaterState:
    """What the launcher remembers between runs, in ``updater.json``.

    ``last_check`` is a UTC ISO timestamp (the throttle clock); ``pending`` is
    ``{"version", "filename", "sha256", "mandatory"}`` describing an update
    already downloaded and verified, waiting to be applied on the next launch.
    """

    last_check: str | None = None
    pending: dict | None = None

    def to_dict(self) -> dict:
        return {"last_check": self.last_check, "pending": self.pending}


def load_state(path: Path) -> UpdaterState:
    """Read the launcher's state, treating any corruption as a clean slate --
    a mangled updater.json must never stop the game from launching."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return UpdaterState()
    if not isinstance(data, dict):
        return UpdaterState()
    last_check = data.get("last_check")
    pending = data.get("pending")
    return UpdaterState(
        last_check=last_check if isinstance(last_check, str) else None,
        pending=pending if isinstance(pending, dict) else None,
    )


def save_state(state: UpdaterState, path: Path) -> None:
    """Write state atomically (temp + replace), like save.py does everywhere."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


# ── the decision (pure) ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class LaunchPlan:
    """What the launcher should do this run, decided without any IO."""

    apply_pending: bool
    pending_version: str | None
    check_now: bool
    reason: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def should_check(
    last_check: str | None,
    now: datetime,
    interval_seconds: float = CHECK_INTERVAL_SECONDS,
) -> bool:
    """Is it time for another update check?

    True if we've never checked, if the recorded time is unreadable, or if the
    interval has elapsed. A ``last_check`` in the *future* (the clock was rolled
    back) is treated as due, so a clock change can't wedge the throttle shut."""
    if not last_check:
        return True
    try:
        last = datetime.fromisoformat(last_check)
    except (TypeError, ValueError):
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    elapsed = (now - last).total_seconds()
    if elapsed < 0:  # clock moved backwards
        return True
    return elapsed >= interval_seconds


def plan_launch(
    local_version: str,
    state: UpdaterState,
    now: datetime,
    *,
    interval_seconds: float = CHECK_INTERVAL_SECONDS,
    skip_check: bool = False,
) -> LaunchPlan:
    """Decide, from local state alone, whether to apply a staged update and
    whether to kick off a background check this run. No network, no files."""
    pending = state.pending or None
    apply = False
    pending_version = None
    if pending and isinstance(pending.get("version"), str):
        pending_version = pending["version"]
        # Only apply a pending build that's actually newer than what's
        # installed -- guards against a stale pending entry left by a manual
        # reinstall to a newer version than the one that was staged.
        try:
            apply = is_newer(pending_version, local_version)
        except UpdateError:
            apply = False
    check = (not skip_check) and should_check(state.last_check, now, interval_seconds)
    reason = (
        f"apply={'yes' if apply else 'no'}"
        f" check={'yes' if check else 'no'}"
    )
    return LaunchPlan(
        apply_pending=apply,
        pending_version=pending_version if apply else None,
        check_now=check,
        reason=reason,
    )


# ── checksums & applying a staged update ────────────────────────────────────


def sha256_file(path: Path) -> str:
    """Hex SHA-256 of a file, streamed so a large exe isn't read into memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: Path, expected_sha256: str) -> bool:
    """True if ``path`` exists and matches the expected hash (case-insensitive)."""
    try:
        return sha256_file(path) == expected_sha256.lower()
    except OSError:
        return False


def apply_pending(
    state: UpdaterState,
    install_dir: Path,
    *,
    exe_name: str = DEFAULT_EXE_NAME,
) -> str | None:
    """Swap a verified staged build into place, keeping one ``.bak`` rollback.

    Returns the applied version, or ``None`` if there was nothing valid to
    apply (no pending entry, staged file missing, or checksum mismatch) -- in
    every ``None`` case the pending entry is cleared and the currently
    installed exe is left untouched. Mutates ``state``; the caller persists it.
    """
    pending = state.pending
    if not pending:
        return None
    install_dir = Path(install_dir)
    staged = install_dir / str(pending.get("filename", ""))
    expected = str(pending.get("sha256", ""))
    version = pending.get("version")

    if not pending.get("filename") or not verify_file(staged, expected):
        # Nothing to trust: drop the pending entry and discard the staged file.
        state.pending = None
        try:
            staged.unlink(missing_ok=True)
        except OSError:
            pass
        return None

    exe_path = install_dir / exe_name
    backup = install_dir / (exe_name + ".bak")
    had_exe = exe_path.exists()
    try:
        if had_exe:
            exe_path.replace(backup)  # atomic; keep the old build for rollback
        staged.replace(exe_path)
    except OSError as error:
        # The swap failed mid-way. Put the old build back if we moved it, so the
        # install is never left without a launchable exe.
        if had_exe and not exe_path.exists() and backup.exists():
            try:
                backup.replace(exe_path)
            except OSError:
                pass
        raise UpdateError(f"Couldn't apply the staged update: {error}") from error

    state.pending = None
    return version if isinstance(version, str) else None


# ── network + staging (side-effecting) ──────────────────────────────────────


def fetch_manifest(
    url: str = VERSION_MANIFEST_URL, *, timeout: float = 5.0
) -> Manifest:
    """GET and validate the published manifest.

    Raises :class:`OSError` when the server can't be reached (so the caller can
    quietly skip on a bad connection) and :class:`UpdateError` when it responds
    with something that isn't a usable manifest."""
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        raise UpdateError(f"Manifest request returned {error.code}") from error
    except urllib.error.URLError as error:
        raise OSError(f"Couldn't reach the update server: {error.reason}") from error
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise UpdateError("Manifest response was not valid JSON") from error
    return parse_manifest(data)


def download(url: str, dest: Path, *, timeout: float = 30.0) -> None:
    """Stream ``url`` to ``dest`` (raising OSError on any transport failure)."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, open(
            dest, "wb"
        ) as handle:
            for chunk in iter(lambda: response.read(_HASH_CHUNK), b""):
                handle.write(chunk)
    except urllib.error.URLError as error:
        dest.unlink(missing_ok=True)
        raise OSError(f"Download failed: {getattr(error, 'reason', error)}") from error


def _staged_filename(version: str) -> str:
    # A dotfile-ish, version-stamped name so it's obviously an internal
    # artifact and two different staged versions never collide.
    safe = re.sub(r"[^0-9A-Za-z._-]", "_", version)
    return f".pending-{safe}.exe"


def stage_update(
    manifest: Manifest,
    install_dir: Path,
    state: UpdaterState,
    *,
    timeout: float = 30.0,
) -> None:
    """Download the manifest's build, verify it, and record it as pending.

    Downloads to a ``.part`` file first and only promotes it to the staged
    name once the checksum matches, so an interrupted or corrupt download can
    never be mistaken for a ready update. Mutates ``state.pending``; the caller
    persists it."""
    install_dir = Path(install_dir)
    staged = install_dir / _staged_filename(manifest.version)
    part = staged.with_suffix(staged.suffix + ".part")
    download(manifest.url, part, timeout=timeout)
    if not verify_file(part, manifest.sha256):
        part.unlink(missing_ok=True)
        raise UpdateError("Downloaded build failed its checksum -- discarded")
    part.replace(staged)
    state.pending = {
        "version": manifest.version,
        "filename": staged.name,
        "sha256": manifest.sha256,
        "mandatory": manifest.mandatory,
    }


@dataclass
class CheckResult:
    """A small record of what a background check did, for logging/tests."""

    checked: bool = False
    reachable: bool = False
    staged_version: str | None = None
    error: str | None = None
    notes: list[str] = field(default_factory=list)


def run_background_check(
    local_version: str,
    state: UpdaterState,
    install_dir: Path,
    *,
    url: str = VERSION_MANIFEST_URL,
    now: datetime | None = None,
    timeout: float = 30.0,
) -> CheckResult:
    """Fetch the manifest and stage a newer build if there is one.

    Stamps ``last_check`` on every *attempt* (even a failed one) to honor the
    throttle, and stages only when the published version is newer than both the
    installed build and any already-pending one. Never raises -- returns a
    :class:`CheckResult` and always leaves ``state`` in a saveable shape (the
    caller persists it)."""
    result = CheckResult()
    state.last_check = (now or _utc_now()).isoformat(timespec="seconds")
    result.checked = True
    try:
        manifest = fetch_manifest(url, timeout=timeout)
    except OSError as error:  # unreachable -- fine, we'll try again next window
        result.error = str(error)
        return result
    except UpdateError as error:  # reachable but served something unusable
        result.reachable = True
        result.error = str(error)
        return result

    result.reachable = True
    if not is_newer(manifest.version, local_version):
        result.notes.append(f"up to date (latest {manifest.version})")
        return result
    pending = state.pending or {}
    if pending.get("version") and not is_newer(
        manifest.version, str(pending["version"])
    ):
        result.notes.append(f"already staged {pending['version']}")
        return result
    try:
        stage_update(manifest, install_dir, state, timeout=timeout)
    except (OSError, UpdateError) as error:
        result.error = str(error)
        return result
    result.staged_version = manifest.version
    result.notes.append(f"staged {manifest.version}")
    return result
