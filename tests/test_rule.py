"""The Rule divider widget: sizing (explicit / auto-fill / docked), the titled
form, and orientation. Pure-logic where possible; the Harness where a Box's
interior width has to be measured for real."""

import pytest

from cozy_tui import App, State, Style
from cozy_tui.testing import Harness
from cozy_tui.widgets import Box, Label, Rule, VBox


def make_ui(*widgets, size="600x200"):
    app = App(full=False, size=size)
    for w in widgets:
        app.add(w)
    return Harness(app)


# ── sizing ────────────────────────────────────────────────────────────────────


def test_explicit_length_is_that_many_cells():
    r = Rule(0, 0, length=10)
    assert r.natural_width(1) == 10
    assert r.natural_height(1) == 1
    ui = make_ui(r)
    assert ui.line(0).startswith("─" * 10)
    assert ui.line(0)[10:11] != "─"  # and no more than that


def test_a_rule_in_a_box_fills_the_interior_without_overhanging_the_border():
    box = Box(0, 0, "300x60", border="rounded")  # 30-cell interior
    box.add(Rule(1, 1))
    ui = make_ui(box)
    line = ui.line(1)
    # │ borders on both ends, a solid run of ─ between them, nothing spilling out
    assert line[0] == "│"
    inner = line[1:31]
    assert inner == "─" * 30
    assert line[31] == "│"


def test_auto_fill_starts_from_the_rules_x_offset():
    box = Box(0, 0, "300x60", border="rounded")  # 30 interior
    box.add(Rule(5, 1))  # inset 4 cells from the interior's left
    ui = make_ui(box)
    line = ui.line(1)
    assert line[1:5] == "    "  # blank up to x=5
    assert line[5:31] == "─" * 26  # fills the rest to the right border
    assert line[31] == "│"


def test_dock_resize_sets_the_length_for_a_docked_or_stretched_rule():
    r = Rule(0, 0)
    r.dock_resize(24, 1, 1)
    assert r.natural_width(1) == 24


def test_a_stretched_rule_fills_a_docked_vboxs_width():
    app = App(full=False, size="800x240")  # 80 cols
    vbox = VBox(0, 0, align="stretch")
    vbox.add(Label(0, 0, "top"))
    rule = Rule()
    vbox.add(rule)
    app.dock(vbox, "fill")
    app._apply_docks()
    vbox.natural_width(app.SCALE)  # force _arrange()
    assert rule.natural_width(1) == app.cols


def test_no_container_and_no_length_falls_back_to_a_default():
    assert Rule(0, 0).natural_width(1) == Rule._DEFAULT


# ── the titled form ───────────────────────────────────────────────────────────


def test_a_title_sits_in_the_line_and_the_rest_fills():
    ui = make_ui(Rule(0, 0, length=20, title="Setup"))
    line = ui.line(0)[:20]
    assert line == "── Setup ───────────"
    assert len(line) == 20


def test_a_title_longer_than_the_rule_is_clipped_to_it():
    ui = make_ui(Rule(0, 0, length=6, title="Way too long"))
    line = ui.line(0)
    assert line[:6] == "── Way"  # clipped at the rule's own width
    assert line[6:7] != "y"  # nothing past cell 6


def test_the_title_may_be_a_state():
    title = State("A")
    ui = make_ui(Rule(0, 0, length=12, title=title))
    assert "A" in ui.line(0)
    title.set("B")
    assert "B" in ui.line(0)
    assert "A" not in ui.line(0)


def test_a_title_is_ignored_on_a_vertical_rule():
    # Vertical rules draw a column of the glyph; the title only makes sense on a
    # horizontal one, so it's simply not rendered rather than raising.
    ui = make_ui(Rule(0, 0, length=3, orientation="vertical", title="x"))
    assert [ui.cell(0, r).char for r in range(3)] == ["│", "│", "│"]


# ── orientation & appearance ──────────────────────────────────────────────────


def test_vertical_rule_is_one_cell_wide_and_length_tall():
    r = Rule(0, 0, length=4, orientation="vertical")
    assert r.natural_width(1) == 1
    assert r.natural_height(1) == 4


def test_char_overrides_the_glyph():
    ui = make_ui(Rule(0, 0, length=5, char="="))
    assert ui.line(0).startswith("=====")


def test_a_bad_orientation_is_rejected():
    with pytest.raises(ValueError):
        Rule(0, 0, orientation="diagonal")


def test_a_rule_is_never_focusable():
    assert Rule(0, 0).focusable is False
