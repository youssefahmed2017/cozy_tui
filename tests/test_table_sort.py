"""Table sorting: the programmatic .sort() method (previously untested) and
click-to-sort column headers (toggle direction on a repeat click, reset to
ascending on a different column, and the ▲/▼ header indicator)."""

import pytest

from cozy_tui import App, Style
from cozy_tui.widgets import Table


def make_app():
    return App(full=False, size="400x150", style=Style(fg="white", bg="black"))


def make_table(**kw):
    tbl = Table(2, 1, **kw)
    tbl.add_column("Name")
    tbl.add_column("Age", align="right")
    tbl.add_row("Charlie", "35")
    tbl.add_row("Alice", "30")
    tbl.add_row("Bob", "25")
    return tbl


def header_y(tbl) -> int:
    return tbl.abs_y + (1 if tbl.show_border else 0)


# ── programmatic .sort() ──────────────────────────────────────────────────────


def test_sort_by_column_name_ascending():
    tbl = make_table()
    tbl.sort("Name")
    assert [r.values[0] for r in tbl._rows] == ["Alice", "Bob", "Charlie"]


def test_sort_by_column_index_reverse():
    tbl = make_table()
    tbl.sort(0, reverse=True)
    assert [r.values[0] for r in tbl._rows] == ["Charlie", "Bob", "Alice"]


def test_sort_unknown_column_name_raises():
    tbl = make_table()
    with pytest.raises(ValueError):
        tbl.sort("Nonexistent")


def test_sort_keeps_the_selection_on_its_own_row():
    tbl = make_table()
    tbl._index = 0  # "Charlie" selected
    tbl.sort("Name")  # -> Alice, Bob, Charlie
    assert tbl.selected_row.values[0] == "Charlie"
    assert tbl._index == 2


def test_sort_updates_sort_col_and_reverse_state():
    tbl = make_table()
    tbl.sort("Age", reverse=True)
    assert tbl._sort_col == 1
    assert tbl._sort_reverse is True


# ── click-to-sort ─────────────────────────────────────────────────────────────


def test_clicking_a_header_sorts_ascending():
    app = make_app()
    tbl = make_table(show_border=True)
    app.add(tbl)
    app.snapshot()  # lays out columns

    tbl.on_mouse_click(tbl.abs_x + 2, header_y(tbl))  # inside "Name"
    assert tbl._sort_col == 0
    assert tbl._sort_reverse is False
    assert [r.values[0] for r in tbl._rows] == ["Alice", "Bob", "Charlie"]


def test_clicking_the_same_header_again_toggles_to_descending():
    app = make_app()
    tbl = make_table(show_border=True)
    app.add(tbl)
    app.snapshot()

    tbl.on_mouse_click(tbl.abs_x + 2, header_y(tbl))
    tbl.on_mouse_click(tbl.abs_x + 2, header_y(tbl))
    assert tbl._sort_reverse is True
    assert [r.values[0] for r in tbl._rows] == ["Charlie", "Bob", "Alice"]


def test_clicking_a_different_header_resets_to_ascending():
    app = make_app()
    tbl = make_table(show_border=True)
    app.add(tbl)
    app.snapshot()

    tbl.on_mouse_click(tbl.abs_x + 2, header_y(tbl))  # Name asc
    tbl.on_mouse_click(tbl.abs_x + 2, header_y(tbl))  # Name desc
    age_col_x = tbl.abs_x + next(
        x for x in range(20) if tbl._col_at(tbl.abs_x + x) == 1
    )
    tbl.on_mouse_click(age_col_x, header_y(tbl))
    assert tbl._sort_col == 1
    assert tbl._sort_reverse is False
    assert [r.values[1] for r in tbl._rows] == ["25", "30", "35"]


def test_clicking_a_data_row_does_not_sort():
    app = make_app()
    tbl = make_table(show_border=True)
    app.add(tbl)
    app.snapshot()

    data_row_y = tbl._data_start_y()
    tbl.on_mouse_click(tbl.abs_x + 2, data_row_y)
    assert tbl._sort_col is None
    assert tbl.selected_index == 0  # normal row-click selection still works


def test_header_click_is_a_noop_when_show_header_is_false():
    app = make_app()
    tbl = make_table(show_header=False, show_border=True)
    app.add(tbl)
    app.snapshot()
    tbl.on_mouse_click(tbl.abs_x + 2, tbl.abs_y + 1)
    assert tbl._sort_col is None


def test_col_at_maps_columns_correctly_with_border():
    app = make_app()
    tbl = make_table(show_border=True)
    app.add(tbl)
    app.snapshot()
    assert tbl._col_at(tbl.abs_x) is None  # the border char itself
    assert tbl._col_at(tbl.abs_x + 1) == 0
    assert tbl._col_at(tbl.abs_x + 100) is None  # far past the table


def test_arrow_indicator_appears_on_the_sorted_column():
    app = make_app()
    tbl = make_table(show_border=True)
    app.add(tbl)
    tbl.sort("Name")
    snap = app.snapshot()
    lines = snap.split("\n")
    header_line = lines[header_y(tbl)]
    assert "▲" in header_line

    tbl.sort("Name", reverse=True)
    snap = app.snapshot()
    header_line = snap.split("\n")[header_y(tbl)]
    assert "▼" in header_line


def test_arrow_does_not_clobber_the_column_title():
    app = make_app()
    tbl = make_table(show_border=True)
    app.add(tbl)
    tbl.sort("Name")
    snap = app.snapshot()
    header_line = snap.split("\n")[header_y(tbl)]
    assert "Name" in header_line


def test_clear_resets_sort_state():
    tbl = make_table()
    tbl.sort("Name")
    assert tbl._sort_col is not None
    tbl.clear()
    assert tbl._sort_col is None
    assert tbl._sort_reverse is False
