from cozy_tui import App, Style
from cozy_tui._dock import dock_layout
from cozy_tui.widgets import Grid, HBox, Label, VBox


def make_app():
    # 80 cols x 24 rows
    return App(full=False, size="800x240", style=Style(fg="white", bg="black"))


def test_undocked_vbox_still_shrinks_to_fit_children():
    vbox = VBox(0, 0, gap=1)
    vbox.add(Label(0, 0, "a"))
    vbox.add(Label(0, 0, "bb"))
    assert vbox.natural_width(1) == 2
    assert vbox.natural_height(1) == 3  # 1 + 1 (gap) + 1


def test_undocked_hbox_still_shrinks_to_fit_children():
    hbox = HBox(0, 0, gap=1)
    hbox.add(Label(0, 0, "a"))
    hbox.add(Label(0, 0, "bb"))
    assert hbox.natural_width(1) == 4  # 1 + 1 (gap) + 2
    assert hbox.natural_height(1) == 1


def test_docked_vbox_reports_full_slice_not_shrink_to_fit():
    app = make_app()
    vbox = VBox(0, 0, gap=1)
    vbox.add(Label(0, 0, "a"))
    vbox.add(Label(0, 0, "bb"))
    app.dock(vbox, "fill")
    app._apply_docks()
    assert vbox.natural_width(app.SCALE) == app.cols
    assert vbox.natural_height(app.SCALE) == app.rows


def test_docked_hbox_reports_full_slice_not_shrink_to_fit():
    app = make_app()
    hbox = HBox(0, 0, gap=1)
    hbox.add(Label(0, 0, "a"))
    hbox.add(Label(0, 0, "bb"))
    app.dock(hbox, "fill")
    app._apply_docks()
    assert hbox.natural_width(app.SCALE) == app.cols
    assert hbox.natural_height(app.SCALE) == app.rows


def test_add_defaults_to_flex_zero():
    vbox = VBox(0, 0)
    label = Label(0, 0, "a")
    vbox.add(label)
    assert label._flex == 0


def test_add_stores_the_flex_weight():
    vbox = VBox(0, 0)
    label = Label(0, 0, "a")
    vbox.add(label, flex=2)
    assert label._flex == 2


def test_vbox_flex_child_grows_into_leftover_vertical_space():
    app = make_app()  # 80x24
    vbox = VBox(0, 0, gap=1)
    fixed = Label(0, 0, "fixed")  # natural height 1
    flexed = VBox(0, 0)
    flexed.add(Label(0, 0, "x"))  # natural height 1
    vbox.add(fixed)
    vbox.add(flexed, flex=1)
    app.dock(vbox, "fill")
    app._apply_docks()
    vbox.natural_height(app.SCALE)  # force _arrange()

    assert fixed.natural_height(1) == 1  # flex=0 sibling is untouched
    # leftover = 24 rows - 1 (fixed) - 1 (gap) - 1 (flexed's own natural) = 21
    assert flexed.natural_height(1) == 1 + 21
    assert fixed.natural_height(1) + 1 + flexed.natural_height(1) == app.rows


def test_vbox_distributes_leftover_space_by_flex_weight():
    app = make_app()  # 24 rows
    vbox = VBox(0, 0)
    a = VBox(0, 0)
    b = VBox(0, 0)
    a.add(Label(0, 0, "a"))  # natural height 1
    b.add(Label(0, 0, "b"))  # natural height 1
    vbox.add(a, flex=1)
    vbox.add(b, flex=2)
    app.dock(vbox, "fill")
    app._apply_docks()
    vbox.natural_height(app.SCALE)  # force _arrange()

    # pool = 24 - 2 (natural) = 22, split 1:2 -> 7/14 extra (+1 remainder to last)
    assert a.natural_height(1) == 8
    assert b.natural_height(1) == 16
    assert a.natural_height(1) + b.natural_height(1) == app.rows


def test_vbox_flex_child_does_not_shrink_below_natural_size_when_pool_is_negative():
    app = make_app()  # 24 rows
    vbox = VBox(0, 0)
    flexed = VBox(0, 0)
    flexed.add(Label(0, 0, "x"))
    for _ in range(30):
        vbox.add(Label(0, 0, "row"))
    vbox.add(flexed, flex=1)
    app.dock(vbox, "fill")
    app._apply_docks()
    vbox.natural_height(app.SCALE)  # force _arrange()

    # 30 fixed rows already exceed the 24-row target -> no negative growth, natural size kept
    assert flexed.natural_height(1) == 1


def test_vbox_without_flex_children_is_unaffected_by_docking():
    app = make_app()
    vbox = VBox(0, 0, gap=1)
    vbox.add(Label(0, 0, "a"))
    vbox.add(Label(0, 0, "bb"))
    app.dock(vbox, "fill")
    app._apply_docks()
    vbox.natural_height(app.SCALE)  # force _arrange()
    # vbox itself still reports the full docked slice (Step 1's contract)...
    assert vbox.natural_height(app.SCALE) == app.rows
    # ...but with no flex children, no leftover space is distributed to anyone.
    assert vbox.children[0].natural_height(1) == 1
    assert vbox.children[1].natural_height(1) == 1


def test_hbox_flex_child_grows_into_leftover_horizontal_space():
    app = make_app()  # 80x24
    hbox = HBox(0, 0, gap=1)
    fixed = Label(0, 0, "f")  # natural width 1
    flexed = HBox(0, 0)
    flexed.add(Label(0, 0, "x"))  # natural width 1
    hbox.add(fixed)
    hbox.add(flexed, flex=1)
    app.dock(hbox, "fill")
    app._apply_docks()
    hbox.natural_width(app.SCALE)  # force _arrange()

    assert fixed.natural_width(1) == 1  # flex=0 sibling is untouched
    # leftover = 80 cols - 1 (fixed) - 1 (gap) - 1 (flexed's own natural) = 77
    assert flexed.natural_width(1) == 1 + 77
    assert fixed.natural_width(1) + 1 + flexed.natural_width(1) == app.cols


def test_hbox_distributes_leftover_space_by_flex_weight():
    app = make_app()  # 80 cols
    hbox = HBox(0, 0)
    a = HBox(0, 0)
    b = HBox(0, 0)
    a.add(Label(0, 0, "a"))  # natural width 1
    b.add(Label(0, 0, "b"))  # natural width 1
    hbox.add(a, flex=1)
    hbox.add(b, flex=2)
    app.dock(hbox, "fill")
    app._apply_docks()
    hbox.natural_width(app.SCALE)  # force _arrange()

    # pool = 80 - 2 (natural) = 78, split 1:2 -> 26/52 extra
    assert a.natural_width(1) == 27
    assert b.natural_width(1) == 53
    assert a.natural_width(1) + b.natural_width(1) == app.cols


def test_hbox_flex_child_does_not_shrink_below_natural_size_when_pool_is_negative():
    app = make_app()  # 80 cols
    hbox = HBox(0, 0)
    flexed = HBox(0, 0)
    flexed.add(Label(0, 0, "x"))
    for _ in range(90):
        hbox.add(Label(0, 0, "c"))
    hbox.add(flexed, flex=1)
    app.dock(hbox, "fill")
    app._apply_docks()
    hbox.natural_width(app.SCALE)  # force _arrange()

    # 90 fixed columns already exceed the 80-col target -> no negative growth
    assert flexed.natural_width(1) == 1


def test_hbox_without_flex_children_is_unaffected_by_docking():
    app = make_app()
    hbox = HBox(0, 0, gap=1)
    hbox.add(Label(0, 0, "a"))
    hbox.add(Label(0, 0, "bb"))
    app.dock(hbox, "fill")
    app._apply_docks()
    hbox.natural_width(app.SCALE)  # force _arrange()
    assert hbox.natural_width(app.SCALE) == app.cols
    assert hbox.children[0].natural_width(1) == 1
    assert hbox.children[1].natural_width(1) == 2


def test_vbox_flex_and_gap_interact_correctly_with_multiple_flex_children():
    app = make_app()  # 24 rows
    vbox = VBox(0, 0, gap=2)
    fixed = Label(0, 0, "fixed")  # natural height 1
    flex_a = VBox(0, 0)
    flex_a.add(Label(0, 0, "a"))  # natural height 1
    flex_b = VBox(0, 0)
    flex_b.add(Label(0, 0, "b"))  # natural height 1
    vbox.add(fixed)
    vbox.add(flex_a, flex=1)
    vbox.add(flex_b, flex=1)
    app.dock(vbox, "fill")
    app._apply_docks()
    vbox.natural_height(app.SCALE)  # force _arrange()

    # total_gap = 2 * (3-1) = 4; pool = 24 - 4 - 3 (natural) = 17, split 1:1 -> 8/9
    assert flex_a.natural_height(1) == 9
    assert flex_b.natural_height(1) == 10
    assert (
        fixed.natural_height(1)
        + 2
        + flex_a.natural_height(1)
        + 2
        + flex_b.natural_height(1)
        == app.rows
    )


def test_hbox_distributes_leftover_space_among_three_weighted_children():
    app = make_app()  # 80 cols
    hbox = HBox(0, 0)
    a, b, c = HBox(0, 0), HBox(0, 0), HBox(0, 0)
    a.add(Label(0, 0, "a"))  # natural width 1
    b.add(Label(0, 0, "b"))  # natural width 1
    c.add(Label(0, 0, "c"))  # natural width 1
    hbox.add(a, flex=1)
    hbox.add(b, flex=2)
    hbox.add(c, flex=3)
    app.dock(hbox, "fill")
    app._apply_docks()
    hbox.natural_width(app.SCALE)  # force _arrange()

    # pool = 80 - 3 (natural) = 77, split 1:2:3 -> 12/25/40 extra
    assert a.natural_width(1) == 13
    assert b.natural_width(1) == 26
    assert c.natural_width(1) == 41
    assert a.natural_width(1) + b.natural_width(1) + c.natural_width(1) == app.cols


def test_vbox_flex_is_a_noop_exactly_at_zero_leftover_space():
    app = make_app()  # 24 rows
    vbox = VBox(0, 0)
    flexed = VBox(0, 0)
    flexed.add(Label(0, 0, "x"))  # natural height 1
    for _ in range(23):
        vbox.add(Label(0, 0, "row"))
    vbox.add(flexed, flex=1)
    app.dock(vbox, "fill")
    app._apply_docks()
    vbox.natural_height(app.SCALE)  # force _arrange()

    # 23 fixed rows + flexed's own natural row == 24 == target exactly -> zero pool
    assert flexed.natural_height(1) == 1


def test_vbox_flex_is_a_noop_when_undocked():
    vbox = VBox(0, 0)
    flexed = VBox(0, 0)
    flexed.add(Label(0, 0, "x"))
    vbox.add(Label(0, 0, "fixed"))
    vbox.add(flexed, flex=1)
    # never docked -> no target size, so flex has nothing to distribute
    assert flexed.natural_height(1) == 1
    assert vbox.natural_height(1) == 2


def test_grid_rejects_non_positive_cols():
    # cols is a divisor in _arrange(); zero/negative would crash the render loop
    # on the first draw, so it's rejected loudly at construction instead.
    import pytest

    for bad in (0, -1):
        with pytest.raises(ValueError):
            Grid(0, 0, cols=bad)


def test_grid_accepts_but_ignores_flex():
    app = make_app()
    grid = Grid(0, 0, cols=2)
    a = Label(0, 0, "a")
    b = Label(0, 0, "b")
    grid.add(a, flex=1)  # Grid doesn't implement flex distribution -- accepted, no-op
    grid.add(b)
    app.dock(grid, "fill")
    app._apply_docks()
    # renders without error; children keep their natural sizes either way
    assert a._flex == 1
    assert a.natural_width(1) == 1
    assert b.natural_width(1) == 1


def test_layout_contains_uses_the_docked_size():
    app = make_app()
    vbox = VBox(0, 0)
    vbox.add(Label(0, 0, "a"))
    app.dock(vbox, "fill")
    app._apply_docks()
    # far outside the single child's own tiny footprint, but inside the docked slice
    assert vbox.contains(app.cols - 1, app.rows - 1)


# ── padding ───────────────────────────────────────────────────────────────────


def test_padding_insets_children_and_grows_the_vbox():
    vbox = VBox(0, 0, padding=2)
    vbox.add(Label(0, 0, "a"))  # w 1
    vbox.add(Label(0, 0, "bb"))  # w 2
    vbox.natural_height(1)  # force _arrange()
    assert (vbox.children[0].x, vbox.children[0].y) == (2, 2)  # inset by (left, top)
    assert vbox.children[1].y == 3
    assert vbox.natural_width(1) == 2 + 2 + 2  # widest child + left + right
    assert vbox.natural_height(1) == 2 + 2 + 2  # two rows + top + bottom


def test_padding_two_tuple_is_vertical_horizontal():
    vbox = VBox(0, 0, padding=(1, 3))
    vbox.add(Label(0, 0, "a"))
    vbox.natural_height(1)
    assert (vbox.children[0].x, vbox.children[0].y) == (3, 1)
    assert vbox.natural_width(1) == 1 + 3 + 3
    assert vbox.natural_height(1) == 1 + 1 + 1


def test_padding_four_tuple_is_top_right_bottom_left():
    vbox = VBox(0, 0, padding=(1, 2, 3, 4))
    vbox.add(Label(0, 0, "a"))
    vbox.natural_height(1)
    assert (vbox.children[0].x, vbox.children[0].y) == (4, 1)  # left, top
    assert vbox.natural_width(1) == 1 + 4 + 2  # child + left + right
    assert vbox.natural_height(1) == 1 + 1 + 3  # child + top + bottom


def test_padding_insets_the_grid():
    grid = Grid(0, 0, cols=2, gap_x=1, gap_y=0, padding=2)
    for ch in "abcd":
        grid.add(Label(0, 0, ch))
    grid.natural_width(1)
    assert (grid.children[0].x, grid.children[0].y) == (2, 2)
    # 2 cols of width 1 + 1 gap between, plus left+right padding
    assert grid.natural_width(1) == (1 + 1 + 1) + 2 + 2


def test_padding_rejects_a_bad_shape():
    import pytest

    with pytest.raises(ValueError):
        VBox(0, 0, padding=(1, 2, 3))


# ── cross-axis alignment ──────────────────────────────────────────────────────


def test_vbox_align_center_centers_narrow_children_in_the_widest():
    vbox = VBox(0, 0, align="center")
    vbox.add(Label(0, 0, "a"))  # w 1
    vbox.add(Label(0, 0, "wiiide"))  # w 6
    vbox.natural_height(1)
    assert vbox.children[0].x == (6 - 1) // 2  # centered within the 6-wide band
    assert vbox.children[1].x == 0


def test_vbox_align_end_right_aligns_children():
    vbox = VBox(0, 0, align="end")
    vbox.add(Label(0, 0, "a"))  # w 1
    vbox.add(Label(0, 0, "wiiide"))  # w 6
    vbox.natural_height(1)
    assert vbox.children[0].x == 6 - 1
    assert vbox.children[1].x == 0


def test_vbox_align_stretch_grows_children_to_the_docked_width():
    app = make_app()  # 80 cols
    vbox = VBox(0, 0, align="stretch")
    inner = VBox(0, 0)  # honors dock_resize, unlike a bare Label
    inner.add(Label(0, 0, "x"))
    vbox.add(inner)
    app.dock(vbox, "fill")
    app._apply_docks()
    vbox.natural_width(app.SCALE)  # force _arrange()
    assert inner.natural_width(1) == app.cols


def test_hbox_align_center_centers_short_children_in_the_tallest():
    hbox = HBox(0, 0, align="center")
    tall = VBox(0, 0)
    for _ in range(3):
        tall.add(Label(0, 0, "t"))  # natural height 3
    hbox.add(Label(0, 0, "a"))  # height 1
    hbox.add(tall)
    hbox.natural_width(1)
    assert hbox.children[0].y == (3 - 1) // 2  # centered within the 3-tall band
    assert hbox.children[1].y == 0


# ── main-axis distribution (justify) ──────────────────────────────────────────


def _docked(layout, w, h):
    layout.dock_resize(w, h, 1)
    layout.natural_height(1)  # force _arrange() at the docked size
    return layout


def test_vbox_justify_center_offsets_the_whole_stack():
    vbox = VBox(0, 0)
    vbox.add(Label(0, 0, "a"))
    vbox.add(Label(0, 0, "b"))
    vbox._justify = "center"
    _docked(vbox, 10, 10)  # 2 rows of content, 8 rows of slack
    assert vbox.children[0].y == 4  # slack // 2
    assert vbox.children[1].y == 5


def test_vbox_justify_end_pushes_the_stack_to_the_bottom():
    vbox = VBox(0, 0, justify="end")
    vbox.add(Label(0, 0, "a"))
    vbox.add(Label(0, 0, "b"))
    _docked(vbox, 10, 10)
    assert vbox.children[0].y == 8
    assert vbox.children[1].y == 9


def test_vbox_justify_between_spreads_the_gap_edge_to_edge():
    vbox = VBox(0, 0, justify="between")
    vbox.add(Label(0, 0, "a"))
    vbox.add(Label(0, 0, "b"))
    _docked(vbox, 10, 10)  # slack 8 across one inter-child gap
    assert vbox.children[0].y == 0
    assert vbox.children[1].y == 9  # last child flush with the bottom row


def test_justify_is_a_noop_once_a_flex_child_eats_the_slack():
    app = make_app()  # 24 rows
    vbox = VBox(0, 0, justify="center")
    vbox.add(Label(0, 0, "a"))
    flexed = VBox(0, 0)
    flexed.add(Label(0, 0, "x"))
    vbox.add(flexed, flex=1)
    app.dock(vbox, "fill")
    app._apply_docks()
    vbox.natural_height(app.SCALE)
    # flex consumed all leftover space, so there's nothing for justify to shift.
    assert vbox.children[0].y == 0


def test_hbox_justify_center_offsets_along_the_horizontal_axis():
    hbox = HBox(0, 0, justify="center")
    hbox.add(Label(0, 0, "a"))  # w 1
    hbox.add(Label(0, 0, "b"))  # w 1
    hbox.dock_resize(10, 3, 1)
    hbox.natural_width(1)
    assert hbox.children[0].x == 4  # (10 - 2) // 2
    assert hbox.children[1].x == 5


def test_align_and_justify_reject_bad_values():
    import pytest

    with pytest.raises(ValueError):
        VBox(0, 0, align="middle")
    with pytest.raises(ValueError):
        VBox(0, 0, justify="spread")


# ── the properties are public, mutable, and reactive ──────────────────────────


def test_align_justify_padding_are_readable_properties():
    v = VBox(0, 0, align="center", justify="end", padding=(1, 2))
    assert v.align == "center"
    assert v.justify == "end"
    assert v.padding == (1, 2, 1, 2)  # normalized to (top, right, bottom, left)


def test_reassigning_align_re_arranges_next_measure():
    v = VBox(0, 0)
    v.add(Label(0, 0, "a"))  # w 1
    v.add(Label(0, 0, "wiiide"))  # w 6
    v.natural_height(1)
    assert v.children[0].x == 0  # start (default)
    v.align = "end"
    v.natural_height(1)  # setter re-dirtied, so this re-arranges
    assert v.children[0].x == 6 - 1


def test_padding_setter_normalizes_and_regrows():
    v = VBox(0, 0)
    v.add(Label(0, 0, "a"))
    v.natural_width(1)
    assert v.natural_width(1) == 1
    v.padding = 2  # int → all four sides
    assert v.padding == (2, 2, 2, 2)
    assert v.natural_width(1) == 1 + 2 + 2


def test_align_justify_setters_validate():
    import pytest

    v = VBox(0, 0)
    with pytest.raises(ValueError):
        v.align = "middle"
    with pytest.raises(ValueError):
        v.justify = "spread"


# ── a clamped dock band must not strand the layout collapsed ──────────────────


def test_a_docked_layout_reports_its_content_floor_not_a_clamped_target():
    # Regression: a dock band is sized min(natural_size, remaining_space), so a
    # layout pass made while the container is momentarily too small clamps the
    # band and dock_resize pins _target to that clamp. natural_* must report the
    # content floor, not the pinned value, or the band stays collapsed forever.
    v = VBox(0, 0)
    v.add(Label(0, 0, "row"))  # content height 1
    v.dock_resize(20, 0, 1)  # a band clamped to zero height
    assert v.natural_height(1) == 1  # content floor, not the pinned 0
    assert v.natural_width(1) == 20  # cross axis still reports the stretch

    h = HBox(0, 0)
    h.add(Label(0, 0, "wide"))  # content width 4
    h.dock_resize(0, 3, 1)  # a band clamped to zero width
    assert h.natural_width(1) == 4
    assert h.natural_height(1) == 3


def test_a_clamped_bottom_dock_recovers_after_the_screen_grows():
    # The same bug end-to-end through the real dock path: three stacked bands
    # that don't all fit at first, then do once the rectangle grows.
    header = VBox(0, 0)
    footer = VBox(0, 0)
    for _ in range(3):
        header.add(Label(0, 0, "x"))  # height 3
        footer.add(Label(0, 0, "x"))  # height 3
    bar = VBox(0, 0)
    bar.add(Label(0, 0, "x"))  # height 1
    items = [(header, "top", 0), (footer, "bottom", 0), (bar, "bottom", 0)]

    dock_layout(items, 0, 0, 80, 5, 1)  # only 5 rows: header+footer eat it all
    assert bar._dock_rect[3] == 0  # the bar is clamped to zero this pass

    dock_layout(items, 0, 0, 80, 20, 1)  # screen grows
    assert bar._dock_rect[3] == 1  # ...and the bar comes back, not stuck at 0
