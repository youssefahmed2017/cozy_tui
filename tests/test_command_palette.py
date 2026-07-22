from cozy_tui import App, Style
from cozy_tui.events import Key, MouseClick
from cozy_tui.testing import Harness
from cozy_tui.widgets import Command, CommandPalette
from cozy_tui.widgets.display.bindings import Bindings


def make_ui(**kw):
    return Harness(App(full=False, size="800x300", style=Style(fg="white", bg="black"), **kw))


# ── Command / CommandPalette (direct, no App) ────────────────────────────────


def test_command_defaults():
    c = Command("Save")
    assert c.name == "Save" and c.description == "" and c.callback is None


def test_palette_matches_default_to_all_commands():
    cmds = [Command("Save"), Command("Load")]
    p = CommandPalette(cmds)
    assert p._matches == cmds
    assert p._index == 0


def test_palette_filters_by_name_or_description():
    cmds = [
        Command("Save", description="Write the file to disk"),
        Command("Load", description="Read a file from disk"),
        Command("Quit"),
    ]
    p = CommandPalette(cmds)
    for ch in "disk":  # only in the descriptions, not any name
        p.on_key(ch)
    assert [c.name for c in p._matches] == ["Save", "Load"]

    for _ in range(4):
        p.on_key(Key.BACKSPACE)
    for ch in "quit":
        p.on_key(ch)
    assert [c.name for c in p._matches] == ["Quit"]


def test_palette_navigation_clamps_without_wrapping():
    cmds = [Command(str(i)) for i in range(5)]
    p = CommandPalette(cmds)
    p.on_key(Key.UP)  # already at 0
    assert p._index == 0
    for _ in range(10):
        p.on_key(Key.DOWN)
    assert p._index == 4  # clamped, not wrapped
    p.on_key(Key.HOME)
    assert p._index == 0
    p.on_key(Key.END)
    assert p._index == 4


def test_palette_enter_fires_on_select_with_the_highlighted_command():
    picked = []
    cmds = [Command("A"), Command("B"), Command("C")]
    p = CommandPalette(cmds, on_select=picked.append)
    p.on_key(Key.DOWN)
    p.on_key(Key.ENTER)
    assert picked == [cmds[1]]


def test_palette_empty_matches_do_not_crash():
    picked = []
    p = CommandPalette([Command("Save")], on_select=picked.append)
    for ch in "nonexistent":
        p.on_key(ch)
    assert p._matches == []
    p.on_key(Key.UP)
    p.on_key(Key.DOWN)
    p.on_key(Key.ENTER)
    assert picked == []


def test_palette_mouse_click_picks_the_two_line_row():
    picked = []
    cmds = [Command("A", description="first"), Command("B", description="second")]
    p = CommandPalette(cmds, on_select=picked.append)
    p.x, p.y = 0, 0
    # row 0/1 (border + search) header rows; command A spans rows 2-3, B spans 4-5
    p.on_mouse_click(col=p.abs_x + 2, row=p.abs_y + 4)
    assert picked == [cmds[1]]


def test_palette_scrolls_when_matches_exceed_height():
    cmds = [Command(str(i)) for i in range(10)]
    p = CommandPalette(cmds, height=3)
    for _ in range(5):
        p.on_key(Key.DOWN)
    assert p._index == 5
    assert p._scroll_off == 5 - 3 + 1  # clamped so index stays in view


# ── App wiring: built-in commands, Ctrl+P, register_command ─────────────────


def test_default_commands_are_registered():
    ui = make_ui()
    app = ui.app
    assert list(app._commands.keys()) == [
        "Quit",
        "Change Theme",
        "Keys",
        "Save Screenshot",
    ]


def test_toggle_devtools_command_only_registered_when_debug():
    ui = make_ui(debug=True)
    app = ui.app
    assert "Toggle DevTools" in app._commands
    app2 = make_ui(debug=False).app
    assert "Toggle DevTools" not in app2._commands


def test_register_command_adds_and_overrides_by_name():
    ui = make_ui()
    app = ui.app
    calls = []
    app.register_command(
        "My Thing", lambda: calls.append("mine"), description="does a thing"
    )
    assert "My Thing" in app._commands
    assert app._commands["My Thing"].description == "does a thing"

    app.register_command("My Thing", lambda: calls.append("mine2"))
    assert len(app._commands) == 5  # still one entry, not two
    app._commands["My Thing"].callback()
    assert calls == ["mine2"]


def test_ctrl_p_is_bound_and_labeled():
    ui = make_ui()
    app = ui.app
    assert Key.CTRL_P in app._key_handlers
    assert app._key_handlers[Key.CTRL_P] == app.open_command_palette
    assert app._bindings[Key.CTRL_P] == ("Command palette", "App")
    assert Key.CTRL_P == Key.ctrl("p")
    assert Key.label(Key.CTRL_P) == "Ctrl+P"


def test_ctrl_p_opens_a_command_palette_and_focuses_it():
    ui = make_ui()
    app = ui.app
    ui.screen
    ui.press(Key.CTRL_P)
    ui.screen
    assert len(app._overlays) == 1
    palette = app._overlays[-1].widget
    assert isinstance(palette, CommandPalette)
    assert app.focused is palette


def test_esc_cancels_without_running_anything():
    ui = make_ui()
    app = ui.app
    ui.screen
    ui.press(Key.CTRL_P)
    ui.screen
    ui.press(Key.ESC)
    ui.screen
    assert app._overlays == []
    assert app._should_quit is False


def test_picking_quit_sets_should_quit():
    ui = make_ui()
    app = ui.app
    ui.screen
    ui.press(Key.CTRL_P)
    ui.screen
    for ch in "quit":
        ui.press(ch)
    ui.screen
    ui.press(Key.ENTER)
    ui.screen
    assert app._should_quit is True
    assert app._overlays == []  # the palette itself closed first


def test_picking_keys_opens_a_bindings_legend():
    ui = make_ui()
    app = ui.app
    ui.screen
    ui.press(Key.CTRL_P)
    ui.screen
    for ch in "keys":
        ui.press(ch)
    ui.screen
    ui.press(Key.ENTER)
    ui.screen
    assert len(app._overlays) == 1
    assert isinstance(app._overlays[-1].widget, Bindings)

    ui.press(Key.ESC)
    ui.screen
    assert app._overlays == []


def test_picking_change_theme_opens_the_theme_palette():
    from cozy_tui.widgets import ThemePalette

    ui = make_ui()

    app = ui.app
    ui.screen
    ui.press(Key.CTRL_P)
    ui.screen
    for ch in "theme":
        ui.press(ch)
    ui.screen
    ui.press(Key.ENTER)
    ui.screen
    assert isinstance(app._overlays[-1].widget, ThemePalette)


def test_click_on_a_command_row_runs_it():
    ui = make_ui()
    app = ui.app
    ui.screen
    ui.press(Key.CTRL_P)
    ui.screen
    palette = app._overlays[-1].widget
    # "Quit" is the first registered command -> first row, spanning 2 lines.
    row_y = palette.abs_y + 2
    ui.click((palette.abs_x + 2, row_y))
    ui.screen
    assert app._should_quit is True


def test_ctrl_p_can_be_overridden_by_the_users_own_binding():
    ui = make_ui()
    app = ui.app
    calls = []
    app.on_key(Key.CTRL_P, lambda: calls.append("mine"), description="My thing")
    ui.press(Key.CTRL_P)
    assert calls == ["mine"]
    assert app._bindings[Key.CTRL_P] == ("My thing", None)
