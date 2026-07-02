"""Adapter from the Input widgets to cozy_tui's built-in clipboard backend.

`cozy_tui.clipboard.copy`/`paste` are already best-effort (never raise; `paste`
returns "" when unavailable), so these stay thin.
"""

from cozy_tui.clipboard import copy as _copy
from cozy_tui.clipboard import paste as _paste


def _clipboard_get() -> str:
    return _paste()


def _clipboard_set(text: str) -> None:
    if text:
        _copy(text)
