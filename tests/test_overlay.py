from cozy_tui import App, Style
from cozy_tui.widgets import Box, Button


def make_app():
    return App(full=False, size="800x240", style=Style(fg="white", bg="black"))


def paint(app):
    """Mirror App.render() without touching the terminal."""
    app.clear()
    app._apply_docks()
    for w in app.widgets:
        w.draw(app)
    app._draw_overlays()


def base_with_button():
    app = make_app()
    btn = Button(1, 1, "Base")
    box = Box(0, 0, "400x100")
    box.add(btn)
    app.add(box)
    app.focus(btn)
    return app, btn


def dialog_with_ok():
    dialog = Box(0, 0, "300x100", title="Dialog")
    ok = Button(1, 1, "OK")
    dialog.add(ok)
    return dialog, ok


def test_open_marks_modal_and_moves_focus_in():
    app, base_btn = base_with_button()
    dialog, ok = dialog_with_ok()
    app.open_overlay(dialog)
    assert app._topmost_modal().widget is dialog
    assert app.focused is ok  # focus dived into the overlay


def test_modal_confines_focus_cycle():
    app, base_btn = base_with_button()
    dialog, ok = dialog_with_ok()
    app.open_overlay(dialog)
    assert app._collect_focusables() == [ok]  # base button excluded


def test_close_restores_previous_focus():
    app, base_btn = base_with_button()
    dialog, _ = dialog_with_ok()
    closed = []
    app.open_overlay(dialog, on_close=closed.append)
    app.close_overlay()
    assert app._topmost_modal() is None
    assert app.focused is base_btn
    assert closed == [dialog]


def test_center_positions_overlay_and_draws_on_top():
    app, _ = base_with_button()
    dialog, _ = dialog_with_ok()
    app.open_overlay(dialog, center=True)
    paint(app)
    w = dialog.natural_width(app.SCALE)
    h = dialog.natural_height(app.SCALE)
    dx = (app.cols - w) // 2
    dy = (app.rows - h) // 2
    assert dialog.x == dx and dialog.y == dy
    # Top-left border corner: "+" normally, "┏" when the dialog holds focus
    # (its OK button is focused), which is exactly what we expect here.
    assert app.buffer[dy][dx].char in ("+", "┏")


def test_backdrop_dims_background_cells():
    app, _ = base_with_button()
    dialog, _ = dialog_with_ok()
    app.open_overlay(dialog, dim=True, center=True)
    paint(app)
    # (0, 0) is outside the centered dialog, so it should be greyed by the scrim.
    assert app.buffer[0][0].style is app._backdrop_style


def test_non_modal_overlay_does_not_confine_focus():
    app, base_btn = base_with_button()
    tip = Box(0, 0, "100x40")  # decorative, non-focusable
    app.open_overlay(tip, modal=False, dim=False)
    assert app._topmost_modal() is None
    assert app.focused is base_btn
    assert app._collect_focusables() == [base_btn]


def test_stacked_modals_topmost_wins():
    app, _ = base_with_button()
    first, first_ok = dialog_with_ok()
    second, second_ok = dialog_with_ok()
    app.open_overlay(first)
    app.open_overlay(second)
    assert app._topmost_modal().widget is second
    assert app._collect_focusables() == [second_ok]
    app.close_overlay()
    assert app._topmost_modal().widget is first
    assert app.focused is first_ok  # focus restored to the first dialog
