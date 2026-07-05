"""Hover-to-highlight: moving the mouse over an item highlights it (moves the
cursor), like arrow-key navigation, without selecting/toggling/activating."""

from cozy_tui import App, Style
from cozy_tui.events import MouseMove
from cozy_tui.widgets import CheckList, ListView, RadioSet


def make_app():
    # The list widgets (ListView/CheckList/RadioSet) opt into mouse_moves
    # themselves, so the App no longer needs a global flag.
    return App(full=False, size="600x200", style=Style(fg="white", bg="black"))


def _hover_row(app, widget, row_index):
    # Hover-to-highlight is opt-in (off by default); enable it, then dispatch a
    # hover at the widget's absolute row for the given item index.
    widget.mouse_moves = True
    app._dispatch_mouse(MouseMove(widget.abs_x, widget.abs_y + row_index))


# ── ListView ──────────────────────────────────────────────────────────────────


def test_listview_hover_moves_cursor():
    app = make_app()
    lv = ListView(0, 0, ["a", "b", "c"])
    app.add(lv)
    _hover_row(app, lv, 2)
    assert lv.selected_index == 2
    assert lv.selected == "c"


def test_listview_hover_does_not_activate():
    app = make_app()
    lv = ListView(0, 0, ["a", "b", "c"])
    activated = []
    lv.on_click(activated.append)  # ListView fires click handler on activation
    app.add(lv)
    _hover_row(app, lv, 1)
    assert lv.selected_index == 1
    assert activated == []  # highlighted, not activated


def test_listview_hover_does_not_change_app_focus():
    app = make_app()
    lv = ListView(0, 0, ["a", "b"])
    app.add(lv)
    _hover_row(app, lv, 1)
    assert app.focused is None  # hover highlights but doesn't steal focus


# ── CheckList ─────────────────────────────────────────────────────────────────


def test_checklist_hover_moves_cursor_without_toggling():
    app = make_app()
    cl = CheckList(0, 0, ["x", "y", "z"])
    app.add(cl)
    _hover_row(app, cl, 2)
    assert cl.selected_index == 2
    assert cl.checked_values == []  # nothing toggled by hover


# ── RadioSet ──────────────────────────────────────────────────────────────────


def test_radioset_hover_moves_cursor_without_selecting():
    app = make_app()
    rs = RadioSet(0, 0, ["Small", "Medium", "Large"], selected=0)
    changes = []
    rs.on_change(changes.append)
    app.add(rs)
    _hover_row(app, rs, 2)
    assert rs._index == 2           # cursor highlight moved
    assert rs.selected == "Small"   # selection unchanged
    assert changes == []            # no on_change on hover


def test_radioset_hover_then_click_selects_hovered():
    app = make_app()
    rs = RadioSet(0, 0, ["Small", "Medium", "Large"], selected=0)
    app.add(rs)
    _hover_row(app, rs, 1)
    rs.on_mouse_click(rs.abs_x, rs.abs_y + 1)
    assert rs.selected == "Medium"
