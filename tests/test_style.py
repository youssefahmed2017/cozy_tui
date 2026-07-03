import pytest

from cozy_tui import ansi
from cozy_tui.ansi import get_color_depth, set_color_depth, style_esc
from cozy_tui.style import Style


@pytest.fixture(autouse=True)
def truecolor_baseline():
    """Pin truecolor for a deterministic baseline (the real default depends on
    the environment's TERM/COLORTERM), and restore afterwards. Tests that
    exercise downgrade set their own depth, which this still restores."""
    original = get_color_depth()
    set_color_depth("truecolor")
    yield
    set_color_depth(original)


def test_named_foreground():
    assert style_esc("red", None, ()) == "\033[0;31m"


def test_named_background_suffix_and_order():
    # Style stores bg with a _bg suffix; bg code precedes fg code.
    s = Style(fg="red", bg="blue")
    assert s.bg == "blue_bg"
    assert style_esc(s.fg, s.bg, s.styles) == "\033[0;44;31m"


def test_truecolor_rgb():
    assert style_esc("rgb(10,20,30)", None, ()) == "\033[0;38;2;10;20;30m"


def test_hex_foreground():
    assert style_esc("#0a141e", None, ()) == "\033[0;38;2;10;20;30m"


def test_hex_shorthand_expands():
    # "#abc" -> "#aabbcc"
    assert style_esc("#abc", None, ()) == "\033[0;38;2;170;187;204m"


def test_hex_background_gets_no_named_suffix():
    s = Style(fg="white", bg="#0000ff")
    assert s.bg == "#0000ff"  # not "#0000ff_bg"
    assert style_esc(s.fg, s.bg, s.styles) == "\033[0;48;2;0;0;255;37m"


def test_indexed_256_foreground_and_background():
    assert style_esc("color(200)", None, ()) == "\033[0;38;5;200m"
    s = Style(bg="color(17)")
    assert s.bg == "color(17)"  # no _bg suffix
    assert style_esc(None, s.bg, ()) == "\033[0;48;5;17m"


def test_styles_appended():
    assert style_esc("white", None, ("bold", "underline")) == "\033[0;37;1;4m"


def test_empty_style_is_reset():
    assert style_esc(None, None, ()) == "\033[0m"


def test_depth_none_suppresses_color_but_keeps_attributes():
    set_color_depth("none")
    # fg/bg dropped; bold (a text attribute, not a color) is kept.
    assert style_esc("red", "blue", ("bold",)) == "\033[0;1m"
    assert style_esc("#ff0000", None, ()) == "\033[0m"


def test_depth_256_downgrades_truecolor():
    set_color_depth("256")
    # Pure red maps into the 6x6x6 cube: 16 + 36*5 = 196.
    assert style_esc("#ff0000", None, ()) == "\033[0;38;5;196m"
    # An explicit color(N) index passes through unchanged at 256.
    assert style_esc("color(200)", None, ()) == "\033[0;38;5;200m"


def test_depth_16_snaps_to_nearest_named():
    set_color_depth("16")
    # Pure red → bright_red fg (91); as bg it becomes 101.
    assert style_esc("#ff0000", None, ()) == "\033[0;91m"
    assert style_esc(None, "#ff0000", ()) == "\033[0;101m"


def test_set_color_depth_rejects_unknown():
    with pytest.raises(ValueError):
        set_color_depth("32bit")
