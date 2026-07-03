from cozy_tui.widgets import ListView


def test_set_item_replaces_in_place_and_keeps_selection():
    lv = ListView(0, 0, ["a", "b", "c"])
    lv.set("b")  # select index 1
    assert lv.selected_index == 1
    lv.set_item(1, "B!")
    assert lv._items[1] == "B!"
    assert lv.selected_index == 1  # selection unchanged
    assert lv.selected == "B!"


def test_set_item_out_of_range_is_noop():
    lv = ListView(0, 0, ["a"])
    lv.set_item(5, "x")  # must not raise
    lv.set_item(-1, "y")
    assert lv._items == ["a"]


def test_set_item_refreshes_width_cache():
    lv = ListView(0, 0, ["a", "bb"])
    _ = lv.natural_width(1)  # populate the width cache
    lv.set_item(0, "a very long card title")
    # width must grow to fit the renamed item
    assert lv.natural_width(1) >= len("a very long card title")
