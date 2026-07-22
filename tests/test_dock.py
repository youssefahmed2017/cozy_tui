from cozy_tui import App, Style
from cozy_tui.testing import Harness
from cozy_tui.widgets import Box, Label


def make_ui():
    # 80 cols x 24 rows
    return Harness(App(full=False, size="800x240", style=Style(fg="white", bg="black")))


def test_docks_consume_a_shrinking_rectangle():
    ui = make_ui()
    app = ui.app
    header = Box(0, 0, "10x10", title="Header")
    status = Box(0, 0, "10x10", title="Status")
    sidebar = Box(0, 0, "180x10", title="Side")
    main = Box(0, 0, "10x10", title="Main")

    app.dock(header, "top")
    app.dock(status, "bottom")
    app.dock(sidebar, "left")
    app.dock(main, "fill")
    app._apply_docks()

    # header/status span full width at top and bottom
    assert header._dock_rect == (0, 0, 80, 3)
    assert status._dock_rect == (0, 21, 80, 3)
    # sidebar spans only the band between them
    hx, hy, hw, hh = sidebar._dock_rect
    assert (hx, hy) == (0, 3)
    assert hh == 18
    # main fills the remainder
    mx, my, mw, mh = main._dock_rect
    assert (mx, my) == (hw, 3)
    assert mw == 80 - hw
    assert mh == 18


def test_fill_box_grows_to_its_slice():
    ui = make_ui()
    app = ui.app
    main = Box(0, 0, "10x10", title="Main")
    app.dock(main, "fill")
    app._apply_docks()
    # A docked Box resizes to fill: footprint (interior + border) == screen.
    assert main.natural_width(app.SCALE) == app.cols
    assert main.natural_height(app.SCALE) == app.rows


def test_bottom_docked_box_with_wrapping_content_converges_and_stays_stable():
    # Regression: a "top"/"bottom"-docked Box's natural_height() is queried
    # to reserve a dock band *before* dock_resize() runs, using whatever
    # self.width currently is (possibly still the tiny constructor value, on
    # the very first frame). A lapping (word-wrapping) child whose wrap
    # count is computed from that too-narrow width used to produce a huge
    # reservation that got baked into self.height by dock_resize() -- and
    # then *stayed* baked in forever, because that inflated self.height was
    # itself used as next frame's floor, even once self.width had converged
    # to the real (wide) terminal width and the wrap count would otherwise
    # have been small.
    ui = make_ui()  # 80x24
    app = ui.app
    footer = Box(0, 0, "10x10", title="keys", border="rounded")
    hint = Label(1, 1, "word " * 40)  # wraps to a handful of lines, not one huge count
    footer.add(hint)
    app.dock(footer, "bottom")

    heights = []
    for _ in range(4):
        app._apply_docks()
        ui.compose()
        heights.append(footer.height)

    # Stable from the very first frame -- no transient spike, no runaway growth.
    assert len(set(heights)) == 1
    assert heights[0] < 200  # sanity bound well under the old runaway (2000px+)
    # The bottom border must actually be visible (not pushed off-screen).
    x, y, w, h = footer._bounds
    assert 0 <= y + h - 1 < app.rows


def test_fill_docked_box_still_grows_to_its_slice_with_wrapping_content():
    # A "fill" dock assigns self.height directly, bypassing natural_height()
    # entirely -- confirms that path (unlike "bottom") is unaffected and a
    # fill box still fills the screen even with a wrapping child inside.
    ui = make_ui()  # 80x24
    app = ui.app
    main = Box(0, 0, "10x10", title="Main")
    main.add(Label(1, 1, "word " * 40))
    app.dock(main, "fill")
    for _ in range(3):
        app._apply_docks()
        ui.compose()
    assert main.natural_width(app.SCALE) == app.cols
    assert main.natural_height(app.SCALE) == app.rows


def test_invalid_side_raises():
    ui = make_ui()
    app = ui.app
    try:
        app.dock(Box(0, 0, "10x10"), "middle")
    except ValueError:
        return
    raise AssertionError("expected ValueError for invalid dock side")
