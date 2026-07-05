"""Every selection widget honors the on_click(widget) contract: on_click fires
with the widget itself on activation (keyboard Enter/Space or mouse click),
alongside the widget's own value-carrying callback (on_select/on_toggle/…)."""

from cozy_tui.events import Key
from cozy_tui.widgets import (CheckList, Dropdown, ListItem, ListView,
                              RadioSet, Table, Tree)


def test_listview_on_click_fires_widget_on_enter_and_click():
    lv = ListView(0, 0, ["a", "b", "c"])
    got = []
    lv.on_click(got.append)
    lv.on_key(Key.ENTER)
    assert got == [lv]  # the widget, not the value
    lv.on_mouse_click(0, lv.abs_y + 1)  # click row 1
    assert got == [lv, lv]


def test_checklist_on_click_fires_widget():
    cl = CheckList(0, 0, ["x", "y"])
    got = []
    cl.on_click(got.append)
    cl.on_key(Key.ENTER)  # toggles + activates
    assert got == [cl]
    cl.on_mouse_click(0, cl.abs_y + 1)
    assert got == [cl, cl]


def test_radioset_on_click_fires_widget():
    rs = RadioSet(0, 0, ["s", "m", "l"])
    got = []
    rs.on_click(got.append)
    rs.on_key(Key.ENTER)
    assert got == [rs]
    rs.on_mouse_click(0, rs.abs_y + 1)
    assert got == [rs, rs]


def test_table_on_click_fires_widget_on_enter():
    tbl = Table(0, 0)
    tbl.add_column("A", width=6)
    tbl.add_row("one")
    tbl.add_row("two")
    got = []
    tbl.on_click(got.append)
    tbl.on_key(Key.ENTER)
    assert got == [tbl]


def test_tree_on_click_fires_widget_on_enter():
    tree = Tree(0, 0)
    tree.add("root")
    got = []
    tree.on_click(got.append)
    tree.on_key(Key.ENTER)
    assert got == [tree]


def test_dropdown_on_click_fires_widget_when_item_chosen():
    dd = Dropdown(0, 0, [ListItem("Dark", "dark"), ListItem("Light", "light")])
    got = []
    dd.on_click(got.append)
    dd.on_key(Key.ENTER)  # open the popup
    dd._lv.on_key(Key.ENTER)  # choose the highlighted row
    assert got == [dd]


def test_on_click_still_carries_no_value_but_select_does():
    # on_click gets the widget; on_select carries the value — both fire.
    lv = ListView(0, 0, [ListItem("Python", "py"), ListItem("Rust", "rs")])
    clicks, selects = [], []
    lv.on_click(clicks.append)
    lv.on_select(selects.append)
    lv._move(1)  # cursor -> Rust
    lv.on_key(Key.ENTER)
    assert clicks == [lv]
    assert selects == ["rs"]
