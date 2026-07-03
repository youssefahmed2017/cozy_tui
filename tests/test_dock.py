from cozy_tui import App, Style
from cozy_tui.widgets import Box


def make_app():
    # 80 cols x 24 rows
    return App(full=False, size="800x240", style=Style(fg="white", bg="black"))


def test_docks_consume_a_shrinking_rectangle():
    app = make_app()
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
    app = make_app()
    main = Box(0, 0, "10x10", title="Main")
    app.dock(main, "fill")
    app._apply_docks()
    # A docked Box resizes to fill: footprint (interior + border) == screen.
    assert main.natural_width(app.SCALE) == app.cols
    assert main.natural_height(app.SCALE) == app.rows


def test_invalid_side_raises():
    app = make_app()
    try:
        app.dock(Box(0, 0, "10x10"), "middle")
    except ValueError:
        return
    raise AssertionError("expected ValueError for invalid dock side")
