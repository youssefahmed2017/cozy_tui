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


def test_len_reports_item_count():
    lv = ListView(0, 0, ["a", "b"])
    assert len(lv) == 2


def test_clear_returns_self_so_calls_chain():
    lv = ListView(0, 0, ["a", "b"])
    result = lv.clear()
    assert result is lv
    assert len(lv) == 0


class _Card(str):
    """A str subclass: equal-valued instances still compare == (so remove()'s
    by-value lookup can't tell them apart) but are genuinely distinct objects
    (unlike two same-content string literals, which CPython may intern to the
    identical object), so `is` can verify exactly which one survived."""


def test_remove_by_value_can_remove_the_wrong_object_among_duplicates():
    # remove()'s value-based lookup is inherently ambiguous with duplicate
    # values -- it always takes the first match, regardless of which one is
    # actually selected. remove_at() is the unambiguous alternative.
    a, b, c = _Card("dup"), _Card("dup"), _Card("dup")
    lv = ListView(0, 0, [a, b, c])
    lv.selected_index = 2  # select c
    lv.remove("dup")  # matches by value -- removes a (the first), not c
    assert lv._items == [b, c]
    assert lv._items[0] is b and lv._items[1] is c  # a was removed, not c


def test_remove_at_removes_the_exact_selected_object():
    a, b, c = _Card("dup"), _Card("dup"), _Card("dup")
    lv = ListView(0, 0, [a, b, c])
    lv.selected_index = 2  # select c
    lv.remove_at(lv.selected_index)
    assert lv._items[0] is a and lv._items[1] is b  # c was removed, precisely
    assert len(lv) == 2


def test_remove_at_out_of_range_is_noop():
    lv = ListView(0, 0, ["a"])
    lv.remove_at(5)  # must not raise
    lv.remove_at(-1)
    assert lv._items == ["a"]
