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


def test_select_index_moves_the_selected_row_and_clamps():
    tbl = Table(0, 0)
    tbl.add_column("C0")
    for i in range(5):
        tbl.add_row(f"r{i}")

    tbl.select_index(3)
    assert tbl.selected_index == 3
    assert tbl.selected_row.values == ("r3",)

    tbl.select_index(99)  # out of range -- clamps to the last row
    assert tbl.selected_index == 4

    tbl.select_index(-5)  # clamps to the first row
    assert tbl.selected_index == 0


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


# ── zebra striping & hover (polish) ──────────────────────────────────────────


def _bg(app, col, row):
    from cozy_tui.ansi import resolve_rgb

    return resolve_rgb(app.buffer[row][col].style.raw_bg)


def make_ui_table(**kw):
    from cozy_tui.testing import Harness

    app = make_app()
    tbl = Table(0, 0, **kw)
    tbl.add_column("Name")
    tbl.add_column("Qty", align="right")
    for i in range(6):
        tbl.add_row(f"item{i}", str(i))
    app.add(tbl)
    return Harness(app), tbl


def test_zebra_is_off_by_default():
    ui, tbl = make_ui_table()
    ui.compose()
    ds = tbl._data_start_y()
    # every plain row shares the same (bare) background
    assert _bg(ui.app, 2, ds) == _bg(ui.app, 2, ds + 1)


def test_zebra_tints_only_the_odd_rows():
    ui, tbl = make_ui_table(zebra=True)
    ui.compose()
    ds = tbl._data_start_y()
    even = _bg(ui.app, 2, ds)  # row 0: untouched base
    odd = _bg(ui.app, 2, ds + 1)  # row 1: tinted stripe
    assert odd is not None and odd != even
    assert _bg(ui.app, 2, ds + 2) == even  # row 2 back to base
    assert _bg(ui.app, 2, ds + 3) == odd  # row 3 tinted again


def test_hover_opts_into_mouse_moves():
    _ui, tbl = make_ui_table(hover=True)
    assert tbl.mouse_moves is True
    _ui2, plain = make_ui_table()
    assert getattr(plain, "mouse_moves", False) is False


def test_hover_highlights_the_row_under_the_mouse():
    ui, tbl = make_ui_table(hover=True, zebra=True)
    ds = tbl._data_start_y()
    ui.hover((3, ds + 2))
    assert tbl._hover_index == 2
    hovered = _bg(ui.app, 2, ds + 2)
    plain = _bg(ui.app, 2, ds)
    assert hovered is not None and hovered != plain  # washed toward the accent


def test_hover_clears_when_the_mouse_leaves():
    ui, tbl = make_ui_table(hover=True)
    ds = tbl._data_start_y()
    ui.hover((3, ds + 1))
    assert tbl._hover_index == 1
    ui.hover((5, ds + 999))  # below every row
    assert tbl._hover_index is None


def test_selection_outranks_hover_and_zebra():
    from cozy_tui.ansi import resolve_rgb
    from cozy_tui.style import selection_style

    ui, tbl = make_ui_table(hover=True, zebra=True)
    ui.app.focus(tbl)
    tbl._index = 1  # select the row that would otherwise be a zebra stripe
    tbl._hover_index = 1  # and hover it
    ui.compose()
    ds = tbl._data_start_y()
    assert _bg(ui.app, 2, ds + 1) == resolve_rgb(selection_style().raw_bg)
