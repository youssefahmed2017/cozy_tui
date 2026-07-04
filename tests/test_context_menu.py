"""Right-click routing and the RightClickMenu widget."""

from cozy_tui import App, Style
from cozy_tui.events import MouseClick
from cozy_tui.widgets import Button, MenuItem, MenuSeparator, RightClickMenu


def make_app():
    return App(full=False, size="800x400", style=Style(fg="white", bg="black"))


# ── right-click routing ─────────────────────────────────────────────────────────


def test_right_click_fires_global_hook_with_target():
    app = make_app()
    btn = Button(0, 0, "Hi")
    app.add(btn)
    seen = []
    app.on_right_click(lambda col, row, w: seen.append((col, row, w)))
    app._dispatch_mouse(MouseClick(1, 0, 2))  # btn 2 = right
    assert seen == [(1, 0, btn)]


def test_right_click_over_empty_space_passes_none():
    app = make_app()
    seen = []
    app.on_right_click(lambda col, row, w: seen.append(w))
    app._dispatch_mouse(MouseClick(40, 20, 2))
    assert seen == [None]


def test_right_click_does_not_focus_or_activate_widget():
    app = make_app()
    activated = []
    btn = Button(0, 0, "Hi").on_click(lambda b: activated.append(b))
    app.add(btn)
    app._dispatch_mouse(MouseClick(1, 0, 2))
    assert app.focused is None  # right-click never steals focus
    assert activated == []      # nor activates


def test_left_click_still_focuses_and_activates():
    app = make_app()
    activated = []
    btn = Button(0, 0, "Hi").on_click(lambda b: activated.append(b))
    app.add(btn)
    app._dispatch_mouse(MouseClick(1, 0, 0))  # btn 0 = left
    assert app.focused is btn
    assert activated == [btn]


def test_per_widget_right_click_handler_fires():
    app = make_app()
    got = []
    btn = Button(0, 0, "Hi").on_right_click(lambda w, col, row: got.append((col, row)))
    app.add(btn)
    app._dispatch_mouse(MouseClick(1, 0, 2))
    assert got == [(1, 0)]


def test_global_hook_can_consume_and_skip_widget():
    app = make_app()
    got = []
    btn = Button(0, 0, "Hi").on_right_click(lambda w, col, row: got.append(1))
    app.add(btn)
    app.on_right_click(lambda col, row, w: True)  # consume
    app._dispatch_mouse(MouseClick(1, 0, 2))
    assert got == []  # per-widget handler skipped because the hook consumed it


# ── the menu widget ─────────────────────────────────────────────────────────────


def test_open_at_opens_modal_overlay_at_point():
    app = make_app()
    menu = RightClickMenu([MenuItem("A"), MenuItem("B")])
    menu.open_at(app, 5, 3)
    assert app._overlays[-1].widget is menu
    assert (menu.x, menu.y) == (5, 3)
    assert app._topmost_modal() is not None


def test_open_at_clamps_to_screen_edges():
    app = make_app()
    menu = RightClickMenu([MenuItem("Longer label"), MenuItem("B")])
    menu.open_at(app, app.cols - 1, app.rows - 1)  # bottom-right corner
    assert menu.x + menu.natural_width(app.SCALE) <= app.cols
    assert menu.y + menu.natural_height(app.SCALE) <= app.rows


def test_navigation_skips_separator_and_disabled():
    menu = RightClickMenu(
        [
            MenuItem("Copy"),
            MenuItem("Paste"),
            MenuSeparator(),
            MenuItem("Delete", enabled=False),
        ]
    )
    assert menu.selected_index == 0
    menu._move(1)
    assert menu.selected_index == 1
    menu._move(1)  # would land on separator then disabled — stays put
    assert menu.selected_index == 1


def test_initial_index_skips_leading_separator():
    menu = RightClickMenu([MenuSeparator(), MenuItem("First")])
    assert menu.selected_index == 1


def test_enter_activates_selected_and_closes():
    app = make_app()
    chosen = []
    menu = RightClickMenu(
        [
            MenuItem("Copy", on_select=lambda i: chosen.append(i.text)),
            MenuItem("Paste", on_select=lambda i: chosen.append(i.text)),
        ]
    )
    menu.open_at(app, 2, 2)
    menu._move(1)  # -> Paste
    from cozy_tui.events import Key

    menu.on_key(Key.ENTER)
    assert chosen == ["Paste"]
    assert not app._overlays  # menu closed itself


def test_click_on_item_selects_it():
    app = make_app()
    chosen = []
    menu = RightClickMenu(
        [MenuItem("Copy", on_select=lambda i: chosen.append("copy")),
         MenuItem("Paste", on_select=lambda i: chosen.append("paste"))]
    )
    menu.open_at(app, 0, 0)
    # Row layout: border(0), Copy(1), Paste(2). Click the Paste row.
    menu.on_mouse_click(2, menu.abs_y + 2)
    assert chosen == ["paste"]


def test_click_on_disabled_item_does_nothing():
    app = make_app()
    chosen = []
    menu = RightClickMenu(
        [MenuItem("Copy", on_select=lambda i: chosen.append("copy")),
         MenuItem("Nope", on_select=lambda i: chosen.append("nope"), enabled=False)]
    )
    menu.open_at(app, 0, 0)
    menu.on_mouse_click(2, menu.abs_y + 2)  # the disabled row
    assert chosen == []
    assert app._overlays  # still open


def test_hover_highlights_item_without_selecting():
    menu = RightClickMenu([MenuItem("Copy"), MenuItem("Paste")])
    menu.x, menu.y = 0, 0
    menu.on_mouse_move(3, menu.abs_y + 2)  # hover the Paste row
    assert menu.selected_index == 1
