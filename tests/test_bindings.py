from cozy_tui import App, Style
from cozy_tui.widgets import Bindings


def make_app():
    return App(full=False, size="800x300", style=Style(fg="white", bg="black"))


def render(app):
    app.clear()
    for w in app.widgets:
        w.draw(app)


def rows_text(app, x, y, w, h):
    return ["".join(c.char for c in app.buffer[y + r][x : x + w]) for r in range(h)]


def test_flat_auto_sizes():
    b = Bindings(
        0, 0, {"↑": "Move Up", "↓": "Move Down", "Enter": "Select", "Esc": "Quit"}
    )
    # keys: max width 5 ("Enter"); descs: max 9 ("Move Down"); gap 3
    assert b._content_w == 5 + 3 + 9
    assert b.natural_width(1) == b._content_w + 4
    assert b.natural_height(1) == 4 + 2  # 4 bindings + 2 border rows


def test_sectioned_layout_and_size():
    b = Bindings(
        0,
        0,
        {
            "Movement": {"↑": "Move Up", "↓": "Move Down"},
            "Actions": {"Enter": "Select", "Esc": "Quit"},
        },
    )
    # rows: header, bind, bind, blank, header, bind, bind = 7
    assert b.natural_height(1) == 7 + 2
    # global key column width across all sections is 5 ("Enter")
    assert b._key_w == 5


def test_title_widens_when_needed():
    b = Bindings(0, 0, {"a": "x"}, title="A Very Long Panel Title")
    assert b._content_w >= len("A Very Long Panel Title")


def test_renders_keys_and_descriptions():
    app = make_app()
    b = Bindings(1, 1, {"↑": "Move Up", "Esc": "Quit"}, title="Keys")
    app.add(b)
    render(app)
    lines = rows_text(app, b.abs_x, b.abs_y, b.natural_width(1), b.natural_height(1))
    joined = "\n".join(lines)
    assert "Keys" in lines[0]  # title in the top border
    assert "↑" in joined and "Move Up" in joined
    assert "Esc" in joined and "Quit" in joined
    # keys share a column: "Esc" and "↑" both start at the same x
    up_row = next(r for r in lines if "Move Up" in r)
    esc_row = next(r for r in lines if "Quit" in r)
    assert up_row.index("↑") == esc_row.index("Esc")


def test_not_focusable():
    b = Bindings(0, 0, {"q": "quit"})
    assert b.focusable is False


# ── auto / app sync ──────────────────────────────────────────────────────────

from cozy_tui.events import Key  # noqa: E402


def _app_with_bindings():
    app = make_app()
    app.on_key(Key.UP, lambda: None, description="Move Up", section="Movement")
    app.on_key(Key.DOWN, lambda: None, description="Move Down", section="Movement")
    app.on_key(Key.ENTER, lambda: None, description="Select", section="Actions")
    app.on_key(Key.ESC, lambda: None, description="Quit", section="Actions")
    app.on_key(Key.F1, lambda: None)  # no description -> omitted from the legend
    return app


def test_auto_explicit_app_builds_sections():
    app = _app_with_bindings()
    b = Bindings(0, 0, app)  # explicit app form
    # 2 headers + 4 binds + 1 blank spacer = 7 rows
    assert b.natural_height(1) == 7 + 2
    assert b._key_w == text_width("Enter")  # widest shown key ("↑","↓","Enter","Esc")


def test_auto_relabels_keys_and_skips_undescribed():
    app = _app_with_bindings()
    b = Bindings(1, 1, "auto")
    app.add(b)
    render(app)
    joined = "\n".join(
        rows_text(app, b.abs_x, b.abs_y, b.natural_width(1), b.natural_height(1))
    )
    assert "Movement" in joined and "Actions" in joined
    assert "↑" in joined and "Move Up" in joined  # Key.UP -> "↑"
    assert "Esc" in joined and "Quit" in joined  # Key.ESC -> "Esc"
    assert "F1" not in joined  # no description -> not shown


def test_auto_resyncs_when_bindings_change():
    app = make_app()
    app.on_key(Key.ESC, lambda: None, description="Quit")
    b = Bindings(0, 0, app)
    h1 = b.natural_height(1)
    app.on_key(Key.F5, lambda: None, description="Refresh")  # register a new one
    assert b.natural_height(1) == h1 + 1  # legend grew by a row


from cozy_tui._width import text_width  # noqa: E402
