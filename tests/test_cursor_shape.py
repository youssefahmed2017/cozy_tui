"""The terminal cursor: DECSCUSR shape selection (cozy_tui/ansi.py) and the
escape App emits for the focused widget."""

import pytest

from cozy_tui import App, Style
from cozy_tui.testing import Harness
from cozy_tui.ansi import TERMINAL_CURSOR_STYLES, cursor_shape_esc
from cozy_tui.widgets import Input, Label


def make_ui():
    return Harness(App(full=False, size="400x60", style=Style(fg="white", bg="black")))


def focused_input(ui, **kw):
    inp = Input(0, 0, 10, **kw)
    inp.value = "hi"
    inp.cursor_pos = 2
    ui.app.widgets = [inp]
    ui.focus(inp)
    return inp


# ── the shape table ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "style, flash, expected",
    [
        ("block", True, "\033[1 q"),
        ("block", False, "\033[2 q"),
        ("underline", True, "\033[3 q"),
        ("underline", False, "\033[4 q"),
        ("vertical", True, "\033[5 q"),
        ("vertical", False, "\033[6 q"),
    ],
)
def test_decscusr_codes(style, flash, expected):
    assert cursor_shape_esc(style, flash) == expected


def test_blinking_shapes_are_odd_and_steady_are_even():
    for style in TERMINAL_CURSOR_STYLES:
        blink = int(cursor_shape_esc(style, True)[2:-2])
        steady = int(cursor_shape_esc(style, False)[2:-2])
        assert blink % 2 == 1
        assert steady == blink + 1


def test_unknown_style_has_no_shape():
    # Empty, so the caller knows to fall back to painting its own caret.
    assert cursor_shape_esc("swirl") == ""
    assert cursor_shape_esc(None) == ""


def test_every_builtin_input_style_is_terminal_drawn():
    assert TERMINAL_CURSOR_STYLES == {"block", "underline", "vertical"}


# ── what the app emits ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "style, flash, shape",
    [
        ("vertical", True, "\033[5 q"),
        ("vertical", False, "\033[6 q"),
        ("block", True, "\033[1 q"),
        ("block", False, "\033[2 q"),
        ("underline", True, "\033[3 q"),
        ("underline", False, "\033[4 q"),
    ],
)
def test_app_emits_position_shape_and_show(style, flash, shape):
    ui = make_ui()
    app = ui.app
    focused_input(ui, cursor_style=style, flash=flash)
    esc = app._cursor_esc()
    assert esc == f"\033[1;3H{shape}\033[?25h"


def test_the_escape_does_not_change_as_the_blink_timer_toggles():
    # The terminal owns the blink now, so the loop's BLINK_INTERVAL wake has
    # nothing to write — toggling visibility ourselves would fight it.
    ui = make_ui()
    app = ui.app
    focused_input(ui, cursor_style="vertical", flash=True)
    before = app._cursor_esc()
    app._cursor_on = not app._cursor_on
    assert app._cursor_esc() == before


def test_cursor_is_hidden_with_nothing_focused():
    ui = make_ui()
    app = ui.app
    app.focus(None)
    assert app._cursor_esc() == "\033[?25l"


def test_cursor_is_hidden_for_a_widget_that_wants_none():
    ui = make_ui()
    app = ui.app
    app.widgets = [Label(0, 0, "x")]
    app.focus(None)
    assert app._cursor_esc() == "\033[?25l"


def test_cursor_is_hidden_when_the_input_disables_it():
    ui = make_ui()
    app = ui.app
    focused_input(ui, cursor=False)
    assert app._cursor_esc() == "\033[?25l"


def test_unknown_style_gets_no_terminal_cursor():
    ui = make_ui()
    app = ui.app
    focused_input(ui, cursor_style="swirl")
    assert app._cursor_esc() == "\033[?25l"


# ── no double-drawn caret ────────────────────────────────────────────────────


def cells(ui, row=0):
    return ui.app.buffer[row]


@pytest.mark.parametrize("style", sorted(TERMINAL_CURSOR_STYLES))
def test_terminal_drawn_styles_paint_no_caret_into_the_buffer(style):
    # Two carets -- one from the terminal, one in the cells -- is the bug this
    # shared TERMINAL_CURSOR_STYLES set exists to prevent.
    ui = make_ui()
    app = ui.app
    focused_input(ui, cursor_style=style)
    cell = cells(ui)[2]  # the cursor column
    assert "underline" not in cell.style.styles


def test_a_custom_style_still_paints_its_own_caret():
    ui = make_ui()
    app = ui.app
    app._cursor_on = True
    focused_input(ui, cursor_style="swirl")
    assert "underline" in cells(ui)[2].style.styles
