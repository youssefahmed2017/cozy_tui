"""Diff widget: diff_lines() classification, rendering (prefixes + theme
colors), sizing, and its cache."""

import pytest

from cozy_tui import App, Style, Theme, get_theme, set_theme
from cozy_tui.widgets import Diff
from cozy_tui.widgets.display.diff import diff_lines


@pytest.fixture(autouse=True)
def _restore_default_theme():
    # Theme is process-wide global state; every test starts and ends on the
    # default theme so switching it in one test can't leak into another.
    original = get_theme()
    yield
    set_theme(original)


def make_app():
    return App(full=False, size="600x300", style=Style(fg="white", bg="black"))


# ── diff_lines() ──────────────────────────────────────────────────────────────


def test_identical_text_is_all_equal():
    text = "a\nb\nc"
    assert diff_lines(text, text) == [("equal", "a"), ("equal", "b"), ("equal", "c")]


def test_pure_insert():
    assert diff_lines("a\nb", "a\nb\nc") == [
        ("equal", "a"),
        ("equal", "b"),
        ("insert", "c"),
    ]


def test_pure_delete():
    assert diff_lines("a\nb\nc", "a\nb") == [
        ("equal", "a"),
        ("equal", "b"),
        ("delete", "c"),
    ]


def test_replace_shows_old_lines_before_new_lines():
    old = "class Button:\n    def click(self):\n        pass\n"
    new = "class Button:\n    def on_click(self):\n        pass\n"
    assert diff_lines(old, new) == [
        ("equal", "class Button:"),
        ("delete", "    def click(self):"),
        ("insert", "    def on_click(self):"),
        ("equal", "        pass"),
    ]


def test_matches_the_user_mockup_ordering():
    old = "class Button:\n    def click(self):\n        pass\n"
    new = (
        "class Button:\n    def on_click(self):\n        pass\n\n"
        "    def hover(self):\n        ...\n"
    )
    assert diff_lines(old, new) == [
        ("equal", "class Button:"),
        ("delete", "    def click(self):"),
        ("insert", "    def on_click(self):"),
        ("equal", "        pass"),
        ("insert", ""),
        ("insert", "    def hover(self):"),
        ("insert", "        ..."),
    ]


def test_blank_lines_are_preserved():
    assert diff_lines("a\n\nb", "a\n\nb") == [
        ("equal", "a"),
        ("equal", ""),
        ("equal", "b"),
    ]


def test_empty_strings_produce_no_lines():
    assert diff_lines("", "") == []


# ── Diff widget ───────────────────────────────────────────────────────────────
# Each rendered row is a list of (text, style) *segments* (gutter+marker,
# then the code) -- helpers below flatten a row for text/width assertions.


def _row_text(row) -> str:
    return "".join(text for text, _style in row)


def test_natural_size_matches_rendered_rows():
    d = Diff(0, 0, "class Button:\n    def click(self):\n", "class Button:\n")
    rows = d._rendered_rows()
    assert d.natural_height(10) == len(rows)
    assert d.natural_width(10) == max(len(_row_text(row)) for row in rows)


def test_empty_diff_reports_height_one_and_does_not_crash():
    app = make_app()
    d = Diff(0, 0, "", "")
    app.add(d)
    app.snapshot()  # must not raise
    assert d.natural_height(10) == 1


def test_draw_writes_line_numbers_and_markers():
    app = make_app()
    d = Diff(2, 1, "a\nb\n", "a\nc\n")
    app.add(d)
    snap = app.snapshot()
    lines = [l for l in snap.split("\n") if l.strip()]
    assert lines[0].strip() == "1   a"  # equal: no marker, just the line number
    assert "2 - b" in snap
    assert "3 + c" in snap


def test_deleted_and_inserted_rows_are_tagged_and_use_theme_colors():
    app = make_app()
    d = Diff(0, 0, "a\nb\n", "a\nc\n")
    app.add(d)
    app.snapshot()
    theme = get_theme()

    rows_by_marker = {_row_text(row)[2]: row for row in d._rendered_rows()}
    delete_gutter_style = rows_by_marker["-"][0][1]
    insert_gutter_style = rows_by_marker["+"][0][1]
    equal_gutter_style = rows_by_marker[" "][0][1]

    assert delete_gutter_style.fg == theme.error
    assert insert_gutter_style.fg == theme.success
    assert equal_gutter_style.fg == d.style.fg


def test_changed_rows_have_a_tinted_background_unchanged_rows_dont():
    d = Diff(0, 0, "a\nb\n", "a\nc\n")
    rows_by_marker = {_row_text(row)[2]: row for row in d._rendered_rows()}
    base_bg = d.style.raw_bg or "black"
    assert rows_by_marker["-"][0][1].bg != f"{base_bg}_bg"
    assert rows_by_marker["+"][0][1].bg != f"{base_bg}_bg"
    assert rows_by_marker[" "][0][1].bg == f"{base_bg}_bg"


def test_code_segments_are_padded_to_fill_the_widest_line():
    d = Diff(0, 0, "short\n", "a longer line\n")
    rows = d._rendered_rows()
    total_code_widths = {sum(len(text) for text, _style in row[1:]) for row in rows}
    assert (
        len(total_code_widths) == 1
    )  # every row's code padded to the same total width


def test_colors_follow_an_active_theme_switch():
    # Regression class: earlier this session, several widgets hardcoded a
    # color instead of reading get_theme() -- verify Diff isn't one of them.
    set_theme(Theme(mode="monochromatic"))
    d = Diff(0, 0, "a\n", "b\n")
    rows = d._rendered_rows()
    theme = get_theme()
    rows_by_marker = {_row_text(row)[2]: row for row in rows}
    assert rows_by_marker["-"][0][1].fg == theme.error
    assert rows_by_marker["+"][0][1].fg == theme.success


def test_identical_text_has_no_error_or_success_gutters():
    # Scoped to the gutter (row tag), not every code token's color -- with
    # syntax highlighting on, a code token can legitimately render in
    # whatever color happens to equal theme.error/success without that
    # meaning the row itself was misclassified as changed.
    d = Diff(0, 0, "same\ntext\n", "same\ntext\n")
    theme = get_theme()
    for row in d._rendered_rows():
        gutter_style = row[0][1]
        assert gutter_style.fg != theme.error
        assert gutter_style.fg != theme.success


# ── syntax highlighting (Rich's Syntax, no new dependency) ───────────────────


def test_python_is_the_default_lexer_and_tokenizes_keywords():
    d = Diff(0, 0, "def foo():\n    pass\n", "def foo():\n    pass\n")
    assert d.lexer == "python"
    row = d._rendered_rows()[0]
    # more than just [gutter, one plain code blob] -- "def"/"foo"/etc each
    # get their own (text, style) segment from Rich's tokenizer.
    assert len(row) > 2


def test_lexer_none_disables_highlighting():
    d = Diff(0, 0, "def foo():\n    pass\n", "def foo():\n    pass\n", lexer=None)
    row = d._rendered_rows()[0]
    assert len(row) == 2  # just [gutter, one plain code segment]
    assert row[1][0].strip() == "def foo():"


def test_highlighted_code_segments_use_the_rows_tinted_background():
    d = Diff(0, 0, "a = 1\n", "a = 2\n")
    for row in d._rendered_rows():
        gutter_bg = row[0][1].bg
        for _text, style in row[1:]:
            assert style.bg == gutter_bg  # every code segment matches its row's tint


def test_highlighting_survives_a_trailing_newline_without_misaligning():
    # Regression: Rich's own line-splitting (unlike str.splitlines()) counts
    # a trailing "\n" as introducing one more, empty, line -- which used to
    # misalign every _highlight_lines() index against
    # _diff_rows_with_index()'s str.splitlines()-based positions for any
    # text ending in a newline (i.e. nearly all real source files).
    old = "a = 1\nb = 2\n"
    new = "a = 1\nb = 3\n"
    d = Diff(0, 0, old, new)
    rows = d._rendered_rows()
    texts = ["".join(t for t, _s in row[1:]).rstrip() for row in rows]
    assert texts == ["a = 1", "b = 2", "b = 3"]


def test_changing_lexer_invalidates_the_cache():
    d = Diff(0, 0, "a = 1\n", "a = 2\n")
    rows_before = d._rendered_rows()
    d.lexer = None
    rows_after = d._rendered_rows()
    assert rows_after is not rows_before
    assert len(rows_after[0]) == 2  # now plain, unhighlighted


def test_highlight_lines_unit():
    from cozy_tui.widgets.display.diff import _highlight_lines

    rows = _highlight_lines("def foo():\n    pass\n", "python", "white")
    assert len(rows) == 2
    assert "".join(t for t, _s in rows[0]) == "def foo():"
    assert "".join(t for t, _s in rows[1]) == "    pass"


def test_highlight_lines_empty_text_returns_no_rows():
    from cozy_tui.widgets.display.diff import _highlight_lines

    assert _highlight_lines("", "python", "white") == []


def test_rendered_rows_are_cached_until_text_changes():
    d = Diff(0, 0, "a\n", "b\n")
    rows_before = d._rendered_rows()
    assert d._rendered_rows() is rows_before  # same object -- never rebuilt

    d.new_text = "c\n"
    rows_after = d._rendered_rows()
    assert rows_after is not rows_before
    assert rows_after == d._rendered_rows()  # re-cached at the new value


def test_diff_is_not_focusable():
    assert Diff(0, 0, "a", "b").focusable is False
