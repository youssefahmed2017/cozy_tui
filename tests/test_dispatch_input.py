"""App._dispatch_input: the single routing chain shared by run()'s own loop
and any other frontend that already has a parsed event (see
_internal/ctui_web/live_server.py) and wants App's normal input semantics
without going through read_key()/a real terminal."""

from cozy_tui import App, Style
from cozy_tui.events import Key, MouseClick
from cozy_tui.testing import Harness
from cozy_tui.widgets import Button, Input, ScrollView


def make_ui(**kw):
    return Harness(
        App(full=False, size="400x100", style=Style(fg="white", bg="black"), **kw)
    )


def test_global_key_handler_returning_quit_sets_should_quit():
    ui = make_ui()
    app = ui.app
    app.on_key("q", lambda: "quit")
    ui.press("q")
    assert app._should_quit is True


def test_global_key_handler_not_quitting_leaves_running():
    ui = make_ui()
    app = ui.app
    calls = []
    app.on_key("q", lambda: calls.append(1))
    ui.press("q")
    assert calls == [1]
    assert app._should_quit is False


def test_tab_and_shift_tab_cycle_focus():
    ui = make_ui()
    app = ui.app
    b1 = Button(0, 0, "One")
    b2 = Button(0, 2, "Two")
    app.add(b1)
    app.add(b2)
    app.focus(b1)

    ui.press(Key.TAB)
    assert app.focused is b2

    ui.press(Key.SHIFT_TAB)
    assert app.focused is b1


def test_modal_esc_closes_it_when_close_on_escape():
    ui = make_ui()
    app = ui.app
    dlg = Button(0, 0, "dlg")
    app.open_overlay(dlg, close_on_escape=True)
    assert app._topmost_modal() is not None

    ui.press(Key.ESC)
    assert app._topmost_modal() is None


def test_modal_f12_toggles_devtools_instead_of_closing_it():
    # F12 must always reach Cozy DevTools (App.toggle_devtools is a no-op
    # without debug=True) rather than being treated as a second "close this
    # modal" key -- otherwise F12 could never open DevTools while any modal
    # (ConfirmDialog, FilePicker, CommandPalette, ...) happens to be open.
    ui = make_ui(debug=True)
    app = ui.app
    dlg = Button(0, 0, "dlg")
    app.open_overlay(dlg, close_on_escape=True)

    ui.press(Key.F12)
    assert app._topmost_modal() is not None  # the modal is still open
    assert app._devtools_panel is not None  # and DevTools opened

    ui.press(Key.F12)
    assert app._devtools_panel is None  # toggles closed again
    assert app._topmost_modal() is not None


def test_modal_confines_tab_to_itself():
    ui = make_ui()
    app = ui.app
    outside = Button(0, 0, "outside")
    app.add(outside)
    dlg_button = Button(0, 0, "in-modal")
    app.open_overlay(dlg_button, close_on_escape=True)
    assert app.focused is dlg_button

    ui.press(Key.TAB)
    assert app.focused is dlg_button  # only one focusable in the modal


def test_ctrl_c_quits_when_focused_widget_has_no_cursor():
    ui = make_ui()
    app = ui.app
    b = Button(0, 0, "Go")
    app.add(b)
    app.focus(b)
    ui.press(Key.CTRL_C)
    assert app._should_quit is True


def test_ctrl_c_delegates_to_focused_cursor_widget_instead_of_quitting():
    ui = make_ui()
    app = ui.app
    inp = Input(0, 0, 20)
    inp.text = "hello"
    app.add(inp)
    app.focus(inp)
    ui.press(Key.CTRL_C)
    assert app._should_quit is False  # Ctrl+C copies instead of quitting


def test_ctrl_c_runs_a_registered_handler_instead_of_quitting():
    ui = make_ui()
    app = ui.app
    calls = []
    app.on_key(Key.CTRL_C, lambda: calls.append(1))
    b = Button(0, 0, "Go")
    app.add(b)
    app.focus(b)

    ui.press(Key.CTRL_C)

    assert calls == [1]
    assert app._should_quit is False


def test_ctrl_c_registered_handler_can_still_request_quit():
    ui = make_ui()
    app = ui.app
    app.on_key(Key.CTRL_C, lambda: "quit")
    ui.press(Key.CTRL_C)
    assert app._should_quit is True


def test_ctrl_c_registered_handler_also_runs_inside_a_modal():
    ui = make_ui()
    app = ui.app
    calls = []
    app.on_key(Key.CTRL_C, lambda: calls.append(1))
    dlg_button = Button(0, 0, "in-modal")
    app.open_overlay(dlg_button)

    ui.press(Key.CTRL_C)

    assert calls == [1]
    assert app._should_quit is False


def test_ctrl_c_still_quits_inside_a_modal_with_no_handler_registered():
    ui = make_ui()
    app = ui.app
    dlg_button = Button(0, 0, "in-modal")
    app.open_overlay(dlg_button)

    ui.press(Key.CTRL_C)

    assert app._should_quit is True


def test_ctrl_c_still_copies_in_a_focused_cursor_widget_even_with_a_handler_registered():
    ui = make_ui()
    app = ui.app
    calls = []
    app.on_key(Key.CTRL_C, lambda: calls.append(1))
    inp = Input(0, 0, 20)
    inp.text = "hello"
    app.add(inp)
    app.focus(inp)

    ui.press(Key.CTRL_C)

    assert calls == []  # copy wins, the registered handler never runs
    assert app._should_quit is False


def test_scroll_key_routes_to_scrollable_focused_widget():
    ui = make_ui()
    app = ui.app
    view = ScrollView(0, 0, "300x50")
    for i in range(20):
        view.add(Button(0, i, f"row {i}"))
    app.add(view)
    app.focus(view)
    app._compose()  # establish max_scroll etc.

    ui.press(Key.SCROLL_DOWN)
    assert view._scroll > 0


def test_scroll_wheel_prefers_the_hovered_scrollable_widget_over_focus():
    # A ScrollView full of focusable children (e.g. Buttons) can never
    # become focused itself -- a focusable container always defers Tab (and
    # open_overlay()'s auto-focus) to its focusable descendants, see
    # App._focusables_in() -- so the wheel has to be able to reach it some
    # other way, or it can never be scrolled with the mouse at all in that
    # shape. Whatever's actually hovered wins over whatever merely holds
    # keyboard focus.
    ui = make_ui()
    app = ui.app
    view = ScrollView(0, 0, "300x50")
    for i in range(20):
        view.add(Button(0, i, f"row {i}"))
    app.add(view)
    other = Button(0, 60, "Elsewhere")
    app.add(other)
    app.focus(other)  # focus is on something else entirely
    app._compose()

    ui.hover(view)
    ui.press(Key.SCROLL_DOWN)

    assert view._scroll > 0
    assert app.focused is other  # hovering to scroll never steals focus


def test_scroll_wheel_finds_a_scrollable_ancestor_when_hovering_a_child():
    # Hovering exactly over one of the ScrollView's own children (its
    # deepest focusable descendant, so hit-testing lands there first, not on
    # the ScrollView itself) must still scroll the ScrollView -- walks up
    # the parent chain to find it.
    ui = make_ui()
    app = ui.app
    view = ScrollView(0, 0, "300x50")
    buttons = [Button(0, i, f"row {i}") for i in range(20)]
    for b in buttons:
        view.add(b)
    app.add(view)
    app._compose()

    ui.hover(buttons[0])
    ui.press(Key.SCROLL_DOWN)

    assert view._scroll > 0


def test_mouse_event_routes_through_dispatch_mouse():
    ui = make_ui()
    app = ui.app
    b = Button(2, 2, "Go")
    app.add(b)
    clicks = []
    b.on_click(lambda w: clicks.append(w))

    ui.click((3, 2))
    assert clicks == [b]
