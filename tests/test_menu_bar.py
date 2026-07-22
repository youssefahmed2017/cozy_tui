from cozy_tui import App, Style
from cozy_tui.events import Key, MouseClick
from cozy_tui.testing import Harness
from cozy_tui.widgets import MenuBar, MenuItem, MenuSeparator, RightClickMenu


def make_ui():
    return Harness(App(full=False, size="400x100", style=Style(fg="white", bg="black")))


def make_bar(app, *, on_new=None, on_copy=None):
    menus = [
        (
            "File",
            [MenuItem("New", on_select=on_new or (lambda it: None)), MenuItem("Quit")],
        ),
        (
            "Edit",
            [MenuItem("Copy", on_select=on_copy or (lambda it: None)), MenuSeparator()],
        ),
        ("View", [MenuItem("Zoom")]),
    ]
    bar = MenuBar(0, 0, menus)
    app.add(bar)
    app.focus(bar)
    return bar


def test_natural_size_and_dock_resize():
    bar = MenuBar(0, 0, [("File", [MenuItem("New")])])
    assert bar.natural_height(10) == 1
    assert bar.natural_width(10) == len(" File ")
    bar.dock_resize(80, 1, 10)
    assert bar._bar_width == 80


def test_label_bounds_after_draw():
    ui = make_ui()
    app = ui.app
    bar = make_bar(app)
    ui.screen
    assert len(bar._label_bounds) == 3
    starts = [s for s, _e in bar._label_bounds]
    assert starts == sorted(starts)  # left to right, increasing


def test_keyboard_left_right_wraps_between_menus():
    ui = make_ui()
    app = ui.app
    bar = make_bar(app)
    ui.screen
    assert bar._index == 0
    bar.on_key(Key.RIGHT)
    bar.on_key(Key.RIGHT)
    assert bar._index == 2
    bar.on_key(Key.RIGHT)
    assert bar._index == 0  # wraps
    bar.on_key(Key.LEFT)
    assert bar._index == 2  # wraps the other way


def test_down_opens_the_highlighted_menu():
    ui = make_ui()
    app = ui.app
    bar = make_bar(app)
    ui.screen
    bar.on_key(Key.DOWN)
    assert isinstance(bar._open_menu, RightClickMenu)
    assert app.focused is bar._open_menu


def test_enter_and_space_also_open():
    for key in (Key.ENTER, " "):
        ui = make_ui()
        app = ui.app
        bar = make_bar(app)
        ui.screen
        bar.on_key(key)
        assert bar._open_menu is not None


def test_esc_closes_and_restores_focus_to_the_bar():
    ui = make_ui()
    app = ui.app
    bar = make_bar(app)
    ui.screen
    bar.on_key(Key.DOWN)
    ui.press(Key.ESC)
    assert bar._open_menu is None
    assert app.focused is bar


def test_mouse_click_on_a_label_opens_its_menu():
    ui = make_ui()
    app = ui.app
    bar = make_bar(app)
    ui.screen
    start, _end = bar._label_bounds[1]  # "Edit"
    ui.click((start, bar.abs_y))
    assert bar._index == 1
    assert bar._open_menu is not None


def test_selecting_an_item_fires_on_select_and_closes_menu():
    calls = []
    ui = make_ui()
    app = ui.app
    bar = make_bar(app, on_new=lambda it: calls.append(it.text))
    ui.screen
    start, _end = bar._label_bounds[0]  # "File"
    ui.click((start, bar.abs_y))
    menu = bar._open_menu
    ui.click((menu.abs_x + 2, menu.abs_y + 1))  # "New" row
    assert calls == ["New"]
    assert bar._open_menu is None
    assert app.focused is bar


def test_click_outside_closes_without_selecting():
    ui = make_ui()
    app = ui.app
    bar = make_bar(app)
    ui.screen
    start, _end = bar._label_bounds[0]
    ui.click((start, bar.abs_y))
    assert bar._open_menu is not None
    ui.click((0, 50))  # far outside the menu
    assert bar._open_menu is None


def test_open_at_is_a_noop_while_already_open():
    ui = make_ui()
    app = ui.app
    bar = make_bar(app)
    ui.screen
    bar.on_key(Key.DOWN)
    first_menu = bar._open_menu
    bar._open_at(1)  # ignored: a menu is already open
    assert bar._open_menu is first_menu


def test_contains_covers_the_full_bar_width():
    ui = make_ui()
    app = ui.app
    bar = make_bar(app)
    ui.screen
    w = bar._bar_width or bar._content_width()
    assert bar.contains(bar.abs_x, bar.abs_y)
    assert bar.contains(bar.abs_x + w - 1, bar.abs_y)
    assert not bar.contains(bar.abs_x + w, bar.abs_y)
    assert not bar.contains(bar.abs_x, bar.abs_y + 1)


def test_empty_menus_do_not_crash():
    ui = make_ui()
    app = ui.app
    bar = MenuBar(0, 0, [])
    app.add(bar)
    app.focus(bar)
    ui.screen
    bar.on_key(Key.RIGHT)
    bar.on_key(Key.DOWN)
    bar.on_mouse_click(0, 0)
    assert bar._open_menu is None


def test_snapshot_shows_all_labels():
    ui = make_ui()
    app = ui.app
    bar = make_bar(app)
    snap = ui.screen.split("\n")[0]
    assert "File" in snap and "Edit" in snap and "View" in snap


def test_docked_to_top_spans_full_width():
    ui = make_ui()
    app = ui.app
    bar = MenuBar(0, 0, [("File", [MenuItem("New")])])
    app.dock(bar, "top")
    ui.screen
    assert bar._bar_width == app.cols
