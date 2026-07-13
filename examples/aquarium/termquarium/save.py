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


def write_save(name: str, aquarium: dict[str, Any], home: Path | None = None) -> Path:
    """Write one save atomically and return its path.

    ``aquarium`` is the complete simulation state.  Its compact metadata is
    repeated at the top level so the load menu can render cards cheaply.
    """
    directory = ensure_data_dirs(home)
    path = directory / f"{safe_filename(name)}.json"
    now = _timestamp()
    existing = read_save(path) if path.exists() else None
    metadata = {
        "name": name.strip() or "Untitled Aquarium",
        "created": (existing or {}).get("metadata", {}).get("created", now),
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
