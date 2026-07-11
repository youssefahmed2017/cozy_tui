"""Table: horizontal scrolling (viewport `width`, column-cursor auto-scroll,
scrollbar drag, and clipping so overflowing columns never bleed past the
table's own viewport into neighboring widgets)."""

from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.widgets import Label, Table


def make_app():
    return App(full=False, size="800x300", style=Style(fg="white", bg="black"))


def make_wide_table(width=None):
    """5 columns, 8 cells wide each, no border: total content width 44."""
    tbl = Table(0, 0, width=width, show_border=False)
    for i in range(5):
        tbl.add_column(f"C{i}", width=8)
    tbl.add_row(*[f"c{i}" for i in range(5)])
    return tbl


def test_default_width_none_matches_old_unclipped_behavior():
    tbl = make_wide_table(width=None)
    assert tbl.natural_width(1) == tbl._total_width() == 44
    assert not tbl._shows_h_bar()
    assert tbl.natural_height(1) == 2 + 1  # header rows + 1 data row, no bar row
    assert tbl.contains(43, tbl.abs_y)  # full unclipped width still hit-testable


def test_narrow_width_reports_viewport_and_shows_bar():
    tbl = make_wide_table(width=20)
    assert tbl.natural_width(1) == 20
    assert tbl._shows_h_bar()
    assert tbl.natural_height(1) == 2 + 1 + 1  # + the new scrollbar row
    assert tbl.contains(19, tbl.abs_y)
    assert not tbl.contains(20, tbl.abs_y)  # past the viewport, not the full content


def test_column_cursor_autoscrolls_into_view():
    tbl = make_wide_table(width=20)
    assert tbl._col_scroll_off == 0

    tbl.on_key(Key.RIGHT)  # -> col 1, fully within [0, 20)
    assert tbl._col_scroll_off == 0

    tbl.on_key(Key.RIGHT)  # -> col 2 (18..26), scrolls to keep its right edge visible
    assert tbl._col_scroll_off == 6

    tbl.on_key(Key.RIGHT)
    tbl.on_key(Key.RIGHT)  # -> col 4 (36..44), clamped to max scroll
    assert tbl._col_scroll_off == 24  # total_w(44) - viewport_w(20)

    tbl.on_key(Key.LEFT)
    tbl.on_key(Key.LEFT)
    tbl.on_key(Key.LEFT)
    tbl.on_key(Key.LEFT)  # back to col 0
    assert tbl._col_scroll_off == 0


def test_scrollbar_only_shown_when_narrower_than_content():
    app = make_app()
    tbl = make_wide_table(width=20)
    app.add(tbl)
    snap = app.snapshot()
    assert Table.THUMB in snap
    assert tbl._h_bar_row is not None

    app2 = make_app()
    fits = make_wide_table(width=None)
    app2.add(fits)
    snap2 = app2.snapshot()
    assert Table.THUMB not in snap2
    assert fits._h_bar_row is None


def test_dragging_the_h_scrollbar_thumb_scrolls():
    app = make_app()
    tbl = make_wide_table(width=20)
    app.add(tbl)
    app.snapshot()  # establishes _h_bar_row
    row = tbl._h_bar_row

    tbl.on_mouse_click(tbl.abs_x, row)  # press at the left of the bar
    assert tbl._col_scroll_off == 0
    tbl.on_mouse_drag(tbl.abs_x + 19, row)  # drag to the right end (viewport_w - 1)
    assert tbl._col_scroll_off == 24  # max scroll
    tbl.on_mouse_release(tbl.abs_x + 19, row)
    assert tbl._dragging_h_bar is False


def test_clicking_a_data_row_is_unaffected_by_the_new_bar_row():
    app = make_app()
    tbl = make_wide_table(width=20)
    tbl.add_row(*[f"d{i}" for i in range(5)])
    app.add(tbl)
    app.snapshot()

    tbl.on_mouse_click(tbl.abs_x, tbl._data_start_y() + 1)  # second data row
    assert tbl.selected_index == 1
    assert tbl._dragging_h_bar is False


def test_scrolled_columns_are_clipped_not_bled_into_neighbors():
    app = make_app()
    label = Label(20, 0, "NEIGHBOR")
    app.add(label)  # drawn first
    tbl = make_wide_table(width=20)
    app.add(tbl)  # drawn after -- would overwrite col 20+ without clipping

    tbl.on_key(Key.RIGHT)
    tbl.on_key(Key.RIGHT)  # col 2 -> _col_scroll_off == 6 (see clamp test above);
    # column 4 (unclamped, still drawn) would land at cols 30..38 without a clip
    snap = app.snapshot()
    assert "NEIGHBOR" in snap


def test_width_none_table_still_has_no_scroll_state_effect():
    tbl = make_wide_table(width=None)
    tbl.on_key(Key.RIGHT)
    tbl.on_key(Key.RIGHT)
    tbl.on_key(Key.RIGHT)
    tbl.on_key(Key.RIGHT)
    assert tbl._col_scroll_off == 0  # nothing to scroll when unconstrained


def test_clear_resets_col_scroll_off():
    tbl = make_wide_table(width=20)
    tbl.on_key(Key.RIGHT)
    tbl.on_key(Key.RIGHT)
    assert tbl._col_scroll_off != 0
    tbl.clear()
    assert tbl._col_scroll_off == 0
