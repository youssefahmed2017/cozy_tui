"""Regression tests for the kanban example (examples/kanban/kanban.py)."""

import importlib.util
import pathlib

from cozy_tui import App
from cozy_tui.events import Key
from cozy_tui.widgets import ListView

_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "examples" / "kanban" / "kanban.py"
)
_spec = importlib.util.spec_from_file_location("kanban_app", _PATH)
k = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(k)


class _Card(str):
    """A str subclass: equal-valued instances still compare == (so a
    value-based lookup can't tell them apart) but are genuinely distinct
    objects (unlike two same-content string literals, which CPython may
    intern to the identical object), so `is` can verify exactly which
    card instance survived an operation."""


def _headless_app(monkeypatch):
    """Boot the real main(), never letting app.run() block on a real terminal."""
    captured = {}
    monkeypatch.setattr(App, "run", lambda self: captured.__setitem__("app", self))
    k.main()
    return captured["app"]


def _list_views(app):
    """The three column ListViews, in To Do / Doing / Done order -- each sits
    inside its own Box, added to the app in that order (see kanban.py)."""
    return [
        next(c for c in box.children if isinstance(c, ListView))
        for box in app.widgets
        if hasattr(box, "children")
    ]


def test_move_relocates_the_exact_selected_card_even_with_a_duplicate_name(
    monkeypatch,
):
    # Regression: move() used ListView.remove()/set(), which match by
    # *value* -- with two cards sharing a name, they could act on the first
    # matching card instead of the one actually selected/highlighted.
    app = _headless_app(monkeypatch)
    todo, doing, done = _list_views(app)

    original = todo.selected  # "Design overlay API", first in To Do
    duplicate = _Card(original)
    todo.append(duplicate)
    todo.selected_index = len(todo) - 1  # select the duplicate, not the original

    app.focus(todo)
    app._key_handlers[Key.RIGHT]()  # move right, into Doing

    assert any(x is original for x in todo._items)  # the original stayed put
    assert not any(x is duplicate for x in todo._items)
    assert doing._items[-1] is duplicate  # the selected card moved, not the original


def test_delete_card_removes_the_exact_selected_card_even_with_a_duplicate_name(
    monkeypatch,
):
    app = _headless_app(monkeypatch)
    todo, _doing, _done = _list_views(app)

    original = todo.selected
    duplicate = _Card(original)
    todo.append(duplicate)
    todo.selected_index = len(todo) - 1  # the duplicate, not the original

    app.focus(todo)
    app._key_handlers["d"]()

    assert any(x is original for x in todo._items)  # the original stayed put
    assert not any(x is duplicate for x in todo._items)


def test_add_card_selects_the_newly_added_card(monkeypatch):
    app = _headless_app(monkeypatch)
    todo, _doing, _done = _list_views(app)
    before = len(todo)

    app.focus(todo)
    app._key_handlers["a"]()  # add_card() also opens a rename prompt

    assert len(todo) == before + 1
    assert todo.selected_index == len(todo) - 1
