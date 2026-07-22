"""Inline markup parsing (cozy_tui.markup) and the widgets that opt into it.

The parser is pure logic, so most of this needs no app; the widget half uses
the Harness and reads colors back out of the cell grid.
"""

import pytest

from cozy_tui import App, Style
from cozy_tui.markup import escape, plain, render, slice_runs, split_lines
from cozy_tui.testing import Harness
from cozy_tui.widgets import (
    AnimatedLabel,
    GlowAnimation,
    Label,
    LevitateAnimation,
    Log,
    Text,
)


def styled(markup, base=None):
    """render() as (text, fg, bg, styles) tuples — easier to assert on."""
    return [
        (text, s.fg, s.bg, s.styles) for text, s in render(markup, base)
    ]


# ── parsing ──────────────────────────────────────────────────────────────────


def test_a_tag_colors_the_text_until_it_is_closed():
    assert styled("[red]bad[/] ok") == [
        ("bad", "red", None, ()),
        (" ok", None, None, ()),
    ]


def test_several_words_in_one_tag_combine():
    (text, fg, bg, styles), = styled("[bold red]Error[/]")
    assert (text, fg, styles) == ("Error", "red", ("bold",))


def test_on_sets_the_background():
    (_text, fg, bg, _styles), = styled("[white on red]bad[/]")
    assert (fg, bg) == ("white", "red_bg")


def test_tags_nest_and_inherit_the_enclosing_style():
    runs = styled("[bold][red]a[/]b[/]")
    assert runs == [("a", "red", None, ("bold",)), ("b", None, None, ("bold",))]


def test_a_closing_tag_may_name_what_it_closes():
    assert styled("[red]a[/red]b") == styled("[red]a[/]b")


def test_an_unclosed_tag_runs_to_the_end():
    assert styled("[red]forever") == [("forever", "red", None, ())]


@pytest.mark.parametrize(
    "markup, color",
    [
        ("[#ff8800]x[/]", "#ff8800"),
        ("[#f80]x[/]", "#f80"),
        ("[rgb(255,136,0)]x[/]", "rgb(255,136,0)"),
        ("[color(33)]x[/]", "color(33)"),
        ("[bright_black]x[/]", "bright_black"),
    ],
)
def test_every_color_form_style_understands_is_a_valid_tag(markup, color):
    assert styled(markup) == [("x", color, None, ())]


def test_spaces_inside_a_color_function_are_not_token_separators():
    assert styled("[rgb(255, 136, 0)]x[/]") == [("x", "rgb(255,136,0)", None, ())]


@pytest.mark.parametrize(
    "text",
    [
        "list[0]",
        "[INFO] server ready",
        "a[a-z]+b",
        "[]",
        "[red on]x",  # dangling "on"
        "[on on red]x",
        "[not_a_color]x",
        "[/]nothing was open",
    ],
)
def test_a_bracket_group_that_is_not_a_real_tag_stays_literal(text):
    # This is what makes markup=True safe on a Log fed by someone else's
    # output: brackets are common, and dropping them would corrupt the line.
    assert plain(text) == text
    assert styled(text) == [(text, None, None, ())]


def test_a_backslash_escapes_a_tag_that_would_otherwise_parse():
    assert plain(r"\[red]not a tag") == "[red]not a tag"
    assert plain(escape("[red]")) == "[red]"


def test_tags_resolve_against_the_base_style():
    base = Style(fg="white", bg="blue", styles=["dim"])
    assert styled("plain[bold]b[/]", base) == [
        ("plain", "white", "blue_bg", ("dim",)),
        ("b", "white", "blue_bg", ("dim", "bold")),
    ]


def test_plain_strips_every_tag():
    assert plain("[red]R[/]\n[green]G[/]") == "R\nG"


def test_split_lines_divides_a_run_that_spans_a_newline():
    lines = split_lines(render("[red]a\nb[/]"))
    assert [[t for t, _s in line] for line in lines] == [["a"], ["b"]]


def test_slice_runs_cuts_on_character_positions():
    runs = render("[red]abc[/]def")
    assert [t for t, _s in slice_runs(runs, 2, 5)] == ["c", "de"]


# ── widgets ──────────────────────────────────────────────────────────────────


def make_ui(*widgets):
    app = App(full=False, size="600x300")
    for w in widgets:
        app.add(w)
    return Harness(app)


def test_label_without_markup_draws_tags_verbatim():
    ui = make_ui(Label(0, 0, "[red]hi[/]"))
    assert "[red]hi[/]" in ui.line(0)


def test_label_with_markup_colors_the_text_and_hides_the_tags():
    ui = make_ui(Label(0, 0, "[red]hi[/] there", markup=True))
    assert ui.line(0).strip() == "hi there"
    assert ui.cell(0, 0).style.fg == "red"
    assert ui.cell(3, 0).style.fg is None


def test_a_markup_label_measures_its_visible_width_not_its_tags():
    assert Label(0, 0, "[red]hi[/]", markup=True).natural_width(10) == 2
    assert Label(0, 0, "[red]hi[/]").natural_width(10) == 10  # tags counted


def test_a_markup_label_reparses_when_its_text_is_reassigned():
    label = Label(0, 0, "[red]a[/]", markup=True)
    ui = make_ui(label)
    label.text = "[blue]Blue![/]"
    assert ui.line(0).strip() == "Blue!"
    assert ui.cell(0, 0).style.fg == "blue"


def test_text_styles_each_of_its_lines_independently():
    ui = make_ui(Text(0, 0, "[red]R[/]\n[green]G[/]\n[blue]B[/]", markup=True))
    assert (ui.line(0)[0], ui.line(1)[0], ui.line(2)[0]) == ("R", "G", "B")
    assert ui.cell(0, 0).style.fg == "red"
    assert ui.cell(0, 1).style.fg == "green"
    assert ui.cell(0, 2).style.fg == "blue"


def test_text_carries_styles_across_a_wrap():
    # The wrapped halves of one tagged phrase must both stay red -- the wrap
    # happens on the plain text, and the runs are sliced to match.
    ui = make_ui(Text(0, 0, "[red]hello world[/]", size="6x3", markup=True))
    assert ui.line(0).startswith("hello")
    assert ui.line(1).startswith("world")
    assert ui.cell(0, 0).style.fg == "red"
    assert ui.cell(0, 1).style.fg == "red"


def test_text_alignment_still_lands_the_styled_run_in_the_right_place():
    ui = make_ui(Text(0, 0, "[red]ab[/]", size="6x1", align="right", markup=True))
    assert ui.line(0)[:6] == "    ab"
    assert ui.cell(4, 0).style.fg == "red"


def test_a_color_animation_keeps_its_own_foreground_over_the_tag():
    # Glow animates fg, so the tag can't win there -- but its attributes do.
    label = AnimatedLabel(
        0, 0, "[bold]RED[/]", animation=GlowAnimation(color_template="red"), markup=True
    )
    ui = make_ui(label)
    assert ui.line(0).strip() == "RED"
    assert ui.cell(0, 0).style.fg.startswith("rgb(")
    assert "bold" in ui.cell(0, 0).style.styles


def test_a_motion_animation_leaves_the_tag_color_intact():
    label = AnimatedLabel(
        0,
        0,
        "[red]RED[/]",
        animation=LevitateAnimation(amplitude=0),
        markup=True,
    )
    ui = make_ui(label)
    assert ui.cell(0, 0).style.fg == "red"


# ── Log ──────────────────────────────────────────────────────────────────────


def test_log_appends_one_row_per_call():
    log = Log(0, 0, "400x60")
    ui = make_ui(log)
    log.log("first")
    log.log("second")
    assert log.lines == ["first", "second"]
    screen = ui.screen
    assert "first" in screen and "second" in screen


def test_log_joins_several_values_like_print():
    log = Log()
    log.log("count:", 42)
    assert log.lines == ["count: 42"]


def test_log_splits_an_embedded_newline_into_separate_rows():
    log = Log()
    log.log("a\nb")
    assert log.lines == ["a", "b"]
    assert len(log.children) == 2


def test_log_markup_colors_a_line():
    log = Log(0, 0, "400x60", markup=True)
    ui = make_ui(log)
    log.log("[red]THIS IS RED[/]")
    assert "THIS IS RED" in ui.screen
    assert ui.cell(0, 0).style.fg == "red"


def test_log_drops_the_oldest_lines_past_max_lines():
    log = Log(max_lines=3)
    for i in range(6):
        log.log(f"line {i}")
    assert log.lines == ["line 3", "line 4", "line 5"]
    # Rows stay numbered 0..n-1, which is what ScrollView measures against.
    assert [c.y for c in log.children] == [0, 1, 2]
    assert [c.text for c in log.children] == ["line 3", "line 4", "line 5"]


def test_log_clear_empties_both_the_lines_and_the_rows():
    log = Log()
    log.log("a")
    log.clear()
    assert log.lines == [] and log.children == []


def test_log_autoscrolls_to_the_newest_line():
    log = Log(0, 0, "400x30")  # 3 rows tall
    ui = make_ui(log)
    for i in range(20):
        log.log(f"line {i}")
    # ScrollView eases toward the bottom rather than jumping: the first draw
    # starts the tween, and the clock has to move before it lands.
    ui.compose()
    ui.advance(0.5)
    assert "line 19" in ui.screen
    assert "line 0" not in ui.screen
