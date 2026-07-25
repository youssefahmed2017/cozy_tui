"""Sparkline and BarChart: value→glyph mapping, scaling, and the data forms
they accept. Mostly pure logic on the render helpers; the Harness where a full
row's layout matters."""

from cozy_tui import App, State
from cozy_tui.testing import Harness
from cozy_tui.widgets import BarChart, Sparkline


def make_ui(*widgets, size="600x200"):
    app = App(full=False, size=size)
    for w in widgets:
        app.add(w)
    return Harness(app)


# ── Sparkline ─────────────────────────────────────────────────────────────────


def test_values_map_across_the_eight_levels():
    line = Sparkline(0, 0, [0, 1, 2, 3, 4, 5, 6, 7], minimum=0, maximum=7)._line()
    assert line == "▁▂▃▄▅▆▇█"


def test_min_and_max_default_to_the_data_range():
    # lowest value → lowest bar, highest → highest, regardless of absolute size
    assert Sparkline(0, 0, [10, 40, 70])._line()[0] == "▁"
    assert Sparkline(0, 0, [10, 40, 70])._line()[-1] == "█"


def test_flat_data_renders_a_mid_level_line():
    assert Sparkline(0, 0, [5, 5, 5])._line() == "▅▅▅"  # frac 0.5 → mid level


def test_an_empty_sparkline_draws_nothing():
    assert Sparkline(0, 0, [])._line() == ""
    assert Sparkline(0, 0, []).natural_width(1) == 0


def test_width_shows_the_most_recent_values():
    sp = Sparkline(0, 0, [1, 2, 3, 4, 5], width=3)
    assert sp._shown() == [3, 4, 5]  # newest three
    assert sp.natural_width(1) == 3


def test_push_appends_and_trims_to_width():
    sp = Sparkline(0, 0, [1, 2, 3], width=3)
    sp.push(4)
    assert sp.values == [2, 3, 4]  # oldest dropped, so the line scrolls left


def test_sparkline_values_may_be_a_state():
    values = State([1, 2])
    ui = make_ui(Sparkline(0, 0, values))
    assert ui.line(0)[:2] == "▁█"
    values.set([9, 1])
    assert ui.line(0)[:2] == "█▁"


# ── BarChart ──────────────────────────────────────────────────────────────────


def test_data_forms_all_normalize_to_label_value_color():
    assert BarChart(0, 0, [("a", 3)])._items() == [("a", 3.0, None)]
    assert BarChart(0, 0, {"a": 3})._items() == [("a", 3.0, None)]
    assert BarChart(0, 0, [5, 6])._items() == [("", 5.0, None), ("", 6.0, None)]
    assert BarChart(0, 0, [("a", 3, "red")])._items() == [("a", 3.0, "red")]


def test_a_bar_fills_proportionally_to_the_max():
    bc = BarChart(0, 0)
    assert bc._bar(10, 10, 8) == "████████"  # full
    assert bc._bar(5, 10, 8) == "████    "  # half
    assert bc._bar(0, 10, 8) == "        "  # empty


def test_a_bar_uses_eighth_of_a_cell_precision():
    # one 64th of an 8-cell bar is a single eighth of the first cell
    assert BarChart(0, 0)._bar(1, 64, 8) == "▏       "


def test_natural_height_is_one_row_per_item():
    assert BarChart(0, 0, [("a", 1), ("b", 2), ("c", 3)]).natural_height(1) == 3


def test_a_rendered_row_has_label_bar_and_value():
    ui = make_ui(BarChart(0, 0, [("apples", 42), ("figs", 63)], width=30))
    row = ui.line(0)
    assert row.startswith("apples ")  # label, right-padded to the widest
    assert "█" in row
    assert row.rstrip().endswith("42")  # value printed after the bar


def test_show_values_false_drops_the_number():
    ui = make_ui(BarChart(0, 0, [("a", 42)], width=20, show_values=False))
    assert "42" not in ui.line(0)


def test_the_largest_value_fills_the_bar_area():
    # plums is the max, so its bar area is entirely full blocks
    ui = make_ui(BarChart(0, 0, [("plums", 63), ("figs", 5)], width=30))
    assert "█" in ui.line(0)
    assert ui.line(1).count("█") < ui.line(0).count("█")  # figs is much shorter


def test_barchart_data_may_be_a_state():
    data = State([("a", 1)])
    bc = BarChart(0, 0, data, width=20)
    ui = make_ui(bc)
    assert ui.line(0).startswith("a ")
    data.set([("a", 1), ("b", 2)])
    assert bc.natural_height(1) == 2
    assert ui.line(1).startswith("b ")


def test_uncapped_charts_are_inert():
    # No height cap → decorative: not a Tab stop, doesn't grab scroll keys.
    assert Sparkline(0, 0).focusable is False
    assert BarChart(0, 0).focusable is False
    assert BarChart(0, 0).scrollable is False


# ── BarChart scrolling (height cap) ─────────────────────────────────────────────


def _rows(n):
    return [(f"p{i}", i + 1) for i in range(n)]


def test_a_height_cap_makes_the_chart_a_scrollable_viewport():
    bc = BarChart(0, 0, _rows(20), width=20, height=5)
    assert bc.focusable is True  # can take keyboard focus
    assert bc.scrollable is True  # App routes wheel/page keys to it
    assert bc.natural_height(1) == 5  # reserves the fixed viewport, not 20 rows


def test_only_the_visible_window_is_drawn():
    bc = BarChart(0, 0, _rows(20), width=20, height=5)
    ui = make_ui(bc)
    # labels rjust to the widest ("p19"), so shorter ones carry a leading space
    assert ui.line(0).lstrip().startswith("p0 ")  # top of the list
    assert ui.line(4).lstrip().startswith("p4 ")  # fifth row is the last visible
    # row 5 is below the viewport: the chart drew nothing there
    assert "p5" not in ui.line(5)


def test_scrolling_advances_the_window():
    bc = BarChart(0, 0, _rows(20), width=20, height=5)
    ui = make_ui(bc)
    bc.scroll_by(3)
    ui.compose()
    assert ui.line(0).lstrip().startswith("p3 ")  # window moved down by three items


def test_scroll_clamps_to_the_content_floor_and_ceiling():
    bc = BarChart(0, 0, _rows(20), width=20, height=5)
    make_ui(bc).compose()
    assert bc._max_scroll == 15  # 20 items - 5 rows
    bc.scroll_to(999)
    assert bc._scroll == 15  # can't scroll past the last full page
    bc.scroll_by(-999)
    assert bc._scroll == 0


def test_no_scrollbar_when_everything_fits():
    bc = BarChart(0, 0, _rows(3), width=20, height=8)
    ui = make_ui(bc)
    ui.compose()
    assert bc._max_scroll == 0
    assert bc._bar_col is None  # nothing to scroll → no scrollbar column
