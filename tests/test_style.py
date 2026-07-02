from cozy_tui.ansi import style_esc
from cozy_tui.style import Style


def test_named_foreground():
    assert style_esc("red", None, ()) == "\033[0;31m"


def test_named_background_suffix_and_order():
    # Style stores bg with a _bg suffix; bg code precedes fg code.
    s = Style(fg="red", bg="blue")
    assert s.bg == "blue_bg"
    assert style_esc(s.fg, s.bg, s.styles) == "\033[0;44;31m"


def test_truecolor_rgb():
    assert style_esc("rgb(10,20,30)", None, ()) == "\033[0;38;2;10;20;30m"


def test_styles_appended():
    assert style_esc("white", None, ("bold", "underline")) == "\033[0;37;1;4m"


def test_empty_style_is_reset():
    assert style_esc(None, None, ()) == "\033[0m"
