from cozy_tui import App, Style
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
