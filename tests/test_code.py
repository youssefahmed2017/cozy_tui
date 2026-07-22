"""The Code widget: Rich/Pygments syntax highlighting bridged into the cell
grid (cozy_tui/widgets/display/code.py)."""

import pytest

from cozy_tui import App, State, Style
from cozy_tui.events import Key
from cozy_tui.testing import Harness
from cozy_tui.widgets import Box, Code, ScrollView


def make_ui():
    app = App(full=False, size="900x300", style=Style(fg="white", bg="black"))
    return Harness(app)


def styles_of(code):
    code._sync()
    return [style for row in code._rows for _text, style in row]


# ── basics ───────────────────────────────────────────────────────────────────


def test_renders_the_source_onto_the_screen():
    ui = make_ui()
    ui.app.add(Code('print("hello world")', lang="python", x=0, y=0))
    ui.compose()
    assert ui.line(0) == 'print("hello world")'


def test_the_documented_constructor_form_works():
    # Exactly as advertised: source first, lang by keyword, no position.
    code = Code('print("helloworld")', lang="python")
    code_js = Code('console.log("helllo")', lang="javascript")
    assert (code.x, code.y) == (0, 0)
    assert code.code == 'print("helloworld")'
    assert code_js.lang == "javascript"


def test_multiline_source_spans_rows():
    ui = make_ui()
    ui.app.add(Code("a = 1\nb = 2\nc = 3", lang="python", x=0, y=0))
    ui.compose()
    assert [ui.line(i) for i in range(3)] == ["a = 1", "b = 2", "c = 3"]


def test_blank_lines_are_preserved():
    ui = make_ui()
    ui.app.add(Code("a = 1\n\nb = 2", lang="python", x=0, y=0))
    ui.compose()
    assert ui.line(1) == ""
    assert ui.line(2) == "b = 2"


def test_empty_source_is_harmless():
    code = Code("", lang="python")
    assert code.natural_height(App.SCALE) >= 1
    assert code.natural_width(App.SCALE) >= 1


# ── highlighting ─────────────────────────────────────────────────────────────


def test_source_is_actually_highlighted():
    code = Code('def greet():\n    print("hi")', lang="python")
    colors = {style.fg for style in styles_of(code)}
    assert len(colors) > 1  # not one flat color -- tokens got distinct styles


def test_the_lang_changes_the_highlighting():
    # `def` is a keyword in Python and a bare identifier in JSON, so the same
    # text highlights differently depending on the lexer.
    source = "def x"
    py = {s.fg for s in styles_of(Code(source, lang="python"))}
    js = {s.fg for s in styles_of(Code(source, lang="json"))}
    assert py != js


def test_unknown_lang_falls_back_to_plain_text():
    # A viewer must never crash mid-draw over a lexer name; Rich renders the
    # text unhighlighted instead, which is the right outcome.
    ui = make_ui()
    ui.app.add(Code("who knows", lang="not_a_real_language", x=0, y=0))
    ui.compose()
    assert ui.line(0) == "who knows"


def test_background_can_be_turned_off():
    plain = Code("a = 1", lang="python", background=False)
    assert all(style.bg is None for style in styles_of(plain))


# ── sizing ───────────────────────────────────────────────────────────────────


def test_auto_size_fits_the_longest_line():
    code = Code("a = 1\nlonger_name = 22", lang="python")
    assert code.natural_width(App.SCALE) == len("longer_name = 22")
    assert code.natural_height(App.SCALE) == 2


def test_explicit_width_is_respected():
    code = Code("a = 1", lang="python", width=30)
    assert code.natural_width(App.SCALE) == 30


def test_line_numbers_add_a_gutter():
    ui = make_ui()
    ui.app.add(Code("a = 1\nb = 2", lang="python", x=0, y=0, line_numbers=True))
    ui.compose()
    assert "1 a = 1" in ui.line(0)
    assert "2 b = 2" in ui.line(1)


def test_line_number_gutter_widens_the_block():
    plain = Code("a = 1", lang="python")
    numbered = Code("a = 1", lang="python", line_numbers=True)
    assert numbered.natural_width(App.SCALE) > plain.natural_width(App.SCALE)


def test_contains_covers_the_rendered_block():
    code = Code("a = 1\nb = 2", lang="python", x=3, y=2)
    assert code.contains(3, 2)
    assert code.contains(3, 3)
    assert not code.contains(3, 4)  # one row past the end
    assert not code.contains(2, 2)


def test_tab_size_expands_tabs():
    ui = make_ui()
    ui.app.add(Code("if x:\n\tpass", lang="python", x=0, y=0, tab_size=8))
    ui.compose()
    assert ui.line(1).startswith(" " * 8)


# ── updating ─────────────────────────────────────────────────────────────────


def test_reassigning_code_re_renders():
    ui = make_ui()
    code = Code("a = 1", lang="python", x=0, y=0)
    ui.app.add(code)
    ui.compose()
    assert ui.line(0) == "a = 1"

    code.code = "b = 2\nc = 3"
    ui.compose()
    assert ui.line(0) == "b = 2"
    assert ui.line(1) == "c = 3"
    assert code.natural_height(App.SCALE) == 2


def test_reassigning_lang_re_renders():
    code = Code("def x", lang="json")
    before = {s.fg for s in styles_of(code)}
    code.lang = "python"
    assert {s.fg for s in styles_of(code)} != before


def test_toggling_line_numbers_re_renders():
    code = Code("a = 1", lang="python")
    width = code.natural_width(App.SCALE)
    code.line_numbers = True
    assert code.natural_width(App.SCALE) > width


def test_render_is_cached_between_unchanged_frames():
    # Highlighting is the expensive part; draw() must not redo it every frame.
    code = Code("a = 1", lang="python")
    code._sync()
    rows = code._rows
    code.natural_height(App.SCALE)
    code.natural_width(App.SCALE)
    code._sync()
    assert code._rows is rows


def test_code_can_be_bound_to_a_state():
    source = State("a = 1")
    code = Code(source, lang="python")
    assert code.natural_height(App.SCALE) == 1
    source.value = "a = 1\nb = 2"
    assert code.code == "a = 1\nb = 2"
    assert code.natural_height(App.SCALE) == 2


# ── composition & misuse ─────────────────────────────────────────────────────


def test_positional_coordinates_raise_a_helpful_error():
    # The rest of the library is Widget(x, y, ...); this one isn't, so the
    # likely mistake gets named instead of failing deep inside Pygments.
    with pytest.raises(TypeError, match="keyword-only"):
        Code(2, 1, "print(1)")
    with pytest.raises(TypeError, match="keyword-only"):
        Code(2, 1)


def test_renders_inside_a_box():
    ui = make_ui()
    box = Box(0, 0, "300x60", title="snippet")
    box.add(Code("let a = 1;", lang="javascript", x=1, y=1))
    ui.app.add(box)
    ui.compose()
    assert "let a = 1;" in ui.line(1)


def test_renders_inside_a_scroll_view():
    ui = make_ui()
    view = ScrollView(0, 0, "300x40", autoscroll=False)
    view.add(Code("\n".join(f"line_{i} = {i}" for i in range(20)), lang="python"))
    ui.app.add(view)
    ui.compose()  # must not raise -- taller than its viewport
    assert "line_0 = 0" in ui.line(0)


# ── CodeInput ────────────────────────────────────────────────────────────────


def make_editor(ui, value="", **kw):
    from cozy_tui.widgets import CodeInput

    editor = CodeInput(0, 0, 40, lang="python", **kw)
    editor.value = value
    ui.app.add(editor)
    return editor


def test_code_input_highlights_when_unfocused():
    ui = make_ui()
    editor = make_editor(ui, 'x = "hi"')
    ui.compose()
    colors = {style.fg for style in styles_of(editor)}
    assert len(colors) > 1


def test_code_input_renders_plain_text_while_focused():
    # Focused falls back to Input.draw -- full cursor/selection/scroll
    # fidelity, which is worth more than color while actually typing.
    ui = make_ui()
    editor = make_editor(ui, 'x = "hi"')
    ui.focus(editor)
    ui.compose()
    assert 'x = "hi"' in ui.line(0)


def test_code_input_shows_the_text_either_way():
    ui = make_ui()
    editor = make_editor(ui, "a = 1")
    ui.compose()
    assert "a = 1" in ui.line(0)
    ui.focus(editor)
    ui.compose()
    assert "a = 1" in ui.line(0)


def test_code_input_code_mirrors_value():
    ui = make_ui()
    editor = make_editor(ui, "a = 1")
    assert editor.code == "a = 1"
    editor.value = "b = 2"
    assert editor.code == "b = 2"


def test_code_input_code_is_read_only():
    # One source of truth: Code's renderer reads Input's value rather than
    # keeping a second copy that could drift.
    ui = make_ui()
    editor = make_editor(ui, "a = 1")
    with pytest.raises(AttributeError):
        editor.code = "c = 3"


def test_code_input_rehighlights_after_typing():
    ui = make_ui()
    editor = make_editor(ui, "")
    ui.focus(editor)
    for ch in "x = 1":
        editor.on_key(ch)
    assert editor.value == "x = 1"
    ui.focus(None)
    ui.compose()
    assert "x = 1" in ui.line(0)
    assert len({style.fg for style in styles_of(editor)}) > 1


def test_code_input_editing_keys_still_work():
    ui = make_ui()
    editor = make_editor(ui, "")
    ui.focus(editor)
    for ch in "abc":
        editor.on_key(ch)
    editor.on_key(Key.BACKSPACE)
    assert editor.value == "ab"


def test_code_input_is_multiline_by_default():
    ui = make_ui()
    editor = make_editor(ui, "a = 1\nb = 2")
    assert editor.multiline is True
    assert editor.natural_height(App.SCALE) >= 2
