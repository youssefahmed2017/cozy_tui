from cozy_tui.widgets import RadioItem, RadioSet
from cozy_tui.events import Key


def make():
    return RadioSet(0, 0, ["A", "B", "C"])


def test_first_option_selected_by_default():
    r = make()
    assert r.selected == "A"
    assert r.selected_index == 0


def test_selected_param_picks_initial():
    r = RadioSet(0, 0, ["A", "B", "C"], selected=2)
    assert r.selected == "C"


def test_arrow_moves_cursor_without_changing_selection():
    r = make()
    r.on_key(Key.DOWN)
    r.on_key(Key.DOWN)
    assert r._index == 2
    assert r.selected == "A"  # cursor moved, selection unchanged


def test_enter_selects_cursor_option_and_fires_change():
    r = make()
    changes = []
    r.on_change(changes.append)
    r.on_key(Key.DOWN)
    r.on_key(Key.ENTER)
    assert r.selected == "B"
    assert changes == ["B"]


def test_space_also_selects():
    r = make()
    r.on_key(Key.DOWN)
    r.on_key(" ")
    assert r.selected == "B"


def test_reselecting_same_option_does_not_fire_change():
    r = make()
    changes = []
    r.on_change(changes.append)
    r.on_key(Key.ENTER)  # already on A
    assert changes == []


def test_only_one_selected_at_a_time():
    r = make()
    r.select("B")
    assert r.selected == "B"
    r.select("C")
    assert r.selected == "C"
    assert r.selected_index == 2


def test_mouse_click_selects_row():
    r = make()
    changes = []
    r.on_change(changes.append)
    r.on_mouse_click(0, r.abs_y + 2)  # third row -> "C"
    assert r.selected == "C"
    assert changes == ["C"]


def test_radio_item_value_distinct_from_text():
    r = RadioSet(0, 0, [RadioItem("One", value=1), RadioItem("Two", value=2)])
    r.on_key(Key.DOWN)
    r.on_key(Key.ENTER)
    assert r.selected == 2


def test_marker_shows_selection_in_snapshot():
    from cozy_tui import App, Style

    app = App(full=False, size="300x60", style=Style(fg="white", bg="black"))
    app.add(RadioSet(0, 0, ["A", "B"], selected=1))
    lines = app.snapshot().split("\n")
    assert "( )" in lines[0] and "A" in lines[0]
    assert "(•)" in lines[1] and "B" in lines[1]


def test_home_end_move_cursor():
    r = make()
    r.on_key(Key.END)
    assert r._index == 2
    r.on_key(Key.HOME)
    assert r._index == 0
