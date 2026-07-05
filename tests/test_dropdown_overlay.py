from cozy_tui import App, Style
from cozy_tui.events import Key
from cozy_tui.widgets import Dropdown, ListItem


def make_app_with_dropdown():
    app = App(full=False, size="800x240", style=Style(fg="white", bg="black"))
    dd = Dropdown(2, 2, [ListItem("A", "a"), ListItem("B", "b"), ListItem("C", "c")])
    app.add(dd)
    app.focus(dd)
    # One render pass so the dropdown captures its App reference (dd._app).
    app.clear()
    app._apply_docks()
    for w in app.widgets:
        w.draw(app)
    return app, dd


def test_opening_pushes_popup_as_modal_overlay():
    app, dd = make_app_with_dropdown()
    dd.on_key(Key.ENTER)
    assert dd._open
    assert app._topmost_modal() is not None
    assert app._topmost_modal().widget is dd._lv
    assert app.focused is dd._lv  # focus dived into the list


def test_header_is_single_row_no_reflow():
    _, dd = make_app_with_dropdown()
    assert dd.natural_height(1) == 1
    dd.on_key(Key.ENTER)  # even while open, the header stays one row
    assert dd.natural_height(1) == 1


def test_enter_selects_confirms_and_restores_focus():
    app, dd = make_app_with_dropdown()
    dd.on_key(Key.ENTER)  # open
    app.focused.on_key(Key.DOWN)  # list moves to "B"
    app.focused.on_key(Key.ENTER)  # confirm
    assert not dd._open
    assert app._topmost_modal() is None
    assert app.focused is dd  # focus restored to the dropdown
    assert dd.selected == "b"


def test_row_click_selects_and_closes():
    app, dd = make_app_with_dropdown()
    dd.on_key(Key.ENTER)
    lv = dd._lv
    lv.on_mouse_click(lv.abs_x, lv.abs_y + 2)  # third row -> "C"
    assert not dd._open
    assert dd.selected == "c"
    assert app.focused is dd


def test_escape_cancels_without_changing_selection():
    app, dd = make_app_with_dropdown()
    dd.set("a")
    dd.on_key(Key.ENTER)
    app.focused.on_key(Key.DOWN)  # highlight moves, but not confirmed
    app.close_overlay(dd._lv)  # what App does on Esc / click-outside
    assert not dd._open
    assert app.focused is dd
    assert dd.selected == "a"  # unchanged


def test_on_select_callback_fires_with_value():
    app, dd = make_app_with_dropdown()
    got = []
    dd.on_select(got.append)
    dd.on_key(Key.ENTER)
    app.focused.on_key(Key.DOWN)
    app.focused.on_key(Key.ENTER)
    assert got == ["b"]
