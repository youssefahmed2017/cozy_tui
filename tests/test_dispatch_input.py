"""App._dispatch_input: the single routing chain shared by run()'s own loop
and any other frontend that already has a parsed event (see
_internal/ctui_web/live_server.py) and wants App's normal input semantics
without going through read_key()/a real terminal."""

from cozy_tui import App, Style
from cozy_tui.events import Key, MouseClick
from cozy_tui.widgets import Button, Input, ScrollView


def make_app(**kw):
    return App(full=False, size="400x100", style=Style(fg="white", bg="black"), **kw)


def test_global_key_handler_returning_quit_sets_should_quit():
    app = make_app()
    app.on_key("q", lambda: "quit")
    app._dispatch_input("q")
    assert app._should_quit is True


def test_global_key_handler_not_quitting_leaves_running():
    app = make_app()
    calls = []
    app.on_key("q", lambda: calls.append(1))
    app._dispatch_input("q")
    assert calls == [1]
    assert app._should_quit is False


def test_tab_and_shift_tab_cycle_focus():
    app = make_app()
    b1 = Button(0, 0, "One")
    b2 = Button(0, 2, "Two")
    app.add(b1)
    app.add(b2)
    app.focus(b1)

    app._dispatch_input(Key.TAB)
    assert app.focused is b2

    app._dispatch_input(Key.SHIFT_TAB)
    assert app.focused is b1


def test_modal_esc_closes_it_when_close_on_escape():
    app = make_app()
    dlg = Button(0, 0, "dlg")
    app.open_overlay(dlg, close_on_escape=True)
    assert app._topmost_modal() is not None

    app._dispatch_input(Key.ESC)
    assert app._topmost_modal() is None


def test_modal_f12_also_closes_it():
    app = make_app()
    dlg = Button(0, 0, "dlg")
    app.open_overlay(dlg, close_on_escape=True)

    app._dispatch_input(Key.F12)
    assert app._topmost_modal() is None


def test_modal_confines_tab_to_itself():
    app = make_app()
    outside = Button(0, 0, "outside")
    app.add(outside)
    dlg_button = Button(0, 0, "in-modal")
    app.open_overlay(dlg_button, close_on_escape=True)
    assert app.focused is dlg_button

    app._dispatch_input(Key.TAB)
    assert app.focused is dlg_button  # only one focusable in the modal


def test_ctrl_c_quits_when_focused_widget_has_no_cursor():
    app = make_app()
    b = Button(0, 0, "Go")
    app.add(b)
    app.focus(b)
    app._dispatch_input(Key.CTRL_C)
    assert app._should_quit is True


def test_ctrl_c_delegates_to_focused_cursor_widget_instead_of_quitting():
    app = make_app()
    inp = Input(0, 0, 20)
    inp.text = "hello"
    app.add(inp)
    app.focus(inp)
    app._dispatch_input(Key.CTRL_C)
    assert app._should_quit is False  # Ctrl+C copies instead of quitting


def test_scroll_key_routes_to_scrollable_focused_widget():
    app = make_app()
    view = ScrollView(0, 0, "300x50")
    for i in range(20):
        view.add(Button(0, i, f"row {i}"))
    app.add(view)
    app.focus(view)
    app._compose()  # establish max_scroll etc.

    app._dispatch_input(Key.SCROLL_DOWN)
    assert view._scroll > 0


def test_mouse_event_routes_through_dispatch_mouse():
    app = make_app()
    b = Button(2, 2, "Go")
    app.add(b)
    clicks = []
    b.on_click(lambda w: clicks.append(w))

    app._dispatch_input(MouseClick(3, 2, 0))
    assert clicks == [b]
