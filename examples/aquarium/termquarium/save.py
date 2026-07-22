"""Versioned, file-based persistence for TermQuarium.

The format intentionally stays ordinary JSON.  A player can inspect, back up,
or share saves without a database or a proprietary container.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SAVE_VERSION = 1
APP_DIRECTORY_NAME = ".termquarium"


def data_dir(home: Path | None = None) -> Path:
    """Return the game's hidden home directory without creating it yet."""
    return (home or Path.home()) / APP_DIRECTORY_NAME


def saves_dir(home: Path | None = None) -> Path:
    return data_dir(home) / "saves"


def ensure_data_dirs(home: Path | None = None) -> Path:
    """Create the documented data layout and return the saves directory."""
    root = data_dir(home)
    (root / "saves").mkdir(parents=True, exist_ok=True)
    (root / "screenshots").mkdir(exist_ok=True)
    for filename in ("config.json", "settings.json"):
        path = root / filename
        if not path.exists():
            path.write_text("{}\n", encoding="utf-8")
    return root / "saves"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def format_relative_time(iso_timestamp: str, now: datetime | None = None) -> str:
    """ "2 hours ago" / "Yesterday" / "3 days ago" style, for the Load menu's
    cards -- a raw ISO timestamp doesn't let a player instantly recognize
    which aquarium they want, per the user's own mockup."""
    try:
        played = datetime.fromisoformat(iso_timestamp)
    except (TypeError, ValueError):
        return "unknown"
    if played.tzinfo is None:
        played = played.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    seconds = (now - played).total_seconds()
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return "just now"
    minutes = seconds / 60
    if minutes < 60:
        n = round(minutes)
        return f"{n} minute{'s' if n != 1 else ''} ago"
    hours = minutes / 60
    if hours < 24:
        n = round(hours)
        return f"{n} hour{'s' if n != 1 else ''} ago"
    days = int(hours // 24)
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"
    if days < 35:
        weeks = days // 7
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    if days < 365:
        months = days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = days // 365
    return f"{years} year{'s' if years != 1 else ''} ago"


def safe_filename(name: str) -> str:
    """Make a friendly save name safe on every supported filesystem."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip().rstrip(".")
    return cleaned or "Untitled Aquarium"


def save_path(name: str, home: Path | None = None) -> Path:
    return saves_dir(home) / f"{safe_filename(name)}.json"


def write_save(
    name: str,
    aquarium: dict[str, Any],
    home: Path | None = None,
    *,
    created: str | None = None,
) -> Path:
    """Write one save atomically and return its path.

    ``aquarium`` is the complete simulation state.  Its compact metadata is
    repeated at the top level so the load menu can render cards cheaply.
    ``created`` overrides the usual "keep the existing file's creation time,
    or stamp a fresh one" logic -- rename_save()/duplicate_save() pass the
    original save's ``created`` through explicitly, since a rename/copy
    isn't really a new aquarium even though it lands at a new path.
    """
    directory = ensure_data_dirs(home)
    path = directory / f"{safe_filename(name)}.json"
    now = _timestamp()
    existing = read_save(path) if path.exists() else None
    metadata = {
        "name": name.strip() or "Untitled Aquarium",
        "created": created or (existing or {}).get("metadata", {}).get("created", now),
        "last_played": now,
        "fish": len(aquarium.get("fish", [])),
        "money": aquarium.get("state", {}).get("money", 0),
        "food": aquarium.get("state", {}).get("food", 0),
        "day": aquarium.get("day", 0),
    }
    payload = {"version": SAVE_VERSION, "metadata": metadata, "aquarium": aquarium}
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    temporary.replace(path)
    return path


def read_save(path: Path) -> dict[str, Any]:
    """Read and validate a save, leaving migrations centralized for v2+."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or "metadata" not in payload
        or "aquarium" not in payload
    ):
        raise ValueError("Not a TermQuarium save")
    version = payload.get("version")
    if version != SAVE_VERSION:
        raise ValueError(f"Unsupported save version: {version}")
    return payload


def delete_save(path: Path) -> None:
    """Remove a save file. A no-op if it's already gone (e.g. deleted from
    outside the game between listing saves and clicking Delete)."""
    path.unlink(missing_ok=True)


def rename_save(path: Path, new_name: str, home: Path | None = None) -> Path:
    """Rename a save in place: same content and original creation time,
    just a new display name -- and, since the filename is derived from the
    name, a new underlying file. The old file is only removed once the new
    one is written successfully, and only if the name actually changed to a
    different path (renaming to the same name is a harmless no-op rather
    than a delete-then-recreate)."""
    payload = read_save(path)
    new_path = write_save(
        new_name,
        payload["aquarium"],
        home,
        created=payload["metadata"].get("created"),
    )
    if new_path != path:
        path.unlink(missing_ok=True)
    return new_path


def duplicate_save(path: Path, new_name: str, home: Path | None = None) -> Path:
    """Copy an existing save under a new name, leaving the original
    untouched -- same content and creation time (it's the same aquarium's
    history, just branched), so a duplicated save right after loading looks
    identical to its source until the player actually changes something."""
    payload = read_save(path)
    return write_save(
        new_name,
        payload["aquarium"],
        home,
        created=payload["metadata"].get("created"),
    )


def list_saves(home: Path | None = None) -> list[tuple[Path, dict[str, Any]]]:
    """Return valid saves newest-first, with only menu metadata exposed."""
    directory = ensure_data_dirs(home)
    cards = []
    for path in directory.glob("*.json"):
        try:
            payload = read_save(path)
            cards.append((path, payload["metadata"]))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return sorted(cards, key=lambda card: card[1].get("last_played", ""), reverse=True)


def _config_path(home: Path | None = None) -> Path:
    ensure_data_dirs(home)
    return data_dir(home) / "config.json"


def load_cloud_key(home: Path | None = None) -> str | None:
    """Return the Cloud Key set up for cloud saves on this machine, or
    None if it's never been configured (or was deliberately forgotten)."""
    try:
        config = json.loads(_config_path(home).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    key = config.get("cloud_key")
    return key if isinstance(key, str) and key else None


def store_cloud_key(key: str | None, home: Path | None = None) -> None:
    """Set (or, with key=None, forget) the Cloud Key in config.json.
    Written atomically like write_save(), so an interrupted write can't
    corrupt whatever else eventually lives alongside cloud_key here."""
    path = _config_path(home)
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        config = {}
    if key:
        config["cloud_key"] = key
    else:
        config.pop("cloud_key", None)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _achievements_path(home: Path | None = None) -> Path:
    ensure_data_dirs(home)
    return data_dir(home) / "achievements.json"


def load_unlocked_achievements(home: Path | None = None) -> set[str]:
    """Account-wide, like the Cloud Key -- lives in the game's data
    directory rather than any one save file, so a New Aquarium or a Load
    never resets what's already been earned."""
    try:
        data = json.loads(_achievements_path(home).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return set(data) if isinstance(data, list) else set()


def store_unlocked_achievements(ids: set[str], home: Path | None = None) -> None:
    """Written atomically like write_save()/store_cloud_key(). Sorted so the
    file diffs cleanly if a player ever pokes at it directly."""
    path = _achievements_path(home)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(sorted(ids), indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
